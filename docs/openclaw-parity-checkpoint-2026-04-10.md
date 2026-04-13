# OpenClaw Parity Checkpoint

Date: 2026-04-10
Source of truth: `C:\Users\skull\OneDrive\Documents\openclaw-main`
Target: `C:\Users\skull\OneDrive\Documents\OpenZues`

## Source inventory

OpenClaw's current surface area breaks down into these major domains:

| Domain | OpenClaw source evidence | OpenZues status on 2026-04-10 |
| --- | --- | --- |
| Gateway | `openclaw-main/README.md` sections for Gateway, WebSocket control plane, auth, remote access, logging, doctor | Partial. OpenZues already has a local-first control plane, App Server transport management, approvals, events, diagnostics, and mission control, but it is not a drop-in OpenClaw gateway. |
| Onboarding | `openclaw-main/README.md` onboarding and wizard references | Gap. OpenZues has connection setup flows, but not an OpenClaw-style onboarding wizard across channels, gateway, and skills. |
| CLI | `openclaw-main/README.md` CLI surface for `gateway`, `agent`, `send`, `doctor`, `nodes`, `channels` | Gap. OpenZues exposes a focused control-plane CLI, not a broad OpenClaw operator/runtime CLI. |
| Channels | `openclaw-main/README.md` multi-channel inbox list and per-channel docs | Gap. OpenZues does not implement WhatsApp/Telegram/Slack/Discord/etc. channel runtimes. |
| Routing | `openclaw-main/README.md` multi-agent routing, group routing, retry/chunking docs | Partial. OpenZues has missions, lane targeting, failover, and interference logic, but not OpenClaw's channel/account routing layer. |
| Voice | `openclaw-main/README.md` Voice Wake and Talk Mode references | Gap. No voice wake/talk-mode companion stack in OpenZues. |
| Canvas | `openclaw-main/README.md` Live Canvas and A2UI references | Gap. No agent-driven canvas host in OpenZues. |
| Nodes | `openclaw-main/docs/nodes/*.md` camera, audio, images, location, screen recording, node pairing | Gap. OpenZues has no node runtime or node RPC surface today. |
| Skills | `openclaw-main/README.md` skills platform, workspace skills, ClawHub references | Partial and improving. OpenZues already publishes live lane skills and now has project skill pins plus claw-style builtin mission skillbooks. |
| Browser | `openclaw-main/README.md` browser control and Chrome/Chromium tooling | Gap. OpenZues can use browser verification in development workflows, but does not ship an OpenClaw browser-control plane. |
| Packaging | `openclaw-main/README.md` channels, Docker, appcast, platform packaging, remote deployment docs | Gap. OpenZues is packaged as a Python app and lacks OpenClaw's multi-platform packaging matrix. |
| Companion apps | `openclaw-main/README.md` macOS app, iOS node, Android node | Gap. OpenZues currently has no companion app family. |

Deeper source inventory from `openclaw-main`:

- 104 extension packages under `extensions/`
- 53 bundled skills under `skills/`
- 31 channel docs under `docs/channels/`
- full native companion stacks under `apps/macos`, `apps/android`, and `apps/ios`

Highest-leverage source reference seams by domain:

- Gateway: `src/gateway/server.impl.ts`, `src/gateway/server-methods.ts`, `src/gateway/server-http.ts`, `src/gateway/server-startup-plugins.ts`
- Onboarding: `src/commands/onboard.ts`, `src/wizard/setup.ts`, `src/commands/onboard-skills.ts`, `src/flows/channel-setup.ts`
- CLI: `openclaw.mjs`, `src/entry.ts`, `src/cli/program/build-program.ts`, `src/cli/program/command-registry.ts`
- Channels: `src/flows/channel-setup.ts`, `src/channels/plugins/index.ts`, plus extension package metadata under `extensions/*/package.json`
- Routing: `src/routing/resolve-route.ts`, `docs/channels/channel-routing.md`
- Voice: `src/plugin-sdk/realtime-voice.ts`, `docs/plugins/voice-call.md`, `apps/macos/.../VoiceWakeRuntime.swift`, `apps/android/.../TalkModeManager.kt`
- Canvas: `src/canvas-host/server.ts`, `src/agents/tools/canvas-tool.ts`, `docs/platforms/mac/canvas.md`
- Nodes: `src/agents/tools/nodes-tool.ts`, `src/cli/nodes-cli/register.ts`, `docs/nodes/index.md`, shared mobile/runtime node code under `apps/android` and `apps/shared/OpenClawKit`
- Skills: `src/agents/skills/workspace.ts`, `src/agents/skills/config.ts`, `src/cli/skills-cli.ts`, `docs/tools/skills.md`
- Browser: `extensions/browser/index.ts`, `extensions/browser/src/cli/browser-cli.ts`, `extensions/browser/src/browser/control-service.ts`, `docs/tools/browser.md`
- Packaging: root `package.json`, `pnpm-workspace.yaml`, `packages/plugin-package-contract/src/index.ts`, platform packaging scripts under `scripts/` and `apps/*`
- Companion apps: shared transport/model code under `apps/shared/OpenClawKit`, plus onboarding stacks in `apps/macos`, `apps/android`, and `apps/ios`

## Completed this turn

The highest-leverage slice already in flight and now checkpointed is the operator-supervision layer that mirrors OpenClaw's control-plane strengths without pretending to have channel/node parity yet.

Completed slice:

- Ops Mesh Sidecar Phase 1 is effectively landed in the worktree: operator inbox, integration readiness inventory, skills registry, and richer lane snapshots.
- Missions now resolve claw-style builtin mission skillbooks and weave them into autonomous prompts, alongside project-specific skill pins.
- Final-answer handoffs clear mission execution state cleanly, which keeps lane ownership and checkpoint semantics coherent for follow-on runs.
- The README now reflects the new operator-facing surfaces so the shipped product description matches the actual dashboard.
- Ops Mesh Phase 2 hardening has started: synthesized inbox notifications now cover reflex-armed and task-attention cases, and scheduled workflow repair signals remain visible even when the underlying mission already appears as failed or blocked.

Primary OpenZues files carrying this slice:

- `src/openzues/services/ops_mesh.py`
- `src/openzues/services/skillbook.py`
- `src/openzues/services/missions.py`
- `src/openzues/web/templates/index.html`
- `src/openzues/web/static/app.js`
- `src/openzues/schemas.py`

## Verification

Targeted automated verification passed from the repo virtualenv:

- `.\.venv\Scripts\python.exe -m pytest tests/test_missions.py tests/test_ops_mesh.py tests/test_app.py tests/test_database.py -q`
- Result: `86 passed`
- Remote-ops regression coverage also passed:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_remote_ops.py -q`
  - Result: `3 passed`

Browser verification against a live local server on `http://127.0.0.1:8877`:

- Page loaded with content.
- No framework error overlay was present.
- `agent-browser errors` returned empty output.
- `agent-browser console` returned empty output.
- DOM checks confirmed the new surfaces are present:
  - `#skills-registry-headline`
  - `#integrations-inventory-headline`
  - `#lane-snapshots`
- Live headings confirmed the new operator sections actually rendered, including:
  - `Operator inbox is active`
  - `Skills registry has live gaps`
  - `Inventory the external systems around each repo`
  - `Recurring workflows, routes, and lane history`
  - `Runs in motion, blocked, or ready for handoff`
- Browser artifact captured at `openzues-browser-check.png`.

## What remains

Large parity gaps still open against OpenClaw:

- onboarding wizard
- broad CLI parity
- channel runtime layer
- channel and account routing parity
- browser-control runtime parity
- canvas runtime parity
- nodes and companion apps
- voice surfaces
- packaging and release-channel parity

## Next best slice

Do not jump to nodes, channels, or companion apps next. The next best slice is to finish Ops Mesh Phase 2 so the control plane can act on the visibility it now has.

Recommended next slice:

- add recurring scheduled launches for playbooks and mission drafts
- continue hardening notification delivery rules for approvals, failed runs, due work, checkpoint review, and continuity warnings
- keep reusing existing `missions`, `mission_checkpoints`, `projects`, `server_requests`, and event-hub primitives instead of inventing a second scheduler or workflow engine

Broader parity ordering after the current Ops Mesh thread is stabilized:

1. gateway/plugin bootstrap and method-registry seams
2. onboarding/config mutation flows
3. routing/session-key policy
4. nodes/canvas minimum useful runtime
5. skills/browser ecosystem seams

That order reflects where OpenClaw's product leverage actually lives. It is a better long-range parity sequence than cloning channels or native UIs first.

## Blockers

No credential blocker hit during this turn. The major remaining work is product scope, not access.

## Operator handoff

- Completed: verified the in-flight Ops Mesh parity slice already present in the OpenZues worktree, refreshed the OpenClaw inventory checkpoint, and confirmed the dashboard renders the new operator surfaces live.
- Verified: `86 passed` across missions, ops mesh, app, and database tests; `3 passed` for remote ops; live browser check passed on `http://127.0.0.1:8877` with no console or overlay errors.
- Next step: keep the current thread on Ops Mesh Phase 2 by landing recurring scheduled launches for playbooks and mission drafts, then harden notification routing for approvals, failures, due work, and checkpoint review.
- Blockers: none beyond normal product-scope depth.

## Update: Scheduled Playbook Slice

Date: 2026-04-10

### Completed this turn

- Closed the remaining Ops Mesh Phase 2 scheduling gap by adding recurring playbook launches beside the already-landed scheduled mission drafts.
- Playbooks now persist scheduler state in SQLite: `cadence_minutes`, `enabled`, `default_variables`, `last_run_at`, `last_status`, and `last_result_summary`.
- The existing Ops Mesh loop now executes due scheduled playbooks directly through the current `PlaybookService` instead of inventing a second workflow runner.
- Manual playbook runs also persist run health, so the library shows the latest status regardless of whether the run was operator-triggered or schedule-triggered.
- Failed scheduled playbooks now surface back into the operator inbox as repair items, which keeps broken recurring routines visible instead of silently failing in the background.
- The dashboard library UI now exposes cadence, enabled state, default variables, next-run timing, and last-result summaries for playbooks.

Primary files carrying this slice:

- `src/openzues/schemas.py`
- `src/openzues/database.py`
- `src/openzues/services/playbooks.py`
- `src/openzues/services/ops_mesh.py`
- `src/openzues/app.py`
- `src/openzues/web/templates/index.html`
- `src/openzues/web/static/app.js`

### Verification

Targeted automated verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_playbooks.py tests/test_database.py tests/test_ops_mesh.py tests/test_app.py -q`
- Result: `71 passed`

Browser verification passed on a live local server at `http://127.0.0.1:8877` using `agent-browser.cmd`:

- page loaded successfully
- no framework error overlay was detected
- body content rendered
- console error capture returned `[]`
- the new playbook schedule controls were present in the DOM:
  - `input[name="cadence_minutes"]`
  - `textarea[name="default_variables"]`
  - `input[name="enabled"]`
- browser artifact refreshed at `openzues-browser-check.png`

### What remains

OpenZues still lacks the larger OpenClaw parity surfaces:

- onboarding wizard and first-run bootstrap
- broad CLI parity
- channels and channel routing
- browser-control runtime
- canvas and nodes
- voice surfaces
- packaging matrix and companion apps

### Next best slice

Do not jump to channels, nodes, or native apps next. The next smallest verified slice should turn the current manual setup forms into a web-first onboarding/bootstrap flow.

Recommended next slice:

- add a first-run setup sequence that wires desktop bridge, project, remote operator, vault secret, skill pin, and first scheduled task in one path
- reuse the current `instances`, `projects`, `operators`, `vault_secrets`, `skill_pins`, and `task_blueprints` APIs instead of creating a second config system
- keep the output as saved product state plus a launch-ready first mission draft, not a passive checklist

### Blockers

No credential or approval blocker hit during this turn.

### Operator handoff

- Completed: landed recurring scheduled playbook launches, persisted playbook run health, surfaced failed scheduled playbooks in the operator inbox, and exposed cadence/default-variable controls in the dashboard.
- Verified: `71 passed` across playbooks, database, ops mesh, and app tests; browser verification passed on `http://127.0.0.1:8877` with no overlay or console errors.
- Next step: build the onboarding/bootstrap flow that compresses connection, project, credentials, skill pins, and first recurring workflow setup into one operator path.
- Blockers: none.

## Update: Web-First Onboarding QuickStart

Date: 2026-04-10

### Completed this turn

- Landed a composite onboarding/bootstrap path that mirrors the highest-leverage OpenClaw onboarding spine without pretending channel or node parity already exists.
- Added a new `/api/onboarding/bootstrap` route that reuses existing OpenZues primitives instead of creating another config system. One request can now stage or reuse a Desktop lane, register the workspace, reuse or create the operator team, issue a remote API key, vault a credential, attach the first tracked integration, pin a project skill, and create or update the first recurring task blueprint.
- The bootstrap route returns a launch-ready mission draft generated from the existing task blueprint machinery, so the first handoff automatically includes project skill pins and known integration inventory in the mission objective.
- Added a dedicated QuickStart panel to the dashboard library shell. It shows setup readiness across lane, workspace, remote access, vaulting, and recurring tasking, and it can preload the generated launch draft directly into the mission composer.
- Kept the slice additive and durable: it reuses `RuntimeManager`, `AccessService`, `VaultService`, `OpsMeshService`, `projects`, `skill_pins`, `integrations`, and `task_blueprints` instead of introducing a second onboarding-only state layer.

Primary files carrying this slice:

- `src/openzues/services/onboarding.py`
- `src/openzues/app.py`
- `src/openzues/schemas.py`
- `src/openzues/web/templates/index.html`
- `src/openzues/web/static/app.js`
- `src/openzues/web/static/app.css`
- `tests/test_app.py`

### Verification

Targeted automated verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_ops_mesh.py -q`
- Result: `68 passed`

Additional integrity checks passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`
- `node --check src/openzues/web/static/app.js`

Browser verification passed on a live local server at `http://127.0.0.1:8877` using `agent-browser.cmd` in shared-session batch mode:

- page title resolved as `OpenZues`
- DOM content was present
- `#onboarding-form` was found
- `#onboarding-headline` resolved to `Bootstrap the first autonomous loop`
- `agent-browser errors` returned no page errors
- `agent-browser console` returned no console output
- browser artifact refreshed at `openzues-browser-check.png`

## Update: Launch Routing and Session-Key Parity

Date: 2026-04-11

### Completed this turn

- Landed a dedicated launch-routing kernel in OpenZues that mirrors the highest-leverage OpenClaw routing seam: one resolver now owns lane selection, provenance, and stable launch session keys.
- Added `LaunchRoutingService` and threaded it through onboarding, setup handoff, gateway bootstrap, Ops Mesh draft generation, and mission creation instead of leaving lane choice spread across ad hoc heuristics.
- Gateway bootstrap state now persists routing policy and continuity hints: `route_binding_mode`, `last_route_instance_id`, and `last_route_resolved_at`.
- Mission drafts and stored missions now carry a durable `session_key`, so repeated launches can keep a stable logical routing identity even when runtime thread ids change.
- Remote-first launches now prefer the last healthy workspace lane, otherwise a connected lane already attached to the saved workspace, before falling back to a generic connected lane.
- The dashboard/setup UI now renders the resolved launch route directly: route mode, match provenance, session key, warnings, and candidate lanes.

Primary files carrying this slice:

- `src/openzues/services/launch_routing.py`
- `src/openzues/services/gateway_bootstrap.py`
- `src/openzues/services/onboarding.py`
- `src/openzues/services/setup.py`
- `src/openzues/services/ops_mesh.py`
- `src/openzues/services/missions.py`
- `src/openzues/database.py`
- `src/openzues/schemas.py`
- `src/openzues/web/static/app.js`
- `src/openzues/web/static/app.css`
- `tests/test_app.py`
- `tests/test_database.py`

### Verification

Focused contract pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`
- Result: `94 passed`

Mission persistence/regression coverage also passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_missions.py -q`
- Result: `29 passed`

Static/runtime checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

Browser verification passed on an isolated local server at `http://127.0.0.1:8766` using `agent-browser.cmd`:

- the page loaded successfully in a writable verification environment
- bootstrap API returned both `launch_route` and `mission_draft.session_key`
- DOM evaluation confirmed the new route card rendered: `document.body.innerHTML.includes("Launch Route") === true`
- DOM evaluation confirmed the rendered HTML contains the resolved session key for the staged launch

### What remains

OpenZues still does not have OpenClaw parity for:

- gateway method-registry and doctor-style capability inventory
- broader CLI parity
- channel runtimes and channel/account routing
- browser-control runtime
- canvas runtime
- nodes and companion apps
- voice surfaces
- packaging and release-channel parity

### Next best slice

Do not jump to channels, nodes, or native apps next. The next best slice is a gateway capability contract that makes the now-deterministic launch routing observable everywhere an operator touches it.

Recommended next slice:

- add a gateway capability/doctor view across API, dashboard, and CLI that summarizes connected lane health, apps/plugins/MCP inventory, approval posture, and launch-policy warnings
- anchor the slice on existing `RuntimeManager`, diagnostics, Ops Mesh integration inventory, and `gateway_bootstrap` state instead of inventing a second gateway subsystem
- keep the output operator-facing and verifiable: one stable capability summary, one warning surface, and one CLI/API/dashboard contract

This is the next smallest useful parity step because routing is now deterministic; the remaining leverage is to expose the gateway surface as a coherent contract before cloning OpenClaw's broader channel/browser ecosystems.

### Blockers

No credential or approval blocker hit during this turn.

### Operator handoff

- Completed: landed the routing/session-key parity slice, persisted launch-route continuity in the gateway profile, threaded session keys into mission drafts and stored missions, and surfaced the route contract in the setup/dashboard UI.
- Verified: `94 passed` across app/database/manager/ops-mesh tests, `29 passed` for mission regressions, `node --check` passed, `compileall` passed, and browser verification confirmed the new launch-route card rendered on a live local server.
- Next step: implement a gateway capability/doctor seam that exposes lane health, plugin/app/MCP inventory, approval posture, and routing warnings consistently across API, dashboard, and CLI.
- Blockers: none.

Browser note:

- single-command `agent-browser` invocations were unreliable because the local daemon restarted during a version mismatch; shared-session batch mode produced stable verification and should be preferred for the next browser pass.

### What remains

The large OpenClaw parity gaps are still open:

- broad CLI parity beyond the current control-plane surface
- gateway/plugin bootstrap and method-registry seams
- channels and channel/account routing
- browser-control runtime parity
- canvas runtime parity
- nodes, voice, and companion apps
- packaging and release-channel parity

### Next best slice

Do not jump to native apps or channels next. The next highest-leverage slice is to close the gateway/bootstrap seam that sits immediately behind onboarding.

Recommended next slice:

- add a gateway/bootstrap control surface that exposes the core runtime defaults now implied by onboarding: lane mode, workspace targeting, auth posture, and safe launch defaults
- start shaping a broader operator CLI around the same primitives so web bootstrap and terminal bootstrap stop diverging
- keep reusing the existing `manager`, `access`, `missions`, and `ops_mesh` services rather than inventing a separate gateway abstraction too early

### Blockers

- No credential blocker hit during this turn.
- Browser verification works, but use `agent-browser` shared-session batch mode until the daemon mismatch noise is gone.

### Operator handoff

- Completed: shipped the web-first onboarding QuickStart slice, including the composite bootstrap endpoint, dashboard QuickStart panel, vault/integration/skill/task orchestration, and launch-ready mission draft handoff.
- Verified: `68 passed` across `test_app.py` and `test_ops_mesh.py`; Python compile and `node --check` passed; browser verification on `http://127.0.0.1:8877` confirmed the onboarding headline and form with no page errors or console output.
- Next step: implement the gateway/bootstrap seam behind onboarding so runtime defaults, auth posture, and broader CLI entrypoints line up with the new QuickStart flow.
- Blockers: none beyond the current `agent-browser` daemon mismatch quirk, which has a working batch-mode workaround.

## Update: Gateway Bootstrap Profile + CLI

Date: 2026-04-11

### Completed this turn

- Landed the next parity seam behind QuickStart: a persisted gateway bootstrap profile that captures the default lane, workspace, operator/team, recurring task, cwd, and safe launch policy instead of leaving those choices implicit in scattered records.
- Wired onboarding to stamp that profile automatically, so the existing web QuickStart path now produces durable gateway/bootstrap state instead of only creating resources.
- Added a one-time backfill path that derives the profile from existing task/project/operator artifacts when older databases predate this slice, which keeps the current OpenZues workspace moving forward without rerunning setup by hand.
- Exposed the profile through the product surface:
  - `GET /api/gateway/bootstrap`
  - `PUT /api/gateway/bootstrap`
  - dashboard payload via `gateway_bootstrap`
  - terminal commands `openzues gateway show` and `openzues gateway bootstrap`
- Added a dashboard Gateway Profile panel in the QuickStart section so operators can see the saved bootstrap posture and launch defaults directly in the UI.

Primary files carrying this slice:

- `src/openzues/services/gateway_bootstrap.py`
- `src/openzues/services/onboarding.py`
- `src/openzues/database.py`
- `src/openzues/schemas.py`
- `src/openzues/app.py`
- `src/openzues/cli.py`
- `src/openzues/web/templates/index.html`
- `src/openzues/web/static/app.js`
- `src/openzues/web/static/app.css`
- `tests/test_app.py`
- `tests/test_database.py`

### Verification

Targeted automated verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_database.py tests/test_app.py -q`
- Result: `59 passed`

Static integrity checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

CLI smoke verification passed against an isolated temp data dir:

- `python -m openzues.cli gateway bootstrap ... --instance-mode create_desktop --json`
- `python -m openzues.cli gateway show --json`
- Result: the bootstrap command created the lane/project/operator/task bundle and the follow-up show command read back the saved staged gateway profile from SQLite.

Browser verification passed on a fresh local server at `http://127.0.0.1:8878` using `agent-browser.cmd`:

- page title resolved as `OpenZues`
- page loaded successfully
- no page errors were reported
- no console output was reported
- screenshot artifact refreshed at `openzues-browser-check.png`

Live API verification on that same server confirmed the new bootstrap surface was present and populated:

- `/api/dashboard` returned `gateway_bootstrap.status = staged`
- `/api/gateway/bootstrap` returned the saved default lane/workspace/operator/task profile

### What remains

OpenZues still lacks the larger OpenClaw parity surfaces:

- re-entrant `setup` vs `onboard` CLI split
- onboarding `keep / modify / reset` flows and reset scopes
- explicit local vs remote gateway bootstrap modes
- richer operational handoff after setup completion
- broad CLI parity beyond bootstrap and control-plane commands
- channels and channel/account routing
- browser-control runtime
- canvas runtime, nodes, voice, companion apps, and packaging matrix

### Next best slice

Do not jump to channels or companion apps next. The next smallest high-leverage slice is to make onboarding re-entrant and operator-safe the way OpenClaw does.

Recommended next slice:

- add a lightweight `openzues setup` initializer beside `openzues gateway bootstrap`
- let bootstrap inspect existing state and choose `keep`, `modify`, or `reset`
- support reset scopes analogous to OpenClaw: config only, config plus credentials/session state, and full workspace bootstrap reset
- finish the flow with an operational handoff that names the saved defaults, connection posture, and recommended next entrypoint instead of stopping at “saved”

That extends the current gateway/bootstrap contract without scattering setup logic across separate web and terminal paths again.

### Blockers

- No credential blocker hit during this turn.
- Browser automation confirmed the page and API surfaces cleanly, but the agent-browser accessibility snapshot remained shallow on the right-rail QuickStart region; use the API payload plus screenshot artifact as the reliable verification pair for this slice.

### Operator handoff

- Completed: shipped the persisted gateway bootstrap profile, wired onboarding and CLI bootstrap to save it, added dashboard/API visibility, and backfilled older databases from existing QuickStart artifacts.
- Verified: `59 passed` across database and app tests; `node --check` and Python compile passed; CLI bootstrap/show smoke passed in an isolated temp data dir; browser verification on `http://127.0.0.1:8878` loaded with no page or console errors; live API returned populated `gateway_bootstrap` data.
- Next step: build the re-entrant `setup`/`onboard` seam with keep/modify/reset behavior and a stronger final operational handoff.
- Blockers: none beyond the known `agent-browser` snapshot shallowness on deep right-rail content.

## Update: Re-entrant Setup Posture + Scoped Reset

Date: 2026-04-11

### Completed this turn

- Closed the next onboarding parity seam from OpenClaw's setup flow: OpenZues now has an explicit setup posture service instead of a one-shot bootstrap path.
- Added durable setup footprint tracking so the product remembers which lane, workspace, operator, task, and optional first-run resources were created or reused during bootstrap.
- Added a new setup inspection surface that explains whether the operator should `bootstrap`, `keep`, `modify`, or `reset`, and it finishes with a concrete operational handoff instead of stopping at "saved".
- Added scoped reset behavior with OpenClaw-style intent:
  - `config`: clear the saved gateway bootstrap profile
  - `config+creds+sessions`: clear the profile, revoke the saved operator API key, clear saved approval/session requests, and disconnect the current lane
  - `full`: additionally remove bootstrap-managed resources when it is safe to do so, while preserving history-bound records when deletion would orphan audit state
- Added a lightweight CLI seam beside `openzues gateway bootstrap`:
  - `openzues setup`
  - `openzues setup bootstrap`
  - `openzues setup reset --scope ...`
- Fixed a CLI runtime bug while landing the slice: command invocations now hydrate `Settings()` per run, so `OPENZUES_DATA_DIR` overrides like `OPENZUES_DATA_DIR` work correctly in isolated environments.
- Tightened gateway bootstrap backfill so explicit setup resets stay reset. Legacy backfill still helps older databases that predate setup footprint metadata, but it no longer silently rehydrates a profile immediately after an intentional reset.

Primary files carrying this slice:

- `src/openzues/services/setup.py`
- `src/openzues/services/onboarding.py`
- `src/openzues/services/gateway_bootstrap.py`
- `src/openzues/cli.py`
- `src/openzues/app.py`
- `src/openzues/database.py`
- `src/openzues/schemas.py`
- `src/openzues/services/access.py`
- `src/openzues/services/manager.py`
- `tests/test_app.py`

### Verification

Targeted automated verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py -q`
- Result: `62 passed`

Additional regression coverage passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_manager.py tests/test_remote_ops.py -q`
- Result: `14 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/test_ops_mesh.py -q`
- Result: `17 passed`

Static integrity checks passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`
- `node --check src/openzues/web/static/app.js`

CLI smoke verification passed against an isolated temp data dir using `OPENZUES_DATA_DIR`:

- `python -m openzues.cli setup --json`
- `python -m openzues.cli setup bootstrap ... --instance-mode create_desktop --json`
- `python -m openzues.cli setup reset --scope full --json`
- `python -m openzues.cli setup --json`

Observed CLI behavior:

- initial `setup` reported `recommended_action = bootstrap`
- bootstrap created the expected lane/project/operator/task spine and returned a mission draft
- full reset cleared the saved profile plus bootstrap-managed resources and returned the setup posture to `recommended_action = bootstrap`

Browser verification was not rerun this turn because the slice did not change the web UI.

### What remains

OpenZues still lacks the larger OpenClaw parity surfaces:

- explicit local vs remote setup modes and a sessionized wizard protocol behind the existing QuickStart shell
- broad CLI parity beyond setup/bootstrap/control-plane commands
- channels and channel/account routing
- browser-control runtime
- canvas runtime
- nodes, voice, and companion apps
- packaging and release-channel parity

### Next best slice

Do not jump to channels, nodes, or native apps next. The next smallest verified slice should stay adjacent to the setup/gateway seam that now exists.

Recommended next slice:

- add explicit local vs remote gateway bootstrap modes and wizard-session state so web QuickStart and terminal setup stop feeling like stateless form posts
- reuse the new setup footprint and gateway bootstrap services instead of inventing another onboarding state layer
- finish by carrying the saved setup posture into a stronger post-setup handoff, ideally with the next launch entrypoint bound directly to the staged lane and task

After that, the next major parity branch should be routing/session-key policy, because OpenClaw's route binding is a smaller and more central kernel than channels or companion apps.

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.

### Operator handoff

- Completed: shipped re-entrant setup posture inspection, durable setup footprint tracking, scoped setup reset behavior, and the new `openzues setup` CLI seam, while keeping gateway backfill safe for older databases.
- Verified: `62 passed` across app and database tests, `14 passed` across manager and remote-ops tests, `17 passed` across ops-mesh tests, Python compile passed, `node --check` passed, and isolated CLI smoke confirmed inspect -> bootstrap -> full reset -> inspect behavior.
- Next step: add explicit local/remote setup modes plus wizard-session state behind the current QuickStart and CLI setup surfaces, then pivot to routing/session-key parity.
- Blockers: none.

## Update: Mode-Aware Setup Wizard Session

Date: 2026-04-11

### Completed this turn

- Closed the next setup parity seam from OpenClaw's wizard flow: OpenZues setup is now explicitly mode-aware (`local` vs `remote`) instead of treating QuickStart as a one-shot local-only post.
- Added a durable setup wizard session in SQLite so web QuickStart and terminal setup no longer behave like stateless form posts. The session remembers mode, flow, and the last non-secret bootstrap draft values.
- Added remote-first bootstrap behavior to onboarding:
  - remote mode no longer assumes OpenZues will create a Desktop lane
  - remote mode can stage workspace, operator access, and recurring tasking without pinning a default lane
  - when no lane exists yet, the result now returns a staged handoff instead of faking a launch-ready draft
- Extended the saved gateway bootstrap profile so it now records setup mode and flow, and its readiness logic reflects remote-first posture instead of only lane-centric local posture.
- Exposed the wizard session end to end:
  - `GET /api/setup/wizard`
  - `PUT /api/setup/wizard`
  - `openzues setup wizard`
  - `openzues setup wizard update --mode ... --flow ...`
- Updated the dashboard QuickStart shell to surface the saved setup posture, show the new mode and flow selectors, and switch behavior correctly when remote mode is selected.

Primary files carrying this slice:

- `src/openzues/schemas.py`
- `src/openzues/database.py`
- `src/openzues/services/setup.py`
- `src/openzues/services/onboarding.py`
- `src/openzues/services/gateway_bootstrap.py`
- `src/openzues/app.py`
- `src/openzues/cli.py`
- `src/openzues/web/templates/index.html`
- `src/openzues/web/static/app.js`
- `tests/test_app.py`
- `tests/test_database.py`

### Verification

Targeted automated verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_database.py tests/test_app.py -q`
- Result: `64 passed`

Static integrity checks passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`
- `node --check src/openzues/web/static/app.js`

CLI smoke verification passed against an isolated temp data dir using `OPENZUES_DATA_DIR`:

- `python -m openzues.cli setup wizard --json`
- `python -m openzues.cli setup wizard update --mode remote --flow quickstart --json`
- `python -m openzues.cli setup --json`

Observed CLI behavior:

- `setup wizard update` normalized `remote + quickstart` into `remote + advanced`
- `setup` surfaced the saved wizard session beside the broader setup posture

Browser verification passed on live local servers:

- observer-mode page load verified at `http://127.0.0.1:8879`
- leader-mode interactive verification passed at `http://127.0.0.1:8881`
- no error overlay was detected
- body content rendered
- the new setup controls were present in the DOM:
  - `#onboarding-setup-mode`
  - `#onboarding-setup-flow`
  - `#onboarding-mode-label`
- remote-mode interaction verified:
  - switching the mode selector to `remote` changed the callout label to `Remote-first bootstrap`
  - the flow selector locked to `advanced`
  - local-only lane controls hid as expected
- browser artifact refreshed at `openzues-browser-check.png`

### What remains

OpenZues still lacks the larger OpenClaw parity surfaces:

- stronger post-bootstrap launch/handoff binding from the staged wizard session into the next mission entrypoint
- routing/session-key policy parity
- broader CLI parity beyond setup/bootstrap/control-plane commands
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

### Next best slice

Do not jump to channels or native apps next. The next smallest verified slice should keep extending the setup seam that now exists.

Recommended next slice:

- bind the saved wizard session and gateway posture into a stronger post-setup launch path so the next mission entrypoint is explicit, not just implied
- then move directly into routing/session-key policy parity, because OpenClaw's route binding kernel is smaller, more central, and more reusable than channels or companion apps
- keep reusing `setup`, `gateway_bootstrap`, `missions`, and `ops_mesh` instead of inventing a separate routing bootstrap subsystem

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.

### Operator handoff

- Completed: shipped explicit local/remote setup modes, durable wizard-session persistence, remote-first bootstrap staging, gateway profile mode/flow persistence, CLI wizard inspection/update commands, and dashboard QuickStart mode controls.
- Verified: `64 passed` across app and database tests; Python compile passed; `node --check` passed; CLI wizard smoke passed; browser verification passed on live local servers with no overlay errors, with the new setup mode/flow controls present and remote-mode behavior confirmed.
- Next step: bind the staged wizard/gateway posture into a stronger post-setup launch handoff, then pivot into routing/session-key parity.
- Blockers: none.

## Update: Persistent Setup Launch Handoff

Date: 2026-04-11

### Completed this turn

- Closed the next setup parity seam by turning the saved setup posture into a persistent launch handoff instead of leaving the next mission entrypoint implicit.
- `SetupService.inspect()` now returns a machine-readable `launch_handoff` alongside the broader setup posture, including status, recommended action, concrete next entrypoint text, the saved task/operator/project references, and a reloadable mission draft when one can be materialized.
- Promoted task-draft rebuilding into a reusable `OpsMeshService.build_task_draft(...)` path so onboarding and later setup re-entry both use the same launch-draft logic.
- Added a dedicated `GET /api/setup/launch` surface plus `openzues setup launch` so the saved handoff is addressable from API, dashboard, and CLI instead of being trapped in the one-shot bootstrap response.
- The dashboard QuickStart area now reloads the saved launch handoff after refresh and exposes a `Load saved launch draft` action when the saved posture can still materialize a draft.

Primary files carrying this slice:

- `src/openzues/services/setup.py`
- `src/openzues/services/ops_mesh.py`
- `src/openzues/services/onboarding.py`
- `src/openzues/schemas.py`
- `src/openzues/app.py`
- `src/openzues/cli.py`
- `src/openzues/web/static/app.js`
- `tests/test_app.py`

### Verification

Targeted automated verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q`
- Result: `63 passed`

Static integrity checks passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`
- `node --check src/openzues/web/static/app.js`

CLI smoke verification passed against an isolated temp data dir using `OPENZUES_DATA_DIR`:

- `python -m openzues.cli setup bootstrap --project-path . --operator-name "CLI Builder" --task-name "CLI Ship Loop" --objective-template "Inspect the repo, ship the next verified slice, and checkpoint it." --json`
- `python -m openzues.cli setup launch --json`

Observed CLI behavior:

- `setup launch` returned a staged saved handoff instead of only generic setup prose
- the saved handoff included `recommended_action: "connect_lane"` plus a concrete `mission_draft` that can be reloaded once the lane reconnects

Browser verification passed on a live local server at `http://127.0.0.1:8879` using `agent-browser.cmd`:

- page content rendered
- no framework error overlay was detected
- the saved handoff card rendered with heading `Saved launch handoff is ready`
- the dashboard exposed a `Load saved launch draft` button after refresh instead of losing the bootstrap draft
- browser artifact refreshed at `openzues-browser-check.png`

### What remains

OpenZues still lacks the larger OpenClaw parity surfaces:

- routing and session-key policy parity
- broader CLI parity beyond setup/bootstrap/control-plane commands
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

### Next best slice

Do not jump to channels or companion apps next. The next smallest verified slice should stay on the control-plane kernel that now has explicit setup re-entry.

Recommended next slice:

- carry the new saved launch handoff into routing/session-key policy so recurring tasks and follow-on launches bind to the correct lane/account posture explicitly
- reuse the existing `gateway_bootstrap`, `setup`, `ops_mesh`, and mission-draft machinery instead of adding a second routing bootstrap layer
- verify that remote-first staged setups without a default lane still produce the right binding instructions once a lane appears

### Blockers

- No credential blocker hit during this turn.
- Browser verification required a narrower command set because the dashboard continuously polls `/api/setup` and `/api/dashboard`, so idle-style waits do not settle; the product itself still rendered correctly.

### Operator handoff

- Completed: landed a persistent saved launch handoff across setup inspection, API, CLI, and dashboard re-entry, and unified setup/onboarding draft rebuilding through Ops Mesh.
- Verified: `63 passed` in targeted app tests; Python compile passed; `node --check` passed; CLI `setup launch` smoke passed; browser verification confirmed the saved handoff card and `Load saved launch draft` action on a live local server with no overlay errors.
- Next step: bind the saved launch handoff into routing/session-key policy so launch targeting becomes explicit for the next recurring cycle, especially in remote-first staged setups.
- Blockers: no product blocker; only the expected browser-harness caveat that polling pages never reach true network-idle.

## Update: Mission Live Thread Telemetry

Date: 2026-04-11

### Completed this turn

- Re-entered from stale-thread recovery, rebuilt context from the parity checkpoint trail, and verified that the previously checkpointed launch-routing and setup-handoff slices are still true in the worktree.
- Confirmed that the current uncommitted slice hardens the operator-supervision layer instead of starting a new parity branch: missions now expose live thread telemetry derived from persisted event traffic plus runtime thread state.
- Added a `Database.get_thread_event_metrics(...)` read path so OpenZues can summarize recent thread activity without replaying raw events in the UI.
- Added `MissionLiveTelemetryView` and wired `MissionService.get_view()` to surface whether a mission is actively streaming, how recently the thread moved, recent event/output counts, and whether token rollup is still pending.
- Confirmed the dashboard consumes that contract: active-loop stats now distinguish live streaming runs, mission cards show live-thread status and recent event rates, and the transcript surface compresses repeated control-chat messages instead of wasting operator attention on duplicates.

Primary files carrying this slice:

- `src/openzues/database.py`
- `src/openzues/schemas.py`
- `src/openzues/services/missions.py`
- `src/openzues/web/static/app.js`
- `src/openzues/web/static/app.css`
- `src/openzues/web/templates/index.html`
- `tests/test_database.py`
- `tests/test_missions.py`
- `tests/test_app.py`

### Verification

Focused verification passed from the workspace root:

- `.\.venv\Scripts\python.exe -m pytest tests/test_database.py tests/test_missions.py tests/test_app.py -q`
- Result: `98 passed`

Static integrity checks passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`
- `node --check src/openzues/web/static/app.js`

Observed verification outcome:

- the new thread-event metric queries returned recent activity as expected
- mission views reported `live_telemetry.streaming == True` when fresh output deltas existed on an active thread
- the broader app pack that already covers onboarding, setup handoff, and launch-route parity stayed green, so this telemetry slice did not regress the earlier control-plane work

### What remains

OpenZues still lacks the larger OpenClaw parity surfaces:

- live telemetry is visible, but radar/reflex logic does not consume it yet to distinguish healthy streaming runs from silent stalled turns
- broader CLI parity beyond setup/bootstrap/control-plane commands
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

### Next best slice

Do not branch into channels or packaging next. The highest-leverage follow-on now is to make the new telemetry actionable.

Recommended next slice:

- feed `live_telemetry` into radar, launchpad, and reflex heuristics so actively streaming missions stop looking stale while quiet in-progress turns surface earlier
- reuse the existing `missions`, `ops_mesh`, `run_pressure`, and `reflexes` seams instead of inventing a separate monitoring subsystem
- keep verification tight by extending the focused mission and ops-mesh test packs before broadening back toward channel/runtime parity

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.

### Operator handoff

- Completed: recovered the latest trusted parity checkpoint, verified the in-flight live-thread telemetry slice already present in the worktree, and turned that verified state into a durable checkpoint.
- Verified: `98 passed` across `tests/test_database.py`, `tests/test_missions.py`, and `tests/test_app.py`; Python compile passed; `node --check` passed.
- Next step: consume `live_telemetry` in radar/reflex policy so OpenZues can tell the difference between healthy streaming work and a mission that only looks active on paper.
- Blockers: none.

## Update: Telemetry-Aware Operator Policy

Date: 2026-04-11

### Completed this turn

- Re-entered from stale-thread recovery, rebuilt context from the parity ledger, and verified the current uncommitted worktree before broadening scope.
- Fixed a workspace-affinity routing regression in `LaunchRoutingService`: route selection now falls back to the saved project path and gateway default cwd when the task row does not carry a cwd, so remote-first launch drafts keep preferring the correct workspace lane.
- Closed the next smallest parity seam behind the live-thread telemetry slice: radar and reflex policy now treat `live_telemetry.streaming` as healthy active work instead of generic stale activity.
- Added an earlier operator-warning path for in-progress missions whose live thread has gone quiet, while preserving higher-priority drift and checkpoint-pressure signals.

Primary files carrying this slice:

- `src/openzues/services/launch_routing.py`
- `src/openzues/app.py`
- `src/openzues/services/reflexes.py`
- `tests/test_app.py`

### Verification

Targeted regression checks passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "remote_workspace_affinity_prefers_project_lane_and_persists_last_route or build_radar_flags_quiet_in_progress_thread_earlier or build_radar_does_not_flag_streaming_thread_as_quiet or build_reflex_deck_arms_thread_heartbeat_for_quiet_in_progress_run or build_reflex_deck_skips_thread_heartbeat_for_streaming_run"`
- Result: `5 passed`

Broader changed-surface verification also passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_database.py tests/test_missions.py tests/test_app.py tests/test_ops_mesh.py -q`
- Result: `123 passed`

Static integrity check passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What remains

OpenZues still lacks the larger OpenClaw parity surfaces:

- telemetry now informs operator policy, but it is still not folded into launchpad or interference planning
- gateway method-registry / doctor-style capability inventory
- broader CLI parity beyond setup/bootstrap/control-plane commands
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

### Next best slice

Do not jump to channels or packaging next. The highest-leverage next step remains the gateway capability / doctor seam that the routing and telemetry work now makes easier to explain and verify.

Recommended next slice:

- expose one operator-facing gateway capability summary across API, dashboard, and CLI
- include connected-lane health, app/plugin/MCP inventory, approval posture, and launch-policy warnings
- reuse existing `RuntimeManager`, diagnostics, Ops Mesh inventory, and gateway bootstrap state instead of inventing a second gateway subsystem

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.

### Operator handoff

- Completed: recovered the trusted parity seam, fixed the workspace-affinity route regression, and made live-thread telemetry actionable in radar and reflex policy.
- Verified: targeted radar/reflex/route tests passed, the broader changed-file pack passed at `123 passed`, and `compileall` passed.
- Next step: build the gateway capability / doctor contract across API, dashboard, and CLI without broadening into channel runtime work.
- Blockers: none.

## Update: Recovery Verification Landing

Date: 2026-04-11

### Completed this turn

- Re-entered from stale-thread recovery and rebuilt context from the parity ledger, current diffs, and the route-selection telemetry seam named in the relay packet before making new changes.
- Verified that the earlier blocker language about a live route-selection regression is now stale in this worktree: the `LaunchRoutingService` workspace-affinity fallback, mission live-telemetry views, and telemetry-aware radar/reflex policy are already present together.
- Added one focused hardening delta instead of reopening the seam broadly: a dedicated regression test now proves the `gateway.default_cwd` fallback branch used by workspace-affinity routing when a task carries no `cwd`, no project binding, and no pinned lane.
- Kept the rest of the turn on verification and checkpoint quality instead of widening scope into a new product slice.

Primary files re-verified this turn:

- `src/openzues/services/launch_routing.py`
- `src/openzues/services/missions.py`
- `src/openzues/services/reflexes.py`
- `src/openzues/app.py`
- `tests/test_app.py`
- `tests/test_missions.py`
- `tests/test_database.py`
- `tests/test_ops_mesh.py`

### Verification

Targeted stale-blocker recovery checks passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "remote_workspace_affinity_prefers_project_lane_and_persists_last_route or setup_endpoint_reports_reentrant_posture_after_bootstrap or setup_launch_endpoint_reports_saved_remote_handoff_gap or build_radar_flags_quiet_in_progress_thread_earlier or build_radar_does_not_flag_streaming_thread_as_quiet or build_reflex_deck_arms_thread_heartbeat_for_quiet_in_progress_run or build_reflex_deck_skips_thread_heartbeat_for_streaming_run"`
- Result: `7 passed`

Isolated route-fallback regression coverage now passes:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "launch_routing_uses_gateway_default_cwd_when_task_has_no_workspace_context or remote_workspace_affinity_prefers_project_lane_and_persists_last_route or setup_endpoint_reports_reentrant_posture_after_bootstrap or setup_launch_endpoint_reports_saved_remote_handoff_gap"`
- Result: `4 passed`

Targeted mission-telemetry recovery checks passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_missions.py -q -k "restart_safe_snapshot_prefers_green_evidence_over_stale_blocker_commentary or get_view_softens_stale_blocker_commentary or get_view_surfaces_live_thread_telemetry or get_view_surfaces_adaptive_delegation_brief or build_turn_prompt_emits_agent_stack_roles"`
- Result: `5 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_database.py tests/test_missions.py tests/test_app.py tests/test_ops_mesh.py -q`
- Result: `125 passed`

Control-plane contract pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`
- Result: `102 passed`

Static integrity checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What remains

The route-selection seam is no longer the highest-risk gap. OpenZues still lacks the larger OpenClaw parity surfaces:

- gateway method-registry / doctor-style capability inventory
- launchpad and interference planning still do not consume the newer telemetry/routing posture
- broader CLI parity beyond setup/bootstrap/control-plane commands
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

### Next best slice

Do not reopen route selection next. The highest-leverage next step is still the gateway capability / doctor seam.

Recommended next slice:

- expose one operator-facing gateway capability summary across API, dashboard, and CLI
- include connected-lane health, app/plugin/MCP inventory, approval posture, and launch-policy warnings
- reuse existing `RuntimeManager`, diagnostics, Ops Mesh inventory, and gateway bootstrap state instead of inventing a second gateway subsystem

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.

### Operator handoff

- Completed: recovered context from the stale-thread relay, proved the named route-selection blocker is no longer live in the current worktree, added a dedicated `default_cwd` route-fallback regression test, and refreshed the parity ledger with a tighter verified landing.
- Verified: `7 passed` targeted route/radar/reflex/setup checks, `4 passed` isolated route-fallback checks, `5 passed` targeted mission recovery/telemetry checks, `102 passed` in the control-plane contract pack, `125 passed` across the broader changed surface, `node --check` passed, and `compileall` passed.
- Next step: build the gateway capability / doctor contract across API, dashboard, and CLI, then decide whether launchpad/interference should consume the same capability summary before broadening further.
- Blockers: none.

## Update: Gateway Capability / Doctor Contract

Date: 2026-04-11

### Completed this turn

- Landed one shared `GatewayCapabilityView` projection so OpenZues now exposes the gateway capability / doctor summary through:
  - `GET /api/gateway/capability`
  - dashboard payload via `dashboard.gateway_capability`
  - CLI command `openzues gateway doctor`
- Tightened the contract surface instead of leaving it implicit:
  - `GET /api/gateway/capability` now declares `response_model=GatewayCapabilityView`
  - CLI regression coverage now proves `gateway doctor --json` matches the API payload, excluding only the time-varying `checked_at` field
- Kept the slice additive and anchored on existing sources instead of inventing a second gateway subsystem:
  - `RuntimeManager` for connected-lane health, pending approvals, and live app/plugin/MCP catalogs
  - `EnvironmentService.collect()` for doctor-style diagnostic evidence
  - `build_ops_mesh(...)` inventory/auth posture for tracked-vs-observed capability readiness
  - `GatewayBootstrapService.get_view()` for saved launch policy, launch-route warnings, and bootstrap posture
- The contract now includes the exact operator-facing fields requested:
  - connected-lane health
  - app/plugin/MCP inventory
  - approval posture
  - launch-policy warnings and saved launch route
- Added a dedicated dashboard summary card beside the existing bootstrap profile so operators can read one coherent gateway surface before drilling into raw diagnostics or the broader Ops Mesh inventory.

Primary files carrying this slice:

- `src/openzues/services/gateway_capability.py`
- `src/openzues/schemas.py`
- `src/openzues/app.py`
- `src/openzues/cli.py`
- `src/openzues/web/templates/index.html`
- `src/openzues/web/static/app.js`
- `tests/test_app.py`
- `tests/test_cli.py`

### Verification

Focused contract checks passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_ops_mesh.py -q -k "gateway or diagnostics or integrations_inventory"`
- Result: `6 passed`

CLI gateway-doctor parity smoke passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "gateway"`
- Result: `1 passed`

Broader changed-surface pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`
- Result: `105 passed`
- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

Additional shell-level dashboard smoke passed:

- fetched `/` through `TestClient` and confirmed the new `gateway-capability-summary` mount point exists
- fetched `/api/dashboard` and confirmed `gateway_capability` is present and populated

Browser verification note:

- No browser-automation tool was exposed in this session, so this turn used HTML/API smoke plus the changed-surface pack instead of a live visual browser run.

### What remains

OpenZues still lacks larger OpenClaw parity surfaces:

- launchpad and interference planning do not yet consume the new gateway capability summary directly
- broader CLI parity beyond setup/bootstrap/control-plane/gateway-doctor commands
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

### Next best slice

Do not reopen route selection or jump to channels next. The next best slice is to make the newly-landed gateway contract actionable in the planning surfaces that already sit on top of it.

Recommended next slice:

- feed `gateway_capability` into launchpad and interference/radar planning so operator recommendations reflect one gateway truth instead of parallel heuristics
- keep reusing the new capability projection rather than recomputing lane/inventory/approval posture again inside those surfaces
- verify that remote-first staged gateways, disconnected saved lanes, and tracked-integration gaps change operator recommendations in the expected direction

That keeps the work on the same high-leverage control-plane spine before broadening into OpenClaw’s channel/browser/node ecosystems.

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- Full visual browser verification was not possible because no browser automation tool was available in the session.

### Operator handoff

- Completed: landed the gateway capability / doctor contract across API, dashboard, and CLI, using existing runtime, diagnostics, Ops Mesh inventory, and gateway bootstrap state, and tightened the API/CLI contract so the CLI payload is proven against the API shape.
- Verified: focused gateway checks passed (`6 passed`), CLI gateway-doctor parity smoke passed (`1 passed`), the broader changed-surface pack passed (`105 passed`), `node --check` passed, `compileall` passed, and TestClient smoke confirmed the dashboard shell and payload expose the new contract.
- Next step: wire `gateway_capability` into launchpad/interference/radar so the operator planning surfaces consume the same gateway truth.
- Blockers: no product blocker; only the absence of a browser automation tool for live visual verification in this session.

## Update: Gateway Capability Planning Consumers

Date: 2026-04-11

### Recovered context

- Re-entered from stale-thread recovery and rebuilt footing from the parity ledger, current worktree, and targeted readback of the new gateway capability service instead of assuming the doctor seam still needed implementation.
- Verified that the requested gateway capability / doctor contract was already materially present in the OpenZues worktree across API, dashboard, and CLI, so this turn did not redo that slice.
- Tightened the recovery proof first: added explicit human-output CLI coverage for `openzues gateway doctor` and then continued immediately to the next smallest downstream seam named in the checkpoint.

### Completed this turn

- Fed the shared `GatewayCapabilityView` into the operator planning surfaces that previously relied on parallel heuristics:
  - `build_radar(...)` now emits a gateway-level warning/critical signal when tracked inventory gaps, pending approvals, repair-state launch routes, or zero ready lanes make the saved gateway posture unsafe to trust.
  - `build_launchpad(...)` now prefers gateway-ready lanes for fresh mission drafts instead of any merely connected lane, and it synthesizes one bounded `gateway_repair` draft when the gateway posture needs repair before broader launches.
  - `build_interference(...)` now surfaces a `gateway_posture` vector when operators are likely to fork work around degraded launch posture, tracked gaps, or repair-state route warnings.
- Kept the seam additive and downstream-only:
  - no second gateway subsystem was added
  - route resolution itself was not redesigned
  - the new planning behavior only consumes the existing `GatewayCapabilityView`
- Tightened the gateway-doctor regression bar:
  - added a dedicated human-readable CLI regression so section summaries in `gateway doctor` cannot silently drift
  - added direct planning-surface tests for radar, launchpad, and interference behavior under degraded gateway posture

Primary files carrying this turn’s delta:

- `src/openzues/app.py`
- `src/openzues/schemas.py`
- `src/openzues/services/interference.py`
- `tests/test_app.py`
- `tests/test_cli.py`

### Verification

Focused gateway-planning pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_cli.py -q -k "gateway or build_launchpad_prefers_gateway_ready_lanes_and_adds_gateway_repair_opportunity or build_interference_surfaces_gateway_posture_vector or build_radar_surfaces_gateway_capability_warning_signal"`
- Result: `9 passed`

Target file packs passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q`
- Result: `75 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q`
- Result: `2 passed`

Broader changed-surface pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`
- Result: `108 passed`

Static integrity checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

Observed harness caveat:

- a single monolithic pytest invocation that added `tests/test_cli.py` on top of the broader app/database/manager/ops-mesh pack showed one order-sensitive failure in `test_remote_workspace_affinity_prefers_project_lane_and_persists_last_route`
- the isolated route-affinity test passed immediately afterward, and the standard broader pack without CLI plus the full CLI pack both passed
- that is not enough evidence to reopen the route-selection seam on this turn; it currently looks like a test-order or async-subprocess cleanup interaction around CLI coverage, not a stable product regression

### What remains

OpenZues still lacks larger OpenClaw parity surfaces:

- control-chat and attention-queue guidance still do not explicitly cite the shared gateway capability view
- broader CLI parity beyond setup/bootstrap/control-plane/gateway-doctor commands
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

### Next best slice

Do not reopen route selection or jump to channels next. The next smallest useful seam is to finish the operator-guidance convergence around the gateway truth that is now shared by doctor, radar, launchpad, and interference.

Recommended next slice:

- feed `gateway_capability` into control chat and attention-queue planning so operator recommendations, nudges, and manual command suggestions cite the same gateway truth
- keep consuming the existing `GatewayCapabilityView` instead of recomputing lane health, approval posture, or tracked inventory readiness inside chat/planning helpers
- verify that remote-first staged gateways, disconnected saved lanes, and tracked-integration gaps change operator guidance consistently across dashboard cards and control-chat actions

That preserves the high-leverage control-plane spine before broadening into OpenClaw’s channel, browser, node, and companion-app ecosystems.

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- Residual harness caveat only: the combined pytest invocation that mixes the broader app pack and CLI tests showed one order-sensitive route-affinity failure, but isolated route coverage and the standard packs passed.

### Operator handoff

- Completed: recovered the stale-thread footing, proved the gateway doctor seam was already landed, tightened its CLI regression bar, and wired the shared `gateway_capability` contract into radar, launchpad, and interference without reopening route resolution.
- Verified: focused gateway-planning checks passed (`9 passed`), full `tests/test_app.py` passed (`75 passed`), full `tests/test_cli.py` passed (`2 passed`), the broader changed-surface app/database/manager/ops-mesh pack passed (`108 passed`), `node --check` passed, and `compileall` passed.
- Next step: consume `gateway_capability` inside control chat and attention-queue planning so the remaining operator-guidance surfaces stop drifting from the gateway truth.
- Blockers: no product blocker; only the noted order-sensitive pytest harness caveat when broad app coverage and CLI tests run as one combined command.

## Update: Gateway Capability Chat And Queue Convergence

Date: 2026-04-11

### Recovered context

- Re-entered from stale-thread recovery and rebuilt footing from the parity ledger, current worktree, and targeted readback of the gateway doctor seam before editing anything new.
- Verified that the original requested gateway capability / doctor contract was already landed across API, dashboard, and CLI, and that radar, launchpad, and interference were already consuming the shared `GatewayCapabilityView`.
- Continued immediately to the next smallest missing seam named in the checkpoint instead of redoing the doctor slice: control chat and the autonomous attention queue still drifted from the shared gateway truth.

### Completed this turn

- Fed the existing `dashboard.gateway_capability` contract into the remaining operator-guidance surfaces inside `control_chat.py`:
  - `plan_control_chat(...)` now appends gateway posture to status replies when launch posture needs repair.
  - `plan_control_chat(...)` now prefers the existing `gateway_repair` launchpad opportunity before broad recoveries, hardeners, or fresh launches when Gateway Doctor says repair-first.
  - `plan_attention_queue(...)` now gates autonomous follow-through on the same repair-first gateway posture and will launch the bounded `gateway_repair` draft, or hold and explain the block if no repair draft exists yet.
  - `build_view(...)` and `build_attention_queue_view(...)` now switch their operator-facing copy to the shared Gateway Doctor posture instead of generic momentum language when the gateway is degraded.
- Kept the slice additive and downstream-only:
  - no new gateway subsystem was introduced
  - no routing logic was reopened
  - no API, schema, or frontend contract changes were required
- Preserved the current dirty-worktree edits in `control_chat.py` by keeping the new gateway logic in the planner/view sections and leaving the unrelated mission-payload `toolsets` propagation intact.

Primary files carrying this turn's delta:

- `src/openzues/services/control_chat.py`
- `tests/test_app.py`

### Verification

Focused planner pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "control_chat or attention_queue or gateway_repair or gateway_capability"`
- Result: `27 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q`
- Result: `96 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`
- Result: `37 passed`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What remains

OpenZues still lacks larger OpenClaw parity surfaces:

- broader CLI parity beyond setup/bootstrap/control-plane/gateway-doctor commands
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

Within the gateway/control-plane spine, the main remaining gap is not another doctor view; it is broader operator command-surface parity on top of the now-shared gateway truth.

### Next best slice

Do not reopen route selection or re-implement the gateway doctor seam next. The gateway truth is now coherent across API, dashboard, CLI, radar, launchpad, interference, control chat, and the attention queue.

Recommended next slice:

- extend broader operator CLI parity by reusing the existing planning helpers for one bounded command-driven action seam
- keep consuming the shared `GatewayCapabilityView` and `gateway_repair` opportunity instead of adding a second CLI policy layer
- verify that command-driven operator actions follow the same repair-first posture already enforced in dashboard chat and queue planning

That keeps the work on the same control-plane spine before broadening into OpenClaw's channel, browser, node, and companion-app ecosystems.

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- The previously noted order-sensitive pytest caveat still stands only for monolithic app-plus-CLI invocations; this turn stayed on the standard separated packs.

### Operator handoff

- Completed: recovered the trusted gateway parity footing, proved the doctor seam and planning consumers were already landed, and finished the remaining chat/queue convergence so those surfaces now cite and obey the same gateway truth.
- Verified: focused planner coverage passed (`27 passed`), full `tests/test_app.py` passed (`96 passed`), the broader database/manager/ops-mesh pack passed (`37 passed`), and `compileall` passed.
- Next step: keep the momentum on operator CLI parity by reusing the existing gateway-aware planning helpers for one bounded command-action seam instead of reopening gateway internals.
- Blockers: no product blocker; only the standing monolithic pytest order-sensitivity caveat already captured in the ledger.

### Re-entry checkpoint

- Recovered context: the gateway doctor contract and its radar/launchpad/interference consumers were already verified before this turn; the live missing seam was gateway-aware control-chat and attention-queue guidance.
- Verified state: those chat/queue consumers now share the same repair-first gateway posture and targeted plus broader verification are green.
- Next step: add the next bounded operator CLI action seam on top of the same planning helpers and gateway truth.
- Blockers: none beyond the known combined app-plus-CLI pytest order sensitivity.

## Update: Gateway-Aware CLI Continue Action

Date: 2026-04-11

### Recovered context

- Re-entered from the latest parity checkpoint instead of broadening scope blindly.
- Verified that the shared gateway truth was already coherent across API, dashboard, CLI doctor, radar, launchpad, interference, control chat, and the attention queue.
- Continued to the next bounded operator CLI seam named in the prior checkpoint: one command-driven action path that reuses the same gateway-aware planning helpers instead of inventing a second CLI policy layer.

### Completed this turn

- Added a top-level `openzues continue` command that reuses the existing gateway-aware control-chat planner for the operator's next step:
  - `openzues continue --plan` previews the next bounded move without executing it
  - `openzues continue` executes the same planner result through the existing `ControlChatService`
- Kept the CLI slice thin and additive:
  - reused `build_brief(...)`, `build_launchpad(...)`, `build_doctrines(...)`, and `GatewayCapabilityService.get_view()` to construct the planning context
  - reused `plan_control_chat("continue", ...)` for preview mode
  - reused `ControlChatService.submit("continue", ...)` for execute mode
  - did not add a second launch-policy or gateway decision layer in the CLI
- Added CLI coverage for:
  - human-readable continue output formatting
  - a real staged-workspace `continue --plan --json` path that proves the command respects the gateway-aware repair-first posture on live data

Primary files carrying this turn's delta:

- `src/openzues/cli.py`
- `tests/test_cli.py`

### Verification

Focused CLI pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "continue or gateway"`
- Result: `6 passed`

Full CLI pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q`
- Result: `11 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q`
- Result: `108 passed`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`
- `node --check src/openzues/web/static/app.js`

### What remains

OpenZues still lacks larger OpenClaw parity surfaces:

- broader CLI parity beyond setup/bootstrap/control-plane/gateway-doctor and the new gateway-aware `continue` action
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

Within the operator-control spine, the remaining leverage is now broader command coverage on top of the same already-shared planning and gateway posture, not another gateway contract rewrite.

### Next best slice

Do not reopen route selection or rebuild the gateway doctor surface next. The next smallest useful CLI seam is another bounded operator command on top of the same planning contract.

Recommended next slice:

- add one explicit queue/control command that reuses the existing attention-queue planning helpers and the shared gateway posture
- keep preview vs execute semantics explicit so operators can inspect the move before firing it
- verify that the CLI action follows the same repair-first posture already enforced in dashboard chat and queue planning

That keeps momentum on CLI parity without drifting into a parallel policy system or jumping early into channel/browser/node ecosystems.

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- The standing monolithic pytest order-sensitivity caveat still applies only when broad app and CLI packs are combined into one command; this turn kept them separated.

### Operator handoff

- Completed: added a gateway-aware `openzues continue` CLI action that previews or executes the same repair-first planner already used in dashboard chat, without introducing a second CLI policy layer.
- Verified: focused CLI checks passed (`6 passed`), the full CLI pack passed (`11 passed`), the broader app pack passed (`108 passed`), `compileall` passed, and `node --check` passed.
- Next step: land one bounded attention-queue/control CLI command on top of the same planning helpers.
- Blockers: none beyond the known combined app-plus-CLI pytest ordering caveat.

### Re-entry checkpoint

- Recovered context: gateway truth was already unified across doctor, planning surfaces, chat, and queue before this turn; the live missing seam was a command-driven operator action on top of that shared planner.
- Verified state: `openzues continue` now reuses the same gateway-aware continue planner in preview and execute modes, and both focused plus broader verification are green.
- Next step: add the next bounded queue/control CLI action while keeping preview/execute semantics explicit and reusing the shared gateway posture.
- Blockers: none beyond the already-documented monolithic pytest ordering caveat.

## Update: Gateway-Aware CLI Status Summary

Date: 2026-04-12

### Recovered context

- Re-entered from stale-thread recovery and rebuilt footing from the parity ledger plus the live worktree before making changes.
- Verified that the original requested gateway capability / doctor contract is already present across API, dashboard, and CLI, and that the subsequent `continue` and `queue` operator CLI seams are also already landed in the repo.
- Continued to the next smallest missing parity seam instead of redoing the doctor surface: the CLI already had a rich `_emit_status(...)` renderer, but there was still no top-level `openzues status` command exposing the shared gateway-aware operator summary.

### Completed this turn

- Added a top-level `openzues status` command that reuses the existing operator planning surfaces instead of inventing another CLI policy layer.
- The new status command now emits one operator-facing summary built from the same shared sources already used elsewhere:
  - `build_brief(...)` for the headline and next actions
  - `GatewayCapabilityService.get_view()` through the existing dashboard builder for gateway posture
  - `build_radar(...)` and `build_launchpad(...)` for signal and opportunity context
  - `plan_control_chat("status", ...)` for the bounded control-chat status summary
  - `plan_attention_queue(...)` for the next autonomous queue move preview
- Kept the slice additive and durable:
  - no route-selection logic was reopened
  - no second gateway subsystem was introduced
  - the CLI reads the same gateway capability truth already used by API and dashboard surfaces
- Tightened the CLI regression bar around this recovered truth:
  - added status JSON coverage that proves the nested `gateway_capability` payload still matches `/api/gateway/capability`
  - added human-output status coverage so terminal rendering of gateway, radar, launchpad, and queue summaries cannot silently drift

Primary files carrying this turn's delta:

- `src/openzues/cli.py`
- `tests/test_cli.py`

### Verification

Focused CLI status/gateway/queue pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "status or gateway or queue"`
- Result: `13 passed`

Full CLI pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q`
- Result: `21 passed`

Broader changed-surface pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`
- Result: `153 passed`

Static integrity checks passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`
- `node --check src/openzues/web/static/app.js`

### What remains

OpenZues still lacks larger OpenClaw parity surfaces:

- broader CLI parity beyond gateway doctor, status, continue, recover, harden, and queue
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

Within the operator-control spine, the remaining leverage is now not another shared gateway projection. The main open gap is more explicit operator actuation on top of the already-shared planner and gateway posture.

### Next best slice

Do not reopen route selection or rebuild the gateway doctor/status surfaces next. The next smallest useful seam is one explicit targeted operator CLI action on top of the same shared planner.

Recommended next slice:

- add one id-addressable CLI action that can fire a specific launchpad opportunity or queue recommendation without recomputing policy in a second place
- keep preview vs execute semantics explicit so operators can inspect the chosen move before firing it
- keep consuming the shared `GatewayCapabilityView`, launchpad, radar, and attention-queue planners instead of inventing another route/approval heuristic

That preserves the high-leverage control-plane spine before broadening into OpenClaw's channel, browser, node, and companion-app ecosystems.

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- The standing monolithic pytest order-sensitivity caveat remains only for combined app-plus-CLI mega-invocations; the standard separated packs used here are green.

### Operator handoff

- Completed: verified that the gateway doctor contract and the queue CLI seam were already present, then landed the missing top-level `status` command on the same shared gateway-aware planner and dashboard truth.
- Verified: focused CLI status/gateway/queue checks passed (`13 passed`), the full CLI pack passed (`21 passed`), the broader app/database/manager/ops-mesh pack passed (`153 passed`), `compileall` passed, and `node --check` passed.
- Next step: add one targeted operator CLI action by explicit opportunity or queue target while continuing to consume the same gateway-aware planning surfaces.
- Blockers: none beyond the already-documented combined app-plus-CLI pytest ordering caveat.

### Re-entry checkpoint

- Recovered context: the gateway capability / doctor contract plus the `continue` and `queue` CLI seams were already landed in the repo before this turn; the live missing seam was status-level CLI observability on top of that shared planner.
- Verified state: `openzues status` now exposes the same gateway-aware operator truth that powers API, dashboard, chat, and queue planning, and the focused plus broader verification packs are green.
- Next step: add a targeted id-addressable operator CLI action on top of the same launchpad/queue/gateway contract.
- Blockers: none beyond the known combined app-plus-CLI pytest order sensitivity already captured in the ledger.

## Update: Launchpad Opportunity CLI Action

Date: 2026-04-12

### Recovered context

- Re-entered from the latest verified parity checkpoint instead of reopening the already-landed gateway doctor seam.
- Verified that the shared gateway capability truth is already coherent across API, dashboard, CLI doctor, status, continue, recover, harden, queue, radar, launchpad, interference, control chat, and the attention queue.
- Continued to the next smallest missing seam named in the checkpoint: one explicit id-addressable operator CLI action on top of the existing launchpad and gateway-aware planner surfaces.

### Completed this turn

- Added a top-level `openzues launch <opportunity-id>` command for explicit launchpad actuation:
  - `openzues launch <id> --plan` previews the selected launchpad move without executing it
  - `openzues launch <id>` executes that exact launchpad draft through the existing mission creation path
- Kept the slice thin and additive:
  - reused `_build_operator_dashboard(...)` to resolve the current launchpad snapshot
  - reused the existing `MissionDraftView -> MissionCreate` conversion instead of adding another operator policy layer
  - reused the existing human/JSON action envelope already used by the other CLI operator commands
  - did not reopen route selection, gateway posture computation, or attention-queue policy
- Tightened operator discoverability in the human CLI status surface:
  - `openzues status` now prints launchpad opportunity ids beside titles when they exist, so the new command is targetable from terminal output without forcing JSON-only discovery
- Kept the queue-targeted follow-through explicitly out of this slice because the current queue executor is still whole-queue, not signal-addressable. That remains the next bounded seam if the operator CLI spine continues.

Primary files carrying this turn's delta:

- `src/openzues/cli.py`
- `tests/test_cli.py`

### Verification

Focused CLI contract pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "launch or status or gateway or queue"`
- Result: `17 passed`

Full CLI pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q`
- Result: `26 passed`

Broader changed-surface pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`
- Result: `154 passed`

Static integrity checks passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`
- `node --check src/openzues/web/static/app.js`

### What remains

OpenZues still lacks larger OpenClaw parity surfaces:

- broader CLI parity beyond gateway doctor, status, continue, recover, harden, queue, and the new explicit launchpad-action command
- explicit queue-signal targeting by id on top of the same attention-queue planner
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime
- nodes, voice, companion apps, and packaging matrix

Within the operator-control spine, the remaining leverage is no longer another gateway summary projection. The next bounded seam is explicit queue-targeted actuation without recreating queue policy inside the CLI.

### Next best slice

Do not reopen route selection or rebuild the gateway doctor/status surfaces next. The next smallest useful seam is a signal-addressable queue action that still reuses the shared gateway-aware planner.

Recommended next slice:

- add one explicit CLI action for a selected queue signal id, but only after introducing a tiny selector in the queue planner/executor path instead of copying queue policy into the CLI
- keep preview vs execute semantics explicit so operators can inspect the chosen queue move before firing it
- keep consuming the existing `GatewayCapabilityView`, `plan_attention_queue(...)`, radar signals, and launchpad opportunities instead of inventing another route or approval heuristic

That keeps the work on the same high-leverage control-plane spine before broadening into OpenClaw's channel, browser, node, and companion-app ecosystems.

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- The standing monolithic pytest order-sensitivity caveat still applies only to combined app-plus-CLI mega-invocations; the standard separated packs used here are green.

### Operator handoff

- Completed: verified the gateway doctor/status/control-plane footing, landed `openzues launch <opportunity-id>` as the next explicit operator CLI action, and made human status output surface launchpad ids for terminal discoverability.
- Verified: focused CLI launch/status/gateway/queue coverage passed (`17 passed`), the full CLI pack passed (`26 passed`), the broader app/database/manager/ops-mesh pack passed (`154 passed`), `compileall` passed, and `node --check` passed.
- Next step: add explicit queue-signal targeting by id while keeping the selector in the shared queue planner/executor path rather than rebuilding policy in the CLI.
- Blockers: none beyond the already-documented combined app-plus-CLI pytest ordering caveat.

### Re-entry checkpoint

- Recovered context: the gateway capability / doctor contract and the broader gateway-aware operator CLI/status surfaces were already landed before this turn; the live missing seam was explicit id-addressable launchpad actuation.
- Verified state: `openzues launch <opportunity-id>` now previews or executes the selected launchpad draft through the existing mission creation spine, and human `status` output now exposes opportunity ids when available.
- Next step: add an explicit queue-signal target path by introducing a small selector into the shared queue planner/executor lane.
- Blockers: none beyond the known combined app-plus-CLI pytest order sensitivity already captured in the ledger.

## Update: Live Watch CLI Recovery Slice

### Recovered context

- Re-entered from stale-thread recovery by reading the parity ledger, the current OpenZues worktree, and the OpenClaw source layout before making changes.
- Verified that the stale relay claiming `instance_mode` was still thin and wizard-session state was missing was no longer true in the repo: setup posture, wizard-session persistence, launch routing, gateway doctor, and the gateway-aware operator CLI spine were already landed.
- Checked the dirty worktree before broadening scope and found the next active seam already in progress: a live `openzues watch` command plus repo-local watcher launcher scripts in the CLI layer.
- Confirmed against the OpenClaw source tree that this is not a missing backend contract from upstream. It is a thin OpenZues operator affordance on top of existing dashboard/setup-launch surfaces, so the right move was to finish and verify it as a bounded CLI parity slice instead of inventing another watcher subsystem.

### Completed this turn

- Finished and verified the in-progress live-watch operator seam in the existing worktree:
  - `openzues watch` now composes `/api/dashboard` plus `/api/setup/launch` into one watch snapshot.
  - the command can resolve a target mission from the saved launch handoff, an explicit mission id, or a task label
  - `--launch` can reconnect or resume the saved target before watching when the current posture allows it
  - `--follow`, `--cycles`, `--until-terminal`, JSON output, and human-readable output are wired through one CLI path
  - `scripts/openzues-watch.cmd` provides a repo-local Windows launcher for the new watch command
- Kept the slice additive and bounded:
  - no new API route was introduced
  - no gateway/routing/schema contract was changed
  - the watch command stays a client composition layer over existing control-plane truth instead of a second supervision backend
- Stabilized three unrelated but newly surfaced calendar-fragile MemPalace gateway-capability tests in `tests/test_app.py` by switching them from fixed April 11 timestamps to relative UTC timestamps. That was necessary so the required broader regression pack would reflect real product behavior on April 12, 2026 instead of failing on stale fixture dates.

Primary files carrying this turn's delta:

- `src/openzues/cli.py`
- `tests/test_cli.py`
- `README.md`
- `scripts/openzues-watch.cmd`
- `tests/test_app.py`

### Verification

Focused watch/CLI coverage passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "watch or status or gateway or queue or launch or continue"`
- Result: `21 passed`

Full CLI pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q`
- Result: `31 passed`

Broader app pack passed after stabilizing the date-fragile MemPalace fixtures:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q`
- Result: `115 passed`

Broader changed-surface control-plane pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`
- Result: `39 passed`

Static integrity checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

Live command smoke passed against a disposable local server on `http://127.0.0.1:8893`:

- `.\.venv\Scripts\python.exe -m openzues.cli serve --host 127.0.0.1 --port 8893`
- `.\.venv\Scripts\python.exe -m openzues.cli watch --url http://127.0.0.1:8893 --json`
- Result: the command returned a real HTTP snapshot that resolved the saved `OpenClaw Total Parity Program` task, included the staged launch handoff, surfaced gateway posture, and attached the live watched mission payload.

### What remains

OpenZues still lacks the larger OpenClaw parity surfaces:

- broader operator CLI parity beyond the current gateway-aware status, continue, launch, queue, recover, harden, and watch actions
- explicit queue-signal targeting by id on top of the existing attention-queue planner
- channel runtime and channel/account routing
- browser-control runtime parity
- canvas runtime parity
- nodes, voice, companion apps, and packaging matrix

Within the operator-control spine, the next leverage is no longer another gateway summary or another passive watch view. The next bounded seam is explicit queue-targeted actuation without recreating queue policy inside the CLI.

### Next best slice

Do not reopen setup posture, launch routing, gateway doctor, or the new watch command next. The next smallest verified slice should stay on the same operator CLI spine.

Recommended next slice:

- add one explicit CLI action for a selected attention-queue signal id
- introduce the selector in the shared queue planner/executor path rather than copying queue policy into the CLI
- keep preview vs execute semantics explicit, the same way `continue`, `launch`, and `watch` keep operator intent inspectable before side effects
- keep consuming the existing `GatewayCapabilityView`, `plan_attention_queue(...)`, radar signals, and launchpad opportunities instead of inventing a second CLI policy layer

That preserves the current high-leverage control-plane parity path before broadening into OpenClaw's channel, browser, canvas, node, voice, and companion-app ecosystems.

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- An untracked `scripts/openzues-watch-browser.cmd` file is present in the worktree and appears to target a not-yet-landed `watch --browser` flag. This turn did not touch or verify that file because it sits outside the verified `watch` contract currently in `src/openzues/cli.py`.

### Operator handoff

- Completed: recovered the parity footing, confirmed the setup/gateway/routing spine was already landed, finished the in-progress `openzues watch` CLI slice, and stabilized three calendar-fragile MemPalace app tests so the broader regression pack is trustworthy again.
- Verified: focused watch/operator CLI coverage passed (`21 passed`), the full CLI pack passed (`31 passed`), the full app pack passed (`115 passed`), the broader database/manager/ops-mesh pack passed (`39 passed`), `node --check` passed, `compileall` passed, and a live smoke against `http://127.0.0.1:8893` returned a real watch snapshot over HTTP.
- Next step: add explicit queue-signal targeting by id while keeping the selector inside the shared attention-queue planner/executor path.
- Blockers: none for the verified `watch` seam; only the unrelated untracked `scripts/openzues-watch-browser.cmd` remains outside the proven contract.

### Re-entry checkpoint

- Recovered context: the stale relay about missing wizard/session posture was obsolete; the actual live missing seam in the worktree was a bounded `openzues watch` CLI affordance on top of already-landed dashboard and setup-launch contracts.
- Verified state: `openzues watch` is now proven by focused tests, full CLI/app/control-plane packs, static checks, and one live local HTTP smoke. The broader regression bar is green again after replacing fixed-date MemPalace fixtures with relative UTC timestamps.
- Next step: land one queue-signal-targeted CLI action on the same shared planner/gateway spine instead of reopening backend routing or jumping to channels.
- Blockers: no product blocker. Keep the untracked `scripts/openzues-watch-browser.cmd` out of scope unless the next cycle explicitly decides to add a browser-mode watch contract.

## Update: Queue Signal Targeting Slice

Date: 2026-04-12

### Recovered context

- Re-entered from the verified `watch` checkpoint instead of reopening the already-landed gateway doctor, status, launchpad, or watch seams.
- Confirmed the live missing operator-control gap was exactly what the last checkpoint named: the attention queue could only act on the next autonomous signal, not an explicitly selected radar signal id.
- Kept the work on the shared planner spine. The CLI was already thin; the missing selector belonged in the existing attention-queue planner and executor, not in another CLI-only policy branch.

### Completed this turn

- Added explicit signal-addressable queue targeting on the shared control-chat path:
  - `plan_attention_queue(...)` now accepts an optional `target_signal_id`
  - `ControlChatService.tick_attention_queue(...)` threads the same selector through execution
  - unknown signal ids now fail clearly with the current available ids instead of silently falling back to the default whole-queue decision
- Extended the CLI without widening scope:
  - `openzues queue --signal-id <id> --plan` previews the selected radar signal
  - `openzues queue --signal-id <id>` executes the selected queue move through the existing queue executor and action log
  - when a selected signal is real but not currently actionable, the CLI returns a safe targeted no-op instead of pretending it fired the next generic queue move
- Tightened terminal discoverability for the new path:
  - human `openzues status` output now prints radar signal ids beside the visible top signals, so operators can target the new queue selector without dropping to raw JSON first

Primary files carrying this slice:

- `src/openzues/services/control_chat.py`
- `src/openzues/cli.py`
- `tests/test_cli.py`
- `tests/test_app.py`

### Verification

Focused queue packs passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "queue"`
- Result: `8 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "attention_queue"`
- Result: `11 passed`

Broader CLI regression coverage passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q`
- Result: `39 passed`

Static integrity check passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What remains

OpenZues still lacks larger OpenClaw parity surfaces:

- broader operator CLI parity beyond the current gateway-aware status, continue, launch, queue, recover, harden, and watch actions
- deeper gateway/plugin bootstrap and method-registry seams
- channel runtime and channel/account routing
- browser-control runtime parity beyond the current operator watch affordances
- canvas runtime parity
- nodes, voice, companion apps, and packaging matrix

Within the operator-control spine, the biggest remaining leverage is no longer basic actuation by launchpad or queue id. The next useful seam is to close the remaining gateway bootstrap/method-registry gap before broadening into channels, browser runtime, or companion apps.

### Next best slice

Do not reopen the queue selector, gateway doctor projection, or watch surface next. The next smallest verified slice should step outward from operator actuation into the gateway substrate.

Recommended next slice:

- inventory the highest-leverage OpenClaw gateway bootstrap and method-registry seams against the current OpenZues gateway bootstrap profile
- add one bounded gateway/bootstrap capability improvement that reuses the existing `GatewayBootstrapService`, `GatewayCapabilityService`, and launch-routing state rather than creating a second gateway stack
- keep the slice operator-verifiable across API, dashboard, and CLI the same way the current control-plane work has been landed

That keeps parity work anchored on OpenClaw's control-plane leverage instead of diffusing into broad channel or native-app scope too early.

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- The wider source-of-truth gaps remain product-scope gaps, not access blockers.

### Operator handoff

- Completed: landed explicit `openzues queue --signal-id <id>` targeting on the shared attention-queue planner/executor, added clear unknown-id handling, and surfaced radar signal ids in human `status` output for terminal discoverability.
- Verified: focused queue CLI coverage passed (`8 passed`), focused attention-queue app coverage passed (`11 passed`), the full CLI pack passed (`39 passed`), and `compileall` passed.
- Next step: move off the now-solid operator CLI spine and take one bounded gateway bootstrap / method-registry parity seam on the same shared control-plane substrate.
- Blockers: none beyond the standing product-scope depth.

### Re-entry checkpoint

- Recovered context: the live missing seam after `watch` was explicit queue-signal targeting by id, not another gateway summary or another passive observer surface.
- Verified state: the shared attention-queue path now supports targeted preview and execution by radar signal id, unknown ids fail clearly without falling back to whole-queue behavior, and human `status` output exposes the visible signal ids needed to drive the command.
- Next step: inventory and land one bounded gateway bootstrap / method-registry improvement against the OpenClaw source seams while keeping API, dashboard, and CLI truth unified.
- Blockers: none.

## Update: Operator Control Reliability Slice

Date: 2026-04-12

### Recovered context

- Re-entered from the queue-targeting checkpoint and the stale-thread relay packet without reopening already-verified onboarding, watch, direct MemPalace proof, or queue-selector work.
- Confirmed the active worktree seam was narrower than the broad parity inventory: gateway capability freshness under slow MCP refresh, mission tool-proof truthfulness, and cache-safe operator surfaces around mutating API failures.
- Reused the existing source-of-truth inventory in this checkpoint and the MemPalace checkpoint instead of rebuilding the full OpenClaw surface map again.

### Completed this turn

- Hardened gateway capability freshness on the live MemPalace seam:
  - `GatewayCapabilityService` now times out slow `mcpServerStatus/list` refreshes and falls back to cached runtime MCP status instead of stalling the operator surface
  - the ready path still requires the full MemPalace tool contract, but transient refresh stalls now degrade into cached truth instead of false warning churn
- Tightened parity tool-proof accounting in mission prompts:
  - mission event scans now look back far enough to survive longer traces
  - command output is now attached to the originating command id so inspection-only reads such as `Get-Content` no longer count as memory-tool proof
  - parity prompts now call out current proof gaps explicitly instead of only listing the declared tool contract
- Closed the remaining operator-surface reliability gap in the dashboard/API cache path:
  - operator dashboard and gateway capability caches are now invalidated in a `finally` path for mutating `/api/` requests
  - failed mutating requests can no longer leave stale operator snapshots resident until the cache TTL expires

Primary files carrying this slice:

- `src/openzues/services/gateway_capability.py`
- `src/openzues/services/missions.py`
- `src/openzues/app.py`
- `tests/test_app.py`
- `tests/test_missions.py`

### Verification

Focused reliability regressions passed from the project virtualenv:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "mutating_api_failure_invalidates_operator_surface_caches or gateway_capability_uses_cached_mcp_status_when_live_refresh_times_out"`
- Result: `2 passed`

Re-verified the active operator-control slice:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "gateway_capability or attention_queue"`
- Result: `21 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "queue or status"`
- Result: `10 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/test_missions.py -q -k "tool_evidence or parity_tool"`
- Result: `2 passed`

### What remains

OpenZues still lacks the broader OpenClaw parity surfaces already inventoried earlier in this checkpoint:

- deeper gateway bootstrap and method-registry parity
- broader CLI parity beyond the current control-plane actions
- channel runtime and routing
- browser-control runtime parity
- canvas, nodes, voice, packaging, and companion apps

Within the current operator-control spine, the freshness/proof/cache seam is now verified. The next leverage point is no longer more MemPalace doctor plumbing or more queue targeting.

### Next best slice

Do not reopen this reliability seam next unless a new regression appears. The next smallest verified slice should move one layer down into the gateway substrate:

- compare OpenClaw's gateway bootstrap and method-registry seams against `GatewayBootstrapService` and the current OpenZues gateway capability/bootstrap contracts
- land one bounded improvement that reuses the existing gateway bootstrap state, launch routing, API, dashboard, and CLI surfaces
- keep the result operator-verifiable the same way this reliability slice stayed grounded in shared control-plane truth

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- The remaining gaps are product-scope gaps, not access blockers.

### Re-entry checkpoint

- Recovered context: the stale-thread relay was pointing at calendar-fragile MemPalace freshness, but the live worktree had already moved onto a tighter operator-control seam around cached gateway truth, targeted actuation, and parity proof accounting.
- Verified state: slow MCP refresh now falls back to cached runtime status, inspection-only command output no longer overclaims tool proof, mutating API failures invalidate operator caches safely, and the focused app/CLI/mission packs are green in the repo virtualenv.
- Next step: inventory and land one bounded gateway bootstrap / method-registry parity improvement on top of the now-stable operator-control substrate.
- Blockers: none.

## Update: Targeted Queue Execution Contract

Date: 2026-04-12

### Recovered context

- Re-entered on the still-open operator-control seam rather than reopening onboarding or queue-selector work that was already verified.
- Confirmed the remaining production-quality gap inside the current slice: `openzues queue --signal-id <id>` could plan against one radar signal but still execute an unrelated safe approval first.
- Kept scope bounded to the shared control-plane contract seam instead of drifting into a broader gateway/bootstrap redesign in the same turn.

### Completed this turn

- Closed the explicit queue-targeting contract gap in `ControlChatService`:
  - targeted attention-queue execution now honors `target_signal_id` before any unrelated safe-approval sweep
  - explicit operator targeting can no longer be silently preempted by a pending safe approval on the lane
- Added a regression that proves the selected-signal path stays bounded even when a safe approval is also available:
  - the test fakes mission creation so it exercises the control-plane contract without dragging live runtime startup into shutdown
  - the assertion proves no approval resolution happened and the selected failed-signal recovery path was the action recorded
- Re-ran the broader operator contract packs after the fix instead of trusting the narrow regression alone.

Primary files carrying this slice:

- `src/openzues/services/control_chat.py`
- `tests/test_app.py`

### Verification

Focused app/dashboard pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "gateway_capability or attention_queue"`
- Result: `22 passed`

Focused mission-proof pack remained green:

- `.\.venv\Scripts\python.exe -m pytest tests/test_missions.py -q -k "tool_evidence or parity_tool_evidence_contract or commentary_orbiting_thread or stalled_executing_thread"`
- Result: `4 passed`

Focused contract guard pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`
- Result: `160 passed`

Static integrity checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

Previously rerun CLI proof for the same seam stayed green in this recovery lane:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "queue or status"`
- Result: `10 passed`

### What remains

The current operator-control seam is now internally consistent, but OpenZues still lacks the larger OpenClaw parity surfaces already inventoried:

- deeper gateway bootstrap and method-registry parity
- broader CLI parity outside the current control-plane operator actions
- channel runtime and channel/account routing
- browser-control runtime, canvas, nodes, voice, packaging, and companion apps

### Next best slice

Do not reopen queue targeting, cache invalidation, or the current mission-proof seam next unless a new regression appears.

The next smallest verified slice should move one layer down into OpenClaw's gateway substrate:

- compare OpenClaw gateway bootstrap and method-registry seams against the current `GatewayBootstrapService`, `GatewayCapabilityService`, and launch-routing contracts
- land one bounded gateway/bootstrap improvement that shows up coherently across API, dashboard, and CLI
- keep the slice additive and operator-verifiable, not a broad stub for channels or native companions

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- The remaining gaps are product-scope gaps, not access blockers.

### Operator handoff

- Completed: closed the last production-quality gap in explicit queue targeting so `queue --signal-id` now stays bounded to the selected radar signal even when a safe approval is pending elsewhere.
- Verified: `22 passed` on the broader app/dashboard queue-capability pack, `4 passed` on the focused mission-proof pack, `160 passed` on the control-plane contract pack, `10 passed` on the focused CLI queue/status pack, plus `node --check` and `compileall`.
- Tool evidence:
  - debugging: used `git diff`, `rg`, and `Get-Content` to inspect the live seam and failing fixture path
  - delegation: used architect/planner sidecars to map the seam and tighten the verification bar
  - browser: not used in this slice because no UI contract changed
  - vision: not used in this slice because no visual surface changed
  - memory: not used directly; recovery context came from the persisted checkpoint doc and relay packet rather than Recall/MemPalace runtime calls
  - session_search: not used directly; the thread did not query Recall/session-search APIs
- Next step: take one bounded OpenClaw gateway bootstrap / method-registry parity seam on top of the now-stable operator-control substrate.
- Blockers: none.

## Update: Mission Runtime Continuity Hardening

Date: 2026-04-12

### Recovered context

- Re-entered on the same operator-control seam after the queue-targeting contract was already checkpointed earlier today.
- Confirmed the dirty worktree had moved beyond queue targeting into a broader continuity pass across mission recovery, runtime refresh hardening, gateway capability refresh behavior, and operator cache consistency.
- Kept scope anchored to the current control-plane spine instead of broadening into channels, nodes, or companion apps.

### Completed this turn

- Finished and verified the in-flight operator continuity hardening slice already present in the worktree.
- Mission control now treats late `turn/start` timeouts as recoverable when the runtime proves the turn actually started, which keeps missions from being stranded in false failed states during launch jitter.
- Missions caught in commentary orbit or stalled inspection reads can now interrupt the stale runtime thread, rebind onto a fresh thread, and resume with a bounded recovery prompt instead of continuing abandoned narration.
- Tool-family proofing is stricter: inspection-only output no longer overclaims `memory` tool use, so parity checkpoints can distinguish real Recall/MemPalace exercise from simple file reads.
- Gateway capability refresh now falls back to cached MCP lane status when a live refresh stalls, which keeps the operator gateway surface readable under runtime slowness.
- Shared operator/dashboard caches now invalidate after mutating API requests, and the CLI attention queue can target an explicit signal id without silent fallback while still surfacing the selected signal id in output.

Primary files carrying this slice:

- `src/openzues/services/missions.py`
- `src/openzues/services/manager.py`
- `src/openzues/services/control_chat.py`
- `src/openzues/services/gateway_capability.py`
- `src/openzues/app.py`
- `src/openzues/cli.py`
- `tests/test_missions.py`
- `tests/test_manager.py`
- `tests/test_app.py`
- `tests/test_cli.py`

### Verification

Focused contract and continuity verification passed from the repo virtualenv:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`
- Result: `162 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py tests/test_missions.py -q`
- Result: `87 passed`
- `node --check src/openzues/web/static/app.js`
- Result: passed
- `.\.venv\Scripts\python.exe -m compileall src/openzues`
- Result: passed

### What remains

The parity inventory is unchanged at the macro level. OpenZues still does not have OpenClaw parity for:

- routed channel/account conversation identity
- channel runtime breadth
- browser-control runtime parity
- canvas runtime parity
- nodes and companion apps
- voice wake and talk-mode surfaces
- packaging and release-channel breadth

This slice hardens continuity on the current control lane. It does not yet reach OpenClaw's bound channel/session routing seam.

### Next best slice

Do not reopen this continuity seam next unless a new regression appears. The next smallest verified parity slice should target routed session identity on top of the existing gateway and mission spine:

- map OpenClaw's `binding-routing` and `session-conversation` seam onto OpenZues lane, operator, project, and mission identity
- add stable session-key policy and conversation reuse before broadening into channel adapters
- keep the work additive by reusing the current mission, launch routing, gateway bootstrap, and recall primitives

### Operator handoff

Completed: landed the operator continuity hardening slice already in flight: recoverable late turn starts, commentary-orbit and stalled-execution thread rebinds, stricter tool-proof accounting, cached gateway capability refresh fallback, cache-safe operator surface invalidation, and bounded CLI queue targeting by signal id.

Verified: `162 passed` across app/database/manager/ops-mesh, `87 passed` across CLI/missions, plus `node --check src/openzues/web/static/app.js` and `.\.venv\Scripts\python.exe -m compileall src/openzues` both passed.

Tool evidence:
- debugging: used `git diff`, `rg`, repo file inspection, targeted `pytest`, `node --check`, and `compileall` to inspect and verify the seam
- delegation: used architect and planner sidecar agents to map the live seam and tighten the parity claim/checkpoint gate
- browser: not used in this slice because no UI flow or DOM contract changed
- vision: not used in this slice because no screenshot or image proof was needed
- memory: not used in this slice; prior checkpoint state was recovered from repository files rather than a live Recall or MemPalace query
- session_search: not used in this slice because no session-search tool surface was available in this runtime

Next step: implement routed session identity and conversation reuse on top of the current gateway/mission spine before broadening into channel adapters or companion runtimes.

Blockers: none.

## Recovery checkpoint 2026-04-12 21:03 America/Chicago

### Completed

- Re-verified the shipped outbound-delivery seam after stalled-execution recovery without reopening the parity inventory.
- Confirmed the prior outbox implementation is still present in the current workspace, so no repair was needed in this turn.

### Verified

- `src/openzues/database.py` still defines durable `outbound_deliveries` storage plus create/update/list helpers carrying `session_key`, `conversation_target`, route scope, payload, summary, and attempt state.
- `src/openzues/services/ops_mesh.py` still persists a pending outbound delivery before webhook dispatch and marks it `delivered` or `failed` afterward.
- `src/openzues/cli.py` still exposes saved outbound deliveries through `routes_deliveries_command`.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -k "outbound_delivery or notification_route" -q` -> `5 passed`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -k "routes_deliveries or routes_list_json_surfaces_saved_notification_routes" -q` -> `2 passed`
- `node --check src/openzues/web/static/app.js` passed

### Next smallest step

- Implement recovery-safe replay for saved outbound deliveries: load eligible `pending` or `failed` rows and rerun them through the existing webhook delivery path with explicit retry-state transitions.

### Blockers

- Recall was unavailable in this runtime (`python -m openzues.cli recall --json` raised `ModuleNotFoundError`), so recovery depended on the named ledger anchor plus narrow seam verification.

## Recovery checkpoint 2026-04-12 21:42 America/Chicago

### Recovered context

- The previously identified outbound replay gap is still the live next seam; nothing in the current target workspace closes it yet.
- This turn stayed narrow on proof instead of starting the replay implementation branch.

### What is already true

- OpenZues persists outbound delivery rows with attempt metadata in `src/openzues/database.py`.
- OpenZues delivery execution in `src/openzues/services/ops_mesh.py` still creates each row as `pending` and immediately flips it to `delivered` or `failed` within the same synchronous webhook attempt.
- OpenClaw already carries a dedicated recovery path in `openclaw-main/src/infra/outbound/delivery-queue-recovery.ts` with explicit retry/backoff and `ackDelivery` / `failDelivery` handling.

### Concrete claim verified

OpenZues still lacks a recovery-safe outbound replay entrypoint; outbound deliveries are durable records, but not yet a reloadable retry queue.

Verification proof:

- `src/openzues/services/ops_mesh.py:3357-3457` shows `_deliver_notifications()` creating an outbound row with `delivery_state="pending"` and then updating that same row directly to `delivered` or `failed` after one webhook attempt.
- `src/openzues/database.py:1280-1412` shows only list/get/create/update helpers for outbound deliveries; there is no targeted queue reload, claim, ack, fail, or replay helper.
- `rg -n "replay|recover.*outbound|outbound.*recover|replay_outbound|ack_outbound|fail_outbound|retry_outbound" src/openzues tests` returned only parity-ledger mission text in `tests/test_missions.py`, with no OpenZues implementation hit for an outbound recovery path.
- `openclaw-main/src/infra/outbound/delivery-queue-recovery.ts:1-220` confirms the source product already has the missing class of behavior: recovery drain, retry backoff, permanent-error classification, and `ackDelivery` / `failDelivery` transitions.

### Operator handoff

Completed: landed the recovery turn by re-verifying the active outbound parity gap instead of reopening broad source inspection.

Verified: the next missing seam is still replay-safe outbound recovery; the target product does not yet expose an entrypoint that reloads and retries saved pending or failed deliveries.

Next smallest step: add the smallest OpenZues recovery seam on top of the existing outbox contract by introducing replay-eligible delivery queries/state transitions plus one operator trigger that reuses the current webhook sender.

Blockers: none.

## Update: Routed Outbox Ledger + Recovery Sweep Guardrails

Date: 2026-04-12

### Recovered context

- Re-entered from the 2026-04-12 recovery checkpoint instead of reopening the source inventory or widening the parity ledger search again.
- Verified that the current uncheckpointed worktree already held the next real additive seam: the first durable routed outbox ledger on top of `conversation_target` and `session_key`.
- Verified that the same worktree also carried a bounded recovery hardening slice in `missions.py` so stale-thread rebounds stop drifting into broad parity-ledger and session-artifact sweeps.

### Completed this turn

- Landed the first durable routed outbox ledger in OpenZues:
  - added `outbound_deliveries` persistence in SQLite
  - added `OutboundDeliveryView` plus `route_scope` schema coverage
  - notification-route tests and live routed deliveries now persist `session_key`, `conversation_target`, route match, delivery state, attempt counts, and error state
  - the dashboard Ops Mesh surface now shows recent routed delivery attempts instead of hiding that state inside route rows only
- Hardened stale-thread parity recovery policy:
  - repeated post-rebind `Select-String` ledger sweeps now trip the same executing-stall guard as repeated full ledger reads
  - broad parity-ledger keyword clouds and `.openzues` / `.codex` / `logs` / `sessions` context sweeps now register as recovery drift
  - parity prompt guidance now explicitly warns against raw checkpoint-kind probes, keyword-cloud ledger searches, and session-dump breadcrumb sweeps

Primary files carrying this slice:

- `src/openzues/database.py`
- `src/openzues/schemas.py`
- `src/openzues/services/missions.py`
- `src/openzues/services/ops_mesh.py`
- `src/openzues/app.py`
- `src/openzues/web/static/app.js`
- `src/openzues/web/templates/index.html`
- `tests/test_missions.py`
- `tests/test_ops_mesh.py`

### Verification

Focused seam verification passed from the workspace root:

- `.\.venv\Scripts\python.exe -m pytest tests/test_missions.py -q -k "parity_tool_evidence_contract or repeated_parity_select_string_after_recovery or parity_ledger_keyword_sweep_after_recovery or parity_context_sweep_after_recovery"`
  - Result: `4 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/test_ops_mesh.py -q -k "outbound_delivery or outbound_delivery_for_matching_event or notification_route_test_api_updates_route_state"`
  - Result: `3 passed`
- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

Observed verification outcome:

- the new recovery-stall detectors fired only on the intended post-rebind drift patterns
- routed test deliveries and matching live delivery paths now persist durable outbox records with session and conversation scope attached
- the dashboard static bundle still parses cleanly after adding the outbox rail

### What remains

OpenZues still does not have OpenClaw parity for:

- dedicated operator API and CLI inspection/repair surfaces for the new routed outbox ledger
- actual channel runtime breadth and channel/account delivery adapters
- browser-control runtime parity
- canvas runtime parity
- nodes, voice, companion apps, and packaging breadth

### Next best slice

Do not reopen the recovery-guardrail seam next unless a regression appears.

The next smallest verified parity slice should make the new routed outbox ledger directly operable:

- add a dedicated outbox inspection surface across API and CLI with per-session and per-route filtering
- surface failed deliveries and retry-safe repair guidance without inventing a second dispatch subsystem
- reuse `outbound_deliveries`, `notification_routes`, `conversation_target`, and gateway capability warnings as the single operator contract

### Re-entry packet

- Recovered context: resumed from the 2026-04-12 routed outbox recovery checkpoint and confirmed the worktree already contained the targeted outbox plus recovery-hardening seams.
- Verified state: `4 passed` for the new parity-recovery guardrails, `3 passed` for the new routed outbox ledger coverage, `node --check` passed, and `compileall` passed.
- Next step: expose the routed outbox ledger as a first-class operator API/CLI surface before broadening into live channel adapter work.
- Blockers: none.

## Recovery checkpoint 2026-04-12 19:26 America/Chicago

### Seam completed

Mission-control recovery now cuts two orbit patterns inside [`src/openzues/services/missions.py`](/abs/path/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/missions.py):

- long-running inspection commands that keep streaming output without landing work
- repeated full `docs/openclaw-parity-checkpoint-2026-04-10.md` reads after a recent recovery rebind already named the seam

This landed via open-command window detection keyed by command-execution item ids, explicit repeated-ledger detection, tighter recovery copy, and summary text that distinguishes quiet stalls from inspection orbit.

### Verified

- `.\.venv\Scripts\python.exe -m pytest tests/test_missions.py -q -k "long_running_inspection or output_only_window or repeated_parity_ledger_read or stalled_executing_thread"` -> `4 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/test_missions.py -q` -> `66 passed`

### What remains

OpenClaw product parity is still missing the operator-facing authoring surfaces for the already-landed routed `conversation_target` contract, plus the broader runtime/channel breadth already listed above. This recovery slice only prevents the mission loop from wasting turns on ledger rereads and inspection orbit.

### Next best slice

Resume the previously named product seam instead of extending mission-control heuristics again:

- expose `conversation_target` through onboarding/bootstrap and task-authoring flows
- keep API, dashboard, and CLI constructors/payload builders aligned in one contract turn
- rerun the contract pack plus the affected app/dashboard surface before checkpointing

### Operator handoff

Completed: hardened recovery so a fresh parity thread no longer spends the next turn rereading the full ledger or holding a read-only inspection command open while commentary continues.

Verified: focused and full `tests/test_missions.py` both passed after the change.

Next step: implement the operator-surface `conversation_target` authoring seam that the prior checkpoint already identified.

Blockers: none.

## Update: Conversation-Target Delivery Route Matching

Date: 2026-04-12

### Recovered context

- Re-entered from the adapter-neutral `conversation_target` checkpoint and OpenZues Recall instead of reopening the broader OpenClaw inventory.
- Verified the existing adapter-facing seam was already real but narrower than the next parity target: notification routes could consume saved `conversation_target` state for exact-match webhook delivery and test pings.
- Locked the next bounded missing seam from the same routing lane: fallback delivery matching so saved routed identity can resolve at peer, account, or channel scope instead of only exact peer equality.

### Completed this turn

- Extended Ops Mesh notification delivery to match routed conversation identity by scope:
  - peer-scoped routes still match exact peer targets
  - account-scoped routes now match any peer within the same channel/account
  - channel-scoped routes now match any routed conversation on that channel
- Added wildcard-aware matching for route tokens so `*` behaves as an explicit fallback marker where operators choose to use it.
- Webhook delivery payloads now surface the resolved routing tier as `routeMatch` alongside the existing `conversationTarget` and `routeConversationTarget` payload fields, which makes the selected fallback visible during verification and downstream handling.
- Kept the slice additive and control-plane only:
  - no channel adapter runtime was introduced
  - no native companion, browser, canvas, or packaging scope was opened
  - the work reuses the existing `conversation_target`, mission event, notification route, vault, and webhook-delivery contracts

Primary files carrying this slice:

- `src/openzues/services/ops_mesh.py`
- `tests/test_ops_mesh.py`

### Verification

Focused delivery routing coverage passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_ops_mesh.py -q -k "test_notification_route_delivers_webhook_ping or test_ops_mesh_service_filters_notification_routes_by_conversation_target or test_notification_route_test_api_updates_route_state"`
- Result: `3 passed`

Broader operator entrypoint coverage passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "test_routes_test_command_executes_delivery_ping"`
- Result: `1 passed`

Integrity check passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What remains

OpenZues still does not have OpenClaw parity for:

- a durable outbound send/outbox contract on top of the now-routable conversation identity
- broader channel runtime and account-binding breadth beyond webhook-style operator delivery
- browser-control runtime parity
- canvas runtime parity
- nodes, voice, companion apps, and packaging breadth

This turn closed the first fallback delivery seam on top of the routed identity spine. It still does not provide a first-class outbound message/send contract or live channel adapters.

### Next best slice

Do not reopen notification-route fallback matching next unless a regression appears.

The next smallest verified parity slice should add a durable routed outbound delivery contract before broadening into real channel runtimes:

- add an operator-visible send/outbox record that persists `conversation_target`, `session_key`, message summary, resolved route scope, and delivery attempt state
- reuse the existing `notification_routes`, mission events, `conversation_target`, and webhook delivery machinery instead of inventing a second dispatch path
- keep the slice additive across API, CLI, and dashboard without pretending full Slack/Discord/Telegram runtime breadth already exists

### Operator handoff

Completed: landed fallback conversation-target matching for notification delivery so saved routed identity now resolves at peer, account, or channel scope, and webhook payloads expose the selected tier through `routeMatch`.

Verified: `3 passed` on the focused notification-route delivery pack, `1 passed` on the CLI delivery test command, and `.\.venv\Scripts\python.exe -m compileall src/openzues` passed.

Tool evidence:
- debugging: used targeted `Get-Content`, `rg`, `pytest`, `compileall`, and `git diff` to lock and verify the seam
- memory: used OpenZues Recall with `openzues recall "conversation_target routed identity adapter contract" --limit 5 --json` before reading broader repo context
- session_search: the same Recall query was used as the session-search path for recovery
- delegation: not used in this slice because the seam and write set were already narrow enough to implement directly
- browser: not used in this slice because no DOM-only contract changed
- vision: not used in this slice because no screenshot or image proof was required

Next step: add the first durable outbound send/outbox contract on top of the now-routable `conversation_target` spine before opening real channel adapters.

Blockers: none.

### Re-entry checkpoint

- Recovered context: the active parity lane had already landed routed identity authoring, and the smallest unfinished follow-on seam was fallback delivery matching for notification routes rather than more route-shape work.
- Verified state: notification routes now consume saved conversation identity at peer, account, or channel scope, and delivered webhook payloads expose `conversationTarget`, `routeConversationTarget`, and `routeMatch`.
- Next step: add a durable send/outbox contract that reuses the same routed identity and delivery path before broadening into channel-specific runtimes.
- Blockers: none.

## Recovery Update: Conversation Target Authoring Verified

Date: 2026-04-12

### Recovered context

- Re-entered from the parity ledger and Recall instead of rebuilding the full OpenClaw inventory.
- Locked the next unfinished seam named in the last checkpoint: operator authoring of the existing adapter-neutral `conversation_target` contract through setup/bootstrap and task-authoring surfaces.

### Completed this turn

- Verified that this seam was already landed in the live OpenZues worktree and only the checkpoint was stale.
- Confirmed the operator-facing forms already expose `conversation_target` fields in the onboarding bootstrap form, task blueprint form, mission composer, and notification route form.
- Confirmed the existing bootstrap/task authoring payload builders already serialize and hydrate `conversation_target`, and the backend already threads it through onboarding, launch routing, mission drafts, stored missions, and dashboard/setup readouts.
- No production code changes were needed for this recovery landing; the durable step was to prove the seam and advance the checkpoint.

Primary files inspected for proof:

- `src/openzues/web/templates/index.html`
- `src/openzues/web/static/app.js`
- `src/openzues/services/onboarding.py`
- `src/openzues/schemas.py`
- `tests/test_app.py`

### Verification

Focused authoring proof passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "onboarding_bootstrap_creates_first_run_bundle_and_launch_draft or task_creation_roundtrips_conversation_target_into_dashboard_draft"`
- Result: `2 passed`

Broader routed-identity regression proof passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_missions.py tests/test_cli.py -q -k "conversation_target or session_key or conversation_reuse or reuse_thread or followup_payload_matching"`
- Result: `10 passed`

Integrity checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What remains

OpenZues still does not have OpenClaw parity for:

- actual channel runtime breadth and adapter delivery on top of the now-authorable routed identity
- browser-control runtime parity
- canvas runtime parity
- nodes, voice, companion apps, and packaging breadth

This recovery turn proved the authoring seam is done. The next leverage point is no longer setup/task form exposure; it is the first bounded adapter execution layer that can consume the saved channel/account route identity.

### Next best slice

Do not reopen `conversation_target` authoring next unless a regression appears.

The next smallest verified parity slice should bind the saved routed identity into one adapter-facing execution seam without pretending full channel breadth already exists:

- reuse the existing `conversation_target`, `session_key`, launch routing, and follow-up contracts
- choose one adapter-neutral delivery or dispatch contract first
- keep the proof additive across API, CLI, and dashboard, not a broad channel runtime clone

### Operator handoff

Completed: verified that `conversation_target` is already authorable through onboarding/bootstrap and task-authoring surfaces in the current worktree, so no new code was required and the stale checkpoint is now corrected.

Verified: `2 passed` on the focused bootstrap/task-authoring proof, `10 passed` on the broader app/database/missions/cli routed-identity pack, plus `node --check src/openzues/web/static/app.js` and `.\.venv\Scripts\python.exe -m compileall src/openzues`.

Tool evidence:
- debugging: used targeted `rg`, `Get-Content`, `pytest`, `node --check`, and `compileall` to inspect and verify the seam
- delegation: used one architect sidecar to confirm that the seam was already landed and to tighten the minimum verification bar before checkpointing
- memory: used OpenZues Recall with `.\.venv\Scripts\python.exe -m openzues.cli recall "openclaw parity onboarding bootstrap" --limit 5 --json` to recover the saved parity context
- session_search: the same Recall query was used as the session-search path before restating the seam

Next step: bind the saved routed identity into the first adapter-facing execution contract so OpenZues can act on the stored channel/account route without broadening into full channel runtime breadth.

Blockers: none.

## Update: Gateway Method Registry Surface

Date: 2026-04-12

### Recovered context

- Re-entered on the gateway/bootstrap parity lane after the continuity and queue slices were already checkpointed.
- Confirmed the active gap was narrower than the broader parity backlog: OpenZues had lane-published MCP server summaries, but callable tool inventory was still not surfaced as a first-class operator contract.
- Kept the scope inside the gateway method-registry seam and reused the existing MCP server status summaries instead of introducing a separate registry source.

### Completed this turn

- Added a new gateway method catalog contract on top of the existing gateway capability inventory.
- The contract now projects unique callable tool names, server counts, and connected-lane counts from lane-published MCP server status catalogs.
- Gateway capability summaries now append the callable method inventory summary when tools are visible, so the API payload, CLI doctor output, and dashboard view all share the same truth.

Primary files carrying this slice:

- `src/openzues/schemas.py`
- `src/openzues/services/gateway_capability.py`
- `src/openzues/cli.py`
- `src/openzues/web/static/app.js`
- `tests/test_app.py`
- `tests/test_cli.py`

### Verification

Focused contract coverage was added for:

- the gateway capability API/dashboard payload including the callable method catalog
- the CLI doctor emitter printing the callable method catalog summary and tool names

### What remains

OpenZues still lacks the broader OpenClaw parity surfaces already inventoried earlier in this checkpoint:

- routed channel/account conversation identity
- channel runtime breadth
- browser-control runtime parity
- canvas runtime parity
- nodes and companion apps
- voice wake and talk-mode surfaces
- packaging and release-channel breadth

This slice closes the operator-facing gateway method-registry inventory gap, but it does not yet reach the routed session identity seam.

### Next best slice

Do not reopen the gateway method catalog slice next unless a regression appears. The next smallest verified parity slice should continue onto routed session identity and conversation reuse on top of the current gateway and mission spine.

### Blockers

- None.

## Update: Routed Session Identity and Gateway Method Catalog

Date: 2026-04-12

### Recovered context

- Re-entered from stale-thread recovery by trusting the existing parity ledger instead of rebuilding the full OpenClaw inventory.
- Verified that the next unfinished seam named in the latest durable checkpoint was routed session identity and conversation reuse on top of the existing gateway and mission spine.
- Confirmed in the dirty worktree that this seam was partially implemented but not yet checkpointed: session-key lookup, launch-route reuse projection, session-aware follow-up matching, and CLI surfacing were all present.
- After that seam was verified, took one more bounded gateway substrate slice: operator-visible callable method inventory from the already-published MCP server catalogs.

### Completed this turn

- Closed the routed session identity and conversation reuse seam:
  - `LaunchRoutingService` now projects `conversation_reuse` beside the stable routed `session_key`
  - mission creation reuses the latest compatible saved thread by `session_key` before starting a new thread
  - follow-up matching now treats `session_key` as the canonical routed identity when thread ids change
  - setup handoff and CLI output now surface the reuse summary so operators can see when the next launch will continue an existing logical conversation
- Closed one bounded gateway method-registry seam on top of that routing work:
  - gateway capability inventory now includes a callable method catalog derived from lane-published MCP server `tools` catalogs
  - the same callable catalog summary is visible through the gateway capability API payload, CLI doctor/status output, and dashboard gateway doctor card
  - the slice reuses the existing runtime-published MCP status summaries instead of introducing a second registry source

Primary files carrying the two verified slices:

- `src/openzues/database.py`
- `src/openzues/schemas.py`
- `src/openzues/services/followups.py`
- `src/openzues/services/gateway_capability.py`
- `src/openzues/services/launch_routing.py`
- `src/openzues/services/missions.py`
- `src/openzues/cli.py`
- `src/openzues/web/static/app.js`
- `tests/test_app.py`
- `tests/test_cli.py`
- `tests/test_database.py`
- `tests/test_missions.py`

### Verification

Focused routed-session seam verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_missions.py tests/test_cli.py tests/test_database.py -q -k "session_key or conversation_reuse or reuse_thread or followup_payload_matching"`
- Result: `5 passed`

Focused gateway method-catalog verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_missions.py tests/test_cli.py tests/test_database.py -q -k "session_key or conversation_reuse or reuse_thread or followup_payload_matching or gateway_capability_endpoint_summarizes_connected_lane_health_inventory_and_warnings or gateway_capability_uses_cached_mcp_status_when_live_refresh_times_out or emit_gateway_capability_surfaces_callable_method_inventory or gateway_doctor_json_includes_gateway_capability_summary"`
- Result: `9 passed`

Static integrity checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What remains

OpenZues still does not have OpenClaw parity for:

- routed channel/account conversation identity beyond the current control-plane session spine
- channel runtime breadth
- browser-control runtime parity
- canvas runtime parity
- nodes and companion apps
- voice wake and talk-mode surfaces
- packaging and release-channel breadth

The current turn closed the control-plane session identity seam and exposed a bounded callable gateway catalog. It did not yet bind that routed identity into a channel/account adapter contract.

### Next best slice

Do not reopen routed session reuse or the gateway method catalog next unless a regression appears.

The next smallest verified parity slice should bind the now-stable routed session identity into the first channel/account routing seam:

- map OpenClaw's adapter-neutral routing/session contract from `openclaw-main/src/routing/resolve-route.ts` and related session-key helpers onto one OpenZues channel/account conversation identity shape
- keep the slice additive by reusing the current `session_key`, `launch_routing`, mission follow-up matching, and gateway capability surfaces
- choose one bounded adapter-neutral contract first; do not broaden into full channel runtime breadth, native companions, or packaging in the same cycle

### Blockers

- No credential blocker hit during this turn.
- No approval blocker hit during this turn.
- The remaining gaps are product-scope gaps, not access blockers.

### Re-entry checkpoint

- Recovered context: the next unfinished seam after continuity hardening was routed session identity and conversation reuse, not another global source inventory pass.
- Verified state: routed launches now expose a stable `session_key` plus `conversation_reuse`, mission creation reuses the latest compatible thread by that key, follow-up matching survives thread-id churn, and gateway doctor now reports callable MCP tool inventory across API, CLI, and dashboard.
- Next step: bind the same routed identity into the first channel/account routing contract so OpenZues stops at one logical conversation shape before broadening into channel-runtime breadth.
- Blockers: none.

## Update: Adapter-Neutral Conversation Target Contract

Date: 2026-04-12

### Recovered context

- Re-entered from the routed-session checkpoint instead of reopening the broader OpenClaw inventory.
- Confirmed the next unfinished seam named in the checkpoint was the first adapter-neutral channel/account routing contract on top of the existing `session_key` spine.
- Queried OpenZues Recall before editing so the active lane reused the saved routing/session continuity context instead of restating it from scratch.

### Completed this turn

- Added a durable adapter-neutral `conversation_target` contract to the routing spine:
  - task blueprints can now carry `channel`, `account_id`, `peer_kind`, and `peer_id`
  - launch routing normalizes that target, includes it in the routed session identity, and surfaces a stable summary beside the existing `session_key`
  - mission drafts inherit the same target, and stored missions now persist it durably in SQLite
- Tightened conversation safety instead of only displaying the new field:
  - thread reuse from `session_key` is now blocked when the incoming conversation target does not match the saved one
  - follow-up matching now prefers the adapter-neutral conversation target before falling back to `session_key` or `thread_id`
- Kept the slice additive:
  - no channel runtime was introduced
  - no native companion or packaging scope was opened
  - the work reuses the existing launch-routing, mission, follow-up, CLI, and dashboard contracts

### What remains

OpenZues still does not have OpenClaw parity for:

- first-class operator input surfaces for this new channel/account route identity during setup/bootstrap or task authoring
- actual channel runtime breadth and adapter delivery
- browser-control runtime parity
- canvas runtime parity
- nodes, voice, companion apps, and packaging breadth

The routed identity contract now exists and is verified. The remaining leverage is to make it authorable through the existing operator surfaces before broadening into live channel runtime breadth.

### Next best slice

Do not reopen the routed session-key or follow-up safety seam next unless a regression appears.

The next smallest verified slice should expose this new `conversation_target` contract through the existing operator setup/task surfaces:

- allow onboarding/bootstrap or task-authoring flows to save a first channel/account/peer target explicitly
- reuse the now-landed `conversation_target` plus routed `session_key` contract instead of inventing another route schema
- keep the proof additive across API, dashboard, and CLI without pretending full channel delivery already exists

### Operator handoff

Completed: landed the first adapter-neutral channel/account routing contract on top of the routed `session_key` spine by adding durable `conversation_target` fields to task blueprints, launch routing, mission drafts, stored missions, and follow-up identity checks.

Verified: `168 passed` across `tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py`; `98 passed` across `tests/test_missions.py tests/test_cli.py`; `node --check src/openzues/web/static/app.js` passed; `.\.venv\Scripts\python.exe -m compileall src/openzues` passed.

Tool evidence:
- debugging: used targeted `Get-Content`, source-file inspection, `pytest`, `node --check`, and `compileall` to map and verify the seam
- delegation: used an architect sidecar to confirm the minimum file set, contract shape, and verification bar before locking the implementation
- browser: not used in this slice because no live browser-only proof was required
- vision: not used in this slice because no screenshot or image proof was required
- memory: used OpenZues Recall with `openzues recall "session_key conversation reuse routing" --limit 5 --json` to recover the saved routing checkpoint context
- session_search: the same Recall query was used to search prior checkpoint/session history before restating the seam

Next step: expose the new `conversation_target` contract through setup/bootstrap and task-authoring surfaces so operators can save the first channel/account route directly without dropping to raw payload editing.

Blockers: none.

## Recovery checkpoint 2026-04-12 19:17 America/Chicago

### Recovered context

- Recovery resumed from the ledger anchor instead of rereading the full parity file again.
- The latest verified product seam in this ledger was already clear: do not extend mission-control recovery heuristics again; move forward on the routed outbound delivery contract.
- `runlogs` was not available in this workspace, so the recovery proof used the named ledger anchor plus a tight source/target file inspection only.

### Concrete claim verified

OpenClaw already has a durable outbound queue surface, while OpenZues still does not have any send/outbox contract on top of the routed `conversation_target` spine.

Source-of-truth proof:

- [`C:/Users/skull/OneDrive/Documents/openclaw-main/src/infra/outbound/delivery-queue-storage.ts`](C:/Users/skull/OneDrive/Documents/openclaw-main/src/infra/outbound/delivery-queue-storage.ts) defines persistent queue entry storage and lifecycle helpers including `enqueueDelivery`, `ackDelivery`, `failDelivery`, plus recovery-safe queue loading.
- A targeted source search also showed the queue is wired into `deliver.ts`, `delivery-queue-recovery.ts`, and dedicated storage/recovery tests under the same outbound area.

Target proof:

- [`src/openzues/database.py`](/abs/path/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/database.py:273) still exposes routed mission/session storage such as `session_key` and `conversation_target_json`, but no outbound queue or outbox table.
- [`src/openzues/schemas.py`](/abs/path/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/schemas.py:1401) still stops at routed mission identity surfaces and does not yet define an operator-visible send/outbox record.
- Targeted absence check: `rg -n --glob "*.py" --glob "*.js" "outbox|delivery-queue|enqueueDelivery|ackDelivery|failDelivery" src/openzues` -> `NO_TARGET_OUTBOX_HITS`

### What remains

OpenZues still needs the first durable outbound send/outbox contract that persists routed delivery intent before any broader channel runtime parity claim is credible.

### Next best slice

Implement the smallest additive outbound contract turn across the existing control plane:

- add a durable send/outbox record in OpenZues that stores `conversation_target`, `session_key`, message summary, resolved route scope, and delivery attempt state
- reuse the existing `notification_routes`, mission events, and webhook delivery machinery instead of inventing a second dispatch path
- wire the record through API, CLI, and dashboard surfaces in the same contract seam
- verify with the contract pack and at least one broader app/dashboard surface before checkpointing

### Operator handoff

Completed: recovery landed on the next real parity seam and verified the checkpoint's core claim that OpenClaw already has a durable outbound queue surface while OpenZues still has none.

Verified: targeted source/target inspections and an explicit absence check on `src/openzues` confirmed the gap without reopening the full ledger.

Tool evidence:

- debugging: used targeted `rg` and line-scoped `Get-Content` only
- memory: not available in this runtime; recovery used the persisted ledger anchor instead
- session_search: not available as a live tool surface in this runtime; recovery used the named anchor plus narrow source/target inspection
- delegation: not used because this turn only proved the next seam and landed a restart-safe checkpoint packet

Next step: implement the first durable routed send/outbox contract in OpenZues, starting at schema/database level and then wiring the same record through API, CLI, and dashboard constructors in one contract turn.

Blockers: none.

## Recovery checkpoint 2026-04-12 20:51 America/Chicago

### Recovered context

- The previous recovery checkpoint is now stale relative to the workspace: the routed send/outbox contract it described as missing is already present in OpenZues.
- This turn avoided another broad parity inventory pass and instead verified the currently shipped outbound-delivery seam directly in the target product.

### Concrete claim verified

OpenZues already has the first durable routed outbox contract across storage, service wiring, CLI, and dashboard surfaces.

Target proof:

- `src/openzues/database.py` already defines `outbound_deliveries`, indexes, plus create/list/get/update helpers for durable outbound records.
- `src/openzues/schemas.py` already defines `OutboundDeliveryView`, and `src/openzues/services/ops_mesh.py` already records pending deliveries, then marks them `delivered` or `failed` after webhook attempts.
- `src/openzues/cli.py`, `src/openzues/app.py`, and `src/openzues/web/static/app.js` already surface saved outbound deliveries through operator-facing CLI and dashboard flows.

Verification proof:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -k "outbound_delivery or notification_route" -q` -> `5 passed`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -k "routes_deliveries or routes_list_json_surfaces_saved_notification_routes" -q` -> `2 passed`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -k "test_mission_creation_appears_on_dashboard or test_task_creation_roundtrips_conversation_target_into_dashboard_draft" -q` -> `2 passed`
- `node --check src/openzues/web/static/app.js` passed
- `.\\.venv\\Scripts\\python.exe -m compileall src/openzues` passed

### What remains

The remaining outbound parity gap is recovery-safe delivery replay, not outbox creation.

- OpenClaw persists queued outbound entries with replay-oriented lifecycle helpers such as `enqueueDelivery`, `ackDelivery`, `failDelivery`, and queue reload/recovery behavior.
- OpenZues currently records outbound attempts durably, but delivery handling is still synchronous per event/test route and stops at recording `pending`, `delivered`, or `failed`; there is no replay worker or recovery path that reloads and retries pending/failed outbound deliveries after interruption.

### Next best slice

Implement the smallest additive outbound recovery seam on top of the existing outbox contract:

- add explicit retry/replay lifecycle semantics for outbound deliveries instead of treating the saved row as a write-only audit log
- provide one recovery entrypoint that reloads eligible pending or failed deliveries and replays them through the existing webhook delivery path
- keep the slice contract-safe across database state transitions, service logic, CLI or operator trigger surface, and dashboard visibility in the same turn
- verify with focused outbound-delivery tests plus one broader app/dashboard surface before checkpointing

### Operator handoff

Completed: corrected the parity ledger to match the current workspace by proving the routed outbox contract is already implemented and verified in OpenZues.

Verified: outbound-delivery persistence and operator surfaces are live across database, service, CLI, and dashboard layers; the next missing seam is delivery recovery/replay semantics.

Tool evidence:

- debugging: used tight source inspection plus bounded `rg` checks on outbound-delivery files only
- verification: ran focused `pytest`, `node --check`, and `compileall`
- delegation: not used
- memory/session search: Recall was unavailable in this runtime, so recovery used the named ledger anchor and narrow seam verification only

Next step: implement replay-safe outbound recovery for saved deliveries so OpenZues can resume or retry interrupted routed sends instead of only logging their prior state.

Blockers: none.

## Recovery checkpoint 2026-04-12 22:11 America/Chicago

### Completed

- Recovered from the stalled `Select-String` inspection lane without reopening the parity inventory.
- Re-verified the highest-value completed outbound parity seam instead of broadening into new implementation work.

### Verified

- Concrete claim rechecked: OpenZues already has the first durable routed outbox contract across service and operator CLI surfaces.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -k "outbound_delivery or notification_route" -q` -> `5 passed`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -k "routes_deliveries or routes_list_json_surfaces_saved_notification_routes" -q` -> `2 passed`

### Next smallest step

- Implement replay-safe outbound recovery for saved deliveries by adding retry/replay lifecycle semantics plus one operator trigger that reloads eligible pending or failed rows through the existing webhook sender.

### Blockers

- None.

## Recovery checkpoint 2026-04-12 recovery lane America/Chicago

### Completed

- Recovered from the stalled parity-ledger reread without reopening the full ledger again.
- Locked onto the active dashboard or control-chat seam already in the worktree and used this turn for bounded proof instead of new breadth.

### Verified

- Concrete claim rechecked: the active OpenClaw parity lane no longer needs to surface stale failed or quiet recovery artifacts while the dashboard can keep serving cached gateway capability posture if a refresh turns slow.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -k "dashboard_reuses_cached_gateway_capability_when_refresh_turns_slow or control_chat_view_hides_stale_failure_and_quiet_messages_for_active_target or attention_queue_view_hides_stale_failure_and_quiet_actions_for_active_target" -q` -> `3 passed`
- Recall succeeded first, so recovery stayed anchored to the live parity mission instead of rebuilding context from repo-wide reads.

### Next smallest step

- Run the broader `tests/test_app.py` pass for this dashboard or control-plane seam, then either checkpoint it as landed or repair any fallout before widening scope again.

### Blockers

- None.

## Recovery checkpoint 2026-04-12 late America/Chicago

### Completed

- Forced a landing turn on the already-landed outbox or notification-route seam instead of reopening the parity ledger or widening the search.
- Left the workspace unchanged and converted this recovery pass into proof of the existing contract.

### Verified

- Concrete claim rechecked: testing a notification route still records outbound delivery state and updates the route-state operator surface.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k "records_outbound_delivery or notification_route_test_api_updates_route_state"` -> `3 passed`
- Recall succeeded and recovery stayed anchored to the outbox or storage seam without rereading the full ledger.

### Next smallest step

- Implement replay-safe outbound recovery for saved deliveries so interrupted notification sends can be retried from persisted state rather than only inspected after the fact.

### Blockers

- None.
