# Hermes Reference Status

Agent report source: Ohm

Last updated: 2026-05-02

Repo: `C:\Users\skull\OneDrive\Documents\hermes-agent-main`

Hermes is a full agent product and a reference/bridge repo. It is not the
OpenClaw parity source of truth.

## Rough Reference Rollup

| Area | Rough Status | Count Toward OpenClaw Parity |
| --- | ---: | --- |
| Advertised Hermes repo surface | 80-85% | No, reference-only |
| OpenClaw-to-Hermes migration path | 75-85% | Only for explicit migration/bridge rows |
| Hermes ACP/editor support | 70-80% | Only for explicit ACP bridge rows |
| Hermes web/dashboard/plugin SDK | 75-85% | No, reference-only |

These are inspection estimates, not measured test results.

## Implemented Capability Inventory

| Status | Surface | Evidence |
| --- | --- | --- |
| [ ] | Core agent and CLI | `pyproject.toml`, `hermes_cli/main.py`, `hermes`, `hermes-agent`, `hermes-acp` |
| [ ] | Model/runtime breadth | provider adapters for OpenAI, Anthropic, OpenRouter/Nous/custom/local, Gemini-like and fallback routing |
| [ ] | Tools/toolsets | `tools`, `toolsets.py`, terminal, file, web, browser, vision, TTS/STT, image generation, MCP, memory, todo, delegation, cron, kanban, skills |
| [ ] | Gateway/channels | `gateway/platforms`, Telegram, Discord, Slack, WhatsApp, Signal, Email, Matrix, Mattermost, SMS, Home Assistant, DingTalk, Feishu, WeCom, Weixin, Yuanbao, webhooks, BlueBubbles/iMessage |
| [ ] | Memory and skills | local memory, Honcho, memory-provider plugins, skill sync/hub, FTS session search, skill docs/catalog |
| [ ] | Cron and automation | cron scheduler, CLI, dashboard APIs, tests under `tests/cron` |
| [ ] | ACP/editor | `docs/acp-setup.md`, `acp_adapter/server.py`, VS Code/Zed/JetBrains setup |
| [ ] | Web/dashboard | `web/src/App.tsx`, `hermes_cli/web_server.py`, sessions, analytics, models, logs, cron, skills, plugins, profiles, config, keys, docs |
| [ ] | Plugins | `plugins`, runtime hooks, dashboard manifests/API, memory/image/platform/observability/Spotify/kanban/achievement plugins |
| [ ] | OpenClaw migration | `docs/migration/openclaw.md`, `hermes_cli/claw.py`, setup wizard migration offer |
| [ ] | Docs/tests | broad documentation and large Python test inventory |

## Strong Overlap With OpenZues/OpenClaw Work

- OpenClaw migration: SOUL, memories, user profile, skills, command allowlists,
  messaging settings, compatible API keys, TTS assets, AGENTS/workspace files.
- Gateway/channel runtime: useful comparison for provider/channel behavior.
- Session/chat/history: useful comparison for session storage/search/dashboard
  and ACP session handling.
- Tool catalog, invocation, and approval policy.
- ACP/editor runtime.
- Cron/automation.
- Plugin/dashboard ecosystem.

## Remaining / Follow-Up Checklist

- [ ] Decide which Hermes rows are bridge targets instead of reference notes.
- [ ] Verify `hermes claw migrate` behavior if OpenZues adds migration tooling.
- [ ] Compare Hermes ACP server lifecycle with OpenClaw ACP expectations before
  borrowing any behavior.
- [ ] Keep Hermes percentages separate from OpenClaw parity.
