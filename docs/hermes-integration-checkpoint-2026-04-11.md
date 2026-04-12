# Hermes Integration Checkpoint

Date: 2026-04-11
Source of truth: `C:\Users\skull\OneDrive\Documents\hermes-agent-main`
Target: `C:\Users\skull\OneDrive\Documents\OpenZues`

## Source inventory

Hermes is not just a skill repo. The current source tree breaks down into these major product domains:

- `gateway/` with 38 files for channel delivery, pairing, sessions, restart/status, and per-platform adapters
- `hermes_cli/` with 43 files for setup, doctor, model/provider management, gateway commands, cron, plugins, pairing, and the curses UI shell
- `skills/` with 405 files and `optional-skills/` with 130 files
- `tools/` with 72 files and a first-class `toolsets.py` policy layer
- `agent/` with 28 files covering memory management, prompt building, context compression, routing, pricing, and subagent/runtime helpers
- `plugins/` with memory and context-engine plugin loaders plus provider-specific implementations
- `cron/` for scheduler and job persistence
- `acp_adapter/` and `acp_registry/` for editor-native ACP integration
- `environments/` for benchmark, parser, and research/runtime environment abstractions
- `tests/` with 527 files spanning the product surface

Highest-leverage source seams by domain:

- Gateway:
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\gateway\run.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\gateway\session.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\gateway\delivery.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\gateway\pairing.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\gateway\platforms\base.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\gateway\platforms\telegram.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\gateway\platforms\discord.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\gateway\platforms\slack.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\gateway\platforms\signal.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\gateway\platforms\whatsapp.py`
- CLI and setup surface:
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\cli.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\hermes_cli\setup.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\hermes_cli\doctor.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\hermes_cli\models.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\hermes_cli\tools_config.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\hermes_cli\plugins_cmd.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\hermes_cli\cron.py`
- Tool policy and execution:
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\toolsets.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\run_agent.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\model_tools.py`
- Learning loop and memory:
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\agent\memory_manager.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\agent\context_compressor.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\agent\prompt_builder.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\plugins\memory\__init__.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\plugins\memory\honcho\__init__.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\plugins\memory\supermemory\__init__.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\plugins\memory\mem0\__init__.py`
- Scheduled automation:
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\cron\scheduler.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\cron\jobs.py`
- Editor and protocol integration:
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\acp_adapter\server.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\acp_adapter\tools.py`
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\docs\acp-setup.md`
- Migration and parity:
  - `C:\Users\skull\OneDrive\Documents\hermes-agent-main\docs\migration\openclaw.md`

## Status by domain

| Domain | Hermes source evidence | OpenZues status on 2026-04-11 |
| --- | --- | --- |
| Skills catalog | `skills/`, `optional-skills/`, skill metadata/frontmatter conventions | Partial and newly improved. OpenZues now auto-discovers local Hermes skills and auto-attaches relevant ones into task drafts and skillbooks. |
| Skill self-improvement loop | `run_agent.py` background skill review, `skill_manage`, learning-loop prompt flow | Gap. OpenZues can pin and suggest skills, but it does not yet run a Hermes-style post-task skill creation or self-improvement loop. |
| Toolsets and tool policy | `toolsets.py`, `model_tools.py`, CLI tool configuration | Gap. OpenZues does not yet expose Hermes-style named toolsets, per-surface tool gating, or a toolset selection contract for missions and lanes. |
| Gateway and messaging surfaces | `gateway/` plus `gateway/platforms/*.py` | Gap. OpenZues has remote operators and mission control, but not Hermes-style Telegram/Discord/Slack/Signal/WhatsApp conversation delivery. |
| CLI and TUI | `cli.py`, `hermes_cli/curses_ui.py`, `hermes_cli/setup.py`, `hermes_cli/doctor.py` | Partial. OpenZues has control-plane CLI and setup/bootstrap flows, but not Hermes-grade terminal chat UX, slash-command ergonomics, or broad operator CLI parity. |
| Setup, doctor, update, migration | `hermes setup`, `hermes doctor`, `hermes update`, `hermes claw migrate` | Partial. OpenZues has setup/bootstrap posture and launch handoff, but not doctor-grade environment diagnosis, update tooling, or Hermes/OpenClaw migration parity. |
| Learning loop and memory plugins | `agent/memory_manager.py`, `plugins/memory/*` | Gap. OpenZues has checkpoint memory and mission context, but not Hermes's pluggable memory-provider layer, user modeling, or session-search-backed recall loop. |
| Session search and recall | README memory/session-search references, `run_agent.py`, plugin prompts | Gap. OpenZues telemetry exists, but there is no Hermes-like cross-session semantic search and summarization surface. |
| Cron and scheduled delivery | `cron/scheduler.py`, `cron/jobs.py`, CLI `/cron` support | Partial. OpenZues now has recurring playbooks and task blueprints, but not Hermes's natural-language cron UX or delivery back into chat platforms. |
| Subagents and parallel work | `delegate_task`, independent subagent budgets, parallel tool execution paths in `run_agent.py` | Partial. OpenZues already uses Codex missions and now has role-aware agent planning, but it does not yet expose a Hermes-style explicit delegation/tool execution policy layer. |
| Terminal backends | README and `cli.py` terminal backend envs for local, Docker, SSH, Daytona, Singularity, Modal | Gap. OpenZues currently assumes Codex-connected local/desktop lanes instead of a Hermes-style executor matrix. |
| ACP/editor protocol | `acp_adapter/`, `acp_registry/`, `docs/acp-setup.md` | Gap. OpenZues can orchestrate Codex lanes, but it does not expose itself as a standalone ACP agent server. |
| Plugin architecture | `plugins/` memory/context_engine loaders, `plugin.yaml` metadata | Gap. OpenZues does not yet have Hermes-style plugin discovery, activation, and config for provider-backed memory/context engines. |
| Research and benchmark environments | `environments/`, `batch_runner.py`, `trajectory_compressor.py`, `rl_cli.py` | Gap. OpenZues is product-focused and does not yet ship Hermes research/eval/trajectory tooling. |

## Completed this turn

The Hermes slice now landed in the OpenZues worktree is the right first integration seam: built-in Hermes skill discovery and automatic use.

Completed slice:

- Added local Hermes skill catalog discovery from the sibling `hermes-agent-main` repo.
- Parsed Hermes skill metadata and scored skills against mission/task context instead of requiring manual pins for every reusable workflow.
- Auto-attached matching Hermes skills into the existing OpenZues skillbook and Ops Mesh task-draft flow.
- Taught generated mission prompts to explicitly open the linked Hermes `SKILL.md` file before executing that workflow.
- Cleaned up dashboard rendering so auto-attached Hermes skills render as automatic system guidance instead of pretending they are manually removable pins.

Primary OpenZues files carrying this slice:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_skills.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\skillbook.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\settings.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_skillbook.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`

## Verification

Focused Hermes integration verification passed from the repo virtualenv:

- `.\.venv\Scripts\python.exe -m pytest tests/test_skillbook.py tests/test_app.py -q -k "test_onboarding_bootstrap_creates_first_run_bundle_and_launch_draft or test_dashboard_auto_attaches_matching_hermes_skill_to_task_draft"`
- `.\.venv\Scripts\python.exe -m pytest tests/test_ops_mesh.py -q -k test_build_ops_mesh_auto_skillbook_includes_claw_style_builtin_skills`
- `.\.venv\Scripts\ruff.exe check src/openzues/services/hermes_skills.py src/openzues/services/skillbook.py src/openzues/services/ops_mesh.py src/openzues/settings.py src/openzues/app.py tests/test_skillbook.py tests/test_app.py`
- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

Observed result:

- Hermes skills are now discovered locally and attached into the launch draft when the task context matches.
- OpenZues task objectives now preserve a durable source path to the Hermes `SKILL.md` file so Codex can follow the real workflow.

## What remains

To integrate Hermes into Zeus end to end, the major remaining product gaps are:

1. Hermes toolset parity:
   - named toolsets
   - lane/mission toolset policy
   - tool availability by run mode and surface
2. Hermes learning loop parity:
   - post-task skill creation
   - skill self-improvement during use
   - memory nudges and background review passes
3. Hermes memory and recall parity:
   - pluggable memory provider layer
   - session-search recall
   - user-profile modeling
4. Hermes CLI/TUI parity:
   - richer terminal chat surface
   - doctor/setup/update/model/tools commands
   - slash-command ergonomics
5. Hermes gateway parity:
   - channel adapters
   - pairing and routing
   - delivery back to chat surfaces
6. Hermes executor parity:
   - Docker/SSH/Modal/Daytona/Singularity backend selection
   - run-environment profiles and safety defaults
7. Hermes ACP/plugin parity:
   - ACP server mode
   - plugin discovery/config lifecycle
8. Hermes research extras:
   - trajectory generation/compression
   - benchmark and RL surfaces

## Next best slice

Do not jump straight to every Hermes chat platform next. The highest-leverage next slice is to import Hermes's tool-policy kernel, because that sits directly between skills, autonomy, and executor selection.

Recommended next slice:

- add Hermes-style named toolsets into OpenZues mission profiles
- bind toolsets to lane posture, mission role, and approval posture
- let setup/bootstrap choose a default toolset for a workspace or mission family
- keep the source of truth in one place so skills, missions, and future executor backends all read the same tool policy

After that, the best parity order is:

1. toolsets and tool policy
2. learning loop and memory protocol
3. doctor/setup/update CLI parity
4. executor backends
5. gateway/channel delivery
6. ACP/plugin and research extras

That order gives Zeus the Hermes brain before giving it Hermes transport surfaces.

## Blockers

- Hermes is developed primarily for Linux, macOS, WSL2, and Termux; native Windows parity is not the reference path. OpenZues will need to translate Hermes concepts into its Windows-first Codex-lane model rather than clone every shell assumption literally.
- The live OpenZues server has not been restarted in this turn, so the newly landed Hermes auto-skill integration is present in the worktree but not yet live on the currently running process until restart.

## Operator handoff

- Completed: mapped the Hermes source tree into parity domains, landed the Hermes auto-skill integration seam in OpenZues, and checkpointed the remaining Hermes integration work in a durable repo document.
- Verified: focused Hermes integration tests and static checks passed; the auto-skill path now resolves real Hermes `SKILL.md` files into OpenZues mission drafts.
- Next step: implement Hermes-style toolsets and tool-policy resolution inside OpenZues so missions, skills, and future executor backends share one capability contract.
- Blockers: no credential blocker; only the normal restart requirement to activate the newly landed Hermes code in the running server.

## Update: Hermes Toolsets + Recall Deck

Date: 2026-04-11

### Completed this turn

- Closed the next Hermes parity seam behind skill auto-attachment: OpenZues now has a real Hermes-style toolset kernel instead of only advisory wording.
- Added a new `src/openzues/services/hermes_toolsets.py` policy layer with named Hermes-inspired toolsets, profile expansion, inference, and operator-facing warnings for unsupported parity areas.
- Threaded normalized toolsets and tool policy through:
  - onboarding bootstrap
  - saved setup wizard session
  - gateway bootstrap profile
  - task blueprints and mission drafts
  - stored missions and live mission views
  - mission turn prompts and Ops Mesh launch objectives
- Taught Hermes skill matching to respect the active toolset posture instead of only raw string relevance, so skills that declare tool requirements no longer get attached blindly.
- Closed the missing Hermes `session_search` seam in the OpenZues control plane:
  - added a new `RecallService`
  - exposed `GET /api/recall`
  - added `openzues recall [query]`
  - added a compact Recall Deck to the structured dashboard
- The recall deck reuses persisted mission state, checkpoints, continuity packets, and proof handoffs instead of inventing another memory store, so recall survives restarts and abrupt shutdowns.

Primary files carrying this slice:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_toolsets.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_skills.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\skillbook.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\missions.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\onboarding.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\setup.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_bootstrap.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_capability.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\control_chat.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\recall.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\database.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\templates\index.html`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_skillbook.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_database.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_missions.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_recall.py`

### Verification

Focused Hermes toolset pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_skillbook.py tests/test_database.py tests/test_missions.py tests/test_app.py -q`
- Result: `133 passed`

Control-plane regression pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_ops_mesh.py tests/test_manager.py tests/test_cli.py -q`
- Result: `39 passed`

Recall changed-surface pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_recall.py tests/test_cli.py tests/test_app.py tests/test_missions.py -q`
- Result: `136 passed`

Broader merged verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_recall.py tests/test_skillbook.py tests/test_database.py tests/test_missions.py tests/test_ops_mesh.py tests/test_manager.py tests/test_cli.py tests/test_app.py -q`
- Result: `176 passed`

Static/runtime checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What is now true

- Hermes toolsets are no longer just descriptive copy. OpenZues now persists and surfaces toolset posture across setup, task, mission, and gateway surfaces.
- Hermes skills can now respect toolset compatibility, which means Zeus is doing a better job of knowing when a Hermes skill actually fits the current run instead of only matching tags or words.
- The dashboard, mission composer, task drafts, gateway bootstrap profile, and mission cards can all show the saved toolset posture and derived tool policy.
- Hermes `session_search` is now partially real inside Zeus:
  - recent recall works
  - keyword recall works
  - results are backed by saved missions and checkpoints
  - CLI, API, and dashboard all share one recall contract
- The recall seam is restart-safe because it reads persisted control-plane state rather than transient thread memory.

### What remains

The biggest Hermes parity gaps are now:

1. learning loop parity
   - post-task skill creation
   - skill self-improvement while a workflow is being used
   - background review passes that turn repeated operator friction into durable doctrine or skills
2. pluggable memory-provider parity
   - builtin plus one external provider contract
   - user modeling and richer recall sources beyond mission/checkpoint state
3. broader CLI/TUI parity
   - doctor/setup/update/model/tool commands
   - richer terminal chat ergonomics
4. executor parity
   - Docker/SSH/Modal/Daytona/Singularity-style backend selection and safety posture
5. gateway/channel parity
   - channel adapters
   - pairing
   - delivery back into chat surfaces
6. ACP/plugin/research parity
   - ACP server mode
   - plugin activation/config lifecycle
   - research and trajectory extras

### Next best slice

Do not jump to channels next. The next highest-leverage Hermes seam is the learning loop itself.

Recommended next slice:

- add a lightweight post-mission review pass that inspects durable checkpoints and detects repeatable workflow gaps
- let that pass emit either:
  - a skill-gap recommendation
  - a doctrine/inoculation update
  - or a candidate reusable micro-skill contract
- keep it grounded in the newly landed recall layer so the review pass can look across prior runs without rereading every thread from scratch

That gives Zeus the beginning of Hermes's self-improvement behavior before we spend time cloning transport surfaces.

### Operator handoff

- Completed: landed Hermes toolset policy persistence and a restart-safe recall deck across API, CLI, and dashboard.

## Update: Hermes Learning Reviews in Cortex

Date: 2026-04-11

### Completed this turn

- Closed the next Hermes parity seam after toolsets and recall: OpenZues now runs a lightweight Hermes-style learning review pass over durable mission history instead of only showing doctrine and warnings.
- Added reusable learning reviews inside the existing cortex surface, so Zues can now mine recent runs for:
  - winning tool postures worth replaying
  - checkpoint-first recovery habits when risky runs ignore proven anchors
  - proof-first verification posture when unstable runs widen scope without the same evidence loop
- Kept the learning loop grounded in persisted mission state and checkpoint history rather than transient thread context, so the new lessons survive restarts and reconnects.
- Exposed the learned-review contract end to end:
  - dashboard cortex column
  - `GET /api/cortex`
  - `openzues learn`
- Updated the Intelligence shell so learned Hermes review count is visible beside doctrines, inoculations, and reflexes.

Primary files carrying this slice:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\cortex.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\templates\index.html`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.css`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`

### Verification

Focused learning-loop verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_cli.py tests/test_recall.py -q`
- Result: `100 passed`

Static/runtime checks passed:

- `.\.venv\Scripts\ruff.exe check src/openzues/app.py src/openzues/cli.py src/openzues/schemas.py src/openzues/services/cortex.py tests/test_cli.py`
- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What is now true

- Hermes parity inside Zues now includes:
  - auto-discovered Hermes skills
  - Hermes-style toolset posture
  - restart-safe recall
  - learned review passes that turn durable run history into explicit future guidance
- The learning loop is no longer implicit. Operators and future autonomous runs can now see which tool posture worked, when checkpoint-first recovery should be preferred, and when proof posture drifted.

### What remains

The next major Hermes gaps are still:

1. post-task skill creation or promotion from repeated learned reviews
2. richer memory-provider parity beyond persisted missions and checkpoints
3. broader Hermes CLI/TUI ergonomics
4. executor backend parity
5. gateway and channel delivery parity
6. ACP/plugin and research extras

### Next best slice

Do not jump to channels next. The next highest-leverage Hermes seam is to let the new learning reviews feed action back into skills and setup posture.

Recommended next slice:

- promote repeated learned tool postures into saved workspace defaults or skill pins
- let review evidence create candidate micro-skills or skill-gap recommendations automatically
- keep using the same cortex/recall/toolset contract instead of inventing a second learning subsystem

### Operator handoff

- Completed: landed Hermes learning reviews across cortex, API, CLI, and dashboard shell chrome.
- Verified: `100 passed` across app, CLI, and recall tests; Ruff, `node --check`, and `compileall` all passed.
- Next step: wire repeated review evidence back into saved skill pins or workspace launch defaults so Hermes learning starts changing future launches automatically.
- Blockers: none.
- Verified: `176 passed` across the merged recall/toolset/control-plane pack, plus JS syntax and Python compile checks.
- Next step: build the Hermes learning-loop seam on top of recall, checkpoints, and doctrine so Zeus can start turning repeated work into reusable skills and guidance automatically.
- Blockers: no product blocker. The only operational caveat is the normal one: restart the live OpenZues server before expecting the new Hermes recall/toolset surfaces to appear in the running process.

## Update: Hermes Doctor + Runtime Profile Control

Date: 2026-04-11

### Completed this turn

- Closed the next Hermes control-plane seam after learning reviews: OpenZues now has a durable Hermes platform layer that inventories the remaining Hermes import domains and actively promotes learned posture back into saved defaults.
- Added a background Hermes learning-promotion loop that reads durable mission history, reuses the existing cortex learning reviews, and auto-promotes repeated winning tool posture into:
  - saved task blueprints for the project
  - the saved gateway bootstrap profile for that workspace
- Added a richer Hermes memory/provider inventory on top of the existing recall seam:
  - `OpenZues Recall`
  - `MemPalace`
  - discovered Hermes memory providers from `hermes-agent-main/plugins/memory/*`
- Added executor backend profile inventory for the Hermes runtime matrix:
  - local Codex desktop lanes
  - workspace shell
  - Docker
  - SSH
  - Modal
  - Daytona
  - Singularity
- Added Hermes plugin, delivery, ACP, and extra-surface doctor decks by inspecting the Hermes source tree and live Codex lane inventories:
  - plugins and MCP/app inventory
  - gateway/channel delivery surfaces
  - ACP adapter seam
  - TUI/research extras
- Added a top-level Hermes doctor surface and runtime update surface:
  - `GET /api/hermes/doctor`
  - `GET /api/runtime/update`
  - `openzues doctor`
  - `openzues update status`
- Promoted the Hermes runtime profile from read-only telemetry into a real saved control seam:
  - `GET /api/hermes/profile`
  - `PUT /api/hermes/profile`
  - `openzues hermes profile`
  - `openzues hermes profile set ...`
  - dashboard form for preferred memory provider, preferred executor, and inventory/autopromote toggles

Primary files carrying this slice:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_platform.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\database.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\settings.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\templates\index.html`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_hermes_platform.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`

### Verification

Focused Hermes platform verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_hermes_platform.py tests/test_app.py tests/test_cli.py -q`
- Result: `111 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_cli.py tests/test_recall.py tests/test_database.py tests/test_missions.py -q`
- Result: `152 passed`

Static/runtime checks passed:

- `.\.venv\Scripts\ruff.exe check src/openzues/app.py src/openzues/cli.py src/openzues/schemas.py src/openzues/services/hermes_platform.py tests/test_app.py tests/test_cli.py`
- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues tests/test_hermes_platform.py`

### What is now true

- Hermes priority imports now landed in OpenZues at the control-plane level:
  1. learning promotion loop
  2. richer memory/provider layer
  3. doctor/setup/update CLI parity
  4. executor backend profiles
  5. ACP/plugin architecture inventory
  6. gateway/channel delivery inventory
  7. TUI/research extras inventory
- The learning loop is no longer just advisory. Repeated winning tool posture can now flow back into saved task and gateway defaults automatically.
- Hermes memory/provider and executor posture are no longer hard-coded guesses. Operators can now save the preferred provider and executor explicitly through API, CLI, and dashboard.
- The lower-priority Hermes domains are now mapped and visible in one doctor contract instead of being scattered across notes or hidden source-tree assumptions.

### What remains

The remaining Hermes gaps are now mostly depth, not visibility:

1. external memory-provider execution beyond inventory and saved preference
2. real executor handoff beyond detection/inventory
3. live gateway/channel transport execution rather than doctor-grade parity mapping
4. ACP server mode rather than ACP seam visibility
5. deeper TUI/chat ergonomics and research runtime execution rather than inventory

### Next best slice

The next strongest Hermes move is no longer “what exists?” but “which mapped surfaces should become executable next?”

Recommended next slice:

- bind the saved Hermes executor profile into mission launch policy so `workspace_shell`, `docker_backend`, and future remote backends can influence how Zeus stages a run
- let the saved memory-provider preference shape recall/memory guidance so MemPalace or discovered Hermes providers become part of the live launch contract rather than only doctor output
- keep gateway/channel and ACP surfaces honest: upgrade them from doctor/inventory parity to executable parity one seam at a time instead of pretending transport parity is already finished

### Operator handoff

- Completed: landed the Hermes platform service, learning-promotion loop, memory/executor/provider inventories, doctor/update surfaces, and writable Hermes runtime profile across API, CLI, and dashboard.
- Verified: `111 passed` in the focused Hermes platform pack, `152 passed` in the broader changed-surface pack, plus Ruff, JS syntax, and Python compile checks.
- Next step: bind the saved Hermes executor and memory-provider defaults into actual mission launch behavior so the runtime profile stops at policy less often and starts affecting execution more directly.
- Blockers: none in the product surface; only the usual operational caveat that the live OpenZues server must be restarted before the currently running process reflects the new Hermes dashboard controls.

## Update: Hermes Runtime Profile Binding

Date: 2026-04-11

### Completed this turn

- Closed the next Hermes execution seam after profile persistence: the saved Hermes runtime profile now shapes real OpenZues behavior instead of staying a passive preference record.
- Added a reusable Hermes runtime-profile helper layer that turns saved memory-provider and executor preferences into:
  - human-readable launch summaries
  - mission objective guidance
  - turn-prompt runtime posture instructions
  - consistent labels across API and dashboard surfaces
- Wired the saved runtime profile into launch-draft generation:
  - onboarding/bootstrap mission drafts now include the preferred memory provider and executor
  - Ops Mesh task drafts now include the same runtime posture summary and contract lines
  - launchpad opportunity drafts and dream-pass drafts now carry the same saved Hermes runtime posture instead of silently falling back to generic defaults
  - gateway bootstrap summaries now surface the saved Hermes memory and executor posture directly
- Wired the same profile into live mission execution:
  - mission views now expose the saved preferred memory/executor fields
  - autonomous turn prompts now inherit executor-profile and memory-provider guidance instead of reusing a generic launch contract
- Wired the saved memory-provider preference into recall ranking:
  - the recall deck now tells the operator which provider is preferred
  - MemPalace-first posture now boosts direct memory-proof and memory-maintenance runs so the recall surface follows the saved Hermes contract rather than treating all prior runs equally

Primary files carrying this slice:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_runtime_profile.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\missions.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\recall.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_bootstrap.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_recall.py`

### Verification

Focused runtime-binding verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_recall.py tests/test_cli.py tests/test_missions.py tests/test_ops_mesh.py -q`
- Result: `178 passed`

Static/runtime checks passed:

- `.\.venv\Scripts\ruff.exe check src/openzues/app.py src/openzues/services/missions.py src/openzues/services/gateway_bootstrap.py src/openzues/services/ops_mesh.py src/openzues/services/recall.py src/openzues/services/hermes_runtime_profile.py tests/test_app.py tests/test_recall.py`
- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What is now true

- Hermes runtime preferences now influence:
  - bootstrap launch drafts
  - saved task drafts in Ops Mesh
  - launchpad and dream drafts
  - live mission prompt posture
  - recall ordering and summary text
  - gateway bootstrap default summaries
- OpenZues no longer treats Hermes memory/executor posture as doctor-only metadata. Those preferences now participate in how Zeus stages and continues work.

### What remains

The next Hermes gaps are now deeper execution seams:

1. executor-specific backend handoff beyond prompt posture
2. external memory-provider execution beyond recall prioritization and protocol guidance
3. gateway/channel transport execution rather than inventory parity
4. ACP server mode rather than ACP seam visibility
5. deeper Hermes chat/TUI ergonomics

### Next best slice

Recommended next slice:

- bind executor profiles into stronger launch orchestration decisions and backend-specific handoff policies
- upgrade memory-provider preference from recall bias into provider-specific execution hooks where those surfaces are available
- keep the next Hermes slice executable, not inventory-only

### Operator handoff

- Completed: landed Hermes runtime-profile binding across launch drafts, live mission prompts, recall posture, and gateway bootstrap summaries.
- Verified: `178 passed` in the focused runtime-binding pack, plus Ruff, JS syntax, and Python compile checks.
- Next step: make executor profiles and external memory providers affect actual backend execution decisions, not just the prompt contract.
- Blockers: none.

## Update: Executor-Aware Launch Orchestration

Date: 2026-04-11

### Completed this turn

- Closed the next Hermes execution seam after runtime-profile binding: executor preference now changes actual launch routing and mission start behavior instead of only changing prompt posture.
- Added a shared Hermes executor launch contract that now drives:
  - launch-route candidate ranking
  - launch-route readiness vs repair posture
  - mission start blocking when an executor cannot actually be armed
- Workspace Shell Profile now influences lane choice directly:
  - workspace-affinity launches now prefer connected lanes with a saved cwd over generic connected lanes when no exact workspace match exists
  - launch routes now mark Workspace Shell launches as repair if no concrete workspace path exists
- External executor profiles now affect launch eligibility honestly instead of cosmetically:
  - `docker`, `ssh`, `modal`, `daytona`, and `singularity` now check host command availability plus workspace-path readiness
  - when those prerequisites are missing, the launch route shifts to `repair`
  - mission execution now stops before opening a new thread and blocks the mission with an explicit executor error instead of pretending the run is healthy
- Codex Desktop preference is now part of route orchestration too:
  - desktop transport remains the preferred posture
  - when no connected desktop lane exists, the route now names the fallback explicitly instead of silently masking the executor mismatch

Primary files carrying this slice:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_runtime_profile.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\launch_routing.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\missions.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_missions.py`

### Verification

Focused executor-orchestration verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_missions.py -q -k "workspace_shell_executor_prefers_lane_with_saved_cwd or docker_executor_marks_launch_route_for_repair or run_now_blocks_when_executor_backend_is_unavailable or remote_workspace_affinity_prefers_project_lane_and_persists_last_route or hermes_profile_shapes_bootstrap_launch_draft or run_now_creates_thread_and_turn"`
- Result: `6 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_recall.py tests/test_cli.py tests/test_missions.py tests/test_ops_mesh.py -q`
- Result: `183 passed`

Static/runtime checks passed:

- `.\.venv\Scripts\ruff.exe check src/openzues/services/hermes_runtime_profile.py src/openzues/services/launch_routing.py src/openzues/services/missions.py tests/test_app.py tests/test_missions.py`
- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues`

### What is now true

- Hermes executor selection now changes:
  - which lane OpenZues prefers for a launch
  - whether a launch is `ready`, `staged`, or `repair`
  - whether a mission is allowed to start at all
- OpenZues no longer treats missing executor prerequisites as soft prose. For unsupported or unarmed executor profiles, the control plane now blocks the launch and says why.

### What remains

The next executor-depth gaps are now narrower and more concrete:

1. real backend-specific invocation for external executors instead of control-plane gating only
2. executor-specific thread/bootstrap defaults beyond lane selection and blocking
3. pairing executor profiles with deeper memory-provider execution seams

### Next best slice

Recommended next slice:

- start wiring one real external executor path end to end, most likely `workspace_shell` first and then `docker`
- keep the same launch-contract seam as the source of truth so new backend execution plugs into existing routing, repair, and mission-blocking behavior
- avoid adding parallel executor state machines; extend the current control plane instead

### Operator handoff

- Completed: landed executor-aware launch routing and executor-aware mission start blocking on top of the Hermes runtime profile.
- Verified: `183 passed` in the broader control-plane pack, plus Ruff, JS syntax, and Python compile checks.
- Next step: wire a real executor backend path behind the now-honest launch contract, starting with the smallest executable backend seam.
- Blockers: none.

## Update: Gateway-Aware CLI Queue Action

Date: 2026-04-12

### Recovered context

- Re-entered from the existing Hermes/OpenClaw parity spine after stabilizing the workstation and rerunning the broader changed-surface regression packs.
- Verified that the current branch already had a shared gateway-aware planning contract across doctor, radar, launchpad, interference, control chat, the autonomous attention queue, and the newer `openzues continue` command.
- Continued to the next bounded operator CLI seam on that same spine instead of broadening scope: give the attention queue the same preview/execute terminal affordance that `continue` already had.

### Completed this turn

- Added a top-level `openzues queue` command that reuses the existing autonomous attention-queue planner instead of inventing a second CLI policy layer.
- Added explicit preview vs execute behavior:
  - `openzues queue --plan` shows the next bounded attention-queue move without firing it
  - `openzues queue` executes one queue cycle through the existing `ControlChatService.tick_attention_queue(...)` path
- Reused the same operator dashboard contract for both terminal command paths:
  - gateway capability posture
  - launchpad opportunities
  - radar signals
  - saved Hermes runtime preferences that shape launchpad construction
- Kept the command honest about degraded gateway posture:
  - when no bounded `gateway_repair` draft exists yet, the queue command now previews and records the same escalation message the dashboard queue would surface
  - the CLI does not fake a recovery launch just to appear autonomous
- Added dedicated human-output rendering for queue actions so terminal output now exposes:
  - mode
  - executed flag
  - action kind
  - queue status
  - signal id
  - target/opportunity/mission references when present

Primary files carrying this turn's delta:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`

### Verification

Focused CLI queue coverage passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q`
- Result: `14 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_missions.py tests/test_ops_mesh.py tests/test_recall.py tests/test_skillbook.py tests/test_hermes_platform.py -q`
- Result: `199 passed`

Static/runtime checks passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues tests/test_cli.py`

### What is now true

- The operator CLI now has two bounded gateway-aware action commands on top of the same planner spine:
  - `openzues continue`
  - `openzues queue`
- Preview and execute semantics are now explicit for both control-chat and queue-style operator actions.
- Terminal operators can inspect the next autonomous queue move without needing the dashboard, and the CLI still follows the same repair-first posture already enforced elsewhere.

### What remains

The larger Hermes/OpenClaw parity gaps are still the same broad families:

1. broader operator CLI parity beyond recall, learn, gateway doctor, `continue`, and `queue`
2. channel runtime and delivery execution rather than delivery inventory
3. browser-control runtime parity
4. canvas runtime parity
5. nodes, voice, companion apps, and packaging matrix

Within the current control-plane seam, the next leverage is still bounded command-surface depth rather than another planning rewrite.

### Next best slice

Recommended next slice:

- add one more bounded operator CLI action on top of the same shared planners, most likely a focused recover/harden action that reuses the existing control-chat decision paths
- keep the CLI thin and planner-backed instead of drifting into a parallel command-policy system
- after that, either broaden operator CLI parity further or pivot back to executable Hermes/OpenClaw surfaces outside the planning spine

### Operator handoff

- Completed: landed `openzues queue` with preview and execute modes on top of the existing gateway-aware attention-queue planner, and added dedicated terminal rendering plus focused CLI coverage.
- Verified: `14 passed` in the full CLI pack, `199 passed` in the broader changed-surface pack, and Python compile checks passed.
- Next step: keep extending bounded operator CLI parity on the same planner spine, or pivot back to a deeper executable runtime seam once the command surface feels complete enough.
- Blockers: none.

## Update: Gateway-Aware Recover + Harden CLI

Date: 2026-04-12

### Recovered context

- Continued directly from the new `openzues queue` seam instead of widening scope.
- Verified that the shared control-chat planner already knew how to choose:
  - gateway repair before unsafe follow-through
  - checkpoint recovery from failed runs
  - checkpoint hardening from finished runs
- The gap was only terminal affordance: the operator CLI still exposed `continue`, but not explicit recovery or hardening actions backed by that same planner.

### Completed this turn

- Added a shared CLI helper for planner-backed control-chat actions so terminal commands can reuse one execution contract instead of duplicating plan/submit wiring.
- Added a top-level `openzues recover` command:
  - `openzues recover --plan` previews the next gateway-aware recovery move
  - `openzues recover` executes through the existing `ControlChatService.submit(...)` path
- Added a top-level `openzues harden` command:
  - `openzues harden --plan` previews the next gateway-aware hardening move
  - `openzues harden` executes through the same shared control-chat submission path
- Kept the CLI thin and honest:
  - recover/harden still respect gateway repair posture
  - recover/harden still reuse mission drafts and launch opportunities from the existing planner
  - no second CLI-only autonomy policy was introduced
- Tightened CLI coverage so the new commands are verified as prompt shims over the planner/submit spine rather than only smoke-tested for output.

Primary files carrying this turn's delta:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`

### Verification

Focused CLI coverage passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q`
- Result: `16 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_database.py tests/test_manager.py tests/test_missions.py tests/test_ops_mesh.py tests/test_recall.py tests/test_skillbook.py tests/test_hermes_platform.py -q`
- Result: `199 passed`

Static/runtime checks passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues tests/test_cli.py`

### What is now true

- The operator CLI now exposes four gateway-aware control surfaces on the same planner spine:
  - `openzues continue`
  - `openzues recover`
  - `openzues harden`
  - `openzues queue`
- Recovery and hardening now work as explicit operator verbs in the terminal instead of being trapped behind freeform chat phrasing.
- The CLI surface still inherits the same repair-first discipline as the dashboard/chat planner, so it stays autonomous without getting reckless.

### What remains

The bigger Hermes/OpenClaw parity gaps are still outside this bounded CLI slice:

1. broader operator CLI parity beyond the current control/recall/learn/gateway surfaces
2. executable delivery/runtime surfaces instead of inventory-only channel parity
3. browser-control runtime parity
4. canvas runtime parity
5. nodes, voice, companion apps, and packaging matrix

Within the operator CLI seam itself, the next leverage is likely status/review-style bounded commands or a deeper runtime action surface rather than more planner duplication.

### Next best slice

Recommended next slice:

- keep extending the operator terminal surface with another bounded command only if it still rides the shared planner/runtime contract
- otherwise pivot back into executable Hermes/OpenClaw runtime seams, where parity gains are now more meaningful than additional prompt wrappers
- keep the checkpoint trail fresh after each bounded slice so restart-safe continuity stays real

### Operator handoff

- Completed: landed explicit `openzues recover` and `openzues harden` commands on the shared gateway-aware control-chat planner, backed by one thin CLI execution helper.
- Verified: `16 passed` in the CLI pack, `199 passed` in the broader changed-surface pack, and Python compile checks passed.
- Next step: either add one more bounded operator action on the same shared contract or pivot back to deeper Hermes/OpenClaw runtime parity.
- Blockers: none.

## Update: Active Delivery Route Testing

Date: 2026-04-12

### Recovered context

- Pivoted away from adding another small operator verb and back into a real Hermes/OpenClaw runtime seam.
- Verified that OpenZues already had real webhook delivery plumbing through Ops Mesh notification routes, but operators still had no first-class way to fire a route test and confirm a delivery path before waiting on a live mission alert.
- Chose the smallest runtime slice that adds actual product capability instead of more inventory: make notification routes directly testable from the service, API, CLI, and dashboard.

### Completed this turn

- Added a real route-test execution path in Ops Mesh:
  - picks a safe synthetic event type that matches the route's configured patterns
  - sends a direct webhook test ping through the existing webhook transport
  - persists `last_delivery_at`, `last_result`, and `last_error` exactly like real deliveries do
- Added `POST /api/notification-routes/{route_id}/test` so delivery health can be exercised over the API without manufacturing a fake mission event.
- Added `openzues routes test <route_id>` so operators can fire a delivery ping from the terminal and get a structured result back.
- Added a dashboard `Test Route` action beside each notification route so the delivery seam is now operable from the product surface instead of only through code or logs.
- Updated Hermes Doctor delivery posture so it stops underselling the gateway seam once active webhook routes exist:
  - the gateway/webhook delivery item can now move to `ready`
  - the delivery deck now reports active testable webhook delivery instead of pure inventory-only posture

Primary files carrying this turn's delta:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_platform.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`

### Verification

Focused delivery/runtime verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_ops_mesh.py -q -k "notification_route or route_test or emits_derived_inbox_notifications_once or emits_reflex_and_task_attention_notifications"`
- Result: `4 passed`

Focused CLI verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "routes_test_command or recover or harden or queue or continue or gateway"`
- Result: `12 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_ops_mesh.py tests/test_cli.py tests/test_hermes_platform.py -q`
- Result: `154 passed`

Static/runtime checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues tests/test_cli.py tests/test_ops_mesh.py`

### What is now true

- Notification routes are no longer just configurable. They are actively testable from:
  - Ops Mesh service code
  - API
  - CLI
  - dashboard UI
- Delivery health now leaves durable evidence in the route record itself through the same `last_result` / `last_error` posture operators already watch.
- Hermes Doctor delivery posture is closer to the truth: OpenZues now has a real, operator-usable webhook delivery seam, not only delivery inventory.

### What remains

The larger Hermes/OpenClaw runtime parity gaps are still broader than this slice:

1. richer non-webhook delivery/channel runtimes
2. deeper executor backend handoff beyond the current launch and workspace-shell posture
3. browser-control runtime parity
4. canvas runtime parity
5. nodes, voice, companion apps, and packaging matrix

### Next best slice

Recommended next slice:

- keep pushing delivery only if the next step adds another executable seam rather than more catalog copy
- otherwise return to executor-depth parity and wire another backend truthfully end to end
- preserve the same pattern used here: runtime action first, then doctor/operator surfaces that accurately describe it

### Operator handoff

- Completed: added active notification-route testing across service, API, CLI, and dashboard, and updated Hermes Doctor delivery posture to reflect a real webhook execution seam.
- Verified: focused delivery checks passed (`4 passed`), focused CLI checks passed (`12 passed`), the broader changed-surface pack passed (`154 passed`), JS syntax passed, and Python compile checks passed.
- Next step: either extend executable delivery beyond webhook testability or return to executor-depth parity for the next non-inventory Hermes runtime seam.
- Blockers: none.

## Update: Explicit Workspace Shell Arming

Date: 2026-04-12

### Recovered context

- Returned to the executor-depth seam after landing active webhook route testing.
- Verified that `workspace_shell` was already real at mission runtime: `run_now(...)` can promote shell-first work onto a stdio lane, but that behavior was still mostly implicit and awkward to operate directly.
- Chose the next bounded executor slice that adds a real operator action instead of another advisory card: let operators explicitly arm a shell-backed lane from saved workspace state.

### Completed this turn

- Added a first-class Hermes executor action to arm the workspace-shell profile:
  - derives a workspace from explicit `cwd` when provided
  - otherwise falls back through saved gateway bootstrap workspace, preferred project, single saved project, or lane cwd
  - creates or reuses a shell-backed stdio lane through the existing runtime manager
- Added `POST /api/hermes/executors/workspace-shell/arm` so the shell profile can be prepared from the product API with the same management posture as other mutating control-plane actions.
- Added `openzues hermes arm-shell` so terminal operators can arm the shell profile directly and get a structured result back.
- Added a Hermes Doctor UI action button so the profile is operable from the dashboard, not just inferred from later mission behavior.
- Tightened the doctor/executor truth:
  - the workspace-shell executor item now distinguishes staged shell-backed lanes from genuinely armed connected ones
  - the executor deck now advertises explicit arm capability
  - workspace-shell prompt guidance now names the lane-arming step instead of treating it like a hidden implementation detail

Primary files carrying this turn's delta:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_platform.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_runtime_profile.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_hermes_platform.py`

### Verification

Focused executor verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_hermes_platform.py -q`
- Result: `2 passed`

Focused API/runtime verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "workspace_shell"`
- Result: `2 passed`

Focused CLI verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "arm_shell or routes_test_command or recover or harden or queue or continue or gateway"`
- Result: `13 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_cli.py tests/test_hermes_platform.py tests/test_missions.py -q`
- Result: `174 passed`

Static/runtime checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues tests/test_cli.py tests/test_app.py tests/test_hermes_platform.py`

### What is now true

- `workspace_shell` is no longer just a runtime behavior OpenZues might discover later during mission execution.
- Operators can now deliberately arm the shell executor from:
  - Hermes platform service
  - API
  - CLI
  - Hermes Doctor UI
- Hermes Doctor is more honest about executor posture:
  - shell-backed stdio lanes are recognized as their own stage of readiness
  - the workspace-shell profile now advertises direct arm capability instead of only passive inventory language

### What remains

The larger Hermes/OpenClaw runtime gaps are still broader than this slice:

1. richer external executor backends beyond workspace shell
2. broader non-webhook delivery and channel runtime execution
3. browser-control runtime parity
4. canvas runtime parity
5. nodes, voice, companion apps, and packaging matrix

### Next best slice

Recommended next slice:

- either keep going deeper on executor truth by wiring the next backend beyond workspace shell
- or pivot back to another executable runtime seam with the same pattern: real operator action first, then doctor/UI posture that accurately reflects it
- avoid broadening back into inventory-only parity work unless it unlocks a concrete next runtime action

### Operator handoff

- Completed: turned workspace-shell execution from a mostly implicit mission-start behavior into an explicit Hermes action across service, API, CLI, and dashboard.
- Verified: focused Hermes, app, and CLI checks passed; the broader app/CLI/Hermes/missions pack passed (`174 passed`); JS syntax passed; Python compile checks passed.
- Next step: either wire the next executor backend truthfully or choose another non-inventory runtime seam of similar leverage.
- Blockers: none.

## Update: Docker Backend Staging Profile

Date: 2026-04-12

### Recovered context

- Returned to the executor-depth seam after landing explicit workspace-shell arming.
- Verified that Docker already existed in the Hermes/OpenZues profile vocabulary, but only as a discovery card plus launch gating. Operators still had no durable way to prepare a Docker profile or see what image/workspace posture had actually been staged.
- Chose the next bounded executor slice that adds a real operator action without pretending full containerized mission execution is already finished: arm Docker as a truthful staged backend profile through the current control-plane lane model.

### Completed this turn

- Added a first-class Docker backend arm action to the Hermes platform service:
  - derives the workspace using the same saved-gateway/project/lane fallback chain as workspace-shell
  - requires the local `docker` command to be present before arming
  - reuses or creates a shell-backed stdio control lane for the target workspace
  - persists the staged Docker profile in the Hermes runtime profile with workspace, image, mount posture, control lane id, and timestamps
- Added `POST /api/hermes/executors/docker/arm` so the Docker staging profile can be prepared from the product API under the same management-gated mutation posture as other control-plane executor actions.
- Added `openzues hermes arm-docker` so terminal operators can arm the Docker profile directly, optionally override the image, and choose whether the staged profile should mount the host workspace.
- Extended Hermes runtime profile views so saved executor-profile state is visible through API/doctor responses instead of being trapped in internal JSON.
- Tightened executor truth in the doctor and prompt layers:
  - Docker now stops being a passive “command exists” card once it is armed
  - Hermes Doctor surfaces Docker as an explicit armable backend with saved image/workspace posture
  - executor guidance can now name the staged Docker image/workspace profile instead of only speaking in generic backend prose
- Added a Docker arm button to the Hermes Doctor UI so operators can prepare the staged backend from the dashboard as well as API/CLI.

Primary files carrying this turn's delta:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_platform.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_runtime_profile.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\missions.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_hermes_platform.py`

### Verification

Focused Hermes executor verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_hermes_platform.py -q`
- Result: `3 passed`

Focused API/runtime verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "docker_arm_api or workspace_shell_arm_api or docker_executor_marks_launch_route_for_repair"`
- Result: `3 passed`

Focused CLI verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "arm_shell or arm_docker"`
- Result: `2 passed`

Focused mission executor verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_missions.py -q -k "workspace_shell or executor_backend_is_unavailable"`
- Result: `2 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_cli.py tests/test_hermes_platform.py tests/test_missions.py tests/test_ops_mesh.py -q`
- Result: `201 passed`

Static/runtime checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues tests/test_app.py tests/test_cli.py tests/test_hermes_platform.py tests/test_missions.py`

### What is now true

- Docker is no longer only a theoretical Hermes executor target inside OpenZues.
- Operators can now deliberately arm a staged Docker backend profile from:
  - Hermes platform service
  - API
  - CLI
  - Hermes Doctor UI
- The staged Docker posture survives restarts because it is persisted in the Hermes runtime profile.
- Hermes Doctor can now distinguish:
  - bare Docker CLI availability
  - a saved Docker workspace/image profile
  - whether that staged backend is anchored to a connected control lane

### What remains

The next executor-depth gaps are narrower again:

1. fuller backend-specific invocation beyond staged Docker control-lane preparation
2. the same explicit arm posture for the next external backend after Docker
3. deeper coupling between executor profiles, delivery surfaces, and memory-provider runtime choices

### Next best slice

Recommended next slice:

- keep going one backend deeper only if the next import produces another real operator action or executable preflight, not just more catalog prose
- the most natural follow-on is either SSH staging parity or a Docker-specific execution/preflight action that proves more of the runtime contract end to end
- keep extending the current control plane instead of introducing a second executor subsystem

### Operator handoff

- Completed: turned Docker from a passive executor inventory item into an explicit staged backend profile across service, API, CLI, doctor, and dashboard.
- Verified: focused Hermes/API/CLI/mission packs passed, the broader changed-surface pack passed (`201 passed`), JS syntax passed, and Python compile checks passed.
- Next step: either give Docker another truthful execution/preflight seam or apply the same explicit-arm pattern to the next external backend.
- Blockers: none.

## Update: Docker Backend Preflight

Date: 2026-04-12

### Recovered context

- Continued directly from the staged Docker backend slice after switching the live Hermes runtime preference to `docker`.
- Verified that Docker arming already persisted a real workspace/image/control-lane profile, but OpenZues still had no truthful way to prove whether the Docker backend was actually usable on the host.
- Chose the next bounded executor seam that adds real operational truth instead of more inventory language: a Docker preflight action that checks the CLI, daemon, and staged image and feeds the result back into Hermes posture.

### Completed this turn

- Added a first-class Docker preflight action to the Hermes platform service:
  - resolves workspace and image from explicit overrides, the staged Docker profile, or the saved gateway workspace fallback chain
  - checks that the `docker` command is present on the host
  - captures Docker CLI version
  - checks daemon reachability with `docker info`
  - checks whether the staged image is already present locally with `docker image inspect`
- Persisted Docker preflight evidence into the Hermes runtime profile so the result survives restarts:
  - `last_preflight_status`
  - `last_preflight_summary`
  - `command_path`
  - `docker_version`
  - `daemon_version`
  - `image_present`
- Added `POST /api/hermes/executors/docker/preflight` so the product API can run the same Docker proof from the management surface.
- Added `openzues hermes preflight-docker` so terminal operators can validate the staged Docker profile directly.
- Extended Hermes Doctor/runtime profile output so saved executor-profile state now includes the last Docker preflight posture instead of only the staged arm data.
- Added a `Preflight Docker` action to the Hermes Doctor UI so Docker truth can be refreshed from the dashboard as well as API/CLI.
- Tightened Docker executor guidance in prompt construction so Docker now speaks from the latest saved preflight result instead of generic backend prose.

Primary files carrying this turn's delta:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_platform.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_runtime_profile.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_hermes_platform.py`

### Verification

Focused Hermes executor verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_hermes_platform.py -q`
- Result: `4 passed`

Focused API/runtime verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "docker_preflight_api or docker_arm_api or workspace_shell_arm_api or docker_executor_marks_launch_route_for_repair"`
- Result: `4 passed`

Focused CLI verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "arm_docker or preflight_docker or arm_shell"`
- Result: `3 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_cli.py tests/test_hermes_platform.py tests/test_missions.py tests/test_ops_mesh.py -q`
- Result: `206 passed`

Static/runtime checks passed:

- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src/openzues tests/test_app.py tests/test_cli.py tests/test_hermes_platform.py`

### What is now true

- Docker is no longer just staged in OpenZues. It now has a truthful proof action that can distinguish:
  - Docker missing on the host
  - daemon unreachable
  - image not yet present
  - backend ready for the staged workspace/image profile
- That proof survives restart because the result is stored in the Hermes runtime profile.
- Hermes Doctor and runtime profile output now expose Docker as an armable and preflightable backend, not just a command-discovery card.

### What remains

The next Docker/executor gaps are narrower again:

1. a deeper Docker execution seam beyond preflight and staging
2. the same explicit arm + preflight truth for SSH or another external backend
3. tighter coupling between executor proof, launch routing, and mission-start behavior

### Next best slice

Recommended next slice:

- either add a Docker-specific launch/preflight promotion rule so routed missions react differently when Docker is fully ready versus only staged
- or give SSH the same explicit arm/preflight truth before broadening into more executor families
- keep extending the current control plane instead of inventing a second executor orchestration layer

### Operator handoff

- Completed: switched Hermes to a Docker-first runtime preference, added a real Docker preflight action across service/API/CLI/dashboard, and persisted its result in the runtime profile.
- Verified: focused Hermes/API/CLI packs passed, the broader changed-surface pack passed (`206 passed`), JS syntax passed, and Python compile checks passed.
- Next step: deepen Docker into launch behavior or carry the same explicit-proof pattern to SSH.
- Blockers: none.

## Update: Docker Control Lane Preference

Date: 2026-04-12

### Recovered context

- Continued immediately after the Docker preflight slice was live enough to prove CLI/daemon/image readiness.
- Found the remaining posture gap was not Docker itself. The staged Docker profile was still reusing a `stdio` workspace-shell lane that launched `codex app-server` directly, which on this Windows host stayed vulnerable to the alias/access-denied path we have been trying to avoid.
- Confirmed the repo already had a healthier control lane available: `Local Codex Desktop` on the same OpenZues workspace.

### Completed this turn

- Taught Docker backend arming to prefer a real desktop control lane before falling back to the shell-backed workspace profile:
  - first prefer a desktop lane already pointed at the same workspace and already connected
  - then prefer any desktop lane already pointed at the same workspace
  - then prefer any connected desktop lane
  - only fall back to shell-backed staging when no usable desktop lane exists
- Kept the fallback behavior intact for environments where a desktop lane is not available, so the Docker backend still has a safe non-desktop path.
- Updated focused API/CLI/service tests so Docker arm now asserts reuse of the desktop bridge rather than the weaker `stdio` alias path.
- Restarted the live OpenZues server on `http://127.0.0.1:8884`, re-armed Docker, and verified the runtime now reuses `Local Codex Desktop` as control instance `2`.
- Pulled the staged Docker image locally and reran live preflight so the backend moved all the way from `staged` to `ready`.

Primary files carrying this turn's delta:

- `C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\hermes_platform.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_hermes_platform.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`
- `C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`

### Verification

Focused Hermes executor verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_hermes_platform.py -q`
- Result: `4 passed`

Focused API/runtime verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -k "docker_preflight_api or docker_arm_api or workspace_shell_arm_api or docker_executor_marks_launch_route_for_repair"`
- Result: `4 passed`

Focused CLI verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q -k "arm_docker or preflight_docker or arm_shell"`
- Result: `3 passed`

Broader changed-surface verification passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_cli.py tests/test_hermes_platform.py tests/test_missions.py tests/test_ops_mesh.py -q`
- Result: `206 passed`

Static/runtime checks passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues tests/test_app.py tests/test_cli.py tests/test_hermes_platform.py`

Live runtime verification on `http://127.0.0.1:8884` passed:

- `POST /api/hermes/executors/docker/arm` reused `Local Codex Desktop`
- the saved Docker executor profile now points at `control_instance_id = 2`
- `POST /api/hermes/executors/docker/preflight` returned `status = ready`
- `GET /api/hermes/profile` persisted `last_preflight_status = ready`
- `GET /api/hermes/doctor` now reports the Docker executor card as `ready`

### What is now true

- Docker no longer depends on the weaker Windows `codex` alias path just to look healthy in OpenZues.
- Hermes now prefers the same real desktop bridge that the live control plane is already using, which makes Docker posture consistent with the rest of the product.
- The Docker backend is fully operator-ready on this host:
  - preferred executor is `docker`
  - staged image is present locally
  - preflight passes
  - Doctor reports the Docker executor as `ready`

### Next best slice

Recommended next slice:

- let Hermes promote Docker from a ready backend profile into real launch-policy decisions, so mission drafts can prefer Docker when the backend is green instead of treating it as an informational sidecar
- or apply the same explicit arm + preflight + control-lane-truth pattern to SSH so the next external backend is equally honest
- keep the control-lane selection logic centralized inside Hermes instead of scattering backend-choice heuristics into missions or the dashboard

### Operator handoff

- Completed: taught Docker arm to reuse the real desktop bridge, restarted live OpenZues on `8884`, pulled the staged Docker image, and verified the Docker backend is fully ready end to end.
- Verified: focused Hermes/API/CLI packs passed, the broader changed-surface pack passed (`206 passed`), Python compile checks passed, and live API verification confirmed `control_instance_id = 2` plus Docker Doctor status `ready`.
- Next step: let mission launch policy actually consume the now-ready Docker posture, or give SSH the same explicit truth path next.
- Blockers: none.
