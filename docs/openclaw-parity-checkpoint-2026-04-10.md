# OpenClaw Parity Checkpoint

## 2026-04-15 Method Registry Recovery Checkpoint

- Seam locked: gateway method registry parity.
- Verified against `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods-list.ts`; OpenZues has no missing built-in gateway methods or gateway events relative to the OpenClaw base registry.
- Focused proof: `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `18 passed in 0.10s`.
- Files anchoring this seam: `src/openzues/services/gateway_method_policy.py` and `tests/test_gateway_method_policy.py`.
- No product code change was required on this recovery turn; the seam was already locked and re-verified.
- Next smallest slice: inspect `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-session-key.ts` against the OpenZues session-key/routing counterpart and land any missing parity there before broadening to browser or wizard seams.

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

## Recovery checkpoint 2026-04-12 late-night America/Chicago

### Completed

- Recovered from the stalled ledger-tail read by locking onto the dashboard gateway-capability cache seam named by the interrupted `tests/test_app.py -k "dashboard_reuses..."` proof attempt.
- Re-read only the focused seam files instead of reopening the full ledger: `tests/test_app.py` for the exact contract and `src/openzues/app.py` for the dashboard gateway-capability cache path.
- Left production code unchanged because the cached-refresh fallback was already landed in `build_gateway_capability()`.

### Verified

- Concrete claim rechecked: `/api/dashboard` reuses the cached gateway-capability payload when a refresh turns slow instead of replacing it with a late refresh result.
- Source proof in `src/openzues/app.py`: when `gateway_cache` already exists, `build_gateway_capability()` wraps `active_gateway_capability_service.get_view()` in `asyncio.wait_for(...)` and returns the existing cache on timeout or refresh failure.
- Focused proof passed: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -k "dashboard_reuses_cached_gateway_capability_when_refresh_turns_slow" -q` -> `1 passed, 128 deselected`.
- Recovery stayed bounded: Recall succeeded first, and no repo-wide sweep or full-ledger reread was performed on this lane.

### Next smallest step

- Compare the rest of the dashboard or gateway contract around cache invalidation and refresh write-through against `C:\Users\skull\OneDrive\Documents\openclaw-main`, then land the smallest parity delta and rerun `tests/test_app.py` plus the contract pack if that seam changes.

### Blockers

- None.

## Recovery checkpoint 2026-04-12 broader app proof America/Chicago

### Completed

- Stayed on the same dashboard or control-chat parity seam instead of opening a new slice.
- Finished the missing broader app-surface verification that the prior recovery checkpoint left outstanding.

### Verified

- Concrete claim rechecked: the current dashboard, gateway-capability cache fallback, and active-mission control-chat filtering changes coexist cleanly across the full app test surface.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q` -> `129 passed in 119.69s`
- The broader pass initially hit the tool timeout at 120 seconds, so the same command was rerun with a longer timeout and captured output; no code changes were needed.

### Next smallest step

- Run the remaining control-plane contract pack for this seam: `tests/test_database.py`, `tests/test_manager.py`, `tests/test_ops_mesh.py`, `node --check src/openzues/web/static/app.js`, and `python -m compileall src/openzues`, then checkpoint the seam as fully verified if those stay green.

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

## Recovery checkpoint 2026-04-12 full app pass America/Chicago

### Completed

- Recovered from the stalled `tests/test_app.py` line-inspection lane by using Recall first, a single anchored ledger tail excerpt, and one bounded verification step.
- Kept the worktree unchanged and converted this turn into proof that the dashboard or control-plane parity seam is broadly green, not just green on a narrow selector.

### Verified

- Concrete claim rechecked: the already-landed dashboard or control-plane parity seam holds across the full application test surface, so the prior targeted dashboard assertions were not hiding broader app fallout.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q` -> `129 passed in 116.08s`

### Next smallest step

- Implement replay-safe outbound recovery for saved deliveries by adding retry or replay lifecycle semantics plus one operator trigger that reloads eligible pending or failed rows through the existing webhook sender.

### Blockers

- None.

## Recovery checkpoint 2026-04-12 outbound proof America/Chicago

### Completed

- Kept the parity lane narrow and used this turn to re-verify the already-landed outbound delivery or notification-route seam instead of reopening broader parity work.
- Left production code unchanged and converted the turn into durable proof for the saved delivery state path.

### Verified

- Concrete claim rechecked: testing a notification route still records outbound delivery state and updates the route-state operator surface.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k "records_outbound_delivery or notification_route_test_api_updates_route_state"` -> `3 passed, 26 deselected in 2.99s`

### Next smallest step

- Implement replay-safe outbound recovery for saved deliveries so eligible pending or failed rows can be retried through the existing webhook sender.

### Blockers

- None.

## Recovery checkpoint 2026-04-12 outbound cli proof America/Chicago

### Completed

- Stayed on the same saved-delivery or notification-route seam and used this turn for one broader operator-surface proof instead of new implementation work.
- Left production code unchanged and added a durable checkpoint for the CLI contract that reads the persisted route or delivery state.

### Verified

- Concrete claim rechecked: the operator CLI still surfaces saved notification routes and recorded delivery state on the routes or deliveries commands.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "routes_deliveries or routes_list_json_surfaces_saved_notification_routes"` -> `2 passed, 44 deselected in 21.19s`

### Next smallest step

- Implement replay-safe outbound recovery for saved deliveries so eligible pending or failed rows can be retried through the existing webhook sender.

### Blockers

- None.

## Recovery checkpoint 2026-04-12 frontend contract proof America/Chicago

### Completed

- Kept the parity lane narrow and used this turn to validate the already-landed dashboard or control-plane frontend contract instead of widening into new implementation work.
- Left production code unchanged and added one more durable proof point for the existing seam.

### Verified

- Concrete claim rechecked: the current dashboard or control-plane JavaScript bundle remains syntactically valid after the already-landed parity work.
- `node --check src/openzues/web/static/app.js` -> passed

### Next smallest step

- Implement replay-safe outbound recovery for saved deliveries so eligible pending or failed rows can be retried through the existing webhook sender.

### Blockers

- None.

## Recovery checkpoint 2026-04-12 outbound replay proof America/Chicago

### Completed

- Recovered from the stale-thread landing anchor with Recall plus one bounded ledger tail excerpt, then stayed on the saved outbound-delivery replay seam instead of broadening back into inventory work.
- Finished the smallest missing piece on that seam by adding focused replay coverage for the already-landed service and CLI paths in `tests/test_ops_mesh.py` and `tests/test_cli.py`.

### Verified

- Concrete claim rechecked: a saved failed outbound delivery that is past backoff is replayed through the existing webhook sender, transitions back to `delivered`, clears the prior error, and increments the attempt count in both the service and operator CLI surfaces.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k replay_outbound_deliveries_retries_saved_failed_delivery` -> `1 passed, 29 deselected in 1.19s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k routes_replay_json_retries_saved_failed_delivery` -> `1 passed, 46 deselected in 6.23s`

### Next smallest step

- Add one equally tight proof for the replay guardrails: either the disabled or missing-route failure path, or the max-retries or backoff-deferred path through `/api/notification-routes/replay`.

### Blockers

- None.

## Recovery checkpoint 2026-04-13 outbound replay disabled-route proof America/Chicago

Completed:

- Stayed on the same saved outbound-delivery replay seam and finished one small missing guardrail: replay refusal when the saved notification route has been disabled.
- Added focused proof points in `tests/test_ops_mesh.py` and `tests/test_cli.py` so the service and operator CLI both prove the disabled-route path without widening production scope.

Verified:

- Concrete claim rechecked: replay does not fire the webhook sender when the saved route is disabled; instead it reports the route as unavailable for replay, keeps the delivery failed, and marks the saved row as maxed out for further replay attempts.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k replay_outbound_deliveries_fails_when_route_is_disabled` -> `1 passed, 30 deselected in 1.39s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k routes_replay_json_reports_disabled_route_failure` -> `1 passed, 47 deselected in 10.95s`

Tool evidence:

- `debugging`: used focused `rg`, bounded file reads, and targeted `pytest` runs on the replay seam.
- `memory`: used OpenZues Recall earlier in this recovery thread to re-anchor the parity lane before the bounded replay work resumed.
- `session_search`: satisfied by the same Recall invocation in this thread because it queried saved mission or checkpoint history before restating context.
- `delegation`: not used on this slice; the seam was already narrow enough that a sidecar would not have tightened scope.

Next step:

- Add one equally tight proof for replay deferral rather than failure: either the backoff-deferred path or the max-retries-skipped path through `/api/notification-routes/replay`.

Blockers:

- None.

## Recovery checkpoint 2026-04-14 gateway handler-family proof refresh America/Chicago

Completed:

- Stayed on the saved `method registry` parity seam and repaired the OpenClaw handler extractor in `tests/test_gateway_method_policy.py` so source-derived proofs now capture both `async` handlers and arrow-form handlers like `talk.mode` and `chat.abort`.
- Landed the next bounded source-of-truth proofs from `openclaw-main/src/gateway/server-methods/channels.ts` and `openclaw-main/src/gateway/server-methods/chat.ts`, locking the exact OpenClaw handler families against the existing OpenZues scope policy without widening into unrelated gateway families.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` -> `13 passed in 0.09s`
- `.\\.venv\\Scripts\\python.exe -m ruff check tests/test_gateway_method_policy.py` -> still fails on pre-existing file-wide `I001`/`E501` issues outside this recovery slice; no new lint blocker remains in the added assertions.

Tool evidence:

- debugging: used exact `rg` probes on `tests/test_gateway_method_policy.py`, `src/openzues/services/gateway_method_policy.py`, and OpenClaw `src/gateway/server-methods/{channels,chat}.ts`, then verified with focused `pytest` and `ruff`.
- delegation: used one Architect sidecar to name the next smallest uncovered handler family and confirm `channels.ts` as the first bounded proof slice before edits.
- memory: used OpenZues Recall via `.\\.venv\\Scripts\\python.exe -m openzues.cli recall --json "gateway method policy"` to recover the active parity seam before touching repo files on this recovery lane.
- session_search: used that Recall result as the saved mission/checkpoint anchor instead of reopening the parity ledger again.

Next step:

- Stay inside `method registry` and take the next mixed-scope OpenClaw handler family with the repaired extractor, preferably `web.ts`, `secrets.ts`, or the first bounded `sessions.ts` subset, then rerun `tests/test_gateway_method_policy.py -q`.
- After the direct handler-family proofs stop yielding leverage, widen back to the queued `routing/session-key` parity seam from the saved re-anchor.

Blockers:

- None for the active parity slice.

## Recovery checkpoint 2026-04-13 replay missing-route-row plain CLI verification America/Chicago

Recovered context:

- Used OpenZues Recall first, then a single bounded ledger tail read to resume the active saved outbound-delivery replay lane without reopening source inventory.
- The prior checkpoint's stated next step was the plain `openzues routes replay` proof for the missing-route-row branch, so this turn only validated whether that gap was still real.

Completed:

- Confirmed the plain-text CLI proof was already landed in `tests/test_cli.py` as `test_routes_replay_reports_missing_saved_route_row_failure`.
- Made no production or test edits because the claimed missing piece was already present and aligned with the existing replay service branch in `src/openzues/services/ops_mesh.py`.

Verified:

- Concrete claim rechecked: plain `openzues routes replay` already reports `Notification route {route_id} is unavailable for replay.` for a saved failed delivery whose persisted `route_id` points to a deleted notification-route row, shows the failed summary counts, does not call the webhook sender, and preserves the saved delivery as failed with max retries reached.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k routes_replay_reports_missing_saved_route_row_failure` -> `1 passed, 61 deselected in 8.73s`

Next step:

- Run one bounded replay-only verification pack that groups the missing-route-row service, JSON CLI, and plain CLI proofs together, then use that frozen replay branch to choose the next smallest parity seam outside saved outbound-delivery replay.

Blockers:

- None.

## Recovery checkpoint 2026-04-13 outbound replay human-readable row-and-maxed proofs America/Chicago

Recovered context:

- Re-entered from OpenZues Recall and the parity-ledger tail, which already pinned the active lane to saved outbound-delivery replay rather than a new source inventory pass.
- The ledger confirmed the next named seam was the plain `routes replay` proof for the missing saved-route-row branch; after landing that, the same formatter lane still had one equally small uncovered count-only branch for max-retries skips.

Completed:

- Added a focused human-readable CLI proof in `tests/test_cli.py` for replaying a saved failed delivery whose `route_id` still exists on the saved row after the notification route row has been deleted.
- Added one adjacent human-readable CLI proof in `tests/test_cli.py` for replaying a saved failed delivery that is already at `OUTBOUND_DELIVERY_MAX_RETRIES`, locking the plain-text `maxed=` counter and summary path.
- Kept the turn additive and test-only because the existing replay service and CLI formatter branches already matched the expected production contract.

Verified:

- Concrete claim rechecked: plain `openzues routes replay` now has focused proof that a missing saved route row renders the replay failure line `Notification route {route_id} is unavailable for replay.`, preserves the failed delivery in storage, and does not call the webhook sender.
- Concrete claim rechecked: plain `openzues routes replay` now has focused proof that a saved failed delivery already at max retries is skipped without a replay attempt, increments `maxed=1`, emits the `hit max retries` summary, and leaves the saved row untouched.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "routes_replay_json_reports_missing_saved_route_row_failure or routes_replay_reports_missing_saved_route_row_failure or routes_replay_json_skips_saved_failed_delivery_at_max_retries or routes_replay_skips_saved_failed_delivery_at_max_retries"` -> `4 passed, 56 deselected in 12.55s`

Tool evidence:

- `debugging`: used bounded reads on `tests/test_cli.py` and the replay formatter/service branch, additive test edits, and one focused `pytest` run on the four replay proofs in scope.
- `memory`: used OpenZues Recall first on recovery to regain the active parity seam before repo reads.
- `session_search`: satisfied by that Recall lookup because it queried saved mission/checkpoint state instead of rediscovering context from dumps.
- `delegation`: not used on this slice because the owned file set and verification bar were already narrow enough to close directly.

Next step:

- Add the adjacent human-readable CLI proof for the remaining count-only replay branch where a saved failed delivery is still inside backoff, confirming plain `openzues routes replay` reports `deferred=1`, keeps `ok: True`, emits the `deferred by backoff` summary, and leaves the saved row untouched.

Blockers:

- None.

## Recovery checkpoint 2026-04-13 outbound replay plain-cli missing-route proof America/Chicago

Recovered context:

- OpenZues Recall re-anchored the mission to the outbound replay seam.
- A bounded replay-branch read plus focused pytest confirmed the live tree had already outrun the ledger on the missing-route-id branch: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`, and `tests/test_cli.py` already covered the service and JSON replay failure for `Saved delivery is missing its notification route.`

Completed:

- Added the next smallest adjacent parity proof on the human-readable CLI surface in `tests/test_cli.py`.
- Landed `test_routes_replay_reports_missing_route_id_failure` to prove plain `routes replay` output preserves the same missing-route failure text, counter summary, and persisted row state as the already-covered JSON path.

Verified:

- Concrete claim rechecked before editing: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k test_replay_outbound_deliveries_fails_when_saved_delivery_is_missing_route_id` -> `1 passed, 33 deselected in 1.10s`
- Concrete claim rechecked before editing: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k test_routes_replay_json_reports_missing_route_id_failure` -> `1 passed, 50 deselected in 9.93s`
- New slice verified: plain `routes replay` now has a focused regression proof for the missing-route-id failure branch, including `ok: False`, the replay counters, the rendered `[error]` delivery line, the canonical error text, and the persisted maxed-out failed row.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "test_routes_replay_reports_missing_route_id_failure or test_routes_replay_json_reports_missing_route_id_failure or test_routes_replay_json_reports_disabled_route_failure or test_routes_replay_json_defers_saved_failed_delivery_in_backoff or test_routes_replay_json_skips_saved_failed_delivery_at_max_retries or test_routes_replay_json_retries_saved_failed_delivery"` -> `6 passed, 46 deselected in 34.63s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k "test_replay_outbound_deliveries_fails_when_saved_delivery_is_missing_route_id or test_replay_outbound_deliveries_fails_when_route_is_disabled or test_replay_outbound_deliveries_defers_saved_failed_delivery_in_backoff or test_replay_outbound_deliveries_skips_saved_failed_delivery_at_max_retries or test_replay_outbound_deliveries_retries_saved_failed_delivery"` -> `5 passed, 29 deselected in 1.46s`

Tool evidence:

- `debugging`: used focused `rg`, bounded file reads, one targeted test edit, and replay-only `pytest` runs.
- `delegation`: used one architect sidecar to compare the narrow replay seam between `openclaw-main` and `OpenZues`, confirm the missing-route branch was already implemented, and identify the next smallest adjacent proof gap.
- `memory`: used OpenZues Recall at re-entry to recover the active parity lane before opening repo files.
- `session_search`: satisfied by the same Recall query because it searched saved mission and checkpoint state before the seam was re-selected.

Next step:

- Add one equally tight non-JSON `routes replay` proof for another failure/skipped variant, with disabled-route refusal as the best next slice because it exercises the same formatter on a distinct replay outcome without widening production code.

Blockers:

- None.

## Recovery checkpoint 2026-04-13 outbound replay missing-route-id proof America/Chicago

Recovered context:

- Re-entered from the parity ledger anchor after OpenZues Recall confirmed the saved outbound-delivery replay seam was still the active lane for mission 28.
- Verified the live service branch in `src/openzues/services/ops_mesh.py` before editing and corrected the seam wording against code: the exact `Saved delivery is missing its notification route.` failure path is the `route_id is None` branch, not the stale-route-row branch.

Completed:

- Added one focused service proof in `tests/test_ops_mesh.py` and one focused CLI proof in `tests/test_cli.py` for replaying a saved failed delivery whose `route_id` is missing.
- Kept production code unchanged because the branch already existed; this slice only hardened the parity seam with direct coverage.

Verified:

- Concrete claim rechecked: when a saved failed outbound delivery has no `route_id`, `/api/notification-routes/replay` counts it as attempted and failed, does not call the webhook sender, maxes the saved delivery's attempt count, and records `Saved delivery is missing its notification route.` on both the replay result and the persisted row.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k replay_outbound_deliveries_fails_when_saved_delivery_is_missing_route_id` -> `1 passed, 33 deselected in 1.19s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k routes_replay_json_reports_missing_route_id_failure` -> `1 passed, 50 deselected in 6.17s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k "replay_outbound_deliveries_retries_saved_failed_delivery or replay_outbound_deliveries_fails_when_route_is_disabled or replay_outbound_deliveries_defers_saved_failed_delivery_in_backoff or replay_outbound_deliveries_skips_saved_failed_delivery_at_max_retries or replay_outbound_deliveries_fails_when_saved_delivery_is_missing_route_id"` -> `5 passed, 29 deselected in 1.32s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "routes_replay_json_retries_saved_failed_delivery or routes_replay_json_reports_disabled_route_failure or routes_replay_json_defers_saved_failed_delivery_in_backoff or routes_replay_json_skips_saved_failed_delivery_at_max_retries or routes_replay_json_reports_missing_route_id_failure"` -> `5 passed, 46 deselected in 26.82s`

Tool evidence:

- `debugging`: used one Recall-confirmed ledger tail read, one bounded service/test branch read, targeted test edits, and replay-only `pytest` runs.
- `memory`: used OpenZues Recall first on re-entry to recover the active mission and checkpoint anchor before repo reads.
- `session_search`: satisfied by the same Recall-backed recovery lookup because it queried saved mission/checkpoint state rather than rebuilding context from dumps.
- `delegation`: not used on this slice because the exact seam, owned files, and verification bar were narrow enough to close directly.

Next step:

- Add one equally tight replay proof for the stale saved-route branch where `route_id` is still present but the notification route row is gone, confirming `/api/notification-routes/replay` reports `Notification route {route_id} is unavailable for replay.` and preserves the no-webhook failure behavior.

Blockers:

- None.

## Recovery checkpoint 2026-04-13 outbound replay backoff-deferral proof America/Chicago

Completed:

- Stayed on the saved outbound-delivery replay seam and finished the next smallest missing proof slice: deferred replay while a failed saved delivery is still inside backoff.
- Added one focused service proof in `tests/test_ops_mesh.py` and one focused operator CLI proof in `tests/test_cli.py` without widening production scope.

Verified:

- Concrete claim rechecked: replay leaves a saved failed delivery untouched while its backoff window is still active, reports it as deferred rather than attempted, does not fire the webhook sender, and preserves the saved row's attempt count and prior error.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k "replay_outbound_deliveries_retries_saved_failed_delivery or replay_outbound_deliveries_fails_when_route_is_disabled or replay_outbound_deliveries_defers_saved_failed_delivery_in_backoff"` -> `3 passed, 29 deselected in 1.46s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "routes_replay_json_retries_saved_failed_delivery or routes_replay_json_reports_disabled_route_failure or routes_replay_json_defers_saved_failed_delivery_in_backoff"` -> `3 passed, 46 deselected in 21.70s`

Tool evidence:

- `debugging`: used focused `rg`, bounded file reads, test edits, and targeted replay-only `pytest` runs.
- `delegation`: not used on this slice because the seam stayed narrow enough to implement and verify directly in the lead lane.
- `memory`: earlier in this recovery thread, Recall was used to re-anchor the replay seam before these bounded proofs continued.
- `session_search`: not re-exercised on this slice; the earlier Recall-backed recovery in this thread remained the active anchor.

Next step:

- Add one equally tight replay proof for the remaining skip path: a saved delivery that is already at max retries should be counted under `skipped_max_retries_count` and left untouched through `/api/notification-routes/replay`.

Blockers:

- None.

## Recovery checkpoint 2026-04-13 outbound replay compact recheck America/Chicago

Completed:

- Re-ran the saved outbound-delivery replay seam as a compact verification pass without widening scope or changing production code.
- Reconfirmed the two highest-value proofs already landed on this seam: successful replay of an eligible saved failed delivery, and refusal to replay when the saved route is disabled.

Verified:

- Concrete claim rechecked: eligible saved failed outbound deliveries still replay cleanly through both the service and CLI surfaces, while disabled-route deliveries remain blocked from replay and stay failed.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k "replay_outbound_deliveries_retries_saved_failed_delivery or replay_outbound_deliveries_fails_when_route_is_disabled"` -> `2 passed, 29 deselected in 0.94s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "routes_replay_json_retries_saved_failed_delivery or routes_replay_json_reports_disabled_route_failure"` -> `2 passed, 46 deselected in 10.34s`

Tool evidence:

- `debugging`: used targeted `pytest` runs plus one bounded checkpoint-tail read on the replay seam.
- `delegation`: not used on this slice because the seam was already narrow and verification-only.
- `memory`: not re-exercised in this compact recheck turn.
- `session_search`: not re-exercised in this compact recheck turn.

Next step:

- Add one equally tight deferred-replay proof through `/api/notification-routes/replay`: either a backoff-deferred saved delivery or a max-retries-skipped saved delivery.

Blockers:

- None.

<!-- OPENZUES_PARITY_MISSION:40 -->

## Update: OpenClaw Total Parity Program

Date: 2026-04-13

### Operator handoff

Completed: stayed on the saved outbound-delivery replay seam and finished one small missing guardrail, proving replay refusal when the saved notification route is disabled. I added focused tests in [tests/test_ops_mesh.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py:1998) and [tests/test_cli.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_cli.py:629), then appended the checkpoint at [docs/openclaw-parity-checkpoint-2026-04-10.md](/C:/Users/skull/OneDrive/Documents/OpenZues/docs/openclaw-parity-checkpoint-2026-04-10.md:2912).

Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k replay_outbound_deliveries_fails_when_route_is_disabled` passed with `1 passed, 30 deselected in 1.39s`, and `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k routes_replay_json_reports_disabled_route_failure` passed with `1 passed, 47 deselected in 10.95s`. The claim now covered is that replay does not call the webhook sender for a disabled saved route, reports the route as unavailable for replay, leaves the delivery failed, and marks it maxed out.

Tool evidence: `debugging` was used through focused `rg`, bounded file reads, and targeted `pytest`; `memory` and `session_search` were exercised earlier in this recovery thread through OpenZues Recall; `delegation` was not used because this slice was already narrow.

Next step: add one equally tight proof for replay deferral rather than failure, either the backoff-deferred path or the max-retries-skipped path through `/api/notification-routes/replay`.

Blockers: none.

### Observed tool evidence

- Thread evidence covered 1 of 4 declared toolsets: debugging. Explicit proof is still missing for delegation, memory, session_search.
- debugging: observed (Command: "C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'rg -n "Notification route .* unavailable for replay|deferred by backoff|max retries|replay_outbound_deliveries|routes_replay" tests/t...)
- delegation: unproven
- memory: unproven
- session_search: unproven

## Recovery checkpoint 2026-04-13 outbound replay max-retries skip proof America/Chicago

Recovered context:

- Re-entered from the parity ledger anchor after Recall showed the saved outbound-delivery replay seam was still the active lane.
- The ledger tail and live service branch agreed that successful replay, disabled-route refusal, and backoff deferral were already covered; the smallest unfinished seam was the max-retries skip path in `tests/test_ops_mesh.py` and `tests/test_cli.py`.

Completed:

- Added one focused service proof and one focused CLI proof for replaying saved failed deliveries that have already exhausted retries.
- Locked the seam in `tests/test_ops_mesh.py` and `tests/test_cli.py` without widening production code because `OpsMeshService.replay_outbound_deliveries` already carries the `skipped_max_retries_count` branch.

Verified:

- Concrete claim rechecked: a saved failed delivery already at `OUTBOUND_DELIVERY_MAX_RETRIES` is skipped by `/api/notification-routes/replay`, counted under `skipped_max_retries_count`, does not call the webhook sender, and preserves the saved row's failed state, attempt count, and prior error.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k replay_outbound_deliveries_skips_saved_failed_delivery_at_max_retries` -> `1 passed, 32 deselected in 1.40s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k routes_replay_json_skips_saved_failed_delivery_at_max_retries` -> `1 passed, 49 deselected in 7.98s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k "replay_outbound_deliveries_retries_saved_failed_delivery or replay_outbound_deliveries_fails_when_route_is_disabled or replay_outbound_deliveries_defers_saved_failed_delivery_in_backoff or replay_outbound_deliveries_skips_saved_failed_delivery_at_max_retries"` -> `4 passed, 29 deselected in 1.57s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "routes_replay_json_retries_saved_failed_delivery or routes_replay_json_reports_disabled_route_failure or routes_replay_json_defers_saved_failed_delivery_in_backoff or routes_replay_json_skips_saved_failed_delivery_at_max_retries"` -> `4 passed, 46 deselected in 26.16s`

Tool evidence:

- `debugging`: used bounded reads on the replay service branch, targeted test edits, and focused replay-only `pytest` runs.
- `memory`: used OpenZues Recall at re-entry to recover the active parity lane before touching repo files.
- `session_search`: satisfied by the same Recall-backed recovery lookup because it queried saved mission and checkpoint state before the seam was chosen.
- `delegation`: not used on this slice because the owned files and verification bar were already narrow enough to close directly.

Next step:

- Add one equally tight replay failure proof for the remaining untested branch where a saved failed delivery has lost its route row entirely and `/api/notification-routes/replay` returns `Saved delivery is missing its notification route.`

Blockers:

- None.

## Recovery checkpoint 2026-04-13 outbound replay missing-route-row proof America/Chicago

Recovered context:

- Re-entered from OpenZues Recall and the parity-ledger tail without reopening the source inventory.
- The active seam was still saved outbound-delivery replay; the smallest unfinished branch was the case where a failed saved delivery still carries `route_id` but the notification route row has been deleted.

Completed:

- Added one focused service proof in `tests/test_ops_mesh.py` and one focused CLI JSON proof in `tests/test_cli.py` for replaying a saved failed delivery whose route row is gone.
- Verified the existing production branch in `src/openzues/services/ops_mesh.py` already synthesizes an unavailable disabled route view for `route_row is None`, so the turn stayed additive and test-only.

Verified:

- Concrete claim rechecked: when `/api/notification-routes/replay` sees a saved failed delivery with a persisted `route_id` whose notification route row no longer exists, it counts the delivery as attempted and failed, does not call the webhook sender, reports `Notification route {route_id} is unavailable for replay.`, synthesizes a disabled route view in the result payload, and maxes the saved delivery's retry state in storage.
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k replay_outbound_deliveries_fails_when_saved_route_row_is_missing` -> `1 passed, 34 deselected in 1.36s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k routes_replay_json_reports_missing_saved_route_row_failure` -> `1 passed, 53 deselected in 14.09s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_ops_mesh.py -q -k "replay_outbound_deliveries_retries_saved_failed_delivery or replay_outbound_deliveries_fails_when_route_is_disabled or replay_outbound_deliveries_fails_when_saved_route_row_is_missing or replay_outbound_deliveries_defers_saved_failed_delivery_in_backoff or replay_outbound_deliveries_skips_saved_failed_delivery_at_max_retries or replay_outbound_deliveries_fails_when_saved_delivery_is_missing_route_id"` -> `6 passed, 29 deselected in 1.49s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "routes_replay_json_retries_saved_failed_delivery or routes_replay_json_reports_disabled_route_failure or routes_replay_json_reports_missing_saved_route_row_failure or routes_replay_json_defers_saved_failed_delivery_in_backoff or routes_replay_json_skips_saved_failed_delivery_at_max_retries or routes_replay_json_reports_missing_route_id_failure"` -> `6 passed, 48 deselected in 36.24s`

Tool evidence:

- `debugging`: used bounded `rg`/`Get-Content` reads on the replay branch, targeted test edits, and replay-only `pytest` verification.
- `delegation`: used one tightly scoped explorer sidecar to confirm the missing-row assertion surface and keep the service/CLI expectations aligned with the disabled-route branch.
- `memory`: used OpenZues Recall first on recovery to re-anchor the mission before repo reads.
- `session_search`: satisfied by the same Recall lookup because it queried saved mission/checkpoint state instead of rebuilding context from dumps.

Next step:

- Add the adjacent human-readable CLI proof for the same missing-route-row branch so plain `openzues routes replay` output is parity-covered alongside the service and JSON surfaces.

Blockers:

- None.

## 2026-04-13 Recovery Checkpoint
Completed: Recovered the stale-thread lane with OpenZues Recall and resumed from the restart-safe anchor without reopening the full parity inventory.
Verified: Ran `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -k replay -q` in `C:\Users\skull\OneDrive\Documents\OpenZues`; result was `9 passed, 53 deselected` in 85.41s, confirming the current replay seam remains green.
Next smallest step: Reopen one anchored excerpt from `docs/openclaw-parity-checkpoint-2026-04-10.md` to identify the next bounded missing seam adjacent to replay output parity, then implement and verify that slice only.
Blockers: None on the verified replay seam. The remaining blocker is seam selection from the anchored ledger excerpt, which was intentionally deferred this turn to avoid broadening scope during recovery.

## Recovery checkpoint 2026-04-13 parity re-anchor America/Chicago

Recovered context:

- This file's tail drifted with unrelated outbound replay checkpoints. For `OpenClaw Total Parity Program`, treat those replay, notification-route, delivery, and generic CLI replay sections as cross-mission contamination rather than the active parity seam.
- The last trustworthy parity-specific trail stays on the OpenClaw control-plane kernel: gateway bootstrap and method-registry inventory, then routing and session-key policy, before channels, browser runtime, nodes, voice, or companion apps.

Completed:

- Patched mission-control recovery so live item events can correct a stale stored `last_turn_id`, which lets OpenZues recognize real final-answer progress instead of staring at the wrong turn window.
- Hardened parity recovery doctrine so future re-entry ignores replay or outbound-route contamination inside this ledger and re-anchors on explicit OpenClaw parity domains instead.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_missions.py -q -k "final_answer_streams or restart_safe_snapshot_for_stale_turn or last_turn_id_from_live_item_event or reporting_orbit"` -> `5 passed, 91 deselected in 0.67s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src/openzues/services/missions.py tests/test_missions.py` -> passed

Next step:

- Resume genuine OpenClaw parity from this re-anchor, not from the outbound replay notes above.
- Preferred next slice: inventory one bounded OpenClaw gateway bootstrap or method-registry gap against `openclaw-main`, land that slice end to end, run focused verification, and checkpoint it here before widening scope again.

Blockers:

- None. The remaining risk is ledger contamination if unrelated recovery notes are appended below this re-anchor again.

## Recovery checkpoint 2026-04-13 parity re-anchor refresh America/Chicago

Recovered context:

- The ledger tail drifted again after the earlier parity re-anchor because a later recovery turn pulled in outbound replay, notification-route, delivery, and generic replay CLI notes.
- For `OpenClaw Total Parity Program`, treat those outbound replay sections as cross-mission contamination, not as the active parity seam.

Completed:

- Hardened mission-control parity recovery so Recall queries seeded with reflex labels like `execution_stall`, `live_heartbeat`, `restart_safe`, `thread_rebind`, `orbit_rebind`, or `reflex_auto` are treated as drift rather than good recovery footing.
- Hardened mission-control parity recovery so generic governor slogans like `force landing`, `checkpoint now`, `recovery packet`, or `next seam` no longer qualify as good Recall queries unless they also name a concrete parity seam.
- Tightened checkpoint-now stall handling so wide parity-ledger tail reads like `Get-Content ... -Tail 80` or `Select-Object -Last 80` are cut quickly instead of being mistaken for useful seam recovery.
- Reclassified OpenZues Recall as inspection-only for execution-stall handling, so read-only parity recovery loops get the same fast governor treatment as other inspection drift.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_missions.py -q -k "checkpoint_landing_drift or parity_recall_query_drift or wide_parity_tail_read or parity_recovery_prompt or final_answer_streams or reporting_orbit or tighter_for_inspection_commands"` -> `8 passed, 90 deselected in 1.85s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_missions.py -q` -> `99 passed in 15.21s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src/openzues/services/missions.py tests/test_missions.py` -> passed

Next step:

- Resume genuine OpenClaw parity from this refreshed re-anchor, not from the replay notes above.
- Preferred next slice: inventory one bounded OpenClaw gateway bootstrap or method-registry gap against `openclaw-main`, implement it end to end, run focused verification, and checkpoint it here before widening toward routing/session-key policy.

## Checkpoint 2026-04-14 gateway method policy recovery refresh America/Chicago

Recovered context:

- Kept this recovery turn pinned to the already-anchored gateway bootstrap and method-registry seam instead of reopening the contaminated ledger tail or rereading the stalled `src/openzues/cli.py` inspection.
- Used OpenZues Recall with the concrete `method registry` seam, then moved straight to exact gateway-policy verification.

Completed:

- Revalidated the existing OpenZues gateway method policy handoff without widening scope or changing production code.
- Confirmed the exact focused proof from the earlier stalled lane still holds: the OpenZues gateway method policy contract remains green against the current source-backed test pack.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` -> `8 passed in 0.36s`

Next step:

- Treat the gateway method policy seam as reverified and complete for this recovery lane.
- Next smallest parity slice: compare OpenClaw `src/shared/device-bootstrap-profile.ts` against OpenZues `src/openzues/cli.py`, `src/openzues/services/onboarding.py`, and `src/openzues/services/gateway_bootstrap.py`, then land the first missing bootstrap-profile field or normalization rule with focused verification before widening toward routing/session-key policy.

## Checkpoint 2026-04-14 routing session thread suffix continuity America/Chicago

Recovered context:

- Revalidated the saved bootstrap-profile anchor against OpenClaw `src/shared/device-bootstrap-profile.ts` and `src/shared/device-auth.ts` before widening scope; the existing OpenZues bootstrap roles/scopes flow in `cli.py`, `onboarding.py`, `gateway_bootstrap.py`, and `device_bootstrap_profile.py` already matched the source-backed normalization and allowlist behavior.
- Used one architect sidecar after the seam was locked to pick the next smallest missing slice, which narrowed the remaining gap to OpenClaw-style `:thread:` session-key suffix parsing and parent recovery.

Completed:

- Added first-class thread-suffix parsing to [session_keys.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/session_keys.py) with `ParsedThreadSessionSuffix`, `parse_thread_session_suffix`, and `resolve_thread_parent_session_key`, matching OpenClaw `src/sessions/session-key-utils.ts` behavior for case-insensitive `:thread:` detection while preserving the raw base key and thread id.
- Wired [missions.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/missions.py) so session-key thread reuse now falls back from a child key like `...:thread:<id>` to its parent base session key when looking up an existing mission thread.
- Added source-backed coverage in [test_session_keys.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_session_keys.py) and [test_missions.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_missions.py) for mixed-case suffix parsing, parent recovery, and mission reuse through a thread-suffixed session key.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_device_bootstrap_profile.py -q` -> `3 passed in 0.03s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_gateway_bootstrap.py -q` -> `6 passed in 0.98s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_session_keys.py tests\\test_missions.py -q -k "session_key"` -> `12 passed, 131 deselected in 1.26s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_session_keys.py tests\\test_missions.py -q` -> `143 passed in 26.85s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src\\openzues\\services\\session_keys.py src\\openzues\\services\\missions.py tests\\test_session_keys.py tests\\test_missions.py` -> passed

Tool evidence:

- debugging: used concrete source/target probes on `openclaw-main/src/shared/device-bootstrap-profile.ts`, `openclaw-main/src/shared/device-auth.ts`, `openclaw-main/src/sessions/session-key-utils.ts`, `openclaw-main/src/routing/session-key.ts`, plus focused reads of `session_keys.py`, `missions.py`, and the exact test files.
- delegation: used one architect sidecar to map the next bounded parity seam and verification bar, which identified the thread-suffix continuity slice.
- memory: used OpenZues Recall earlier in this recovery thread to re-anchor on `gateway bootstrap`, `routing/session-key`, and `browser runtime` without rebuilding the global inventory.
- session_search: queried saved parity history through `.\.venv\Scripts\python.exe -m openzues.cli recall --json` using concrete seam names before choosing the next slice.

Next step:

- Compare OpenClaw thread-key construction in `openclaw-main/src/routing/session-key.ts` against OpenZues `src/openzues/services/session_keys.py` and `src/openzues/services/launch_routing.py`, then land the next smallest routing continuity rule around when child `:thread:` keys should be minted or preserved during route resolution.

Blockers:

- None.

## Checkpoint 2026-04-15 routing child session preservation America/Chicago

Completed:

- Extended [launch_routing.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/launch_routing.py) so workspace-affinity route descriptions preserve an existing child `:thread:` session key when the reusable conversation already lives on that exact child session for the resolved lane, instead of collapsing the handoff back to the base launch key.
- Added [Database.get_latest_thread_child_mission_by_parent_session_key](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/database.py) so routing can find saved child-session missions by their parent launch key without widening the rest of the mission lookup contract.
- Added a focused regression in [test_launch_routing.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_launch_routing.py) covering the preserved child-session route, `last_route_policy="session"`, and reusable thread continuity on the resolved lane.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_launch_routing.py -q` -> `2 passed in 1.39s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src/openzues/database.py src/openzues/services/launch_routing.py tests/test_launch_routing.py` -> passed

Next smallest step:

- Stay on routing/session-key continuity and compare OpenClaw `src/routing/resolve-route.ts` thread-parent binding behavior against OpenZues conversation-target routing, then land one focused inheritance rule or checkpoint the exact contract gap if no direct peer-thread surface exists yet.

Blockers:

- None.

## Checkpoint 2026-04-15 routing parent-peer contract gap America/Chicago

Completed:

- Compared OpenClaw `src/routing/resolve-route.ts` against OpenZues `src/openzues/services/launch_routing.py` for the saved `routing/session-key` seam instead of widening scope.
- Confirmed the next missing OpenClaw behavior is peer-parent binding inheritance (`parentPeer` plus `matchedBy="binding.peer.parent"`), but OpenZues launch routing currently only routes from a single normalized `ConversationTargetView` peer and a session key.
- Left production code unchanged on this turn because there is no direct OpenZues conversation-target contract for a parent peer yet; porting the OpenClaw rule now would require a wider schema/API/CLI/dashboard seam instead of a safe one-file routing patch.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_launch_routing.py -q` -> `2 passed in 1.59s`

Next smallest step:

- Treat `parentPeer` inheritance as a contract-gap checkpoint, then compare OpenClaw peer-parent routing inputs against OpenZues `ConversationTargetView` and the gateway/task surfaces that populate it; land the smallest additive parent-peer field set end to end only if that contract can be threaded through schemas, persistence, API payloads, and launch routing in one slice.

Blockers:

- OpenZues does not yet expose a source-of-truth parent-peer field in the launch conversation-target contract, so there is no narrow routing-only hook for OpenClaw's `binding.peer.parent` behavior yet.

## Checkpoint 2026-04-14 routing session-key reflex landing America/Chicago

Recovered context:

- Stayed pinned to the saved `routing/session-key` seam from the latest parity checkpoint instead of reopening Recall or rereading the parity ledger again during the forced-landing turn.
- Reused the already recovered anchor directly: OpenClaw `src/routing/session-key.ts` versus OpenZues `src/openzues/services/session_keys.py` and `src/openzues/services/launch_routing.py`.

Completed:

- Revalidated the current OpenZues routing/session-key seam with exact focused tests instead of widening scope or guessing at a broader routing change.
- Confirmed the existing `:thread:` suffix parsing and launch-routing path remain green after recovery, so the prior parity slice is still durable.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_launch_routing.py tests\\test_session_keys.py -q` -> `9 passed in 1.20s`

Next step:

- Compare the OpenClaw `resolveThreadSessionKeys(...)` consumer path against OpenZues launch-route session-key output and land one smallest production rule around preserving the base parent session key when a routed child `:thread:` session key is reused.
- Keep the next turn bounded to `openclaw-main/src/routing/session-key.ts`, `src/openzues/services/session_keys.py`, `src/openzues/services/launch_routing.py`, and the exact routing/session-key test files.

Blockers:

- The remaining gap is not verified yet: this reflex landing did not inspect the downstream OpenClaw route consumer that decides whether the parent base session key must travel alongside a child `:thread:` key, so the next turn should patch only after that single source-backed comparison.

## Checkpoint 2026-04-14 thread session key helper parity America/Chicago

Recovered context:

- Continued from the saved `routing/session-key` anchor instead of reopening Recall or rereading the parity ledger.
- Used the named OpenClaw seam directly: `openclaw-main/src/routing/session-key.ts` and its focused test coverage in `openclaw-main/src/routing/session-key.test.ts`.

Completed:

- Added OpenClaw-style `resolve_thread_session_keys(...)` to [session_keys.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/session_keys.py) with a durable `ResolvedThreadSessionKeys` result that carries both the resolved child session key and an optional parent session key.
- Matched the source-backed behavior for the bounded helper seam: blank thread ids collapse back to the base key with no parent passthrough, suffixed thread keys lowercase the normalized thread token, and callers can preserve the base key while still carrying an explicit parent session key when `use_suffix=False`.
- Added focused parity coverage in [test_session_keys.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_session_keys.py) for suffix minting, blank-thread fallback, and parent-session passthrough.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_session_keys.py -q` -> `11 passed in 0.72s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src\\openzues\\services\\session_keys.py tests\\test_session_keys.py` -> passed

Next step:

- Compare the downstream OpenClaw route or reply consumer that actually uses `parentSessionKey` against OpenZues launch handoff and mission-thread reuse paths, then wire this new helper into one concrete consumer if the source-backed comparison shows a missing continuity rule.
- Keep the next slice bounded to the same routing/session-key seam: one OpenClaw consumer file plus `src/openzues/services/launch_routing.py` or `src/openzues/services/missions.py`, whichever the source comparison proves is the real parity gap.

Blockers:

- None for this helper seam.
- The remaining consumer-path parity gap is still not proven from source in OpenZues, so the next turn should not widen past one exact consumer file before patching.

## Checkpoint 2026-04-14 parent session consumer inspection America/Chicago

Recovered context:

- Continued from the saved thread-session helper checkpoint instead of reopening Recall or rereading the ledger.
- Used the next bounded source path named there: one exact downstream OpenClaw consumer of `parentSessionKey`, then checked the matching OpenZues mission and launch-routing lookup paths.

Completed:

- Inspected OpenClaw `src/auto-reply/reply/session.ts` and verified that its `parentSessionKey` consumer is a session-store fork path, not a launch-route reuse lookup. The concrete behavior there is: when a thread session has a distinct parent session and that parent session store entry exists, OpenClaw can fork local session state from the parent before continuing the child thread session.
- Revalidated that OpenZues already covers the only source-backed mission continuity lookup that can receive a child `:thread:` session key today: [missions.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/missions.py) falls back from the child key to the parent base session key during thread reuse lookup.
- Confirmed that [launch_routing.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/launch_routing.py) does not currently emit or consume child `:thread:` session keys, so adding a parent-session fallback there on this evidence would be speculative rather than parity-backed.

Verified:

- Source inspection only on:
  `openclaw-main/src/auto-reply/reply/session.ts`
  `src/openzues/services/missions.py`
  `src/openzues/services/launch_routing.py`
- Bounded workspace check:
  `rg -n ":thread:|thread_id.*session_key|session_key.*thread_id|resolve_thread_session_keys\\(" src/openzues tests -g "*.py"`
  confirmed the live OpenZues child-thread session-key consumer remains `missions.py`, plus the new helper/tests added in the previous slice.

Next step:

- Leave the thread-session parent consumer seam closed unless a later OpenClaw parity pass introduces a real OpenZues session-store or child-thread routing surface that matches the source behavior.
- Next highest-leverage parity slice should move to the next unfinished OpenClaw domain named in the re-anchor trail after routing/session-key continuity, such as browser runtime, nodes, voice, or packaging, using one exact source file and one exact OpenZues target path.

Blockers:

- No blocker for the inspected seam itself.
- There is no verified one-to-one OpenZues contract today for the OpenClaw parent-session store fork behavior, so implementing it now would be speculative drift rather than source-backed parity.

## Checkpoint 2026-04-14 nodes voice packaging seam map America/Chicago

Recovered context:

- Continued from the post-routing checkpoint trail without reopening Recall or rereading the ledger.
- Used the next saved parity domains directly: first `nodes`, then a bounded `packaging` probe only after the nodes/voice contract proved already green.

Completed:

- Revalidated that the active OpenZues `nodes` and `voice` parity surface in this workspace is the gateway method policy contract, not a live gateway handler tree. OpenClaw `src/gateway/server-methods/nodes.ts` exists and is already reflected in OpenZues policy coverage, while `src/openzues/gateway/server-methods/nodes.py` does not exist because this repo has no corresponding handler module surface yet.
- Confirmed the OpenClaw `nodes.ts` browser-proxy mutation guard (`normalizeBrowserProxyPath`, `isPersistentBrowserProxyMutation`, `isForbiddenBrowserProxyMutation`) is embedded in the node handler runtime, but OpenZues currently has no matching node handler or browser-proxy invoke surface to patch one-to-one.
- Mapped the next packaging-adjacent OpenZues surface to desktop package discovery and environment diagnostics through [codex_desktop.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/codex_desktop.py) and [environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/environment.py), then compared that against OpenClaw `src/cli/update-cli/progress.ts`.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_gateway_method_policy.py -q` -> `16 passed in 0.48s`
- Source inspection only on:
  `openclaw-main/src/gateway/server-methods/nodes.ts`
  `openclaw-main/src/cli/update-cli/progress.ts`
  `src/openzues/services/gateway_method_policy.py`
  `src/openzues/services/codex_desktop.py`
  `src/openzues/services/environment.py`
- Bounded workspace probes confirmed:
  `src/openzues/gateway` has no file-backed handler surface today
  OpenZues contains no direct browser-proxy mutation or node handler implementation matching the OpenClaw runtime guard

Next step:

- Treat the nodes/voice gateway contract seam as source-backed complete in OpenZues unless a later parity pass introduces a real handler/runtime surface.
- Next smallest packaging slice: compare OpenClaw `src/cli/update-cli/progress.ts` failure-hint behavior against OpenZues desktop/environment diagnostics in `src/openzues/services/environment.py`, `src/openzues/services/codex_desktop.py`, and `tests/test_environment.py`, then land one exact operator-facing hint improvement only if the overlap is source-backed.

Blockers:

- No blocker for the verified nodes/voice contract seam itself.
- There is still no one-to-one OpenZues runtime target for the deeper OpenClaw node/browser mutation guard, so implementing that logic now would be speculative drift rather than parity.

## Checkpoint 2026-04-14 packaging diagnostic hint parity America/Chicago

Recovered context:

- Continued from the saved packaging slice instead of reopening Recall or rereading the ledger.
- Used the exact file pair named in the prior checkpoint: OpenClaw `src/cli/update-cli/progress.ts` versus OpenZues environment diagnostics in [environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/environment.py) with focused coverage in [test_environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_environment.py).

Completed:

- Landed one bounded operator-facing packaging hint improvement in [environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/environment.py): when `codex` is missing from PATH but Codex Desktop is installed locally, the `codex_cli` diagnostic now downgrades from a generic warning to actionable info and explicitly points the operator toward Desktop transport or Quick Connect to stage a runnable local bridge.
- Kept the improvement source-backed and narrow: the overlap with OpenClaw `progress.ts` was the style of recovery guidance, not package-manager state, so this slice improved the already existing OpenZues packaging/desktop recovery hint rather than inventing an updater contract that does not exist in this repo.
- Added a focused regression in [test_environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_environment.py) covering the installed-desktop + missing-PATH case.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_environment.py -q` -> `3 passed in 0.88s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src\\openzues\\services\\environment.py tests\\test_environment.py` -> passed

Next step:

- Stay within the packaging/desktop seam and compare one more exact OpenClaw packaging-status or recovery-hint file against OpenZues desktop/environment diagnostics before widening again.
- Preferred next slice: inspect whether OpenClaw `src/cli/update-cli/progress.ts` or one adjacent packaging-status file has another operator-facing failure hint that cleanly maps to OpenZues `codex_desktop_bridge` or `codex_desktop_install` diagnostics, then land at most one more hint or state detail with focused `tests/test_environment.py` coverage.

Blockers:

- None for this slice.
- The remaining packaging overlap is still only partial, so the next turn should keep to one exact OpenClaw packaging file and the existing OpenZues desktop/environment diagnostics surface instead of broadening into updater runtime work.

## Checkpoint 2026-04-14 desktop install source-kind parity America/Chicago

Recovered context:

- Continued from the saved packaging/desktop diagnostics seam instead of reopening Recall or rereading the ledger.
- Used one exact adjacent packaging-status file from OpenClaw, `src/cli/update-cli/status.ts`, and kept the OpenZues target bounded to [codex_desktop.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/codex_desktop.py), [environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/environment.py), and their focused tests.

Completed:

- Added an explicit desktop install source-kind contract to [codex_desktop.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/codex_desktop.py): `DesktopDiscovery` now records whether the discovered runtime came from the packaged desktop install, the latest desktop session spawn path, or a PATH fallback.
- Wired that source-kind into [environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/environment.py) so the `codex_desktop_install` diagnostic now reports a clearer install/status line such as `packaged desktop runtime`, which is the closest OpenZues counterpart to OpenClaw update-status install source reporting.
- Extended focused coverage in [test_codex_desktop.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_codex_desktop.py) and [test_environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_environment.py) so the packaged-runtime path is explicit in both discovery and diagnostics.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_codex_desktop.py tests\\test_environment.py -q` -> `6 passed in 0.67s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src\\openzues\\services\\codex_desktop.py src\\openzues\\services\\environment.py tests\\test_codex_desktop.py tests\\test_environment.py` -> passed

Next step:

- Stay in the same packaging/desktop seam and inspect one more exact OpenClaw packaging-status or recovery-hint file only if it still maps cleanly to the existing OpenZues desktop/environment diagnostics surface.
- Preferred next slice: compare whether OpenClaw packaging status exposes another source-of-install nuance or recovery hint that should surface in `codex_desktop_bridge` or `codex_desktop_session`, then land at most one more additive diagnostic detail with focused `tests/test_codex_desktop.py` and `tests/test_environment.py` coverage.

Blockers:

- None for this slice.
- The remaining overlap is still diagnostic-only; do not widen into updater runtime or package-manager execution unless a later source comparison proves a direct OpenZues contract.

## Checkpoint 2026-04-14 desktop session initialization detail parity America/Chicago

Recovered context:

- Continued from the saved packaging/desktop diagnostics seam instead of reopening Recall or rereading the ledger.
- Stayed within the already-open OpenClaw packaging-status comparison lane and the existing OpenZues desktop/environment diagnostics surface.

Completed:

- Tightened [environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/environment.py) so the `codex_desktop_session` diagnostic now makes the existing session initialization state explicit instead of only reporting transport and app-server version.
- The session detail now distinguishes a healthy desktop session that initialized Codex CLI from a partial desktop session that reached app-server reporting but did not finish CLI initialization.
- Added focused coverage in [test_environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_environment.py) for both the initialized and uninitialized desktop-session detail strings.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_environment.py -q` -> `4 passed in 0.62s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src\\openzues\\services\\environment.py tests\\test_environment.py` -> passed

Next step:

- Keep the next slice in the same packaging/desktop diagnostics seam and inspect at most one more exact OpenClaw packaging-status or recovery-hint file only if it still maps cleanly to `codex_desktop_bridge` or `codex_desktop_session`.
- Preferred next slice: surface one more additive state detail around staged bridge readiness or session provenance only if the comparison remains diagnostic-only and can be proved with focused `tests/test_environment.py` or `tests/test_codex_desktop.py` coverage.

Blockers:

- None for this slice.
- The remaining overlap is still diagnostic-only; do not widen into updater runtime, package-manager execution, or unrelated parity domains unless a later source comparison proves a direct OpenZues contract.

## Checkpoint 2026-04-14 desktop bridge provenance detail parity America/Chicago

Recovered context:

- Continued from the saved packaging/desktop diagnostics seam instead of reopening Recall or rereading the ledger.
- Stayed within the existing OpenZues desktop/environment diagnostics surface and reused the already-open packaging-status comparison lane.

Completed:

- Tightened [environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/environment.py) so the `codex_desktop_bridge` diagnostic now reports what OpenZues will stage the bridge from when no staged runtime exists yet.
- The pre-stage bridge detail now uses the desktop runtime provenance already tracked by `source_kind`, for example `from the packaged desktop runtime`, and it also carries the discovered source path as the diagnostic value.
- Added focused regression coverage in [test_environment.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_environment.py) for the installed-desktop + not-yet-staged case.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_environment.py -q` -> `4 passed in 1.15s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src\\openzues\\services\\environment.py tests\\test_environment.py` -> passed

Next step:

- Keep the next slice inside the same packaging/desktop diagnostics seam and inspect at most one more exact OpenClaw packaging-status or recovery-hint file only if it still maps cleanly to `codex_desktop_bridge` or `codex_desktop_session`.
- Preferred next slice: surface one more additive detail around session provenance or staged-bridge recovery only if it can be proved with focused `tests/test_environment.py` or `tests/test_codex_desktop.py` coverage.

Blockers:

- None for this slice.
- The remaining overlap is still diagnostic-only; do not widen into updater runtime, package-manager execution, or unrelated parity domains unless a later source comparison proves a direct OpenZues contract.

## Checkpoint 2026-04-14 device bootstrap normalizer parity America/Chicago

Recovered context:

- Re-entry stayed pinned to the saved `gateway bootstrap` / `method registry` anchor and took the already-named `device-bootstrap-profile` slice instead of reopening the contaminated replay tail.
- The OpenClaw source of truth for this slice is `openclaw-main/src/shared/device-bootstrap-profile.ts`, which keeps bootstrap-profile normalization pure and leaves the pairing default profile as a separate exported constant.

Completed:

- Matched OpenZues bootstrap-profile normalization to the OpenClaw contract by removing the implicit fallback from `src/openzues/services/device_bootstrap_profile.py`.
- Split the focused parity proof so the default pairing profile remains covered separately while normalization now proves the empty-input case directly in `tests/test_device_bootstrap_profile.py`.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_device_bootstrap_profile.py tests/test_gateway_bootstrap.py -q` -> `7 passed in 1.38s`

Next step:

- Keep the recovery lane narrow and compare the remaining gateway bootstrap profile handoff in `src/openzues/services/gateway_bootstrap.py` against OpenClaw onboarding/bootstrap usage for the first missing persisted field or normalization edge.

Blockers:

- None for this slice.

## Checkpoint 2026-04-14 forced-landing gateway policy proof America/Chicago

Completed:

- Stopped the reporting loop and kept scope pinned to the already-completed gateway method policy seam.
- Did not reopen Recall or widen the parity ledger after the landing guard fired.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` -> `8 passed in 0.09s`

## Checkpoint 2026-04-14 gateway bootstrap default profile parity America/Chicago

Completed:

- Kept the recovery lane pinned to the saved `gateway bootstrap` seam and landed the first remaining bootstrap-profile handoff in `src/openzues/services/gateway_bootstrap.py`.
- Matched OpenClaw bootstrap issuance behavior for the first saved gateway profile: when no bootstrap roles or scopes are supplied and no prior row exists, OpenZues now persists the pairing default profile instead of an empty profile.
- Added a focused regression in `tests/test_gateway_bootstrap.py` so the service boundary proves the persisted row keeps the default bootstrap roles/scopes even when the caller omits them.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_bootstrap.py -q` -> `5 passed in 2.69s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "persists_default_device_bootstrap_profile"` -> `1 passed, 63 deselected in 16.64s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src/openzues/services/gateway_bootstrap.py tests/test_gateway_bootstrap.py` -> passed

Next step:

- Stay on the same gateway bootstrap seam and compare the remaining OpenClaw bootstrap/pairing handoff for the next smallest missing field or policy edge, then only widen toward routing/session-key after that proof is locked.

Blockers:

- None for this slice.

Next smallest step:

- Compare OpenClaw `src/shared/device-bootstrap-profile.ts` to OpenZues `src/openzues/cli.py`, `src/openzues/services/onboarding.py`, and `src/openzues/services/gateway_bootstrap.py`.
- Land exactly one missing bootstrap-profile field or normalization rule, then run the tightest exact verification for that slice before any broader routing/session-key work.

Blockers:

- None in this turn; this was a proof-and-checkpoint landing only.

## Checkpoint 2026-04-14 CLI bootstrap profile parity America/Chicago

Recovered context:

- Stayed on the saved `device-bootstrap-profile` seam from the parity re-anchor instead of reopening the contaminated replay tail.
- Compared OpenClaw `src/shared/device-bootstrap-profile.ts` to the named OpenZues handoff points and found the concrete gap in `src/openzues/cli.py`: the CLI bootstrap builder never forwarded the pairing default `bootstrap_roles` and `bootstrap_scopes`.

Completed:

- Patched `src/openzues/cli.py` so `_build_bootstrap_payload()` stamps the OpenClaw pairing bootstrap profile into every CLI bootstrap payload by default.
- Added a focused CLI regression proof in `tests/test_cli.py` that runs `setup bootstrap`, then `gateway show`, and asserts the saved gateway bootstrap contract keeps `["node", "operator"]` plus the OpenClaw operator handoff scopes.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "bootstrap_can_stage_mempalace_from_cli or persists_default_device_bootstrap_profile"` -> `2 passed, 62 deselected in 20.66s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "setup_endpoint_reports_reentrant_posture_after_bootstrap or gateway_bootstrap_endpoint_updates_saved_launch_profile"` -> `2 passed, 144 deselected in 8.99s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src/openzues/cli.py tests/test_cli.py` -> passed

Next step:

- Keep the parity lane narrow and compare the remaining non-CLI gateway bootstrap handoff against OpenClaw onboarding/bootstrap usage for the next missing persisted field or normalization edge.
- After the bootstrap-profile handoff is exhausted, widen toward routing/session-key policy from the parity re-anchor.

Blockers:

- None for this slice.

## Checkpoint 2026-04-14 bootstrap-profile seam pin America/Chicago

Completed:

- Took one bounded inspection step against the next parity seam named in the prior checkpoint: OpenClaw `src/shared/device-bootstrap-profile.ts` versus OpenZues bootstrap-related entry points.
- Confirmed the OpenClaw source-of-truth bootstrap profile contract is centered on normalized `roles` and `scopes`, plus a pairing setup default that grants `operator.approvals`, `operator.read`, `operator.talk.secrets`, and `operator.write`.

Verified:

- Inspected `C:/Users/skull/OneDrive/Documents/openclaw-main/src/shared/device-bootstrap-profile.ts` and matched the relevant OpenZues touchpoints with exact bounded searches in `src/openzues/services/gateway_bootstrap.py`, `src/openzues/services/onboarding.py`, and `src/openzues/cli.py`.

Next smallest step:

- Read only the exact OpenZues bootstrap payload builder and save path lines needed to answer one question: where `roles` and `scopes` should be normalized and persisted to mirror OpenClaw's bootstrap profile contract.
- Then land exactly one missing normalization rule or default-scope field with a focused test for that bootstrap slice.

Blockers:

- The single bounded command in this turn established the source contract and the target files, but it did not expose enough exact target-line context to safely edit without a second turn.

Blockers:

- None. The remaining risk is future ledger contamination below this heading, and the mission governor now explicitly pushes back on that path.

## Checkpoint 2026-04-14 gateway bootstrap backfill profile parity America/Chicago

Recovered context:

- Resumed from the saved parity re-anchor and the `device-bootstrap-profile` seam instead of reopening the contaminated replay tail.
- Kept the slice pinned to OpenClaw `openclaw-main/src/shared/device-bootstrap-profile.ts` and the exact OpenZues backfill handoff in `src/openzues/services/gateway_bootstrap.py`.

Completed:

- Landed the first missing persisted bootstrap-profile field on the gateway backfill path by saving the OpenClaw pairing bootstrap profile instead of null `bootstrap_roles` / `bootstrap_scopes`.
- Tightened the existing dashboard backfill proof in `tests/test_app.py` so the recovered gateway/profile views must carry the persisted pairing roles and operator scopes after backfill.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "dashboard_backfills_gateway_bootstrap_from_existing_quickstart_artifacts"` -> `1 passed, 145 deselected in 5.55s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src/openzues/services/gateway_bootstrap.py tests/test_app.py` -> passed

Next step:

- Stay on the bootstrap-profile seam and compare OpenClaw bootstrap profile usage against OpenZues `src/openzues/cli.py` `_build_bootstrap_payload` and `src/openzues/services/onboarding.py` to see whether quickstart/onboarding should explicitly seed the pairing profile when callers omit bootstrap roles/scopes.
- After that, widen toward the previously queued routing/session-key policy seam only if the bootstrap-profile path is clean.

Blockers:

- None for this slice.

## Checkpoint 2026-04-14 onboarding bootstrap profile parity America/Chicago

Recovered context:

- Re-entered from the saved OpenClaw parity re-anchor and stayed on the bounded `device-bootstrap-profile` / gateway bootstrap seam instead of reopening the contaminated replay tail.
- The remaining non-CLI gap lived on direct onboarding/bootstrap callers: OpenZues CLI already seeded the pairing profile, but `/api/onboarding/bootstrap` could still omit `bootstrap_roles` / `bootstrap_scopes` and drift away from OpenClaw's pairing default.

Completed:

- Patched `src/openzues/services/onboarding.py` so direct onboarding/bootstrap calls now seed the OpenClaw pairing bootstrap profile when callers omit both bootstrap lists.
- Patched `src/openzues/services/setup.py` so the saved wizard-session read path surfaces the stored bootstrap profile instead of collapsing it back to empty lists during setup inspection.
- Tightened `tests/test_app.py` so the existing setup re-entry proof now asserts both the saved gateway bootstrap profile and the saved wizard session keep the OpenClaw pairing roles and operator handoff scopes.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "setup_endpoint_reports_reentrant_posture_after_bootstrap"` -> `1 passed, 145 deselected in 6.29s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src/openzues/services/onboarding.py src/openzues/services/setup.py tests/test_app.py` -> passed

Next step:

- Treat the bootstrap-profile seam as clean across CLI, onboarding API, gateway save, and gateway backfill paths.
- Widen to the queued routing/session-key parity seam from the re-anchor, starting with one bounded comparison between the relevant OpenClaw routing/session-key source and OpenZues `src/openzues/services/launch_routing.py`.

Blockers:

- None for this slice.

## Checkpoint 2026-04-14 routing session-key punctuation parity America/Chicago

Recovered context:

- Stayed on the saved `routing/session-key` seam after the bootstrap-profile handoff and kept the slice pinned to OpenClaw `openclaw-main/src/routing/session-key.ts` plus OpenZues `src/openzues/services/launch_routing.py`.
- Verified the concrete OpenClaw contract first: routing lowercases channel and peer tokens, but only account ids are sanitized.

Completed:

- Patched `src/openzues/services/launch_routing.py` so launch-route conversation targets preserve punctuated peer ids while still sanitizing account ids to the OpenClaw account-id contract.
- Added focused proof in `tests/test_launch_routing.py` for a punctuated channel peer id and kept an existing app-level launch-handoff route pack green.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_launch_routing.py -q` -> `1 passed in 0.42s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "setup_launch_handoff_keeps_workspace_affinity_session_key_across_lane_churn"` -> `1 passed, 145 deselected in 2.72s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src/openzues/services/launch_routing.py tests/test_launch_routing.py` -> passed

Next step:

- Stay on the routing/session-key parity seam and compare the next launch-handoff continuity rule from OpenClaw `src/routing/session-key.ts` against OpenZues `src/openzues/services/session_keys.py` and mission reuse paths.
- Keep the next slice bounded to one missing rule plus focused verification before widening beyond routing/session-key.

Blockers:

- None for this slice.

## Checkpoint 2026-04-14 routing main-session alias parity America/Chicago

Recovered context:

- Stayed on the saved `routing/session-key` seam and narrowed the next rule to OpenClaw default-agent main-session canonicalization in `openclaw-main/src/routing/session-key.ts`.
- Checked the OpenZues reuse boundary in `src/openzues/services/missions.py` plus `src/openzues/database.py` and confirmed lookup was lowercasing only, so legacy `main` rows would not match canonical `agent:main:main` continuity.

Completed:

- Added `canonicalize_session_key()` and `session_key_lookup_aliases()` to `src/openzues/services/session_keys.py`.
- Wired mission create/reuse to canonicalize bare `main` into `agent:main:main` and taught database lookup to search the legacy `main` alias alongside the canonical key for continuity.
- Added focused coverage in `tests/test_session_keys.py`, `tests/test_missions.py`, and `tests/test_app.py`.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_session_keys.py -q` -> `4 passed in 0.42s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_missions.py -q -k "main_session_alias"` -> `1 passed, 130 deselected in 0.79s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "default_agent_main_session_alias"` -> `1 passed, 146 deselected in 2.25s`
- `.\\.venv\\Scripts\\python.exe -m ruff check --extend-ignore E501 src/openzues/services/session_keys.py src/openzues/services/missions.py src/openzues/database.py tests/test_session_keys.py tests/test_missions.py tests/test_app.py` -> passed

Next step:

- Stay on the routing/session-key parity seam and compare the next OpenClaw continuity rule from `src/routing/session-key.ts`, likely already-qualified agent-key handling or thread-suffix continuity, against OpenZues session-key normalization and mission reuse.
- Keep the next slice bounded to one rule plus focused service/API coverage before widening beyond routing/session-key.

Blockers:

- None for this slice.

## Checkpoint 2026-04-14 routing main-session alias verification landing America/Chicago

Completed:

- Stopped broadening and treated the saved `routing/session-key` checkpoint as the anchor for this reflex turn.
- Reverified the just-landed default-agent main-session continuity slice without reopening the parity ledger or widening into a new rule.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_session_keys.py tests/test_missions.py tests/test_app.py -q -k "main_session_alias or default_agent_main_session_alias"` -> `2 passed, 280 deselected in 4.30s`

Next smallest step:

- Stay on the `routing/session-key` seam and compare one next OpenClaw continuity rule, preferably already-qualified agent-key handling or thread-suffix continuity, against OpenZues `src/openzues/services/session_keys.py` and mission reuse.
- Keep the next slice to one rule plus exact service/API verification before widening beyond routing/session-key.

Blockers:

- None for this landing turn.

## Recovery checkpoint 2026-04-13 gateway bootstrap verification America/Chicago

Recovered context:

- Re-entered from the parity re-anchor above and stayed on the bounded `gateway bootstrap` seam instead of reopening contaminated replay notes.
- Used `openclaw-main/src/wizard/setup.gateway-config.ts` as the source-side bootstrap contract reference and compared it against `src/openzues/services/gateway_bootstrap.py` to confirm the target still exposes a real persisted bootstrap surface rather than a stub.

Completed:

- Verified the existing OpenZues gateway bootstrap slice is still intact end to end across onboarding bootstrap, saved gateway bootstrap state, dashboard backfill, reset cleanup, and Hermes launch-summary shaping.
- Did not widen into method-registry or routing/session-key work after the governor warning because no single missing bootstrap gap was isolated from the bounded source/target read.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "onboarding_bootstrap or gateway_bootstrap or dashboard_backfills_gateway_bootstrap or dashboard_bootstraps_remote_access_foundations or setup_endpoint_reports_reentrant_posture_after_bootstrap or setup_reset_full_removes_bootstrap_managed_resources or setup_reset_full_removes_bootstrap_managed_mempalace_loop or hermes_profile_shapes_bootstrap_launch_draft or dashboard_bootstraps_remote_access_foundations"` -> `11 passed, 130 deselected in 20.82s`

Next step:

- Leave bootstrap closed for now and take the next smallest parity slice named in the re-anchor: `method registry`.
- Lock that seam with one bounded source/target pair before editing, preferably a concrete registry entry or gateway method exposure gap that can be verified with one exact test file.

Blockers:

- No bootstrap blocker remains from this turn.
- The next cycle still needs a narrower method-registry source anchor before code changes start.

## Recovery checkpoint 2026-04-14 method registry reserved admin policy America/Chicago

Recovered context:

- Re-entered from the `Recovery checkpoint 2026-04-13 parity re-anchor refresh America/Chicago` anchor and stayed on the bounded `method registry` seam instead of reopening contaminated replay notes.
- Used `C:\Users\skull\OneDrive\Documents\openclaw-main\src\shared\gateway-method-policy.ts` as the source-side contract for reserved gateway method policy and compared it against `src/openzues/services/gateway_capability.py` plus the existing gateway capability CLI/API surfaces in OpenZues.

Completed:

- Landed the next method-registry parity slice by adding `src/openzues/services/gateway_method_policy.py`, mirroring OpenClaw's reserved admin gateway prefixes for `exec.approvals.*`, `config.*`, `wizard.*`, and `update.*`.
- Enriched `GatewayCapabilityMethodCatalogView` and the gateway capability inventory builder so OpenZues now classifies reserved admin methods, exposes the enforced scope as `operator.admin`, and carries the reserved-admin summary through `/api/gateway/capability`, `/api/dashboard`, and the CLI gateway capability emitter.
- Added focused API and CLI proofs that reserved admin methods are surfaced as a distinct posture rather than being mixed into the generic method inventory with no policy signal.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "gateway_capability_classifies_reserved_admin_methods or gateway_capability_surfaces_connected_lane_inventory"` -> `1 passed, 141 deselected in 6.30s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "callable_method_inventory or reserved_admin_methods"` -> `2 passed, 61 deselected in 1.56s`
- `.\\.venv\\Scripts\\python.exe -m ruff check src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_capability.py src/openzues/schemas.py src/openzues/cli.py tests/test_app.py tests/test_cli.py` -> passed

Next step:

- Keep the next slice inside `method registry` before widening elsewhere: mirror the remaining OpenClaw operator-scope classification groups from `src/gateway/method-scopes.ts` so OpenZues can distinguish read, write, approvals, and pairing methods instead of only flagging reserved admin prefixes.
- If that classification lands cleanly, the next best parity seam after method-registry closure is the previously deferred routing/session-key policy path.

Blockers:

- None on this slice. The current gap is design bandwidth, not missing runtime primitives: OpenZues now has the method-catalog surface needed for fuller scope classification.

## Recovery checkpoint 2026-04-14 method registry closure verification America/Chicago

Recovered context:

- Re-entered from the `Recovery checkpoint 2026-04-14 method registry reserved admin policy America/Chicago` anchor and kept the turn bounded to `method registry`.
- Compared `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\method-scopes.ts` against `src/openzues/services/gateway_method_policy.py` plus the existing API proof in `tests/test_app.py`.

Completed:

- Verified that the remaining OpenClaw operator-scope classification groups were already mirrored in the target worktree; `gateway_method_policy.py` already carries the explicit read, write, approvals, pairing, admin, reserved-admin, and node-role mappings named by the source contract.
- Verified that the method-registry parity slice is already closed at the API surface, so no production edit was required on this recovery turn.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` -> `3 passed in 0.04s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "gateway_capability_classifies_operator_scopes_and_reserved_admin_methods"` -> `1 passed, 141 deselected in 4.72s`

Next step:

- Leave `method registry` closed and move to the next bounded parity seam from the prior handoff: `routing/session-key` policy.
- Lock that seam against one source/target pair before editing, preferably the OpenClaw session-key policy source and the matching OpenZues routing/session launch surface.

Blockers:

- None. The next cycle can start directly on `routing/session-key` without reopening gateway bootstrap or method-registry inventory work.

## Recovery checkpoint 2026-04-14 method registry seam
- Completed: locked the OpenClaw method-registry seam without reopening the ledger and tightened `tests/test_gateway_method_policy.py` so OpenZues now extracts handler names directly from `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods\nodes.ts`, `nodes-pending.ts`, and `voicewake.ts` before asserting the current node, pairing, read/write, and node-role scope mappings.
- Verified claim: the current OpenClaw node and voice handler surface is fully covered by the OpenZues gateway method policy for this seam.
- Verification:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q`
  - `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -k gateway_capability_classifies_operator_scopes_and_reserved_admin_methods -q`
  - `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -k emit_gateway_capability_surfaces_reserved_admin_methods -q`
- Remaining: broader OpenClaw parity domains are still open beyond the method registry, especially the first production slice that turns the already-classified node/voice/canvas/browser methods into a concrete OpenZues runtime or control-plane surface.
- Next best slice: inspect one concrete source-of-truth file under `openclaw-main/src/gateway` for the smallest unimplemented runtime surface behind the classified methods, with `node.pending` or `voicewake` as the next likely bounded seam.

## Recovery checkpoint 2026-04-14 method registry reserved prefixes
- Completed: extended the method-registry parity lock to cover OpenClaw's remaining reserved admin prefixes by adding source-anchored assertions for `config.patch`, `exec.approvals.node.set`, `update.run`, and `wizard.status` in `tests/test_gateway_method_policy.py`, plus an end-to-end gateway capability/dashboard proof in `tests/test_app.py`.
- Verified claim: OpenZues classifies the unscoped reserved OpenClaw registry methods as `operator.admin`, preserves them in the gateway capability inventory, and still leaves `status` and `node.pending.drain` in their non-admin buckets.
- Verification:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q`
  - `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "gateway_capability_classifies_operator_scopes_and_reserved_admin_methods or gateway_capability_tracks_reserved_admin_registry_prefixes_end_to_end"`
  - `.\\.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q -k "emit_gateway_capability_surfaces_reserved_admin_methods"`
- Remaining: the method-registry seam is now tighter, but it is still only policy and inventory proof; the next parity win should convert one classified gateway surface into a real OpenZues runtime path.
- Next best slice: inspect one concrete `openclaw-main/src/gateway/server-methods/*.ts` source file for `node.pending` or `voicewake`, isolate the smallest missing runtime/control-plane behavior in OpenZues, implement it end to end, and rerun the focused app plus contract proofs.

## Recovery checkpoint 2026-04-14 gateway method policy proof
- Completed: Verified the in-flight gateway method policy seam remains wired through `src/openzues/services/gateway_method_policy.py` into `src/openzues/services/gateway_capability.py`.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed (`5 passed`) and `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "gateway_capability_classifies_operator_scopes_and_reserved_admin_methods or gateway_capability_tracks_reserved_admin_registry_prefixes_end_to_end"` passed (`2 passed, 141 deselected`).
- Remaining: The broader OpenClaw parity lane is still open; this recovery turn did not widen scope beyond proving the method-policy and gateway-capability contract already present in the worktree.
- Next: Land the pending method-policy edit set cleanly, then run the wider contract pack if the schema, CLI, dashboard, or API surfaces changed: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`, `node --check src/openzues/web/static/app.js`, and `.\\.venv\\Scripts\\python.exe -m compileall src/openzues`.

## Recovery checkpoint 2026-04-14 reporting-loop arrest
- Completed: Stopped scope growth and held the lane on the already implemented gateway method-policy parity seam.
- Verified: Existing focused proof remains the latest concrete evidence on this recovery path: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` -> `5 passed`; `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "gateway_capability_classifies_operator_scopes_and_reserved_admin_methods or gateway_capability_tracks_reserved_admin_registry_prefixes_end_to_end"` -> `2 passed, 141 deselected`.
- Next smallest step: Run the broader contract pack only if the pending worktree changes in schema, CLI, dashboard, or API are the slice being landed next.
- Blockers: None newly discovered in this forced-landing turn.

## Recovery checkpoint 2026-04-14 routing session-key lane churn proof America/Chicago
- Recovered context: Re-entered from the 2026-04-13 parity re-anchor and kept the turn inside `routing/session-key`, using `C:\Users\skull\OneDrive\Documents\openclaw-main\src\config\sessions\session-key.ts` as the source-side canonical-session contract and `src/openzues/services/launch_routing.py` plus `tests/test_app.py` as the target seam.
- Completed: Added a focused API proof in `tests/test_app.py` that a `workspace_affinity` launch keeps the same routed session key when the preferred workspace lane changes, while correctly refusing stale thread reuse after the route resolves to a different lane.
- Verified claim: OpenZues now has an explicit parity proof that workspace-affinity routing preserves session identity across lane churn without incorrectly reviving a thread from the prior lane.
- Verification:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "keeps_workspace_affinity_session_key_across_lane_churn"` -> `1 passed, 144 deselected in 4.97s`
- Remaining: `routing/session-key` still needs its next production slice if source-side OpenClaw behavior exposes a concrete normalization or reuse policy that OpenZues does not yet implement; this turn only closed the missing proof for the current behavior.
- Next best slice: inspect one narrower OpenClaw source pair under `src/config/sessions/` or `src/routing/` for the smallest still-missing session-key normalization rule, preferably explicit-session normalization or thread-aware routing, then land it with one matching OpenZues launch-routing or follow-up test.
- Blockers: None.

## Recovery checkpoint 2026-04-14 routing session-key explicit normalization America/Chicago
- Recovered context: Stayed on the existing `routing/session-key` anchor after the lane-churn proof and compared OpenClaw explicit-session normalization in `C:\Users\skull\OneDrive\Documents\openclaw-main\src\config\sessions\explicit-session-key-normalization.ts` against OpenZues mission ingress in `src/openzues/schemas.py` and mission reuse via `tests/test_app.py`.
- Completed: Normalized explicit mission `session_key` values at OpenZues mission ingress so mixed-case or padded keys are canonicalized before storage and thread reuse lookup, then added an API proof that a follow-on mission reuses the saved thread even when the caller sends `session_key` with casing and whitespace drift.
- Verified claim: OpenZues now preserves thread continuity for explicit session keys even when the inbound mission payload is not already canonicalized, which closes the smallest concrete normalization gap surfaced by the OpenClaw session-key source seam.
- Verification:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "normalizes_explicit_session_key_for_thread_reuse"` -> `1 passed, 145 deselected in 3.66s`
- Remaining: `routing/session-key` still has open parity room beyond this adapter-neutral normalization step, especially if OpenClaw exposes a smaller thread-aware routing or explicit session-id fallback rule that OpenZues can map onto its control plane without importing channel-runtime breadth.
- Next best slice: inspect one exact OpenClaw source seam around `src/commands/agent/session.ts` or adjacent routing helpers for a thread-aware explicit-session fallback that can map cleanly onto `src/openzues/services/missions.py` or `src/openzues/services/followups.py`, then land one focused reuse rule with an exact API test.
- Blockers: None.

## Checkpoint 2026-04-14 Recovery lane 019d8b74-3311-7703-816d-b2f696818eea
- Completed: resumed from Recall without reopening the parity ledger and kept the scope pinned to the recovered `gateway bootstrap` seam.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_gateway_method_policy.py -q` passed (`8 passed in 0.06s`), so the OpenZues gateway method policy proof for the recovered seam is still green.
- Remains: the broader gateway bootstrap parity slice still needs a source-of-truth comparison between OpenClaw `src/gateway/server-plugin-bootstrap.ts` and `src/gateway/client-bootstrap.ts` versus OpenZues `src/openzues/services/gateway_bootstrap.py` and the related dashboard contract.
- Next best slice: compare the OpenClaw bootstrap source files against the OpenZues gateway bootstrap service/dashboard path, land any missing contract wiring, then rerun the focused gateway pack plus `tests/test_app.py` if the dashboard/schema contract moves.

## Checkpoint 2026-04-14 Recovery lane 019d8bba-9e22-74e1-9a10-c2f6903052de
- Completed: re-entered through Recall on the saved `gateway bootstrap` seam and took the bounded recovery step of re-verifying the exact gateway method-policy contract instead of reopening source inventory or widening scope.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_gateway_method_policy.py -q` passed (`8 passed in 0.05s`), confirming the recovered seam still holds in the current worktree.
- Remains: the highest-leverage unfinished parity slice is still the OpenClaw bootstrap comparison between `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-plugin-bootstrap.ts` and `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\client-bootstrap.ts` versus OpenZues `src/openzues/services/gateway_bootstrap.py` and any coupled dashboard contract surface.
- Next best slice: diff that exact bootstrap source seam, implement any missing OpenZues contract wiring end to end, then rerun the focused gateway pack and `tests/test_app.py` if the bootstrap/dashboard contract changes.

## Checkpoint 2026-04-14 recovery lane

- Completed: re-anchored on the saved `gateway bootstrap` / `method registry` seam without reopening the parity ledger body, then reran the exact focused proof already tied to that seam.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` (`8 passed`).
- Concrete claim locked: the OpenZues gateway method policy still matches the saved OpenClaw operator-scope and node-role registry expectations for this seam.
- Remaining: the next missing parity slice still needs to move forward from the already named gateway-adjacent backlog instead of re-reading the ledger.
- Next best slice: compare OpenZues routing/session-key behavior against `C:\\Users\\skull\\OneDrive\\Documents\\openclaw-main\\src\\routing\\session-key.ts`, land the smallest missing contract, and rerun the exact seam proof plus the required broader app/dashboard pack if the contract surface changes.

## Checkpoint 2026-04-14 recovery lane 019d8bf7-8cc1-7e61-af75-168003f6c8ee

- Completed: used OpenZues Recall to re-anchor on the saved `browser runtime` checkpoint trail, then spent this recovery turn on one bounded broader-surface verification step only.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q --maxfail=1` did not complete within the 123s command window and terminated with `OSError: [Errno 22] Invalid argument` while flushing pytest stdout.
- Concrete claim locked: the recovery lane still does not have a clean broader `tests/test_app.py` proof for the saved browser-runtime/control-plane parity seam, so that surface remains unverified.
- Remaining: no production code changed in this turn; the blocker is still verification-path behavior for the broader app surface rather than a newly identified source/target parity delta.
- Next best slice: rerun `tests/test_app.py` through a capture-safe path that preserves stdout, isolate whether the stall is a real app regression or a harness/console issue, and only then resume the next missing parity implementation seam.

## Recovery checkpoint 2026-04-14 gateway bootstrap verification
- Completed: resumed from the saved `gateway bootstrap` / `method registry` seam without reopening the parity ledger, re-read only `tests/test_gateway_method_policy.py` and `src/openzues/services/gateway_method_policy.py`, and confirmed the OpenZues policy surface still matches the recovered parity slice.
- Verified: `./.venv/Scripts/python.exe -m pytest tests/test_gateway_method_policy.py -q` -> `8 passed in 0.19s`.
- Remaining: broader OpenClaw parity work is still open beyond this already-landed gateway policy seam; the next cycle should take the next unfinished parity domain from the existing ledger anchor instead of rebuilding inventory.
- Next best slice: use the saved parity anchor to pick one concrete unfinished domain after `gateway bootstrap` / `method registry`, implement that slice end to end, then rerun the exact seam proof plus the broader contract pack if the change touches gateway or dashboard contracts.

## Recovery checkpoint 2026-04-14 broader gateway contract proof blocked
- Completed: stayed anchored to the saved `gateway bootstrap` / `method registry` recovery seam and spent the single bounded follow-up step on the required broader surface proof instead of reopening the parity ledger.
- Verified: focused seam proof from the prior checkpoint still stands at `./.venv/Scripts/python.exe -m pytest tests/test_gateway_method_policy.py -q` -> `8 passed in 0.19s`.
- Blocker: `./.venv/Scripts/python.exe -m pytest tests/test_app.py -q --maxfail=1` timed out after 124042 ms on this recovery turn, so the broader app-level confirmation is still unresolved.
- Next smallest step: rerun `tests/test_app.py` with a longer timeout or a tighter in-file target, then checkpoint that broader proof before opening a new parity seam.

## Recovery checkpoint 2026-04-14 broader gateway contract proof resolved
- Completed: kept the lane pinned to the recovered `gateway bootstrap` / `method registry` seam and cleared the outstanding broader-proof blocker without widening into a new parity domain.
- Verified: `./.venv/Scripts/python.exe -m pytest tests/test_gateway_method_policy.py -q` -> `8 passed in 0.11s`.
- Verified: `./.venv/Scripts/python.exe -m pytest tests/test_app.py -q --maxfail=1` -> `146 passed in 143.37s (0:02:23)`.
- Remaining: no production code changed in this turn; the saved gateway bootstrap and method-registry parity slice is now reverified at both the exact seam and broader app surface.
- Next smallest step: use the existing parity anchor to compare OpenClaw `src/shared/device-bootstrap-profile.ts` against OpenZues `src/openzues/cli.py`, `src/openzues/services/onboarding.py`, and `src/openzues/services/gateway_bootstrap.py`, then land exactly one missing bootstrap-profile normalization or persisted field with focused verification before widening toward routing/session-key work.

## Recovery checkpoint 2026-04-14 routing session-key reverify
- Completed: stayed anchored on the recovered `routing/session-key` seam, re-read only the OpenZues launch-route session-key builder and the OpenClaw routing session-key source, and revalidated that OpenZues still preserves stable workspace-affinity launch keys and saved-thread reuse across lane churn.
- Verified: [launch_routing.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/launch_routing.py:500) builds deterministic `launch:mode:...` session keys that retain task/project/operator/channel identity and only pin `lane:` for `task_lane` and `saved_lane`, which matches the current parity checkpoint intent for reusable launch sessions.
- Verified: `./.venv/Scripts/python.exe -m pytest tests/test_app.py::test_setup_launch_handoff_keeps_workspace_affinity_session_key_across_lane_churn tests/test_database.py::test_get_latest_mission_by_session_key_prefers_active_session tests/test_missions.py::test_create_reuses_saved_thread_from_session_key -q` -> `3 passed in 6.77s`.
- Remaining: no production code changed in this recovery turn; broader OpenClaw parity work is still open beyond the already-landed `routing/session-key` slice.
- Next best slice: compare OpenClaw `src/routing/resolve-route.ts` and adjacent browser/control-route handoff behavior against OpenZues [launch_routing.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/launch_routing.py:130), [missions.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/missions.py:1), and [app.js](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/web/static/app.js:1), then land exactly one missing route-resolution or handoff contract delta with a focused app/database/missions proof pack.

## Recovery checkpoint 2026-04-14 resolve-route source anchor
- Completed: used the saved checkpoint’s named next seam directly and inspected only OpenClaw [resolve-route.ts](/C:/Users/skull/OneDrive/Documents/openclaw-main/src/routing/resolve-route.ts:40) as the source-of-truth contract for the next parity slice.
- Verified: the source contract clearly requires route resolution to produce `sessionKey`, `mainSessionKey`, and `lastRoutePolicy`, with inbound updates targeting `mainSessionKey` when policy is `main` and the active `sessionKey` otherwise ([resolve-route.ts](/C:/Users/skull/OneDrive/Documents/openclaw-main/src/routing/resolve-route.ts:65)).
- Remaining: this reflex turn did not widen into OpenZues implementation edits, so parity is still unverified for the `lastRoutePolicy` / inbound-last-route portion of the route-resolution contract.
- Blocker: none; the next comparison target is now pinned to one contract delta instead of the broader routing surface.
- Next smallest step: compare OpenClaw [resolve-route.ts](/C:/Users/skull/OneDrive/Documents/openclaw-main/src/routing/resolve-route.ts:93) route outputs against OpenZues [launch_routing.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/launch_routing.py:130) and [missions.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/missions.py:1), then implement exactly one missing `main-session` or `last-route` persistence/handoff field with focused verification.

## Recovery checkpoint 2026-04-14 gateway bootstrap verification
- Completed: re-anchored through OpenZues Recall on the saved `gateway bootstrap` seam and spent the bounded recovery step on the exact focused parity proof instead of reopening the ledger or widening scope.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_method_policy.py -q` -> `9 passed in 0.05s`, confirming the current OpenZues gateway method policy contract still matches the saved bootstrap / method-registry checkpoint target covered by [tests/test_gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py:1) and [gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py:1).
- Remaining: no production code changed in this recovery turn, so any unported OpenClaw gateway bootstrap or handler-registry deltas beyond the existing policy mirror are still open.
- Blocker: none; the seam is still live and the exact proof file is green.
- Next smallest step: compare OpenClaw [server-methods-list.ts](/C:/Users/skull/OneDrive/Documents/openclaw-main/src/gateway/server-methods-list.ts:1) and the handler registries referenced by [tests/test_gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py:25) against [gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py:1), then land exactly one missing bootstrap or method-registry delta and rerun `tests/test_gateway_method_policy.py` plus the broader app/dashboard pack if that contract changes.

## Recovery checkpoint 2026-04-14 gateway bootstrap seam reverify America/Chicago
- Completed: reused OpenZues Recall on the saved `gateway bootstrap parity` anchor, then spent the bounded repo step on the owned OpenZues files instead of reopening the ledger or broadening into unrelated parity seams.
- Verified: `rg -n "method_registry|gateway bootstrap|bootstrap|register" src/openzues/services/gateway_bootstrap.py tests/test_gateway_method_policy.py` confirmed the active seam is still pinned to [gateway_bootstrap.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_bootstrap.py:153) and [tests/test_gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py:85), including the `wizard.bootstrap` bootstrap-policy assertions; `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_method_policy.py -q` then passed with `9 passed in 0.05s`.
- Remaining: this recovery turn verified the existing OpenZues bootstrap / method-policy contract only; it did not yet compare the OpenClaw source-of-truth registries or port any additional gateway bootstrap deltas.
- Blocker: none.
- Next smallest step: read OpenClaw [server-methods-list.ts](/C:/Users/skull/OneDrive/Documents/openclaw-main/src/gateway/server-methods-list.ts:1) and the corresponding OpenZues registry/policy files, land one missing registry/bootstrap delta if found, and rerun `tests/test_gateway_method_policy.py` plus the broader contract pack if that delta changes shared gateway/dashboard wiring.

## Recovery checkpoint 2026-04-14 forced landing gateway registry anchor America/Chicago
- Completed: used the saved checkpoint's named next seam directly and spent the single bounded repo command on a source-of-truth vs target comparison between OpenClaw [server-methods-list.ts](/C:/Users/skull/OneDrive/Documents/openclaw-main/src/gateway/server-methods-list.ts:1) and OpenZues [gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py:1).
- Verified: `rg -n "wizard\.bootstrap|wizard\.status|setup\.session|gateway|doctor|continue|status" C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods-list.ts src\openzues\services\gateway_method_policy.py` showed OpenClaw still declares `wizard.status` at [server-methods-list.ts](/C:/Users/skull/OneDrive/Documents/openclaw-main/src/gateway/server-methods-list.ts:47), while the same bounded probe surfaced no `wizard.status` or `wizard.bootstrap` entries in [gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py:1). The previously verified focused proof for the existing policy seam remains green in [tests/test_gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py:1).
- Next smallest step: inspect the exact OpenClaw `wizard.*` classification shape and port one missing gateway-method-policy delta, starting with `wizard.status` if the source file confirms it belongs in the reserved/admin mirror, then rerun `tests/test_gateway_method_policy.py -q`.
- Blockers: none; the slice is narrowed to a concrete `wizard.*` source/target gap candidate.

## Recovery checkpoint 2026-04-14 resolve-route main-session handoff America/Chicago

### Recovered context

- The saved gateway-policy seam was already green in this worktree, so the next trustworthy parity anchor was the `resolve-route` contract pinned at [resolve-route.ts](/C:/Users/skull/OneDrive/Documents/openclaw-main/src/routing/resolve-route.ts:40).
- OpenClaw requires resolved routes to surface both `sessionKey` and `mainSessionKey`, plus a `lastRoutePolicy` that distinguishes direct-main reuse from per-session routing.

### Completed

- Added `main_session_key` and `last_route_policy` to OpenZues [LaunchRouteView](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/schemas.py:1348) so route handoffs now expose the same route-shape concepts as the OpenClaw source seam.
- Updated [LaunchRoutingService.describe](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/launch_routing.py:221) to derive a stable main-session key by rebuilding the route key without lane pinning, then mark `last_route_policy` as `main` when the active route already collapses to that key and `session` when the route stays lane-specific.
- Surfaced the new fields in the operator UI route card via [app.js](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/web/static/app.js:1707), showing the main-session key only when it differs from the active per-lane session and adding a last-route policy pill.
- Locked the contract with focused API proofs in [tests/test_app.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_app.py:1417) and [tests/test_app.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_app.py:2431) so both task-lane and workspace-affinity launch shapes stay covered.

### Verification

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py::test_onboarding_bootstrap_creates_first_run_bundle_and_launch_draft tests/test_app.py::test_remote_workspace_affinity_prefers_project_lane_and_persists_last_route -q` -> `2 passed in 7.35s`
- `.\.venv\Scripts\python.exe -m ruff check src/openzues/schemas.py src/openzues/services/launch_routing.py tests/test_app.py` -> passed

### What remains

- This slice closes the route-handoff shape gap only. OpenZues still does not consume `main_session_key` / `last_route_policy` anywhere beyond the launch-route handoff, so any OpenClaw behavior that targets inbound route updates at the main session still needs a follow-on parity pass.
- Broader parity domains beyond routing remain open, including browser runtime, nodes, voice, packaging, and companion-app surfaces that have not yet been re-anchored in this recovery lane.

### Next best slice

- Inspect the exact OpenClaw consumer path for `resolveInboundLastRouteSessionKey` and compare it against OpenZues [missions.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/missions.py:2689) plus any follow-up route persistence path.
- Land one focused `last_route_policy` consumer delta if the source contract shows inbound last-route updates or thread reuse should target `main_session_key` for workspace-affinity launches, then rerun the narrow app/missions proof pack.

### Blockers

- None.

### Re-entry checkpoint

- Recovered context: the gateway method-policy seam is verified; the active parity lane now advances from the routed-session contract instead of reopening bootstrap inventory.
- Verified state: OpenZues route handoffs now emit `session_key`, `main_session_key`, and `last_route_policy`, with task-lane routes marked `session` and workspace-affinity routes marked `main`.
- Next step: inspect the OpenClaw inbound last-route session-key consumer and port the smallest missing OpenZues persistence/reuse rule.
- Blockers: none.

**Checkpoint 2026-04-14**
Completed: stayed on the saved `gateway bootstrap` / `method registry` seam without reopening the parity ledger. Added exact startup-boot coverage in `tests/test_gateway_bootstrap.py` for the resolved launch-lane path, `BOOT.md`-missing skip, no-resolved-lane skip, and missing-thread-id failure.
Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_bootstrap.py tests/test_gateway_method_policy.py -q` -> `13 passed`.
Remaining: production parity still needs a source-of-truth compare for gateway startup wiring beyond policy coverage, especially `src/openzues/services/gateway_bootstrap.py` and the app startup hook in `src/openzues/app.py`.
Next best slice: compare OpenClaw gateway startup/boot semantics against `src/openzues/services/gateway_bootstrap.py` plus `src/openzues/app.py`, then land any missing runtime behavior with an exact app-level test.

**Checkpoint 2026-04-15**
Completed: compared OpenClaw gateway startup failure handling in `openclaw-main/src/gateway/server.impl.ts` against `src/openzues/services/gateway_bootstrap.py` plus `src/openzues/app.py`. Landed the missing cleanup semantics in the FastAPI lifespan hook so startup boot failures now unwind owner-started resources, close the runtime manager, and release the control-plane lease before re-raising the original boot reason. Added the exact app-level regression in `tests/test_app.py`.
Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -k "gateway_bootstrap_startup_failure_preserves_boot_reason" -q` -> `1 passed, 158 deselected`; `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_bootstrap.py -q` -> `13 passed`.
Remaining: gateway bootstrap startup parity is tighter, but OpenClaw parity is still incomplete. The next highest-leverage seam is gateway HTTP/readiness startup surfacing around the app boundary, especially how startup state and degraded launch readiness are exposed after gateway initialization.
Next best slice: compare OpenClaw `src/gateway/server-http.ts` readiness/startup semantics against `src/openzues/app.py` health and control-plane endpoints, then land the missing runtime behavior with one exact app-level test.

## Recovery checkpoint 2026-04-14 routing session-key legacy canonical reuse America/Chicago

Recovered context:

- Re-entered from the existing `routing/session-key` anchor instead of reopening gateway bootstrap or method-registry work.
- Compared OpenClaw `C:\Users\skull\OneDrive\Documents\openclaw-main\src\agents\command\session.ts` against OpenZues `src/openzues/database.py`, `src/openzues/services/followups.py`, and `tests/test_missions.py` to isolate the smallest remaining explicit-session reuse gap.

Completed:

- Normalized OpenZues session-key reuse and followup identity matching so legacy mixed-case or padded stored `session_key` values no longer break thread reuse or recovery-run equivalence.
- Updated `src/openzues/database.py` to resolve the latest mission by `LOWER(TRIM(session_key))`, which lets canonical inbound keys reuse older saved threads even when the stored row predates current normalization.
- Updated `src/openzues/services/followups.py` so recovery/checkpoint followups compare normalized session identities before falling back to thread identity.
- Added focused regressions in `tests/test_missions.py` for legacy mixed-case thread reuse and normalized followup matching.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_missions.py -q -k "create_reuses_saved_thread_from_session_key or create_reuses_saved_thread_from_legacy_mixed_case_session_key or followup_payload_matching_uses_session_key_when_thread_changes or followup_payload_matching_normalizes_session_key_before_reuse"` -> `4 passed, 105 deselected in 1.20s`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_missions.py -q` -> `109 passed in 32.16s`

Tool evidence:

- debugging: used exact `rg`/`Get-Content` probes on `src/openzues/database.py`, `src/openzues/services/followups.py`, `src/openzues/services/missions.py`, `tests/test_missions.py`, and the OpenClaw source seam before patching; verified with focused `pytest`.
- delegation: used one Architect sidecar (`Godel`) to map the explicit-session fallback seam and confirm the minimal owned-file boundary before edits.
- memory: used OpenZues Recall via `.\\.venv\\Scripts\\python.exe -m openzues.cli recall --json "gateway bootstrap method registry"` to recover the prior parity anchor.
- session_search: queried saved OpenClaw mission/checkpoint history through that Recall result before restating the active seam.

Next step:

- Stay inside `routing/session-key` and inspect the exact OpenClaw inbound consumer for session-key or route-policy fallback, preferably `src/routing/resolve-route.ts` or the adjacent session-id helper named in the last route handoff checkpoint.
- Land one focused OpenZues consumer rule only if the source contract shows `main_session_key` or last-route policy should influence inbound thread reuse beyond the launch-handoff shape now proven.

Blockers:

- Focused parity verification is green for this slice.
- A repo-local `ruff check src/openzues/database.py src/openzues/services/followups.py tests/test_missions.py` run still reports a pre-existing unrelated `E501` at `src/openzues/database.py:1045`, so the lint proof for this turn is test-backed rather than lint-clean.
## Recovery checkpoint 2026-04-14 gateway bootstrap method registry verification

- Re-entry stayed on the saved `gateway bootstrap` / `method registry` seam and used Recall first instead of reopening the ledger tail.
- Focused source lock: [src/openzues/services/gateway_bootstrap.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_bootstrap.py), [src/openzues/services/gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py), [tests/test_gateway_bootstrap.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_bootstrap.py), and [tests/test_gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Concrete claim verified: OpenZues already carries the saved parity slice for startup boot dispatch and gateway method scope classification. The focused proof pack is green without additional edits:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_gateway_bootstrap.py` -> `4 passed`
  - `.\.venv\Scripts\python.exe -m pytest tests\test_gateway_method_policy.py` -> `9 passed`
- Current blocker status: the stalled lane was orbiting on checkpoint inspection, not on a failing bootstrap or method-policy seam.
- Next bounded step: inspect the first broader contract surface that consumes this seam in [tests/test_app.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_app.py) and only then decide whether any dashboard or API parity gap remains.
## Checkpoint 2026-04-14 device bootstrap normalizer verification refresh America/Chicago

Completed:

- Held the saved `device-bootstrap-profile` parity slice without widening scope or reopening the ledger.
- Revalidated the normalization handoff as the current mission anchor.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_device_bootstrap_profile.py -q` -> `3 passed in 0.04s`

Next step:

- Compare `openclaw-main/src/shared/device-bootstrap-profile.ts` against `src/openzues/cli.py`, `src/openzues/services/onboarding.py`, and `src/openzues/services/gateway_bootstrap.py`, then land the first missing bootstrap-profile field or normalization rule with focused verification.
## Recovery checkpoint 2026-04-14 gateway method wizard registry proof refresh

- Re-entry stayed on the saved `gateway bootstrap` / `method registry` seam without reopening broader parity inventory.
- Concrete claim verified: OpenClaw's current wizard gateway registry is exactly `wizard.cancel`, `wizard.next`, `wizard.start`, and `wizard.status`, and OpenZues already classifies all four through the reserved `wizard.` admin prefix in [src/openzues/services/gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py).
- Landed one bounded proof delta in [tests/test_gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py) by adding a source-derived regression test that locks the full OpenClaw wizard registry instead of sampling only `wizard.status`.
- Verified:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_gateway_method_policy.py -q` -> `10 passed in 0.11s`
- Recovery note: the stale checkpoint claim that `wizard.status` was still a live missing registry gap was no longer true on the current branch; the real high-leverage step was refreshing the parity proof so future recovery lanes do not chase that dead delta again.
- Next bounded step: compare the next uncovered OpenClaw gateway handler family beyond wizard prefixes against [tests/test_gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py) and land one equally source-derived proof or missing classification delta.

Blockers:

- None.
## Recovery checkpoint 2026-04-14 method registry re-anchor

- Completed: added a canonical gateway method registry in `src/openzues/services/gateway_method_policy.py` so OpenZues now materializes the OpenClaw base gateway methods plus current OpenZues control-plane additions even when no live lane catalog is publishing tool names.
- Completed: wired `src/openzues/services/gateway_capability.py` to fall back to that local registry for the method-catalog surface instead of reporting a fully idle seam when catalogs are offline.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_gateway_method_policy.py -q` passed (`15 passed in 0.12s`), including the new assertion that the local registry covers the OpenClaw base registry.
- Next smallest step: add one focused gateway-capability fallback test that exercises the no-live-catalog path directly and proves the staged registry summary/scopes returned by `/api/gateway/capability`.
- Blockers: none.

## Recovery checkpoint 2026-04-14 gateway boot prompt parity

- Completed: tightened the `gateway bootstrap` seam by aligning OpenZues startup boot prompt wording with OpenClaw's current `src/gateway/boot.ts` contract in [src/openzues/services/gateway_bootstrap.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_bootstrap.py).
- Completed: the boot prompt now explicitly tells the runtime to use `message` with `action=send`, provide `channel + target`, use `target` instead of `to`, and reply with the silent token after sending.
- Completed: locked that claim in [tests/test_gateway_bootstrap.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_bootstrap.py) so future recovery lanes do not regress the boot-message contract while touching onboarding or launch routing.
- Verified:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_gateway_bootstrap.py -q` -> `6 passed in 1.41s`
  - `.\\.venv\\Scripts\\python.exe -m compileall src/openzues/services/gateway_bootstrap.py` -> compiled cleanly
- Remaining on this seam: compare the rest of OpenClaw `src/gateway/boot.ts` outcome semantics against `GatewayBootstrapService.run_startup_boot_once`, especially the missing/empty/error branches and any startup lifecycle differences beyond prompt text.
- Next bounded step: stay inside the same boot seam and add one source-derived test for the next unmatched `boot.ts` behavior before widening back out to gateway capability or broader onboarding parity.
- Blockers: none.

## Recovery checkpoint 2026-04-14 gateway boot outcome parity

- Completed: stayed inside the `gateway bootstrap` seam and locked the remaining `boot.ts` file-outcome branches in [tests/test_gateway_bootstrap.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_bootstrap.py) instead of reopening broader gateway inventory work.
- Concrete claim verified: OpenZues now has source-derived proof that `GatewayBootstrapService.run_startup_boot_once` mirrors OpenClaw's `src/gateway/boot.ts` behavior for whitespace-only `BOOT.md` files and unreadable `BOOT.md` failures at the level that matters for control-plane behavior: skip on empty, fail on read error, and never dispatch a boot launch in either branch.
- Verified:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_gateway_bootstrap.py -q` -> `8 passed in 1.50s`
  - `.\\.venv\\Scripts\\python.exe -m compileall src/openzues/services/gateway_bootstrap.py tests/test_gateway_bootstrap.py` -> compiled cleanly
- Remaining on this seam: OpenClaw `runBootOnce` also snapshots and restores the main session mapping around the boot run; OpenZues uses a different runtime surface, so the next parity decision is whether an equivalent launch-state preservation invariant belongs in `RuntimeManager` / gateway bootstrap here or whether the architectural difference is intentional.
- Next bounded step: inspect only the OpenZues launch-state handoff around `GatewayBootstrapService.run_startup_boot_once` and `RuntimeManager.start_thread`/`start_turn`, then land either one focused preservation fix or one explicit proof test that the current OpenZues flow does not trample the primary session mapping.
- Blockers: none.

## Recovery checkpoint 2026-04-14 boot launch-state preservation parity

- Completed: stayed on the boot launch-state seam and fixed the concrete preservation gap in [manager.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/manager.py): `RuntimeManager.start_thread()` no longer replaces `runtime.threads` with a single idle placeholder when a new thread starts.
- Concrete claim verified: startup boot thread seeding now preserves the preexisting live thread snapshot instead of temporarily trampling it, which is OpenZues' closest equivalent to OpenClaw's `runBootOnce` session-mapping preservation invariant.
- Completed: added a focused regression in [test_manager.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_manager.py) proving a new boot thread is appended while an existing active thread remains visible.
- Verified:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_manager.py -q` -> `23 passed in 26.38s`
  - `.\\.venv\\Scripts\\python.exe -m compileall src/openzues/services/manager.py tests/test_manager.py` -> compiled cleanly
- Remaining on this seam: confirm whether boot-triggered `start_turn()` timeout recovery also preserves the existing runtime thread snapshot correctly when the turn starts late and the runtime refresh returns partial thread status.
- Next bounded step: stay inside `RuntimeManager.start_turn()` and add one focused preservation proof around timeout recovery with preexisting thread state before widening back out to other gateway parity slices.
- Blockers: none.

## Recovery checkpoint 2026-04-14 start-turn timeout preservation parity

- Completed: stayed inside the same runtime-state seam and tightened [manager.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/manager.py) so `_confirm_timed_out_start_turn()` now merges refreshed thread status with the pre-timeout runtime snapshot instead of dropping unrelated threads during late-turn recovery.
- Concrete claim verified: when `RuntimeManager.start_turn()` recovers from a timeout and the refresh only surfaces the timed-out thread, OpenZues now keeps the preexisting runtime thread snapshot visible rather than temporarily erasing it.
- Completed: added a focused regression in [test_manager.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_manager.py) proving timeout recovery preserves an existing thread while surfacing the newly active recovered thread, and updated the local test doubles to match the current `_schedule_refresh_instance(..., methods=...)` signature.
- Verified:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_manager.py -q` -> `26 passed in 26.63s`
  - `.\\.venv\\Scripts\\python.exe -m compileall src/openzues/services/manager.py tests/test_manager.py` -> compiled cleanly
- Remaining on this seam: both `start_thread()` and `start_turn()` now preserve the in-memory runtime snapshot during boot recovery, but the next parity question is whether gateway bootstrap should also prove that its boot launch path leaves broader control-plane lane state untouched at the service boundary.
- Next bounded step: return to the `gateway bootstrap` seam and add one focused proof in [test_gateway_bootstrap.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_bootstrap.py) or [test_manager.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_manager.py) that startup boot preserves existing connected-lane runtime state outside the new boot thread/turn itself.
- Blockers: none.

## Recovery checkpoint 2026-04-14 gateway method policy recovery proof America/Chicago

- Completed: resumed the stalled `gateway method policy` recovery lane without reopening broader parity inventory and rechecked the exact seam that had been left in inspection orbit at [src/openzues/services/gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py).
- Concrete claim verified: OpenZues already covers every OpenClaw canonical base gateway method from `openclaw-main/src/gateway/server-methods-list.ts`; a focused source-to-target extraction found `MISSING []`, and the existing parity proof in [tests/test_gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py) passed cleanly.
- Verified:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_gateway_method_policy.py -q` -> `15 passed in 0.04s`
- Recovery note: no production edit was needed on this turn because the inspected registry seam was already closed on the current branch; the durable action was re-establishing proof so the next cycle does not spend more time rereading the same policy file.
- Next bounded step: stay on the same gateway registry lane, but move one layer outward to [src/openzues/services/gateway_capability.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_capability.py) and add or verify the no-live-catalog fallback test that proves `/api/gateway/capability` serves the staged local registry/scopes when OpenClaw catalogs are absent.
- Blockers: none.

## Recovery checkpoint 2026-04-14 gateway capability staged registry fallback America/Chicago

- Completed: stayed on the named `gateway capability` seam and added a focused regression in [tests/test_app.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_app.py) that exercises `/api/gateway/capability` with a connected lane whose MCP catalogs are fully offline.
- Concrete claim verified: when no lane-published tool catalogs are available, OpenZues falls back to the staged local method registry and still returns the expected method inventory contract through both `/api/gateway/capability` and the dashboard payload, including the staged headline, local registry count, scope coverage, and reserved admin list.
- Verified:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_app.py -q -k staged_local_method_registry_when_lane_catalogs_are_offline` -> `1 passed, 152 deselected in 5.68s`
- Recovery note: this was a proof-only parity slice; [src/openzues/services/gateway_capability.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_capability.py) already had the fallback behavior, but the endpoint contract was not locked against regression before this turn.
- Next bounded step: stay on the same gateway-capability surface and add the matching CLI proof in [tests/test_cli.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_cli.py) so the staged local registry summary is also covered when operators inspect gateway posture outside the dashboard/API path.
- Blockers: none.

## Recovery checkpoint 2026-04-14 gateway capability staged registry CLI proof America/Chicago

- Completed: stayed on the same `gateway capability` seam and added a focused human-output regression in [tests/test_cli.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_cli.py) for `_emit_gateway_capability(...)` when the method catalog is coming from the staged local registry instead of a live lane catalog.
- Concrete claim verified: the CLI now has locked proof that the staged fallback summary is surfaced to operators with the expected offline registry headline, the first six staged tool names, the first six reserved admin methods, and the operator/node-role scope counts.
- Verified:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_cli.py -q -k staged_local_method_registry_summary` -> `1 passed, 68 deselected in 1.93s`
- Recovery note: this was another proof-only slice; no production code changed because [src/openzues/cli.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/cli.py) already rendered the staged registry fields correctly once the payload contract was present.
- Next bounded step: stay on `gateway capability` and lock one broader contract proof by rerunning or extending the app-side gateway-capability cluster around cached/offline catalog behavior, then decide whether the next real parity delta is still inside gateway capability or can move to the next checkpointed gateway/bootstrap seam.
- Blockers: none.

## Recovery checkpoint 2026-04-14 gateway capability timeout-to-staged fallback America/Chicago

- Completed: stayed on the same `gateway capability` contract seam and added a focused regression in [tests/test_app.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_app.py) for the previously unproven combined case where live MCP status refresh times out and no cached lane catalog is available.
- Concrete claim verified: when `list_mcp_server_status(...)` times out and the connected lane has no cached tool catalog, `/api/gateway/capability` and the dashboard both fall back to the staged local gateway method registry instead of collapsing to an idle/empty method catalog.
- Verified:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_app.py -q -k refresh_times_out_without_cached_catalogs` -> `1 passed, 153 deselected in 7.00s`
- Recovery note: this was a proof-only slice; [src/openzues/services/gateway_capability.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_capability.py) already handled the fallback, but the timeout-plus-offline branch was not locked before this turn.
- Next bounded step: stay on the gateway-capability proof cluster long enough to run the exact cached/offline trio together or add one final contract test around server-count/lane-count semantics under degraded refresh, then decide whether gateway capability is fully re-anchored and the mission can return to the next gateway/bootstrap parity seam.
- Blockers: none.

## Recovery checkpoint 2026-04-14 stalled gateway method policy reverify America/Chicago

- Completed: resumed the stalled recovery lane directly on [src/openzues/services/gateway_method_policy.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py) and compared its staged registry/scope map against OpenClaw's canonical [method-scopes.ts](/C:/Users/skull/OneDrive/Documents/openclaw-main/src/gateway/method-scopes.ts) and [server-methods-list.ts](/C:/Users/skull/OneDrive/Documents/openclaw-main/src/gateway/server-methods-list.ts) without reopening broader parity inventory.
- Concrete claim verified: the previously suspicious control-plane and fallback registry methods are already present in OpenZues; an exact probe confirmed `poll`, `sessions.get`, `sessions.resolve`, `sessions.steer`, `push.test`, `connect`, `web.login.start`, and `web.login.wait` all resolve inside `list_known_gateway_methods()`.
- Verified:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_gateway_method_policy.py -q` -> `16 passed in 0.08s`
- Recovery note: no production edit was needed on this turn because the gateway method policy seam is already closed on the current branch; the durable action was re-establishing proof after the stalled read-only inspection orbit.
- Next bounded step: move one layer outward to [src/openzues/services/gateway_capability.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_capability.py) and run or extend the exact cached/offline gateway-capability proof cluster so staged registry fallback is locked across the degraded refresh paths, not just the raw policy map.
- Blockers: none.

## Recovery checkpoint 2026-04-14 method registry verification America/Chicago
- Re-entered from the saved `2026-04-13 parity re-anchor refresh` anchor and stayed on the bounded `method registry` seam instead of reopening the parity ledger.
- Verified the currently landed OpenZues gateway bootstrap and method catalog surface without broadening scope: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -k "method_catalog or gateway_bootstrap" -q` passed with `3 passed, 153 deselected`.
- Completed this turn: proof that the dashboard/app contract for the saved method-registry parity slice is still green after recovery.
- Remaining work on this seam: compare one concrete OpenClaw source-of-truth file under `openclaw-main\\src\\gateway` (`node-registry.ts` or `server-methods-list.ts`) against the OpenZues capability inventory serializer and land one additive delta if a field or summary is still missing.
- Next smallest step: inspect exactly one source file and exactly one target serializer path, then run the same focused `tests/test_app.py` method-catalog pack plus any directly touched unit test.
- Blockers: none found on this recovery turn.

## Recovery checkpoint 2026-04-14 method registry base-list proof America/Chicago
- Continued from the saved `method registry` seam without reopening the parity ledger.
- Compared OpenClaw `openclaw-main\\src\\gateway\\server-methods-list.ts` `BASE_METHODS` against OpenZues `src\\openzues\\services\\gateway_method_policy.py:list_known_gateway_methods()`.
- Verified concrete claim: OpenZues already covers every OpenClaw built-in gateway method in its staged fallback registry. Proof run:
  - `source_count 128`
  - `target_count 141`
  - `source_only []`
  - `target_only_sample ['chat.inject', 'config.openFile', 'connect', 'poll', 'push.test', 'sessions.get', 'sessions.resolve', 'sessions.steer', 'sessions.usage', 'sessions.usage.logs', 'sessions.usage.timeseries', 'web.login.start', 'web.login.wait']`
- Completed this turn: locked the highest-risk parity claim for the local method-registry fallback path; no additive code delta was required.
- Remaining work: verify whether the extra OpenZues-only methods are intentional extensions or whether one follow-up parity note/test should pin that superset behavior.
- Next smallest step: add one focused unit test that asserts the OpenClaw base method list remains a subset of `list_known_gateway_methods()`, or compare `GATEWAY_EVENTS` against the nearest OpenZues event surface if the mission wants the next adjacent contract slice.
- Blockers: none found.

## Recovery checkpoint 2026-04-14 method registry guard verification America/Chicago
- Continued from the saved `method registry` seam and verified the concrete parity guard already exists in `tests/test_gateway_method_policy.py`.
- Proof run: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -k "known_gateway_method_registry_covers_openclaw_base_registry or openclaw_gateway_events_are_not_treated_as_registry_methods" -q` passed with `2 passed, 14 deselected in 0.11s`.
- Completed this turn: confirmed the OpenClaw base gateway method subset contract and the adjacent `GATEWAY_EVENTS` separation contract are both pinned in focused tests; no additive code delta was required.
- Remaining work: move to the next adjacent parity seam under `src\\gateway` only if it names a concrete contract not already covered by the staged registry tests.
- Next smallest step: compare one OpenClaw gateway source file such as `node-registry.ts` against the OpenZues gateway capability serializer or node-role policy tests, then run only the directly touched test file plus `tests/test_app.py` if a contract surface changes.
- Blockers: none found.
## Checkpoint 2026-04-14 gateway bootstrap boot failure proof America/Chicago

Recovered context:

- Stayed on the saved OpenClaw parity anchor from the 2026-04-13 parity re-anchor refresh and kept the seam pinned to `gateway bootstrap`.
- Reused the already-verified gateway method policy footing and compared the OpenClaw source-of-truth boot contract in `openclaw-main/src/gateway/boot.ts` against `src/openzues/services/gateway_bootstrap.py` without reopening the contaminated parity-ledger tail.

Completed:

- Added a focused OpenZues regression proof for the startup boot failure path when boot-turn dispatch raises after the launch lane is resolved.
- Confirmed the existing `GatewayBootstrapService.run_startup_boot_once()` failure branch returns the surfaced lane error as `Startup boot failed: ...`, which is the closest current OpenZues analogue to OpenClaw's thrown `agentCommand` boot failure.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_bootstrap.py -q` -> `10 passed in 4.56s`
- `.\\.venv\\Scripts\\python.exe -m ruff check tests/test_gateway_bootstrap.py` -> passed

Next step:

- Stay on `gateway bootstrap` and decide the next smallest source-backed gap between `openclaw-main/src/gateway/boot.ts` and `src/openzues/services/gateway_bootstrap.py`.
- Best next slice: inspect whether OpenClaw's boot-run session isolation and mapping restoration needs an OpenZues-native equivalent around startup boot threads, then either land that additive isolation slice or checkpoint the architecture mismatch explicitly.

Blockers:

- No hard blocker, but the remaining delta is architectural: OpenClaw mutates and restores a main-session mapping during boot, while OpenZues already launches boot work on a fresh thread via `RuntimeManager`. The next turn needs to verify whether parity here is behavioral or intentionally translated.

## Recovery checkpoint 2026-04-15 routing session-key proof

Completed:

- Kept the active parity slice bounded to `routing/session-key` and avoided reopening the global source inventory.
- Added missing OpenClaw continuity proofs to [tests/test_session_keys.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_session_keys.py): backward-compatible direct `agent:*:(dm|direct):*` keys still classify as valid agent keys, and blank channel peer ids normalize to `unknown` instead of collapsing to the main session.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_session_keys.py -q` -> `14 passed in 0.98s`
- Source/target bootstrap anchor check after landing the routing proof:
  OpenClaw `src/gateway/boot.ts` still contains explicit main-session mapping snapshot/restore helpers, while OpenZues `src/openzues/services/gateway_bootstrap.py` currently starts a fresh boot thread and returns only the resulting `thread_id`.

Next smallest step:

- Stay on `gateway bootstrap`.
- Decide whether OpenClaw's `snapshotMainSessionMapping` / `restoreMainSessionMapping` behavior needs an OpenZues-native equivalent around startup boot threads, or whether the existing fresh-thread launch is the intended translated behavior that should be checkpointed as an architectural divergence.

Blockers:

- No hard blocker.
- The remaining question is behavioral parity, not file discovery: OpenClaw preserves and restores a main-session mapping during boot, and OpenZues does not expose an obvious matching mapping layer in `gateway_bootstrap.py`.

## Recovery checkpoint 2026-04-15 gateway bootstrap anchor

Completed:

- Reused the saved `gateway bootstrap` anchor directly instead of reopening the ledger or rerunning Recall.
- Verified the concrete source-of-truth claim behind the next seam with one bounded repo command.

Verified:

- OpenClaw `src/gateway/boot.ts` still contains explicit boot-time main-session mapping lifecycle hooks:
  `snapshotMainSessionMapping` at line 77, `restoreMainSessionMapping` at line 115, snapshot use at line 168, restore call at line 191.
- OpenZues [src/openzues/services/gateway_bootstrap.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_bootstrap.py) currently exposes `GatewayBootstrapBootResult.thread_id`, enters `run_startup_boot_once`, and launches startup boot through `self.manager.start_thread(...)` at line 216 before extracting `thread_id`, with no matching mapping snapshot/restore helper visible in that file.

Next smallest step:

- Stay on `gateway bootstrap`.
- Inspect whether OpenZues has an equivalent session-mapping layer outside `gateway_bootstrap.py` that makes the OpenClaw boot snapshot/restore unnecessary, or land a small additive mapping-preservation slice if no equivalent exists.

Blockers:

- No hard blocker.
- The current blocker is architectural uncertainty only: the parity gap is now narrowed to boot-time session mapping preservation, not general gateway boot execution.

## Recovery checkpoint 2026-04-15 gateway bootstrap session-mapping resolution America/Chicago

Completed:

- Resolved the open boot-time session-mapping question from the prior gateway bootstrap checkpoint.
- Verified that OpenZues already preserves startup-boot thread identity through the runtime manager, so OpenClaw's `snapshotMainSessionMapping` and `restoreMainSessionMapping` hooks do not map 1:1 onto a missing OpenZues session-store layer.
- Re-ran the focused gateway contract pack for the active seam:
  `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py tests/test_session_keys.py -q`

Verified:

- OpenClaw `src/gateway/boot.ts` still snapshots and restores a main-session mapping around the boot run because it dispatches through agent-session config helpers.
- OpenZues [src/openzues/services/gateway_bootstrap.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_bootstrap.py) launches startup boot with `self.manager.start_thread(...)`, extracts a concrete `thread_id`, and immediately calls `self.manager.start_turn(...)` against that thread.
- OpenZues [src/openzues/services/manager.py](/C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/manager.py) `start_thread(...)` already treats runtime thread identity as the durable primitive:
  it records pre-launch `known_thread_ids`, recovers a newly visible thread on timeout, upserts the returned `thread_id` into `runtime.threads`, appends it to `runtime.loaded_thread_ids`, and waits for thread visibility before returning.
- The focused parity checks remain green after that verification: `30 passed`.

Conclusion:

- Do not add an OpenClaw-style boot session-store snapshot/restore shim to `gateway_bootstrap.py`.
- On the OpenZues path, boot isolation is already handled by explicit thread creation and runtime thread tracking, so the earlier uncertainty was architectural, not an unfinished implementation gap.

Next smallest step:

- Stay on `gateway bootstrap`.
- Compare OpenClaw `src/gateway/boot.ts` failure/reporting semantics against OpenZues `GatewayBootstrapBootResult`, then add or tighten a focused startup-boot test if OpenZues is still missing a behavioral assertion for skipped, failed, or recovered boot runs.

Blockers:

- No hard blocker.
- The remaining work on this seam is behavioral parity coverage, not session-key plumbing.

## Recovery checkpoint 2026-04-15 gateway bootstrap failure semantics coverage America/Chicago

Completed:

- Stayed on the saved `gateway bootstrap` seam instead of reopening Recall or re-reading the parity ledger.
- Compared OpenClaw `src/gateway/boot.ts` boot-result handling against OpenZues startup-boot tests.
- Tightened [tests/test_gateway_bootstrap.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_bootstrap.py) with the missing failure assertion for `self.manager.start_thread(...)` raising during startup boot.

Verified:

- Exact focused verification passed:
  `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_bootstrap.py -q`
- Result: `11 passed`.
- OpenZues now has explicit startup-boot coverage for:
  successful boot dispatch, missing `BOOT.md`, empty `BOOT.md`, unreadable `BOOT.md`, missing resolved launch lane, missing returned `thread_id`, thread-launch exception, and turn-dispatch exception.

Next smallest step:

- Stay on `gateway bootstrap`.
- Compare OpenClaw `runBootOnce` skipped/failed result-shape semantics against any dashboard/API surface that serializes `GatewayBootstrapBootResult`, then add one focused contract assertion there if OpenZues does not yet prove the boot status reaches the UI unchanged.

Blockers:

- No hard blocker.
- Remaining risk on this seam is contract propagation, not boot execution coverage.

## Recovery checkpoint 2026-04-15 gateway bootstrap startup failure propagation America/Chicago

Completed:

- Stayed on the saved `gateway bootstrap` seam and compared OpenClaw `src/gateway/boot.ts` plus `src/hooks/bundled/boot-md/handler.ts` against OpenZues `src/openzues/app.py` instead of reopening broader gateway inventory.
- Verified the OpenClaw source contract does not serialize boot results into a dashboard surface; it preserves `failed` and `skipped` result reasons only through the immediate startup consumer path.
- Added one focused app-level regression in [tests/test_app.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_app.py:4881) so a failed `GatewayBootstrapBootResult` now has an exact control-plane lifespan proof that the boot reason survives unchanged through startup failure.

Verified:

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q -k "gateway_bootstrap_startup_failure_preserves_boot_reason"` -> `1 passed, 157 deselected in 3.93s`

Concrete claim locked:

- OpenZues already matches the saved OpenClaw boot-result consumer shape at the only active contract surface: when startup boot returns `status="failed"`, the control-plane lifespan raises with the original boot reason instead of rewriting or dropping it.

Remaining:

- This turn added proof only; OpenZues still does not persist startup boot outcomes into `/api/dashboard` or `/api/gateway/bootstrap`, and the OpenClaw source seam did not require such a UI surface.
- Broader parity work remains open outside this closed gateway-bootstrap sub-seam.

Next smallest step:

- Leave this startup-failure propagation slice closed and move to the saved `device-bootstrap-profile` seam: compare `C:\Users\skull\OneDrive\Documents\openclaw-main\src\shared\device-bootstrap-profile.ts` against `src/openzues/cli.py`, `src/openzues/services/onboarding.py`, and `src/openzues/services/gateway_bootstrap.py`, then land one missing normalization or persisted-field delta with focused verification.

Blockers:

- None.

## Recovery checkpoint 2026-04-15 method registry parity landing
- Completed: verified gateway method name coverage between `src/openzues/services/gateway_method_policy.py` and `openclaw-main/src/gateway/server-methods-list.ts` without reopening the parity ledger.
- Verified: OpenClaw `BASE_METHODS` count = 128 and OpenZues `list_known_gateway_methods()` count = 141; OpenZues is missing zero OpenClaw method names.
- Verified detail: the current delta is OpenZues-only methods `chat.inject`, `config.openFile`, `connect`, `poll`, `push.test`, `sessions.get`, `sessions.resolve`, `sessions.steer`, `sessions.usage`, `sessions.usage.logs`, `sessions.usage.timeseries`, `web.login.start`, and `web.login.wait`.
- Next smallest step: lock scope/auth parity for that OpenZues-only delta against the corresponding OpenClaw gateway/control-plane seams before broadening to another domain.
- Blockers: none.

## Recovery checkpoint 2026-04-15 method registry scope/auth anchor
- Completed: took one bounded source-of-truth pass on the OpenClaw gateway seam for the OpenZues-only method delta instead of reopening the ledger.
- Verified: the OpenZues-only methods are not arbitrary drift; OpenClaw has corresponding control-plane handlers for `poll` in `src/gateway/server-methods/send.ts`, `sessions.get` / `sessions.resolve` / `sessions.steer` in `src/gateway/server-methods/sessions.ts`, `sessions.usage` / `sessions.usage.timeseries` / `sessions.usage.logs` in `src/gateway/server-methods/usage.ts`, and `web.login.start` / `web.login.wait` in `src/gateway/server-methods/web.ts`.
- Verified: this leaves the remaining noisy delta methods `chat.inject`, `config.openFile`, `connect`, and `push.test` for a tighter exact-source scope/auth check rather than a broad text sweep.
- Next smallest step: run one exact-source verification for `connect` and the remaining control-plane delta against the owning OpenClaw handler file(s), then compare those auth/scope expectations with `src/openzues/services/gateway_method_policy.py`.
- Blockers: the one-shot grep was too noisy for `connect`, so that method still needs an exact-file verification pass before calling the scope/auth seam closed.

## Recovery checkpoint 2026-04-15 remaining control-plane source anchor
- Completed: verified the owning OpenClaw source files for the last unresolved method-registry delta without reopening the parity ledger.
- Verified: `chat.inject` is implemented in `openclaw-main/src/gateway/server-methods/chat.ts`, `config.openFile` in `openclaw-main/src/gateway/server-methods/config.ts`, `connect` in `openclaw-main/src/gateway/server-methods/connect.ts`, and `push.test` in `openclaw-main/src/gateway/server-methods/push.ts`.
- Verified: every method currently listed as OpenZues-only at the registry layer now has a concrete OpenClaw handler seam; the remaining work is scope/auth comparison, not method-existence discovery.
- Next smallest step: take one exact-file scope/auth pass over those four owning OpenClaw handler files and compare the result to `src/openzues/services/gateway_method_policy.py` before changing code.
- Blockers: none.

## Recovery checkpoint 2026-04-15 gateway method registry parity locked
- Completed: locked the OpenClaw gateway method registry seam by comparing `openclaw-main/src/gateway/server-methods-list.ts` against `src/openzues/services/gateway_method_policy.py`.
- Verified: a direct source-vs-target diff reported `MISSING_COUNT 0`, so OpenZues already classifies every OpenClaw `BASE_METHODS` entry in the canonical gateway registry.
- Verified: focused proof passed with `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q -k classifies_all_openclaw_base_methods` (`1 passed, 15 deselected`).
- Verified: the adjacent event seam is still open; a bounded lookup found no OpenZues event-catalog owner for OpenClaw events such as `connect.challenge`, `voicewake.changed`, `exec.approval.requested`, or `device.pair.requested`.
- Next smallest step: map where OpenZues surfaces gateway event subscriptions and add or wire a canonical event registry that can be compared directly to OpenClaw `GATEWAY_EVENTS` in `openclaw-main/src/gateway/server-methods-list.ts`.
- Blockers: none.

## Recovery checkpoint 2026-04-15 gateway event catalog seam blocked cleanly
- Completed: took one bounded OpenZues lookup on the named next seam instead of broadening back into the parity ledger or Recall.
- Verified: `rg -n --glob 'src/openzues/**' 'connect\\.challenge|voicewake\\.changed|exec\\.approval\\.requested|device\\.pair\\.requested|session\\.message|sessions\\.changed'` returned no matches, so OpenZues does not currently expose a canonical event registry or obvious mirrored event-name surface for representative OpenClaw gateway events.
- Verified: the previously completed gateway method-registry seam remains the most recent closed slice; this turn did not reopen or alter that logic.
- Next smallest step: inspect one concrete OpenZues gateway/websocket transport file that emits or subscribes to session events, identify the owning abstraction for event names, and either add a canonical event registry there or checkpoint the exact missing owner file if no such abstraction exists.
- Blockers: the owning OpenZues file for gateway event names is still unidentified after the single bounded lookup, so the next turn should spend its first repo command on one concrete transport file rather than another pattern sweep.

## Recovery checkpoint 2026-04-15 websocket transport owner identified
- Completed: followed the saved gateway event-catalog anchor into one concrete transport file, `src/openzues/app.py`, instead of reopening Recall or widening the ledger search.
- Verified: `src/openzues/app.py:2913-2921` is the live websocket event transport; the `/ws` handler subscribes to `active_hub` and forwards raw `event` payloads with `json.dumps(event)`.
- Verified: this transport file is not a canonical OpenClaw-style gateway event registry owner; it relays whatever names upstream publishers emit and does not define mirrored gateway event constants such as `connect.challenge`, `voicewake.changed`, or `sessions.changed`.
- Next smallest step: inspect `src/openzues/services/hub.py` as the likely owning abstraction behind `active_hub`, then either add a canonical gateway event registry there or checkpoint that event names are producer-scattered and name the first producer file to normalize.
- Blockers: none for the next slice; the current blocker was reduced from "owner unknown" to "transport confirmed, registry owner still upstream of `app.py`."

## Recovery checkpoint 2026-04-15 gateway event owner reduction America/Chicago
- Completed: followed the saved event-catalog seam into `src/openzues/services/hub.py` and one bounded producer lookup instead of reopening Recall or widening the parity ledger again.
- Verified: `src/openzues/services/hub.py` is only a generic `BroadcastHub`; it stores subscriber queues and republishes arbitrary event dictionaries, but it does not define canonical event-name constants or an OpenClaw-style gateway event registry.
- Verified: a bounded lookup of `active_hub` / `publish(` shows event producers are currently scattered across `src/openzues/services/control_chat.py`, `src/openzues/services/hermes_platform.py`, `src/openzues/services/manager.py`, `src/openzues/services/ops_mesh.py`, `src/openzues/services/remote_ops.py`, and `src/openzues/services/missions.py`, so the missing parity seam is a producer-side normalization point rather than the hub transport itself.
- Next smallest step: inspect `src/openzues/services/manager.py` first as the likely central producer, verify which event names it emits today, and decide whether that file should own a canonical gateway event registry or defer to a new shared constant module.
- Blockers: none.
## Recovery checkpoint 2026-04-15 method registry parity lock

- Completed: verified the OpenClaw gateway base method registry in `openclaw-main/src/gateway/server-methods-list.ts` remains fully covered by OpenZues `list_known_gateway_methods()`, and tightened the parity contract in `tests/test_gateway_method_policy.py` so the OpenZues-only control-plane extras `config.openFile`, `poll`, and `push.test` are now explicitly locked alongside the previously asserted extras.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests\test_gateway_method_policy.py -q` passed (`16 passed`).
- Next smallest step: inspect the same gateway seam for parity around startup/plugin bootstrap surfaces, starting with `openclaw-main/src/gateway/server-startup-plugins.ts` versus OpenZues gateway capability/bootstrap summaries, and confirm whether plugin-registered method scopes need an additional OpenZues proof.
- Blockers: none in this slice.

## Recovery checkpoint 2026-04-15 startup plugin scope proof America/Chicago

- Completed: compared OpenClaw `openclaw-main/src/gateway/server-startup-plugins.ts` against the existing OpenZues gateway method-scope surfaces and confirmed this seam already has a source-backed proof path, so no production patch was needed on this recovery turn.
- Completed: locked the key parity claim to the existing OpenZues consumer path in `src/openzues/services/gateway_capability.py`, which already reads per-tool `scope` metadata from live lane catalogs and routes it through the same reserved-admin coercion rules exposed by `src/openzues/services/gateway_method_policy.py`.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests\test_app.py -q -k plugin_scoped_methods_from_catalog_metadata` passed (`1 passed, 157 deselected`).
- Verified: `.\.venv\Scripts\python.exe -m pytest tests\test_gateway_method_policy.py -q -k "plugin_scope or reserved_admin_policy"` passed (`2 passed, 14 deselected`).
- Next smallest step: return to the still-open gateway event catalog seam and inspect `src/openzues/services/manager.py` as the first central producer, then decide whether it should own canonical gateway event constants or defer to a new shared registry module before patching.
- Blockers: none.

## Recovery checkpoint 2026-04-15 manager event-owner probe America/Chicago

- Completed: used the saved gateway event-catalog anchor directly and spent the turn's single bounded repo command on `src/openzues/services/manager.py`.
- Verified: `rg -n "publish\\(|active_hub|event_name|event\\s*=|sessions\\.changed|session\\.message|voicewake|approval|pair" src\openzues\services\manager.py` only found the generic hub publish sites at `manager.py:1429` and `manager.py:1451`, plus unrelated approval-policy strings, which is evidence that `manager.py` forwards caller-supplied event types rather than owning a canonical OpenClaw-style event registry.
- Next smallest step: inspect the exact `manager.py` publish helper body and its first caller on the next turn so the parity lane can name the first real producer-owned event namespace before deciding between a shared registry module and producer-local constants.
- Blockers: this probe intentionally stopped at grep-level evidence, so the concrete producer that supplies those event type strings is still unverified until the next bounded source read.
## Recovery checkpoint 2026-04-15 gateway method registry hold

- Anchor: Stayed on the saved OpenClaw parity gateway seam instead of reopening the ledger or broadening into unrelated routing, browser, voice, or delivery work.
- Completed: Verified that `src/openzues/services/gateway_method_policy.py` still mirrors the OpenClaw gateway method-registry baseline anchored by `openclaw-main/src/gateway/server-methods-list.ts`.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `16 passed in 0.16s`.
- Concrete claim locked: OpenZues' local known-method registry still covers the OpenClaw base gateway registry, including the explicit control-plane additions already tracked in the parity mirror.
- Blockers: none.
- Next best slice: stay inside the gateway seam and inspect the OpenClaw plugin/bootstrap boundary against `src/openzues/services/gateway_bootstrap.py`, then land the smallest missing startup-boot or lane-resolution parity gap with a focused gateway/bootstrap test pack.
## Recovery checkpoint 2026-04-15 gateway bootstrap anchor hold

- Completed: Stayed on the saved gateway/plugin bootstrap seam and verified the existing OpenZues startup-boot path without reopening the ledger or broadening scope.
- Verified: bounded source inspection of `src/openzues/services/gateway_bootstrap.py` confirmed that `run_startup_boot_once()` already gates on saved bootstrap state, reads `BOOT.md`, resolves a launch lane, and only starts a boot turn when `launch_route.resolved_instance` exists.
- Concrete proof: `gateway_bootstrap.py` lines covering `BOOT_FILENAME`, `GatewayBootstrapBootResult`, and `run_startup_boot_once()` show the expected skip/fail/run contract, including the resolved-lane guard at the `launch_route is None or launch_route.resolved_instance is None` branch.
- Next smallest step: run the exact gateway bootstrap test file for this seam, then compare any failing assertion against `openclaw-main/src/gateway/boot.ts` before changing code.
- Blockers: none.

## Recovery checkpoint 2026-04-15 gateway bootstrap session-key seam
Completed:
- Verified the actual OpenClaw source seam is `openclaw-main/src/gateway/boot.ts`, not a Python `bootstrap.py` file.
- Verified `src/openzues/services/gateway_bootstrap.py` already matches the OpenClaw boot prompt contract for `BOOT.md`, the `message` tool `target` wording, and the silent reply token flow.

Verified:
- OpenClaw `src/gateway/boot.ts` snapshots and restores the main session mapping around the boot run.
- OpenZues `src/openzues/services/gateway_bootstrap.py` launches startup boot by calling `RuntimeManager.start_thread()` and `start_turn()` directly.
- OpenZues still models `session_key` and `main_session_key` in launch routing, so startup boot is bypassing the session-key reuse contract instead of reusing it.

Next smallest step:
- Implement the gateway startup boot launch through a session-key-aware path so the boot turn preserves the saved main-session identity the way OpenClaw `boot.ts` does, then extend `tests/test_gateway_bootstrap.py` with the focused regression.

Blockers:
- None; the remaining work is choosing the smallest contract-safe place to thread `session_key`/`main_session_key` into the startup boot launch path without broadening into unrelated mission routing.

## Recovery checkpoint 2026-04-15 gateway bootstrap session-key verification
Completed:
- Re-verified the saved gateway bootstrap anchor without reopening the ledger body.
- Confirmed the current OpenZues startup boot path still bypasses session-key-aware launch reuse.

Verified:
- `src/openzues/services/gateway_bootstrap.py:216` launches startup boot with `await self.manager.start_thread(...)`.
- `src/openzues/services/gateway_bootstrap.py:229` dispatches the boot prompt with `await self.manager.start_turn(...)`.
- `src/openzues/services/manager.py:999` defines `start_thread(...)` without a `session_key` parameter, which confirms the current startup boot path cannot preserve the saved main-session identity yet.

Next smallest step:
- Add the smallest session-key-aware thread launch path for gateway startup boot, then extend `tests/test_gateway_bootstrap.py` with the focused regression that proves the saved main session is preserved.

Blockers:
- None.

## Recovery checkpoint 2026-04-15 gateway bootstrap verification
- Completed: Re-anchored on the gateway bootstrap seam without reopening the parity ledger, then verified the new startup-boot and saved-launch bootstrap behavior already landed in `src/openzues/services/gateway_bootstrap.py` and `tests/test_gateway_bootstrap.py`.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_bootstrap.py -q` passed (`11 passed`); `.\\.venv\\Scripts\\python.exe -m pytest tests/test_launch_routing.py -q` passed (`2 passed`); `node --check src/openzues/web/static/app.js` passed; `.\\.venv\\Scripts\\python.exe -m compileall src/openzues` passed.
- Blocker: The broader contract pack `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q` did not complete inside the 244s timeout on this recovery turn, so cross-surface proof for the full control-plane seam is still incomplete.
- Next smallest step: Resume with one bounded verification slice only: rerun `tests/test_app.py` by itself first, fix the first failure if one appears, then continue outward to `tests/test_database.py` and `tests/test_manager.py` only after `tests/test_app.py` is green.

## Recovery checkpoint 2026-04-15 app-surface verification blocker
- Completed: Used the saved gateway-bootstrap checkpoint as the anchor and spent this turn on exactly the next named verification step, `tests/test_app.py`, without reopening the parity ledger or widening the seam.
- Verified: The command started cleanly with `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -q`.
- Blocker: `tests/test_app.py` did not complete within the 244s bounded timeout on this reflex turn, so the broader app-surface proof for the gateway bootstrap contract remains unresolved.
- Next smallest step: Re-run `tests/test_app.py -q` with a longer timeout or isolated environment, capture the first failing or hanging test, and fix only that app-surface issue before widening to any additional suite.

## Recovery checkpoint 2026-04-15 app-surface first failure captured
- Completed: Reused the saved app-surface anchor and re-ran the exact named proof as `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -vv --maxfail=1` so the stalled verification could land on one concrete blocker instead of timing out again.
- Verified: `tests/test_app.py` now advances through 87 passing cases before the first hard failure at `tests/test_app.py::test_attention_queue_does_not_harden_a_hardener_again`, where `plan_attention_queue(...)` returns `None` for a completed `Harden OpenZues Workspace` mission carrying the OpenClaw parity handoff objective.
- Blocker: The remaining gateway-bootstrap app-surface proof is blocked on attention-queue logic drift in `src/openzues/services/control_chat.py` near `plan_attention_queue`; pytest also emitted secondary `aiosqlite` thread shutdown warnings, but they did not stop collection before the first assertion failure.
- Next smallest step: Inspect and patch `src/openzues/services/control_chat.py` so completed hardener missions are recognized as already-hardened parity handoffs instead of falling through to `None`, then rerun `tests/test_app.py -k does_not_harden_a_hardener_again -q` followed by `tests/test_app.py -q`.

## Recovery checkpoint 2026-04-15 gateway parity re-anchor
- Completed: Treated the app-surface tail as contamination, re-anchored on the OpenClaw gateway seam, compared `C:\\Users\\skull\\OneDrive\\Documents\\openclaw-main\\src\\gateway\\server-methods-list.ts` against `src/openzues/services/gateway_method_policy.py`, and reran the focused proof `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_method_policy.py -q`.
- Verified: Gateway method registry parity is currently locked; the OpenClaw base registry is fully covered in OpenZues, and the focused suite passed with `16 passed in 0.08s`.
- Remaining gap: `C:\\Users\\skull\\OneDrive\\Documents\\openclaw-main\\src\\gateway\\boot.ts` still preserves and restores the main-session mapping around boot execution, while `src/openzues/services/gateway_bootstrap.py` currently runs startup boot in a fresh thread without an equivalent session-preservation guard.
- Next smallest step: Inspect the target session-preservation seam around `src/openzues/services/gateway_bootstrap.py`, `src/openzues/services/session_keys.py`, and the runtime manager contract, then add a focused startup-boot regression test before widening back to broader app-surface verification.

## Recovery checkpoint 2026-04-15 startup-boot session guard seam confirmed
- Completed: Used the saved gateway parity re-anchor directly and verified the cited runtime seam with one bounded code lookup across `src/openzues/services/gateway_bootstrap.py` and `src/openzues/services/manager.py`.
- Verified: `GatewayBootstrapService.run_startup_boot_once()` still performs boot by calling `self.manager.start_thread(...)` and then `self.manager.start_turn(...)`, and the current runtime manager contract only exposes those fresh-thread entrypoints at `src/openzues/services/manager.py:999` and `src/openzues/services/manager.py:1080`; there is no parallel session-mapping preservation hook in this path yet.
- Blockers: None on inspection. The remaining work is implementation, not discovery.
- Next smallest step: Add a focused regression test that captures startup boot preserving the main session mapping expectation, then patch `src/openzues/services/gateway_bootstrap.py` and any minimal runtime/session helper needed to satisfy that test before rerunning only the new startup-boot pack.

## Recovery checkpoint 2026-04-15 session-key fallback guard locked
- Completed: Took one bounded routing/session-key slice under the OpenClaw gateway parity anchor and added a regression in `tests/test_missions.py` proving that a thread-suffixed incoming session key must not reuse a saved thread through parent-session fallback when the conversation target changes.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_missions.py -q -k "create_reuses_saved_thread_from_thread_suffixed_session_key or create_blocks_thread_reuse_when_conversation_target_changes or create_blocks_parent_session_fallback_thread_reuse_when_conversation_target_changes"` passed with `3 passed, 140 deselected in 1.85s`, confirming both the existing reuse path and the new mismatch guard.
- Remaining gap: The named gateway parity anchor is still the startup-boot session-preservation seam; `src/openzues/services/gateway_bootstrap.py` still lacks the OpenClaw-style main-session mapping guard around boot execution.
- Next smallest step: Add the focused startup-boot regression named by the prior checkpoint, then patch `src/openzues/services/gateway_bootstrap.py` and the minimal manager/session helper needed to preserve the main-session mapping during boot before rerunning that exact startup-boot pack.
## 2026-04-15 Recovery checkpoint - gateway bootstrap

- Completed: Re-anchored on the gateway seam from the stalled `openclaw-main\\src\\gateway` inspection and verified the in-flight OpenZues gateway bootstrap implementation against OpenClaw `src/gateway/boot.ts`.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_bootstrap.py -q` -> `11 passed in 2.59s`.
- Next smallest step: Lock the gateway method registry seam by comparing `openclaw-main\\src\\gateway\\server-methods-list.ts` with `src/openzues/services/gateway_method_policy.py`, then prove it with `tests/test_gateway_method_policy.py`.
- Blockers: None in this slice.
## 2026-04-15 Recovery Checkpoint
- Seam locked: gateway bootstrap startup boot parity (`openclaw-main/src/gateway/boot.ts` -> `src/openzues/services/gateway_bootstrap.py`).
- Verified claim: OpenZues already dispatches `BOOT.md` startup boot to the resolved launch lane and skips cleanly when no launch lane resolves.
- Proof: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_bootstrap.py -k "dispatches_boot_prompt_to_resolved_launch_lane or skips_without_resolved_launch_lane" -q` -> `2 passed, 9 deselected`.
- Changes landed this turn: none; recovery closed the stalled inspection orbit by replacing directory enumeration with exact source-to-target verification.
- Remaining gateway seam: method registry and scope-policy parity after bootstrap.
- Next best slice: compare `openclaw-main/src/gateway/method-scopes.ts` and `openclaw-main/src/gateway/server-methods-list.ts` against `src/openzues/services/gateway_method_policy.py`, then land any missing catalog or scope behavior with focused tests.
## 2026-04-15 Method Registry Checkpoint
- Completed: verified gateway method-registry and scope-policy parity anchor (`openclaw-main/src/gateway/method-scopes.ts` and `openclaw-main/src/gateway/server-methods-list.ts` against `src/openzues/services/gateway_method_policy.py`).
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -k "mirrors_openclaw_operator_scope_groups or known_gateway_method_registry_covers_openclaw_base_registry" -q` -> `2 passed, 14 deselected`.
- Result: no code changes were needed on this reflex turn; the current OpenZues registry already covers the cited OpenClaw base-method catalog and operator scope groups.
- Next smallest step: inspect one concrete gateway handler seam under the same anchor, starting with `openclaw-main/src/gateway/server-methods/config.ts` against the OpenZues control-plane/config surface that feeds gateway capability and dashboard catalogs.
- Blockers: none found in the verified method-registry slice.

## 2026-04-15 Config Handler Checkpoint
- Completed: stayed on the saved post-registry seam and compared OpenClaw `openclaw-main/src/gateway/server-methods/config.ts` against the current OpenZues config-facing gateway surface instead of reopening broader parity inventory.
- Completed: verified the existing OpenZues contract already covers the OpenClaw config handler registry methods through `src/openzues/services/gateway_method_policy.py` and propagates the staged registry summary through the app/dashboard and CLI surfaces without new code changes.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py tests/test_app.py tests/test_cli.py -q -k "config_handlers or staged_method_registry_summary or staged_local_method_registry_summary"` -> `2 passed, 242 deselected in 2.10s`.
- Concrete claim locked: the OpenClaw config handler method set (`config.get`, `config.schema`, `config.schema.lookup`, `config.set`, `config.patch`, `config.apply`, `config.openFile`) is already classified in OpenZues, and the staged gateway method catalog exposed by API/dashboard/CLI still includes the reserved config admin methods unchanged.
- Next smallest step: stay on the same gateway-handler anchor and inspect the next concrete handler seam, `openclaw-main/src/gateway/server-methods/channels.ts`, against the OpenZues gateway capability / dashboard / CLI catalog surfaces before broadening to unrelated gateway runtime work.
- Blockers: none in this verified config-handler slice.
## 2026-04-15 Session-Key Forced Landing Checkpoint

- Completed: Re-anchored on the `routing/session-key` seam instead of reopening the parity ledger. Verified that OpenZues already carries the core OpenClaw session-key helper surface in `src/openzues/services/session_keys.py`.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_session_keys.py -q` passed (`17 passed`).
- Concrete claim locked: OpenZues does not yet expose an OpenClaw-style run-id to session-key resolver. A bounded search across `src/openzues` found no equivalent for `resolveSessionKeyForRun`, `resolvePreferredSessionKeyForSessionIdMatches`, or `toAgentRequestSessionKey`-driven run lookup.
- Next smallest step: implement a single additive run-id resolver on the OpenZues side, backed by persisted mission/session state, and cover it with one exact test file before widening back to gateway/bootstrap work.
- Blockers: none confirmed, but the storage surface for `run_id -> session_key` still needs to be chosen deliberately from existing mission/swarm persistence rather than guessed.

## 2026-04-15 Gateway Registry Recovery Checkpoint
- Completed: used the stalled `openclaw-main/src/gateway` inspection as a bounded recovery seam and re-verified the live OpenClaw gateway registry anchor instead of reopening broader parity inventory.
- Completed: confirmed that OpenZues already mirrors the OpenClaw gateway method catalog classification and keeps OpenClaw event-only names out of the registry surface; no production code changes were required in this recovery slice.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed (`16 passed in 0.44s`).
- Concrete claim locked: the OpenClaw `src/gateway/server-methods-list.ts` method/event contract is still covered by `src/openzues/services/gateway_method_policy.py`, and event-only names such as `sessions.changed`, `session.message`, `session.tool`, `exec.approval.requested`, and `plugin.approval.requested` remain disjoint from `list_known_gateway_methods()`.
- Remaining unfinished seam: the newer `routing/session-key` checkpoint is still the active gap, specifically the missing OpenClaw-style `run_id -> session_key` resolver on the OpenZues side.
- Next smallest step: compare `openclaw-main/src/gateway/server-session-key.ts` against `src/openzues/services/session_keys.py`, choose the existing persisted mission/swarm storage that can own `run_id -> session_key`, and land that resolver with one exact test file before returning to broader gateway/bootstrap work.
- Blockers: none in the registry seam; the only design choice still open is which existing persistence surface should back the run-id lookup.

## 2026-04-15 Routing Session-Key Reflex Checkpoint
- Completed: stayed on the saved `routing/session-key` seam and compared OpenClaw `openclaw-main/src/gateway/server-session-key.ts` directly against OpenZues `src/openzues/services/session_keys.py` without reopening the parity ledger or widening into unrelated gateway files.
- Verified: OpenClaw currently exposes a concrete `resolveSessionKeyForRun(runId)` helper backed by agent-run context, a cached `run_id -> session_key` lookup, and fallback session-store matching via `sessionId === runId`; the OpenZues session-key module still contains none of that run-id resolution surface.
- Concrete claim locked: the saved checkpoint was accurate. OpenZues remains missing the OpenClaw-style run-id resolver seam, and that gap is now narrowed to choosing the existing persisted mission/swarm/session store that should own the `run_id -> session_key` lookup.
- Next smallest step: inspect exactly one existing OpenZues persistence surface that already stores run/session identifiers, add a minimal additive resolver in `src/openzues/services/session_keys.py`, and verify it with `tests/test_session_keys.py -q` before broadening back to bootstrap or dashboard work.
- Blockers: unresolved storage choice only; no code was changed on this reflex turn because selecting the wrong persistence owner would create fake parity.

## 2026-04-15 Method Registry Forced Landing
- Completed: locked the gateway method-registry seam by tightening `tests/test_gateway_method_policy.py` so the OpenZues registry delta against OpenClaw is exact instead of subset-only.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `16 passed in 0.12s`.
- Concrete claim: OpenZues covers every method in `openclaw-main/src/gateway/server-methods-list.ts`; the only allowed OpenZues-only registry methods are `chat.inject`, `config.openFile`, `connect`, `poll`, `push.test`, `sessions.get`, `sessions.resolve`, `sessions.steer`, `sessions.usage`, `sessions.usage.logs`, `sessions.usage.timeseries`, `web.login.start`, and `web.login.wait`.
- Next smallest step: inspect the `routing/session-key` seam against `openclaw-main/src/gateway/server-session-key.ts` and decide whether OpenZues needs a run-id to session-key resolver or an explicit checkpointed blocker because no equivalent run-id persistence exists yet.
- Blockers: none for the method-registry seam; `routing/session-key` remains unresolved and likely needs a storage-mapping decision before code changes.
## 2026-04-15 Device Bootstrap Profile Proof
- Completed: stayed on the saved bootstrap-profile anchor from the gateway parity lane and added a source-derived parity proof in [tests/test_device_bootstrap_profile.py](/C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_device_bootstrap_profile.py) against OpenClaw `src/shared/device-bootstrap-profile.ts` instead of widening into a new gateway or browser seam.
- Completed: locked that OpenZues still mirrors the OpenClaw pairing bootstrap profile for default roles/scopes and the underlying normalization rules used by onboarding and gateway bootstrap saves. No production code changed because this slice resolved as a proof gap, not a behavior gap.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_device_bootstrap_profile.py -q` passed with `3 passed in 0.07s`, and `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_bootstrap.py -q` passed with `11 passed in 2.33s`.
- Concrete claim verified: OpenZues default bootstrap roles/scopes and normalization behavior currently match the OpenClaw source contract in `openclaw-main/src/shared/device-bootstrap-profile.ts`, so the saved gateway bootstrap profile is not missing an obvious roles/scopes normalization delta on this seam.
- Next smallest step: return to the already-named `routing/session-key` seam and compare OpenClaw `openclaw-main/src/gateway/server-session-key.ts` against `src/openzues/services/session_keys.py` to decide whether OpenZues needs a run-id to session-key resolver or an explicit checkpointed architectural blocker.
- Blockers: none. This turn intentionally stopped after the bounded parity proof and exact verification.

## 2026-04-15 Gateway Method Registry Proof
- Completed: added a regression proof in `tests/test_gateway_method_policy.py` that walks the OpenClaw runtime `src/gateway/server-methods/*.ts` handlers, ignores test fixtures, and asserts every real handler is either classified by OpenZues operator scope policy or explicitly treated as a node-role method. No production code changed because the gap was proof coverage, not runtime behavior.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `17 passed in 0.15s`.
- Concrete claim verified: current OpenClaw runtime gateway handlers produce `134` method entries across `31` non-test `server-methods` files, and OpenZues classifies all of them with `missing_count=0`.
- Next smallest step: resume the already-queued `routing/session-key` seam by comparing OpenClaw `openclaw-main/src/gateway/server-session-key.ts` with `src/openzues/services/session_keys.py`, then either land the missing resolver behavior or checkpoint the exact blocker.
- Blockers: none.

## 2026-04-15 Gateway Bootstrap Recovery Checkpoint
- Completed: resumed the stalled `gateway bootstrap` and `method registry` inspection from the saved parity anchor, checked the existing target seam in `src/openzues/services/gateway_bootstrap.py` and `src/openzues/services/gateway_method_policy.py`, and confirmed this lane was already implemented rather than missing runtime code.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_bootstrap.py tests/test_gateway_method_policy.py -q` passed with `28 passed in 2.80s`.
- Concrete claim verified: OpenZues currently ships both a startup boot dispatcher and a source-backed gateway method policy proof for this seam; the combined focused pack is green without any recovery edits.
- Next smallest step: move to the queued `routing/session-key` seam by comparing OpenClaw `openclaw-main/src/gateway/server-session-key.ts` with `src/openzues/services/session_keys.py`, then either land the missing run-id or lane-key resolver behavior or checkpoint the exact storage blocker.
- Blockers: none on the bootstrap or method-registry seam.

## 2026-04-15 Routing Session-Key Blocker Checkpoint
- Completed: compared OpenClaw `openclaw-main/src/gateway/server-session-key.ts` against OpenZues `src/openzues/services/session_keys.py` and the focused target proof in `tests/test_session_keys.py` without widening beyond the named seam.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_session_keys.py -q` passed with `17 passed in 0.75s`.
- Concrete claim verified: OpenClaw includes a `resolveSessionKeyForRun(runId)` helper with cached run-id lookup and fallback session-store matching by `sessionId`, while OpenZues `session_keys.py` currently covers only session-key parsing, normalization, aliasing, and thread suffix helpers. There is no equivalent run-id to session-key resolver in the inspected OpenZues seam, and the current focused tests do not claim one.
- Next smallest step: choose the OpenZues source of truth for run-id to session-key resolution, then add the smallest equivalent resolver plus exact tests for cache hit, store hit, and miss behavior.
- Blockers: unresolved storage contract. This reflex turn stopped before implementation because the OpenClaw behavior depends on a run/session store lookup path that has not been tied to a concrete OpenZues persistence surface in the inspected seam.

## 2026-04-15 Gateway Nodes Registry Recovery Checkpoint
- Completed: resumed the stalled `gateway/server-methods/nodes` inspection by checking OpenClaw `openclaw-main/src/gateway/server-methods/nodes.ts` plus `nodes-pending.ts`, then comparing that seam against OpenZues `src/openzues/services/gateway_method_policy.py` and a focused target search for `node.pair`, `node.invoke`, `node.pending`, and `node.canvas.capability.refresh`.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `17 passed in 0.07s`.
- Concrete claim verified: the node-only gateway registry parity is already locked in OpenZues. `tests/test_gateway_method_policy.py` proves the OpenClaw node-role registry methods (`node.invoke.result`, `node.event`, `node.pending.drain`, `node.canvas.capability.refresh`, `node.pending.pull`, `node.pending.ack`, `skills.bins`) and the combined node/voice handler classification match the source seam. The focused target search also showed those node methods currently exist only in `src/openzues/services/gateway_method_policy.py`, not in a runtime node service yet.
- Next smallest step: keep the `gateway nodes` seam bounded, pick the concrete OpenZues runtime owner for node pairing/invoke/pending flows, and then map OpenClaw `openclaw-main/src/gateway/server-methods/nodes.ts` plus `nodes-pending.ts` into that target with exact tests before broadening to browser or voice follow-ons.
- Blockers: none for the registry proof; the remaining work is choosing and implementing the target runtime contract for node handlers.

## Recovery checkpoint 2026-04-15 gateway nodes registry reverify America/Chicago
- Completed: stayed on the saved `gateway nodes` seam instead of broadening into browser, voice, or packaging work. No production files changed on this reflex turn.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `17 passed in 0.11s`, so the already-landed OpenZues gateway registry still covers the OpenClaw node-role method surface named in `openclaw-main/src/gateway/server-methods/nodes.ts` and `nodes-pending.ts`.
- Next smallest step: create the first concrete OpenZues runtime owner for the remaining node handler contract, starting with one bounded target under `src/openzues/services` for `node.pending.*` queue state and then port the adjacent `node.invoke`/pairing behavior into that owner with exact tests.
- Blockers: none for the registry seam itself; the open question is implementation ownership, not source-of-truth coverage.

## Recovery checkpoint 2026-04-15 gateway registry seam lock America/Chicago
- Completed: resumed from the saved gateway/node anchor without reopening the full ledger, verified OpenClaw `openclaw-main/src/gateway/server-methods-list.ts` against OpenZues `src/openzues/services/gateway_method_policy.py`, and confirmed the local registry helper still mirrors the OpenClaw base method list.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `17 passed in 0.15s`.
- Concrete claim verified: OpenZues is not missing any OpenClaw base gateway methods in the registry seam. A direct comparison against `server-methods-list.ts` produced `missing []`; the only extras are OpenZues control-plane methods already covered by the existing test expectation: `chat.inject`, `config.openFile`, `connect`, `poll`, `push.test`, `sessions.get`, `sessions.resolve`, `sessions.steer`, `sessions.usage`, `sessions.usage.logs`, `sessions.usage.timeseries`, `web.login.start`, `web.login.wait`.
- Remaining gap locked: `src/openzues/services` still has gateway policy/bootstrap files only and no dedicated runtime owner for node pairing, invoke, or pending queue behavior, so the unfinished seam is runtime handling rather than registry coverage.
- Next smallest step: create one bounded runtime owner under `src/openzues/services` for `node.pending.*` state and tests first, then wire `node.invoke` and pairing flows onto that owner before broadening to browser, voice, or packaging seams.
- Blockers: none.

## Recovery checkpoint 2026-04-15 node pending seam anchor America/Chicago
- Completed: used the saved post-registry anchor directly and inspected the exact OpenClaw source seam at `openclaw-main/src/gateway/server-methods/nodes-pending.ts` instead of broadening into adjacent gateway domains.
- Verified: the unfinished runtime contract is specifically `node.pending.drain` and `node.pending.enqueue`. OpenClaw’s handler file proves this seam depends on queue-state operations (`drainNodePendingWork`, `enqueueNodePendingWork`), request validation, and offline wake/reconnect behavior (`maybeWakeNodeWithApns`, `waitForNodeReconnect`, `maybeSendNodeWakeNudge`) before returning the enqueue/drain response shape.
- Next smallest step: add one bounded OpenZues runtime owner under `src/openzues/services` for `node.pending.*` queue state first, with exact tests covering enqueue, drain, revision/deduping behavior, and only then decide whether wake/reconnect wiring can be ported in the same slice or should stay as the next checkpointed follow-on.
- Blockers: OpenZues still has no existing node runtime service file to extend, so the next turn must choose and create that owner explicitly rather than patching gateway policy again.

## Recovery checkpoint 2026-04-15 node pending forced landing America/Chicago
- Completed: verified the earlier gateway method-registry claim against `openclaw-main/src/gateway/server-methods-list.ts` and confirmed the live parity anchor has already advanced to the `node.pending.*` runtime seam named in the saved checkpoint.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `17 passed in 0.09s`; a direct source-vs-target registry diff showed `missing=[]` for OpenClaw base methods; `openclaw-main/src/gateway/server-methods/nodes-pending.ts` proves the next missing owner is queue-state runtime behavior for `node.pending.enqueue` and `node.pending.drain`, while OpenZues currently only exposes policy/catalog references for those methods.
- Next smallest step: create one bounded runtime owner under `src/openzues/services` for node pending queue state, add exact tests for enqueue, drain, dedupe, and revision behavior first, then wire gateway handlers onto that owner before attempting wake/reconnect follow-on work.
- Blockers: none.
## 2026-04-15 Gateway Method Registry Proof
- Seam: gateway method registry and method-scope parity.
- Verified claim: `src/openzues/services/gateway_method_policy.py` already covers the OpenClaw base registry in `openclaw-main/src/gateway/server-methods-list.ts`; the focused diff returned `MISSING_COUNT 0`.
- Verification: `./.venv/Scripts/python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `17 passed in 0.15s` on 2026-04-15.
- Outcome: no code changes were needed for this seam.
- Remaining gap: node gateway methods appear in OpenZues policy and tests, but the bounded runtime search only surfaced those names in `src/openzues/services/gateway_method_policy.py`; no runtime handler implementation surfaced under `src/openzues` for `node.invoke.result`, `node.event`, `node.pending.pull`, `node.pending.ack`, or `node.canvas.capability.refresh`.
- Next seam: map `openclaw-main/src/gateway/node-registry.ts` into the OpenZues gateway runtime path and land the smallest production slice that makes node invoke/result flow real instead of catalog-only.
## 2026-04-15 Gateway Registry Verification

- Completed: Verified the in-flight OpenClaw gateway parity slice already staged in `src/openzues/services/gateway_method_policy.py`, `src/openzues/services/gateway_bootstrap.py`, `src/openzues/services/session_keys.py`, and `src/openzues/services/launch_routing.py` without reopening the ledger or broadening scope.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py tests/test_gateway_bootstrap.py tests/test_session_keys.py tests/test_launch_routing.py -q` passed with `47 passed in 2.27s`.
- Next smallest step: run the broader contract seam pack named by mission control against the already-staged gateway/onboarding/routing work: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_ops_mesh.py -q`, `node --check src/openzues/web/static/app.js`, and `.\\.venv\\Scripts\\python.exe -m compileall src/openzues`.
- Blockers: none from the focused gateway verification slice; remaining risk is contract drift outside the narrow gateway/session-key pack until the broader pack is rerun.
## 2026-04-15 Gateway Method Registry Re-anchor

- Completed: Re-anchored the stalled `gateway bootstrap` / `method registry` / `session-key` seam against `openclaw-main/src/gateway/server-methods-list.ts`, `openclaw-main/src/gateway/server-session-key.ts`, `src/openzues/services/gateway_method_policy.py`, and `src/openzues/services/session_keys.py`.
- Verified: The OpenZues gateway method registry already covers the OpenClaw base gateway method list; the only raw diff noise was the TypeScript import strings, not missing method names. `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `17 passed`.
- Next smallest step: Check the remaining `routing/session-key` parity seam for run-id to session-key resolution behavior, using `openclaw-main/src/gateway/server-session-key.ts` as the source contract and one targeted OpenZues consumer path.
- Blockers: None in this slice. The prior stall was inspection drift, not a failing contract.
## 2026-04-15 Gateway Bootstrap Startup Boot Proof

- Completed: Verified the saved `gateway bootstrap` seam directly against `openclaw-main/src/gateway/boot.ts` and `src/openzues/services/gateway_bootstrap.py` instead of reopening broader parity inventory.
- Verified claim: OpenZues already preserves the OpenClaw startup boot contract for `BOOT.md` dispatch on a resolved launch lane, including the exact boot-check prompt shape and `target`-field messaging instruction.
- Verification: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_bootstrap.py -k run_startup_boot_once_dispatches_boot_prompt_to_resolved_launch_lane -q` passed with `1 passed, 10 deselected` on 2026-04-15.
- Outcome: no code changes were needed for this seam.
- Next smallest step: follow the ledger's unresolved runtime gap and map `openclaw-main/src/gateway/node-registry.ts` into the OpenZues gateway runtime path so node invoke/result handling is implemented beyond catalog policy coverage.
- Blockers: none.

## 2026-04-15 Gateway Method Registry Re-anchor
- Completed: Re-locked the OpenClaw `gateway` recovery anchor without reopening the ledger. Verified that OpenZues carries the gateway method registry in `src/openzues/services/gateway_method_policy.py` and surfaces it through `src/openzues/services/gateway_capability.py`, so the stalled `openclaw-main/src/gateway` inspection was not a missing target package.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed with `17 passed in 0.16s` on 2026-04-15.
- Next smallest step: Compare `src/openzues/services/gateway_bootstrap.py` against OpenClaw `src/gateway/boot.ts` for the startup boot / launch-lane contract, then land only the first concrete bootstrap gap that changes behavior.
- Blockers: None.

## 2026-04-15 Gateway Bootstrap Prompt Re-anchor
- Completed: Verified the first concrete `gateway_bootstrap` parity claim against OpenClaw source without reopening the ledger. OpenClaw `src/gateway/boot.ts` carries the same BOOT-file startup prompt contract already implemented in OpenZues `src/openzues/services/gateway_bootstrap.py`, including `BOOT.md`, message-tool `target`, and silent-reply token instructions.
- Verified: `rg -n "BOOT\.md|BOOT_OK|boot check|boot prompt|startup boot|startThread|start_turn|thread_id|message tool|ONLY:" C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\boot.ts` returned the matching prompt lines at 36 and 45-53 on 2026-04-15.
- Next smallest step: Compare the remaining `boot.ts` execution path against `src/openzues/services/gateway_bootstrap.py`, specifically lane resolution and boot-run dispatch, and land only the first behavioral gap if one exists.
- Blockers: None.
## 2026-04-15 Gateway Method Registry Re-anchor

- Completed: Re-anchored the stalled `src/gateway` inspection onto the concrete method-registry seam instead of re-running a broad directory inventory. Verified that OpenClaw's `src/gateway/server-methods-list.ts` `BASE_METHODS` set is fully covered by OpenZues `list_known_gateway_methods()` in `src/openzues/services/gateway_method_policy.py`.
- Verified: Focused Python diff from the OpenZues workspace reported `Missing from OpenZues: 0`. The only delta is 13 OpenZues-only control-plane methods: `chat.inject`, `config.openFile`, `connect`, `poll`, `push.test`, `sessions.get`, `sessions.resolve`, `sessions.steer`, `sessions.usage`, `sessions.usage.logs`, `sessions.usage.timeseries`, `web.login.start`, and `web.login.wait`.
- Next smallest step: Stay in the same gateway seam and lock event-registry parity against OpenClaw `GATEWAY_EVENTS` from `openclaw-main/src/gateway/server-methods-list.ts`, then decide whether OpenZues needs a first-class event catalog or an explicit documented non-parity exception.
- Blockers: None on method-registry parity. The forced landing happened because the old turn stayed in broad `src/gateway` inventory instead of proving one concrete gateway claim.

## 2026-04-15 Gateway Event Registry Check

- Completed: Verified the next saved seam directly against OpenClaw `GATEWAY_EVENTS` in `openclaw-main/src/gateway/server-methods-list.ts` without reopening the parity ledger.
- Verified: OpenClaw publishes 23 gateway events. `src/openzues/services/gateway_method_policy.py` contains 7 event-name strings incidentally (`agent`, `chat`, `presence`, `talk.mode`, `health`, `heartbeat`, `cron`) but no first-class event-catalog symbol. 16 OpenClaw events are missing from that file: `connect.challenge`, `session.message`, `session.tool`, `sessions.changed`, `tick`, `shutdown`, `node.pair.requested`, `node.pair.resolved`, `node.invoke.request`, `device.pair.requested`, `device.pair.resolved`, `voicewake.changed`, `exec.approval.requested`, `exec.approval.resolved`, `plugin.approval.requested`, and `plugin.approval.resolved`.
- Next smallest step: Add a first-class OpenZues gateway event catalog beside the method registry in `src/openzues/services/gateway_method_policy.py`, then wire one focused assertion into `tests/test_app.py` so staged method/event registry reporting cannot drift silently.
- Blockers: No blocker, but event parity is currently incomplete and undocumented.

## 2026-04-15 Gateway Method And Event Registry Proof

- Completed: Locked the gateway method-policy seam already in the worktree instead of restarting discovery. Confirmed that `src/openzues/services/gateway_method_policy.py` now carries both the OpenClaw-aligned method registry and a first-class gateway event catalog.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py -q` passed on 2026-04-15 with `18 passed in 0.07s`. That focused pack proves `list_known_gateway_methods()` covers OpenClaw `BASE_METHODS`, `list_known_gateway_events()` matches OpenClaw `GATEWAY_EVENTS`, and the operator-scope classification stays aligned with runtime handler files under `openclaw-main/src/gateway/server-methods`.
- Next smallest step: Keep the slice in the same gateway/control-plane contract seam and prove the registry reaches product surfaces. Add or tighten one focused `tests/test_app.py` assertion around any app/dashboard/API exposure of the gateway method/event catalog, then rerun that exact app contract pack before broadening into another parity domain.
- Blockers: None.

## 2026-04-15 Gateway Bootstrap Contract Recovery Checkpoint

- Completed: Resumed from the existing gateway parity worktree instead of reopening discovery. Locked the active seam to `src/openzues/services/gateway_bootstrap.py`, `src/openzues/services/launch_routing.py`, `src/openzues/services/session_keys.py`, and `src/openzues/services/gateway_method_policy.py`, then proved the saved contract survives both seam-local tests and a broader app-surface slice.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_bootstrap.py tests/test_launch_routing.py tests/test_session_keys.py tests/test_gateway_method_policy.py -q` passed on 2026-04-15 with `49 passed in 2.35s`. `node --check src/openzues/web/static/app.js` passed. `.\\.venv\\Scripts\\python.exe -m compileall src/openzues` passed. `.\\.venv\\Scripts\\python.exe -m pytest tests/test_app.py -k "gateway_bootstrap or launch_routing or gateway_capability or setup_launch_handoff or onboarding_bootstrap" -q` passed with `29 passed, 130 deselected in 81.74s`.
- Concrete claim locked: The current gateway bootstrap / launch-routing / session-key parity slice is wired through the FastAPI app surface for onboarding bootstrap, saved launch routing, and gateway capability endpoints; it is not just unit-test green.
- Remaining gap: The full `tests/test_app.py -q` run did not finish within the 124 second recovery timeout, so the next lane should treat full-file app coverage as an unresolved verification bound rather than assuming a clean broader pass.
- Next smallest step: Stay in the same gateway/control-plane seam and isolate the long-running `tests/test_app.py` cases outside the verified gateway subset. Tighten the next `-k` window until the slow or hanging surface is named, then either optimize that path or capture a separate checkpoint before broadening into another OpenClaw domain.
- Blockers: None.

## 2026-04-15 Gateway Plugin Method Scope Recovery Checkpoint

- Completed: Recovered the stalled gateway inspection by locking to the OpenClaw method-scope seam instead of reopening global discovery. Checked `openclaw-main/src/gateway/method-scopes.test.ts` against `src/openzues/services/gateway_method_policy.py`, `src/openzues/services/gateway_capability.py`, `tests/test_gateway_method_policy.py`, and `tests/test_app.py`. No production edit was needed because the plugin-scoped gateway method parity path is already present in the target worktree.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py::test_gateway_authorization_helpers_match_openclaw_operator_scope_behavior tests/test_app.py::test_gateway_capability_classifies_plugin_scoped_methods_from_catalog_metadata -q` passed on 2026-04-15 with `2 passed in 6.03s`.
- Concrete claim locked: OpenZues already mirrors the OpenClaw plugin method-scope contract for this seam. Non-reserved plugin methods can be classified from live catalog metadata with their published scope (`browser.request` -> `operator.write`), while reserved admin prefixes are still coerced to `operator.admin` (`wizard.custom` in the catalog view, `config.plugin.inspect` in the policy helper).
- Next smallest step: Stay in the gateway bootstrap/plugin startup seam and compare OpenClaw `src/gateway/server-startup-plugins.ts` plus `src/gateway/server-plugin-bootstrap.ts` against the OpenZues startup path to prove the live plugin route/method registry is pinned during startup, not only summarized later in gateway capability reporting.
- Blockers: None.
## 2026-04-15 Gateway Node Registry

- Completed: added `src/openzues/services/gateway_node_registry.py` to mirror the OpenClaw gateway node-session seam with register, list/get, event send, invoke request tracking, timeout handling, and disconnect cleanup.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests/test_gateway_node_registry.py -q` passed with `4 passed in 0.09s`.
- Next smallest step: wire the new registry into the live gateway surface so advertised methods like `node.list`, `node.describe`, `node.invoke`, and `node.invoke.result` stop being registry-only policy entries and start using real session state.
- Blockers: OpenZues still does not have a live gateway transport/router implementation under `src/openzues`, so this slice stops at the tested service boundary rather than full runtime integration.

## 2026-04-15 - Gateway method registry event parity
- Completed: verified the OpenClaw canonical gateway method registry against `openclaw-main/src/gateway/server-methods-list.ts`, confirmed built-in method parity, and closed the remaining event-catalog gap by adding `update.available` to `src/openzues/services/gateway_method_policy.py`.
- Completed: hardened `tests/test_gateway_method_policy.py` so the OpenClaw parity extractor resolves `GATEWAY_EVENT_UPDATE_AVAILABLE` from `openclaw-main/src/gateway/events.ts` instead of silently dropping that event from comparisons.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py tests/test_app.py -k "gateway_method_policy or gateway_capability" -q` -> `35 passed, 142 deselected`.
- Next smallest step: check the next unfinished parity seam under gateway/bootstrap inventory, specifically whether OpenClaw's staged bootstrap posture exposes any additional source-of-truth fields that OpenZues still omits from `src/openzues/services/gateway_bootstrap.py` and the dashboard payload.
- Blockers: none for the gateway method/event registry seam.

## 2026-04-15 - Recovery audit: gateway session-key and method base parity
- Completed: inspected OpenClaw `src/gateway/server-session-key.ts` and verified OpenZues already carries the matching routed session-key seam across `src/openzues/services/session_keys.py`, `src/openzues/services/launch_routing.py`, mission thread reuse, and database session-key lookups; no code change was needed.
- Completed: compared OpenClaw `src/gateway/server-methods-list.ts` against `src/openzues/services/gateway_method_policy.py` and confirmed there are no missing OpenClaw base gateway methods in OpenZues; the only differences are OpenZues control-plane extensions such as `chat.inject`, `connect`, `poll`, `sessions.get`, `sessions.resolve`, and web login helpers.
- Verified: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_gateway_method_policy.py tests/test_session_keys.py tests/test_launch_routing.py -q` -> `37 passed in 0.84s`.
- Next smallest step: resume the previously named gateway/bootstrap inventory seam by diffing OpenClaw `src/gateway/client-bootstrap.ts` and `src/gateway/boot.ts` against `src/openzues/services/gateway_bootstrap.py`, `src/openzues/schemas.py`, and the dashboard payload to find any still-missing staged bootstrap fields.
- Blockers: none; this recovery turn closed the false lead that `routing/session-key` or the base gateway method registry were still unfinished parity gaps.

## 2026-04-15 Recovery checkpoint: routing/session-key seam
- Completed: Re-anchored on the OpenClaw `gateway` namespace without reopening the parity ledger; confirmed the source seam file is `openclaw-main/src/gateway/server-session-key.ts`.
- Verified: `server-session-key.ts` resolves a run id to a session key by checking agent run context first, then the combined gateway session store, normalizing with `toAgentRequestSessionKey`, caching positive hits, and caching misses for 1000 ms.
- Next smallest step: Map this seam onto the real OpenZues target files that own routing/session-key and session-store behavior, then port the resolver and its focused tests into that surface.
- Blockers: A guessed mirror path `src/openzues/gateway` does not exist, so the target ownership for this seam still needs a bounded file-level mapping before implementation.
