# OpenZues

OpenZues is a local-first Codex control plane built for operators who want more than a chat window.
It speaks the official Codex App Server JSON-RPC protocol, keeps a live event timeline, surfaces approvals,
tracks local projects, and folds GitHub context into the same dashboard.

## Why it exists

OpenZues is optimized to beat "assistant wrapper" products on operator UX:

- durable mission control for long-running autonomous Codex objectives
- checkpoint memory that captures each final-answer handoff from autonomous runs
- approval-aware continuation so long builds pause cleanly and resume without losing context
- live thread and turn telemetry
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
- `pytest`
- `ruff check .`
- `mypy src`

## Architecture

- `src/openzues/services/codex_rpc.py`: protocol client and transport handling
- `src/openzues/services/manager.py`: runtime state, persistence wiring, broadcast hub
- `src/openzues/services/missions.py`: autonomous mission runner, checkpoint capture, and continuation logic
- `src/openzues/services/github.py`: local git and GitHub CLI integration
- `src/openzues/app.py`: FastAPI app and API surface
- `src/openzues/web/`: operator UI
