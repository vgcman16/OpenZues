# MemPalace Integration Checkpoint

Date: 2026-04-11
Source of truth: `C:\Users\skull\OneDrive\Documents\mempalace-main\mempalace-main`
Target: `C:\Users\skull\OneDrive\Documents\OpenZues`

## Re-entry context

- Recovered from the prior OpenClaw parity lane, then continued on the redirected Zeus x MemPalace integration seam without redoing verified gateway work.
- Reconfirmed the smallest durable MemPalace fit for Zeus:
  - reuse tracked integrations, Ops Mesh inventory, onboarding bootstrap, and mission/task prompt construction
  - do not invent a second memory subsystem
  - keep route selection untouched unless a real failing proof demands it
- The right MemPalace contract in Zeus is:
  - a shared operating protocol in launch prompts and live mission prompts
  - a first-class bootstrap preset so operators do not have to hand-enter MemPalace details
  - lane-gap guidance in Ops Mesh when project memory is expected but not actually published on a connected lane
  - an automatic maintenance loop that reuses scheduled Zeus task blueprints instead of raw backend-side memory jobs

## Completed in this re-entry

- Added shared MemPalace defaults and detection helpers in `src/openzues/services/memory_protocol.py`.
- Landed the first real behavior seam:
  - tracked MemPalace integrations now inject a MemPalace operating protocol into generated task launch objectives
  - the same protocol is injected into live mission prompts for enabled global or project integrations
- Promoted MemPalace from a generic tracked integration to a first-class onboarding preset:
  - `use_mempalace` now normalizes the integration payload in `src/openzues/services/onboarding.py`
  - bootstrap now resolves MemPalace as `MemPalace` / `mempalace` / `python -m mempalace.mcp_server` with `auth_scheme="none"`
  - shared notes stay sourced from the MemPalace helper instead of being duplicated
- Added the dashboard affordance in `src/openzues/web/templates/index.html` and `src/openzues/web/static/app.js`:
  - operators now get a `Track MemPalace memory` checkbox
  - checking it prefills the visible integration fields to the MemPalace defaults
  - submit payloads now pass `use_mempalace` and avoid the old GitHub-shaped auth default
- Tightened Ops Mesh readiness guidance in `src/openzues/services/ops_mesh.py`:
  - when MemPalace is tracked but no connected relevant lane publishes it, the recommended action now tells the operator to expose `python -m mempalace.mcp_server` instead of showing only the generic install/enable guidance
- Finished the runtime/operator contract so MemPalace now feels native instead of merely configured:
  - gateway doctor inventory now carries an explicit MemPalace memory posture with `memory_status`, `memory_summary`, and `memory_recommended_action`
  - the dashboard gateway doctor card now renders that memory posture alongside lane health, inventory, approvals, launch policy, and diagnostics
  - CLI doctor output now prints a dedicated `memory:` line, and CLI bootstrap can stage MemPalace via `--use-mempalace`
  - completed or paused missions with MemPalace in scope now surface a handoff item that explicitly prompts memory writeback before the operator stops
- Landed the missing end-to-end automation slice without reopening the route seam:
  - onboarding now auto-creates or updates a second managed task blueprint named `MemPalace Memory Loop` whenever MemPalace is staged through the preset or explicit MemPalace integration fields
  - the loop reuses existing task scheduling, launch routing, mission prompts, and integration inventory instead of inventing a second gateway or memory scheduler
  - the maintenance objective explicitly reviews recent checkpoints and durable repo signal, writes stable truths back through MemPalace when tools exist, and refuses to default to `mempalace compress`
  - cadence is intentionally slower than the primary ship loop so the maintenance pass stays lightweight and additive
- Tightened setup durability around the new loop:
  - bootstrap results now surface the managed memory task as a first-class resource in API/dashboard flows
  - setup wizard session now persists the MemPalace toggle instead of dropping it on reload
  - full setup reset now removes the managed MemPalace loop so bootstrap-owned automation does not get stranded
- Upgraded gateway doctor truthfulness for memory automation:
  - when MemPalace is live and the scheduled loop is armed, API/dashboard/CLI all report that automatic memory maintenance is armed
  - when MemPalace is live but the loop is disabled or missing, doctor posture now degrades to a warning instead of pretending the stack is fully automatic
- Finished the missing live doctor contract without inventing a second gateway subsystem:
  - `RuntimeManager` now keeps a compact cached view of `mcpServerStatus/list`, including tool names, resource names, resource templates, and auth posture
  - gateway doctor now reloads that existing runtime surface for connected lanes and requires the live MemPalace tool contract before it reports memory automation as fully ready
  - the required proof contract is currently `mempalace_status`, `mempalace_search`, and `mempalace_diary_write`
  - API, dashboard, and CLI now expose `memory_evidence` lines that show either the passing lane proof or the exact missing-tool/auth gap
  - top-level doctor severity now stays in warning posture when MemPalace is tracked but the live tool contract is incomplete
- Closed the remaining quality gaps around the operator path:
  - CLI service commands now close connected runtime clients on the same event loop they were created on, which removes the Windows subprocess transport warnings from the gateway/setup CLI test path
  - gateway doctor now also reports maintenance freshness from the existing `MemPalace Memory Loop` task blueprint state
  - when the loop has not run yet, doctor says that plainly; when it last completed, doctor shows the recency; when it failed or drifted far past cadence, doctor degrades memory posture to a warning
- Landed the durable writeback telemetry seam on top of the existing maintenance loop instead of inventing another memory ledger:
  - the MemPalace maintenance objective now requires a structured writeback block at the top of its handoff: `Writeback status`, `Writeback at`, and `Writeback scope`
  - gateway doctor now parses that persisted task result signal to recover the last successful durable writeback timestamp per memory scope
  - API, dashboard, and CLI now report explicit writeback evidence when available, and they say the signal is unreported instead of guessing when a maintenance run completed without one
  - completed writeback proof stays additive; explicit unavailable/deferred writeback reports degrade memory posture only when the signal itself says durable recall freshness is not currently proven
- Landed the missing direct roundtrip proof seam without inventing backend-side MemPalace RPC:
  - the MemPalace maintenance objective now also requires a structured readback proof block: `Roundtrip status`, `Roundtrip at`, `Roundtrip scope`, and `Roundtrip detail`
  - the contract explicitly ties readback proof to the real MemPalace tool surface from `mempalace-main`: `mempalace_search` or `mempalace_diary_read` on the same lane after a durable write
  - gateway doctor now prefers the latest memory-task mission checkpoint over the truncated task summary so it can recover the full structured roundtrip proof block
  - API, dashboard, and CLI now surface the last verified roundtrip proof when it exists, and they degrade memory posture when the latest loop explicitly reports failed or unavailable readback proof
- Landed the operator proof-traceability seam on top of the existing doctor payload instead of inventing a memory details page:
  - gateway doctor inventory now carries a structured `memory_proof_reference` object that points to the latest linked memory-task mission, its proof kind/status, a clipped checkpoint excerpt, and the mission continuity path
  - dashboard doctor now renders that proof reference and can jump straight to the exact proof mission when it is already in the current mission fleet
  - CLI doctor now prints the same proof summary plus the continuity endpoint path so the operator can inspect the exact checkpoint behind the doctor posture
- Closed the remaining backend proof gap without inventing a fake MCP subsystem:
  - a live probe against the Codex app-server confirmed the real limitation: the surface exposes `mcpServerStatus/list` and `mcpServer/resource/read`, but no generic backend-side MCP tool invocation RPC
  - Zeus now fixes that limitation by launching a bounded read-only `MemPalace Direct Proof` mission from the control plane through the existing mission/runtime stack
  - `GatewayCapabilityService.launch_memory_proof()` selects a connected MemPalace-ready lane from existing runtime status, gateway bootstrap state, and the managed `MemPalace Memory Loop` task instead of reopening launch routing
  - API (`POST /api/gateway/memory/prove`), dashboard (`Run direct memory proof`), and CLI (`gateway memory-prove`) all reuse that one launcher
  - direct-proof missions are explicitly additive and production-safe:
    - single-turn
    - no built-in agents
    - no verification pass
    - no auto-commit
    - no failover
    - no MemPalace writes or compaction
  - gateway doctor now prefers the latest direct control-plane proof reference when one exists and exposes launchability metadata so operators can rerun the proof from any surface
- Added the proof drill-in seam on top of the existing mission continuity packet instead of inventing a memory detail model:
  - gateway doctor inventory now includes the selected proof mission's continuity packet inline as `memory_proof_continuity`
  - the packet is built from the existing `build_continuity_packet()` helper, so it stays consistent with the main continuity deck instead of drifting into a second relay format
  - dashboard doctor now shows the proof relay state/score plus a collapsible `Anchor / Drift / Next` drill-in under the proof summary
  - CLI doctor now prints the same relay state, summary, anchor, and next handoff so API/dashboard/CLI all share the same operator proof drill-in

## Verification

Focused direct-proof pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_app.py tests/test_cli.py -q -k "memory_proof or memory_prove or direct_memory_proof or gateway_capability"`
- Result: `13 passed`

Broader changed-surface pack passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py tests/test_app.py tests/test_manager.py tests/test_missions.py tests/test_ops_mesh.py tests/test_database.py -q`
- Result: `169 passed`

Static integrity check passed:

- `.\.venv\Scripts\python.exe -m compileall src/openzues`

Existing live smoke proofs from the prior MemPalace slice still stand:

- MemPalace itself was exercised in an isolated temp environment:
  - `mempalace init`, `mempalace mine`, semantic search, tool search, diary write, and diary read all worked against real local content
- OpenZues itself was smoke-tested in a fresh temp workspace:
  - bootstrap with `use_mempalace` created both the primary ship loop and `MemPalace Memory Loop`
  - the task list exposed both loops
  - gateway capability reported `memory_status=ready` with `Automatic memory loop is armed`
- This turn did not rerun the full manual smoke; it added the missing runtime contract tests around live tool proof and gateway doctor surfacing.

## What is now true in Zeus

- Operators can stage MemPalace through onboarding without manually typing its name, kind, or MCP entrypoint.
- Operators can also stage the same preset from the CLI with `setup bootstrap --use-mempalace` or `gateway bootstrap --use-mempalace`.
- Zeus launch drafts and live mission prompts now carry one shared MemPalace working contract instead of relying on ad hoc operator instructions.
- Ops Mesh now distinguishes the specific failure mode where project memory is tracked but no relevant connected lane exposes MemPalace.
- Gateway doctor now exposes MemPalace memory posture directly across API, dashboard, and CLI instead of burying it inside generic inventory counts.
- Completed MemPalace-backed missions now nudge the operator to write durable context back before ending the handoff.
- Zeus now has a built-in automatic MemPalace maintenance loop:
  - bootstrap stages a second recurring task blueprint dedicated to memory upkeep
  - the loop is visible in dashboard task inventory and bootstrap results
  - doctor posture now distinguishes between "memory is live" and "memory is live and automatically maintained"
- Gateway doctor now also proves the live tool contract instead of trusting only a published server label:
  - the ready path now requires a connected lane to expose `mempalace_status`, `mempalace_search`, and `mempalace_diary_write`
  - when those tools are missing, API/dashboard/CLI show the exact missing tool in `memory_evidence` and keep the memory posture in warning state
  - when the contract is present, API/dashboard/CLI show the passing lane proof in `memory_evidence`
- Gateway doctor now also surfaces maintenance freshness from the existing scheduled loop:
  - `memory_evidence` now reports whether `MemPalace Memory Loop` has not run yet, last completed recently, is currently running, or last failed
  - failed or badly overdue maintenance runs now keep memory posture in warning state even when the live tool contract is otherwise healthy
- Gateway doctor now also surfaces durable writeback proof from the loop itself:
  - when the loop reports `Writeback status: wrote` or `corrected` with an absolute UTC timestamp, doctor surfaces the latest proven writeback time for that memory scope
  - when the loop completes but does not emit a structured writeback block yet, doctor says the writeback signal is unreported rather than fabricating freshness
  - when the loop explicitly reports `deferred`, `unavailable`, or `none`, doctor surfaces that scope-level writeback posture and can keep memory in warning state even if the lane still exposes the right tools
- Gateway doctor now also surfaces direct readback proof from the loop itself:
  - when the loop reports `Roundtrip status: verified` with an absolute UTC timestamp and a detail line, doctor surfaces the last proven MemPalace readback time and the proof detail in `memory_evidence`
  - when the loop explicitly reports `failed` or `unavailable`, doctor keeps memory posture in warning state even if the writeback and live tool-contract proofs are otherwise healthy
  - doctor now reads the latest linked mission checkpoint first, so the full proof block survives even when task summary fields are truncated for dashboard brevity
- Gateway doctor now also carries an explicit proof reference back to the exact maintenance mission:
  - API now exposes `memory_proof_reference` with the mission id, proof kind/status, clipped checkpoint excerpt, and continuity path
  - dashboard uses that shared payload to render an `Open proof mission` jump when the mission is present in the loaded fleet
  - CLI prints the same proof summary and continuity path so the operator can inspect the exact handoff behind the doctor summary
- Zeus can now launch and prove live control-plane MemPalace access itself without waiting for the scheduled loop:
  - API exposes `POST /api/gateway/memory/prove`
  - CLI exposes `gateway memory-prove`
  - dashboard doctor renders `Run direct memory proof` whenever a connected MemPalace-ready lane is available
  - the launched mission is a bounded read-only proof run that uses the existing mission/runtime stack instead of a second gateway subsystem
- Gateway doctor now prefers the direct control-plane proof when it exists:
  - `memory_proof_reference` can now resolve to `proof_kind="control_plane"`
  - `memory_summary` includes the latest backend-triggered proof freshness/detail
  - the inventory payload now also carries `memory_proof_launchable`, `memory_proof_target_instance_id`, and `memory_proof_launch_label` so every surface can expose the same operator action
- Gateway doctor now also carries the selected proof mission's relay packet inline:
  - API exposes `memory_proof_continuity` with the same continuity packet shape already used by `/api/missions/{id}/continuity`
  - dashboard shows the relay state/score and a compact `Anchor / Drift / Next` drill-in without sending operators to a separate memory page
  - CLI prints that same relay context so the proof trail stays aligned across all operator surfaces
- The automatic loop is intentionally conservative:
  - it uses existing task routing and mission prompts
  - it prefers raw recall and writeback
  - it does not silently switch Zeus over to lossy AAAK compaction because MemPalace's own README still positions AAAK/compress as experimental and weaker than raw mode
- The slice stays additive and reuses existing Zeus surfaces:
  - onboarding bootstrap
  - integration inventory
  - gateway doctor
  - launch draft construction
  - live mission prompt construction
  - existing gateway/operator guidance

## What remains

- The Codex app-server still does not expose a generic backend-side MCP invoke RPC; Zeus now works around that cleanly by launching a bounded proof mission on a live lane, but raw direct RPC is still unavailable upstream.
- Gateway doctor now surfaces self-reported writeback, roundtrip, and direct control-plane proof from linked mission checkpoints, but there is still no standalone historical ledger of multiple proof events over time inside OpenZues.
- Per-project freshness is visible when each project has its own maintenance loop, and doctor now preloads the selected proof mission's continuity packet inline, but it still does not cache or diff multiple historical proof packets over time.
- The MemPalace slice is green. The previous Windows asyncio transport warnings on the tested CLI path were resolved by explicit runtime cleanup; any remaining warning work would be outside this MemPalace seam.

## Next best seam

The next best MemPalace slice is optional proof drill-in, not more core integration plumbing:

- if we keep pushing this seam, preload the latest proof mission's continuity packet from the existing `/api/missions/{id}/continuity` route so the doctor can show a tighter handoff excerpt without another click
- that preload is now done, so the next optional step would be proof history over time or richer project-filtered recall, not more gateway doctor plumbing
- keep that proof trail lane-side, because the current app-server surface still exposes catalogs and mission state but not a generic backend-side MCP invoke RPC
- avoid inventing a separate memory dashboard; keep using gateway capability, task inventory, mission cards, and mission continuity as the operator surfaces

## Re-entry handoff

- Recovered context: the prior slice had already verified bootstrap, prompt wiring, Ops Mesh guidance, the automatic `MemPalace Memory Loop`, live tool proof, maintenance freshness, durable writeback proof, direct roundtrip proof, and proof traceability, but it still lacked a backend-triggered control-plane proof action.
- Verified state: the direct-proof pack passed (`13 passed`), the broader changed-surface pack passed (`169 passed`), and `compileall` passed. The earlier live MemPalace smoke remains the last manual proof and still matches the implemented contract.
- Next step: if we keep going on MemPalace, the best remaining work is optional proof history over time or richer project-filtered recall, not more core integration plumbing.
- Blockers: the upstream app-server still does not expose a generic backend-side MCP tool invocation RPC. Zeus now routes around that by launching a bounded proof mission on a live lane, so there is no product blocker left inside the MemPalace seam.
