# OpenClaw Source Domain Map

Agent report source: Banach

Last updated: 2026-05-08

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
| [~] | Channels, routing, delivery | Telegram audio/voice, Telegram `channels.logout` bot-token config cleanup, LINE `channels.logout` token/secret config cleanup, Nextcloud Talk signed bot send plus `channels.logout` bot-secret config cleanup, WhatsApp native send/poll/media/action breadth plus managed Web-auth `channels.logout` cleanup, QQBot credential `channels.logout` cleanup, Zalo user profile credential `channels.logout` cleanup, Synology Chat incoming-webhook, Mattermost channel-id and route-backed account probe, Feishu/Lark route-backed account probe, text and direct media sends plus read/post media resource hydration, presentation-card send/thread-reply, image/file/audio/video media sends with local-root guards, audioAsVoice transcode, mediaMaxMb caps, and channel capability metadata, and read/edit/pin/unpin/list-pins/channel-info/member-info/channel-list/react/reactions actions, Microsoft Teams Bot Framework proactive text/threaded replies, Adaptive Card polls, `/api/messages` bearer-gated webhook dispatch, configured Teams webhook path plus `/api/messages` fallback, Bot Framework JWT validation, attachment-only inbound placeholders, inbound attachment URL metadata, media staging, inbound media Graph/Bot Framework auth fallback, personal welcome-card member lifecycle, group welcome member lifecycle, adaptive-card inbound session routing, inbound mention stripping/HTML fallback, feedback invoke recording, feedback-disabled invoke consuming, feedback reflection learning/follow-up, SSO no-config invoke acknowledgement, configured SSO token exchange/store, configured SSO verify-state magic-code flow, SSO DM allowlist sign-in drop handling, SSO route allowlist sign-in drop handling, SSO group sender allowlist sign-in drop handling, Graph reaction listing/write/read/pin/unpin/list-pins/search/member-info/channel-list/channel-info actions, Bot Framework edit/delete/upload-file and adaptive-card send actions, stored delegated-token reaction writes, expired delegated-token fallback, delegated refresh-token flow, delegated OAuth setup URL/bootstrap/completion, delegated-auth probe posture, native readiness probe, user-reference routing, FileConsent, and Graph upload verified; Signal JSON-RPC send plus reaction actions and route-backed account probe, IRC PRIVMSG and route-backed account probe, Twitch chat route-backed sends plus send action and account probe, BlueBubbles native sends/actions/media plus account probe, Tlon route-backed account probe plus native HTTP-poke text/group reply sends, image-media upload hook, hosted Memex upload, custom S3 upload, DM inbound firehose session routing, group/thread inbound firehose session routing, inbound image media staging, inbound authorization/pending approvals, approval response replay, approval block/admin handling, production SSE monitor lifecycle, and `channels.start`/`channels.stop` native runtime wiring, and iMessage config-backed CLI/RPC account probe verified; channel registry, broader session routing, full inbound/outbound delivery, typing/status/reactions, pairing, access groups remain | `src/channels`, `src/routing`, `docs/channels`, `extensions/telegram/openclaw.plugin.json`, `extensions/line/src`, `extensions/whatsapp/src`, `extensions/qqbot/src`, `extensions/zalouser/src`, `extensions/googlechat/src`, `extensions/nextcloud-talk/src`, `extensions/mattermost/src`, `extensions/signal/src`, `extensions/irc/src`, `extensions/twitch/src`, `extensions/bluebubbles/src`, `extensions/tlon/src`, `extensions/imessage/src` |
| [ ] | Provider and model capability matrix | model catalogs, auth profiles, provider discovery, text/media/search/voice providers | `src/model-catalog`, `extensions/openai`, `extensions/anthropic`, `docs/providers` |
| [~] | Plugin and extension system | SDK, manifests, bundled/installed plugins, lifecycle, hooks, ClawHub/npm packaging; document and web-content extractor contracts plus CommonJS/ESM runtime import/execution, request-time tool factory context, text-runtime string helpers, string-coerce-runtime helpers, text-autolink-runtime helpers, dedupe-runtime helpers, retry-runtime helpers, keyed-async-queue helpers, lazy-value helpers, lazy-runtime helpers, config-paths helpers, context-visibility-runtime helpers, heartbeat-runtime helpers, json-store helpers, diagnostic-runtime helpers, system-event-runtime helpers, oauth-utils helpers, runtime-config-snapshot helpers, runtime-fetch helpers, runtime-doctor helpers, runtime-secret-resolution helpers, memory-core-host-query helpers, memory-core-host-multimodal helpers, memory-core-host-secret helpers, memory-core-host-events helpers, memory-core-host-status helpers, memory-core-engine-runtime facade helpers, memory-core-host-engine-embeddings helpers, memory-core-host-engine-foundation helpers, provider-setup helpers, self-hosted-provider-setup helpers, LM Studio runtime helpers, media-store helpers, browser-security-runtime helpers, command-primitives-runtime helpers, media-mime helpers, command-detection helpers, global-singleton helpers, concurrency-runtime helpers, channel-inbound-debounce helpers, channel-inbound helpers, channel-route helpers, channel-policy helpers, group-access helpers, group-activation helpers, provider-selection-runtime helpers, windows-spawn helpers, command-status helpers, command-auth native helpers, process-runtime command helpers, run-command normalized helpers, poll-runtime helpers, CLI runtime helpers, approval-auth-runtime helpers, approval-auth-helpers, approval-approvers helpers, approval-reply-runtime helpers, approval-renderers helpers, approval-client-helpers, approval-client-runtime alias helpers, approval-delivery-helpers, approval-native-helpers, approval-native-runtime delivery helpers/factory/expiration, approval-handler-adapter-runtime helpers, approval-handler-runtime adapter factory/wrapper/capability bridge, approval-runtime aggregate helpers, approval-gateway-runtime resolver helpers, Telegram command config helpers, param-readers helpers, provider-zai-endpoint helpers, provider-env-vars helpers, session-visibility helpers, simple-completion-runtime extractAssistantText helper, webhook helper shims, fetch/SSRF helper shims, provider model/catalog helper shims, models-provider-runtime helper shim, skill-commands-runtime helper shim, skills-runtime helper shim, provider entry/enable/auth-result helper shims, provider-auth-runtime helper shims, provider-auth API-key helper shims, provider-auth-login helper/runtime alias shims, provider-auth facade helper shims, provider web-search contract helper shims, provider web facade helper shims, device-bootstrap helper shims, runtime-store helper shims, runtime helper shims, directory-runtime helper shims, directory-config-runtime helper shims, thread-bindings-runtime helper shims, conversation-runtime helper shims, outbound-runtime helper shims, conversation-binding-runtime helper shims, session-binding/session-key runtime alias shims, session-store runtime helper shims, model-session-runtime helper shims, account-id/configured-id subpath shims, agent-media-payload helper shims, agent-config-primitives helper shims, ACP binding resolve helper shims, Anthropic CLI facade helper shims, Anthropic Vertex auth-presence helper shims, Anthropic Vertex facade helper shims, XAI model-id helper shims, channel pairing path helper shims, channel inbound root helper shims, channel location helper shims, state path helper shims, setup adapter runtime helper shims, channel secret TTS runtime helper shims, channel secret basic/runtime helper shims, secret-file-runtime helper shim, secret-ref-runtime helper shim, secret-input-runtime helper shim, secret-input-schema helper shim, cron-store-runtime helper shim, file-access-runtime helper shim, logging-core helper shim, native-command-config-runtime helper shim, host-runtime helper shim, image-generation-core auth-runtime helper shim, talk config runtime helper shims, GitHub Copilot token helper shims, channel plugin common/core helper shims, channel entry contract helper shims, channel config primitives/schema helper shims, runtime-env helper shims, gateway-runtime facade helper shim, hook-runtime facade helper shim, agent-runtime-test-contracts facade helper shim, channel-target-testing facade helper shim, channel-test-helpers facade helper shim, plugin-test-api facade helper shim, channel-config-helpers helper shims, channel-config-writes alias shim, channel-lifecycle helper shim, exact channel-core helper shim, channel-contract-testing helper shim, channel-targets helper shim, channel-streaming helper shim, channel-envelope helper shim, channel-mention-gating helper shim, channel-runtime-context helper shim, channel-runtime compatibility facade shim, channel-activity-runtime helper shim, inbound-envelope helper shim, allow-from helpers, allowlist-config-edit helpers, access-groups helpers, direct-DM access helpers, direct-DM guard-policy helpers, direct-DM helpers, channel-send-result helpers, channel-pairing helpers, command-auth helpers, channel-setup helpers, channel-reply-options-runtime helpers, channel-reply-pipeline helpers, channel-feedback helpers, markdown-table-runtime helpers, reply-history helpers, reply-reference helpers, reply-dedupe helpers, string-normalization helpers, dangerous-name helpers, channel-logging helpers, time-runtime helpers, number-runtime helpers, secure-random-runtime helpers, collection-runtime helpers, async-lock-runtime helpers, transport-ready-runtime helpers, target-resolver-runtime helpers, response-limit-runtime helpers, error-runtime helpers, temp-path helpers, secret-input helpers, routing/session helper shims, reply-chunking helpers, text-chunking helpers, reply-payload helpers, account-helper shims, account-core/account-resolution shims, tool-payload shims, boolean-param shims, channel-actions shims, status-helper shims, and channel-status shims verified; broader SDK helper/runtime contracts remain | `src/plugins`, `src/plugin-sdk`, `extensions`, `packages/plugin-sdk` |
| [ ] | Tools, skills, MCP, ACPX | browser/exec/diffs/file tools, skills, MCP integration, ACPX runtime, plugin commands | `src/tools`, `src/mcp`, `extensions/browser`, `extensions/acpx` |
| [ ] | Memory and knowledge | memory plugins, embeddings, dreaming, QMD/wiki/LanceDB, memory host SDK | `extensions/memory-core`, `extensions/memory-wiki`, `packages/memory-host-sdk`, `docs/concepts/memory.md` |
| [~] | Media, voice, web, canvas | canvas shortcode normalization verified; image/video/realtime voice/media understanding helper shims landed; music generation, web search/fetch, Canvas/A2UI breadth remain | `src/media`, `src/image-generation`, `src/realtime-voice`, `src/canvas-host`, `extensions/comfy` |
| [ ] | Automation, cron, tasks, commitments | scheduled runs, task commands, commitment safety, heartbeat/maintenance | `src/cron`, `src/tasks`, `src/commitments`, `docs/cli/cron.md` |
| [ ] | Config, secrets, security, sandbox | schemas, config migration, SecretRef, auth, approvals, sandbox policy, SSRF/network safety | `src/config`, `src/secrets`, `src/security`, `src/agents/sandbox`, `docs/gateway/sandboxing.md` |
| [ ] | Control UI and web surfaces | Vite/Lit Control UI, chat, settings, agents, sessions, logs, i18n, WebChat/TUI docs | `ui/src/ui/views`, `ui/src/ui/controllers`, `ui/src/i18n`, `docs/web` |
| [~] | Companion apps and nodes | node.presence.alive and QR human approval guidance verified; macOS app, iOS/Android nodes, shared OpenClawKit, pairing, node capabilities remain | `src/gateway/server-node-events.ts`, `apps/ios`, `apps/android`, `apps/shared` |
| [ ] | QA, tests, scenarios | unit/e2e/live/docker tests, QA Lab, scenario catalog, provider/channel regressions | `test/vitest`, `scripts/e2e`, `qa/scenarios`, `extensions/qa-lab` |
| [~] | Packaging, distribution, release | packageDistribution doctor JSON, dist inventory validation, exact missing-inventory diagnostics, missing/unexpected file drift warnings, legacy `.openclaw-install-stage*` debris warnings, mixed-case staging path proof, local build metadata/dependency omission, unsafe symlinked dist path warnings, externalized bundled extension dist omission, private QA dist omission, source-checkout package-root warnings, bundled runtime sidecar enforcement, and private-QA sidecar omission verified; source-install pnpm workspace warnings, update-status channel projection, registry/git availability, human update-available hints, git metadata envelope, config channel precedence, git branch channel labeling, loose/packed git-tag stable/beta channel labeling, update-status timeout, update status inherited parent options, update package-spec env override, explicit update install-spec preservation, root update runtime dispatch, package update runtime path, npm omit-optional fallback, package update version verification, package update failedStep projection, staged npm package swap, staged npm crash cleanup, npm shim rollback, git update control-ui clean-check exclusion, git update no-upstream guard, git preflight candidate/worktree/selection/rebase-abort/cleanup-repair/dev-target-ref/dev-branch-normalization guards, beta package latest fallback, post-update plugin sync, package update doctor repair, non-interactive update doctor, stale global rename-dir cleanup, low package-update disk warning, requested update-channel persistence, post-update package doctor env, stored update-channel dry-run preview, Corepack prompt suppression/preservation, Windows package install env, portable Git PATH prepending, owning/ambient npm command resolution, missing-version verifier wording, source-checkout package update verifier, package update missing dist-inventory gate, package update invalid dist-inventory rejection, package update dist inventory file drift, package update runtime staging-debris verifier, package update supplemental sidecar enforcement, package update inventory omission filters, package update unsafe dist path rejection, package update externalized extension omission, package update includeInCore inventory guard, package update private QA omission proof, package update malformed extension manifest rejection, doctor malformed extension manifest warning, package update legacy sidecar fallback, package update omitted-subtree safety ordering, and update dry-run package-spec preview verified; plugin packages, Docker/Podman, macOS DMG/Sparkle, CI release workflows, broader update channels remain | `src/flows/doctor-health.ts`, `src/commands/doctor-install.ts`, `src/infra/update-global.ts`, `src/infra/package-update-steps.ts`, `src/cli/update-cli/update-command.ts`, `src/cli/update-cli/status.ts`, `src/cli/update-cli.option-collisions.test.ts`, `src/infra/update-runner.ts`, `scripts/openclaw-npm-publish.sh`, `scripts/package-mac-dist.sh`, `Dockerfile`, `.github/workflows` |
| [ ] | Observability, diagnostics, ops | logging, OpenTelemetry/Prometheus, health/status, proxy capture, runtime reports | `src/logging`, `extensions/diagnostics-otel`, `extensions/diagnostics-prometheus`, `docs/logging.md` |

Packaging row addendum: `OZ-PKG-001CA` release-channel git update coverage
from `src/infra/update-runner.ts`, `src/infra/update-channels.ts`, and
`src/infra/update-check.ts` is checkpointed in `1f45d307`; it covers stable
tag selection, beta stable-fallback, detached checkout, and `no-release-tag`.
`OZ-PKG-001CB` preflight edge-failure proof from
`src/infra/update-runner.ts` is checkpointed in `7b15fafc`; it covers
`no-target-sha` and `preflight-no-good-commit`.
`OZ-PKG-001CC` startup auto-update dispatch from
`src/infra/update-startup.ts`, `src/infra/update-startup.test.ts`, and
`src/infra/update-check.ts` is checkpointed in `822eb6a9`; it covers
config-enabled package auto-update dispatch and `OPENCLAW_NO_AUTO_UPDATE`.
`OZ-PKG-001CD` startup auto-update throttling from
`src/infra/update-startup.ts` and `src/infra/update-startup.test.ts` is
checkpointed in `a1bb5d30`; it covers stable first-seen delay/jitter and beta
recent-attempt suppression.
`OZ-PKG-001CE` startup auto-update check-interval gating from
`src/infra/update-startup.ts` and `src/infra/update-startup.test.ts` is
checkpointed in `392177e5`; it covers persisted `lastCheckedAt` beta/stable
interval skips before version lookup or command execution.
`OZ-PKG-001CF` startup update availability hint state from
`src/infra/update-startup.ts` and `src/infra/update-startup.test.ts` is
checkpointed in `087924f8`; it covers persisted available/notified version
and tag fields, command-only `OPENCLAW_NO_AUTO_UPDATE` suppression, recent-check
availability hydration, and up-to-date availability clearing.
`OZ-PKG-001CG` startup update source-checkout availability clearing from
`src/infra/update-startup.ts` and `src/infra/update-startup.test.ts` is
checkpointed in `e66c5082`; it covers non-package install `lastCheckedAt`
refresh plus stale available/auto-first-seen state clearing before npm lookup.
`OZ-PKG-001CH` recurring startup update runner checks from
`src/infra/update-startup.ts` and `src/infra/update-startup.test.ts` are
checkpointed in `49150d76`; they cover repeated runner checks gated by
persisted `lastCheckedAt`.
`OZ-PKG-001CI` combined human update-status hint formatting from
`src/commands/status.update.ts` is checkpointed in `1d19a46c`; it covers the
OpenClaw ` · ` separator for combined git/npm availability details.

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
The imported `agent-runtime` tool bridge SDK helper coverage from
`src/plugin-sdk/agent-runtime.ts`, `src/agents/tools/common.ts`, and
`src/tools/*` descriptor/availability/planning/protocol helpers is verified in
`01653787` and counted with the plugin/extension system row above.
The imported `agent-runtime` facade utility coverage from model-auth markers,
sandbox paths, identity-avatar public source projection, and simple-completion
selection helpers is verified in `a6d70a6f` and counted with the
plugin/extension system row above.
The imported `agent-runtime` model-catalog lookup coverage from
`src/plugin-sdk/agent-runtime.ts`, `src/agents/model-catalog.ts`, and
`src/agents/model-catalog-lookup.ts` is verified in `a5794303` and counted
with the plugin/extension system row above.
The imported `agent-runtime` PI embedded utility coverage from
`src/plugin-sdk/agent-runtime.ts`, `src/agents/pi-embedded-utils.ts`, and
adjacent assistant-visible-text/reasoning-tag/chat-message helpers is verified
in `db2affa5` and counted with the plugin/extension system row above.
The imported `agent-runtime` embedded block chunker coverage from
`src/plugin-sdk/agent-runtime.ts`,
`src/agents/pi-embedded-block-chunker.ts`, and `src/markdown/fences.ts` is
verified in `da591809` and counted with the plugin/extension system row above.
The imported `agent-runtime` model-auth helper coverage from
`src/plugin-sdk/agent-runtime.ts`, `src/agents/model-auth.ts`,
`src/agents/model-auth-env.ts`, and adjacent auth/profile helpers is verified
in `b93c187b` and counted with the plugin/extension system row above.
The imported `agent-runtime` schema/typebox helper coverage from
`src/plugin-sdk/agent-runtime.ts`, `src/agents/schema/typebox.ts`,
`src/agents/schema/string-enum.ts`, and `src/infra/outbound/channel-target.ts`
is verified in `0884d4f3` and counted with the plugin/extension system row
above.
The imported `agent-runtime` web-tool helper coverage from
`src/plugin-sdk/agent-runtime.ts`, `src/agents/tools/web-shared.ts`,
`src/agents/tools/web-fetch-utils.ts`, and
`src/agents/tools/web-guarded-fetch.ts` is verified in `9bc67f5e` and counted
with the plugin/extension system row above.
The imported `agent-runtime` provider-auth alias helper coverage from
`src/plugin-sdk/agent-runtime.ts`, `src/agents/provider-auth-aliases.ts`,
`src/plugins/plugin-config-trust.ts`, and
`src/plugins/plugin-control-plane-context.ts` is verified in `61731b33` and
counted with the plugin/extension system row above.
The imported `agent-runtime` TTS helper coverage from
`src/plugin-sdk/agent-runtime.ts`, `src/tts/tts.ts`,
`src/plugin-sdk/tts-runtime.ts`, and `extensions/speech-core/src/tts.ts` is
verified in `9b328bbd` and counted with the plugin/extension system row above.
The imported `agent-runtime` agent-command entrypoint coverage from
`src/plugin-sdk/agent-runtime.ts`, `src/agents/agent-command.ts`,
`src/agents/agent-runtime-config.ts`, `src/agents/command/types.ts`, and
`src/commands/agent.ts` is verified in `9e6496fb` and counted with the
plugin/extension system row above.
The imported `file-lock` helper coverage from `src/plugin-sdk/file-lock.ts` is
verified in `ed03c127` and counted with the plugin/extension system row above.
The imported `google-model-id` alias coverage from
`src/plugin-sdk/google-model-id.ts` is verified in `67db67b5`, and the
imported `googlechat-runtime-shared` schema coverage from
`src/plugin-sdk/googlechat-runtime-shared.ts` is verified in `f721b7e3`, and
the imported `open-prose` exact helper coverage from
`src/plugin-sdk/open-prose.ts` is verified in `ef8830b1`, and imported
`runtime-group-policy` helper coverage from
`src/plugin-sdk/runtime-group-policy.ts` is verified in `b11adc13`; imported
`browser-cdp` helper coverage from `src/plugin-sdk/browser-cdp.ts` is verified
in `4e15c3c2`, imported `browser-config-support` coverage from
`src/plugin-sdk/browser-config-support.ts` is verified in `33463b7c`, and
imported `browser-config` facade coverage from
`src/plugin-sdk/browser-config.ts`, `src/plugin-sdk/browser-profiles.ts`,
`src/plugin-sdk/browser-control-auth.ts`, and
`src/plugin-sdk/browser-trash.ts` is verified in `300224b7`, and imported
`browser-control-auth` exact helper coverage from
`src/plugin-sdk/browser-control-auth.ts` plus
`extensions/browser/src/browser/control-auth.ts` is verified in `d1d7b371`,
and imported `browser-profiles` exact helper coverage from
`src/plugin-sdk/browser-profiles.ts` plus
`extensions/browser/browser-profiles.ts` is verified in `73d20703`, and
imported `browser-config-runtime` helper coverage from
`src/plugin-sdk/browser-config-runtime.ts`, `src/config/config.ts`,
`src/config/paths.ts`, `src/plugins/config-state.ts`, and
`src/utils/boolean.ts` is verified in `7a4ef6f0`, and imported
`browser-trash` exact helper coverage from `src/plugin-sdk/browser-trash.ts`
is verified in `9a90555e`, and imported `browser-maintenance` exact helper
coverage from `src/plugin-sdk/browser-maintenance.ts` is verified in
`ce39d8c6`, and imported `browser-host-inspection` exact helper coverage from
`src/plugin-sdk/browser-host-inspection.ts` and
`extensions/browser/src/browser/chrome.executables.ts` is verified in
`bf5ce3f0`, and imported `browser-node-host` exact facade coverage from
`src/plugin-sdk/browser-node-host.ts` and
`extensions/browser/src/node-host/invoke-browser.ts` is verified in
`2ef00b04`, and imported `browser-node-runtime` aggregate coverage from
`src/plugin-sdk/browser-node-runtime.ts` and
`extensions/browser/src/sdk-node-runtime.ts` is verified in `bc7ef301`, and
imported `gateway-runtime` facade coverage from
`src/plugin-sdk/gateway-runtime.ts`, adjacent gateway client/auth/node helpers,
`src/cli/gateway-rpc.ts`, and `src/infra/ws.ts` is verified in `dc028590`, and
imported `hook-runtime` facade coverage from `src/plugin-sdk/hook-runtime.ts`,
`src/hooks/fire-and-forget.ts`, `src/hooks/internal-hooks.ts`,
`src/hooks/message-hook-mappers.ts`, and
`src/plugins/hook-runner-global.ts` is verified in `89db1c12`, and imported
`agent-runtime-test-contracts` facade coverage from
`src/plugin-sdk/agent-runtime-test-contracts.ts` plus adjacent
`src/plugin-sdk/test-helpers/agents/*` contract fixtures is verified in
`0db396fe`, and imported `channel-target-testing` facade coverage from
`src/plugin-sdk/channel-target-testing.ts` and
`src/test-helpers/resolve-target-error-cases.ts` is verified in `e6307d8a`,
and imported `channel-test-helpers` facade coverage from
`src/plugin-sdk/channel-test-helpers.ts` plus adjacent
`src/plugin-sdk/test-helpers/*` channel helper modules and
`src/test-utils/channel-plugins.ts` is verified in `67872a14`, and
imported `plugin-test-api` facade coverage from
`src/plugin-sdk/plugin-test-api.ts` is verified in `db9e84ac`, imported
`plugin-test-contracts` facade coverage from
`src/plugin-sdk/plugin-test-contracts.ts` and adjacent
`src/plugin-sdk/test-helpers/*` contract modules is verified in `086382f8`,
imported `plugin-test-runtime` aggregate coverage from
`src/plugin-sdk/plugin-test-runtime.ts` is verified in `084da020`, imported
`provider-test-contracts` aggregate coverage from
`src/plugin-sdk/provider-test-contracts.ts` and adjacent
`src/plugin-sdk/test-helpers/*provider*` helper suites is verified in
`7494160a`, imported `test-env` aggregate coverage from
`src/plugin-sdk/test-env.ts` and adjacent env/network/time fixture helpers is
verified in `e2368bf5`, imported `test-fixtures` aggregate coverage from
`src/plugin-sdk/test-fixtures.ts` and adjacent generic fixture helpers is
verified in `aa63f674`, imported `test-node-mocks` aggregate coverage from
`src/plugin-sdk/test-node-mocks.ts` and adjacent node builtin mock helpers is
verified in `b5b60a9e`, imported `provider-http-test-mocks` aggregate
coverage from `src/plugin-sdk/provider-http-test-mocks.ts` and adjacent
provider HTTP mock helpers is verified in `462e8f82`, and imported
deprecated `testing` compatibility coverage from `src/plugin-sdk/testing.ts`
and adjacent runtime guard/min-host/runtime-sidecar helper sources is verified
in `e6747208`, and imported `browser-setup-tools` aggregate coverage from
`src/plugin-sdk/browser-setup-tools.ts` and
`extensions/browser/src/sdk-setup-tools.ts` is verified in `50876922`, and
imported `browser-support` aggregate coverage from
`src/plugin-sdk/browser-support.ts` is verified in `37eec77e`, and imported
`browser-bridge` exact facade coverage from `src/plugin-sdk/browser-bridge.ts`
is verified in `f0635cce`, and imported `agent-harness-runtime` /
`agent-harness` exact helper coverage from
`src/plugin-sdk/agent-harness-runtime.ts` and `src/plugin-sdk/agent-harness.ts`
is verified in `ee7f5c49`, and imported `sandbox` exact helper coverage from
`src/plugin-sdk/sandbox.ts` plus adjacent `src/agents/sandbox/*` helpers is
verified in `2aba5dbc`, and imported `proxy-capture` exact helper coverage
from `src/plugin-sdk/proxy-capture.ts` plus adjacent `src/proxy-capture/*`
helpers is verified in `84300681`, and imported `setup-runtime` exact helper
coverage from `src/plugin-sdk/setup-runtime.ts` plus adjacent setup wizard
helpers is verified in `252f28fe`, and imported `setup-tools` exact helper
coverage from `src/plugin-sdk/setup-tools.ts` plus adjacent CLI, archive,
brew, binary detection, docs-link, and config-dir helpers is verified in
`e0f1e72c`, and imported `setup` exact facade coverage from
`src/plugin-sdk/setup.ts` plus adjacent setup helper, setup wizard, setup
binary, setup proxy, setup group-access, setup-tools, config secret, utils,
and resolution-note helpers is verified in `ec94f934`, and imported
`config-runtime` exact helper coverage from
`src/plugin-sdk/config-runtime.ts` plus adjacent plugin config, config IO,
config mutation, config logging, session-store, session-reset, and config
policy helpers is verified in `74fd1711`, and imported
`plugin-config-runtime` exact helper coverage from
`src/plugin-sdk/plugin-config-runtime.ts` plus adjacent plugin config-state
helpers is verified in `458d6c7f`, and imported `config-mutation` exact
helper coverage from `src/plugin-sdk/config-mutation.ts` plus adjacent config
mutation, config IO, config logging, and model shared update helpers is
verified in `a9813667`, and imported `provider-tools` exact helper coverage
from `src/plugin-sdk/provider-tools.ts`, `src/agents/schema/clean-for-gemini.ts`,
and `src/plugins/provider-model-compat.ts` is verified in `2762ee46`, and
imported `provider-stream-shared` exact helper coverage from
`src/plugin-sdk/provider-stream-shared.ts`,
`src/agents/pi-embedded-runner/stream-payload-utils.ts`, adjacent stream
wrappers, and `src/shared/message-content-blocks.ts` is verified in
`711865e0`, and imported `provider-stream` / `provider-stream-family` exact
helper coverage from `src/plugin-sdk/provider-stream.ts` and
`src/plugin-sdk/provider-stream-family.ts` is verified in `da9a3e66`, and
imported `provider-transport-runtime` exact helper coverage from
`src/plugin-sdk/provider-transport-runtime.ts` plus adjacent transport stream,
message-transform, prompt-boundary, and OpenAI completions helpers is verified
in `dd8bcfd8`, and imported `provider-http` exact helper coverage from
`src/plugin-sdk/provider-http.ts`, `src/agents/provider-http-errors.ts`,
`src/media-understanding/shared.ts`, `src/agents/provider-attribution.ts`, and
`src/agents/provider-request-config.ts` is verified in `750bbf71`, and
imported `provider-catalog-runtime` exact helper coverage from
`src/plugin-sdk/provider-catalog-runtime.ts`,
`src/plugins/provider-runtime.ts`, `src/plugins/providers.ts`, and
`src/plugins/providers.runtime.ts` is verified in `2ede5f0d`. All are counted
with the plugin/extension system row above.
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
`provider-http` from `src/plugin-sdk/provider-http.ts`, adjacent
`src/agents/provider-http-errors.ts`, `src/media-understanding/shared.ts`,
`src/agents/provider-attribution.ts`, and
`src/agents/provider-request-config.ts` is checkpointed in `750bbf71`.
`provider-catalog-runtime` from
`src/plugin-sdk/provider-catalog-runtime.ts`, adjacent
`src/plugins/provider-runtime.ts`, `src/plugins/providers.ts`, and
`src/plugins/providers.runtime.ts` is checkpointed in `2ede5f0d`.
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
`channel-runtime` from `src/plugin-sdk/channel-runtime.ts`,
`src/channels/chat-type.ts`, `src/channels/reply-prefix.ts`,
`src/channels/typing.ts`, `src/channels/plugins/outbound/interactive.ts`,
`src/polls.ts`, `src/infra/system-events.ts`,
`src/infra/channel-activity.ts`, `src/infra/heartbeat-events.ts`,
`src/infra/heartbeat-visibility.ts`, `src/infra/transport-ready.ts`, and
`src/plugin-sdk/channel-lifecycle.core.ts` is checkpointed in `1cc947f3`.
`compat` from `src/plugin-sdk/compat.ts`, adjacent
`src/plugin-sdk/channel-reply-pipeline.ts`,
`src/plugin-sdk/channel-lifecycle.core.ts`,
`src/plugin-sdk/runtime-store.ts`, `src/plugin-sdk/keyed-async-queue.ts`,
`src/plugin-sdk/account-id.ts`, `src/plugin-sdk/temp-path.ts`,
`src/plugin-sdk/channel-config-helpers.ts`,
`src/plugin-sdk/allow-from.ts`, `src/plugin-sdk/channel-config-schema.ts`,
`src/plugin-sdk/channel-policy.ts`, `src/plugin-sdk/reply-history.ts`,
`src/plugin-sdk/directory-runtime.ts`,
`src/plugin-sdk/bluebubbles-policy.ts`, `src/plugin-sdk/bluebubbles.ts`,
`src/channels/command-gating.ts`, `src/context-engine/delegate.ts`,
`src/context-engine/registry.ts`, `src/infra/diagnostic-events.ts`,
`src/agents/schema/typebox.ts`, and
`src/plugins/provider-auth-helpers.ts` is checkpointed in `f21a22bd`.
`discord` from `src/plugin-sdk/discord.ts`, adjacent channel common/status/
config schema contracts, and bundled Discord public-surface delegation for
`api.js` and `runtime-api.js` is checkpointed in `307777d8`.
`extension-shared` from `src/plugin-sdk/extension-shared.ts`, adjacent
`src/utils/zod-parse.ts`, `src/utils/fetch-timeout.ts`,
`src/infra/net/proxy-env.ts`, `src/secrets/ref-contract.ts`,
`src/plugin-sdk/channel-lifecycle.core.ts`, and
`src/plugin-sdk/runtime-logger.ts` is checkpointed in `b56d15d7`.
`resolution-notes` from `src/plugin-sdk/resolution-notes.ts` is checkpointed
in `9c56ff39`.
`facade-loader` from `src/plugin-sdk/facade-loader.ts` is checkpointed in
`29aa7956`.
`session-transcript-hit` from `src/plugin-sdk/session-transcript-hit.ts` is
checkpointed in `b294d317`.
`pairing-access` from `src/plugin-sdk/pairing-access.ts` is checkpointed in
`e04677d3`.
`facade-resolution-shared` from `src/plugin-sdk/facade-resolution-shared.ts`
is checkpointed in `2938b03a`.
`facade-runtime` from `src/plugin-sdk/facade-runtime.ts` is checkpointed in
`1e9b65f5`.
`test-helpers/string-utils` from
`src/plugin-sdk/test-helpers/string-utils.ts` is checkpointed in `e2ba3082`.
Count all with the plugin/extension system row above.

## How To Use This Map

- Split each broad domain into source-backed seams before implementation.
- Link every OpenZues parity row back to at least one OpenClaw source path.
- Do not give parity credit for Hermes/Warp similarities unless the OpenClaw
  behavior is also mapped and verified.
- Move broad domain rows only when the child seam weights are verified.
