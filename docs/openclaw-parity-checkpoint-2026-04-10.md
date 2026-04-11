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
