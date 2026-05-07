# OpenClaw Source Domain Map

Agent report source: Banach

Last updated: 2026-05-07

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
| [~] | Plugin and extension system | SDK, manifests, bundled/installed plugins, lifecycle, hooks, ClawHub/npm packaging; document and web-content extractor contracts plus CommonJS/ESM runtime import/execution, request-time tool factory context, text-runtime string helpers, string-coerce-runtime helpers, text-autolink-runtime helpers, dedupe-runtime helpers, retry-runtime helpers, keyed-async-queue helpers, lazy-value helpers, lazy-runtime helpers, config-paths helpers, context-visibility-runtime helpers, heartbeat-runtime helpers, json-store helpers, diagnostic-runtime helpers, system-event-runtime helpers, oauth-utils helpers, runtime-config-snapshot helpers, runtime-fetch helpers, runtime-doctor helpers, runtime-secret-resolution helpers, memory-core-host-query helpers, memory-core-host-multimodal helpers, memory-core-host-secret helpers, memory-core-host-events helpers, memory-core-host-status helpers, memory-core-engine-runtime facade helpers, memory-core-host-engine-embeddings helpers, memory-core-host-engine-foundation helpers, provider-setup helpers, self-hosted-provider-setup helpers, LM Studio runtime helpers, media-store helpers, browser-security-runtime helpers, command-primitives-runtime helpers, media-mime helpers, command-detection helpers, global-singleton helpers, concurrency-runtime helpers, channel-inbound-debounce helpers, channel-inbound helpers, channel-route helpers, channel-policy helpers, group-access helpers, group-activation helpers, provider-selection-runtime helpers, windows-spawn helpers, command-status helpers, command-auth native helpers, process-runtime command helpers, run-command normalized helpers, poll-runtime helpers, CLI runtime helpers, approval-auth-runtime helpers, approval-auth-helpers, approval-approvers helpers, approval-reply-runtime helpers, approval-renderers helpers, approval-client-helpers, approval-client-runtime alias helpers, approval-delivery-helpers, approval-native-helpers, approval-native-runtime delivery helpers/factory/expiration, approval-handler-adapter-runtime helpers, approval-handler-runtime adapter factory/wrapper/capability bridge, approval-runtime aggregate helpers, approval-gateway-runtime resolver helpers, Telegram command config helpers, param-readers helpers, provider-zai-endpoint helpers, provider-env-vars helpers, session-visibility helpers, simple-completion-runtime extractAssistantText helper, webhook helper shims, fetch/SSRF helper shims, provider model/catalog helper shims, models-provider-runtime helper shim, skill-commands-runtime helper shim, skills-runtime helper shim, provider entry/enable/auth-result helper shims, provider-auth-runtime helper shims, provider-auth API-key helper shims, provider-auth-login helper/runtime alias shims, provider-auth facade helper shims, provider web-search contract helper shims, provider web facade helper shims, device-bootstrap helper shims, runtime-store helper shims, runtime helper shims, directory-runtime helper shims, directory-config-runtime helper shims, thread-bindings-runtime helper shims, conversation-runtime helper shims, outbound-runtime helper shims, conversation-binding-runtime helper shims, session-binding/session-key runtime alias shims, session-store runtime helper shims, model-session-runtime helper shims, account-id/configured-id subpath shims, agent-media-payload helper shims, agent-config-primitives helper shims, ACP binding resolve helper shims, Anthropic CLI facade helper shims, Anthropic Vertex auth-presence helper shims, Anthropic Vertex facade helper shims, XAI model-id helper shims, channel pairing path helper shims, channel inbound root helper shims, channel location helper shims, state path helper shims, setup adapter runtime helper shims, channel secret TTS runtime helper shims, channel secret basic/runtime helper shims, secret-file-runtime helper shim, secret-ref-runtime helper shim, secret-input-runtime helper shim, secret-input-schema helper shim, cron-store-runtime helper shim, file-access-runtime helper shim, logging-core helper shim, native-command-config-runtime helper shim, host-runtime helper shim, image-generation-core auth-runtime helper shim, talk config runtime helper shims, GitHub Copilot token helper shims, channel plugin common/core helper shims, channel entry contract helper shims, channel config primitives/schema helper shims, runtime-env helper shims, channel-config-helpers helper shims, channel-config-writes alias shim, channel-lifecycle helper shim, exact channel-core helper shim, channel-contract-testing helper shim, channel-targets helper shim, channel-streaming helper shim, channel-envelope helper shim, channel-mention-gating helper shim, channel-runtime-context helper shim, channel-activity-runtime helper shim, inbound-envelope helper shim, allow-from helpers, allowlist-config-edit helpers, access-groups helpers, direct-DM access helpers, direct-DM guard-policy helpers, direct-DM helpers, channel-send-result helpers, channel-pairing helpers, command-auth helpers, channel-setup helpers, channel-reply-options-runtime helpers, channel-reply-pipeline helpers, channel-feedback helpers, markdown-table-runtime helpers, reply-history helpers, reply-reference helpers, reply-dedupe helpers, string-normalization helpers, dangerous-name helpers, channel-logging helpers, time-runtime helpers, number-runtime helpers, secure-random-runtime helpers, collection-runtime helpers, async-lock-runtime helpers, transport-ready-runtime helpers, target-resolver-runtime helpers, response-limit-runtime helpers, error-runtime helpers, temp-path helpers, secret-input helpers, routing/session helper shims, reply-chunking helpers, text-chunking helpers, reply-payload helpers, account-helper shims, account-core/account-resolution shims, tool-payload shims, boolean-param shims, channel-actions shims, status-helper shims, and channel-status shims verified; broader SDK helper/runtime contracts remain | `src/plugins`, `src/plugin-sdk`, `extensions`, `packages/plugin-sdk` |
| [ ] | Tools, skills, MCP, ACPX | browser/exec/diffs/file tools, skills, MCP integration, ACPX runtime, plugin commands | `src/tools`, `src/mcp`, `extensions/browser`, `extensions/acpx` |
| [ ] | Memory and knowledge | memory plugins, embeddings, dreaming, QMD/wiki/LanceDB, memory host SDK | `extensions/memory-core`, `extensions/memory-wiki`, `packages/memory-host-sdk`, `docs/concepts/memory.md` |
| [~] | Media, voice, web, canvas | canvas shortcode normalization verified; image/video/realtime voice/media understanding helper shims landed; music generation, web search/fetch, Canvas/A2UI breadth remain | `src/media`, `src/image-generation`, `src/realtime-voice`, `src/canvas-host`, `extensions/comfy` |
| [ ] | Automation, cron, tasks, commitments | scheduled runs, task commands, commitment safety, heartbeat/maintenance | `src/cron`, `src/tasks`, `src/commitments`, `docs/cli/cron.md` |
| [ ] | Config, secrets, security, sandbox | schemas, config migration, SecretRef, auth, approvals, sandbox policy, SSRF/network safety | `src/config`, `src/secrets`, `src/security`, `src/agents/sandbox`, `docs/gateway/sandboxing.md` |
| [ ] | Control UI and web surfaces | Vite/Lit Control UI, chat, settings, agents, sessions, logs, i18n, WebChat/TUI docs | `ui/src/ui/views`, `ui/src/ui/controllers`, `ui/src/i18n`, `docs/web` |
| [~] | Companion apps and nodes | node.presence.alive verified; macOS app, iOS/Android nodes, shared OpenClawKit, pairing, node capabilities remain | `src/gateway/server-node-events.ts`, `apps/ios`, `apps/android`, `apps/shared` |
| [ ] | QA, tests, scenarios | unit/e2e/live/docker tests, QA Lab, scenario catalog, provider/channel regressions | `test/vitest`, `scripts/e2e`, `qa/scenarios`, `extensions/qa-lab` |
| [~] | Packaging, distribution, release | packageDistribution doctor JSON, dist inventory validation, update-status channel projection, and git branch channel labeling verified; npm package, plugin packages, Docker/Podman, macOS DMG/Sparkle, CI release workflows, update channels remain | `src/flows/doctor-health.ts`, `src/commands/doctor-install.ts`, `src/infra/update-global.ts`, `scripts/openclaw-npm-publish.sh`, `scripts/package-mac-dist.sh`, `Dockerfile`, `.github/workflows` |
| [ ] | Observability, diagnostics, ops | logging, OpenTelemetry/Prometheus, health/status, proxy capture, runtime reports | `src/logging`, `extensions/diagnostics-otel`, `extensions/diagnostics-prometheus`, `docs/logging.md` |

Plugin/extension row addendum: `memory-core-host-engine-qmd` helper coverage is
verified in `147b0978` and `memory-core-host-engine-storage` helper coverage is
verified in `884c9afb`; `@openclaw/memory-host-sdk/engine` aggregate coverage
is verified in `fa5ad046`; `@openclaw/memory-host-sdk/runtime` aggregate
coverage is verified in `ebd215d5`; memory-host package facade coverage for
`query`, `multimodal`, `secret`, and `status` is verified in `c95e0129`. All
are counted with the SDK helper/runtime set above.
The imported `agent-runtime` core SDK helper coverage from
`src/plugin-sdk/agent-runtime.ts` and adjacent agent scope/path/time/defaults/
identity/provider-id helpers is verified in `a8e871a3` and counted with the
plugin/extension system row above.
The imported `agent-runtime` model-selection SDK helper coverage from
`src/plugin-sdk/agent-runtime.ts`, `src/agents/model-selection.ts`,
`src/agents/model-selection-normalize.ts`,
`src/agents/model-selection-shared.ts`,
`src/agents/model-selection-resolve.ts`, and `src/agents/model-ref-shared.ts`
is verified in `0d009e7d` and counted with the plugin/extension system row
above.
The imported `speech-core` SDK helper coverage from
`src/plugin-sdk/speech-core.ts`, adjacent `src/tts/*` helpers, and
`src/agents/provider-http-errors.ts` is verified in `ff03eba7` and is counted
with the plugin/extension system row above.
The imported `video-generation-core` SDK helper coverage from
`src/plugin-sdk/video-generation-core.ts`, adjacent video/media generation
helpers, failover helpers, model input helpers, logging, and provider env-var
helpers is verified in `f85c7465` and is counted with the
plugin/extension system row above.
The imported `image-generation-core` SDK helper coverage from
`src/plugin-sdk/image-generation-core.ts`, adjacent image/media generation
helpers, Gemini auth, Google model id helpers, failover helpers, model input
helpers, logging, auth-runtime, and provider env-var helpers is verified in
`1a128fa5` and is counted with the plugin/extension system row above.
The imported `music-generation-core` SDK helper coverage from
`src/plugin-sdk/music-generation-core.ts`, adjacent music generation helpers,
failover helpers, model input helpers, logging, and provider env-var helpers
is verified in `a17da4e3` and is counted with the plugin/extension system row
above.
The imported `media-generation-runtime` and `media-generation-runtime-shared`
SDK helper coverage from `src/plugin-sdk/media-generation-runtime.ts`,
`src/plugin-sdk/media-generation-runtime-shared.ts`, and
`src/media-generation/runtime-shared.ts` is verified in `f475d85a` and is
counted with the plugin/extension system row above.
The imported `image-generation-runtime` SDK helper coverage from
`src/plugin-sdk/image-generation-runtime.ts` and
`src/image-generation/runtime.ts` is verified in `719fcee8` and is counted
with the plugin/extension system row above.
The imported `video-generation-runtime` SDK helper coverage from
`src/plugin-sdk/video-generation-runtime.ts`, `src/video-generation/runtime.ts`,
`src/video-generation/normalization.ts`, `src/video-generation/capabilities.ts`,
and `src/video-generation/duration-support.ts` is verified in `2cf18309` and
is counted with the plugin/extension system row above.
The imported `realtime-transcription` SDK helper coverage from
`src/plugin-sdk/realtime-transcription.ts`,
`src/realtime-transcription/provider-registry.ts`,
`src/plugins/provider-registry-shared.ts`, and
`src/realtime-transcription/websocket-session.ts` is verified in `18a7e15b`
and is counted with the plugin/extension system row above.
The imported `realtime-voice` SDK helper coverage from
`src/plugin-sdk/realtime-voice.ts`, `src/realtime-voice/provider-types.ts`,
`src/realtime-voice/provider-registry.ts`,
`src/realtime-voice/provider-resolver.ts`,
`src/realtime-voice/agent-consult-tool.ts`,
`src/realtime-voice/agent-consult-runtime.ts`,
`src/realtime-voice/session-runtime.ts`, and
`src/realtime-voice/audio-codec.ts` is verified in `0f6e62d7` and is counted
with the plugin/extension system row above.
The imported `media-understanding-runtime` SDK helper coverage from
`src/plugin-sdk/media-understanding-runtime.ts`,
`src/media-understanding/runtime.ts`,
`src/media-understanding/runtime-types.ts`, `src/media-understanding/runner.ts`,
`src/media-understanding/runner.entries.ts`,
`src/media-understanding/runner.attachments.ts`,
`src/media-understanding/attachments.normalize.ts`,
`src/media-understanding/attachments.select.ts`,
`src/media-understanding/attachments.cache.ts`,
`src/media-understanding/provider-registry.ts`, and
`src/media-understanding/resolve.ts` is verified in `65d2ce12` and is counted
with the plugin/extension system row above.
The imported `media-understanding` SDK provider-helper coverage from
`src/plugin-sdk/media-understanding.ts`,
`src/media-understanding/openai-compatible-video.ts`,
`src/media-understanding/openai-compatible-audio.ts`, and
`src/media-understanding/shared.ts` is verified in `4a383013` and is counted
with the plugin/extension system row above.
The imported `messaging-targets` SDK helper coverage from
`src/plugin-sdk/messaging-targets.ts` and `src/channels/targets.ts` is verified
in `cd85f7f5` and is counted with the plugin/extension system row above.
The imported `request-url` SDK helper coverage from
`src/plugin-sdk/request-url.ts` is reverified from the `f4a23a25`
fetch/SSRF helper checkpoint and is counted with the plugin/extension system
row above.
The imported `persistent-dedupe` SDK helper coverage from
`src/plugin-sdk/persistent-dedupe.ts` is verified in `cfe26bca` and is counted
with the plugin/extension system row above.
The imported `qa-runner-runtime` SDK helper coverage from
`src/plugin-sdk/qa-runner-runtime.ts` is verified in `f9d46a8f` and is counted
with the plugin/extension system row above.

Latest verified plugin SDK helper additions: `fetch-runtime` from
`src/plugin-sdk/fetch-runtime.ts`, `src/infra/fetch.ts`,
`src/infra/net/proxy-env.ts`, `src/infra/net/proxy-fetch.ts`, and
`src/infra/net/ssrf.ts` is checkpointed in `3aa66305` with focused,
adjacent, imported-plugin, `ruff`, and `mypy` evidence; `cli-backend` from
`src/plugin-sdk/cli-backend.ts` and `src/agents/cli-watchdog-defaults.ts` is
checkpointed in `be724e3f` with the same evidence class; type-only SDK barrels
`config-types`, `document-extractor`, `music-generation`,
`provider-model-types`, `qa-channel-protocol`, and `tts-runtime.types` are
checkpointed in `fceeecc8`; `config-schema` from
`src/plugin-sdk/config-schema.ts`, `src/config/zod-schema.ts`, and
`src/plugins/schema-validator.ts` is checkpointed in `ae5489b2`; `entrypoints`
from `src/plugin-sdk/entrypoints.ts` and
`scripts/lib/plugin-sdk-entrypoints.json` is checkpointed in `bd810f14`;
`diffs` from `src/plugin-sdk/diffs.ts` is checkpointed in `008c6120`; `acpx`
from `src/plugin-sdk/acpx.ts` is checkpointed in `c7541c95`;
`acp-runtime-backend` from `src/plugin-sdk/acp-runtime-backend.ts` is
checkpointed in `4833176b`; `acp-runtime` from `src/plugin-sdk/acp-runtime.ts`
is checkpointed in `44166f55`; `acp-binding-runtime` from
`src/plugin-sdk/acp-binding-runtime.ts` is checkpointed in `37b428c1`;
`cli-runtime` from `src/plugin-sdk/cli-runtime.ts` is checkpointed in
`c052ce13`; `runtime-doctor` from `src/plugin-sdk/runtime-doctor.ts` is
checkpointed in `1a917206`; `provider-setup` and
`self-hosted-provider-setup` from `src/plugin-sdk/provider-setup.ts` and
`src/plugin-sdk/self-hosted-provider-setup.ts` are checkpointed in
`25ad92b6`; `lmstudio` and `lmstudio-runtime` from
`src/plugin-sdk/lmstudio.ts`, `src/plugin-sdk/lmstudio-runtime.ts`,
`extensions/lmstudio/src/models.ts`, and `extensions/lmstudio/src/runtime.ts`
are checkpointed in `6f11c3fa`; `runtime-secret-resolution` from
`src/plugin-sdk/runtime-secret-resolution.ts`,
`src/cli/command-secret-targets.ts`, `src/secrets/resolve.ts`, and
`src/secrets/runtime-shared.ts` is checkpointed in `d9574b0f`;
`memory-core-host-query` from `src/plugin-sdk/memory-core-host-query.ts`,
`packages/memory-host-sdk/src/query.ts`, and
`packages/memory-host-sdk/src/host/query-expansion.ts` is checkpointed in
`0eaf8bf8`; `memory-core-host-multimodal` from
`src/plugin-sdk/memory-core-host-multimodal.ts`,
`packages/memory-host-sdk/src/multimodal.ts`, and
`packages/memory-host-sdk/src/host/multimodal.ts` is checkpointed in
`5be944f7`; `memory-core-host-secret` from
`src/plugin-sdk/memory-core-host-secret.ts`,
`packages/memory-host-sdk/src/secret.ts`, and
`packages/memory-host-sdk/src/host/secret-input.ts` is checkpointed in
`78f2a009`; `memory-core-host-events` from
`src/plugin-sdk/memory-core-host-events.ts` and
`src/memory-host-sdk/events.ts` is checkpointed in `d5695975`;
`memory-core-host-status` from `src/plugin-sdk/memory-core-host-status.ts`,
`packages/memory-host-sdk/src/status.ts`, and
`packages/memory-host-sdk/src/host/status-format.ts` is checkpointed in
`bfcb12a2`; `memory-core-host-runtime-files` from
`src/plugin-sdk/memory-core-host-runtime-files.ts`,
`packages/memory-host-sdk/src/runtime-files.ts`,
`packages/memory-host-sdk/src/host/internal.ts`,
`packages/memory-host-sdk/src/host/read-file.ts`, and
`packages/memory-host-sdk/src/host/backend-config.ts` is checkpointed in
`a8d7b586`; `memory-host-files` from
`src/plugin-sdk/memory-host-files.ts` is checkpointed in `857111d8`;
`memory-core-host-runtime-core` from
`src/plugin-sdk/memory-core-host-runtime-core.ts`,
`packages/memory-host-sdk/src/runtime-core.ts`, and adjacent memory state,
current-time, byte-size, routing, and transcript helper behavior is
checkpointed in `7b0703b7`; `memory-host-core` from
`src/plugin-sdk/memory-host-core.ts` is checkpointed in `362efd71`;
`memory-host-events` from `src/plugin-sdk/memory-host-events.ts` is
checkpointed in `97885bb6`; `memory-host-markdown` from
`src/plugin-sdk/memory-host-markdown.ts` is checkpointed in `4d8513b6`;
`memory-host-search` from `src/plugin-sdk/memory-host-search.ts`,
`src/plugin-sdk/memory-host-search.runtime.ts`, and
`src/plugins/memory-runtime.ts` is checkpointed in `a76a8d50`;
`memory-host-status` from `src/plugin-sdk/memory-host-status.ts` is
checkpointed in `2317c1e7`; `memory-core-host-runtime-cli` from
`src/plugin-sdk/memory-core-host-runtime-cli.ts`,
`packages/memory-host-sdk/src/runtime-cli.ts`, and adjacent
CLI/runtime/theme/progress/home-path helper behavior is checkpointed in
`762da43c`; `memory-core-engine-runtime` from
`src/plugin-sdk/memory-core-engine-runtime.ts` is checkpointed in `ad4b05e5`;
`memory-core-host-engine-embeddings` from
`src/plugin-sdk/memory-core-host-engine-embeddings.ts` and
`packages/memory-host-sdk/src/engine-embeddings.ts` is checkpointed in
`4a1d82a8`; `memory-core-host-engine-foundation` from
`src/plugin-sdk/memory-core-host-engine-foundation.ts` and
`packages/memory-host-sdk/src/engine-foundation.ts` is checkpointed in
`4d0b1103`; `memory-core-host-engine-qmd` from
`src/plugin-sdk/memory-core-host-engine-qmd.ts`,
`packages/memory-host-sdk/src/engine-qmd.ts`, and adjacent QMD
parser/scope/process/session-file/query helpers is checkpointed in
`147b0978`; `memory-core-host-engine-storage` from
`src/plugin-sdk/memory-core-host-engine-storage.ts`,
`packages/memory-host-sdk/src/engine-storage.ts`, and adjacent internal,
read-file, schema, sqlite, sqlite-vec, fs-utils, backend-config, and
multimodal helper behavior is checkpointed in `884c9afb`;
`@openclaw/memory-host-sdk/engine` from
`packages/memory-host-sdk/src/engine.ts`,
`src/memory-host-sdk/engine.ts`, and package export behavior is checkpointed in
`fa5ad046`; `@openclaw/memory-host-sdk/runtime` from
`packages/memory-host-sdk/src/runtime.ts`,
`src/memory-host-sdk/runtime.ts`, and package export behavior is checkpointed
in `ebd215d5`; `@openclaw/memory-host-sdk/query`, `multimodal`, `secret`, and
`status` package facades from `packages/memory-host-sdk/src/query.ts`,
`packages/memory-host-sdk/src/multimodal.ts`,
`packages/memory-host-sdk/src/secret.ts`, and
`packages/memory-host-sdk/src/status.ts` are checkpointed in `c95e0129`.
`speech-core` from `src/plugin-sdk/speech-core.ts`, adjacent `src/tts/*`
helpers, and `src/agents/provider-http-errors.ts` is checkpointed in
`ff03eba7`.
`video-generation-core` from `src/plugin-sdk/video-generation-core.ts`,
adjacent video/media generation helpers, failover helpers, model input
helpers, logging, and provider env-var helpers is checkpointed in `f85c7465`.
`image-generation-core` from `src/plugin-sdk/image-generation-core.ts`,
adjacent image/media generation helpers, Gemini auth, Google model id helpers,
failover helpers, model input helpers, logging, auth-runtime, and provider
env-var helpers is checkpointed in `1a128fa5`.
`music-generation-core` from `src/plugin-sdk/music-generation-core.ts`,
adjacent music generation helpers, failover helpers, model input helpers,
logging, and provider env-var helpers is checkpointed in `a17da4e3`.
`media-generation-runtime` and `media-generation-runtime-shared` from
`src/plugin-sdk/media-generation-runtime.ts`,
`src/plugin-sdk/media-generation-runtime-shared.ts`, and
`src/media-generation/runtime-shared.ts` are checkpointed in `f475d85a`.
`image-generation-runtime` from `src/plugin-sdk/image-generation-runtime.ts`
and `src/image-generation/runtime.ts` is checkpointed in `719fcee8`.
`video-generation-runtime` from `src/plugin-sdk/video-generation-runtime.ts`,
`src/video-generation/runtime.ts`, `src/video-generation/normalization.ts`,
`src/video-generation/capabilities.ts`, and
`src/video-generation/duration-support.ts` is checkpointed in `2cf18309`.
`realtime-transcription` from `src/plugin-sdk/realtime-transcription.ts`,
`src/realtime-transcription/provider-registry.ts`,
`src/plugins/provider-registry-shared.ts`, and
`src/realtime-transcription/websocket-session.ts` is checkpointed in
`18a7e15b`.
`realtime-voice` from `src/plugin-sdk/realtime-voice.ts`,
`src/realtime-voice/provider-types.ts`,
`src/realtime-voice/provider-registry.ts`,
`src/realtime-voice/provider-resolver.ts`,
`src/realtime-voice/agent-consult-tool.ts`,
`src/realtime-voice/agent-consult-runtime.ts`,
`src/realtime-voice/session-runtime.ts`, and
`src/realtime-voice/audio-codec.ts` is checkpointed in `0f6e62d7`.
`media-understanding-runtime` from
`src/plugin-sdk/media-understanding-runtime.ts`,
`src/media-understanding/runtime.ts`,
`src/media-understanding/runtime-types.ts`, `src/media-understanding/runner.ts`,
`src/media-understanding/runner.entries.ts`,
`src/media-understanding/runner.attachments.ts`,
`src/media-understanding/attachments.normalize.ts`,
`src/media-understanding/attachments.select.ts`,
`src/media-understanding/attachments.cache.ts`,
`src/media-understanding/provider-registry.ts`, and
`src/media-understanding/resolve.ts` is checkpointed in `65d2ce12`.
`media-understanding` from `src/plugin-sdk/media-understanding.ts`,
`src/media-understanding/openai-compatible-video.ts`,
`src/media-understanding/openai-compatible-audio.ts`, and
`src/media-understanding/shared.ts` is checkpointed in `4a383013`.
`messaging-targets` from `src/plugin-sdk/messaging-targets.ts` and
`src/channels/targets.ts` is checkpointed in `cd85f7f5`.
Count all with the plugin/extension system row above.

## How To Use This Map

- Split each broad domain into source-backed seams before implementation.
- Link every OpenZues parity row back to at least one OpenClaw source path.
- Do not give parity credit for Hermes/Warp similarities unless the OpenClaw
  behavior is also mapped and verified.
- Move broad domain rows only when the child seam weights are verified.
