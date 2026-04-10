# OpenZues

OpenZues is a local-first Codex control plane built for operators who want more than a chat window.
It speaks the official Codex App Server JSON-RPC protocol, keeps a live event timeline, surfaces approvals,
tracks local projects, and folds GitHub context into the same dashboard.

## Why it exists

OpenZues is optimized to beat "assistant wrapper" products on operator UX:

- live thread and turn telemetry
- approval inbox for command and file-change prompts
- reusable playbooks with variable interpolation for recurring operator flows
- environment diagnostics for Codex, GitHub CLI, Python, and workspace health
- project-aware Codex launches with cwd targeting
- local Git and GitHub visibility beside each workspace
- transport flexibility for `codex app-server` over stdio or a WebSocket endpoint

## Current capabilities

- register one or more Codex App Server connections
- launch App Server subprocesses or connect to a WebSocket endpoint
- initialize the Codex transport and stream notifications in real time
- create threads, start turns, interrupt turns, run standalone commands, and start reviews
- collect unresolved server requests and resolve them from the UI
- save and run command, turn, thread+turn, and review playbooks
- inspect live diagnostics before debugging connection failures by hand
- browse models, apps, plugins, skills, MCP status, config, and thread history
- register local projects and inspect git status, branches, commits, and PRs through `gh`
- persist connection configs, projects, events, and pending requests in SQLite

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
   openzues serve --reload
   ```

4. Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

## Default connection strategy

OpenZues defaults to the official stdio launch path:

```text
codex app-server
```

On some Windows Store Codex installs, direct subprocess execution can fail with `Access is denied`.
If that happens, keep the connection config but switch the transport to WebSocket until the local launcher
behavior is resolved in your environment.

## Developer commands

- `openzues serve --reload`
- `pytest`
- `ruff check .`
- `mypy src`

## Architecture

- `src/openzues/services/codex_rpc.py`: protocol client and transport handling
- `src/openzues/services/manager.py`: runtime state, persistence wiring, broadcast hub
- `src/openzues/services/github.py`: local git and GitHub CLI integration
- `src/openzues/app.py`: FastAPI app and API surface
- `src/openzues/web/`: operator UI
