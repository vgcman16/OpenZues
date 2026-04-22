# OpenZues

OpenZues is a local-first Codex control plane built for operators who want more than a chat window.
It speaks the official Codex App Server JSON-RPC protocol, keeps a live event timeline, surfaces approvals,
tracks local projects, and folds GitHub context into the same dashboard.

## Project status

OpenZues is an open-source alpha.

It is already useful for serious local operator workflows, especially on Windows with Codex Desktop, but it
is still evolving quickly. The core control-plane experience is real today; the broader ecosystem surface is
not complete yet.

What that means in practice:

- the strongest path today is local-first mission control, approvals, checkpoints, playbooks, routing, operator oversight, and a growing slice of OpenClaw-style gateway/setup/session/cron behavior
- Windows and Codex Desktop bridging are first-class; other environments are improving but less battle-tested
- APIs, automation posture, and dashboard surfaces may still change quickly between releases
- this is not yet full OpenClaw or Hermes end-to-end parity across channels, nodes, voice, browser runtime, or companion apps

## OpenClaw parity progress

Best-effort estimate: OpenZues is at roughly **30%** of overall OpenClaw parity today, with a reasonable band of about **25-35%**.
That estimate is intentionally conservative and reflects the whole OpenClaw product surface, not just the local control-plane path.

Most of the parity progress so far is in gateway/control-plane-adjacent work: setup and bootstrap flows, launch routing and session-key handling, operator supervision, checkpoint continuity, gateway method coverage, bounded session surfaces, and mission-backed cron/usage compatibility.
The current active gateway/cron/session-delivery family is materially further along, at roughly **70%** of its bounded local parity path.
The biggest gaps are still the broader OpenClaw runtime surfaces: multi-channel delivery, wider CLI/runtime parity, browser and canvas control, nodes, voice, packaging, and companion apps.

For the detailed parity rollup, see [docs/openclaw-parity-progress.md](docs/openclaw-parity-progress.md) and the living checkpoint ledger at [docs/openclaw-parity-checkpoint-2026-04-10.md](docs/openclaw-parity-checkpoint-2026-04-10.md).

## Why it exists

OpenZues is optimized to beat "assistant wrapper" products on operator UX:

- durable mission control for long-running autonomous Codex objectives
- checkpoint memory that captures each final-answer handoff from autonomous runs
- approval-aware continuation so long builds pause cleanly and resume without losing context
- live thread and turn telemetry
- operator inboxes, lane snapshots, and capability maps for supervising multiple autonomous lanes
- approval inbox for command and file-change prompts
- reusable playbooks with variable interpolation for recurring operator flows
- environment diagnostics for Codex, GitHub CLI, Python, and workspace health
- one-click Codex Desktop bridge that stages a runnable local App Server binary on Windows
- project-aware Codex launches with cwd targeting
- local Git and GitHub visibility beside each workspace
- transport flexibility for desktop bridge, `codex app-server` over stdio, or a WebSocket endpoint

## Current capabilities

- register one or more Codex App Server connections
- quick-connect to the local Codex Desktop install from the dashboard
- launch App Server subprocesses or connect to a WebSocket endpoint
- initialize the Codex transport and stream notifications in real time
- create threads, start turns, interrupt turns, run standalone commands, and start reviews
- collect unresolved server requests and resolve them from the UI
- save and run command, turn, thread+turn, and review playbooks
- launch autonomous missions that keep a Codex thread moving until blocked, paused, or complete
- capture mission checkpoints from final answers so users have a durable memory stream
- synthesize an operator inbox from approvals, fragile missions, reflexes, due runs, and ready handoffs
- map repo skill coverage and integration readiness across connected lanes
- capture checkpoint-aware lane snapshots with continuity and safest-handoff context
- inspect live diagnostics before debugging connection failures by hand
- browse models, apps, plugins, skills, MCP status, config, and thread history
- register local projects and inspect git status, branches, commits, and PRs through `gh`
- persist connection configs, projects, events, and pending requests in SQLite
- persist mission state, checkpoints, and autonomous progress in SQLite so runs can survive restarts

## Quick start

1. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the project:

   ```powershell
   pip install -e .[dev]
   ```

3. Run the app:

   ```powershell
   openzues --reload
   ```

4. Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

## Default connection strategy

OpenZues now defaults to `Desktop (Recommended)`:

```text
Codex Desktop bridge -> staged local codex.exe -> app-server
```

This is specifically designed for Windows Store Codex installs where direct subprocess execution can fail
with `Access is denied`. OpenZues detects the installed desktop package, stages a runnable local copy of
`codex.exe` under `%LOCALAPPDATA%\OpenZues\runtime`, verifies it with `--version`, and then launches
`app-server` from that staged path.

If you prefer, you can still use raw stdio:

```text
codex app-server
```

Or connect to a WebSocket endpoint when you have one available.

## Developer commands

- `openzues --reload`
- `openzues watch --port 8884 --follow --launch`
- `pytest`
- `ruff check .`
- `mypy src`

## Live Watch

When you want to watch the real control plane instead of a second shadow process, point the watcher at
the running OpenZues server:

```powershell
openzues watch --port 8884 --follow --launch
```

That view reads the live `/api/dashboard` and `/api/setup/launch` surfaces, locks onto the saved setup
handoff task by default, and can auto-resume or launch the saved mission before it starts polling.

For a repo-local Windows launcher, use:

```powershell
scripts\openzues-watch.cmd --port 8884 --follow --launch --until-terminal
```

To pair the live API watch with browser verification on the same dashboard:

```powershell
scripts\openzues-watch-browser.cmd --port 8884 --follow --launch
```

That browser-backed path uses `agent-browser` to open the live UI, confirm the page has content,
check for a framework error overlay, collect page and console errors, and capture an annotated
screenshot artifact beside the mission watch output.

For a longer-running operator monitor with a rolling log plus a stable screenshot that refreshes
every few cycles, use:

```powershell
scripts\openzues-operator-monitor.cmd
```

By default that launcher watches port `8884`, writes a rolling log to
`%LOCALAPPDATA%\OpenZues\watch\operator-monitor.log`, and keeps the latest browser screenshot at
`%LOCALAPPDATA%\OpenZues\watch\operator-monitor.png`. The wrapper uses the live API watcher for the
mission heartbeat, then refreshes the browser screenshot out of process with a fresh `agent-browser`
session so Windows shell quirks do not jam the main monitor loop.

## What Is Still Missing

These are the biggest gaps before OpenZues can claim broader control-plane parity:

- multi-channel inbox and channel runtime surfaces
- richer browser, canvas, and node runtime layers
- voice wake and talk-mode experiences
- companion app family and packaging breadth
- more polished onboarding and operator docs for new contributors

If you open an issue or PR around one of those seams, that is helpful and on-strategy.

## Open Source Conventions

- License: [MIT](LICENSE)
- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Security policy: [SECURITY.md](SECURITY.md)
- Community expectations: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Architecture

- `src/openzues/services/codex_rpc.py`: protocol client and transport handling
- `src/openzues/services/manager.py`: runtime state, persistence wiring, broadcast hub
- `src/openzues/services/missions.py`: autonomous mission runner, checkpoint capture, and continuation logic
- `src/openzues/services/ops_mesh.py`: operator inbox, lane snapshots, skill coverage, and integration readiness
- `src/openzues/services/skillbook.py`: claw-style builtin mission skillbooks and project skill pin resolution
- `src/openzues/services/github.py`: local git and GitHub CLI integration
- `src/openzues/app.py`: FastAPI app and API surface
- `src/openzues/web/`: operator UI
