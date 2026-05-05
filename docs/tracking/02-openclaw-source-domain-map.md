# OpenClaw Source Domain Map

Agent report source: Banach

Last updated: 2026-05-05

OpenClaw is the upstream source of truth for repo-wide parity. Each domain below
should become one or more bounded OpenZues parity seams before it can affect the
repo-wide percentage.

## Domain Checklist

| Status | Domain | Track | Source Evidence |
| --- | --- | --- | --- |
| [ ] | Product entrypoints and package surface | npm binary, source/dev launcher, exports, version/build metadata | `openclaw.mjs`, `src/entry.ts`, `package.json` |
| [ ] | CLI, TUI, setup, onboarding | commands, setup/onboard/wizard, TUI, doctor/status/update | `src/cli`, `src/commands`, `src/tui`, `src/wizard` |
| [ ] | Gateway control plane and APIs | gateway server, protocol, WebSocket/HTTP, Control UI serving, OpenAI/OpenResponses compatibility | `src/gateway`, `docs/gateway/protocol.md`, `docs.acp.md` |
| [ ] | Agent runtime, sessions, harnesses | embedded agents, CLI backends, ACP/Codex/Pi harnesses, subagents, session stores, compaction | `src/agents`, `src/sessions`, `src/acp`, `docs/pi.md` |
| [~] | Channels, routing, delivery | Telegram audio/voice, Google Chat native text/thread/media/DM, Nextcloud Talk signed bot, Synology Chat incoming-webhook, Mattermost channel-id, Feishu/Lark route-backed text and direct media sends plus read/post media resource hydration, presentation-card send/thread-reply, image/file/audio/video media sends with local-root guards, audioAsVoice transcode, mediaMaxMb caps, and channel capability metadata, and read/edit/pin/unpin/list-pins/channel-info/member-info/channel-list/react/reactions actions, Microsoft Teams Bot Framework proactive text/threaded replies, Adaptive Card polls, `/api/messages` bearer-gated webhook dispatch, configured Teams webhook path plus `/api/messages` fallback, Bot Framework JWT validation, attachment-only inbound placeholders, inbound attachment URL metadata, media staging, inbound media Graph/Bot Framework auth fallback, personal welcome-card member lifecycle, group welcome member lifecycle, adaptive-card inbound session routing, inbound mention stripping/HTML fallback, feedback invoke recording, feedback-disabled invoke consuming, feedback reflection learning/follow-up, SSO no-config invoke acknowledgement, configured SSO token exchange/store, configured SSO verify-state magic-code flow, SSO DM allowlist sign-in drop handling, SSO route allowlist sign-in drop handling, SSO group sender allowlist sign-in drop handling, Graph reaction listing/write/read/pin/unpin/list-pins/search/member-info/channel-list/channel-info actions, Bot Framework edit/delete/upload-file and adaptive-card send actions, stored delegated-token reaction writes, expired delegated-token fallback, delegated refresh-token flow, delegated OAuth setup URL/bootstrap/completion, delegated-auth probe posture, native readiness probe, user-reference routing, FileConsent, and Graph upload verified; Signal JSON-RPC send plus reaction actions, IRC PRIVMSG, and Twitch chat route-backed sends plus send action verified; channel registry, broader session routing, full inbound/outbound delivery, typing/status/reactions, pairing, access groups remain | `src/channels`, `src/routing`, `docs/channels`, `extensions/telegram/openclaw.plugin.json`, `extensions/googlechat/src`, `extensions/nextcloud-talk/src`, `extensions/mattermost/src`, `extensions/signal/src`, `extensions/irc/src`, `extensions/twitch/src` |
| [ ] | Provider and model capability matrix | model catalogs, auth profiles, provider discovery, text/media/search/voice providers | `src/model-catalog`, `extensions/openai`, `extensions/anthropic`, `docs/providers` |
| [~] | Plugin and extension system | SDK, manifests, bundled/installed plugins, lifecycle, hooks, ClawHub/npm packaging; document and web-content extractor contracts plus CommonJS/ESM runtime import/execution, request-time tool factory context, text-runtime string helpers, error-runtime helpers, temp-path helpers, secret-input helpers, routing/session helper shims, reply-chunking helpers, reply-payload helpers, account-helper shims, account-core/account-resolution shims, tool-payload shims, boolean-param shims, channel-actions shims, status-helper shims, and channel-status shims verified; broader SDK helper/runtime contracts remain | `src/plugins`, `src/plugin-sdk`, `extensions`, `packages/plugin-sdk` |
| [ ] | Tools, skills, MCP, ACPX | browser/exec/diffs/file tools, skills, MCP integration, ACPX runtime, plugin commands | `src/tools`, `src/mcp`, `extensions/browser`, `extensions/acpx` |
| [ ] | Memory and knowledge | memory plugins, embeddings, dreaming, QMD/wiki/LanceDB, memory host SDK | `extensions/memory-core`, `extensions/memory-wiki`, `packages/memory-host-sdk`, `docs/concepts/memory.md` |
| [~] | Media, voice, web, canvas | canvas shortcode normalization verified; image/video/music generation, media understanding, TTS/STT/realtime voice, web search/fetch, Canvas/A2UI breadth remain | `src/media`, `src/image-generation`, `src/realtime-voice`, `src/canvas-host`, `extensions/comfy` |
| [ ] | Automation, cron, tasks, commitments | scheduled runs, task commands, commitment safety, heartbeat/maintenance | `src/cron`, `src/tasks`, `src/commitments`, `docs/cli/cron.md` |
| [ ] | Config, secrets, security, sandbox | schemas, config migration, SecretRef, auth, approvals, sandbox policy, SSRF/network safety | `src/config`, `src/secrets`, `src/security`, `src/agents/sandbox`, `docs/gateway/sandboxing.md` |
| [ ] | Control UI and web surfaces | Vite/Lit Control UI, chat, settings, agents, sessions, logs, i18n, WebChat/TUI docs | `ui/src/ui/views`, `ui/src/ui/controllers`, `ui/src/i18n`, `docs/web` |
| [~] | Companion apps and nodes | node.presence.alive verified; macOS app, iOS/Android nodes, shared OpenClawKit, pairing, node capabilities remain | `src/gateway/server-node-events.ts`, `apps/ios`, `apps/android`, `apps/shared` |
| [ ] | QA, tests, scenarios | unit/e2e/live/docker tests, QA Lab, scenario catalog, provider/channel regressions | `test/vitest`, `scripts/e2e`, `qa/scenarios`, `extensions/qa-lab` |
| [~] | Packaging, distribution, release | packageDistribution doctor JSON, dist inventory validation, update-status channel projection, and git branch channel labeling verified; npm package, plugin packages, Docker/Podman, macOS DMG/Sparkle, CI release workflows, update channels remain | `src/flows/doctor-health.ts`, `src/commands/doctor-install.ts`, `src/infra/update-global.ts`, `scripts/openclaw-npm-publish.sh`, `scripts/package-mac-dist.sh`, `Dockerfile`, `.github/workflows` |
| [ ] | Observability, diagnostics, ops | logging, OpenTelemetry/Prometheus, health/status, proxy capture, runtime reports | `src/logging`, `extensions/diagnostics-otel`, `extensions/diagnostics-prometheus`, `docs/logging.md` |

## How To Use This Map

- Split each broad domain into source-backed seams before implementation.
- Link every OpenZues parity row back to at least one OpenClaw source path.
- Do not give parity credit for Hermes/Warp similarities unless the OpenClaw
  behavior is also mapped and verified.
- Move broad domain rows only when the child seam weights are verified.
