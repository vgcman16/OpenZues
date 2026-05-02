# Warp Reference Status

Agent report source: Lovelace

Last updated: 2026-05-02

Repo: `C:\Users\skull\OneDrive\Documents\warp-master`

Warp is a Rust client/ADE with a custom WarpUI terminal client. Its open source
surface is the client app, WarpUI, integration tests, agent skills, and specs.
The server, Drive backend, hosted auth, and Oz orchestration are outside this
repo.

## Status Categories

- Confirmed local: implemented in Warp client and locally testable.
- Feature-flagged: code or flag present; needs enabled-build/runtime proof.
- Backend-gated: client hook exists, but Warp server/Oz/Drive backend is needed.
- Bridge candidate: useful via MCP, ACP, CLI agent, workflow, or skill adapter.
- External owner: belongs primarily to OpenClaw, OpenZues, or Hermes.
- Spec-only/in-flight: documented in `specs`, not proven implemented.
- No parity target: intentionally out of Warp scope.
- Needs verification: plausible from source, but needs focused proof.

## Implemented / Represented Warp Surface

| Status | Surface | Evidence |
| --- | --- | --- |
| [ ] | Terminal/ADE core | `WARP.md`, terminal emulator, WarpUI, TTY, SSH/WSL, completions, history, prompt, shared sessions, settings, SQLite, GraphQL client |
| [ ] | Agent mode/tooling | `crates/ai/src/agent/action/mod.rs`, command execution, shell output, file reads/edits, grep/glob, codebase search, MCP tools/resources, computer use, child agents |
| [ ] | BYO CLI agents | `app/src/terminal/cli_agent.rs`, Claude Code, Codex, Gemini, OpenCode, Copilot, Cursor, Goose, skill-provider mapping |
| [ ] | MCP/skills bridge | `app/src/ai/mcp/mod.rs`, Warp/Claude/Codex/generic `.agents` config paths, CLI and SSE transports |
| [ ] | Code/editor/review | file tree, editor, code review pane, diff state, git dialogs, PR/commit/push surfaces |
| [ ] | Cloud/Oz hooks | `crates/warp_features/src/lib.rs`, `crates/warp_cli/src/lib.rs`, ambient agents, cloud mode, scheduled agents, managed secrets, orchestration hooks |
| [ ] | Remote execution/files | `app/src/remote_server/mod.rs`, remote daemon/proxy, repo metadata, file model, SSH transport install/connect/reinstall lifecycle |
| [ ] | Test/spec posture | `WARP.md`, `CONTRIBUTING.md`, nextest-based unit/integration testing and specs |

## Bridge Candidates

- [ ] Expose OpenZues as an MCP, ACP, or CLI-agent backend inside Warp.
  - Status: bridge candidate
  - References: OpenZues local operator control, Codex bridge, approvals,
    missions, playbooks, checkpoints, ACP/session/gateway methods.

- [ ] Expose OpenClaw Gateway as an MCP/SSE or CLI harness surfaced from Warp.
  - Status: bridge candidate
  - References: OpenClaw sessions, tools, cron, skills, browser/canvas/nodes,
    multi-agent routing, channels, and companion apps.

- [ ] Surface Hermes as an ACP/CLI-agent candidate for Warp.
  - Status: bridge candidate
  - References: Hermes CLI/TUI runtime, skills, memory, MCP, cron, subagents,
    messaging gateway, `hermes-acp`.

## External / Backend-Gated Boundaries

- [ ] Warp server/Oz/Drive backend behavior is not fully testable from this repo.
- [ ] OpenClaw multi-channel inbox, voice wake/talk, live canvas, and
  node/companion-app breadth remain OpenClaw/OpenZues parity work, not Warp
  client parity.
- [ ] Do not count Warp client similarities toward OpenClaw parity without a
  mapped OpenClaw source and OpenZues verification proof.
