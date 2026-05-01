# OpenClaw Parity Unresolved Seams

Updated: 2026-05-01

Current percentage rollup:

- Repo-wide OpenClaw parity is estimated at ~45% overall, with a reasonable
  band of ~40-50%.
- The active gateway/session/tool-contract family is estimated at ~97% of the
  bounded OpenZues-local parity path.
- The chat/session contract subfamily is estimated at ~98% after the latest
  `chat.send`, `chat.inject`, `chat.abort`, `sessions.create`,
  `sessions.patch`, `sessions.delete`, `sessions.spawn`, and `tools.invoke`
  runtime seams.
- Fully locked bounded slices are now tracked in
  `docs/openclaw-parity-progress.md` under "Fully Completed / Locked Bounded
  Slices"; remaining queue heads here should focus on sandbox runtime setup,
  channel-registered thread binders, broader provider-native adapters,
  CLI/runtime breadth, packaging/doctor surfaces, and companion app parity.

Current queue-head adjustment: `sessions.spawn runtime="acp"` now uses a real
native `GatewayAcpSpawnService` backed by `RuntimeManager`, including thread
creation/resume, child turn start, durable ACP session metadata, tracked
`agent.wait` cleanup, and parent completion announcements. The old unavailable
boundary remains only when no ACP spawn service is registered, and ACP preflight
errors for attachments, `lightContext`, and `sandbox="require"` are preserved.
ACP `mode="session"` now also matches OpenClaw's guard by returning
`errorCode="thread_required"` unless `thread=true`, before dispatching any
RuntimeManager thread or turn.
ACP-backed `sessions.delete` and `sessions.reset` now run OpenClaw-shaped
runtime cleanup before mutating local session state: cancel first, then close
with `discardPersistentState=true`, `requireAcpSession=false`, and
`allowBackendUnavailable=true`. The production RuntimeManager ACP adapter
best-effort interrupts active Codex app-server turns during cancel, while the
local metadata/transcript mutation remains native to OpenZues. Remaining ACP
parity is the standalone ACP bridge server/client harness and deeper protocol
session presentation, permission, and replay breadth.
ACP `sessions.spawn` now also resolves OpenClaw's target-agent policy before
runtime dispatch: explicit `agentId` wins, `acp.defaultAgent` supplies the
default, missing targets return `errorCode="target_agent_required"`, and
`acp.allowedAgents` rejects forbidden targets with
`errorCode="agent_forbidden"`. Accepted RuntimeManager ACP child sessions are
now stamped under `agent:<targetAgentId>:acp:<runtimeId>` and persist the
resolved target agent id in session metadata.
ACP `streamTo="parent"` accepted runs now continue through the same native
tracking path as ordinary ACP spawns: child metadata is persisted, run tracking
is registered for `agent.wait`, cleanup policy is consumed on terminal waits,
parent completion announcements still fire, and `streamLogPath` / `note`
fields are preserved in the spawn response. The RuntimeManager ACP adapter now
also rejects `streamTo="parent"` without a requester session before starting a
thread, matching OpenClaw's `requester_session_required` guard. Remaining ACP
parity is the standalone ACP bridge server/client harness and deeper protocol
session presentation, permission, replay, and parent-stream relay breadth.
RuntimeManager-backed ACP prompt dispatch now also mirrors OpenClaw's prompt
presentation prefix: when a child turn has `cwd`, the adapter sends
`[Working directory: ...]` before the task text and redacts the user home to
`~` while preserving Windows backslash separators. Remaining ACP presentation
parity is deeper bridge server/client protocol metadata and replay behavior.
ACP spawns that omit `cwd` now also inherit the target custom agent workspace
before runtime dispatch, drop that inherited cwd when the workspace no longer
exists so the backend can choose its default, and return
`errorCode="cwd_resolution_failed"` for non-missing workspace access failures
without starting the ACP runtime.
RuntimeManager-backed ACP accepted responses now also include OpenClaw's
mode-specific accepted notes for ordinary run spawns and persistent
thread-bound session spawns. Remaining ACP presentation parity is deeper
bridge server/client protocol metadata, replay behavior, and parent-stream
relay breadth.
RuntimeManager-backed ACP `thread=true` spawns now also match OpenClaw's
provider-context preflight: persistent thread-bound ACP sessions require a
requester channel context and return `errorCode="thread_binding_invalid"`
before any RuntimeManager thread or turn is started when that context is
missing. RuntimeManager-backed current-placement ACP sessions now also synthesize
OpenClaw-shaped current-conversation binding metadata from requester provider
context: LINE-style targets normalize into a persistent `sessionBinding`
(`targetKind="session"`, `placement="current"`), while `threadBinding` and
`completionDelivery` keep the routable account/channel/target fields for
wait-time completion delivery. LINE group/current contexts now also preserve
OpenClaw's fallback precedence by binding and delivering to `agentGroupId`
when it is present, and the gateway method owner now forwards that group
context to the production ACP spawn adapter instead of dropping LINE at channel
normalization. RuntimeManager-backed Matrix ACP `thread=true` sessions now also
synthesize child-placement binding metadata from requester context, preserving
canonical Matrix room casing in `sessionBinding.conversation.parentConversationId`
and using the native ACP runtime thread id as OpenZues' local child-thread
handle for `threadBinding`, `completionDelivery`, and
`sessionBinding.metadata`. Matrix top-level `channel:<room>` requester targets
now also format bound delivery as `room:<room>` the way OpenClaw's Matrix
delivery resolver does, and Discord child-placement delivery now targets
`channel:<child-runtime-thread>` instead of the requester parent channel.
RuntimeManager-backed ACP thread-binding records now also include OpenClaw-style
thread intro metadata, including `threadName`, optional `label`, and the
runtime cwd line when `cwd` is present.
Remaining ACP binding parity is real provider-native child-thread
creation/store breadth, unbind lifecycle breadth, and the
standalone ACP bridge server/client runtime.
Gateway-level ACP `thread=true` spawns now also honor OpenClaw's channel
thread-binding spawn policy for explicit
`channels.<channel>.threadBindings.spawnAcpSessions=false`, returning the same
`thread_binding_invalid` error before runtime dispatch. Remaining ACP binding
parity is provider-adapter capability/placement defaults, persistent session
binding records, and unbind lifecycle breadth.
Gateway-level subagent `thread=true` spawns now also honor OpenClaw's channel
thread-binding spawn policy for explicit
`channels.<channel>.threadBindings.spawnSubagentSessions=false`, returning the
same no-dispatch policy error before route binding or child runtime dispatch.
OpenClaw's child-placement channel default is now also mirrored for gateway
ACP and subagent thread spawns: Discord and Matrix require explicit
`spawnAcpSessions=true` / `spawnSubagentSessions=true` when the spawn flag is
unset, while current-placement channels keep the permissive default. Remaining
thread-binding parity is provider-adapter capability breadth and
unbind/end-hook lifecycle breadth.
OpenClaw's canonical `session.threadBindings` config keys now survive native
config writes for `enabled`, `idleHours`, and `maxAgeHours`, while legacy
`threadBindings.ttlHours` is rejected at session, channel, and channel-account
paths before snapshot validation. The doctor surface now also reports a native
`legacyConfig` contribution for already-persisted `ttlHours` keys and
`doctor --fix` rewrites them to `idleHours` before the rest of doctor reads the
validated snapshot. The same native `legacyConfig` contribution now also covers
OpenClaw's nested Slack, Google Chat, and Discord `allow` -> `enabled` channel
alias migration, including account-scoped channel/group/guild-channel entries.
It also migrates `tools.web.x_search.apiKey` into
`plugins.entries.xai.config.webSearch.apiKey`, preserving non-auth legacy
`x_search` knobs and existing plugin-owned auth.
Telegram legacy streaming aliases now also flow through the same doctor
contribution: `streamMode`, scalar/boolean `streaming`, `chunkMode`,
`blockStreaming`, `draftChunk`, and `blockStreamingCoalesce` migrate into
nested `channels.telegram.streaming` / account-scoped streaming config.
Slack legacy streaming aliases now also normalize through `doctor --json` /
`doctor --fix`: `streamMode`, scalar/boolean `streaming`, `chunkMode`,
`blockStreaming`, `blockStreamingCoalesce`, and `nativeStreaming` migrate into
nested `channels.slack.streaming` / account-scoped streaming config, including
`nativeStreaming` -> `nativeTransport`.
Google Chat legacy `streamMode` keys are now removed through the same native
doctor contribution for root and account-scoped channel config.
Runtime gateway legacy config now also follows OpenClaw's compatibility
migrator for non-loopback Control UI safety: `doctor --fix` seeds
`gateway.controlUi.allowedOrigins` for existing `lan` / `tailnet` / `custom` /
`auto` binds when no explicit origins are configured, and legacy
`gateway.bind` host aliases normalize to bind modes.
Legacy `audio.transcription` now migrates into
`tools.media.audio.models` through `doctor --fix`, including safe executable
mapping, existing-model preservation, invalid-command removal, and `tools.media`
config retention.
Agent sandbox `perSession` aliases now migrate to `sandbox.scope` for
`agents.defaults.sandbox` and `agents.list[].sandbox`, including explicit-scope
preservation.
Top-level `memorySearch` now migrates into
`agents.defaults.memorySearch`, merging only missing nested fields when defaults
already exist.
Top-level `heartbeat` now splits into `agents.defaults.heartbeat` and
`channels.defaults.heartbeat`, with existing defaults receiving only missing
fields and empty legacy heartbeat blocks removed.
TTS provider config now normalizes legacy `messages.tts.<provider>` and
`plugins.entries.voice-call.config.tts.<provider>` keys into nested
`tts.providers`, including `edge` -> `microsoft`.
`tools.web.search` provider-owned config now also migrates into bundled plugin
entry `webSearch` config: global `apiKey` maps to Brave, provider-scoped
records such as `grok` and `kimi` map through the OpenClaw manifest ownership
table to `xai` and `moonshot`, existing plugin config wins, and modern
`openaiCodex` search config stays under `tools.web.search`.
OpenClaw's bundled plugin load-path doctor helper is now covered by a native
`bundledPluginLoadPaths` contribution: legacy `plugins.load.paths` entries
that still point at source-style `extensions/<plugin>` are detected, warned,
and rewritten to packaged `dist/extensions/<plugin>` or
`dist-runtime/extensions/<plugin>` paths before stale plugin config cleanup
runs.
OpenClaw's stale plugin config doctor helper is now covered by a native
`stalePluginConfig` doctor contribution: `doctor --json` scans
`plugins.allow` and `plugins.entries.<id>` against native/bundled plugin
registry ids, `doctor --fix` removes stale allow/entry references, and repair
pauses with the upstream warning when plugin manifest discovery has errors.
OpenClaw's legacy plugin manifest contract-key doctor helper is now covered by
a native `legacyPluginManifests` contribution: manifest load paths are scanned
for top-level `speechProviders`, `mediaUnderstandingProviders`, and
`imageGenerationProviders`, `doctor --json` reports the upstream migration
lines, and `doctor --fix` moves/removes those keys under `contracts` before
stale plugin cleanup runs.
Open DM policy wildcard repair now also follows OpenClaw's
`open-policy-allowfrom` helper: `doctor --json` reports the missing
`allowFrom` wildcard changes, `doctor --fix` writes top-level or nested
wildcards based on channel mode, and nested `dm.policy="open"` is
canonicalized for channels that support top-level `dmPolicy`.
Allowlist DM policy sender recovery now also follows OpenClaw's
`allowlist-policy-repair` helper: `doctor --fix` restores missing
`allowFrom` sender lists from the saved channel pairing store, dedupes and
normalizes stored senders, and writes top-level or nested `allowFrom` based on
the channel mode.
The currently identified OpenClaw legacy-config doctor migrator files are now
covered by native OpenZues repair paths. Future config work should come from a
new upstream migration file or validation seam rather than this closed queue.
The repo-level queue now returns to the runtime lifecycle head: persistent
thread-bound provider binding records and unbind/end-hook lifecycle breadth.

Current queue-head adjustment: `sessions.spawn sandbox="require"` now has a
production app-wired `RuntimeManagerSandboxChatSendService` that starts Codex
app-server child turns with an explicit `workspace-write` sandbox override,
calls Windows sandbox setup before dispatch, persists `sandboxed`,
`sandboxMode`, sandbox policy, runtime id, runtime thread/session ids, and
still returns the existing precise forbidden response when no sandbox runtime
is available. `sandbox="require"` now also resolves OpenClaw's
`agents.defaults.sandbox` plus `agents.list[].sandbox` target posture before
dispatching; targets whose effective sandbox `mode` is `off` keep the same
forbidden response even when a sandbox send adapter is wired. Remaining sandbox
parity is deeper media/workspace staging behavior from OpenClaw. Sandboxed
requesters now also match OpenClaw's guard by forbidding unsandboxed child
targets even when the caller leaves `sandbox="inherit"`, and effectively
sandboxed `mode="all"` / `mode="non-main"` child targets now dispatch through
the native sandbox runtime even when the caller uses inherited sandbox policy.
The native sandbox adapter now preserves read-only Codex sandbox policy metadata
when dispatched with `sandbox_mode="read-only"`; remaining staging work is
limited to deeper OpenClaw provider filesystem staging. Explicit
`workspaceAccess="ro"` and `"none"` now map to native read-only sandbox turns,
while omitted/`"rw"` access keeps the writable workspace sandbox path.
Sandboxed `sessions.spawn` calls that omit `cwd` now stage inline attachments
inside the resolved child sandbox workspace from `workspaceRoot`, persist that
workspace as `spawnedWorkspaceDir`, pass it into the sandbox runtime dispatch,
and keep the OpenClaw untrusted-attachment prompt suffix.
Sandboxed spawned-session `agent` follow-up launches now also resolve the saved
`spawnedWorkspaceDir` / `sandboxWorkspaceRoot`, dispatch through the native
sandbox runtime with `sandbox="require"`, the persisted sandbox mode, and the
target agent id, persist returned runtime/policy metadata, and keep the run
tracked for `agent.wait` instead of leaking the follow-up through the host
control-chat runtime.
Sandboxed `chat.send` now also stages managed path-backed inbound attachments
already persisted under `openzuesSavedPath`, copying them into the child
workspace's `media/inbound` directory and rewriting runtime attachment metadata
to sandbox-relative media refs instead of host paths.
If provisional child metadata/session materialization fails after inline
attachment staging, OpenZues now removes the staged attachment directory,
forgets provisional child state, and returns the spawn error envelope before
dispatching the child runtime.
Tracked child-run completion now also applies OpenClaw-style attachment
retention cleanup: staged `sessions.spawn` attachment dirs are removed for
`cleanup="delete"` and for kept sessions unless
`tools.sessions_spawn.attachments.retainOnSessionKeep=true` is configured.
The same OpenClaw attachment config block is now schema-preserved and consumed
for explicit `enabled=false`, `maxFiles`, `maxFileBytes`, `maxTotalBytes`, and
`retainOnSessionKeep` behavior; absent config stays on OpenZues' compatible
enabled path.
Sandboxed `chat.send` attachment delivery now stages base64 media into the
session workspace under `media/inbound/...`, strips inline payload bytes before
runtime handoff, and carries sandbox-relative media paths in the runtime prompt.
The sibling `sessions.send` attachment path now uses the same sandbox workspace
staging behavior, and `sessions.steer` now does the same for steered follow-up
messages. Node `agent.request` attachment delivery now also stages sandboxed
media into the target session workspace before runtime handoff. Remaining
sandbox media staging work is deeper inbound provider media staging.
The CLI now exposes `sandbox list --json` with OpenClaw-shaped top-level
`containers` / `browsers` arrays sourced from saved sandbox session metadata,
`sandbox explain` JSON/human output with OpenClaw's top-level `docsUrl`,
`agentId`, `sessionKey`, `mainSessionKey`, `sandbox`, `elevated`, and `fixIt`
fields backed by saved sandbox runtime metadata, and `sandbox recreate` target
validation plus `--force` cleanup for saved sandbox runtime metadata so stale
runtime posture is forgotten and recreated on the next use. `sandbox explain`
now also resolves config-only sandbox posture from OpenClaw-shaped
`agents.defaults.sandbox`, `agents.list[].sandbox`, `tools.sandbox.tools`,
and `agents.list[].tools.sandbox.tools` config: mode/scope/workspace access,
default allow/deny policy, explicit `allow`/`alsoAllow`/`deny`, source
metadata, and the actionable `agents.defaults.sandbox.mode=off` fix-it entries
are projected even before a sandbox runtime has been spawned.

Current queue-head adjustment: `sessions.spawn thread=true` now has a
production route-backed `GatewaySubagentThreadBinderRegistry` wired at app
construction. Supported Slack, Telegram, Discord, WhatsApp, LINE, and Matrix
route contexts create persistent child sessions, force cleanup to `keep`, store
thread/account/channel binding metadata, and route completion delivery through
the bound thread. Binder results must now report both `status="ok"` and
`threadBindingReady=true`; unsupported, unconfigured, or not-ready channels
still return the upstream-shaped error before child dispatch. Remaining
lifecycle parity is deeper provider-native unbind/end-hook behavior and
ACP/session binding policy breadth.
Initial thread-bound child runs now dispatch through the chat-send adapter with
the bound `channel`, `to`, `account_id`, and `thread_id` kwargs instead of
starting as an unbound control-chat-only turn.
Thread-bound child runs whose binding hook reports readiness without a
routable delivery origin now also follow OpenClaw's generic-binding fallback:
the initial child turn receives the requester channel context with
`deliver=false`, stays persistent with `cleanup="keep"`, and keeps parent
completion announcements enabled.
Terminal `agent.wait` completion announcements now also use the saved
`completionDelivery` route through the direct channel-send service and persist
the provider delivery result/error on the child session metadata.
Thread-bound subagent startup failures now also run best-effort binding cleanup
after a binding has been prepared but before the child run is accepted: the
fakeable binder protocol exposes `unbind`, the production route-backed binder
returns a stateless no-op cleanup result, and the provisional child transcript
and metadata are still deleted with the original actionable startup error.
Route-backed thread-bound subagent spawns now persist an OpenClaw-shaped
current-conversation `sessionBinding` record on the child session metadata,
including `bindingId`, `targetSessionKey`, `targetKind`, `conversation`,
`status`, `boundAt`, and `metadata.lastActivityAt` alongside the existing
delivery metadata. The production route-backed binder now also accepts LINE
notification routes and stores LINE current-conversation ids without the
provider/type prefix while preserving the original routable `to` target. The
native CLI can now create `--kind line` routes with default `gateway/send` and
`gateway/poll` subscriptions, so route-backed LINE current-conversation binders
are operator-configurable without direct database edits. The native web/API
operator surface now also classifies LINE as a first-class route channel with
the upstream `LINE` label and offers LINE in the notification-route form with
the same default gateway send/poll subscriptions. Matrix route-backed child
thread binders are now operator-configurable through the same surfaces:
`routes create --kind matrix`, `/api/gateway/channels`, and the web
notification-route form all classify Matrix as a native gateway send/poll
route. Native Zalo direct/media send routes are now operator-configurable
through matching `routes create --kind zalo`, channel inventory, and web
notification-route form surfaces, so the already-landed Zalo provider runtime
no longer needs manual route insertion for setup.
Route-backed `sessions.reset` and `sessions.delete` now also call the binder's
`unbind` hook with the saved `sessionBinding` / `threadBinding` record before
mutating or deleting metadata, and reset strips stale binding/completion fields
from the preserved session entry.
Matrix route-backed thread-bound subagent bindings now also persist
OpenClaw's bundled `placement="child"` default in the `sessionBinding`
metadata instead of treating Matrix as a current-conversation channel. Remaining
thread-binding parity is deeper provider-native child-thread creation and
provider-owned binding stores for ACP/session runtimes.
Reset/delete lifecycle now also emits the OpenClaw-shaped `subagent_ended`
event through a fakeable native lifecycle service after session mutation,
including `sendFarewell=true`, `targetKind`, and `outcome=reset/deleted`;
`sessions.delete emitLifecycleHooks=false` still skips only that hook while the
delete/unbind path proceeds.
Cross-agent thread-bound subagent spawns now also resolve the requester origin
through OpenClaw-style route `bindings`: when the target agent has a configured
route binding for the requester channel/peer, the binder context and initial
child run use the target agent's bound account instead of the caller's inbound
account.
Cross-agent ACP `sessions.spawn runtime="acp" thread=true` now uses the same
target-agent route-bound requester origin before thread-binding policy checks
and RuntimeManager dispatch, so account-scoped ACP spawn policy and ACP
requester context use the target agent account instead of the caller account.
ACP accepted results that include a prepared thread binding now persist
OpenClaw-shaped `threadBinding`, `sessionBinding targetKind="session"`,
`completionDelivery`, and bound delivery context metadata on the child session,
so downstream wait/reset/delete lifecycle paths can see the ACP session binding
record instead of only requester-origin metadata.
ACP thread-bound spawns with a channel context but no explicit account id now
mirror OpenClaw's `resolveAcpSpawnChannelAccountId`: the native gateway uses
`channels.<channel>.defaultAccount` when present and otherwise falls back to
`default` before account-scoped spawn policy checks and ACP runtime dispatch.
ACP Telegram `thread=true` current-conversation bindings now also preserve
forum-topic conversations whether the requester supplies a topic-qualified
`to` target or a group plus `threadId`; persisted `sessionBinding`
conversation ids use OpenClaw's `chatId:topic:threadId` shape without a
self-parent conversation record.
ACP `streamTo="parent"` spawns now also run a native parent-stream relay path:
the RuntimeManager-backed service resolves a child stream log path, registers a
provisional relay before dispatch, restarts the relay if the final Codex turn id
differs from the provisional run id, notifies the accepted relay, and returns
`streamLogPath` for gateway metadata persistence. App and CLI construction wire
the file-backed relay into the ACP spawn service.
Run-mode ACP spawns from canonical subagent requester sessions now also enable
parent streaming implicitly when heartbeat delivery is session-local
(`target="last"` with no explicit heartbeat route), the requester has a usable
current delivery route, no thread context, the spawn is not thread-bound, and
the gateway heartbeat runtime is enabled; `set-heartbeats enabled=false` now
suppresses implicit ACP parent streaming without changing explicit
`streamTo="parent"` requests.
Accepted ACP spawns now also register an OpenClaw-shaped running background task
record in durable child-session metadata: the record carries `runtime="acp"`,
`sourceId` / `runId`, owner/requester session keys, child session key, label,
task text, `status="running"`, `deliveryStatus`, and timestamps. The native
`tasks` CLI projection now reads those metadata-backed ACP records alongside
mission and blueprint tasks.
ACP terminal waits now also update those metadata-backed task records when a
tracked child run reaches a terminal mission snapshot: successful runs become
`status="succeeded"` with `terminalSummary`, `terminalOutcome="succeeded"`,
`endedAt`, `lastEventAt`, and session-queued delivery status; provider
completion delivery can subsequently mark the task delivery as `delivered` or
`failed`.
ACP in-flight runtime progress now also advances those metadata-backed task
records before terminal wait: app-server text delta events are matched by ACP
run id or runtime thread id, normalized into an appended `progressSummary`, and
bump `lastEventAt` while the record remains `status="running"`.
Gateway ACP spawns now also honor `acp.enabled=false` before any runtime
boundary, returning OpenClaw's `errorCode="acp_disabled"` disabled-policy
response without selecting a target agent or dispatching RuntimeManager work.
The ACP `mode="session"` / `thread=true` preflight is now enforced by the
gateway method owner itself, so fakeable or alternate ACP services cannot
receive a persistent ACP request that lacks a bound thread.
Remaining lifecycle parity is deeper provider-native binding record stores,
provider-native child-thread creation, and production ACP provider binding
creation breadth.

Current queue-head adjustment: provider-native direct `send` now preserves
OpenClaw runtime delivery fields (`messageThreadId`, `replyToId`,
`replyToMessageId`, `silent`, `forceDocument`, media, `audioAsVoice`, account,
and thread)
through gateway `send`, `OpsMeshService`, shared outbound runtime requests,
route-backed providers, and Telegram native document/reply/silent/thread
payloads. The provider runtime result envelope now also persists `messageId`,
`runtime`, `channel`, `roomId`, `timestamp`, and safe `meta` fields, Slack
route sends use `replyToId` as the thread fallback, Discord route sends preserve
reply and silent flags, and saved failed `gateway/send` / `gateway/poll` rows
replay through provider-native runtime calls with their original OpenClaw-style
delivery options. The CLI now exposes `routes send` and `routes poll` as thin
JSON/human wrappers over the same native direct send/poll runtime owner,
including reply/thread/media/silent/document/idempotency options, with
OpenClaw-compatible `--media` and `--thread-id` aliases alongside the native
`--media-url` / `--thread` spellings, plus poll aliases for
`--poll-question`, repeatable `--poll-option`, `--poll-multi`,
`--poll-duration-seconds`, `--poll-duration-hours`, and
`--poll-anonymous` / `--poll-public`. Direct
provider-backed `gateway.send` calls with an explicit `sessionKey` now
canonicalize and pass that key as the runtime/mirror session while keeping the
saved delivery row attached to the channel-derived target session for history
and replay. Provider-backed `gateway.send` calls from sandboxed source sessions
now normalize `/workspace/...` and `file:///workspace/...` media references
through the saved sandbox workspace root before dispatch, deduping equivalent
container/file-url forms while preserving remote media URLs. Remaining
provider work is deeper provider-specific edge cases not yet exposed by focused
tests and broader non-route CLI ergonomics.
Direct audio-as-voice media sends now also preserve OpenClaw's
`audioAsVoice` hint from gateway `send` through OpsMesh saved payloads,
`GatewayOutboundRuntimeMessageRequest`, route-backed provider event payloads,
provider-backed runtime delivery, and saved failed-send replay formatting.
Gateway `send` message bodies now also run the bounded OpenClaw outbound
payload directive normalization for `[[reply_to:...]]`, `[[reply_to_current]]`,
`[[audio_as_voice]]`, and line-start `MEDIA:` entries before channel delivery,
so directive markers do not leak as visible outbound text.
Telegram native poll route sends now also forward OpenClaw's multi-select
intent to Bot API payloads with `allows_multiple_answers`, preserving explicit
multi-select and default single-choice behavior alongside anonymous, duration,
silent, and topic-thread options.
Telegram poll delivery now also carries OpenClaw-style reply context through
gateway `poll`, the shared outbound runtime, direct route sends, replay, CLI
`routes poll --reply-to`, and native Bot API `reply_to_message_id` payloads.
WhatsApp Cloud API native route sends now also apply `replyToId` as Cloud API
`context.message_id` and switch URL media sends to `type="document"` /
`document.link` when `forceDocument=true`, while retaining saved delivery
payload and provider-result metadata. `gifPlayback=true` WhatsApp media sends
now use Cloud API `type="video"` / `video.link`, mirroring OpenClaw's
WhatsApp video/GIF outbound behavior while keeping the existing caption and
saved delivery metadata path.
Zalo native route-backed direct text sends now use OpenClaw's Bot API
`/bot{token}/sendMessage` shape and 2000-character split behavior, with native
provider result metadata persisted through the direct-send delivery path.
Zalo media sends now use the upstream `sendPhoto` path, preserve caption text
only on the first media item, iterate multiple media URLs, and persist
`mediaIds` / `mediaUrls`. Remaining Zalo provider parity is limited to deeper
provider-specific edge cases surfaced by future upstream contract checks.
Gateway `message.action` now has a fakeable native action dispatcher that
receives OpenClaw-shaped channel/action params, normalized routing metadata,
trusted-owner posture, tool context, and idempotency key, returning the
dispatcher payload instead of always reporting unsupported action. Remaining
route-backed Slack action parity now includes `react` add/remove dispatch via
Slack `reactions.add` / `reactions.remove` plus `reactions` listing via
`reactions.get full=true` and `edit` dispatch via Slack `chat.update` using
the saved native route token. Slack `delete` now dispatches through
`chat.delete` with the same route token and channel/message metadata path.
Slack `pin` now dispatches through `pins.add` with upstream-style
`messageId` -> `timestamp` mapping, and Slack `unpin` now dispatches through
`pins.remove` with the same route-token path. Slack `list-pins` now dispatches
through `pins.list` and returns provider-shaped pin items. Slack channel-history
`read` now dispatches through `conversations.history` with OpenClaw's
`limit`/`before`/`after` parameter mapping, while threaded reads dispatch
through `conversations.replies` and filter out the parent message. Slack
`member-info` now dispatches through `users.info` and returns the provider
info envelope. Slack `emoji-list` now dispatches through `emoji.list` and
applies OpenClaw's sorted local result limit. Slack `upload-file` now dispatches
through Slack's external upload flow with OpenClaw's `filePath` / `path` /
`media`, caption, filename/title, and thread aliases, including native local
path reads before the presigned upload. Slack `download-file` now dispatches
through fresh `files.info` metadata, rejects definite channel/thread scope
mismatches before media fetch, downloads private file URLs with the saved route
token, and returns saved local media path metadata.
Slack `send` now dispatches through the native Slack route as OpenClaw's generic
action entrypoint, including `threadId` / `replyTo` routing, blocks validation,
and the same external upload helper for media sends.
Empty-emoji `react` now also resolves the bot user through `auth.test`,
removes only the bot-owned reactions, and returns the removed names.
Telegram route-backed action parity now includes `react` add/remove/empty-clear
dispatch via Bot API `setMessageReaction`, including the upstream empty
reaction-array remove shape and soft missing-message-id result.
Discord route-backed action parity now includes `react` add dispatch via REST
own-reaction `PUT` using the saved bot token and OpenClaw-style encoded emoji
identifier, plus explicit `remove=true` through the matching own-reaction
`DELETE`. Empty-emoji `react` now also fetches message reactions, removes each
own reaction identifier, and returns the removed list. Discord `reactions` now
fetches message reaction summaries and per-reaction users with bounded limits,
so no smaller Discord reaction action seam remains in this queue. Discord
`send` now dispatches through the native webhook route owner with OpenClaw's
`to` / `message` / `replyTo` / `threadId` / `silent` and media path aliases.
Discord `edit` now dispatches through the route-backed bot-token REST path,
mapping `message` to the upstream `content` edit payload.
Discord `delete` now dispatches through the same route-backed bot-token REST
path and returns the upstream-shaped `{ok: true}` payload.
Discord `pin`, `unpin`, and `list-pins` now dispatch through the same
route-backed bot-token REST path, including upstream-shaped `{ok: true}` pin
mutations and normalized pinned-message timestamps for `list-pins`.
Discord `read` now dispatches through the same route-backed bot-token REST
path, including upstream-style `limit` integer parsing, 1-100 clamping,
`before` / `after` / `around` query params, and normalized message timestamps.
Discord `fetch-message` now dispatches through the same route-backed bot-token
REST path, including OpenClaw `messageLink` parsing, direct
`guildId`/`channelId`/`messageId` params, normalized timestamp metadata, and
the upstream-shaped `{ok: true, message, guildId, channelId, messageId}`
payload.
Discord `permissions` now dispatches through the same route-backed bot-token
REST path, fetching channel, bot identity, guild, and member records before
applying OpenClaw's guild/role/member overwrite order into a permission
summary.
Discord `thread-create` now dispatches through the same route-backed bot-token
REST path, including standalone channel-type lookup, non-forum public-thread
defaults, auto-archive duration mapping, and starter-message delivery into the
created thread.
Discord `sticker` now dispatches through the same route-backed bot-token REST
path, mapping upstream `stickerId` / `stickerIds` params into Discord
`sticker_ids` channel-message sends with optional message content.
Discord `poll` now dispatches through the same route-backed bot-token REST
path, mapping OpenClaw `to`, `content`, `question`, `answers`,
`allowMultiselect`, and `durationHours` params into a Discord poll message
body with `layout_type=1` and returning the upstream-shaped `{ok: true}`
payload.
Discord `set-presence` now follows OpenClaw's gateway-backed runtime shape
through a fakeable native adapter, including status/activity validation,
projected presence payloads, and the honest gateway-not-available error when
no Discord Gateway adapter is registered.
Discord guild-admin `member-info` now dispatches through the same route-backed
bot-token REST path and returns the upstream-shaped `{ok: true, member}`
payload.
Discord guild-admin `role-info` now dispatches through the same route-backed
bot-token REST path and returns the upstream-shaped `{ok: true, roles}`
payload.
Discord guild-admin `emoji-list` now dispatches through the same route-backed
bot-token REST path and returns the upstream-shaped `{ok: true, emojis}`
payload.
Discord guild-admin `channel-info` and `channel-list` now dispatch through the
same route-backed bot-token REST path and return the upstream-shaped channel
metadata payloads.
Discord guild-admin `role-add` and `role-remove` now dispatch through the same
route-backed bot-token REST path and return the upstream-shaped `{ok: true}`
payloads.
Discord guild-admin `channel-create` now dispatches through the same
route-backed bot-token REST path, mapping OpenClaw's channel creation fields
into the Discord channel body and returning `{ok: true, channel}`.
Discord guild-admin `channel-edit` now dispatches through the same
route-backed bot-token REST path, including OpenClaw's `clearParent` nulling
and channel/thread edit body mapping plus forum/media `availableTags`
projection to Discord `available_tags`.
Discord guild-admin `channel-delete` now dispatches through the same
route-backed bot-token REST path and returns the upstream-shaped
`{ok: true, channelId}` payload.
Discord guild-admin `channel-move` now dispatches through the same
route-backed bot-token REST path, including the OpenClaw one-item guild
channel positions body with parent clearing/assignment and integer position
coercion.
Discord guild-admin `channel-permission-set` and
`channel-permission-remove` now dispatch through the same route-backed
bot-token REST path, mapping role/member target types to Discord permission
overwrite types, preserving optional `allow`/`deny`, normalizing channel ids,
and returning the upstream-shaped `{ok: true}` payload.
Discord guild-admin `category-create` now dispatches through the same
route-backed bot-token REST path, creating a type `4` category and returning
the upstream-shaped `{ok: true, category}` payload.
Discord guild-admin `category-edit` now dispatches through the same
route-backed bot-token REST path, PATCHing optional name and integer position
fields onto the category channel and returning `{ok: true, category}`.
Discord guild-admin `category-delete` now dispatches through the same
route-backed bot-token REST path and returns the upstream-shaped
`{ok: true, channelId}` payload.
Discord guild-admin `voice-status` now dispatches through the same
route-backed bot-token REST path, reading guild voice-state metadata and
returning the upstream-shaped `{ok: true, voice}` payload.
Discord guild-admin `event-list` now dispatches through the same route-backed
bot-token REST path, reading guild scheduled events and returning the
upstream-shaped `{ok: true, events}` payload.
Discord guild-admin `event-create` now dispatches its scheduled-event payload
through the same route-backed bot-token REST path, including entity type,
timing, channel, description, location, privacy mapping, and OpenClaw-style
cover image URL/path/data-URI resolution with PNG/JPG/GIF validation.
Discord moderation `timeout` now dispatches explicit-until,
`durationMin`/`durationMinutes`, and encoded audit-log reason paths through the
same route-backed bot-token REST path and returns the upstream-shaped
`{ok: true, member}` payload.
Discord moderation `kick` now dispatches through the same route-backed
bot-token REST path, including encoded audit-log reason headers and the
upstream-shaped `{ok: true}` payload.
Discord moderation `ban` now dispatches through the same route-backed bot-token
REST path, including clamped `delete_message_days`, encoded audit-log reason
headers, and the upstream-shaped `{ok: true}` payload.
Discord `thread-list` now dispatches active guild and archived channel
thread-list paths through the same route-backed bot-token REST path, including
archived `before`/`limit` query parameters, and returns the upstream-shaped
`{ok: true, threads}` payload.
Discord `thread-reply` now dispatches through the same route-backed bot-token
REST path, including `message_reference` mapping, OpenClaw-style `mediaUrl`
uploads through Discord multipart `payload_json` + `files[0]`, and the
upstream-shaped `{ok: true, result}` payload.
Discord `search` now dispatches through the same route-backed bot-token REST
path, including content, repeated channel/author filters, clamped limit, and
the upstream-shaped `{ok: true, results}` payload.
Discord guild-admin `emoji-upload` now dispatches through the same
route-backed bot-token REST path, including data URL/local/canvas/HTTP media
loading, PNG/JPG/GIF validation, role filtering, and the upstream-shaped
`{ok: true, emoji}` payload.
Discord guild-admin `sticker-upload` now dispatches through the same
route-backed bot-token REST path, including data URL/local/canvas/HTTP media
loading, PNG/APNG/Lottie JSON validation, multipart sticker creation, and the
upstream-shaped `{ok: true, sticker}` payload.
WhatsApp route-backed action parity now includes `react` add/remove dispatch
via the native WhatsApp Cloud API messages endpoint, including direct JID
normalization to E.164 recipients, the upstream empty-emoji/remove shape, and
same-provider/same-chat `toolContext.currentMessageId` fallback with cross-chat
fallback rejection. Remaining action parity is other production provider action
adapters, `supportsAction` breadth, and deeper trusted-sender requirements for
provider-specific tool contexts.
Official Zalo route-backed action parity now includes upstream's supported
`send` action via the native Bot API route owner, including text and optional
`media` sends plus the public `kind="zalo"` route-create/view schema. Zalo
reactions remain intentionally unsupported because the upstream official Zalo
plugin advertises `reactions: false`. `channels capabilities` now also reports
Zalo's upstream support posture: direct/group chat types, media enabled, and
reactions/polls/threads disabled. Zalouser reaction parity remains a separate
future native user-session runtime seam.
Gateway `poll` now also mirrors OpenClaw's provider capability guard for
anonymous polls: `isAnonymous` is accepted only for Telegram, whose upstream
outbound adapter advertises anonymous-poll support, and non-Telegram channels
return `INVALID_REQUEST` before any runtime dispatch.
Telegram topic-qualified native polls now have the same focused proof as
topic-qualified sends: parent supergroup routes accept
`telegram:group:<chatId>:topic:<threadId>` targets, and the Bot API
`sendPoll` payload carries `message_thread_id`.
`channels.status --probe` now has the first production route-backed account
probe: enabled native Slack routes call Slack `auth.test` through the stored
route secret, while configured/no-account cases return an honest
`native_provider_route_unavailable` posture instead of a vacuous success.
Telegram native routes now probe Bot API `getMe` through the saved bot token
and return provider bot metadata through the same channel status account probe
envelope.
Discord native routes now probe Discord API `/users/@me` and
`/oauth2/applications/@me` with the saved bot token, returning bot identity and
privileged intent metadata through the same account probe envelope.
WhatsApp matches the upstream channel plugin's no-`probeAccount` posture: route
status reports an unsupported/no-hook probe envelope without degrading the
overall `channels.status --probe` result.

Current queue-head adjustment: the CLI now exposes top-level `sessions --json`
inventory plus `--agent` and positive `--active` filters as a thin wrapper over
the production `sessions.list` gateway method owner, and still exposes
`sessions spawn` / `sessions wait` as JSON/human wrappers over the production
`GatewayNodeMethodService` owner instead of duplicating runtime logic. The CLI
service builder wires the same native ACP spawn, sandbox-required child-turn,
route-backed thread binder, direct send/poll, config, model inventory, and
control-chat submit seams used by the app-server path. Gateway `sessions.patch`
and `sessions.delete` now reject non-control webchat clients with the upstream
`use chat.send for session-scoped updates` error before mutating session
storage. `sessions cleanup`
now accepts the upstream command shape and returns OpenClaw-shaped no-mutation
maintenance summaries from the native `sessions.list` owner for both dry-run
preview and enforce/apply no-op cases. `--fix-missing` now maps OpenClaw's
missing transcript-file pruning onto OpenZues' SQLite-backed session metadata
by deleting only agent-filtered metadata rows whose control-chat transcript has
no messages. `sessions cleanup` dry-run now also previews OpenClaw-shaped stale
`updatedAt` pruning and `session.maintenance.maxEntries` count caps from the
native `sessions.list` rows, and `--enforce` deletes those stale/capped native
metadata rows. Native disk-budget maintenance now mirrors OpenClaw's
post-prune budget envelope over SQLite metadata rows: configured
`maxDiskBytes` / `highWaterBytes` preview oldest non-active evictions, protect
`--active-key`, return `diskBudget` result metadata, and delete evicted rows
under `--enforce`. `sessions cleanup --all-agents --json` now returns
OpenClaw-shaped grouped `stores` summaries by native session-key agent while
retaining the single SQLite-backed physical store. No smaller native
`sessions cleanup` seam remains; any deeper cleanup work would require a
future first-class multi-store transcript owner beyond OpenZues' current
session store. The CLI now also exposes read-only `tasks`, `tasks list`, and
`tasks show` inspection over native OpenZues mission and task-blueprint state,
returning OpenClaw-shaped task records with `runtime`, `status`, `taskId`,
session/run lookup, delivery, notify, timestamp, progress, and terminal summary
fields. `tasks audit` now applies OpenClaw-shaped stale-running, stale-queued,
lost, delivery-failed, missing-cleanup, and timestamp-consistency checks to
those native records with the upstream JSON filter/summary envelope and an
explicit empty TaskFlow audit summary. `tasks maintenance` now returns the
upstream preview/apply envelope with native task summary, audit-before/after,
cleanup-stamp accounting, and explicit zero TaskFlow maintenance. `tasks flow
list/show` now projects saved task blueprints as `task_mirrored` TaskFlows,
links mission task records through `parentFlowId`, and returns upstream-shaped
linked tasks plus task summaries. `tasks cancel` now resolves task id, run id,
or session key lookups against native task records and pauses active
mission-backed tasks through `MissionService.pause()`, preserving the upstream
not-found/could-not-cancel boundary for unsupported records. `tasks notify`
now persists `taskNotifyPolicy` in gateway session metadata and the task
read-model projects the saved policy through later list/show output. `tasks
flow cancel` now disables the native task blueprint, stamps an OpenClaw-shaped
cancelled result, and pauses active linked mission tasks while preserving the
upstream not-found/could-not-cancel boundary. No smaller source-backed `tasks`
CLI command remains in the current native projection; deeper parity would be a
richer native TaskFlow mutation registry if OpenZues grows a first-class flow
owner.
Top-level
`status --json` now accepts OpenClaw's `--all`, `--usage`, `--deep`, and
`--timeout` / `--timeout-ms` breadth flags, forwards the timeout into the
native live health probe for `--deep`, and projects honest unavailable JSON
sections for provider usage and security-audit runtime adapters that do not
yet exist. Plain `status --json` now also includes OpenClaw-shaped
`gatewayService` and `nodeService` summaries with truthful native OpenZues
unmanaged status instead of omitting the managed-service read model. Text-mode
`status --all` now renders the OpenClaw-shaped
pasteable report skeleton with overview, channel, agent, and read-only
diagnosis sections backed by the same native status payload. Remaining
CLI/runtime parity includes ACP/sandbox status commands, deeper model
auth/probe inspection, production provider usage/security-audit adapter wiring,
plugin/runtime inspection, deeper runtime bridge doctor checks, non-metadata
external sandbox container cleanup, and broader TUI ergonomics.
`status --json --usage
--all` now consumes fakeable native provider-usage and security-audit runtime
adapters when registered while keeping the honest unavailable placeholders
when they are absent. The existing
`sandbox list` human output now also mirrors OpenClaw's total/running summary
line and config-mismatch recreate hint after listing native saved sandbox
runtimes. Top-level `doctor --json` / human output now also mirrors OpenClaw's
Sandbox doctor preflight for `agents.defaults.sandbox.mode`: when mode is
`non-main` or `all`, the effective backend defaults to Docker, and `docker
version` is unavailable, the Hermes doctor payload carries the same actionable
Sandbox warning text while preserving the existing warning surface. The
top-level human/JSON doctor view now also reports OpenClaw-style session lock
health for saved `agents/*/sessions/*.jsonl.lock` files, including pid
liveness, age, stale posture, and read-only guidance without removing files.
The same state-integrity doctor surface now reports a structured
`stateDirectory` payload and CRITICAL warning when the configured OpenZues data
directory is missing, mirroring OpenClaw's missing-state-directory doctor
warning.
Top-level doctor output now also includes OpenClaw's `doctor:legacy-cron`
contribution for configured file-backed cron stores: it reports legacy
`jobId`, `schedule.cron`, top-level payload/delivery, and `notify` fallback
issues, and `doctor --fix` rewrites the store before the scheduler has to
consume old shapes.
Top-level doctor output now also includes the upstream `doctor:security` and
`doctor:shell-completion` contribution surfaces as stable native read models.
`doctor:security` now covers OpenClaw's
`approvals.exec.enabled=false` forwarding-only warning and fails soft when
legacy config must be reported by earlier migrators first. It also covers the
implicit heartbeat direct-policy upgrade warning for configured default and
per-agent heartbeat delivery whose `directPolicy` is unset, plus canonical
non-loopback gateway bind exposure without configured auth while leaving raw
legacy bind aliases under the legacy-config migrator. It now also compares
global and per-agent `tools.exec` policy against the native
`settings/exec-approvals.json` host policy and emits the OpenClaw-shaped
config/host/effective-policy warning when the requested policy is broader or
less prompt-heavy than the host permits. Configured channel DM security now
also mirrors OpenClaw's OPEN, invalid-open-allowFrom, locked allowlist/pairing,
disabled, and shared-main-session warnings using native config snapshots and
the existing pairing allowFrom store. `doctor:shell-completion` now reports
native shell/profile/cache/slow-pattern status and `doctor --fix` regenerates a
missing cache and replaces slow dynamic profile stanzas with a cached source
line. First-time `doctor --fix` installation for profiles with no existing
completion is also wired through the same native cache/profile path.
Top-level doctor output now also includes OpenClaw's `doctor:oauth-tls`
contribution for configured Codex OAuth profiles: the native preflight probes
the OpenAI auth endpoint through a fakeable boundary, classifies TLS
certificate trust failures, and reports the upstream CA-certificate remediation
guidance without importing the TypeScript runtime.
Top-level doctor output now also includes OpenClaw's `doctor:hooks-model`
contribution for configured Gmail hook model overrides: it resolves aliases and
model refs from native config, warns for `agents.defaults.models` allowlist
drift, and warns when the hook model is missing from the configured model
catalog.
Top-level doctor output now also includes OpenClaw's `doctor:bootstrap-size`
contribution for configured workspaces: it scans `AGENTS.md` against native
bootstrap character budgets and reports truncation/near-limit guidance without
mutating workspace files.
Top-level doctor output now includes the first OpenClaw
`doctor:workspace-status` native read model: manifest-backed plugin registry
records are summarized into loaded/imported/disabled/error/bundle counts, with
skill and TaskFlow recovery hints left as follow-on workspace-status seams.
Top-level doctor output now includes the first OpenClaw
`doctor:device-pairing` gateway-backed warning: pending requests returned by
`device.pair.list` are surfaced with sanitized device labels, request counts,
and the upstream review/approve command guidance. The same contribution now
classifies paired-device repair, role-upgrade, scope-upgrade, missing-token,
operator-baseline, and token-scope drift states from the gateway snapshot while
quoting untrusted device/role command arguments. CLI service construction now
wires the same native pairing runtime as the app server, so real CLI doctor
runs can read local `device.pair.list` state. The contribution now also reads
OpenClaw-shaped local `identity/device.json` / `identity/device-auth.json`
cache files from the native data directory and warns for stale cached tokens,
missing gateway-token matches, and cached-scope drift. Remaining device doctor
work is limited to deeper repair automation if OpenZues adopts a first-class
local device-auth cache writer.
The top-level `acp` and `acp client` command surfaces now accept the
upstream option shape and return precise native-unavailable bridge errors that
point users to the supported `sessions spawn --runtime acp` path; remaining
ACP CLI parity is the real bridge server/client runtime. The unavailable
boundary now validates provenance modes, rejects mixed inline/file secret
sources, validates secret-file readability, and warns when inline token or
password flags are used.
`acp client` now also builds an OpenClaw-shaped native spawn plan before that
unavailable boundary: default OpenZues ACP server launches use `openzues acp`,
set `OPENCLAW_SHELL=acp-client`, strip provider auth and active-skill env keys
case-insensitively, and preserve provider auth when callers choose an explicit
custom ACP server. The spawn preflight now also mirrors OpenClaw's Windows-safe
ACP client invocation resolver by unwrapping `.cmd` shims to the Python
executable without shell execution. Remaining ACP CLI parity is still the real
bridge client/server protocol runtime rather than the spawn preflight contract.
The CLI now also exposes `models list` as a thin OpenClaw-shaped JSON/human
wrapper over the production `models.list` gateway method owner, including
provider/local filters without duplicating the model catalog runtime, and
`models status` projects the same catalog into OpenClaw-style
default/resolved/allowed/auth status fields. `models aliases list` now reads
OpenClaw-shaped `agents.defaults.models[*].alias` config from the native
OpenZues config projection, falls back to model-catalog alias metadata when
available, and supports the upstream JSON/plain/human output shapes. `models
aliases add` now normalizes aliases, defaults unqualified model ids to the
OpenAI provider, rejects duplicates pointing elsewhere, and writes the alias
through `GatewayConfigService` into `agents.defaults.models`. `models aliases
remove` now clears the alias field from the matched configured model, preserves
the model entry, reports the upstream empty-alias message when none remain, and
returns the upstream not-found error for missing aliases. No smaller model alias
CLI command remains. `models fallbacks list` now projects
`agents.defaults.model.fallbacks` from the native config snapshot and supports
the upstream JSON/plain/human output shapes. `models fallbacks add` now resolves
model aliases to canonical provider/model keys, upserts the configured model
entry, appends only missing fallback targets, and writes through
`GatewayConfigService`. `models fallbacks remove` now resolves model aliases,
removes matching canonical fallback targets, preserves the remaining order, and
returns the upstream not-found error for missing fallback targets. `models
fallbacks clear` now empties the configured text fallback list while preserving
the existing primary model config. No smaller text fallback CLI command remains;
`models image-fallbacks list` now projects
`agents.defaults.imageModel.fallbacks` from the native config snapshot and
supports the upstream JSON/plain/human output shapes. `models image-fallbacks
add` now appends canonical image fallback model ids, defaults unqualified ids to
OpenAI, and upserts the configured model entry. `models image-fallbacks remove`
now resolves aliases, removes matching canonical image fallback targets, keeps
remaining order intact, and returns the upstream not-found error for missing
image fallback targets. `models image-fallbacks clear` now empties the
configured image fallback list while preserving the existing primary image model
config. No smaller image fallback CLI command remains. `models auth order get`
now reads the per-agent native `auth-state.json` order override with
OpenClaw-style provider normalization and JSON/human output. `models auth order
set` now validates requested profile ids against the target agent's
`auth-profiles.json`, rejects provider mismatches with OpenClaw-shaped errors,
dedupes the requested order, and writes the per-agent `auth-state.json` order
override. `models auth order clear` now removes the selected provider order
override while preserving neighboring auth-state metadata. No smaller auth-order
CLI command remains; the next model CLI queue head is the provider auth command
cluster. `models auth login` now forwards `--provider`, `--method`, and
`--set-default` through the native fakeable model-auth runtime, preserving the
existing precise unavailable boundary when that runtime is not wired. `models
auth login-github-copilot` now maps to the native model-auth runtime with
`provider="github-copilot"`, `method="device"`, and `--yes`. `models auth
setup-token` now forwards `--provider` and `--yes` through the native fakeable
model-auth runtime while preserving the same unavailable boundary when no
setup-token owner is wired. `models auth paste-token` now forwards `--provider`,
`--profile-id`, and `--expires-in` through the same runtime boundary. The
remaining provider-auth CLI head is `models auth add`. `models auth add` now
forwards to the native fakeable model-auth runtime's interactive add helper, so
no smaller provider-auth CLI command remains. `models set` now resolves aliases
and provider aliases, rewrites `agents.defaults.model.primary` into the
OpenClaw object form, preserves fallback metadata, upserts the canonical model
entry, migrates the duplicated OpenRouter legacy key, and reports the resolved
default model. The remaining root model mutation queue head is
`models set-image`, then non-interactive `models scan` posture. `models
set-image` now resolves aliases and provider aliases through the same native
model config writer, rewrites `agents.defaults.imageModel.primary` into the
OpenClaw object form, preserves image fallback metadata, upserts the canonical
model entry, and reports the resolved image model. No smaller root model
mutation command remains; the next model CLI queue head is non-interactive
`models scan` posture. `models scan` now exposes upstream-shaped
`--min-params`, `--max-age-days`, `--provider`, `--max-candidates`,
`--timeout`, `--concurrency`, `--no-probe`, `--yes`, `--no-input`,
`--set-default`, `--set-image`, and `--json` options; `--no-probe --json`
returns fakeable/native OpenRouter free-model metadata without credentials, and
`--yes` applies preselected text/image fallbacks plus default/image-model
updates through the native config writer without prompting. The remaining scan
depth was live OpenRouter tool/image probing parity beyond the metadata/runtime
posture; `models scan` now performs native OpenRouter chat-completions tool
probes with a required `ping` tool and image probes with a small data-URL image
for image-capable candidates, preserving the upstream missing-key guard and
fakeable HTTP transport coverage. No smaller model-scan CLI/probe seam remains.
`models status --probe` now falls back to the native `models.authStatus`
gateway owner when no explicit model-auth runtime is injected, adapting provider
profile health into the existing auth JSON/check shape and preserving the
explicit fakeable `model_auth.status` runtime precedence. No smaller live auth
status/probe fallback seam remains in the model CLI cluster.
Top-level `health`
now queries the live gateway `/api/health` and `/readyz` owners, emits
OpenClaw-shaped JSON/human readiness fields, and propagates the configured
connection timeout. `channels status --probe --timeout <ms> --json` now
accepts the upstream options and preserves probe/timeout metadata with an
honest unavailable provider-probe posture. The CLI now routes status probes
through the `channels.status` gateway method owner, and the channel inventory
service has a fakeable account-probe adapter that records per-account probe
results when one is registered; remaining channel CLI parity is provider-specific
credential probe implementations and production provider-backed live resolve
adapters.
`channels capabilities --channel/--account/--target --timeout
--json` now returns a native OpenClaw-shaped capability report over
route-backed channel metadata, including support/actions and the same account
probe result used by `channels.status` when one is available, otherwise an
honest unavailable probe envelope. `channels resolve` now accepts upstream-shaped
entries/channel/account/kind/JSON options, resolves saved route-backed
conversation targets first, and falls through to a fakeable live target
resolver for provider adapters before returning OpenClaw-shaped unresolved
rows. `channels logs` now reads the native workspace log tail, parses
OpenClaw-shaped structured log lines, filters by channel, applies the upstream
limit-after-filtering rule, and emits JSON/human output.
Slack native routes now provide the first production live target resolver slice:
channel/group resolution calls Slack `conversations.list` through the stored
route token and matches channel ids, mentions, and names. Slack user resolution
now also calls Slack `users.list` through the same native route token and
matches user ids, mentions, names, display/real names, and email addresses.
`channels resolve` now mirrors OpenClaw's auto-kind batching for live resolver
entries so user-looking inputs are sent to user resolution and group-looking
inputs are sent to group/channel resolution while preserving output order.
Telegram native routes now support the upstream username resolver slice:
`channels resolve --channel telegram --kind user` calls Bot API `getChat` with
the stored route token and returns the numeric chat id plus normalized
`@username` display.
The CLI now exposes OpenClaw's metadata-only `infer` / `capability` command
alias for `list` and `inspect --name`, returning canonical capability ids,
descriptions, transports, flags, and result shapes from
`src/cli/capability-cli.ts`. The nested `infer model` / `capability model`
catalog commands now also cover `run`, `list`, `inspect --model`, `providers`,
and `auth status`, using the native control-chat, `agent`, `models.list`, and
model-status gateway method owners while preserving OpenClaw's model-run
capability envelope, raw catalog-array, provider-summary, and model-auth status
JSON shapes. The gateway `agent` method now accepts model-only and
provider/model `model run` overrides and persists them through the native
session metadata path before dispatch; gateway model runs now wait for the
final `agent.wait` result before projecting OpenClaw-style provider/model
output envelopes. Model auth login/logout CLI commands now dispatch through a
fakeable native model-auth runtime hook and keep a precise unavailable boundary
when that runtime is absent. `models status --probe` now also consumes a
fakeable native model-auth status/probe runtime when one is registered, while
keeping the honest unavailable probe posture when it is absent. `models status
--check` now mirrors OpenClaw's non-zero exit behavior for known auth failures
or expired/missing OAuth profiles. Remaining `infer` parity is production
model-auth backend wiring, deeper TTS provider/runtime breadth beyond the
now-landed CLI family, and any
gateway-backed capability transports not already covered by native OpenZues
command families. The first TTS slices now project the native
`tts.providers`, `tts.status`, `tts.enable`, `tts.disable`, and
`tts.setProvider` method owners plus the native `tts.convert` runtime into
OpenClaw-shaped provider objects, gateway-tagged status JSON, raw
state-mutation payloads, provider voice lists, and `tts.convert` capability
envelopes for the `infer` / `capability` alias family. `image providers` now
projects a fakeable native image-generation registry into OpenClaw's provider
summary shape and returns an empty list when no provider registry is wired;
`image describe` now wraps a fakeable native media-understanding runtime in
OpenClaw's normalized image-description envelope, and `image describe-many`
now repeats that envelope output for each requested image file. `image generate`
now wraps a fakeable native image-generation runtime in OpenClaw's saved-output
envelope, and `image edit` reuses that runtime with repeated input files.
`audio providers` now filters the fakeable native media-understanding registry
to audio-capable providers and preserves OpenClaw's provider summary shape.
`audio transcribe` now wraps the same fakeable native media-understanding
runtime with language/prompt/model hints and returns OpenClaw's
`audio.transcription` envelope.
`video providers` now exposes the registered `infer` / `capability video`
group and projects fakeable native generation plus media-understanding provider
registries into OpenClaw's generation/description provider shape.
`video describe` now wraps the fakeable native media-understanding runtime in
OpenClaw's `video.description` envelope with provider/model attribution.
`video generate` now wraps the fakeable native video-generation runtime in
OpenClaw's saved video output envelope with provider/model attempts.
`web providers` now exposes the registered `infer` / `capability web` group
and projects fakeable native search/fetch provider registries into OpenClaw's
provider summary shape.
`web search` now wraps the fakeable native web runtime in OpenClaw's
single-result local envelope with provider attribution.
`web fetch` now wraps the fakeable native web runtime in the same OpenClaw
single-result local envelope while preserving provider and format hints.
`embedding providers` now exposes the registered `infer` / `capability
embedding` group and projects the fakeable native embedding registry into
OpenClaw's provider summary shape.
`embedding create` now wraps the fakeable native embedding runtime in OpenClaw's
provider/model/attempts envelope and maps repeated `--text` values to vector
outputs with dimensions.
Discord native routes now have the first production live resolver slice:
channel-id inputs and channel mentions call `/users/@me/guilds` plus
`/channels/{id}` with the stored route token and return OpenClaw-shaped
channel id/name rows. Guild-qualified Discord channel names now also call
`/guilds/{guildId}/channels` and match OpenClaw-style normalized channel
slugs. Global `#channel` inputs now search all bot guilds, prefer active
non-thread channels, and report the upstream multiple-match note.
Discord user resolution now searches guild members with the saved route token
for guild-qualified names and preserves the OpenClaw-shaped id/name/note
projection.
Telegram native sends now parse topic-qualified targets like
`telegram:group:<chatId>:topic:<threadId>` into a base `chat_id` plus
`message_thread_id` instead of treating the full target as the chat id.
Telegram parent supergroup routes now also match topic-qualified sends for the
same chat id, while topic-specific routes remain specific to their thread id.
WhatsApp native route sends now match OpenClaw's direct text/media outbound
chunking contract for text-only long sends by splitting bodies into 4000
character messages and returning the last provider message id instead of
truncating the payload.
WhatsApp native media sends now also preserve OpenClaw's leading-caption
contract: provider-visible image/document/video captions contain only the
original outbound text, while generated media URL/settings summaries remain
delivery metadata instead of being appended to captions.
Gateway poll requests now mirror OpenClaw's provider capability guard for
`durationSeconds`: Telegram can still opt into second-granularity polls, while
Slack/Discord/WhatsApp reject `durationSeconds` before runtime dispatch and
continue using `durationHours` where applicable.
Telegram gateway poll validation now also matches the upstream Telegram adapter
duration contract by accepting only `durationSeconds` in the 5-600 range and
rejecting `durationHours` with the OpenClaw-shaped guidance message.
The same Telegram duration contract is now enforced in the OpsMesh
route-backed provider path so direct CLI/runtime sends and replays cannot
bypass the gateway-method validation before posting `sendPoll`.
Gateway poll option validation now follows OpenClaw's provider caps for
Telegram and Discord by rejecting more than 10 options while keeping WhatsApp's
12-option path available.

Current queue-head adjustment: `tools.invoke` plugin execution now routes
through a fakeable `GatewayPluginRuntimeService`, preserving core mappings
first, config allow/deny gating, owner-only hiding, before-call hooks, and
OpenClaw-shaped plugin executor error projection. The service now also accepts
ordered registry/config executor specs, preserves first registered plugin-name
winner semantics among enabled entries, skips later duplicates, keeps core mappings ahead of
registry-backed plugins, and applies owner-only visibility to registry tools.
`tools.catalog` now also appends OpenClaw-shaped `plugin:<pluginId>` groups
from the same enabled plugin runtime specs by default, suppresses core-name
collisions, and honors `includePlugins=false` for core-only catalog reads.
`tools.effective` now projects the same runtime specs as upstream-style
`source="plugin"` entries under the `Connected tools` group while filtering
empty groups from plugin-only sessions. Optional plugin runtime executors now
preserve OpenClaw's `optional` tool metadata and can be enabled by exact tool
name, plugin id, or `group:plugins` allowlist entries before dispatching
through `tools.invoke`. Registry/config executor specs now also preserve
OpenClaw-style `parameters` / schema metadata so `/tools/invoke` merges a
top-level `action` into plugin args only when the declared schema exposes an
`action` property; explicit `args.action` remains authoritative and non-action
schemas stay untouched before before-call hooks and executor dispatch. Remaining
tool parity is future
production runtime activation/import metadata beyond the native manifest
snapshot adapter and deeper marketplace install/update/uninstall flows.

Current queue-head adjustment: the CLI now exposes `plugins list` with
OpenClaw-shaped JSON (`workspaceDir`, `plugins`, `diagnostics`) and human
output projected from the existing Hermes/OpenZues plugin inventory deck. The
surface supports `--enabled`, `--verbose`, and `--json`, maps ready/partial
inventory to loaded plugins, keeps source-only Hermes families disabled, and
does not introduce a second plugin scanner. `plugins doctor` now reports plugin
load errors from the same projection and preserves OpenClaw's
`No plugin issues detected.` clean snapshot behavior. `plugins inspect` and
its `plugins info` alias now return OpenClaw-shaped JSON reports with
`plugin`, `shape`, `capabilityMode`, capability kinds, diagnostics, policy, and
install metadata projected from the same inventory, and `inspect --all` returns
all records with top-level saved install metadata when present. Runtime-backed
`plugins inspect` tool reports now preserve OpenClaw's registered-tool
`optional` metadata instead of collapsing native executor tools into a single
required group. `plugins enable`
/ `plugins disable` now write through the
existing gateway config owner with OpenClaw-shaped
`plugins.entries.<id>.enabled` persistence, preserve existing entry config,
append configured allowlists on enable, and mirror built-in channel plugin
toggles into `channels.<id>.enabled` for channel-backed providers. Remaining
plugin CLI parity is remote marketplace clone/update breadth and deeper
production plugin manifest/runtime metadata discovery. `plugins marketplace list` now
supports local Claude-compatible marketplace manifests from
`.claude-plugin/marketplace.json` or `marketplace.json`, returning the
OpenClaw-shaped `source`, `name`, `version`, and `plugins` JSON payload while
leaving remote clone semantics to the heavier packaging/install queue.
`plugins install <name> --marketplace <local>` now resolves local manifest
entries, rejects escaping/missing plugin sources, persists an OpenClaw-shaped
`plugins.installs.<id>` marketplace record, enables the plugin, appends the
native load path, and returns JSON/human restart posture without importing the
TypeScript runtime. `plugins uninstall` now removes native plugin config
entries, install records, allowlist entries, load paths, memory slot ownership,
and owned channel config while keeping local marketplace source directories
intact and reporting OpenClaw-shaped action metadata. `plugins update` now
supports local marketplace install records, including `--dry-run`, `--all`,
skipped/error/updated/unchanged outcomes, manifest version refresh, and
restart posture without writing during dry-run. `plugins doctor` now reports
OpenClaw-shaped compatibility notices for legacy `before_agent_start` and
hook-only plugin inventory signals. `plugins list` now also merges saved
OpenClaw-shaped `plugins.entries` / `plugins.installs` records from the native
gateway config owner, so config-installed marketplace plugins are visible even
when the live platform deck has not loaded them yet; `plugins inspect --all --json`
now preserves those saved install records in the report-level `install` field.
`plugins list --json` now also performs OpenClaw-style metadata-only discovery
for configured `plugins.load.paths` entries that contain `openclaw.plugin.json`,
preserving manifest `id`, `name`, `description`, `version`, contracts, tool
names, manifest/root paths, and enabled/default status without importing plugin
code. `plugins inspect --json` now also consults the native
`GatewayPluginRuntimeService.catalog_specs()` registry when present: matching
runtime executor specs mark discovered plugins as imported, switch the inspect
report from inventory-only to `capabilityMode="runtime"`, and project
OpenClaw-shaped runtime tool entries with `names` / `optional` metadata.
Inspect reports now also project OpenClaw-shaped policy summaries from
`plugins.entries.<id>.hooks.allowPromptInjection` and
`plugins.entries.<id>.subagent` (`allowModelOverride`, `allowedModels`, and
`hasAllowedModelsConfig`) instead of always returning an empty policy object.
`plugins inspect --json` now also preserves OpenClaw's plugin-record runtime
surface fields: `commands`, `cliCommands`, `services`, `gatewayMethods`,
`httpRouteCount`, and `bundleCapabilities` are copied from live inventory or
metadata-only manifest records instead of being zeroed in the report.
Remaining plugin CLI parity is remote marketplace clone/update breadth and
deeper runtime activation/import metadata beyond the native metadata/runtime
projection.

Current queue-head adjustment: `sessions.spawn` now preserves and applies
OpenClaw's `gateway.agents.defaults.subagents.runTimeoutSeconds` config default
when callers omit explicit `runTimeoutSeconds` / legacy `timeoutSeconds`.
Remaining spawn work should stay on ACP harness execution, sandboxed target
runtimes, thread-binding lifecycle hooks, and completion/cleanup orchestration.

Current queue-head adjustment: `sessions.spawn` now also preserves
`expectsCompletionMessage` on spawned-session metadata, matching OpenClaw's
subagent run-registry intent at the durable state boundary. Remaining work is
to consume that flag in the future lifecycle/cleanup owner rather than drop it
at spawn time.

Current queue-head adjustment: `sessions.spawn lightContext=true` now reaches
the child run dispatcher as `bootstrap_context_mode="lightweight"` /
`bootstrap_context_run_kind="default"` and persists `bootstrapContextMode` on
the spawned session. Remaining work is to make the deeper subagent lifecycle
owner consume the metadata the same way OpenClaw's child runtime does.

Current queue-head adjustment: `sessions.spawn` now wraps spawned child runs in
the OpenClaw-shaped `[Subagent Context]` / `[Subagent Task]` bootstrap envelope
instead of sending raw task text directly. Remaining spawn gaps are now deeper:
ACP harness execution, thread-bound session spawns, sandboxed target runtimes,
and lifecycle cleanup/announce handling.

Current queue-head adjustment: `sessions.spawn` now persists lifecycle policy
metadata (`spawnMode`, `cleanup`, and resolved `runTimeoutSeconds`) on child
sessions. Remaining work is the lifecycle owner that consumes those fields for
completion announcements and cleanup.

Current queue-head adjustment: omitted `sessions.spawn` run timeout now
resolves to OpenClaw's explicit no-timeout sentinel (`0`) and persists that
resolved value on child metadata.

Current queue-head adjustment: terminal `agent.wait` now consumes local
spawned-session lifecycle metadata for `cleanup: "delete"` and default
completion announcements. It deletes ephemeral child transcript/metadata when
requested, appends a parent-visible completion message unless
`expectsCompletionMessage=false`, and records `completionAnnouncedRunId` /
`completionAnnouncedAtMs` so recovered observations of the same terminal run do
not duplicate the parent message.

Current queue-head adjustment: `agent.wait` now ignores terminal session
fallback missions whose end timestamp is older than the tracked run start time,
preventing stale completed mission state in a reused session from falsely
completing a newer tracked run.

Current queue-head adjustment: explicit `agent.wait timeoutMs=0` now preserves
OpenClaw-style no-wait polling semantics instead of widening to the local
30-second default; omitted `timeoutMs` still uses the default wait.

Current queue-head adjustment: `agent.wait` now prefers exact mission
`swarm.run_id` matches before falling back to the latest mission in the tracked
session, so unrelated active session work cannot hide a terminal mission for
the requested run id.

Current queue-head adjustment: `agent.wait` now rebuilds recovered exact-run
tracking through the normal session alias map, so terminal waits discovered
from durable `swarm.run_id` metadata are forgotten after the snapshot is
consumed instead of leaking synthesized run ids in memory.

Current queue-head adjustment: historical exact `agent.wait` calls no longer
evict a different current run tracked for the same session; exact-run recovery
only takes session tracker ownership when no other run is active there.

Current queue-head adjustment: `sessions.spawn` active-child-cap pruning now
observes terminal tracked child runs without consuming the `agent.wait`
lifecycle path. Finished children no longer emit parent completion messages or
run cleanup merely because a requester attempts another spawn; the later
`agent.wait` call still consumes the terminal snapshot and lifecycle metadata.

Current queue-head adjustment: tracked `agent.wait` session fallback now asks
for the latest terminal mission in that session, rather than reusing the
status-card lookup that prefers active rows. A stale active mission can no
longer hide a completed or failed mission for the tracked run.

Current queue-head adjustment: tracked `agent.wait` thread-child fallback now
uses the same terminal-only posture for child missions under the tracked parent
session. Stale active thread-child rows can no longer mask a completed or
failed child mission when the tracked run is waiting for terminal state.

Current queue-head adjustment: exact `agent.wait` run-id lookup now prefers
terminal `swarm.run_id` mission rows before falling back to the active-aware
durable run lookup. Duplicate stale active rows for the same run id can no
longer hide completed or failed exact-run terminal state.

Current queue-head adjustment: tracked `agent.wait` fallback now drops stale
terminal candidates before continuing to the next lookup source. An old exact
terminal row can no longer stop the wait from finding a fresher terminal
session or child mission for the tracked run.

Current queue-head adjustment: after dropping a stale exact terminal candidate,
tracked `agent.wait` now re-checks the active-aware exact run-id lookup before
falling through to session fallback. A currently active exact run can no longer
be completed by an unrelated session terminal row.

Current queue-head adjustment: OpenZues now advertises an explicit
`sessions_history` tool posture and exposes `sessions.history` as an
agent-tool-style gateway read: it resolves session aliases, hides tool rows by
default, allows `includeTools`, redacts secrets, strips usage/cost metadata, and
applies the OpenClaw-inspired 4k text cap plus 80 KiB response budget. The next
bounded seam should either wire this through a native agent-tool executor or
continue to the next source-backed `chat.*` / `sessions.*` runtime mismatch.

Current queue-head adjustment: OpenZues now also advertises `session_status`
and exposes `session.status` as a bounded status-card gateway read. It returns
OpenClaw-style `content` plus `details`, resolves session aliases through the
session snapshot owner, and can apply the same provider/model override metadata
used by `sessions.patch`. The next bounded seam should stay with neighboring
agent session tools (`sessions_send`, `sessions_list`, `sessions_spawn`, or
native executor wiring) rather than broad product inventory.

Current queue-head adjustment: `sessions.send` now accepts OpenClaw-style
label targeting, with optional `agentId`, and rejects ambiguous key+label calls
before runtime dispatch. The gateway API path resolves the label through the
existing session inventory and sends to the canonical session key. The next
neighboring seam should inspect `sessions_list`, `sessions_spawn`, or native
agent-tool executor wiring.

Current queue-head adjustment: `sessions_list` is now an explicit tool posture,
and `sessions.list` accepts OpenClaw-style `kinds` plus `messageLimit`.
Snapshots can filter `main`/`other` aliases without breaking existing
OpenZues `global`/`thread` kinds, and can attach bounded non-tool recent
message context. The next neighboring seam should inspect `sessions_spawn`,
native agent-tool executor wiring, or another concrete upstream session-tool
mismatch.

Current queue-head adjustment: `sessions_spawn` is now an explicit tool
posture, and `sessions.spawn` can create a bounded subagent-style child session
from a task. It stores spawn ownership/depth metadata, sends the initial task
with optional thinking and timeout, rejects channel-delivery params, and
returns an OpenClaw-style accepted payload. Remaining spawn parity includes ACP
harness spawning, attachment materialization, sandbox/depth guardrails, and
lifecycle hook cleanup.

Current queue-head adjustment: `agents_list` is now an explicit tool posture,
and `agents.list toolProjection=sessions_spawn` returns an OpenClaw-style
`requester`, `allowAny`, and bounded `agents` list for spawn targeting while
preserving the existing broad OpenZues agent inventory by default. Remaining
agent-target parity is the richer OpenClaw subagent allowlist config model.

Current queue-head adjustment: `sessions.spawn` now materializes inline
subagent attachments into `.openclaw/attachments/<id>` under the target
workspace, writes a manifest, returns a receipt, persists the receipt in session
metadata, and appends an untrusted-attachment prompt suffix to the child task.
OpenClaw-style cleanup for failures after staging but before runtime dispatch is
now closed as well, and terminal child-run cleanup removes staged attachment
dirs unless explicit retention is configured. OpenClaw attachment config limits
and explicit disabled posture are now closed for the native spawn path.
Remaining spawn parity includes ACP protocol breadth and deeper sandbox
lifecycle guardrails.

Current queue-head adjustment: `sessions.spawn` now accepts internal
`requesterSessionKey` context for native executor calls, resolves that requester
session, reads its stored `spawnDepth`, and returns OpenClaw-style `forbidden`
when the caller is already at the default max depth. Remaining depth parity is
configurable max depth, ancestry fallback, and active-child counting until the
next slice closes the legacy fallback.

Current queue-head adjustment: `sessions.spawn requesterSessionKey=...` now
falls back to legacy `spawnedBy` / `parentSessionKey` ancestry when a requester
session has no stored `spawnDepth`, preserving the default max-depth guard for
older child-session metadata. Remaining depth parity is configurable max depth
and active-child counting; remaining spawn parity also includes ACP harness
spawning, sandbox behavior, lifecycle hooks, and native agent-tool executor
wiring.

Current queue-head adjustment: `sessions.spawn` now honors persisted
`gateway.agents.defaults.subagents.maxSpawnDepth` from the control config schema,
so operators can allow bounded nested subagent launches above the default max
depth of 1. Remaining depth/concurrency parity is active-child counting through
`maxChildrenPerAgent`; remaining spawn parity also includes ACP harness
spawning, sandbox behavior, lifecycle hooks, and native agent-tool executor
wiring.

Current queue-head adjustment: `sessions.spawn` now honors persisted
`gateway.agents.defaults.subagents.maxChildrenPerAgent` by counting live tracked
child runs for the requester and returning OpenClaw-style `forbidden` before
submitting another task when the cap is reached. Remaining spawn parity includes
ACP harness spawning, sandbox behavior, lifecycle hooks, role/control-scope
metadata, and native agent-tool executor wiring.

Current queue-head adjustment: `sessions.spawn` now persists depth-derived
`subagentRole` (`orchestrator` or `leaf`) and `subagentControlScope`
(`children` or `none`) on spawned session metadata. Remaining spawn parity
includes ACP harness spawning, sandbox behavior, lifecycle hooks, and native
agent-tool executor wiring.

Current queue-head adjustment: `sessions.spawn sandbox="require"` now returns
the OpenClaw-style `forbidden` response before runtime dispatch when OpenZues
has no sandboxed target runtime to provide. Remaining spawn parity includes ACP
harness spawning, thread/session-mode hooks, lifecycle cleanup, and native
agent-tool executor wiring.

Current queue-head adjustment: `sessions.spawn mode="session"` now returns the
upstream-shaped error unless `thread=true` is also supplied, avoiding
half-bound persistent child sessions. Remaining spawn parity includes ACP
harness spawning, configured target policy (`allowAgents` / `requireAgentId`),
thread-binding hooks, lifecycle cleanup, and native agent-tool executor wiring.

Current queue-head adjustment: `sessions.spawn` now honors persisted
`requireAgentId` and `allowAgents` target policy, and
`agents.list toolProjection=sessions_spawn` now exposes the matching requester,
`allowAny`, and allowed target list instead of advertising every configured
agent. Remaining spawn parity includes ACP harness spawning, thread-binding
hooks, lifecycle cleanup, and native agent-tool executor wiring.

Current queue-head adjustment: `sessions.spawn thread=true` now returns the
upstream-shaped no-hook error before runtime dispatch because OpenZues has no
channel plugin `subagent_spawning` hook wired to bind persistent child threads.
Remaining spawn parity includes ACP harness spawning, lifecycle cleanup, and
native agent-tool executor wiring.

Current queue-head adjustment: `sessions.spawn runtime="acp" sandbox="require"`
now returns the upstream-shaped ACP sandbox policy error before the generic
ACP-unavailable boundary. Remaining spawn parity includes actual ACP harness
spawning, lifecycle cleanup, and native agent-tool executor wiring.

Current queue-head adjustment: live `session.message` payloads now carry nested
OpenClaw transcript identity metadata (`message.__openclaw.id` /
`message.__openclaw.seq`) alongside the existing top-level `messageId` /
`messageSeq`. The next bounded transcript seam should stay with session-event
replay/filtering or another source-backed `chat.*` / `sessions.*` mismatch.

Current queue-head adjustment: broad `sessions.subscribe` clients now receive
live `session.message` transcript events as well as `sessions.changed`, matching
OpenClaw's operator session stream while keeping `sessions.messages.subscribe`
as the narrower session-key filter. The next bounded seam should move to
direct REST/session-history replay parity or another source-backed transcript
gap.

Current queue-head adjustment: direct `GET /sessions/{sessionKey}/history` now
serves OpenClaw-style JSON/SSE history, including cursor pagination, preserved
`messages`, `items`, `hasMore`, `nextCursor`, raw `__openclaw.seq` metadata,
default 8k text caps, lenient invalid-cursor handling, initial `history` SSE
events, and `not_found` responses for unknown session keys. The next bounded
seam should inspect live SSE update behavior or the next source-backed
transcript replay gap.

Current queue-head adjustment: RPC `sessions.get` now defaults to OpenClaw's
200-message limit instead of clipping no-limit reads to 50 messages. The next
bounded transcript seam should continue through live SSE updates or another
source-backed `sessions.*` response-shape mismatch.

Current queue-head adjustment: direct session-history SSE streams now stay live
after the initial `history` event. Unbounded streams emit inline OpenClaw-style
`message` events from live `session.message` gateway events, bounded or cursor
streams emit refreshed `history` windows, and non-message `sessions.changed`
updates refresh history without duplicating normal message-phase updates. The
next bounded transcript seam should stay with remaining `sessions-history-http`
edge cases such as auth/scope rejection, duplicate/freshest session resolution,
or silent transcript refresh semantics if they map cleanly to OpenZues'
SQLite-backed session store.

Current queue-head adjustment: RPC `sessions.get` now accepts explicit limits
above 1000 like OpenClaw's WebSocket method, while direct HTTP
`/sessions/{sessionKey}/history` keeps its upstream 1000-row REST cap. The next
bounded transcript seam should inspect another source-backed `chat.*` /
`sessions.*` mismatch instead of conflating RPC limits with direct REST limits.

Current queue-head adjustment: direct session-history HTTP now rejects non-GET
methods with OpenClaw's `405`, `Allow: GET`, and plain-text
`Method Not Allowed` response instead of FastAPI's default JSON 405. The next
bounded transcript seam should stay on source-backed direct-history edge cases
or move to the next concrete `chat.*` / `sessions.*` runtime mismatch.

Current queue-head adjustment: direct session-history HTTP now rejects blank
decoded session keys with OpenClaw's `400` `invalid_request_error` JSON before
dispatching to history lookup or method-specific handling. The next bounded
transcript seam should stay on direct-history source edges only when they map
cleanly to OpenZues' SQLite-backed session store.

Current queue-head adjustment: remote direct session-history HTTP now honors a
declared `x-openclaw-scopes` header, rejecting scope sets that omit
`operator.read` with OpenClaw-style forbidden JSON while preserving loopback and
no-header API-key behavior. Remaining direct-history edges that depend on
OpenClaw's file-backed duplicate transcript store should be treated carefully
because OpenZues' current source of truth is SQLite-backed control-chat rows.

Current queue-head adjustment: direct session-history SSE now covers the
remaining OpenClaw history-state invariants that map to the SQLite transcript
store: silent `NO_REPLY` rows do not emit fast-path `message` events, bounded
windows stay anchored on visible history after silent refreshes, and later
visible messages retain raw `messageSeq` numbering after transcript-only
refreshes. The next bounded seam should move to a source-backed `chat.history`
or `sessions.*` mismatch rather than OpenClaw-only file-store duplicate rows.

Current queue-head adjustment: persisted custom agents now flow through
`agent.identity.get` by explicit `agentId` and by `agent:<id>:main` session keys,
using the SQLite agent registry as the truth source while preserving malformed
session-key and mismatched-selector rejection. The next adjacent session/agent
seam is custom-agent workspace file ownership or another transcript/runtime gap.

Current queue-head adjustment: `agents.files.list/get/set` now resolve persisted
custom-agent workspaces before reading or writing allowed instruction/memory
files, instead of forcing all file calls through the main OpenZues workspace.
The next adjacent seam should stay in session/chat transcript/runtime ownership
unless a smaller custom-agent lifecycle gap is proven.

Current queue-head adjustment: `sessions.send` and `sessions.steer` now reject
`agent:<id>:...` keys whose custom-agent owner has been deleted, matching the
OpenClaw deleted-agent guard before runtime send/steer dispatch. The next seam
should continue through chat-history/session-read model fidelity.

Current queue-head adjustment: `chat.history` now hides assistant-only
`NO_REPLY` / `ANNOUNCE_SKIP` / `REPLY_SKIP` rows and strips inline
`[[reply_to...]]` / `[[audio_as_voice]]` directives from displayed text. The
next history seam is usage/cost/read-model metadata fidelity or another bounded
transcript projection mismatch.

Current queue-head adjustment: `chat.history` now preserves optional assistant
`usage` / `cost` metadata from control-chat rows through nullable SQLite JSON
columns while still withholding arbitrary debug/details fields. The next
read-model seam should stay bounded to transcript truncation, metadata, or
session-history parity.

Current queue-head adjustment: `chat.history maxChars` now applies per-message
prefix truncation with the OpenClaw `...(truncated)...` marker instead of using
a global tail budget that drops older messages. The next transcript seam should
move to `sessions.get`/history parity or a narrow API mirror if found.

Current queue-head adjustment: `chat.history` now applies the current OpenClaw
default 8,000-character text cap when callers omit `maxChars`, while
`sessions.get` keeps its raw-session behavior. The next bounded seam should
inspect session event subscriptions or preview sanitization rather than keep
widening history.

Current queue-head adjustment: `chat.history` and direct
`GET /sessions/{sessionKey}/history` now honor the persisted
`gateway.webchat.chatHistoryMaxChars` control-UI config value, while explicit
RPC `maxChars` still overrides config. The next bounded seam should inspect a
new source-backed `chat.*` / `sessions.*` read-model mismatch, not the now-closed
default/config text cap path.

Current queue-head adjustment: `chat.history` now replaces single oversized
projected messages with `[chat.history omitted: message too large]` and
OpenClaw truncation metadata before serialization once they exceed the current
128 KiB single-message budget, while preserving large-but-valid messages below
that cap. The next bounded history seam should prove whether recent small
messages survive alongside an oversized latest message.

Current queue-head adjustment: `chat.history` now enforces a final serialized
message-array byte budget after single-message placeholder replacement, using
OpenClaw's 6 MiB default and keeping the newest rows that fit while dropping
older rows. The next bounded transcript seam should move to event replay or
`sessions.get` fidelity.

Current queue-head adjustment: `sessions.preview` now reuses chat-history
display hygiene by hiding assistant skip-only rows and stripping inline
reply/audio directives before rendering preview text. The next nearby seam is
session message event subscription replay/shape if a focused mismatch is found.

Current queue-head adjustment: live `session.message` events now apply the same
OpenClaw display hygiene: inline `[[reply_to...]]` / `[[audio_as_voice]]`
directives are stripped and assistant-only `NO_REPLY` / `ANNOUNCE_SKIP` /
`REPLY_SKIP` rows no longer emit `session.message` or message-phase
`sessions.changed` events. The next bounded transcript seam should move to
session message final/delta replay shape, `sessions.get` fidelity, or another
focused `chat.*`/`sessions.*` mismatch from upstream tests.

Current queue-head adjustment: live transcript `session.message` and
`sessions.changed` events now project assistant message `usage_json` / `cost_json`
into OpenClaw-shaped top-level `inputTokens`, `outputTokens`, `totalTokens`,
`totalTokensFresh`, and `estimatedCostUsd` metadata. The next bounded seam should
stay with session event metadata breadth, `sessions.get` fidelity, or SSE/history
transcript replay parity.

Current queue-head adjustment: transcript `session.message` and message-phase
`sessions.changed` events now copy persisted spawned-session metadata,
`forkedFromParent`, and last-route thread fields (`lastChannel`, `lastTo`,
`lastAccountId`, `lastThreadId`) from the session payload. The next bounded seam
should move to session message subscription/filtering parity, `sessions.get`
fidelity, or SSE fast-path replay gaps.

Current queue-head adjustment: `sessions.get` now supports cursor pagination
when the visible transcript spans multiple pages, preserving the legacy
`messages` field while adding `items`, `hasMore`, `nextCursor`, and raw
`__openclaw.seq` metadata. The returned string `nextCursor` can be passed
directly into the next `sessions.get` call. The next bounded seam should stay
with session history read-model fidelity, unknown-session status, or SSE
fast-path parity.

Current queue-head adjustment: `sessions.get` now accepts OpenClaw `seq:<n>`
cursor strings in addition to bare numeric cursor strings. The next bounded
read-model seam should move to session event replay/SSE parity or another
source-backed transcript mismatch.

Current queue-head adjustment: `sessions.patch` now resolves the requested
session key before patching and can update metadata/message-backed child
sessions instead of only the current session. The next bounded seam should stay
with remaining `sessions.*` parameter breadth, lifecycle hook/event fidelity, or
session history replay behavior.

Current queue-head adjustment: `sessions.create` now scopes the `key=main`
alias to the requested persisted custom agent, returning and storing
`agent:<id>:main` instead of rejecting the request as an `agentId` /
`sessionKey` mismatch. The next bounded seam should stay with `sessions.create`
sentinel/parameter fidelity or another adjacent session lifecycle gap.

Current queue-head adjustment: `sessions.create` now preserves literal `global`
and `unknown` sentinel keys when `agentId` is supplied, instead of trying to
force them through agent-scoped session-key validation. The next bounded seam
should continue through session-create response fidelity or session-list
transcript usage/model fallback parity.

Current queue-head adjustment: initial `sessions.create` runs now return the
pending OpenClaw-style `messageSeq` for the first submitted user turn while
leaving established `sessions.send` / `sessions.steer` response payloads stable.
The next bounded seam should move to `sessions.list` transcript usage/model
fallback parity.

Current queue-head adjustment: `sessions.list` now derives fresh prompt-token
usage totals, estimated cost, assistant model identity, and known Anthropic 1M
context from persisted assistant transcript rows. The next bounded seam should
continue with `sessions.changed` mutation-event usage metadata or another
adjacent session lifecycle/read-model gap.

Current queue-head adjustment: mutation `sessions.changed` payloads now copy
fresh transcript-derived `totalTokensFresh` and `estimatedCostUsd` alongside
the existing token/model fields. The next bounded seam should continue with
remaining session lifecycle metadata such as reset/delete/compaction event
fidelity.

Current queue-head adjustment: mutation `sessions.changed` payloads now copy
persisted session setting and route fields, including `responseUsage`,
`fastMode`, `forkedFromParent`, `lastChannel`, `lastTo`, `lastAccountId`, and
`lastThreadId`. The next bounded seam should stay in the adjacent session
event metadata cluster.

Current queue-head adjustment: `sessions.patch` now resolves request aliases
such as `subagent:child` before metadata writes, response keys, and
`sessions.changed` publishes, so subagent mutations land under
`agent:main:subagent:child`. The next bounded seam should continue through
session reset/delete alias fidelity or list/read-model details.

Current queue-head adjustment: session snapshots now include an OpenClaw-shaped
`deliveryContext` object derived from persisted last-route metadata while
retaining the raw `last*` fields. The next bounded seam should continue through
session-store RPC response fidelity.

Current queue-head adjustment: session snapshots and mutation `sessions.changed`
events now preserve string `lastThreadId` values such as Slack decimal thread
ids instead of dropping them through an integer-only route metadata parser. The
next bounded seam should continue through session-store RPC response fidelity.

Current queue-head adjustment: `sessions.list` defaults now include
`modelProvider` alongside `model`, `contextTokens`, and `mainSessionKey`, closing
the next small OpenClaw response-shape gap in the session inventory header. The
next bounded seam should continue through adjacent `sessions.*` response
fidelity.

Current queue-head adjustment: session snapshots now emit
`totalTokensFresh: false` for no-usage or stale-usage rows instead of omitting
the freshness marker. The next bounded seam should continue through adjacent
`sessions.*` response fidelity.

Current queue-head adjustment: `sessions.patch` now splits provider-qualified
model overrides into `providerOverride` and `modelOverride`, returns the
OpenClaw-style patch entry shape, and resolves/list rows under the split model
identity. The next bounded seam should continue through adjacent `sessions.*`
response fidelity.

Current queue-head adjustment: `sessions.reset` now discards stale runtime
`modelProvider` / `model` / `contextTokens` metadata while preserving explicit
provider/model overrides as `modelOverrideSource: user`. The next bounded seam
should continue through adjacent `sessions.*` response fidelity.

Current queue-head adjustment: `sessions.reset` and session payloads now
preserve owned child metadata such as group/channel fields, queue settings,
auth-profile overrides, CLI bindings, custom display name, and nested delivery
context. The next bounded seam should continue through adjacent `sessions.*`
response fidelity.

Current queue-head adjustment: `sessions.preview` now resolves mixed-case
legacy main aliases by keeping the freshest exact stored alias row instead of
merging stale duplicate alias transcripts. The next bounded seam should
continue through adjacent `sessions.*` alias cleanup and response fidelity.

Current queue-head adjustment: `sessions.delete` now resolves request aliases
such as `subagent:child` before deleting metadata/transcript rows and returning
the mutation key. The next bounded seam should continue through adjacent
`sessions.*` alias cleanup and response fidelity.

Current queue-head adjustment: `sessions.compact` now resolves request aliases
such as `subagent:child` before compaction/checkpoint writes and response
shaping, so archived history lands under `agent:main:subagent:child`. The next
bounded seam should continue through adjacent `sessions.*` alias cleanup and
response fidelity.

Current queue-head adjustment: `sessions.compaction.restore` now resolves
request aliases such as `subagent:child` before checkpoint lookup, transcript
restore, and mutation-event publishing. The next bounded seam should continue
through compaction inventory read aliases or adjacent `sessions.*` response
fidelity.

Current queue-head adjustment: `sessions.compaction.list/get` now resolve
request aliases such as `subagent:child` before checkpoint inventory reads, so
short subagent keys can locate canonical checkpoint rows. The next bounded seam
should continue through compaction branch alias cleanup or adjacent
`sessions.*` response fidelity.

Current queue-head adjustment: `sessions.compaction.branch` now resolves
request aliases such as `subagent:child` before copying source metadata,
branching checkpoint history, and publishing source/target session-change
events. The next bounded seam should move out of compaction alias cleanup and
continue through adjacent `sessions.*` response fidelity.

Current queue-head adjustment: `sessions.messages.subscribe/unsubscribe` now
resolve request aliases such as `subagent:child` before returning the key and
updating the hub's scoped message filter, so canonical subagent
`session.message` events reach short-alias subscribers. The next bounded seam
should continue through adjacent `sessions.*` response fidelity.

Current queue-head adjustment: `sessions.get` now resolves request aliases
such as `subagent:child` before reading transcript rows, so short aliases return
the canonical subagent transcript instead of an empty message list. The next
bounded seam should continue through adjacent session usage/read-model
fidelity.

Current queue-head adjustment: `sessions.usage`, `sessions.usage.timeseries`,
and `sessions.usage.logs` now resolve request aliases such as `subagent:child`
before reading usage summaries, mission points, or usage-linked transcript rows.
The next bounded seam should continue through adjacent session-keyed read/write
surfaces.

Current queue-head adjustment: `chat.history` now resolves request aliases such
as `subagent:child` before reading transcript rows and session metadata. The
next bounded seam should continue through adjacent session-keyed runtime paths
if a focused mismatch is proven.

Current queue-head adjustment: `chat.send`, `sessions.send`, and
`sessions.steer` now resolve request aliases such as `subagent:child` before
runtime dispatch, run tracking, pending-message counts, and session-change
events. The next bounded seam should continue through remaining session-keyed
runtime surfaces such as abort/wait if a focused mismatch is proven.

Current queue-head adjustment: `chat.abort` now records tracked run owner
connection/device metadata from `chat.send`, `sessions.send`,
`sessions.steer`, `sessions.spawn`, `sessions.create`, and `agent`, then
rejects explicit and session-scoped aborts from non-owner requesters unless the
caller has `operator.admin`, while preserving same-device reconnect aborts and
legacy ownerless-run compatibility. The next bounded seam should continue into
OpenClaw abort partial transcript persistence or the adjacent `agent.wait`
read model if a focused mismatch is proven.

Current queue-head adjustment: `chat.abort` now persists buffered assistant
partials returned by the native abort runtime into the SQLite transcript as
idempotent `runId:assistant` assistant messages with `stopReason="stop"` and
`openclawAbort` metadata. RPC aborts record `origin="rpc"`, `/stop`-style
abort commands record `origin="stop-command"`, blank partials are ignored, and
`chat.history` projects the stored abort metadata. The next bounded seam should
move to `agent.wait` read-model fidelity or another source-backed
session/runtime mismatch.

## How To Read This Queue

- This queue is repo-level and cross-cutting. It is for seams likely to fall between shard workers or cut across cron, session, gateway, delivery, and integration ownership.
- `Hot` means the relevant product files are already active in the current dirty tree, so the parity orchestrator should prefer verification and ledger work unless a fix is clearly surgical.
- `Next unowned` means the seam is not yet covered by the current hot write sets and is the best follow-on slice for this thread.

## Unresolved Queue

| Priority | Seam | Status | Why it still matters | Next exact move |
| --- | --- | --- | --- | --- |
| P1 | Browser/canvas/nodes/voice OpenClaw feature-family seam | Active | OpenZues now routes direct text send, multi-media URL send, `poll`, explicit cron announce, saved session-like delivery replays, provider-shaped send/poll callbacks, opt-in route-backed gateway webhook adapters, account/channel-specific native adapter bindings, Slack Web API delivery/uploads, Telegram Bot API delivery/media groups, Discord webhook delivery/polls, and WhatsApp Cloud API text/media/interactive-button delivery through one shared outbound runtime owner; full Ops Mesh, CLI, and adjacent gateway node/session/model/log/presence sweeps now prove no smaller provider-runtime blocker remains in this queue. The first browser/canvas/nodes/voice slices are now landed: `node.event` honors upstream-style `chat.subscribe` / `chat.unsubscribe`, the registry can route session-scoped events back to subscribed nodes, node `exec.started` / `exec.finished` / `exec.denied` events queue session-scoped next-heartbeat system notifications with duplicate `exec.finished` suppression, `notifications.changed` events become session-scoped notification wakes, `voice.transcript` events route into the chat runtime with stable node-voice idempotency plus near-duplicate suppression, text `agent.request` deep-links route into the chat runtime with route-safe delivery plus receipt/thinking/timeout hints, effective `agent.request` attachments keep an honest default unavailable boundary and can now pass through an injected attachment runtime, direct `chat.send`, `sessions.send`, and `sessions.steer` can use that injected attachment runtime when wired, `create_app()` now persists effective base64 attachments to durable local media files and passes bounded `media://`/hash/path metadata into control chat instead of raw blob text, recorded `push.apns.register` events move `push.test` from missing-registration to the honest sender-runtime boundary, registered nodes can complete `push.test` through an injected APNS sender adapter, app-level direct plus relay registrations now send OpenClaw-compatible APNS requests with ES256 bearer tokens, bearer relay grants, gateway signatures, and provider response metadata, disconnected APNS-registered nodes can wake/reconnect before `node.invoke`, `node.invoke` retries an available APNS-backed wake once when the first nudge does not reconnect, direct APNS registrations are cleared on upstream-style `400 BadDeviceToken` / `410` invalidation results from alert or wake sends, failed background wake retries send one throttled foreground APNS reopen nudge, assistant control-chat shortcodes now produce structured canvas previews rendered in the web transcript, `/__openclaw__/a2ui` serves a traversal-safe A2UI scaffold plus bundle, `/__openclaw__/ws` exposes the live-reload upgrade boundary plus websocket accept path and reload broadcast owner, `/__openclaw__/canvas/` serves a default canvas host page from the traversal-safe canvas state root, the app now runs a filesystem-backed debounce watcher that publishes `canvas/reload` into connected canvas clients, served canvas HTML now carries the OpenClaw live-reload/action bridge hook, scoped capability URLs now consume minted node canvas tokens for canvas/A2UI/WS paths, malformed `canvas.a2ui.push*` JSONL is rejected before node dispatch, configured node allow/deny command lists now flow into node invoke plus node catalog/scope-upgrade logic, node list/describe/API catalog/pairing surfaces now advertise only allowlisted commands instead of raw rejected declarations, advertised native browser commands now have gateway-method runtimes backed by `agent-browser` with a truthful unavailable boundary, plugin-published node-host browser commands/caps are visible in capability/bootstrap inventory, `chat.send` media-only final replies now project stale `NO_REPLY` plus media into OpenClaw-style `MEDIA:<url>` transcript text, `update.run` now drives a native fakeable git/install/build runner before sentinel/restart projection, and ACP client spawn preflight now resolves Windows `.cmd` shims without shell execution. The broad family is still minimal compared with OpenClaw and remains an active repo-wide parity family. | Rotate to the next source-backed runtime/session seam, currently ACP interactive protocol replay or sandboxed spawn media/workspace staging. |

Current queue-head adjustment: `browser.status` is now productized as a read-only gateway method backed by the existing browser posture in operator status, with method/API/policy verification. The next small browser-runtime seam is `browser.verify` / `browser.doctor` productization or a richer node-host plugin command inventory proof.

Current queue-head adjustment: `browser.verify` and `browser.doctor` are now productized as read-scope gateway methods. `browser.verify` runs a bounded `agent-browser` verification, and `browser.doctor` combines existing browser posture with optional verification, so the next small browser/canvas/node seam shifts to richer node-host plugin inventory or the next unimplemented upstream browser command family.

Current queue-head adjustment: plugin node-host browser command inventory is
now surfaced through the native capability and bootstrap read models. OpenZues
projects OpenClaw-style plugin-declared `nodeHostCommands` and `nodeHostCaps`
into `browser_runtime.node_host_commands` / `node_host_caps`, filters them to
the browser cap family, carries the per-lane counts, and avoids inflating the
saved-launch runtime method count with locally built-in browser gateway
methods. The next browser/canvas/node pass should only reopen this family for
new source-backed runtime inventory gaps; the active next repo-level seam can
rotate to ACP client harness replay, sandboxed spawn media/workspace staging,
or another bounded runtime-control queue head.

Current queue-head adjustment: `browser.tabs` is now productized as the first read-only browser command-breadth slice beyond status/verify/open/snapshot/console/errors. The next small browser/canvas/node seam is likely another upstream browser command family such as lifecycle/profile/screenshot/action commands, or richer plugin node-host inventory.

Current queue-head adjustment: `browser.profiles` is now productized as a read-only profile inventory method and native catalog entry. The next small browser/canvas/node seam is likely a bounded screenshot/lifecycle method, or richer plugin node-host inventory.

Current queue-head adjustment: `browser.screenshot` is now productized as a read-only browser capture method and native catalog entry. It writes through `agent-browser` to a controlled temp artifact instead of accepting arbitrary caller-supplied paths, so the next small browser/canvas/node seam is likely lifecycle commands such as browser start/stop or richer plugin node-host inventory.

Current queue-head adjustment: `browser.pdf` is now productized as a read-only browser page-export method and native catalog entry. It writes through `agent-browser pdf` to a controlled temp artifact, so the next small browser/canvas/node seam moves to mutating browser actions/lifecycle or richer plugin node-host inventory.

Current queue-head adjustment: `browser.navigate` is now productized as a write-scoped active-session navigation method and native catalog entry. It uses the local `agent-browser open <url>` primitive and intentionally does not claim upstream target-tab routing yet, so the next small browser seam is target-aware navigation/action support, close/lifecycle methods, or richer plugin node-host inventory.

Current queue-head adjustment: `browser.close` is now productized as a write-scoped session/all-session close method and native catalog entry. It uses `agent-browser close [--all]` and intentionally does not claim upstream targetId tab-close semantics yet, so the next small browser seam is target-aware tab actions or a bounded `browser.act` subset.

Current queue-head adjustment: the first `browser.act` slice is now productized as a write-scoped bounded action bridge and native catalog entry. It maps wait/click/type/fill/press/hover/focus/check/uncheck/evaluate/resize/close into local `agent-browser` primitives, so the next small browser seam is target-aware tab routing, richer action grammar, or lifecycle start/stop.

Current queue-head adjustment: target-aware tab focus/close is now productized. `browser.focus` focuses a tab target/index, and `browser.close` accepts `targetId` for tab close while preserving session/all-session close. The next small browser seam is richer action grammar, tab open tracking, or lifecycle start/stop.

Current queue-head adjustment: `browser.open` now uses new-tab semantics and parses returned target metadata, while `browser.navigate` owns active-session URL navigation. The next small browser seam is richer targetId-to-tab resolution, action grammar, or lifecycle start/stop.

Current queue-head adjustment: `browser.start` and `browser.stop` are now productized as write-scoped lifecycle gateway methods. `browser.start` initializes an `agent-browser` session on `about:blank`, and `browser.stop` closes the session or all sessions when explicitly requested. The next small browser seam is fixing the local tab inventory verb to match the actual `agent-browser tab list` lifecycle and then continuing into richer action grammar.

Current queue-head adjustment: `browser.tabs` now calls the installed CLI's real `agent-browser tab list` inventory verb instead of the stale top-level `tabs` help path. The next small browser seam is richer `browser.act` grammar for documented local primitives such as double-click, select, scroll, and scroll-into-view.

Current queue-head adjustment: the bounded `browser.act` mapper now includes documented local primitives for double-click, select, scroll, and scroll-into-view. Riskier file/network/storage actions remain separate seams; the next small browser seam is a read-only info bridge such as `browser.get` or `browser.is`.

Current queue-head adjustment: `browser.get` is now productized as a read-only value bridge for installed `agent-browser get <what> [selector]` values. The next adjacent browser seam is `browser.is` for visible/enabled/checked state checks.

Current queue-head adjustment: `browser.is` is now productized as a read-only visible/enabled/checked state bridge. The next low-risk browser seam is history navigation (`browser.back`, `browser.forward`, `browser.reload`) before riskier file/network/storage actions.

Current queue-head adjustment: `browser.back`, `browser.forward`, and `browser.reload` are now productized as write-scoped history navigation methods. The next low-risk browser seam is read-only runtime stream status before mutating stream enable/disable or network/storage/file actions.

Current queue-head adjustment: `browser.stream.status` is now productized as a read-only runtime stream posture method. The next adjacent browser seam is mutating stream lifecycle (`browser.stream.enable` / `browser.stream.disable`) before moving into higher-risk network/storage/file actions.

Current queue-head adjustment: `browser.stream.enable` and `browser.stream.disable` are now productized as write-scoped runtime stream lifecycle methods with bounded port validation. The next browser command-family seam should move to a read-only network/storage/file capability before any broader mutation surface.

Current queue-head adjustment: `browser.network.requests` is now productized as a read-only filtered request-log bridge and intentionally does not expose `--clear`, route, unroute, or HAR mutation. The next adjacent browser seam is read-only request detail (`browser.network.request`) before storage/file mutation.

Current queue-head adjustment: `browser.network.request` is now productized as a read-only captured request detail bridge. The next adjacent browser seam is read-only storage/cookie inventory before storage mutation.

Current queue-head adjustment: `browser.cookies.get` and `browser.storage.get` are now productized as read-only cookie/localStorage/sessionStorage inventory methods. The next browser seam should stay in read-only diagnostics, such as diff or browser session inventory, before set/clear/upload/download mutation.

Current queue-head adjustment: `browser.session.current` and `browser.session.list` are now productized as read-only agent-browser session diagnostics. The next browser seam is read-only diff diagnostics before visual-diff file-output or upload/download mutation.

Current queue-head adjustment: `browser.diff.snapshot` is now productized as a read-only snapshot diff diagnostic without arbitrary baseline file paths. The next browser seam should either add guarded auth-profile metadata reads or take a write-scoped diff-url/browser mutation with explicit policy classification.

Current queue-head adjustment: `browser.auth.list` and `browser.auth.show` are now productized as read-only auth profile metadata methods. The next browser seam is a write-scoped diff URL/navigation diagnostic or a guarded file-output diff path.

Current queue-head adjustment: `browser.diff.url` is now productized as a write-scoped URL comparison diagnostic with explicit navigation-policy classification. It validates URL pair input plus screenshot/full-page/wait-until/selector/compact/depth options and intentionally does not expose arbitrary baseline or output file paths yet. The next browser seam is a guarded visual diff file-output path or the next low-risk browser file/upload/download diagnostic boundary.

Current queue-head adjustment: `browser.diff.screenshot` is now productized as a guarded visual diff diagnostic. It accepts only existing OpenZues temp screenshot baselines, always writes the diff image to an OpenZues-controlled temp artifact, validates threshold/selector/full-page options, and remains read-scoped because it does not expose arbitrary output paths or mutate browser state. The next browser seam is a low-risk file boundary such as controlled download capture, upload guardrails, or read-only trace/profile metadata.

Current queue-head adjustment: `browser.download` is now productized as a write-scoped controlled file capture method. It clicks a selector through `agent-browser download`, writes only to an OpenZues-generated temp path, and treats caller filenames as sanitized hints rather than paths. The next browser seam is upload guardrails or a read-only trace/profile metadata boundary.

Current queue-head adjustment: `browser.upload` is now productized as a write-scoped guarded file-input method. It accepts only existing OpenZues temp artifacts (`openzues-browser-*`) and rejects arbitrary local files before invoking `agent-browser upload`. The next browser seam is read-only trace/profile metadata or another bounded debug diagnostic before broader debug/control mutation.

Current queue-head adjustment: `browser.trace.start` and `browser.trace.stop` are now productized as write-scoped browser debug artifact methods. `trace start` records through the current `agent-browser` session, and `trace stop` writes only to an OpenZues-generated temp ZIP artifact instead of accepting arbitrary output paths. The next browser seam is the adjacent profiler artifact lifecycle (`browser.profiler.start` / `browser.profiler.stop`) or another bounded debug diagnostic.

Current queue-head adjustment: `browser.profiler.start` and `browser.profiler.stop` are now productized as write-scoped browser performance artifact methods. `profiler start` accepts optional comma-separated categories, and `profiler stop` writes only to an OpenZues-generated temp JSON artifact. The next browser seam is another bounded debug/control command such as recording lifecycle, proxy/profile boundaries, or target-aware action breadth.

Current queue-head adjustment: `browser.record.start`, `browser.record.stop`, and `browser.record.restart` are now productized as write-scoped video recording lifecycle methods. Start/restart write only to OpenZues-generated temp WebM artifacts, and stop reports the tracked per-session artifact path/size. The next browser seam is proxy/profile mutation boundaries or target-aware action breadth.

Current queue-head adjustment: `browser.highlight` and `browser.inspect` are now productized as write-scoped browser debug methods. Highlight targets a selector/ref through `agent-browser highlight`, and inspect opens DevTools through `agent-browser inspect`; clipboard, proxy, and auth-vault mutations remain intentionally outside this bounded slice. The next browser seam is target-aware action breadth such as drag/mouse/keyboard/find, or a separately guarded clipboard/proxy decision.

Current queue-head adjustment: the bounded `browser.act` mapper now includes installed `agent-browser drag <src> <dst>` support with source/destination validation. The next browser seam is remaining target-aware action breadth such as mouse/keyboard/find, or a separately guarded clipboard/proxy decision.

Current queue-head adjustment: the bounded `browser.act` mapper now includes installed `agent-browser mouse move/down/up/wheel` support with structured action, coordinate, button, and delta validation. The next browser seam is remaining keyboard/find action breadth or a separately guarded clipboard/proxy decision.

Current queue-head adjustment: the bounded `browser.act` mapper now includes installed focused `agent-browser keyboard inserttext <text>` support, while existing `kind="type"` without a selector continues to cover `keyboard type`. The next browser seam is semantic `find` action breadth or a separately guarded clipboard/proxy decision.

Current queue-head adjustment: the bounded `browser.act` mapper now includes installed semantic `agent-browser find <locator> <value> [action] [text]` support for role/text/label/placeholder/alt/title/testid/first/last/nth locators, bounded actions, role name filtering, and exact matching. The next browser seam is a separately guarded clipboard/proxy/settings decision.

Current queue-head adjustment: `browser.set` is now productized for guarded low-risk settings: viewport, device, geo, offline, and media. The next browser seam is a separately guarded clipboard bridge or scoped headers/credentials setting decision; persistent proxy mutation remains intentionally guarded.

Current queue-head adjustment: `browser.clipboard.read`, `browser.clipboard.write`, `browser.clipboard.copy`, and `browser.clipboard.paste` are now productized as structured gateway methods backed by the installed `agent-browser clipboard` operations. The next browser seam is scoped headers/credentials settings, guarded storage/cookie mutation, HAR mutation, or auth save/login/delete; persistent proxy mutation remains intentionally guarded.

Current queue-head adjustment: `browser.storage.set` and `browser.storage.clear` are now productized as write-scoped localStorage/sessionStorage mutation methods backed by installed `agent-browser storage local|session set/clear` operations. The next browser seam is guarded cookie mutation, scoped headers/credentials settings, HAR mutation, or auth save/login/delete; persistent proxy mutation remains intentionally guarded.

Current queue-head adjustment: `browser.cookies.set` and `browser.cookies.clear` are now productized as write-scoped cookie mutation methods backed by installed `agent-browser cookies set/clear` operations. Runtime payloads avoid echoing cookie values from real browser calls. The next browser seam is scoped headers/credentials settings, HAR mutation, auth save/login/delete, or confirmation handling; persistent proxy mutation remains intentionally guarded.

Current queue-head adjustment: `browser.network.har.start` and `browser.network.har.stop` are now productized as write-scoped browser network artifact methods backed by installed `agent-browser network har start/stop` operations. HAR stop writes only to an OpenZues-generated temp `.har` artifact. The next browser seam is scoped headers/credentials settings, auth save/login/delete, confirmation handling, or batch/chat/dashboard productization; persistent proxy mutation remains intentionally guarded.

Current queue-head adjustment: `browser.confirm` and `browser.deny` are now productized as write-scoped pending-action decision methods backed by installed `agent-browser confirm/deny <id>` operations. The next browser seam is scoped headers/credentials settings, auth save/login/delete, or batch/chat/dashboard productization; persistent proxy mutation remains intentionally guarded.

Current queue-head adjustment: `browser.auth.login` and `browser.auth.delete` are now productized as write-scoped auth profile methods backed by installed `agent-browser auth login/delete <name>` operations. Password-bearing `auth.save` remains the next auth seam and should use stdin/vault-safe handling rather than echoing secrets in outputs. The next browser seam is password-safe auth save, scoped headers/credentials settings, or batch/chat/dashboard productization; persistent proxy mutation remains intentionally guarded.

Current queue-head adjustment: `browser.auth.save` is now productized as a write-scoped auth profile method backed by installed `agent-browser auth save <name> --password-stdin`. OpenZues keeps the password out of argv, sends it only over stdin, and redacts exact password echoes from the runtime payload. The next browser seam is scoped headers/credentials settings or batch/chat/dashboard productization; persistent proxy mutation remains intentionally guarded.

Current queue-head adjustment: `browser.set` now includes installed `agent-browser set headers <json>` and `set credentials <user> <pass>` support. The gateway validates header JSON, preserves proxy as a guarded boundary, and redacts header values plus HTTP-auth passwords from runtime payloads. The next browser seam is batch/chat/dashboard productization or provider/iOS-specific command boundaries.

Current queue-head adjustment: `browser.batch` is now productized as a bounded write-scoped bridge for installed `agent-browser batch [--bail] "<cmd>" ...` commands. The gateway accepts up to 20 one-line browser command strings, passes them as argv without a shell, and returns structured line/result metadata. The next browser seam is chat/dashboard productization or provider/iOS-specific command boundaries.

Current queue-head adjustment: `browser.dashboard.start` and `browser.dashboard.stop` are now productized as write-scoped bridges for the installed agent-browser observability dashboard lifecycle. Start validates an optional 1-65535 port and stop maps to `agent-browser dashboard stop`. The next browser seam is chat command productization or provider/iOS-specific command boundaries.

Current queue-head adjustment: `browser.chat` is now productized as a write-scoped single-shot bridge for installed `agent-browser chat <message>`. The gateway validates message/model/quiet/verbose params and leaves missing AI Gateway credentials as normal runtime unavailable errors. The next browser seam is provider/iOS-specific command boundaries; persistent proxy mutation remains intentionally guarded.

Current queue-head adjustment: `browser.ios.device.list`, `browser.ios.swipe`, and `browser.ios.tap` are now productized as provider-scoped bridges for installed `agent-browser -p ios` commands. Device list is read-scoped; swipe/tap are write-scoped and validate direction, distance, and target. Windows/non-Xcode hosts still surface iOS runtime unavailability honestly, and persistent proxy/profile mutation remains intentionally guarded. The browser command queue should now hand off to the next repo-level parity family instead of circling this seam.

Current queue-head adjustment: repo-level rotation moved from browser command productization into cron parity. `cron.add` and `cron.update` now accept OpenClaw-style `schedule.kind="cron"` objects with `expr`, optional `tz`, and optional `staggerMs`; cron jobs round-trip through `cron.list`, compute next due time, and launch through `cron.run` with `mode="due"`. The next repo-level method seam should move to gateway session or agent-file surfaces rather than reopening the closed browser command queue.

Current queue-head adjustment: `cron.add` and `cron.update` now also accept and
round-trip OpenClaw-style per-job `failureAlert` objects. OpenZues persists the
native alert config in the task-blueprint payload, projects `failureAlert` in
cron job snapshots, and merges update patches with the same object/`false`
contract used by OpenClaw. Remaining cron parity is the actual consecutive
failure alert dispatch/runtime state fields (`lastErrorReason`,
`lastDurationMs`, `consecutiveErrors`, delivery status, and alert cooldown
metadata), not the gateway method schema/persistence boundary.

Current queue-head adjustment: `cron.update` now accepts OpenClaw-style
`patch.state` objects and merges them into persisted native `cron_state`
metadata. Cron snapshots sanitize and project the persisted fields
(`nextRunAtMs`, `runningAtMs`, `lastRunAtMs`, `lastRunStatus`, `lastStatus`,
`lastError`, `lastErrorReason`, `lastDurationMs`, `consecutiveErrors`,
`lastDelivered`, `lastDeliveryStatus`, `lastDeliveryError`, and
`lastFailureAlertAtMs`) while preserving existing OpenZues-derived run status
fields when local execution data exists. Remaining cron parity is now the
runtime side of this state: `cron.run` should update consecutive failure
metadata and consume `failureAlert.after` / `cooldownMs` to dispatch alerts.

Current queue-head adjustment: Ops Mesh mission-result handling now consumes
per-job `failureAlert` runtime policy for failed cron runs. Failed scheduled
missions update persisted `cron_state` with last run/error/duration/delivery
status, increment `consecutiveErrors`, emit the OpenClaw-shaped failure-alert
message after the configured `after` threshold, stamp `lastFailureAlertAtMs`,
and suppress repeat alerts inside `cooldownMs`. Remaining cron runtime parity
is the broader OpenClaw config surface around retry/backoff policy and
provider-specific alert delivery metadata.

Current queue-head adjustment: main-session `systemEvent` cron dispatch now
persists OpenClaw-style success state when the wake request is queued:
`lastRunAtMs`, `lastRunStatus="ok"`, `lastStatus="ok"`, `lastDurationMs=0`,
`lastDeliveryStatus="not-requested"`, and reset consecutive failure state.
Remaining cron parity is no longer the local wake-result state boundary; it is
global cron config retry/backoff policy and richer provider delivery result
attribution.

Current queue-head adjustment: Ops Mesh now accepts production-wired global
`cron.failureAlert` settings through `Settings` / app construction and applies
them to failed cron jobs that have no per-job `failureAlert`, matching
OpenClaw's global `enabled` / `after` / `cooldownMs` behavior while preserving
per-job override and `failureAlert=false` suppression. Remaining cron runtime
parity is OpenClaw's retry/backoff policy for transient one-shot jobs and
richer provider-specific alert delivery attribution.

Current queue-head adjustment: transient failed one-shot cron jobs now consume
production-wired global `cron.retry` settings through `Settings` / app
construction. For `schedule.kind="at"` jobs, Ops Mesh records
`state.nextRunAtMs = endedAt + backoff`, keeps the job enabled while retry
attempts remain, and the scheduler plus `cron.run mode="due"` honor that retry
timestamp even after the original `schedule.at` has been consumed. Permanent or
exhausted one-shot failures are disabled while preserving error state for
inspection. Provider-specific failure-alert result attribution was audited
against upstream and skipped as a parity seam because OpenClaw's failure-alert
runtime is fire-and-forget. The active cron queue has moved to CLI parity.

Current queue-head adjustment: the CLI now exposes `cron status`,
`cron list`, `cron runs`, `cron run`, `cron rm` / `remove` / `delete`,
`cron enable`, and `cron disable` as thin JSON/human wrappers over the
production `cron.status`, `cron.list`, `cron.runs`, `cron.run`,
`cron.remove`, and `cron.update` gateway method owners. `cron list --all`
forwards the upstream `includeDisabled=true` shape, human list output includes
OpenClaw-style job id, name, schedule, status, target, agent, and model fields,
`cron runs` preserves the upstream `--id` / positive `--limit` request shape,
`cron run` preserves the upstream `--due` request shape plus ran/enqueued exit
rule, and the mutation commands preserve the upstream id/patch method shapes.
`cron add --name --cron --message` now also covers the first upstream create
path with inferred isolated agent turns, `wakeMode="now"`, enabled state, and
default announce delivery through channel `last`. Remaining cron CLI parity is
the rest of the larger `cron add` option surface. Main-session system-event
jobs now cover `--every`, `--description`, `--session-key`, `--wake
next-heartbeat`, and `--disabled`; `cron create` now aliases `cron add`, and
`--model` trims into the agent-turn payload, and delivery flags now cover
`--announce`, `--no-deliver`, `--channel`, `--to`, `--account`, and
`--best-effort-deliver`; cron schedule flags now cover `--tz`, `--stagger`,
and `--exact`, including OpenClaw-style `--at` parsing for IANA timezone
offset-less datetimes, DST-gap rejection, relative durations with `--tz`,
offset-less UTC defaults, and native `tzdata`-backed Windows timezone data.
`cron edit` now exists for basic name,
description, enable/disable, direct schedule patching, native-supported
session/agent fields, agentTurn/systemEvent payload patching, and delivery
metadata, failure-alert flags, and existing-cron `--exact` schedule patching;
`cron.add` and `cron.update` now persist agentTurn payload extras (`thinking`,
`timeoutSeconds`, `lightContext`, and `toolsAllow`), and `cron add` exposes the
matching CLI flags. `cron edit` now exposes the same flags plus
`--no-light-context` and `--clear-tools`. Explicit `deleteAfterRun=true`
storage, default one-shot delete-after-run on gateway-created `cron.add` jobs,
successful system-event `cron.run` cleanup, and isolated agent
mission-completion cleanup now work. No smaller source-backed cron queue head
remains; rotate back to the repo-level session/runtime-control and broader
CLI/runtime/doctor queue.

Current queue-head adjustment: `agents.files.list`, `agents.files.get`, and `agents.files.set` now cover OpenClaw's bootstrap/memory workspace files (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`, `HEARTBEAT.md`, `BOOTSTRAP.md`, `MEMORY.md`, and `memory.md`) while preserving the existing OpenZues `.codex/AGENTS.md` file. The next repo-level method seam should move to session/runtime-control surfaces instead of reopening agent-file filename breadth.

## Verified This Run

- Closed the node `agent.request` attachment-runtime adapter seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): effective node attachments now preserve the default unavailable boundary when no runtime exists and pass message, idempotency, thinking, delivery, timeout, attachments, route, and node context into an injected attachment sender when one is wired.
- Added focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) for the injected node attachment runtime while keeping the existing unavailable-boundary proof.
- Verified the slice with `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`, `PYTHONPATH=src;.venv\Lib\site-packages python -m mypy src/openzues/services/gateway_node_methods.py`, and a focused 15-test node/APNS/agent-request pack: `15 passed`.
- Closed the adjacent direct chat/session attachment-runtime adapter seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): `chat.send`, `sessions.send`, and `sessions.steer` now call the injected attachment sender for effective attachments, while text-only sends keep the existing chat sender and default installs keep the explicit unavailable boundary.
- Added focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) for direct chat, session send, and session steer attachment runtime paths, including `sessions.steer` preserving `interruptedActiveRun`.
- Verified the direct chat/session slice with `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`, `PYTHONPATH=src;.venv\Lib\site-packages python -m mypy src/openzues/services/gateway_node_methods.py`, and a focused 31-test chat/session/node/APNS pack: `31 passed`.
- Closed the app-level attachment bridge seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): `create_app()` now wires the injected attachment sender and preserves effective attachment type, MIME/name, route/node hints, and inline/base64 evidence in a bounded control-chat text envelope.
- Updated endpoint proofs in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py) so effective `chat.send`, `sessions.send`, and `sessions.steer` attachments now produce chat transcript entries instead of HTTP 503.
- Verified the app-level bridge with `ruff check src/openzues/app.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, `PYTHONPATH=src;.venv\Lib\site-packages python -m mypy src/openzues/app.py src/openzues/services/gateway_node_methods.py`, and a focused 16-test attachment API/method pack: `16 passed`.
- Closed the app-level APNS direct/relay binding seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_apns.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_apns.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_identity.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_identity.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\settings.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/settings.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): `create_app()` now wires `push.test` to OpenClaw-compatible APNS direct and relay senders, resolves `OPENZUES_APNS_*` / `OPENCLAW_APNS_*` credentials, signs direct ES256 bearer JWTs from `.p8` keys, signs relay bodies with the gateway device identity, and preserves APNS/relay status, ids, token suffix, topic, environment, and transport metadata.
- Added endpoint proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py) showing a node-recorded relay registration sends the exact bearer-auth relay body and verifies the Ed25519 `x-openclaw-gateway-signature` payload, plus a node-recorded direct registration sends to the production APNS HTTP/2 endpoint with an ES256 bearer JWT and APNS headers.
- Verified the APNS direct/relay binding with `ruff check src/openzues/services/gateway_apns.py src/openzues/services/gateway_identity.py src/openzues/settings.py src/openzues/app.py tests/test_gateway_nodes_api.py pyproject.toml`, `mypy src/openzues/services/gateway_apns.py src/openzues/services/gateway_identity.py src/openzues/settings.py src/openzues/app.py`, and a focused APNS method/API pack: `6 passed`.
- Closed the first APNS-backed node wake seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_apns.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_apns.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): disconnected nodes with recorded APNS registrations can now send background direct/relay APNS wake payloads before `node.invoke` waits for reconnect, and app wiring reuses the same APNS sender service for both `push.test` and node wake.
- Added method proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing a disconnected APNS-registered node wakes, reconnects, and completes `node.invoke` without a saved-lane wake callback.
- Verified the APNS wake seam with `ruff check src/openzues/services/gateway_apns.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_identity.py src/openzues/settings.py src/openzues/app.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py pyproject.toml`, `mypy src/openzues/services/gateway_apns.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_identity.py src/openzues/settings.py src/openzues/app.py`, and a focused APNS send/wake pack: `9 passed`.
- Closed the APNS-backed `node.invoke` wake retry seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): an available APNS-backed wake now waits for reconnect, retries once if the node remains disconnected, then invokes the node if the retry brings it back.
- Added red-first method proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py): `test_node_invoke_retries_recorded_apns_wake_when_first_wake_does_not_reconnect` first failed on the missing retry, then passed after the retry helper landed.
- Verified the APNS wake retry seam with `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`, `mypy src/openzues/services/gateway_node_methods.py`, and a focused APNS send/wake pack: `10 passed`.
- Closed the stale direct APNS registration cleanup seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): direct registrations are now invalidated in the SQLite node-event stream when APNS alert or wake sends return `400 BadDeviceToken` or `410`, while relay registrations and mismatched environment overrides stay intact.
- Added focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py): `test_push_test_clears_stale_direct_apns_registration_on_bad_device_token` was the red proof for repeated stale sends, and `test_node_invoke_clears_stale_direct_apns_registration_after_wake_failure` protects the wake-side cleanup.
- Verified the stale APNS cleanup seam with `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`, `mypy src/openzues/services/gateway_node_methods.py`, and a focused APNS send/wake pack: `12 passed`.
- Closed the foreground APNS nudge seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): when background APNS wake plus forced retry still leave the node disconnected, `node.invoke` now sends a best-effort alert nudge telling the user to reopen OpenZues, throttled to one nudge per node per 10 minutes.
- Added red-first proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py): `test_node_invoke_sends_foreground_apns_nudge_after_wake_retry_stalls` first failed with no nudge call, then passed and verifies the throttle by running a second failed invoke inside the window.
- Verified the foreground nudge seam with `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`, `mypy src/openzues/services/gateway_node_methods.py`, and a focused APNS send/wake/nudge pack: `13 passed`.
- Closed the durable app-level attachment bridge in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): effective base64 attachments entering through `chat.send`, `sessions.send`, and `sessions.steer` now persist under `data/gateway-attachments/inbound` and the control-chat prompt receives `media://` refs, saved paths, SHA-256 hashes, and byte counts instead of raw base64 content.
- Updated endpoint proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py): the attachment API tests first failed because no artifact existed, then passed while asserting the raw `Zm9v` payload is absent from the prompt.
- Verified the durable attachment seam with `pytest tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_sends_effective_chat_send_attachments_ tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_sends_effective_sessions_send_attachments_ tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_steers_effective_sessions_attachments_ -q`: `6 passed`, `ruff check src/openzues/app.py tests/test_gateway_nodes_api.py`: clean, and `mypy src/openzues/app.py`: clean.
- Closed the `channels.start` method-boundary seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): OpenZues now validates the OpenClaw `channels.start` shape and returns a truthful unsupported-runtime error for channels without a native start runtime instead of reporting the method as unknown.
- Added operator catalog discovery for `channels.start` in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_commands.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_commands.py).
- Verified the `channels.start` seam with `pytest tests/test_gateway_node_methods.py::test_channels_start_allows_blank_account_id_and_fails_runtime_boundary tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_allows_blank_channels_start_account_id -q`: `2 passed`, adjacent channel regression packs: `6 passed`, `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_commands.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean, and `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_commands.py`: clean.
- Closed the read-only `doctor.memory.dreamDiary` seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): OpenZues now reads `DREAMS.md` / `dreams.md` from the active workspace and returns the OpenClaw-shaped `agentId`, `found`, `path`, `content`, and `updatedAtMs` payload while leaving mutating dreaming repair/backfill methods explicitly unavailable.
- Added method and HTTP proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py).
- Verified the dream diary seam with `pytest tests/test_gateway_node_methods.py::test_doctor_memory_dream_diary_reads_workspace_diary tests/test_gateway_node_methods.py::test_doctor_memory_family_returns_explicit_unavailable_contract -q`: `6 passed`, `pytest tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_reads_doctor_memory_dream_diary tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_returns_doctor_memory_family_unavailable_contract -q`: `6 passed`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean, and `mypy src/openzues/services/gateway_node_methods.py`: clean.
- Closed the read-only `doctor.memory.status` payload seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): OpenZues now returns the OpenClaw-shaped `agentId` plus `embedding.ok=false` diagnostic when memory search is unavailable instead of converting that state into a method-level 503.
- Added method and HTTP proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py).
- Verified the memory status seam with `pytest tests/test_gateway_node_methods.py::test_doctor_memory_status_returns_missing_runtime_payload tests/test_gateway_node_methods.py::test_doctor_memory_dream_diary_reads_workspace_diary tests/test_gateway_node_methods.py::test_doctor_memory_family_returns_explicit_unavailable_contract -q`: `7 passed`, `pytest tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_returns_doctor_memory_status_payload tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_reads_doctor_memory_dream_diary tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_returns_doctor_memory_family_unavailable_contract -q`: `7 passed`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean, and `mypy src/openzues/services/gateway_node_methods.py`: clean.
- Closed the control-chat canvas preview integration seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\control_chat.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/control_chat.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/schemas.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/web/static/app.js): assistant `[embed ...]` shortcodes now stay raw in storage but become stripped `content` plus structured `canvas_previews` on view/append responses, and the web transcript renders those previews as sandboxed iframe cards.
- Added focused control-chat proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_app.py): `test_control_chat_view_extracts_canvas_embed_previews` first failed because the shortcode stayed in visible content, then passed with the structured preview payload.
- Verified the control-chat canvas seam with `pytest tests/test_app.py::test_control_chat_view_extracts_canvas_embed_previews -q`: `1 passed`, `pytest tests/test_gateway_canvas_render.py tests/test_app.py::test_control_chat_view_extracts_canvas_embed_previews -q`: `4 passed`, `ruff check src/openzues/schemas.py src/openzues/services/control_chat.py src/openzues/services/gateway_canvas_render.py tests/test_app.py tests/test_gateway_canvas_render.py`: clean, `mypy src/openzues/schemas.py src/openzues/services/control_chat.py src/openzues/services/gateway_canvas_render.py`: clean, and `node --check src/openzues/web/static/app.js`: clean.
- Closed the A2UI scaffold serving seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_a2ui.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_a2ui.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): `/__openclaw__/a2ui/` now serves a bundled scaffold, `/__openclaw__/a2ui/a2ui.bundle.js` exposes the OpenClaw canvas action bridge helper, HEAD requests return headers only, and encoded traversal paths stay 404.
- Added focused app proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py): `test_create_app_serves_a2ui_canvas_scaffold_and_blocks_traversal` first failed with 404, then passed after route binding.
- Verified the A2UI seam with `pytest tests/test_gateway_canvas_documents.py::test_create_app_serves_a2ui_canvas_scaffold_and_blocks_traversal -q`: `1 passed`, `pytest tests/test_gateway_canvas_documents.py tests/test_gateway_canvas_render.py tests/test_app.py::test_control_chat_view_extracts_canvas_embed_previews -q`: `18 passed`, `ruff check src/openzues/services/gateway_canvas_a2ui.py src/openzues/app.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/services/gateway_canvas_a2ui.py src/openzues/app.py src/openzues/services/gateway_canvas_documents.py src/openzues/services/gateway_canvas_render.py src/openzues/services/control_chat.py`: clean.
- Closed the canvas live-reload websocket boundary seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_a2ui.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_a2ui.py): plain HTTP on `/__openclaw__/ws` now returns the OpenClaw-style `426 upgrade required`, websocket upgrades are accepted and held until disconnect, and the A2UI bundle opens the same live-reload path with optional `oc_cap`.
- Added focused websocket proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py): `test_create_app_exposes_canvas_live_reload_websocket_path` first failed on immediate websocket close, then passed after route binding.
- Verified the websocket seam with `pytest tests/test_gateway_canvas_documents.py::test_create_app_exposes_canvas_live_reload_websocket_path -q`: `1 passed`, `pytest tests/test_gateway_canvas_documents.py tests/test_gateway_canvas_render.py tests/test_app.py::test_control_chat_view_extracts_canvas_embed_previews -q`: `19 passed`, `ruff check src/openzues/services/gateway_canvas_a2ui.py src/openzues/app.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/services/gateway_canvas_a2ui.py src/openzues/app.py src/openzues/services/gateway_canvas_documents.py src/openzues/services/gateway_canvas_render.py src/openzues/services/control_chat.py`: clean.
- Closed the canvas host root/default page seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_documents.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): `/__openclaw__/canvas/` now creates and serves the default OpenClaw Canvas test page from `data/canvas/index.html`, `/__openclaw__/canvas/index.html` resolves to the same file, and encoded traversal paths are rejected before filesystem access.
- Added focused root-host proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py): `test_create_app_serves_canvas_host_root_and_blocks_traversal` first failed with 404, then passed after root route binding.
- Verified the root-host seam with `pytest tests/test_gateway_canvas_documents.py::test_create_app_serves_canvas_host_root_and_blocks_traversal -q`: `1 passed`, `pytest tests/test_gateway_canvas_documents.py tests/test_gateway_canvas_render.py tests/test_app.py::test_control_chat_view_extracts_canvas_embed_previews -q`: `20 passed`, `ruff check src/openzues/services/gateway_canvas_documents.py src/openzues/app.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/services/gateway_canvas_a2ui.py src/openzues/app.py src/openzues/services/gateway_canvas_documents.py src/openzues/services/gateway_canvas_render.py src/openzues/services/control_chat.py`: clean.
- Closed the canvas live-reload broadcast delivery seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): `create_app()` now exposes `canvas_live_reload_hub`, canvas websocket clients subscribe to it, and `canvas/reload` events deliver the exact `reload` text frame expected by the A2UI/client-side reload hook.
- Closed the canvas filesystem watch/debounce seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_live_reload.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_live_reload.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): the app now snapshots `data/canvas`, ignores dotfiles and `node_modules`, coalesces file changes, and publishes `canvas/reload` into the canvas websocket hub.
- Closed the served canvas HTML live-reload hook seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_a2ui.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_a2ui.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): HTML assets under `/__openclaw__/canvas` now preserve their content while receiving the OpenClaw `OpenClaw.postMessage` / `openclawSendUserAction` bridge plus `/__openclaw__/ws` `location.reload()` hook.
- Closed the scoped canvas capability route seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): minted `node.canvas.capability.refresh` tokens can now authorize `/__openclaw__/cap/<token>/__openclaw__/canvas/...`, `/__openclaw__/cap/<token>/__openclaw__/a2ui/...`, and `/__openclaw__/cap/<token>/__openclaw__/ws`, while missing or expired tokens return an honest unauthorized boundary.
- Closed the A2UI JSONL validation seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): `node.invoke` now rejects malformed `canvas.a2ui.push` / `canvas.a2ui.pushJSONL` payloads before dispatch, requires a non-empty `params.jsonl`, enforces exactly one A2UI action key per JSONL object, and rejects mixed v0.8/v0.9 payloads.
- Closed the configured plugin node-host command allowlist seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\settings.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/settings.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_service.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_service.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): `gateway_node_allow_commands` and `gateway_node_deny_commands` now flow into node invoke and node scope/catalog logic so plugin-declared commands such as `browser.inspect` can be intentionally enabled without weakening defaults.
- Closed the allowlist-normalized node command catalog seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_service.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_service.py): `node.list`, `node.describe`, `/api/gateway/nodes`, `/api/gateway/nodes/{node_id}`, and new `node.pair.request` payloads now expose only commands that survive platform plus configured allow/deny policy instead of raw node declarations that `node.invoke` would reject.
- Added focused red-first proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) and HTTP coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py): iOS nodes declaring `canvas.snapshot`, `system.run`, and `browser.inspect` now advertise only `canvas.snapshot` unless the extra command is explicitly enabled.
- Verified the allowlist-normalized catalog seam with `pytest tests/test_gateway_node_methods.py::test_node_list_and_describe_expose_only_allowlisted_live_commands tests/test_gateway_node_methods.py::test_node_pair_request_records_only_allowlisted_commands tests/test_gateway_nodes_api.py::test_gateway_node_catalog_endpoint_exposes_only_allowlisted_live_commands -q`: `3 passed`, adjacent node catalog/pairing regression pack: `6 passed`, `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_node_service.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean, and `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_node_service.py`: clean.
- Closed the native browser command runtime seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): advertised `browser.open`, `browser.snapshot`, `browser.console`, and `browser.errors` commands now execute through an injectable/default `agent-browser` runtime instead of being catalog-only names, while missing runtime execution returns `UNAVAILABLE` / 503.
- Added method and HTTP proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the native browser runtime seam with `pytest tests/test_gateway_node_methods.py::test_browser_commands_dispatch_to_configured_runtime tests/test_gateway_node_methods.py::test_browser_commands_return_unavailable_when_runtime_is_missing tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_open_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `4 passed`, adjacent browser/commands pack: `7 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/app.py`: clean.
- Closed the `browser.status` gateway-method seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): `browser.status` now validates an empty payload, reuses the existing operator status service, returns only `browser_posture`, and keeps a truthful `UNAVAILABLE` / 503 boundary when the posture owner is not wired.
- Added method, HTTP, and operator-scope proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the `browser.status` seam with `pytest tests/test_gateway_node_methods.py::test_browser_status_returns_browser_posture_from_status_service tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_status_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `3 passed`, adjacent browser/commands/policy pack: `9 passed`, `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/app.py`: clean.
- Closed the `browser.verify` / `browser.doctor` gateway-method seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): `browser.verify` now runs a bounded live-browser verification through `agent-browser`, and `browser.doctor` returns the existing browser posture with optional verification rather than falling through as unsupported.
- Added method, HTTP, and operator-scope proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the `browser.verify` / `browser.doctor` seam with `pytest tests/test_gateway_node_methods.py::test_browser_verify_dispatches_to_configured_runtime tests/test_gateway_node_methods.py::test_browser_doctor_combines_posture_with_optional_verification tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_verify_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `4 passed`, adjacent browser/commands/policy pack: `12 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/app.py`: clean.
- Closed the `browser.tabs` command-breadth seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_commands.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_commands.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): `browser.tabs` is now advertised, classified as read-scope, dispatched through the gateway method layer, and backed by an `agent-browser tabs` runtime that accepts JSON or plain-text output.
- Added method, HTTP, catalog, and operator-scope proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the `browser.tabs` seam with `pytest tests/test_gateway_node_methods.py::test_commands_list_returns_bounded_native_operator_inventory tests/test_gateway_node_methods.py::test_browser_tabs_dispatches_to_configured_runtime tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_supports_commands_list tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_tabs_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `5 passed`, adjacent browser/commands/policy pack: `14 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py src/openzues/app.py`: clean.
- Closed the `browser.profiles` command-breadth seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_commands.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_commands.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): `browser.profiles` is now advertised, classified as read-scope, dispatched through the gateway method layer, and backed by an `agent-browser profiles` runtime that accepts JSON or plain-text output.
- Added method, HTTP, catalog, and operator-scope proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the `browser.profiles` seam with `pytest tests/test_gateway_node_methods.py::test_commands_list_returns_bounded_native_operator_inventory tests/test_gateway_node_methods.py::test_browser_profiles_dispatches_to_configured_runtime tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_supports_commands_list tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_profiles_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `5 passed`, adjacent browser/commands/policy pack: `16 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py src/openzues/app.py`: clean.
- Closed the `browser.screenshot` command-breadth seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_commands.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_commands.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): `browser.screenshot` is now advertised, classified as read-scope, dispatched through the gateway method layer, and backed by an `agent-browser screenshot` runtime that writes to a controlled temp artifact.
- Added method, HTTP, catalog, and operator-scope proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the `browser.screenshot` seam with `pytest tests/test_gateway_node_methods.py::test_commands_list_returns_bounded_native_operator_inventory tests/test_gateway_node_methods.py::test_browser_screenshot_dispatches_to_configured_runtime tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_supports_commands_list tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_screenshot_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `5 passed`, adjacent browser/commands/policy pack: `16 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py src/openzues/app.py`: clean.
- Closed the `browser.pdf` command-breadth seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_commands.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_commands.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): `browser.pdf` is now advertised, classified as read-scope, dispatched through the gateway method layer, and backed by an `agent-browser pdf` runtime that writes to a controlled temp artifact.
- Added method, HTTP, catalog, and operator-scope proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the `browser.pdf` seam with `pytest tests/test_gateway_node_methods.py::test_commands_list_returns_bounded_native_operator_inventory tests/test_gateway_node_methods.py::test_browser_pdf_dispatches_to_configured_runtime tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_supports_commands_list tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_pdf_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `5 passed`, adjacent browser/commands/policy pack: `18 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py src/openzues/app.py`: clean.
- Closed the `browser.navigate` command-breadth seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_commands.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_commands.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): `browser.navigate` is now advertised, classified as write-scope, dispatched through the gateway method layer, and backed by the active-session `agent-browser open <url>` navigation primitive.
- Added method, HTTP, catalog, and operator-scope proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the `browser.navigate` seam with `pytest tests/test_gateway_node_methods.py::test_commands_list_returns_bounded_native_operator_inventory tests/test_gateway_node_methods.py::test_browser_navigate_dispatches_to_configured_runtime tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_supports_commands_list tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_navigate_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `5 passed`, adjacent browser/commands/policy pack: `20 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py src/openzues/app.py`: clean.
- Closed the `browser.close` command-breadth seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_commands.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_commands.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): `browser.close` is now advertised, classified as write-scope, dispatched through the gateway method layer, and backed by the session/all-session `agent-browser close [--all]` runtime.
- Added method, HTTP, catalog, and operator-scope proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the `browser.close` seam with `pytest tests/test_gateway_node_methods.py::test_commands_list_returns_bounded_native_operator_inventory tests/test_gateway_node_methods.py::test_browser_close_dispatches_to_configured_runtime tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_supports_commands_list tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_close_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `5 passed`, adjacent browser/commands/policy pack: `22 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py src/openzues/app.py`: clean.
- Closed the first `browser.act` command-breadth seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_commands.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_commands.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): `browser.act` is now advertised, classified as write-scope, dispatched through the gateway method layer, and maps a bounded action subset into local `agent-browser` primitives.
- Added method, HTTP, catalog, mapper, and operator-scope proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the `browser.act` seam with `pytest tests/test_gateway_node_methods.py::test_commands_list_returns_bounded_native_operator_inventory tests/test_gateway_node_methods.py::test_browser_act_dispatches_to_configured_runtime tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_supports_commands_list tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_act_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `5 passed`, adjacent browser/commands/policy pack: `25 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py src/openzues/app.py`: clean.
- Closed the target-aware tab focus/close seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_commands.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_commands.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_method_policy.py): `browser.focus` is now advertised and write-scoped, and `browser.close` now accepts `targetId` for tab close while preserving session/all-session close.
- Added method, HTTP, catalog, and operator-scope proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_method_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_method_policy.py).
- Verified the target-aware tab seam with `pytest tests/test_gateway_node_methods.py::test_commands_list_returns_bounded_native_operator_inventory tests/test_gateway_node_methods.py::test_browser_close_dispatches_target_tab_to_configured_runtime tests/test_gateway_node_methods.py::test_browser_focus_dispatches_to_configured_runtime tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_supports_commands_list tests/test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_runs_browser_focus_runtime tests/test_gateway_method_policy.py::test_gateway_method_policy_mirrors_openclaw_operator_scope_groups -q`: `6 passed`, adjacent browser/commands/policy pack: `28 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py src/openzues/app.py`: clean.
- Closed the tab-open tracking seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_browser_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_browser_runtime.py): `browser.open` now uses `agent-browser tab new <url>` and parses returned target metadata, while `browser.navigate` remains the active-session navigation method.
- Added parser proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py).
- Verified the tab-open tracking seam with `pytest tests/test_gateway_node_methods.py::test_browser_tab_target_id_accepts_json_and_plain_output -q`: `1 passed`, adjacent browser/commands/policy pack: `30 passed`, `ruff check src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`: clean, and `mypy src/openzues/services/gateway_browser_runtime.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/gateway_commands.py src/openzues/app.py`: clean.
- Added focused broadcast proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py): `test_canvas_live_reload_broadcast_reaches_connected_websocket` first failed because no reload hub existed, then passed when the connected websocket received `reload`.
- Verified the broadcast seam with `pytest tests/test_gateway_canvas_documents.py::test_canvas_live_reload_broadcast_reaches_connected_websocket tests/test_gateway_canvas_documents.py::test_create_app_exposes_canvas_live_reload_websocket_path -q`: `2 passed`, `pytest tests/test_gateway_canvas_documents.py tests/test_gateway_canvas_render.py tests/test_app.py::test_control_chat_view_extracts_canvas_embed_previews -q`: `21 passed`, `ruff check src/openzues/app.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/services/gateway_canvas_a2ui.py src/openzues/app.py src/openzues/services/gateway_canvas_documents.py src/openzues/services/gateway_canvas_render.py src/openzues/services/control_chat.py`: clean.
- Closed the macOS `screen.snapshot` command-policy seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_command_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_command_policy.py): OpenZues now mirrors OpenClaw by allowing non-dangerous `screen.snapshot` for macOS nodes while keeping `screen.record` gated unless explicitly added through `allow_commands`.
- Added focused policy proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_command_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_command_policy.py).
- Verified the screen policy seam with `pytest tests/test_gateway_node_command_policy.py tests/test_gateway_node_registry.py::test_pull_pending_actions_filters_commands_not_allowlisted_for_platform -q`: `3 passed`, `ruff check src/openzues/services/gateway_node_command_policy.py tests/test_gateway_node_command_policy.py`: clean, and `mypy src/openzues/services/gateway_node_command_policy.py`: clean.
- Closed the first managed canvas document helper seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_documents.py): OpenZues now builds OpenClaw-shaped `/__openclaw__/canvas/documents/...` entry and asset URLs and resolves hosted canvas paths back into managed local storage while rejecting traversal document IDs and entrypoint segments.
- Added focused helper proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py).
- Verified the canvas helper seam with `pytest tests/test_gateway_canvas_documents.py -q`: `3 passed`, `ruff check src/openzues/services/gateway_canvas_documents.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/services/gateway_canvas_documents.py`: clean.
- Closed the inline canvas document materialization seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_documents.py): OpenZues can now materialize inline HTML documents under managed canvas storage, emit OpenClaw-shaped manifests and entry URLs, trim titles, and replace prior content for stable document IDs.
- Extended focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py).
- Verified the inline materialization seam with `pytest tests/test_gateway_canvas_documents.py -q`: `5 passed`, `ruff check src/openzues/services/gateway_canvas_documents.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/services/gateway_canvas_documents.py`: clean.
- Closed the path/PDF canvas document materialization seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_documents.py): workspace-relative path entrypoints now copy into managed canvas storage, and local PDF documents now get an OpenClaw-style `index.html` viewer wrapper while preserving the stable managed entry URL.
- Extended focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py).
- Verified the path/PDF materialization seam with `pytest tests/test_gateway_canvas_documents.py -q`: `7 passed`, `ruff check src/openzues/services/gateway_canvas_documents.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/services/gateway_canvas_documents.py`: clean.
- Closed the managed canvas asset copying/listing seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_documents.py): declared assets now copy from the workspace into managed canvas document storage, preserve optional content types in the manifest, and resolve to stable local paths plus hosted asset URLs with optional base URL prefixing.
- Extended focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py).
- Verified the asset seam with `pytest tests/test_gateway_canvas_documents.py -q`: `8 passed`, `ruff check src/openzues/services/gateway_canvas_documents.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/services/gateway_canvas_documents.py`: clean.
- Closed the remote PDF and image wrapper canvas document seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_documents.py): remote PDF URLs now materialize as managed `index.html` PDF viewer pages with `externalUrl`, and image path entrypoints now copy the source media and emit an OpenClaw-style centered image wrapper.
- Extended focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py).
- Verified the wrapper seam with `pytest tests/test_gateway_canvas_documents.py -q`: `10 passed`, `ruff check src/openzues/services/gateway_canvas_documents.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/services/gateway_canvas_documents.py`: clean.
- Closed the canvas document manifest loading and non-PDF URL pass-through seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_documents.py): saved manifests can now be loaded by document ID, missing manifests return `None`, and non-PDF URL entrypoints stay external while preserving `entryUrl` / `externalUrl`.
- Extended focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py).
- Verified the manifest seam with `pytest tests/test_gateway_canvas_documents.py -q`: `12 passed`, `ruff check src/openzues/services/gateway_canvas_documents.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/services/gateway_canvas_documents.py`: clean.
- Closed the FastAPI managed canvas document serving seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): `create_app()` now serves managed canvas document files at `/__openclaw__/canvas/documents/...` through the same traversal-safe resolver and returns 404 for invalid or missing paths.
- Extended end-to-end proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_documents.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_documents.py).
- Verified the app serving seam with `pytest tests/test_gateway_canvas_documents.py::test_create_app_serves_managed_canvas_document_paths tests/test_gateway_canvas_documents.py -q`: `13 passed`, `ruff check src/openzues/app.py src/openzues/services/gateway_canvas_documents.py tests/test_gateway_canvas_documents.py`: clean, and `mypy src/openzues/app.py src/openzues/services/gateway_canvas_documents.py`: clean.
- Closed the managed canvas media download bridge in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): Ops Mesh now resolves `/__openclaw__/canvas/documents/...` media paths against the OpenZues data dir before Slack native upload fetches, matching OpenClaw's local canvas-media resolution before provider upload.
- Wired `create_app()` to pass the active data dir into Ops Mesh for managed canvas media resolution in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py).
- Verified the media bridge with `pytest tests/test_ops_mesh.py::test_slack_media_download_resolves_managed_canvas_document_path tests/test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_slack_native_route -q`: `2 passed`, `pytest tests/test_gateway_canvas_documents.py::test_create_app_serves_managed_canvas_document_paths -q`: `1 passed`, `ruff check src/openzues/services/ops_mesh.py src/openzues/app.py tests/test_ops_mesh.py`: clean, and `mypy src/openzues/services/ops_mesh.py src/openzues/app.py`: clean.
- Closed the canvas embed shortcode parser seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_canvas_render.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_canvas_render.py): OpenZues can now strip valid Control UI `[embed ...]` shortcodes, build OpenClaw-shaped canvas preview payloads from `ref` or explicit `url`, clamp preferred heights, preserve invalid-target shortcodes, and ignore fenced code blocks.
- Added focused parser proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_canvas_render.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_canvas_render.py).
- Verified the parser seam with `pytest tests/test_gateway_canvas_render.py -q`: `3 passed`, `ruff check src/openzues/services/gateway_canvas_render.py tests/test_gateway_canvas_render.py`: clean, and `mypy src/openzues/services/gateway_canvas_render.py`: clean.
- Closed the provider-awareness part of the outbound queue head in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_outbound_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_outbound_runtime.py): the shared owner now accepts structured provider send and poll callbacks before falling back to the session-backed transcript deliverer.
- Routed direct gateway send and poll through those callbacks in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): provider send requests carry text, media URL, GIF, account, thread, session, and agent metadata; provider poll requests carry question, options, selection, duration, silent, anonymous, account, thread, and session metadata.
- Added focused regression proofs in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) for provider-backed direct send and poll transport while rechecking the session-backed owner fallback.
- Closed the first concrete adapter part of the outbound queue head in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): notification routes that explicitly subscribe to `gateway/send` or `gateway/poll` now act as route-backed provider adapters behind the shared runtime owner, while inventory-only routes keep falling back to the session-backed path.
- Updated the dashboard notification-route copy in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\templates\index.html`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/web/templates/index.html) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/web/static/app.js) so operators can discover the `gateway/send` and `gateway/poll` adapter events from the product surface.
- Added focused route-backed adapter proofs in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) for direct send and poll provider webhooks, including provider response `messageId` / `id` propagation.
- Closed the provider-result metadata part of the outbound queue head in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_outbound_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_outbound_runtime.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): route/provider send and poll results now preserve native IDs such as `chatId`, `channelId`, `toJid`, `conversationId`, and `pollId` through fresh responses, saved outbound delivery `route_scope`, and cached `idempotencyKey` responses.
- Extended the focused route-backed adapter proofs in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) so cached direct send/poll retries keep provider-backed transport metadata and native provider result fields without reposting.
- Closed the native adapter-binding part of the outbound queue head in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_outbound_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_outbound_runtime.py): the shared owner can now bind account/channel-specific native message and poll adapters ahead of generic provider callbacks and session fallback.
- Added focused native-adapter proofs in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) for Slack-style account-specific send and poll adapters, including native result propagation and `runtime="native-provider-backed"` delivery scope.
- Closed the first concrete provider-execution slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/schemas.py): notification routes can now be `kind="slack"`, `kind="telegram"`, or `kind="discord"` and deliver native provider-shaped direct send/poll payloads behind the same runtime owner instead of the generic webhook envelope.
- Slack routes use `chat.postMessage` for text/poll-style messages and Slack's external file upload flow for media URL sends; Telegram routes use Bot API `sendMessage` / `sendPhoto` / `sendPoll`; Discord routes use webhook execute payloads with native `content`, `embeds`, and `poll` bodies.
- Added focused concrete-provider proofs in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) for Slack media upload, Slack poll, Telegram photo send, Telegram poll, Discord embed send, and Discord poll, all preserving `runtime="native-provider-backed"` plus provider-native result metadata.
- Closed the WhatsApp/business-provider part of the outbound queue head in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/schemas.py): notification routes can now be `kind="whatsapp"` and direct WhatsApp targets use direct peer session keys instead of being misclassified as channel peers.
- WhatsApp native routes use the Cloud API messages endpoint for text messages, URL media sends, and interactive-button poll-style delivery while preserving message, contact/chat, channel, conversation, and poll identifiers through fresh/cached gateway responses plus saved delivery scope.
- Added focused WhatsApp proofs in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) for native text/media send and poll-style delivery, including Bearer-token handling and direct-peer session key preservation.
- Closed the first productization slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/cli.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\templates\index.html`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/web/templates/index.html), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/web/static/app.js): operators can now create native provider routes from the CLI with `routes create --kind slack|telegram|discord|whatsapp`, and the dashboard route form exposes provider kind selection instead of hardcoding every route to `webhook`.
- Native provider route setup now defaults missing event lists to `gateway/send,gateway/poll` on both CLI and dashboard paths, while generic webhooks keep mission/task notification defaults.
- Added a focused CLI proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_cli.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_cli.py) for `routes create --kind whatsapp` with conversation-target and secret preservation.
- Closed the first native route replay/test hardening slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): saved native routes for `gateway/send` and `gateway/poll` now dispatch through the provider-native Slack/Telegram/Discord/WhatsApp posting code instead of the generic webhook envelope.
- Native route test/replay now synthesizes bounded provider payloads from saved event summaries and conversation targets when a saved route test does not already include `message`, `question`, `options`, or `to`.
- Added a focused Ops Mesh proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) showing `test_notification_route` for a Slack native route posts `chat.postMessage`, stores the provider message id, and records `runtime="native-provider-backed"` plus provider result metadata.
- Closed the Telegram multi-media file hardening slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): Telegram native sends now use Bot API `sendMediaGroup` when more than one media URL is present instead of silently sending only the first photo.
- Telegram list-shaped `sendMediaGroup` results now preserve the first message id as the delivery message id and collect provider media IDs from each returned photo message.
- Added a focused Telegram media-group proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) for two-photo media sends, caption placement on the first media item, and saved provider media IDs.
- Closed the WhatsApp multi-media fallback slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): WhatsApp native sends now split multiple media URLs into multiple Cloud API image messages, captioning the first image and preserving every returned message id as `mediaIds`.
- Added a focused WhatsApp media proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) for two-image sends, Bearer-token reuse, and saved provider media IDs.
- Closed the WhatsApp reply/document payload slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): WhatsApp Cloud API direct sends now preserve `replyToId` as `context.message_id` and send forced-document media through `type="document"` / `document.link` while keeping caption text and saved provider result metadata.
- Added a focused WhatsApp reply-document proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) covering `reply_to_id`, `force_document`, Bearer-token reuse, and saved delivery payload metadata.
- Closed the WhatsApp GIF/video payload slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): WhatsApp Cloud API direct sends now map `gifPlayback=true` media sends to `type="video"` / `video.link`, with `forceDocument=true` still taking precedence.
- Added a focused WhatsApp GIF/video proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) covering the native provider payload, caption settings, Bearer-token reuse, and saved `gifPlayback` event metadata.
- Closed the provider failure-detail polish slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): HTTP provider error bodies are now parsed and included in webhook/provider upload error messages instead of reporting only the status code.
- Added a focused HTTP-error proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) showing a provider JSON body such as `{"error":"channel_not_found"}` surfaces as `Webhook returned 400: channel_not_found`.
- Verified this provider-runtime slice with:
  - `.\.venv\Scripts\ruff.exe check src/openzues/schemas.py src/openzues/services/gateway_outbound_runtime.py src/openzues/services/ops_mesh.py tests/test_ops_mesh.py`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_ops_mesh.py -k "slack_native_route or telegram_native_route or discord_native_route or whatsapp_native_route or native_adapter_binding or uses_gateway_route_adapter" --basetemp .codex-tmp\pytest-native-provider-runtime`: `12 passed`
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m mypy src/openzues/schemas.py src/openzues/services/gateway_outbound_runtime.py src/openzues/services/ops_mesh.py`: clean
  - `.\.venv\Scripts\ruff.exe check src/openzues/cli.py tests/test_cli.py`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_cli.py -k "routes_create_command_productizes_native_provider_routes" --basetemp .codex-tmp\pytest-cli-route-create`: `1 passed`
  - `node --check src/openzues/web/static/app.js`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m mypy src/openzues/cli.py`: clean
  - `.\.venv\Scripts\ruff.exe check src/openzues/services/ops_mesh.py tests/test_ops_mesh.py`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_ops_mesh.py -k "tests_slack_native_route or slack_native_route or telegram_native_route or discord_native_route or whatsapp_native_route or native_adapter_binding or uses_gateway_route_adapter" --basetemp .codex-tmp\pytest-native-route-test`: `13 passed`
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m mypy src/openzues/services/ops_mesh.py`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_ops_mesh.py -k "telegram_media_group or telegram_native_route or tests_slack_native_route or native_adapter_binding or uses_gateway_route_adapter" --basetemp .codex-tmp\pytest-telegram-media-group`: `8 passed`
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_ops_mesh.py -k "whatsapp_media or whatsapp_native_route or telegram_media_group" --basetemp .codex-tmp\pytest-whatsapp-media`: `4 passed`
  - `python -m pytest tests\test_ops_mesh.py -q -k "preserves_whatsapp_reply_document"`: `1 passed`
  - `python -m pytest tests\test_ops_mesh.py -q -k "whatsapp_native_route or whatsapp_media or preserves_whatsapp_reply_document or splits_whatsapp_media"`: `4 passed`
  - `python -m pytest tests\test_ops_mesh.py -q -k "telegram_native_route or discord_native_route or send_direct_channel_message_uses_whatsapp_native_route or preserves_whatsapp_reply_document"`: `6 passed`
  - `python -m pytest tests\test_ops_mesh.py -q -k "whatsapp_gif_video_payload"`: `1 passed`
  - `python -m pytest tests\test_ops_mesh.py -q -k "whatsapp_gif_video_payload or preserves_whatsapp_reply_document or splits_whatsapp_media or whatsapp_native_route or whatsapp_media"`: `5 passed`
  - `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`: clean
  - `mypy src\openzues\services\ops_mesh.py`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_ops_mesh.py -k "post_json_webhook_includes_provider_http_error_body or whatsapp_media or telegram_media_group" --basetemp .codex-tmp\pytest-webhook-error`: `3 passed`
- Queue head narrowed after this run: provider-shaped runtime callbacks, route-backed gateway provider adapters, provider-result metadata, native adapter binding, native Slack/Telegram/Discord/WhatsApp provider execution, basic CLI/dashboard setup, native route replay/test dispatch, Telegram multi-media sends, WhatsApp multi-media fallbacks, and provider HTTP failure detail are now real. No smaller provider-runtime blocker remains in this queue; the next move is a final adjacent boundary sweep before moving to the next OpenClaw feature family.
- Closed the final provider boundary sweep in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_outbound_runtime.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_outbound_runtime.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): cron failure direct-delivery branches now require a session-backed deliverer instead of treating provider-backed `gateway/send` route adapters as live cron announce delivery, and route-less webhook replay now distinguishes true ad-hoc webhook rows from notification-route rows that lost their `route_id`.
- Verified the final provider boundary sweep with `tests/test_ops_mesh.py`: `88 passed`, and `tests/test_cli.py`: `89 passed`.
- Closed the adjacent gateway node/session sweep in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_command_policy.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_command_policy.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_service.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_service.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\control_chat.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/control_chat.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): desktop nodes now get system-command pending-action pulls, catalog views preserve explicit empty live command lists, existing silent scope-upgrade requests do not drift on read, main-agent wake targeting uses session defaults, immediate wake retry recovers after submit failure, and app startup tolerates fake Ops Mesh services without outbound runtime attributes.
- Verified the adjacent sweep with `ruff check src tests`: clean, `mypy src`: clean, `tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: `746 passed`, and `tests/test_gateway_logs.py tests/test_gateway_models.py tests/test_gateway_node_methods.py tests/test_gateway_node_pairing_refresh.py tests/test_gateway_nodes_api.py tests/test_gateway_system_presence.py`: `781 passed`.
- Closed the first browser/canvas/nodes/voice queue-head slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_registry.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_registry.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): connected nodes can now subscribe/unsubscribe to session-scoped downstream events through upstream-shaped `node.event` `chat.subscribe` / `chat.unsubscribe`, and disconnects clean up node session subscriptions.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing a subscribed node receives a routed `chat` payload and stops receiving it after `chat.unsubscribe`.
- Verified the node subscription slice with `ruff check src/openzues/services/gateway_node_registry.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean, `mypy src/openzues/services/gateway_node_registry.py src/openzues/services/gateway_node_methods.py`: clean, and `tests/test_gateway_node_registry.py` plus the focused node.event tests: `19 passed`.
- Closed the next node-event slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): `exec.started`, `exec.finished`, and `exec.denied` node events now format upstream-shaped system notifications and queue them through `GatewayWakeService` as `next-heartbeat` `node.exec` wake requests scoped to the reported session key.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing `exec.finished` creates both the raw `node.event` record and the derived session-scoped `system-event` / wake request.
- Verified the exec node-event slice with `ruff check src/openzues/services/gateway_node_registry.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean, `mypy src/openzues/services/gateway_node_registry.py src/openzues/services/gateway_node_methods.py`: clean, and `tests/test_gateway_node_registry.py` plus focused node.event tests: `20 passed`.
- Closed the notification node-event slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): `notifications.changed` posted/removed payloads now format OpenClaw-style notification summaries and queue `next-heartbeat` wakes with `reason="notifications-event"` scoped to the reported session key.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing posted notification events create both the raw `node.event` record and the derived session-scoped `system-event` / wake request.
- Verified the notification node-event slice with `ruff check src/openzues/services/gateway_node_registry.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean, `mypy src/openzues/services/gateway_node_registry.py src/openzues/services/gateway_node_methods.py`: clean, and `tests/test_gateway_node_registry.py` plus focused node.event tests: `21 passed`.
- Closed the voice transcript node-event slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): `voice.transcript` now routes non-empty transcript text into the existing chat runtime with `thinking="low"`, `deliver=False`, and a stable `node-voice-*` idempotency key derived from upstream event identifiers or transcript text.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing a node voice transcript calls the chat runtime with the expected session, message, thinking, delivery, and idempotency semantics.
- Verified the voice transcript slice with `ruff check src/openzues/services/gateway_node_registry.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean, `mypy src/openzues/services/gateway_node_registry.py src/openzues/services/gateway_node_methods.py`: clean, and `tests/test_gateway_node_registry.py` plus focused node.event tests: `22 passed`.
- Closed the text `agent.request` node-event slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): node deep-link requests now route non-empty messages into the existing chat runtime, preserving explicit `key` as the idempotency key and mapping `thinking`, `deliver`, and `timeoutSeconds` into local chat-send arguments.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing a node `agent.request` message reaches the chat runtime with the expected session, message, idempotency, thinking, delivery, and timeout semantics.
- Verified the agent-request slice with `ruff check src/openzues/services/gateway_node_registry.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean, `mypy src/openzues/services/gateway_node_registry.py src/openzues/services/gateway_node_methods.py`: clean, and `tests/test_gateway_node_registry.py` plus focused node.event tests: `23 passed`.
- Closed the APNS registration boundary in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): `push.test` now recognizes valid recorded `push.apns.register` node events instead of falsely reporting that the node has no APNS registration.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing a node-recorded direct APNS registration changes `push.test` to the truthful `UNAVAILABLE` sender-runtime boundary while preserving the older missing-registration error for unregistered nodes.
- Verified the APNS registration boundary with `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean, `PYTHONPATH=src;.venv\Lib\site-packages python -m mypy src/openzues/services/gateway_node_methods.py`: clean, and focused APNS plus node-event regression tests: `8 passed`.
- Closed the voice transcript near-duplicate seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): repeated `voice.transcript` events with the same session/fingerprint inside the upstream 1500ms window no longer double-submit chat work.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing duplicate transcript events within the dedupe window produce only one chat-send call.
- Verified the voice dedupe seam with `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean, `PYTHONPATH=src;.venv\Lib\site-packages python -m mypy src/openzues/services/gateway_node_methods.py`: clean, and focused node-event/APNS regression tests: `9 passed`.
- Closed the exec-finished duplicate seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): repeated `exec.finished` events for the same session/run id inside the upstream 10-minute window no longer emit duplicate derived system notifications or wake requests.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing duplicate raw exec events are still recorded while the derived `system-event` / wake path only fires once.
- Verified the exec dedupe seam with `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean, `PYTHONPATH=src;.venv\Lib\site-packages python -m mypy src/openzues/services/gateway_node_methods.py`: clean, and focused node-event/APNS regression tests: `10 passed`.
- Closed the injected APNS sender seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): after a valid recorded registration, `push.test` now calls a provided APNS sender runtime with node id, registration, title/body, and environment override instead of only reporting unavailable.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing registered nodes can complete `push.test` through the injected sender while the default no-sender path remains the honest unavailable boundary.
- Verified the APNS sender seam with `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean, `PYTHONPATH=src;.venv\Lib\site-packages python -m mypy src/openzues/services/gateway_node_methods.py`: clean, and focused node-event/APNS regression tests: `11 passed`.
- Closed the route-safe `agent.request` delivery seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): node deep-links now only forward `deliver=True` when a known channel and non-empty target are present, and explicit route hints are passed through the chat runtime hook.
- Added focused proofs in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing explicit `channel` / `to` hints remain deliverable while a deliver request without a route is downgraded to `deliver=False`.
- Verified the route-safe agent-request seam with `ruff check src/openzues/services/gateway_node_methods.py src/openzues/app.py tests/test_gateway_node_methods.py`: clean, `PYTHONPATH=src;.venv\Lib\site-packages python -m mypy src/openzues/services/gateway_node_methods.py src/openzues/app.py`: clean, and focused node-event/APNS regression tests: `12 passed`.
- Closed the `agent.request` receipt acknowledgement seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): node deep-links with `receipt=true` and a resolved route now send a bounded receipt acknowledgement through the existing direct channel send runtime.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing receipt text, route, session key, and stable receipt idempotency reach the channel message service while the agent request still enters chat.
- Verified the receipt seam with `ruff check src/openzues/services/gateway_node_methods.py src/openzues/app.py tests/test_gateway_node_methods.py`: clean, `PYTHONPATH=src;.venv\Lib\site-packages python -m mypy src/openzues/services/gateway_node_methods.py src/openzues/app.py`: clean, and focused node-event/APNS regression tests: `13 passed`.
- Closed the honest `agent.request` attachment boundary in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): effective node attachments now return the same control-chat attachment-runtime unavailable error instead of silently dropping attachment context and launching text-only work.
- Added a focused proof in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) showing effective image attachments on `agent.request` do not call chat and produce the explicit unavailable boundary.
- Verified the attachment-boundary seam with `ruff check src/openzues/services/gateway_node_methods.py src/openzues/app.py tests/test_gateway_node_methods.py`: clean, `PYTHONPATH=src;.venv\Lib\site-packages python -m mypy src/openzues/services/gateway_node_methods.py src/openzues/app.py`: clean, and focused node-event/APNS regression tests: `14 passed`.
- Reverified the whole gateway node method surface after the node-event push/agent changes with `PYTHONPATH=src;.venv\Lib\site-packages python -m pytest tests/test_gateway_node_methods.py -q --tb=short`: `389 passed`.
- Re-read the adjacent upstream model/session source-of-truth in `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods\models.ts`, `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-model-catalog.ts`, and `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\sessions-resolve.ts`: OpenClaw filters gateway catalogs through the allowed model set and `spawnedBy` visibility filters do not surface global or `unknown` sessions to spawned-session lookups.
- Integrated the adjacent hot dirty gateway model/session/config-schema shard instead of widening the still-blocked provider-runtime seam.
- Fixed one verification-found gateway model regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_models.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_models.py): `agents.defaults.models` allowlists now filter the gateway catalog like OpenClaw, and synthetic configured-only allowlist entries stay visible even when no live instance model row advertises them yet because allowlist dedupe now keys off the emitted catalog instead of all known config metadata.
- Fixed one gateway session visibility regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_sessions.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_sessions.py): `spawnedBy`-filtered key and snapshot lookups now reject global plus `unknown` sessions instead of treating metadata-only `spawnedBy` matches as visible spawned sessions.
- Reverified the adjacent config-schema guard in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_config_schema.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_config_schema.py): long but otherwise valid lookup paths now survive normalization while indexed tuple-item paths plus forbidden-segment guards stay intact.
- Verified this shard with:
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_gateway_models.py -q -k "allowlist or object_shaped or configured_aliases_for_primary_and_fallbacks" --basetemp .codex-tmp/gateway-models-allowlist-rerun-2`: `4 passed`
  - direct exact-function execution against repo-local proof roots for eight focused `gateway_sessions` proofs:
    - `test_resolve_key_session_id_prefilters_spawned_by_before_duplicate_preference`
    - `test_resolve_key_by_key_accepts_parent_session_key_for_spawned_by_filter`
    - `test_resolve_key_by_key_prefers_latest_controller_owner_over_stale_spawned_by`
    - `test_owner_alias_metadata_is_canonicalized_for_filters_snapshot_and_child_sessions`
    - `test_resolve_key_requires_primary_selector_even_with_spawned_by_filter`
    - `test_resolve_key_key_lookup_rejects_global_session_for_spawned_by_filter_like_openclaw`
    - `test_resolve_key_label_lookup_accepts_parent_session_key_for_spawned_by_filter`
    - `test_build_snapshot_spawned_by_filter_excludes_global_and_unknown_sessions_like_openclaw`
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_gateway_node_methods.py -q -k "config_schema_lookup_accepts_punctuation_rich_path_segments or config_schema_lookup_accepts_long_valid_paths or config_schema_lookup_supports_array_paths_and_rejects_invalid_lookup_paths" --basetemp .codex-tmp/gateway-config-schema-paths`: `3 passed`
  - `.\.venv\Scripts\ruff.exe check --extend-ignore E501 src/openzues/services/gateway_models.py src/openzues/services/gateway_sessions.py src/openzues/services/gateway_config_schema.py tests/test_gateway_models.py tests/test_gateway_sessions.py tests/test_gateway_node_methods.py`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m mypy src/openzues/services/gateway_models.py src/openzues/services/gateway_sessions.py src/openzues/services/gateway_config_schema.py`: clean
- Queue head unchanged after this run: the provider-runtime seam remains the next honest move, and this hot gateway model/session/config-schema shard is now ledgered so it does not create a shorter cross-cutting detour ahead of that owner gap.
- Re-read the upstream outbound source-of-truth in `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods\send.ts`, `C:\Users\skull\OneDrive\Documents\openclaw-main\src\infra\outbound\outbound-send-service.ts`, and `C:\Users\skull\OneDrive\Documents\openclaw-main\src\cli\send-runtime\channel-outbound-send.ts` plus the upstream node guard rails in `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods\nodes.ts`: the provider-runtime queue head is still real, and OpenClaw also rejects `system.execApprovals.*` plus persistent browser-profile mutations through `browser.proxy` on the `node.invoke` boundary.
- Integrated the adjacent hot dirty gateway bootstrap/node/config-schema shard instead of widening that blocked provider-runtime seam.
- Fixed one bootstrap readiness regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_bootstrap.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_bootstrap.py): broken saved lane/workspace references now mark bootstrap `degraded` even when no other launch prerequisite is currently ready, so missing saved defaults no longer under-report as merely staged.
- Fixed one config-schema lookup gap in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_config_schema.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_config_schema.py): over-strict path character filtering is gone, so punctuation-rich plugin entry ids still resolve through `config.schema.lookup` while indexed tuple-item lookups such as `pair.1` remain supported on both method and HTTP surfaces.
- Fixed one `node.invoke` guard-rail gap in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): the gateway now rejects `system.execApprovals.*` and persistent browser-profile mutations through `browser.proxy` before any wake attempt, matching the upstream OpenClaw boundary instead of letting those calls drift into generic node execution.
- Reverified the adjacent hot node/control-plane shards already living in the dirty tree:
  - bearer `Authorization` still wins over the legacy `X-OpenClaw-Token` fallback when both are present
  - pending-work wakes and `node.invoke` waits still hold until reconnect on both the method and managed HTTP surfaces
  - commandless paired-node reconnects still stage silent scope-upgrade requests while approved commands stay pinned
- Verified this shard with:
  - direct exact-function execution against repo-local proof roots for 20 focused proofs:
    - bootstrap degraded-state proofs for missing saved lane plus missing saved remote workspace
    - bearer precedence, indexed tuple-item config lookup, and punctuation-rich config lookup proofs
    - method plus HTTP pending-work reconnect waits
    - method plus HTTP commandless paired-node reconnect staging
    - method plus HTTP `node.invoke` rejection of `system.execApprovals.*`
    - three method plus three HTTP `browser.proxy` persistent-mutation rejection proofs
  - `.\.venv\Scripts\ruff.exe check --extend-ignore E501 src/openzues/services/gateway_bootstrap.py src/openzues/services/gateway_config_schema.py src/openzues/services/gateway_node_methods.py tests/test_gateway_bootstrap.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m mypy src/openzues/services/gateway_bootstrap.py src/openzues/services/gateway_config_schema.py src/openzues/services/gateway_node_methods.py`: clean
- Queue head unchanged after this run: the provider-runtime seam remains the next honest move, and this hot gateway bootstrap/node/config-schema shard is now ledgered so it does not create a shorter cross-cutting detour ahead of that owner gap.
- Re-read the upstream outbound source-of-truth in `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods\send.ts`, `C:\Users\skull\OneDrive\Documents\openclaw-main\src\infra\outbound\outbound-send-service.ts`, and `C:\Users\skull\OneDrive\Documents\openclaw-main\src\cli\send-runtime\channel-outbound-send.ts` plus the local `src/openzues/services/gateway_outbound_runtime.py`: the queue head is still real because OpenZues still has no provider-backed channel adapter or runtime-manager target to wire behind `GatewayOutboundRuntimeService`.
- Integrated the adjacent hot dirty gateway/setup/session/model/node/wizard shard instead of widening that blocked provider-runtime seam.
- Fixed one verification-found wizard regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_wizard.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_wizard.py): answering the optional remote saved-lane step now marks that optional field complete and advances to `task_name` instead of re-emitting the same `instance_id` selector on the next step.
- Fixed one gateway model regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_models.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_models.py): object-shaped `config.model = { primary, fallbacks }` entries now synthesize the configured primary model, deduped fallback models, and the default reasoning effort the same way string-valued configs already did.
- Fixed one gateway session regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_sessions.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_sessions.py): snapshot `limit` and `active_minutes` now normalize to a positive integer floor like OpenClaw, and owner-session aliases from `controllerSessionKey` / `requesterSessionKey` / `spawnedBy` / `parentSessionKey` now canonicalize across filters, payloads, and child-session discovery instead of diverging on raw alias strings.
- Fixed one node pending-work parity gap in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_service.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_service.py): saved-lane and managed-lane pending-work wakes now wait through reconnect before returning, so `wakeTriggered` no longer resolves before the node actually shows back up in registry state.
- Fixed one setup/onboarding regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\setup.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/setup.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\web\static\app.js`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/web/static/app.js), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_wizard.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_wizard.py): switching a saved local draft to remote now clears the stale pinned local lane hint before bootstrap/handoff, remote wizard sessions keep `instance_mode="existing"` honest, and the optional saved-lane selector can pin or skip the first remote launch without getting stuck.
- Reverified the hot node/control-plane shard already living in the dirty tree:
  - commandless paired-node reconnects now stage silent scope-upgrade requests while `node.list`, `node.describe`, and `node.pair.list` keep approved commands pinned until approval
  - `config.schema.lookup` now resolves indexed tuple-item schemas on both the method and HTTP API surfaces
  - bearer `Authorization` now wins over the legacy `X-OpenClaw-Token` fallback when both are present
- Verified this shard with:
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_gateway_models.py -q`: `9 passed`
  - direct exact-function execution against repo-local proof roots for the six session filter clamp cases, owner-alias session proofs, method plus HTTP pending-work reconnect proofs, commandless paired-node reconnect staging, indexed tuple-item config schema lookup, the full remote wizard saved-lane progression, and the remote-switch bootstrap proof: all passed
  - `node tests/test_onboarding_wizard_reload.test.js`: six onboarding reload proofs passed, including stale lane-hint clearing on local-to-remote switches
  - `.\.venv\Scripts\ruff.exe check --extend-ignore E501 src/openzues/services/gateway_models.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_node_service.py src/openzues/services/gateway_sessions.py src/openzues/services/gateway_wizard.py src/openzues/services/setup.py tests/test_app.py tests/test_gateway_models.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_sessions.py tests/test_gateway_wizard.py`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m mypy src/openzues/services/gateway_models.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_node_service.py src/openzues/services/gateway_sessions.py src/openzues/services/gateway_wizard.py src/openzues/services/setup.py`: clean
- Queue head unchanged after this run: the provider-runtime seam remains the next honest move, and this hot gateway/setup/session/model/node/wizard shard is now ledgered so it does not create a shorter cross-cutting detour ahead of that owner gap.
- Integrated the hot gateway capability/bootstrap/logs/wizard shard already active in the dirty tree without widening the still-open provider-runtime queue head.
- Fixed one real regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_capability.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_capability.py): wrapped or list-style live MCP tool catalogs now give unscoped plugin tool names a capability-only fallback of `operator.write`, so bare string entries like `browser.request` stay counted and classified in the gateway capability scope summary while reserved `wizard.*` methods still coerce to `operator.admin` and explicit built-in methods keep their canonical scopes.
- Added focused regression coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_capability.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_capability.py) for:
  - wrapped inner string tool catalogs keeping `tool_count`, `classified_method_count`, and scope groups aligned
  - wrapped MCP status refresh payloads preserving callable tool names through array-like wrappers without regressing the cached fallback path
- Verified the capability/control-plane shard with:
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_gateway_capability.py -q`: `15 passed`
  - direct app proof against repo-local paths for `/api/gateway/capability` plus `/api/dashboard`: passed with `classified_method_count == 3` on the mixed scoped plus bare-string plugin tool catalog
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_gateway_wizard.py -q`: `7 passed`
  - direct exact-function execution against repo-local proof paths:
    - `test_get_view_marks_remote_bootstrap_staged_without_enabled_ingress`
    - `test_get_view_marks_remote_bootstrap_staged_when_saved_task_is_disabled`
    - `test_gateway_logs_tail_reads_configured_log_file_path_even_when_other_logs_are_newer`
    - `test_gateway_logs_tail_falls_back_to_latest_rolling_log_when_configured_daily_file_is_missing`
  - `.\.venv\Scripts\ruff.exe check src/openzues/services/gateway_capability.py tests/test_gateway_capability.py`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m mypy src/openzues/services/gateway_capability.py`: clean
- Queue head unchanged after this run: the checked upstream outbound/runtime files still expect provider-native delivery behind channel outbound adapters, while the local tree still ends at the shared session-backed owner, so there is no honest provider-runtime cutover yet to land behind `GatewayOutboundRuntimeService`.
- Re-read the upstream outbound source-of-truth in `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods\send.ts`, `C:\Users\skull\OneDrive\Documents\openclaw-main\src\infra\outbound\outbound-send-service.ts`, and `C:\Users\skull\OneDrive\Documents\openclaw-main\src\cli\send-runtime\channel-outbound-send.ts`, then landed one shared outbound runtime owner in `src/openzues/services/gateway_outbound_runtime.py`, `src/openzues/services/ops_mesh.py`, and `src/openzues/app.py`: direct gateway send/poll, explicit cron announce/session delivery, and saved session-like outbound delivery replays now all resolve through one explicit `GatewayOutboundRuntimeService` instead of calling the control-chat session appender ad hoc.
- Added focused proof coverage in `tests/test_ops_mesh.py` for:
  - direct gateway send succeeding when only the shared outbound runtime owner is wired
  - saved failed announce delivery replay succeeding through that same runtime owner without falling back to the legacy raw session callback
- Verified the new owner path with:
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_ops_mesh.py -q -k "runtime_owner or send_direct_channel_message_uses_known_channel_default_account or replay_outbound_deliveries_retries_saved_failed_announce_delivery or send_direct_channel_poll_records_session_backed_delivery" --basetemp .codex-tmp/ops-mesh-runtime-owner-rerun`: `5 passed`
  - direct exact-function execution of `test_send_endpoint_delivers_channel_target_message_and_records_outbound_delivery` and `test_poll_endpoint_delivers_channel_target_poll_and_records_outbound_delivery` against repo-local temp paths after the known Windows/OneDrive pytest cleanup failure: passed
  - `.\.venv\Scripts\ruff.exe check src/openzues/services/gateway_outbound_runtime.py src/openzues/services/ops_mesh.py src/openzues/app.py tests/test_ops_mesh.py`: clean
  - `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m mypy src/openzues/services/gateway_outbound_runtime.py src/openzues/services/ops_mesh.py src/openzues/app.py`: clean
- Reverified the hot node/pairing shard against `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods\nodes.ts` and `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\node-catalog.ts`, then fixed one regression beneath the already-landed dirty-tree scope-upgrade work in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py): paired-node catalogs now keep approved commands pinned while silent scope-upgrade requests surface widened live commands, and managed offline `node.invoke` calls now preserve the truthful `503 NOT_CONNECTED` boundary after a failed wake/connect attempt instead of leaking a platform allowlist `400`.
- Added focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) for:
  - offline managed-lane `node.invoke` keeping the `NOT_CONNECTED` boundary even when the platform allowlist would reject the command first
- Reverified the hot node/pairing shard by direct exact-function execution against repo-local temp paths for:
  - `test_pair_request_refresh_preserves_silent_when_omitted`
  - `test_pair_request_refresh_clears_silent_when_false`
  - `test_node_list_stages_silent_scope_upgrade_request_for_paired_command_expansion`
  - `test_node_invoke_raises_scope_upgrade_pending_approval_for_unapproved_live_command`
  - `test_node_invoke_surfaces_not_connected_wake_metadata_when_saved_lane_wake_fails`
  - `test_node_invoke_keeps_not_connected_boundary_for_offline_managed_lane`
  - `test_gateway_nodes_endpoints_stage_silent_scope_upgrade_request_for_paired_command_expansion`
  - `test_gateway_node_method_call_endpoint_blocks_scope_upgrade_until_repair_request_is_approved`
  - `test_gateway_node_method_call_endpoint_keeps_not_connected_boundary_when_managed_wake_fails`
- Verified the touched gateway node-method files with `.\.venv\Scripts\ruff.exe check --extend-ignore E501 src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean.
- Verified the touched gateway node-method types with `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m mypy src/openzues/services/gateway_node_methods.py`: clean.
- Reverified the still-open queue head against `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods\send.ts`, `C:\Users\skull\OneDrive\Documents\openclaw-main\src\infra\outbound\outbound-send-service.ts`, `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\protocol\schema\agent.ts`, and the local bridge candidates in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_registry.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_registry.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\manager.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/manager.py): OpenZues does have a generic `node.invoke` request/result seam plus remembered node `commands`/`caps`, but neither the checked local tree nor the upstream gateway/runtime surfaces currently advertise a provider-owned outbound `send` / `poll` / `announce` command or runtime-manager call target, so the remaining gap is missing outbound runtime ownership rather than another local validation, retry, or saved-read-model seam.
- Reverified the bounded local owner still holds with `PYTHONPATH=src;.venv\Lib\site-packages C:\Users\skull\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_ops_mesh.py -q -k "test_ops_mesh_service_send_direct_channel_message_dedupes_idempotent_retries_while_inflight or test_ops_mesh_service_send_direct_channel_poll_records_session_backed_delivery" --basetemp tmp_orchestrator_pytest/provider-runtime-doc-pass-ops`: `2 passed`, plus direct invocation of `test_send_endpoint_reuses_idempotent_channel_target_delivery` and `test_poll_endpoint_delivers_channel_target_poll_and_records_outbound_delivery` against repo-local temp paths after the known Windows/OneDrive pytest cleanup issue.
- Tightened one smaller transport-read-model seam under the still-open provider-runtime queue head in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\schemas.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/schemas.py): fresh `gateway.send` / `gateway.poll` responses, cached idempotent direct-delivery retries, and saved outbound delivery views now all surface the same honest session-backed transport envelope plus `runId` / `channel` instead of only mirrored `sessionKey` / `messageId`.
- Added focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py) for:
  - direct send/poll runtime responses carrying honest session-backed transport metadata
  - cached idempotent direct-send/direct-poll retries rebuilding the same `runId` / `channel` / transport contract from saved outbound rows
  - gateway send/poll API responses preserving that same transport contract across text, media, thread-target, duration, anonymous, and blank-account slices
- Closed one smaller retry-semantics seam under the still-open provider-runtime queue head in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\database.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/database.py): the shared session-backed direct send/poll owner now persists request `idempotencyKey` plus mirrored message id on outbound deliveries, dedupes in-flight retries, and reuses completed rows so repeated gateway retries do not duplicate outbound delivery history or mirrored assistant session messages.
- Added focused proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py) for:
  - in-flight idempotent direct-send retries collapsing onto one shared delivery task
  - completed idempotent direct-poll retries reusing the stored delivery row
  - end-to-end `gateway.send` duplicate retries reusing the same local response without writing a second outbound row or assistant message
- Closed one cross-cutting saved direct-poll replay seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py) with focused coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py): saved failed `gateway/poll` deliveries now rebuild the full bounded local poll transcript with options plus settings during replay instead of collapsing to the question-only summary while riding the shared announce/session replay owner.
- Closed the hot session archive/compaction inventory surfacing seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_sessions.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_sessions.py): session snapshots now stop seeding the empty fallback main control-chat row when only mission-backed or transcript-backed sessions have persisted evidence, while message and changed-event payloads still surface the latest compaction checkpoint metadata for the real session.
- Reverified the landed session/heartbeat/presence/bootstrap/pairing shard against the local OpenClaw sources of truth in `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\sessions-resolve.ts`, `C:\Users\skull\OneDrive\Documents\openclaw-main\src\infra\heartbeat-events.ts`, `C:\Users\skull\OneDrive\Documents\openclaw-main\src\infra\system-presence.ts`, `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\client-bootstrap.ts`, and `C:\Users\skull\OneDrive\Documents\openclaw-main\src\infra\pairing-pending.ts`: the dirty shard now holds sessionId/key/label resolution parity, compaction checkpoint metadata surfacing, OpenClaw-shaped last-heartbeat payload promotion, self-presence host/ip/version/platform/device metadata, bootstrap runtime inventory/auth readiness slices, and pairing refresh preservation of pending `silent` state.
- Closed one cross-cutting read-model regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\database.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/database.py) with focused coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_database.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_database.py): task blueprint reads now preserve authoritative row-level columns over duplicated payload JSON, so disabled recurring tasks no longer appear launch-ready in gateway bootstrap and the same `enabled` truth now flows consistently into setup, onboarding, cron, Ops Mesh, launch routing, Hermes platform, and remote-ops readers that reuse the shared task owner.
- Reverified the hot session-resolve parity slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_sessions.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_sessions.py) against `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\sessions-resolve.ts`: OpenZues now holds the OpenClaw-style selector contract for mutually exclusive `key` / `sessionId` / `label`, required nonblank selector presence, trimmed label lookup, visibility-aware metadata lookup, and ambiguous-label errors.
- Reverified the hot gateway bootstrap/log/wizard/presence/node payload shards without widening their write sets:
  - bootstrap stays staged when the saved recurring task is disabled or the saved remote ingress is missing/unauthenticated
  - configured log-file paths win over unrelated newer logs, while missing rolling daily files fall back to the latest existing runtime log
  - wizard steps now expose stable `field` ids and picker-only setup saves do not preseed guided drafts
  - gateway self presence now exposes host/ip/version/platform/device metadata and remains sorted ahead of connected nodes
  - paired-node payloads now preserve `deviceFamily`, `modelIdentifier`, `caps`, `commands`, and pending `silent` state on the gateway surface
- Landed one shared explicit-target default-account kernel in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): gateway direct sends and cron explicit announce/failure deliveries now derive a known channel default account from saved notification-route inventory before building the shared target session key, so account-aware explicit targets no longer split into avoidable account-less aliases when callers omit `accountId`.
- Added focused regression coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) for:
  - shared direct-send default-account reuse from route inventory
  - cron explicit announce default-account reuse from the same inventory
- Landed one shared direct channel-target send owner in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): the reusable explicit-target owner that cron announce delivery used privately is now exposed for gateway callers, and `gateway.send` routes text-only direct messages through the same canonical target session/runtime instead of staying a perpetual 503 placeholder.
- Added focused regression coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) for injected direct-send runtime calls plus thread-id derivation from a thread-scoped `sessionKey`.
- Added focused API proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py) for real `gateway.send` delivery history/session writes plus blank optional routing identifiers.
- Landed one shared direct channel-target poll owner in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): `poll` now reuses the same canonical explicit-target session owner as `gateway.send`, records `gateway/poll` outbound delivery history, mirrors a formatted poll summary into the target session, and resolves known default channel accounts from saved route inventory before delivery.
- Added focused regression coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) for injected direct-poll runtime calls.
- Added focused API proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py) for real `gateway.poll` delivery history, thread-target session keys, duration/silent metadata, anonymous metadata, large durations, and blank-account routing.
- Added focused runtime proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) for the shared session-backed direct-poll owner.
- Closed the remaining session-backed `gateway.send` media breadth gap in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): `gateway.send` now normalizes `mediaUrl` plus `mediaUrls`, preserves explicit `gifPlayback`, records that media metadata in saved outbound delivery history, mirrors a readable media block into the target session, and saved replay now rebuilds the same text-plus-media message from stored gateway-send payloads.
- Added focused regression coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) for media-bearing direct-send runtime calls.
- Added focused runtime and replay proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_ops_mesh.py) for session-backed direct media delivery plus saved media-send replay message reconstruction.
- Added focused API proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py) for real `gateway.send` media delivery history plus the mirrored assistant session message.
- Closed the saved direct-transport replay read-model seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/cli.py): replay results for saved `session`, `announce`, and route-less `webhook` deliveries now surface honest transport kind plus target identity instead of a synthetic webhook-only route view, and the human CLI now prints route kind plus target for saved direct-delivery history and replay.
- Closed one verification-found regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_models.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_models.py): merged model catalog entries now sort by provider plus canonical model id before display name, so richer duplicate names do not destabilize catalog order.
- Landed one reusable channel/account routing kernel slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\session_keys.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/session_keys.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): launch session keys and Ops Mesh route matching now canonicalize conversation-target `account_id` the same way, while preserving lowercase channel/peer identity for routed channel deliveries.
- Added focused regression coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_channel_account_routing.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_channel_account_routing.py) for canonical launch session keys plus peer/account route matching across raw `Workspace Bot` versus canonical `workspace-bot` identity.
- Verified direct-send unit coverage with `tests/test_gateway_node_methods.py -k "test_send_returns_validated_unavailable_contract or test_send_uses_channel_message_runtime_and_derives_thread_from_session_key"`: `2 passed`.
- Verified direct-send media unit coverage with `tests/test_gateway_node_methods.py -k "test_send_returns_validated_unavailable_contract or test_send_uses_channel_message_runtime_and_derives_thread_from_session_key or test_send_uses_channel_message_runtime_for_media_payloads"`: `3 passed`.
- Verified direct-poll unit coverage with `tests/test_gateway_node_methods.py -k "test_poll_returns_validated_unavailable_contract or test_poll_uses_channel_poll_runtime"`: `2 passed`.
- Verified the new temp-path-sensitive direct-send API proofs by directly executing the exact test functions against repo-local temp paths:
  - `test_send_endpoint_delivers_channel_target_message_and_records_outbound_delivery`
  - `test_send_endpoint_allows_blank_optional_routing_identifiers`
- Verified the new temp-path-sensitive direct-send media API proof by directly executing the exact test function against a repo-local temp path:
  - `test_send_endpoint_delivers_channel_target_media_and_records_outbound_delivery`
- Verified the new temp-path-sensitive direct-poll API proofs by directly executing the exact test functions against repo-local temp paths:
  - `test_poll_endpoint_delivers_channel_target_poll_and_records_outbound_delivery`
  - `test_poll_endpoint_allows_thread_id_and_routes_poll_to_thread_session`
  - `test_poll_endpoint_records_duration_hours_and_silent_settings`
  - `test_poll_endpoint_records_is_anonymous_setting`
  - `test_poll_endpoint_allows_large_duration_hours`
  - `test_poll_endpoint_allows_blank_account_id`
- Verified shared direct-send media delivery plus replay formatting with `tests/test_ops_mesh.py -k "test_ops_mesh_service_send_direct_channel_message_uses_known_channel_default_account or test_ops_mesh_service_send_direct_channel_message_records_media_delivery or test_saved_outbound_delivery_replay_message_formats_gateway_send_media_payload"`: `3 passed`.
- Verified saved direct replay route identity with `tests/test_ops_mesh.py -k "replay_outbound_deliveries_retries_saved_failed_session_delivery or replay_outbound_deliveries_retries_saved_failed_announce_delivery or replay_outbound_deliveries_retry_secret_backed_ad_hoc_webhook_delivery"`: `3 passed`.
- Verified saved direct poll replay formatting with `tests/test_ops_mesh.py -k "saved_outbound_delivery_replay_message_formats_gateway_poll_payload or replay_outbound_deliveries_retries_saved_failed_gateway_poll_delivery or saved_outbound_delivery_replay_message_formats_gateway_send_media_payload or replay_outbound_deliveries_retries_saved_failed_announce_delivery"`: `4 passed`.
- Verified saved direct-delivery CLI surfaces with `tests/test_cli.py -k "routes_deliveries_reports_saved_direct_transport_identity or routes_replay_json_reports_saved_announce_transport_identity or routes_replay_reports_saved_announce_transport_identity"`: `3 passed`.
- Verified the shared direct-send/poll runtime owners with `tests/test_ops_mesh.py -k "send_direct_channel_message_uses_known_channel_default_account or send_direct_channel_poll_records_session_backed_delivery"`: `2 passed`.
- Verified the shared direct-send/poll runtime types with `mypy src/openzues/services/ops_mesh.py src/openzues/services/gateway_node_methods.py`: clean.
- Verified the new default-account kernel with `tests/test_ops_mesh.py -k "known_channel_default_account"`: `2 passed`.
- Verified the new task-blueprint truth coverage by directly executing `test_task_blueprint_reads_prefer_row_enabled_over_stale_payload_enabled`.
- Verified the new gateway session resolve coverage by directly executing:
  - `test_resolve_key_rejects_multiple_primary_selectors_like_openclaw`
  - `test_resolve_key_requires_a_nonblank_primary_selector_like_openclaw`
  - `test_resolve_key_label_lookup_skips_hidden_metadata_matches`
  - `test_resolve_key_label_lookup_trims_whitespace_like_openclaw`
  - `test_resolve_key_rejects_ambiguous_visible_label_matches`
- Verified the hot bootstrap/log/wizard/system-presence shard coverage by directly executing:
  - `test_get_view_marks_local_bootstrap_staged_when_saved_task_is_disabled`
  - `test_get_view_surfaces_saved_workspace_integration`
  - `test_get_view_does_not_claim_secret_ready_for_label_only_integration`
  - `test_get_view_marks_remote_bootstrap_staged_without_enabled_ingress`
  - `test_get_view_marks_remote_bootstrap_staged_when_saved_task_is_disabled`
  - `test_gateway_logs_tail_reads_configured_log_file_path_even_when_other_logs_are_newer`
  - `test_gateway_logs_tail_falls_back_to_latest_rolling_log_when_configured_daily_file_is_missing`
  - `test_wizard_prompts_for_mode_when_session_has_no_saved_mode`
  - `test_local_wizard_collects_operator_name_before_task_name`
  - `test_local_wizard_prompts_for_flow_before_workspace_when_missing`
  - `test_remote_wizard_collects_optional_identity_fields_before_task_name`
  - `test_gateway_system_presence_self_entry_includes_gateway_metadata`
  - `test_gateway_system_presence_keeps_self_entry_sorted_before_connected_nodes`
- Verified the hot node pairing and gateway wizard API coverage by directly executing:
  - `test_node_methods_surface_openclaw_shaped_pair_list_payloads`
  - `test_node_pair_request_persists_and_refreshes_openclaw_pending_entries`
  - `test_node_pair_request_refresh_preserves_omitted_fields_and_allows_explicit_empty_lists`
  - `test_node_pair_list_preserves_silent_pending_entries`
  - `test_onboarding_wizard_http_endpoint_supports_remote_completion`
  - `test_onboarding_wizard_http_endpoint_prompts_for_mode_and_local_flow_from_blank_start`
  - `test_picker_only_setup_wizard_save_does_not_preseed_guided_mode_step`
  - `test_gateway_node_method_call_endpoint_supports_local_wizard_completion_from_saved_draft`
  - `test_onboarding_wizard_start_clears_explicit_blank_optional_remote_identity_fields`
- Reverified the adjacent existing explicit-announce proofs by directly executing the exact test functions against repo-local temp paths:
  - `test_ops_mesh_service_delivers_explicit_cron_failure_to_announce_target`
  - `test_ops_mesh_service_delivers_explicit_cron_failure_to_announce_thread_target`
- Verified the shared task owner with `ruff check src/openzues/database.py tests/test_database.py`: clean.
- Verified the shared task owner types with `mypy src/openzues/database.py`: clean.
- Verified the shared direct-send/poll files with `ruff check --extend-ignore E501 src/openzues/services/ops_mesh.py src/openzues/services/gateway_node_methods.py src/openzues/app.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_ops_mesh.py`: clean.
- Verified the touched explicit-target owner files with `ruff check src/openzues/services/ops_mesh.py tests/test_ops_mesh.py`: clean.
- Verified the touched explicit-target owner types with `mypy src/openzues/services/ops_mesh.py`: clean.
- Verified touched schema/runtime types with `mypy src/openzues/services/ops_mesh.py src/openzues/cli.py src/openzues/schemas.py`: clean.
- Verified touched routing runtime types with `mypy src/openzues/services/session_keys.py src/openzues/services/ops_mesh.py`: clean.
- Verified touched files with `ruff check src/openzues/schemas.py src/openzues/services/ops_mesh.py src/openzues/cli.py tests/test_ops_mesh.py tests/test_cli.py`: clean.
- Verified this run's touched routing files with `ruff check src/openzues/services/session_keys.py src/openzues/services/ops_mesh.py tests/test_channel_account_routing.py`: clean.
- Verified model catalog coverage with `tests/test_gateway_models.py`: `3 passed`.
- Verified pending-work coverage with `tests/test_gateway_node_pending_work.py`: `7 passed`.
- Verified remote wizard ordering with `tests/test_gateway_wizard.py -k "remote_wizard_collects_operator_name_before_task_name"`: `1 passed`.
- Verified main-session cron wake routing with `tests/test_gateway_nodes_api.py -k "main_system_event_cron_run_routes_session_key_through_wake_queue"`: `1 passed`.
- Verified replay + wake regressions with `tests/test_ops_mesh.py -k "replay_outbound_deliveries_retry_secret_backed_ad_hoc_webhook_delivery or ops_mesh_routes_due_main_system_event_session_key_through_wake_queue"`: `2 passed`.
- Verified the temp-path-sensitive gateway session and local wizard proofs by directly executing the exact test functions against repo-local temp paths:
  - `test_build_snapshot_discovers_mission_and_transcript_sessions_without_metadata`
  - `test_build_snapshot_sorts_discovered_sessions_by_updated_at_desc`
  - `test_resolve_key_prefers_structural_session_id_match_over_fresher_fuzzy_duplicate`
  - `test_resolve_key_rejects_ambiguous_structural_session_id_duplicates`
  - `test_gateway_node_method_call_endpoint_supports_local_wizard_completion_from_saved_draft`
- Verified the new temp-path-sensitive channel/account routing proofs by directly executing the exact test functions against repo-local temp paths:
  - `test_build_launch_session_key_canonicalizes_channel_account_and_peer_identity`
  - `test_ops_mesh_matches_routes_after_account_id_canonicalization`
  - `test_ops_mesh_service_filters_notification_routes_by_conversation_target`

## Verification Notes

- `pytest` temp-path cleanup currently hits `WinError 5` in this Windows/OneDrive environment, so temp-path-heavy proofs may need direct invocation until that harness issue is cleaned up.
- The repo virtualenv launcher currently points at a missing base Python; focused verification succeeded by running the Codex runtime interpreter with `.venv\\Lib\\site-packages` on `PYTHONPATH`.
- `tests/test_gateway_nodes_api.py` still carries unrelated historical `E501` lines, so touched-file Ruff verification for this seam used `--extend-ignore E501` instead of widening into repo-style cleanup.
- `plugin.approval.*` moved from explicit hard-503 validation to a bounded local lifecycle in `GatewayNodeMethodService`: request creates a pending record, list exposes pending records, resolve records and broadcasts the decision, and waitDecision returns the stored decision.
- Verified `plugin.approval.*` with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k plugin_approval`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `device.pair.*` moved from explicit hard-503 validation to persisted pairing lifecycle aliases over `GatewayNodePairingService`: list exposes OpenClaw-shaped `deviceId` pending/paired payloads, approve/reject broadcast `device.pair.resolved`, and remove deletes paired devices without exposing the node token.
- Verified `device.pair.*` with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k device_pair`, `pytest tests/test_gateway_node_methods.py -q -k "node_pair or device_pair"`, `ruff check src/openzues/database.py src/openzues/services/gateway_node_pairing.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/database.py src/openzues/services/gateway_node_pairing.py src/openzues/services/gateway_node_methods.py`.
- `exec.approval.*` moved from explicit hard-503 validation to a bounded local approval lifecycle in `GatewayNodeMethodService`: request creates a pending approval, list/get expose pending metadata, resolve records and broadcasts the decision, and waitDecision returns the stored decision.
- Verified `exec.approval.*` with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k exec_approval`, the combined `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "exec_approval or plugin_approval or device_pair"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `exec.approvals.*` moved from explicit hard-503 validation to persisted policy config files under the OpenZues data dir, including global get/set, node get/set, socket-token redaction, and base-hash guards.
- Verified `exec.approvals.*` with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k exec_approvals`, `ruff check src/openzues/services/gateway_node_methods.py src/openzues/app.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py src/openzues/app.py`.
- `device.token.rotate/revoke` moved from explicit hard-503 validation to a persisted SQLite token runtime: rotate creates or replaces role-scoped device auth tokens, `device.pair.list` now summarizes those tokens without leaking the paired-node token, revoke records `revokedAtMs`, and unknown device/role calls fail as invalid requests.
- Verified `device.token.*` with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k device_token`, `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "device_pair or device_token or node_pair"`, `ruff check src/openzues/database.py src/openzues/services/gateway_node_pairing.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/database.py src/openzues/services/gateway_node_pairing.py src/openzues/services/gateway_node_methods.py`.
- `agents.create/update/delete` moved from explicit hard-503 validation to a persisted SQLite custom-agent registry: create/update materialize workspace `IDENTITY.md`, list now includes custom agents alongside `main`, and delete removes the registry entry without touching workspace files unless a later deletion runtime intentionally adds safe trash handling.
- Verified `agents.*` mutation with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "agents_mutate or agents_mutation or agents_list_returns"`, `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "agents_list or agents_files or agents_mutate or agents_mutation or agent_identity"`, `ruff check src/openzues/database.py src/openzues/services/gateway_agents.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_method_policy.py`, and `mypy src/openzues/database.py src/openzues/services/gateway_agents.py src/openzues/services/gateway_node_methods.py`.
- `config.set/patch/apply` moved from explicit hard-503 validation to a bounded writable control-UI config owner: set/apply validate full config JSON, patch shallow/deep-merges JSON patches into the current config, writes `settings/control-ui-config.json`, enforces base-hash guards once the file exists, and `config.get` reads back the durable snapshot.
- Verified config mutation with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "config_get or config_open_file or config_write or control_ui_config"`, `ruff check src/openzues/services/gateway_config.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_config.py src/openzues/services/gateway_node_methods.py`.
- `doctor.memory.backfillDreamDiary/resetDreamDiary/resetGroundedShortTerm/repairDreamingArtifacts/dedupeDreamDiary` moved from explicit hard-503 validation to bounded workspace mutation helpers for OpenZues dreaming artifacts.
- Verified doctor-memory mutation with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k doctor_memory`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- Admin-scoped `chat.send` origin-route fields moved from explicit hard-503 validation to bounded route-provenance preservation in the submitted runtime message, while non-admin callers remain blocked and broader system provenance remains guarded.
- Verified `chat.send` origin-route provenance with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "originating_fields or originating_route or system_provenance"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- Admin-scoped `chat.send` system provenance moved from explicit hard-503 validation to bounded runtime-envelope preservation for input provenance plus receipt text, while non-admin callers remain blocked.
- Verified `chat.send` system provenance with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "originating_fields or originating_route or system_provenance"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `sessions.steer` moved past a false interruption-runtime dependency: idle steer sends now use the chat send runtime without requiring an abort service, while active-run interruption and stop commands still require the abort runtime.
- Verified idle `sessions.steer` with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k sessions_steer`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `chat.abort` now resolves request aliases such as `subagent:child` through the shared existing-session resolver before interrupting active tracked runs, so short child aliases can cancel the canonical runtime run.
- Verified `chat.abort` alias resolution with `pytest tests/test_gateway_node_methods.py -q -k "chat_abort_uses_resolved_subagent_store_key"`, `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_abort or chat_send or sessions_send or sessions_steer"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `sessions.abort` now resolves request aliases such as `subagent:child` through the shared existing-session resolver before interrupting active tracked runs and publishing the abort `sessions.changed` event under the canonical key.
- Verified `sessions.abort` alias resolution with `pytest tests/test_gateway_node_methods.py -q -k "sessions_abort_uses_resolved_subagent_store_key"`, `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_abort or chat_abort or chat_send or sessions_send or sessions_steer"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `sessions.preview` now resolves request aliases such as `subagent:child` through the shared existing-session resolver before reading transcript rows, while preserving the caller's requested key in each preview response slot.
- Verified `sessions.preview` alias resolution with `pytest tests/test_gateway_node_methods.py -q -k "sessions_preview_uses_resolved_subagent_store_key"`, `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_preview or sessions_get or chat_history or sessions_usage"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `tools.effective` now resolves request aliases such as `subagent:child` through the shared existing-session resolver before deriving session-scoped toolsets and agent identity.
- Verified `tools.effective` alias resolution with `pytest tests/test_gateway_node_methods.py -q -k "tools_effective_uses_resolved_subagent_store_key"`, `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "tools_effective or tools_catalog or sessions_preview"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- direct channel `send` now resolves known request aliases such as `subagent:child` before passing source-session provenance to the delivery runtime, while preserving unknown structural source keys exactly.
- Verified direct-send alias resolution with `pytest tests/test_gateway_node_methods.py -q -k "send_uses_resolved_subagent_store_key_for_delivery_provenance"`, `pytest tests/test_gateway_nodes_api.py -q -k "send_endpoint_delivers_channel_target_message_and_records_outbound_delivery or send_endpoint_delivers_channel_target_media_and_records_outbound_delivery"`, `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "send_ or poll_ or message_action"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `plugin.approval.request` and `exec.approval.request` now resolve known request aliases such as `subagent:child` before storing durable approval provenance, while preserving unknown legacy session ids.
- Verified approval provenance alias resolution with `pytest tests/test_gateway_node_methods.py -q -k "plugin_approval_request_uses_resolved_subagent_store_key"`, `pytest tests/test_gateway_node_methods.py -q -k "exec_approval_request_uses_resolved_subagent_store_key"`, `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "plugin_approval or exec_approval or send_uses_resolved_subagent_store_key_for_delivery_provenance"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- internal `node.event` routing now resolves known request aliases such as `subagent:child` before chat subscriptions, exec/notification wake events, voice transcripts, and agent requests, while preserving the raw recorded node event.
- Verified node-event alias routing with `pytest tests/test_gateway_node_methods.py -q -k "node_event_chat_subscribe_uses_resolved_subagent_store_key"`, `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "node_event or node_invoke"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `wake` now resolves known request aliases such as `subagent:child` before deriving agent id and queueing wake requests.
- Verified wake alias resolution with `pytest tests/test_gateway_node_methods.py -q -k "wake_uses_resolved_subagent_store_key"`, `pytest tests/test_gateway_nodes_api.py -q -k "wake_now_auto_retries_after_submit_error"`, `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "wake or cron_wake"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- Persisted custom agents now flow into session orchestration: `sessions.create` accepts custom `agentId` values, generates custom-agent session keys, records the agent metadata, and `sessions.list agentId=...` can filter those sessions.
- Verified the custom-agent session bridge with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_create or sessions_list_filters_by_agent"`, `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py src/openzues/services/gateway_agents.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py src/openzues/services/gateway_agents.py`.
- Shared known/existing session-key resolution now falls back to a unique session-id lookup, so short aliases such as `subagent:child` can resolve to custom-agent store keys like `agent:builder-prime:subagent:child`; `agent.identity.get` now uses that resolver before deriving identity.
- Verified custom-agent child alias identity with `pytest tests/test_gateway_node_methods.py -q -k "agent_identity_get_uses_resolved_custom_subagent_store_key"`, the adjacent `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "agent_identity or sessions_resolve or sessions_get or sessions_preview or chat_abort or sessions_abort or tools_effective or send_uses_resolved_subagent_store_key_for_delivery_provenance or plugin_approval or exec_approval or node_event_chat_subscribe or wake_uses_resolved"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `agent` launch now validates custom `agentId` values through the persisted agent registry and resolves known child aliases before dispatch, so `agentId=builder-prime` plus `sessionKey=subagent:child` launches against `agent:builder-prime:subagent:child`.
- Verified custom-agent child launch with `pytest tests/test_gateway_node_methods.py -q -k "agent_launch_uses_resolved_custom_subagent_store_key"`, the adjacent `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "agent_launch or agent_rejects or agent_identity or sessions_create or sessions_list_filters_by_agent"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `agent` launch now defaults persisted custom agents with no explicit session selector to scoped main sessions such as `agent:builder-prime:main` and persists `agentId` metadata for discovery.
- Verified custom-agent default launch with `pytest tests/test_gateway_node_methods.py -q -k "agent_launch_defaults_custom_agent_to_scoped_main_session"`, the adjacent `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "agent_launch or agent_rejects or agent_identity or sessions_create or sessions_list_filters_by_agent"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `sessions.patch` now resolves request keys through the shared existing-session resolver, so short aliases can mutate custom-agent child sessions such as `agent:builder-prime:subagent:child`.
- Verified custom-agent patch alias routing with `pytest tests/test_gateway_node_methods.py -q -k "sessions_patch_uses_resolved_custom_subagent_store_key"`, the adjacent `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_patch or sessions_get or chat_history or sessions_usage or sessions_preview"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `sessions.reset` now resolves request keys through the shared existing-session resolver before clearing transcripts and runtime metadata, preserving durable custom-agent metadata for aliases such as `subagent:child`.
- Verified custom-agent reset alias routing with `pytest tests/test_gateway_node_methods.py -q -k "sessions_reset_uses_resolved_custom_subagent_store_key"`, the adjacent `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_reset or sessions_delete or sessions_patch or sessions_preview"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `sessions.delete` now resolves request keys through the shared existing-session resolver before archive/delete work, so short aliases delete custom-agent child sessions rather than silently no-oping.
- Verified custom-agent delete alias routing with `pytest tests/test_gateway_node_methods.py -q -k "sessions_delete_uses_resolved_custom_subagent_store_key"`, the adjacent `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_delete or sessions_reset or sessions_patch or sessions_compact or sessions_compaction"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `chat.inject` now resolves request keys through the shared existing-session resolver before appending assistant transcript rows, so injected notes for custom-agent child aliases land on the canonical session.
- Verified custom-agent inject alias routing with `pytest tests/test_gateway_node_methods.py -q -k "chat_inject_uses_resolved_custom_subagent_store_key"`, the adjacent `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_inject or chat_history or chat_send or sessions_get or sessions_preview"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `sessions.create parentSessionKey` now resolves request keys through the shared existing-session resolver before deriving generated child session keys, so custom-agent parent aliases spawn under canonical custom parents.
- Verified custom-agent create-parent alias routing with `pytest tests/test_gateway_node_methods.py -q -k "sessions_create_resolves_custom_subagent_parent_key"`, the adjacent `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_create or sessions_list_filters_by_agent or agent_launch or agent_identity"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `sessions.create key=subagent:* agentId=<custom>` now scopes explicit child keys through the custom-agent store helper before mismatch validation, so `subagent:child` creates `agent:builder-prime:subagent:child` instead of failing as a main-agent key.
- Verified custom-agent explicit-key create routing with `pytest tests/test_gateway_node_methods.py -q -k "sessions_create_scopes_custom_agent_request_key"`, the adjacent `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_create or sessions_list_filters_by_agent or agent_launch or agent_identity"`, `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`, and `mypy src/openzues/services/gateway_node_methods.py`.
- `sessions.resolve key=subagent:* agentId=<custom>` now probes the custom-agent store before falling back to default-main aliases, and agent-filtered `sessionId` / label lookups no longer mistake legacy launch sessions for agent-owned sessions.
- Verified custom-agent resolver alias routing with `pytest tests/test_gateway_sessions.py -q -k "key_lookup_scopes_custom_agent_request_key_alias"`, `pytest tests/test_gateway_sessions.py tests/test_gateway_node_methods.py -q -k "resolve_key or sessions_resolve"`, the adjacent `pytest tests/test_gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_list_filters_by_agent or sessions_resolve or resolve_key or sessions_create or agent_launch or agent_identity"`, `ruff check src/openzues/services/gateway_sessions.py src/openzues/services/gateway_node_methods.py tests/test_gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`, and `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py`.
- Direct `POST /tools/invoke` now exists in OpenZues and can invoke safe core tool aliases such as `agents_list` with OpenClaw-shaped `{ok:true,result}` payloads; high-risk tool names such as `sessions_spawn` remain 404-hidden by default.
- Persisted `gateway.tools.allow` / `gateway.tools.deny` now flows into `tools.invoke` for the bounded `cron` tool bridge: `allow=["cron"]` opens `cron.status`, while `deny=["cron"]` wins over allow.
- `tools.invoke` now has an injected before-call hook boundary, so hook owners can block with OpenClaw-shaped `tool_call_blocked` errors or rewrite params before the mapped gateway method executes.
- Injected plugin/non-core executors can now run through `tools.invoke` after persisted `gateway.tools.allow` explicitly opens the tool, while unallowed plugin executors remain 404-hidden.
- Plugin executor input/auth/crash failures now map to OpenClaw-shaped `tool_error` responses instead of leaking raw executor exceptions.
- Owner-only filtering now survives `gateway.tools.allow`, so scoped non-admin callers cannot invoke owner-only control-plane tools such as `cron` even when the gateway allowlist opens them.
- Injected plugin executors can now declare custom owner-only metadata, so OpenZues can mirror OpenClaw's `ownerOnly: true` custom tool behavior without exposing those tools to scoped non-admin callers.
- `chat.inject`, `chat.history`, and live session transcript projection now strip trailing OpenClaw external-untrusted metadata suffix blocks from visible message text.
- `chat.send` final payload projection now strips trailing OpenClaw external-untrusted metadata suffix blocks from returned text blocks while preserving normal run-ack payloads.
- `chat.send` media-only final reply projection now mirrors OpenClaw's
  transcript builder: final payloads whose only reply content is media, even
  when stale text says `NO_REPLY`, return assistant text as `MEDIA:<url>`
  instead of leaking the control sentinel.
- Verified the media-only final reply seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_chat_send_projects_media_only_final_payload_text_like_openclaw
  -q`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k
  "chat_send and (final_payload or returns_run_ack or attachment_runtime or
  inherited_delivery_context)"`, `ruff check
  src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- `chat.send deliver=true` now inherits persisted channel-scoped `deliveryContext` routes when the resolved session key is scoped to the same external channel token.
- Gateway requester metadata now carries `clientMode`, so configured-main CLI `chat.send` delivery can inherit saved external routes while UI/webchat callers remain route-local.
- Session snapshots now derive missing `deliveryContext` fields from `origin.provider/accountId/threadId` route metadata, allowing configured-main delivery inheritance for older route records.
- Webchat `chat.send deliver=true` callers no longer inherit external delivery routes from channel-scoped sessions, preserving the internal webchat surface.
- `tools.invoke` now maps native `sessions_spawn` only after explicit `gateway.tools.allow`, preserving the default 404-hidden high-risk posture.
- `tools.invoke` now maps native `sessions_send` only after explicit `gateway.tools.allow`, preserving the default 404-hidden high-risk posture.
- Direct `/tools/invoke` route headers now survive into explicitly allowed
  `sessions_spawn` calls: `GatewayNodeMethodRequester` carries the
  OpenClaw message route context, `sessions.spawn` stores it as
  `requesterOrigin` / child `deliveryContext`, and the focused API proof
  verifies the resulting child session.
- Direct `/tools/invoke` body `sessionKey` now acts as the requester context
  for allowed `sessions_spawn`, filling native `requesterSessionKey` before
  dispatch so child metadata records the actual parent session.
- Direct `/tools/invoke` body `sessionKey` and requester channel now flow into
  allowed `sessions_send` as OpenClaw input provenance, so target runtime
  messages carry `sourceSessionKey`, `sourceChannel`, and `sourceTool`.
- `sessions_send` now accepts OpenClaw's `timeoutSeconds` argument when routed
  through `tools.invoke`, converts it to native `timeoutMs`, and preserves the
  existing millisecond override path for internal callers.
- `sessions_send timeoutSeconds=0` now returns OpenClaw's no-wait accepted
  result shape through `tools.invoke`, including target `sessionKey` and a
  pending announce delivery marker instead of raw internal chat runtime fields.
- `sessions_send` now accepts OpenClaw's target `sessionKey` argument through
  `tools.invoke` and translates it to the native `sessions.send key` parameter
  before method validation.
- successful nonzero `sessions_send timeoutSeconds` calls now normalize
  runtime replies into OpenClaw-shaped `status: ok` tool results with optional
  `reply`, target `sessionKey`, and pending announce delivery metadata.
- nonzero `sessions_send timeoutSeconds` calls now snapshot the target
  transcript before dispatch, poll for a fresh assistant row, and return that
  reply in the OpenClaw-shaped `status: ok` result when it appears.
- `sessions_send timeoutSeconds` now accepts numeric OpenClaw values and floors
  them to whole seconds before converting to native `timeoutMs`, instead of
  requiring integer-only input.
- `sessions_send` timeout/error tool results now include the target
  `sessionKey`, matching OpenClaw's public error/timeout envelope.
- `sessions_spawn` now accepts numeric OpenClaw `runTimeoutSeconds` /
  `timeoutSeconds` values and floors them to whole seconds before converting to
  native runtime milliseconds.
- `sessions_send` target runtime prompts now include OpenClaw's
  agent-to-agent message context, preserving requester session/channel and
  target session alongside the provenance envelope.
- Verified the `tools.invoke` bridge with `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "tools_invoke"`, the adjacent `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "tools_invoke or tools_catalog or tools_effective or config_get or config_set or cron_status"`, staged-registry app/CLI catalog tests, touched-file Ruff, and touched-source mypy.
- Verified the route-header spawn bridge with `python -m pytest tests\test_gateway_nodes_api.py -q -k "tools_invoke_endpoint_propagates_route_headers_to_sessions_spawn"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified the requester-session bridge with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_spawn_uses_body_session_key_as_requester"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified the sessions-send provenance bridge with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_preserves_requester_provenance"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified the sessions-send timeout alias with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_accepts_timeout_seconds_alias"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified the no-wait sessions-send result shape with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_zero_timeout_returns_accepted_shape"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified the OpenClaw `sessionKey` target alias with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_accepts_openclaw_session_key_arg"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified the successful sessions-send reply shape with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_reply_result_is_openclaw_shaped"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified the async transcript wait-loop with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_waits_for_fresh_assistant_reply"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified numeric timeoutSeconds parsing with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_floors_numeric_timeout_seconds"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified timeout/error envelope shaping with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_timeout_result_includes_session_key"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified sessions-spawn numeric timeout parsing with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_spawn_floors_numeric_timeout_seconds"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Verified sessions-send A2A target context with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_preserves_requester_provenance"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- `sessions_send` now starts OpenClaw-style A2A announce work after a waited
  successful target reply: the target gets the structured announce prompt, a
  literal `ANNOUNCE_SKIP` stays silent, and non-skip announce replies are
  delivered to the target session's saved `deliveryContext` channel/thread
  route.
- Verified sessions-send announce/delivery parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_runs_announce_step_after_reply"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- `sessions_send timeoutSeconds=0` now starts OpenClaw-style A2A announce work
  after a later assistant transcript reply appears, while preserving the
  immediate accepted result envelope.
- Verified sessions-send no-wait announce parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_zero_timeout_announces_after_later_reply"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- `sessions_send` A2A announce flow now runs OpenClaw's requester/target reply
  ping-pong loop before final announce, using the default five-turn cap and
  stopping on literal `REPLY_SKIP`.
- Verified sessions-send reply ping-pong parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_runs_a2a_reply_ping_pong_before_announce"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- `session.agentToAgent.maxPingPongTurns` now survives control-config
  validation and caps the `sessions_send` A2A reply loop, matching OpenClaw's
  operator-tunable turn limit.
- Verified sessions-send ping-pong config parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_honors_configured_ping_pong_turn_cap"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py src\openzues\schemas.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py src\openzues\schemas.py`.
- `tools.agentToAgent.enabled` now survives control-config validation and
  blocks cross-agent `sessions_send` before runtime dispatch when disabled,
  returning OpenClaw-style `status: forbidden` tool results.
- Verified cross-agent disabled policy parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke_sessions_send_blocks_cross_agent_when_a2a_disabled"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- `tools.sessions.visibility` now survives control-config validation and gates
  `sessions_send` before runtime dispatch: default `tree` blocks cross-agent
  sends unless visibility is `all`, explicit `self` blocks same-agent
  non-current sends, and default `tree` allows spawned child sessions while
  blocking unrelated same-agent sessions.
- Verified sessions-send visibility policy parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "spawned_child_session or unspawned_same_agent or tree_visibility or a2a_disabled or self_visibility"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- The same visibility/A2A guard now covers `tools.invoke sessions_history`,
  `session_status`, and `sessions_list`: history/status return forbidden tool
  results before lookup, while list filters invisible rows.
- Verified neighboring session-tool access policy parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_history_defaults_to_tree_visibility or session_status_enforces_self_visibility or sessions_list_filters_default_tree"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_history or session_status or sessions_list"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- `sessions_send` label lookup now applies OpenClaw's pre-resolution
  `agentId` A2A gate before lookup/runtime dispatch, closing the label-based
  bypass left after key-based send policy landed.
- Verified label lookup policy parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "cross_agent_label_lookup"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_history or session_status or sessions_list or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- `sessions_send` label targets now resolve to canonical keys before the
  `tools.invoke` wait snapshot and result normalization, so label-based
  nonzero waits include the fresh assistant reply and target `sessionKey`.
- Verified label wait/result parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "label_waits_for_fresh_assistant_reply"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_history or session_status or sessions_list or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- Label-based `sessions_send timeoutSeconds=0` now shares the same canonical
  target key path, preserving the accepted result envelope and scheduling the
  later A2A announce from the resolved target transcript.
- Verified label no-wait announce parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "label_zero_timeout_announces_after_later_reply"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_history or session_status or sessions_list or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- `sessions.history` now treats OpenClaw `toolResult` rows as tool messages:
  default history hides them and `includeTools=true` preserves the original
  `toolResult` role instead of leaking them as `other`.
- Verified `toolResult` filtering parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "tool_result_role_by_default"`, focused `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_history"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_history or session_status or sessions_list or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- `sessions.history` now applies OpenClaw `session-transcript-repair`
  redaction to structured `sessions_spawn` tool-call blocks, replacing inline
  attachment content with `__OPENCLAW_REDACTED__` while preserving only
  `name`, `encoding`, and `mimeType`.
- Verified the `sessions_spawn` attachment transcript redaction seam with
  `python -m pytest tests\test_gateway_node_methods.py -q -k
  "sessions_history_redacts_sessions_spawn_tool_call_attachments"` (`1
  passed`), adjacent history coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_history_redacts_sessions_spawn_tool_call_attachments or
  sessions_history_returns_redacted_agent_tool_projection or
  sessions_history_filters_openclaw_tool_result_role_by_default or
  sessions_history_supports_tool_opt_in_and_text_truncation or
  sessions_history_floors_numeric_openclaw_limit or
  sessions_history_uses_resolved_subagent_store_key or chat_history"` (`18
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- `sessions.list` now mirrors OpenClaw's numeric filter parsing for `limit`,
  `activeMinutes`, and `messageLimit`: finite numbers are floored, minimums
  are enforced with OpenClaw-style lower bounds, and capped fields clamp at the
  local/OpenClaw maxima.
- Verified `sessions_list` numeric filter parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_list_floors_numeric_openclaw_filters"`, focused `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_list"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_history or session_status or sessions_list or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- `session.status model=default` now removes stale `providerOverride`,
  `modelOverride`, `modelOverrideSource`, auth-profile override fields, stale
  fallback/runtime model cache fields, and sets `liveModelSwitchPending` when
  the model selection changed; `changedModel` now reflects the actual metadata
  delta instead of merely the presence of a `model` parameter.
- Verified `session_status` reset parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "model_default_resets_auth"`, focused `python -m pytest tests\test_gateway_node_methods.py -q -k "session_status"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_history or session_status or sessions_list or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- `chat.history` and `sessions.history` now share OpenClaw-style
  assistant-visible transcript sanitization for `<tool_result>` XML blocks and
  dangling `<think>` blocks, preventing tool-result payloads from leaking into
  user/agent history recall.
- Verified transcript sanitizer parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "strip_tool_result_xml_blocks"`, focused `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_history"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_history or session_status or sessions_list or sessions_spawn or chat_history"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- `sessions_yield` is no longer an absent OpenClaw session tool: the native
  method returns `No session context` without a session, `Yield not supported
  in this context` without a callback, and `status: yielded` after an injected
  yield callback; `tools.invoke` maps top-level requester `sessionKey` into
  the method and the catalog advertises the tool.
- Verified `sessions_yield` parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_yield or tools_catalog_returns"`, focused `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_catalog or tools_effective or sessions_yield"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or tools_catalog or tools_effective or sessions_yield or sessions_send or sessions_history or session_status or sessions_list or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- `sessions.spawn` now follows OpenClaw's provisional-child cleanup behavior
  when runtime start fails: the dispatch exception becomes a structured error
  result, child metadata/transcript/run state are deleted, and materialized
  attachments are best-effort removed instead of leaving ghost sessions.
- Verified the spawn cleanup seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "provisional_child_when_runtime_start_fails"`, the adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\hermes_toolsets.py`.
- `sessions.spawn` now preserves OpenClaw's ACP preflight ordering even while
  full ACP spawning remains unavailable locally: `lightContext` with
  `runtime=acp` raises the upstream-style error, and ACP inline attachments
  return the specific unsupported-attachments result instead of a generic ACP
  boundary.
- Verified the ACP preflight seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "light_context_for_acp or acp_attachments_before_runtime_boundary"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `RuntimeManagerAcpSpawnService` now preserves OpenClaw's ACP direct-spawn
  session-mode policy: `mode="session"` returns `errorCode="thread_required"`
  unless `thread=true`, and the RuntimeManager thread/turn dispatch path is not
  touched for that rejected request.
- Verified the ACP session-mode runtime guard with `python -m pytest tests\test_gateway_acp_spawn.py -q -k "rejects_session_mode_without_thread"`, adjacent `python -m pytest tests\test_gateway_acp_spawn.py -q`, gateway projection `python -m pytest tests\test_gateway_node_methods.py -q -k "acp and spawn"`, `ruff check src\openzues\services\gateway_acp_spawn.py tests\test_gateway_acp_spawn.py`, and `mypy src\openzues\services\gateway_acp_spawn.py`.
- `channels.status --probe` now wires the production Ops Mesh channel-account
  probe path into the app and CLI GatewayChannelsService owners. Slack native
  notification routes probe `auth.test` with the saved bot token; no configured
  account returns `native_provider_route_unavailable` instead of reporting an
  empty `ok` probe.
- Verified the route-backed Slack probe seam with `python -m pytest tests\test_cli.py -q -k "route_backed_slack_probe"`, adjacent `python -m pytest tests\test_cli.py -q -k "channels_status_json or channels_capabilities_json or channels_resolve_json"`, gateway projection `python -m pytest tests\test_gateway_node_methods.py -q -k "channels_status"`, `ruff check src\openzues\app.py src\openzues\cli.py src\openzues\services\gateway_channels.py src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy src\openzues\app.py src\openzues\cli.py src\openzues\services\gateway_channels.py src\openzues\services\ops_mesh.py`.
- Telegram native notification routes now probe Bot API `getMe` with the saved
  bot token and return `botId`, `username`, and `firstName` in the account probe
  result.
- Verified the route-backed Telegram probe seam with `python -m pytest tests\test_cli.py -q -k "route_backed_telegram_probe"`, adjacent `python -m pytest tests\test_cli.py -q -k "route_backed_slack_probe or route_backed_telegram_probe or channels_status_json or channels_capabilities_json"`, `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Discord native notification routes now probe Discord API `users/@me` plus
  `oauth2/applications/@me` with the saved bot token and return bot identity
  plus privileged intent metadata.
- Verified the route-backed Discord probe seam with `python -m pytest tests\test_cli.py -q -k "route_backed_discord_probe"`, adjacent `python -m pytest tests\test_cli.py -q -k "route_backed_slack_probe or route_backed_telegram_probe or route_backed_discord_probe or channels_status_json or channels_capabilities_json"`, `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py`.
- WhatsApp route-backed channel status now reflects the upstream plugin's lack
  of a live `probeAccount` hook as `status="unsupported"` without `ok=false`,
  so `channels.status --probe` does not degrade a WhatsApp-only account.
- Verified the WhatsApp no-hook probe seam with `python -m pytest tests\test_cli.py -q -k "whatsapp_no_hook_probe"`, adjacent `python -m pytest tests\test_cli.py -q -k "route_backed_slack_probe or route_backed_telegram_probe or route_backed_discord_probe or whatsapp_no_hook_probe or channels_status_json or channels_capabilities_json"`, `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Thread-bound `sessions.spawn` initial child runs now pass the bound delivery
  origin into the chat-send runtime as `deliver=true`, `channel`, `to`,
  `account_id`, and `thread_id`, matching the upstream bind-before-run flow.
- Verified the thread-bound initial child delivery seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "thread_mode_delivers_initial_child_run"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_thread_mode or thread_mode_delivers_initial_child_run or sessions_spawn_session_mode"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Thread-bound `agent.wait` terminal announcements now deliver through the
  saved `completionDelivery` channel route via `send_channel_message_service`,
  while retaining parent transcript announcements and idempotent metadata.
- Verified the thread-bound completion delivery seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "thread_bound_completion_uses_completion_delivery_route"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_announces_spawn_completion or thread_bound_completion_uses_completion_delivery_route or no_completion_announce or completion_dedupe or sessions_spawn_thread_mode"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- Slack route-backed `channels resolve --kind channel` now uses Slack
  `conversations.list` with the saved route token to resolve channel ids,
  channel mentions, and names before falling back to unresolved results.
- Verified the Slack channel resolver seam with `python -m pytest tests\test_cli.py -q -k "route_backed_slack_channel_resolver"`, adjacent `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_slack_channel_resolver or channels_status_json or route_backed_slack_probe"`, `ruff check src\openzues\services\ops_mesh.py src\openzues\app.py src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py src\openzues\app.py src\openzues\cli.py`.
- Slack route-backed `channels resolve --kind user` now uses Slack `users.list`
  with the saved route token to resolve user ids, mentions, names, display/real
  names, and email addresses before falling back to unresolved results.
- Verified the Slack user resolver seam with `python -m pytest tests\test_cli.py -q -k "route_backed_slack_user_resolver"`, adjacent `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json or route_backed_slack_probe"`, `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py`.
- `channels resolve` now mirrors OpenClaw's auto-kind batching for live
  resolver entries, splitting user-looking inputs to the user resolver and
  group-looking inputs to the group/channel resolver while preserving command
  output order.
- Verified the auto-kind resolver seam with `python -m pytest tests\test_cli.py -q -k "auto_groups_route_backed_slack_targets"`, adjacent `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json or route_backed_slack_probe"`, `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Telegram route-backed `channels resolve --kind user` now calls Bot API
  `getChat` with the saved route token to resolve usernames to numeric chat ids
  before returning OpenClaw-shaped resolve rows.
- Verified the Telegram username resolver seam with `python -m pytest tests\test_cli.py -q -k "route_backed_telegram_user_resolver"`, adjacent `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_telegram_user_resolver or route_backed_telegram_probe or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json"`, `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Discord route-backed `channels resolve --kind channel` now calls
  `/users/@me/guilds` and `/channels/{id}` with the saved route token to resolve
  channel mentions and channel ids before returning OpenClaw-shaped resolve
  rows.
- Verified the Discord channel-id resolver seam with `python -m pytest tests\test_cli.py -q -k "route_backed_discord_channel_resolver"`, adjacent `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_discord_channel_resolver or route_backed_discord_probe or route_backed_telegram_user_resolver or route_backed_telegram_probe or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json"`, `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Discord route-backed `channels resolve --kind channel` now also resolves
  `guild/channel` and `guild#channel` inputs by listing `/guilds/{guildId}/channels`
  and matching normalized OpenClaw-style channel slugs.
- Verified the Discord guild-channel resolver seam with `python -m pytest tests\test_cli.py -q -k "route_backed_discord_guild_channel_resolver"`, adjacent `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_discord_channel_resolver or route_backed_discord_guild_channel_resolver or route_backed_discord_probe or route_backed_telegram_user_resolver or route_backed_telegram_probe or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json"`, `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Discord route-backed `channels resolve --kind channel` now resolves global
  `#channel` inputs by searching all bot guilds, preferring active non-thread
  matches, and preserving OpenClaw's multiple-match note.
- Verified the Discord global-channel resolver seam with `python -m pytest tests\test_cli.py -q -k "route_backed_discord_global_channel_resolver"`, adjacent `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_discord_channel_resolver or route_backed_discord_guild_channel_resolver or route_backed_discord_global_channel_resolver or route_backed_discord_probe or route_backed_telegram_user_resolver or route_backed_telegram_probe or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json"`, `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Discord route-backed `channels resolve --kind user` now resolves
  guild-qualified user names through `/guilds/{guildId}/members/search`,
  applies OpenClaw's member scoring, and returns id/name/note rows.
- Verified the Discord user resolver seam with `python -m pytest tests\test_cli.py -q -k "route_backed_discord_user_resolver"`, adjacent `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_discord_user_resolver or route_backed_discord_channel_resolver or route_backed_discord_guild_channel_resolver or route_backed_discord_global_channel_resolver or route_backed_discord_probe or route_backed_telegram_user_resolver or route_backed_telegram_probe or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json"`, `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Telegram native sends now parse topic-qualified targets into base `chat_id`
  plus `message_thread_id`, matching OpenClaw's `parseTelegramTarget` behavior
  for `telegram:group:<chatId>:topic:<threadId>`.
- Verified the Telegram topic-target seam with `python -m pytest tests\test_ops_mesh.py -q -k "telegram_topic_target"`, adjacent `python -m pytest tests\test_ops_mesh.py -q -k "send_direct_channel_message_uses_telegram_native or telegram_topic_target or send_direct_channel_poll_uses_telegram"`, `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Telegram parent supergroup routes now match topic-qualified send targets for
  the same base chat id, while topic-specific route peer ids still require the
  same topic id.
- Verified the Telegram topic parent-route seam with `python -m pytest tests\test_ops_mesh.py -q -k "topic_to_parent"`, adjacent `python -m pytest tests\test_ops_mesh.py -q -k "send_direct_channel_message_uses_telegram_native or telegram_topic_target or topic_to_parent or send_direct_channel_poll_uses_telegram"`, `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- `chat.history` and `sessions.history` now mirror OpenClaw's numeric history
  limit parsing: finite JSON numbers are floored and bounded instead of
  requiring integer-only input.
- Verified the history numeric-limit seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "numeric_openclaw_limit or sessions_history or chat_history"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_history or chat_history or sessions_send or sessions_list or session_status"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.get` now mirrors OpenClaw's finite numeric `limit` parsing,
  flooring non-integer JSON numbers while leaving the explicit large-limit path
  intact for direct transcript reads.
- Verified the `sessions.get` numeric-limit seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_get"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_get or chat_history or sessions_history"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.preview` now follows OpenClaw's key normalization behavior: blank
  whitespace keys are filtered after validation, duplicate keys are preserved,
  and only the first 64 normalized keys are processed.
- Verified the `sessions.preview` key-normalization seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_preview_filters_blank_keys_like_openclaw or sessions_preview_preserves_duplicate_keys_like_openclaw"`, cap coverage in the focused preview cluster, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_preview"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `tools.invoke sessions_list` now aligns `count` with the post-filter visible
  session rows, matching OpenClaw's tool result shape after sandbox/visibility
  filtering.
- Verified `sessions_list` post-filter count parity with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_list_filters_default_tree_cross_agent_rows"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_list or sessions_history or session_status"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `tools.invoke sessions_list` now mirrors OpenClaw's global row rules,
  dropping `unknown` and hiding `global` unless the requester session is the
  global alias.
- Verified the global/unknown row-filter seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_list_hides_global_for_non_global_requester or sessions_list_filters_default_tree_cross_agent_rows"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_list or sessions_history or session_status"` (`81 passed`, one aiosqlite thread-close warning), `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `tools.invoke sessions_list` now normalizes OpenClaw tool `kinds` before
  native dispatch, preserving only `main`, `group`, `cron`, `hook`, `node`, and
  `other` while ignoring unsupported values such as `global`.
- Verified the `sessions_list` unsupported-kind seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_list_ignores_unsupported_openclaw_kinds"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_list or sessions_history or session_status"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `tools.invoke sessions_list` now projects the OpenClaw-supported argument
  set before native dispatch, so local-only filters like `label` are ignored at
  the agent-tool boundary instead of suppressing visible sessions.
- Verified the `sessions_list` argument-projection seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_list_ignores_unsupported_openclaw_args or sessions_list_ignores_unsupported_openclaw_kinds or sessions_list_hides_global_for_non_global_requester"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_list or sessions_history or session_status"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `tools.invoke sessions_history` now projects only the OpenClaw-supported
  argument set (`sessionKey`, `limit`, `includeTools`) before native dispatch,
  ignoring local-only fields such as `maxChars`.
- Verified the `sessions_history` argument-projection seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_history_ignores_unsupported_openclaw_args"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_list or sessions_history or session_status"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `tools.invoke session_status` now projects only the OpenClaw-supported
  argument set (`sessionKey`, `model`) before native dispatch, ignoring
  local-only fields such as `includeDebug`.
- Verified the `session_status` argument-projection seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "session_status_ignores_unsupported_openclaw_args"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_list or sessions_history or session_status"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `tools.invoke sessions_yield` now matches OpenClaw's context contract: only
  top-level requester context supplies `sessionKey`, while tool args are
  projected to the optional `message`.
- Verified the `sessions_yield` context/projection seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_yield_ignores_session_key_arg_without_context or sessions_yield_ignores_unsupported_openclaw_args or sessions_yield_uses_requester_session_context"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_list or sessions_history or session_status or sessions_yield"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `tools.invoke sessions_send` now ignores unknown tool args after translating
  OpenClaw `sessionKey` and requester context, while preserving supported
  OpenClaw/local compatibility fields.
- Verified the `sessions_send` unknown-arg seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_send_ignores_unknown_openclaw_args or sessions_send_accepts_openclaw_session_key_arg or sessions_send_preserves_requester_provenance"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_send or sessions_list or sessions_history or session_status or sessions_yield"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `tools.invoke sessions_spawn` now ignores unknown OpenClaw tool args before
  native dispatch while preserving the upstream explicit errors for unsupported
  delivery params such as `target`, `channel`, and `replyTo`.
- Verified the `sessions_spawn` unknown-arg seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_ignores_unknown_openclaw_args or allows_sessions_spawn_when_gateway_tools_allow_configured or sessions_spawn_floors_numeric_timeout_seconds"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_spawn or sessions_send or sessions_list or sessions_history or session_status or sessions_yield"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `tools.invoke sessions_spawn` now ignores raw `args.requesterSessionKey`;
  only top-level requester/runtime context supplies native spawn lineage, so
  tool payload metadata cannot spoof the parent session.
- Verified the `sessions_spawn` requester-context seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_ignores_arg_requester_session_key or sessions_spawn_uses_body_session_key_as_requester or sessions_spawn_ignores_unknown_openclaw_args"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_spawn or sessions_send or sessions_list or sessions_history or session_status or sessions_yield"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- accepted `sessions.spawn` results now include OpenClaw's run-mode
  push-not-poll `note` unless the requester is a cron session.
- Verified the `sessions_spawn` accepted-note seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_returns_openclaw_accepted_note_for_run_mode or sessions_spawn_creates_openclaw_style_subagent_session"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_spawn or sessions_send or sessions_list or sessions_history or session_status or sessions_yield"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- accepted `sessions.spawn` results now include `modelApplied: true` when a
  local explicit model override was persisted for the child session.
- Verified the `sessions_spawn` model-applied seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_reports_model_applied_for_model_override or sessions_spawn_creates_openclaw_style_subagent_session"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "tools_invoke or sessions_spawn or sessions_send or sessions_list or sessions_history or session_status or sessions_yield"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.create` now matches OpenClaw's explicit key-agent mismatch error
  when the requested `key` is already scoped to a different agent than
  `agentId`.
- Verified the `sessions.create` mismatch seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_create_reports_openclaw_key_agent_mismatch or sessions_create_scopes_custom_agent_request_key or sessions_create_scopes_main_alias_to_requested_agent"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.create` now preserves the created session and returns `runError`
  when the optional initial send fails, instead of letting the send failure
  abort the whole create method.
- Verified the `sessions.create` initial-send error seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_create_returns_run_error_when_initial_send_fails or sessions_create_registers_metadata_session_and_sends_initial_message"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.patch` now applies OpenClaw's spawn-lineage support gate, rejecting
  non-null `spawnedBy`, `spawnedWorkspaceDir`, `spawnDepth`, `subagentRole`,
  and `subagentControlScope` patches on non-subagent/non-ACP sessions.
- Verified the `sessions.patch` lineage-support seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_patch_rejects_spawn_lineage_on_main_session or sessions_patch_persists_metadata_backed_child_session"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.patch` now applies OpenClaw's spawn-lineage immutability rules:
  already-set lineage fields cannot be changed or cleared.
- Verified the `sessions.patch` lineage-immutability seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_patch_rejects_changed_spawned_by or sessions_patch_persists_metadata_backed_child_session"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.patch` now rejects duplicate labels already present on another
  metadata-backed session before applying the patch.
- Verified the `sessions.patch` duplicate-label seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_patch_rejects_duplicate_label or sessions_patch_persists_current_session_metadata_and_surfaces_it"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.patch` now normalizes `responseUsage` with OpenClaw aliases:
  `"on"` / truthy aliases become `"tokens"`, `"off"` / falsey aliases clear
  the override, and invalid values use the upstream error message.
- Verified the `sessions.patch` response-usage seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_patch_normalizes_response_usage_on_to_tokens or sessions_patch_persists_current_session_metadata_and_surfaces_it"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.patch` now normalizes `execSecurity` case and rejects unsupported
  values using the OpenClaw `deny` / `allowlist` / `full` contract.
- Verified the `sessions.patch` exec-security seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_patch_normalizes_exec_security_case or sessions_patch_persists_current_session_metadata_and_surfaces_it"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.patch` now normalizes `execAsk` case and rejects unsupported values
  using the OpenClaw `off` / `on-miss` / `always` contract.
- Verified the `sessions.patch` exec-ask seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_patch_normalizes_exec_ask_case or sessions_patch_persists_current_session_metadata_and_surfaces_it"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.patch` now normalizes `execHost` case and rejects unsupported
  values using the OpenClaw `auto` / `sandbox` / `gateway` / `node` contract.
- Verified the `sessions.patch` exec-host seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_patch_normalizes_exec_host_case or sessions_patch_persists_current_session_metadata_and_surfaces_it"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.patch` now normalizes `elevatedLevel` aliases such as
  `auto-approve` / `autoapprove` to `full` and approval aliases to `ask`.
- Verified the `sessions.patch` elevated-level seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_patch_normalizes_elevated_level_alias or sessions_patch_persists_current_session_metadata_and_surfaces_it"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.patch` now normalizes `sendPolicy` case and rejects unsupported
  values using the OpenClaw `allow` / `deny` contract.
- Verified the `sessions.patch` send-policy seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_patch_normalizes_send_policy_case or sessions_patch_persists_metadata_backed_child_session"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.patch` now normalizes `groupActivation` case and rejects
  unsupported values using the OpenClaw `mention` / `always` contract.
- Verified the `sessions.patch` group-activation seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_patch_normalizes_group_activation_case or sessions_patch_persists_current_session_metadata_and_surfaces_it"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.delete deleteTranscript=false` now deletes metadata/session entry
  while retaining transcript messages and returning no archived transcript,
  matching OpenClaw's `deleted && deleteTranscript` archival split.
- Verified the `sessions.delete` retained-transcript seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_delete_false_deletes_entry_and_retains_transcript or sessions_delete_removes_metadata_backed_session_and_transcript"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "sessions_delete or sessions_reset or sessions_patch or sessions_create or sessions_spawn or tools_invoke"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `chat.send timeoutMs` now uses OpenClaw's timer-safe resolver semantics:
  `0` maps to the no-timeout sentinel and values above the timer-safe ceiling
  clamp to `2_147_000_000` instead of being rejected.
- Verified the `chat.send` timeout-clamp seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_send_clamps_large_timeout_ms_like_openclaw or chat_send_returns_run_ack_from_injected_control_chat_bridge"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "chat_send or chat_history"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `chat.send sessionKey` now applies OpenClaw's protocol-level 512-character
  max before runtime dispatch.
- Verified the `chat.send` session-key cap seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_send_rejects_session_key_above_openclaw_limit or chat_send_returns_run_ack_from_injected_control_chat_bridge"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "chat_send or chat_history"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `chat.send systemInputProvenance` now validates the OpenClaw schema before
  scope checks, rejecting non-object values and unsupported `kind` values
  instead of silently omitting them.
- Verified the `chat.send` provenance-validation seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_send_rejects_invalid_system_input_provenance_kind or chat_send_rejects_non_object_system_input_provenance or chat_send_system_provenance_fields_require_admin_scope_before_runtime or chat_send_system_provenance_fields_preserve_runtime_context"`, API-focused `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "system_input_provenance or system_provenance"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "chat_send or chat_history"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `chat.inject` now applies OpenClaw's schema guards for non-empty `message`
  and `label` length (`<= 100`) before appending assistant transcript rows.
- Verified the `chat.inject` validation seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_inject"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "chat_inject or chat_send or chat_history"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `chat.abort` now applies OpenClaw's optional-but-non-empty `runId` schema,
  rejecting `runId: ""` instead of widening it into a session-scoped abort.
- Verified the `chat.abort` run-id seam with `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "chat_abort_rejects_empty_run_id_like_openclaw or rejects_empty_chat_abort_run_id or chat_abort_interrupts_tracked_gateway_run_with_injected_runtime"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "chat_abort or chat_inject or chat_send or chat_history"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `agent.wait` now consumes spawned-session `cleanup: "delete"` policy for
  terminal tracked child runs, deleting the ephemeral child transcript and
  metadata after returning the terminal snapshot.
- Verified the terminal spawn-cleanup seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_applies_spawn_cleanup_delete_on_terminal_child_run"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_defaults_omitted_run_timeout_to_zero or sessions_spawn_persists_completion_expectation_override"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `agent.wait` now also emits a parent-visible completion message for terminal
  spawned child runs by consuming `parentSessionKey` and
  `expectsCompletionMessage` metadata.
- Verified the wait-consumed completion announcement seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_announces_spawn_completion_to_parent_session or agent_wait_skips_spawn_completion_announcement_when_not_expected"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `update.run` now returns the OpenClaw-shaped runtime-control envelope
  (`ok`, `result`, `restart`, `sentinel`) instead of the flat update view,
  clamps tiny `timeoutMs` values to the upstream 1000ms minimum, writes a
  data-dir restart sentinel payload with session delivery/note/thread context,
  and only reports a restart object when the native update tick actually
  requested one.
- `update.run` now also executes a native fakeable update runner before
  restart projection: the app/CLI wire through `RuntimeUpdateService.run_update`,
  the service performs git clean/fetch/pull plus Python install/build steps,
  dirty worktrees return `status="skipped"` / `reason="dirty"`, and successful
  runner results drive the OpenClaw-shaped restart payload plus sentinel stats.
- Verified the `update.run` envelope/sentinel seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "update_run"`, endpoint proof `python -m pytest tests\test_gateway_nodes_api.py -q -k "update_run"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "update_run or config_write_methods_persist_control_ui_config_with_base_hash or supports_config_set_patch_apply"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- Verified the native update-runner seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_update_run_executes_native_update_runner_before_restart_scheduling
  tests\test_runtime_updates.py::test_runtime_update_run_update_executes_native_git_install_build_steps
  tests\test_runtime_updates.py::test_runtime_update_run_update_skips_dirty_worktree_before_fetch
  -q`, adjacent `python -m pytest tests\test_runtime_updates.py -q`,
  endpoint proof `python -m pytest tests\test_gateway_node_methods.py
  tests\test_gateway_nodes_api.py -q -k "update_run"`, `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\runtime_updates.py src\openzues\app.py
  src\openzues\cli.py tests\test_gateway_node_methods.py
  tests\test_gateway_nodes_api.py tests\test_runtime_updates.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\runtime_updates.py src\openzues\app.py
  src\openzues\cli.py`.
- `config.patch` and `config.apply` now consume the same OpenClaw restart
  request fields they already validated, returning `config-patch` /
  `config-apply` restart sentinels with session delivery context, note,
  thread id, config path stats, and a written data-dir sentinel file while
  preserving the native no-direct-restart posture.
- Verified the config restart-sentinel seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "config_write_methods_persist_control_ui_config_with_base_hash"`, endpoint proof `python -m pytest tests\test_gateway_nodes_api.py -q -k "config_write_lifecycle"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "config_write_methods_persist_control_ui_config_with_base_hash or config_write_lifecycle or update_run"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `config.patch` now also matches OpenClaw's no-op branch: patches that
  validate but do not change the native config return `noop=true`, preserve the
  current hash/config/path payload, and skip restart/sentinel decoration while
  still enforcing the existing base-hash guard.
- Verified the config no-op seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "config_patch_noop_skips_restart_sentinel or config_write_methods_persist_control_ui_config_with_base_hash"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "config_patch_noop_skips_restart_sentinel or config_write_methods_persist_control_ui_config_with_base_hash or config_write_lifecycle or update_run"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\services\gateway_config.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\services\gateway_config.py`.
- `secrets.resolve` now has the upstream-shaped command-target resolver seam:
  OpenZues trims the command and target ids, filters empty targets, rejects
  unknown OpenClaw secret target ids before dispatch, calls a fakeable native
  resolver, and validates the returned assignments/diagnostics/inactive refs
  into the OpenClaw `{ok, assignments, diagnostics, inactiveRefPaths}` result.
- Verified the `secrets.resolve` resolver seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "secrets_resolve or secrets_reload"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "secrets_resolve or secrets_reload or config_patch_noop_skips_restart_sentinel or update_run"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `models.authStatus` now returns a native OpenClaw-shaped auth snapshot
  instead of the placeholder unavailable response. The `GatewayModelsService`
  owner supports a fakeable auth-status runtime, TTL caching with
  `refresh=true` bypass, sanitized provider/profile projection, empty native
  snapshots when no instances are present, and missing-provider synthesis for
  refreshable configured providers without env-backed API keys.
- Verified the `models.authStatus` seam with `python -m pytest tests\test_gateway_models.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "models_auth_status"`, adjacent `python -m pytest tests\test_gateway_models.py -q`, `python -m pytest tests\test_cli.py -q -k "model_auth_status or models_status or infer_model_auth"`, `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "models_auth_status or models_list or secrets_resolve or secrets_reload"`, `ruff check src\openzues\services\gateway_models.py src\openzues\services\gateway_node_methods.py tests\test_gateway_models.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_models.py src\openzues\services\gateway_node_methods.py`.
- `chat.abort` now enforces OpenClaw's tracked-run ownership guard. Runs store
  owner connection/device metadata when started through `chat.send`,
  `sessions.send`, `sessions.steer`, `sessions.spawn`, `sessions.create`, and
  `agent`; explicit and session-scoped aborts from other requesters return
  `INVALID_REQUEST` / `unauthorized`, same-device reconnects remain allowed,
  admin callers bypass the owner check, and legacy ownerless tracked runs keep
  the historical compatible behavior.
- Verified the `chat.abort` ownership seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_abort"`, API proof `python -m pytest tests\test_gateway_nodes_api.py -q -k "chat_abort"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_abort or sessions_steer or sessions_abort or compaction_restore"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `chat.abort` now persists OpenClaw-shaped aborted assistant partials from the
  native abort adapter. OpenZues stores them once per `runId:assistant` in the
  SQLite transcript, stamps `stopReason="stop"` plus `openclawAbort` metadata,
  preserves `/stop` as `origin="stop-command"`, ignores blank partials, and
  projects the metadata through `chat.history`.
- Verified the abort partial transcript seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_abort_persists_partial_assistant_transcript_like_openclaw or chat_send_stop_persists_abort_partial_with_stop_command_origin or chat_abort"`, API proof `python -m pytest tests\test_gateway_nodes_api.py -q -k "chat_abort"`, adjacent transcript proof `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_abort or chat_history or sessions_history"`, shared session read-model proof `python -m pytest tests\test_gateway_sessions.py -q -k "message_payloads_surface or transcript_usage or control_chat"`, `ruff check src\openzues\database.py src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\database.py src\openzues\services\gateway_node_methods.py`.
- Closed the OpsMesh provider-runtime poll option-cap seam: direct poll calls
  now validate channel-specific OpenClaw caps before provider route lookup, and
  Telegram/Discord/WhatsApp native provider post helpers apply the same guard
  before replay/provider payload dispatch. Verified with `python -m pytest
  tests\test_ops_mesh.py -q -k "rejects_provider_option_caps"`, adjacent
  native poll pack `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_uses_telegram_native_route or
  send_direct_channel_poll_uses_discord_native_route or
  send_direct_channel_poll_uses_whatsapp_native_route or
  rejects_provider_option_caps or rejects_invalid_telegram_durations"`,
  `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py`.
- Closed the poll `maxSelections` option-count seam from OpenClaw
  `normalizePollInput`: Gateway `poll` and OpsMesh direct/native provider poll
  paths now reject `maxSelections` values above the cleaned option count before
  runtime dispatch or replay/provider post construction. Verified with
  `python -m pytest tests\test_gateway_node_methods.py -q -k
  "poll_rejects_max_selections_above_option_count"`, `python -m pytest
  tests\test_ops_mesh.py -q -k "rejects_max_selections_above_options"`,
  adjacent gateway/OpsMesh poll packs, `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py tests\test_gateway_node_methods.py
  tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py`.
- Closed the poll duration mutual-exclusion seam from OpenClaw
  `normalizePollInput`: Gateway `poll` and OpsMesh direct/native provider poll
  paths now reject requests that set both `durationSeconds` and
  `durationHours` before runtime dispatch or replay/provider post
  construction. Verified with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "poll_rejects_mutual_duration_fields"`, `python -m pytest
  tests\test_ops_mesh.py -q -k "rejects_invalid_telegram_durations"`,
  adjacent gateway/OpsMesh poll packs, `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py tests\test_gateway_node_methods.py
  tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py`.
- Closed the blank poll option filtering seam from OpenClaw
  `normalizePollInput`: Gateway `poll` and OpsMesh direct/provider poll
  delivery now trim options and drop blank entries before validation, dispatch,
  persisted delivery payloads, and native provider payload construction.
  Verified with `python -m pytest tests\test_gateway_node_methods.py -q -k
  "test_poll_uses_channel_poll_runtime"`, `python -m pytest
  tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_uses_telegram_native_route"`, adjacent
  gateway/OpsMesh poll packs, `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py tests\test_gateway_node_methods.py
  tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py`.
- Closed the omitted poll `maxSelections` default seam from OpenClaw
  `normalizePollInput`: Gateway `poll`, OpsMesh direct/provider poll delivery,
  and the shared outbound runtime now normalize missing `maxSelections` to `1`
  before runtime dispatch, persisted delivery payloads, and native/provider
  request construction. Verified with `python -m pytest
  tests\test_gateway_node_methods.py -q -k "test_poll_uses_channel_poll_runtime"`,
  `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_uses_gateway_route_adapter or
  gateway_outbound_runtime_poll_defaults_max_selections_to_one"`, adjacent
  gateway/OpsMesh poll packs, `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py
  tests\test_gateway_node_methods.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- Closed the remaining OpsMesh poll shape guards from OpenClaw
  `normalizePollInput`: direct/provider poll delivery now rejects empty
  questions and fewer than two cleaned options before provider lookup,
  persisted delivery creation, route-backed runtime posting, or native provider
  payload construction. Verified with `python -m pytest
  tests\test_ops_mesh.py -q -k "rejects_invalid_poll_shape"`, adjacent OpsMesh
  provider poll pack, `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Closed the `agents.files.list` primary-memory projection seam: OpenZues now
  mirrors OpenClaw by listing `MEMORY.md` when present, falling back to legacy
  `memory.md` only when the primary file is absent, instead of returning both.
  Verified with `python -m pytest tests\test_gateway_node_methods.py -q -k
  "agents_files_list_prefers_primary_memory_file_like_openclaw"`, adjacent
  agent-files pack, `ruff check
  src\openzues\services\gateway_agent_files.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_agent_files.py`.
- Closed the ACP sandboxed-requester policy seam: `sessions.spawn
  runtime="acp"` now rejects sandboxed requester sessions before ACP target
  resolution or runtime dispatch, using the OpenClaw host-runtime error while
  preserving the existing explicit `sandbox="require"` ACP rejection. Verified
  with `python -m pytest tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_rejects_sandboxed_requester_to_acp_runtime"`, adjacent ACP
  spawn policy/runtime pack, `ruff check
  src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py`.
- Closed the `tools.invoke` scoped plugin visibility seam: plugin executors
  are no longer gated solely by `gateway.tools.allow`; non-core plugin tools
  can be exposed by the invoking agent's OpenClaw-style `tools.allow` policy,
  while the existing gateway default-deny behavior for high-risk core tools
  remains intact. Verified with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "tools_invoke_runs_plugin_executor_from_agent_tool_allowlist"`, adjacent
  `tools.invoke` plugin pack, config smoke, `ruff check
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py`.
- Closed the doctor sandbox shared-scope override warning seam: `doctor --json`
  now adds OpenClaw-shaped warnings when agent-level `sandbox.docker`,
  `sandbox.browser`, or `sandbox.prune` overrides resolve to `scope="shared"`
  and would be ignored. Verified with `python -m pytest tests\test_cli.py -q
  -k "doctor_json_warns_about_shared_sandbox_agent_overrides"`, adjacent doctor
  sandbox/lock pack, `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Closed the sandboxed session-tools visibility clamp seam: `tools.invoke`
  session history/status/send/list access now treats sandboxed requesters as
  tree/spawned-scoped when sandbox `sessionToolsVisibility` is omitted or
  `spawned`, while explicit `sessionToolsVisibility="all"` keeps the broader
  configured visibility. Verified with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_history_clamps_sandboxed_requester_to_tree_visibility or
  sessions_history_allows_sandboxed_requester_when_visibility_all"`, adjacent
  sessions visibility pack, `ruff check
  src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py`.
- Closed the `chat.inject` parent-link seam from OpenClaw
  `chat.inject.parentid.test.ts`: injected assistant transcript rows now record
  the current control-chat leaf as `parentId` metadata and project that linkage
  through `chat.history` plus session message payloads. Verified with
  `python -m pytest
  tests\test_gateway_node_methods.py::test_chat_inject_records_parent_id_from_current_transcript_leaf -q`,
  adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k
  "chat_inject or chat_history"`, `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_sessions.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_sessions.py`.
- Closed the cron direct-announce replay idempotency seam from OpenClaw
  `delivery-dispatch.double-announce.test.ts`: explicit cron failure announce
  and failure-alert channel deliveries now pass stable
  `cron-direct-delivery:v1:*` idempotency keys into the shared direct-channel
  delivery owner, so repeated handling of the same failed cron execution reuses
  the saved delivered row instead of double-sending. Verified with
  `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_dedupes_replayed_cron_failure_announce_delivery -q`,
  adjacent `python -m pytest tests\test_ops_mesh.py -q -k
  "explicit_cron_failure_to_announce or replayed_cron_failure_announce or
  send_direct_channel_message_dedupes_inflight_idempotent_retries or
  replay_outbound_deliveries_retries_saved_failed_announce_delivery"`, `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Closed the first `chat.send` mixed attachment ordering seam from OpenClaw
  `chat.directive-tags.test.ts` / `chat-attachments.ts`: effective image
  attachments now carry `imageOrder` through the native attachment runtime,
  using OpenClaw's 2 MB decoded-size inline/offloaded boundary, and the
  app-wired control-chat path persists that ordering metadata on the user turn.
  Verified with `python -m pytest
  tests\test_gateway_node_methods.py::test_chat_send_passes_image_order_for_mixed_inline_and_offloaded_attachments
  tests\test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_preserves_chat_send_attachment_image_order -q`,
  adjacent `python -m pytest tests\test_gateway_node_methods.py
  tests\test_gateway_nodes_api.py -q -k "chat_send and attachment"`, `ruff
  check src\openzues\services\gateway_node_methods.py
  src\openzues\services\control_chat.py src\openzues\app.py
  tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and
  `mypy src\openzues\services\gateway_node_methods.py
  src\openzues\services\control_chat.py src\openzues\app.py`.
- Closed the bundled plugin runtime dependency doctor seam from OpenClaw
  `doctor-bundled-plugin-runtime-deps.test.ts` /
  `bundled-runtime-deps.ts`: OpenZues now reads manifest-adjacent
  `package.json` `dependencies` and `optionalDependencies`, exposes them
  through plugin inventory/inspect JSON, computes bundled install roots, skips
  source checkouts, honors enabled channel plugin config, suppresses installed
  dependency sentinels, and reports missing deps plus conflicting versions
  through `plugins doctor --json`. Verified with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies
  tests\test_cli.py::test_plugins_doctor_json_reports_missing_bundled_runtime_dependencies
  tests\test_cli.py::test_plugins_doctor_json_limits_runtime_deps_to_enabled_channel_plugins
  -q`, adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_list_json_discovers_openclaw_manifest_load_paths or runtime_deps or
  runtime_dependencies or plugins_doctor or
  plugins_inspect_json_projects_runtime_executor_tools"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the top-level bundled plugin runtime dependency doctor contribution
  seam from OpenClaw `doctor-health-contributions.ts`: `doctor --json` now
  includes the `doctor:bundled-plugin-runtime-deps` contribution, reusing the
  native dependency scanner and reporting missing deps, conflicts, diagnostics,
  and a truthful no-install repair boundary. Verified with `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_bundled_plugin_runtime_dependency_contribution
  -q`, adjacent `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_bundled_plugin_runtime_dependency_contribution or
  doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_and_update_status_json_include_hermes_sections or
  plugins_doctor_json_reports_missing_bundled_runtime_dependencies or
  plugins_doctor_json_limits_runtime_deps_to_enabled_channel_plugins"`, `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the structured `doctor:sandbox` contribution seam from OpenClaw
  `doctor-sandbox.ts` / `doctor-health-contributions.ts`: `doctor --json` now
  reports resolved sandbox mode/backend, Docker availability, missing-Docker
  and shared-scope override warnings, status, summary, and the current
  no-install repair boundary as structured data instead of warning text only.
  Verified with `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_sandbox_contribution -q`,
  adjacent `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_sandbox_contribution or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_warns_about_shared_sandbox_agent_overrides or
  doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution or
  doctor_and_update_status_json_include_hermes_sections"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the first structured `doctor:memory-search` gateway probe seam from
  OpenClaw `doctor-gateway-health.ts` / `doctor-memory-search.ts`: `doctor
  --json` now calls the native `doctor.memory.status` gateway method when
  available, records checked/ready/error/provider state, and projects the
  OpenClaw-shaped "Gateway memory probe for default agent is not ready"
  warning into structured JSON. Verified with `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_gateway_memory_probe_contribution
  -q`, adjacent `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_sandbox_contribution or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution or
  doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_and_update_status_json_include_hermes_sections"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the compact CLI root-option token seam from OpenClaw
  `cli-root-options.ts`: the native CLI now accepts `--dev`, `--no-color`,
  `--profile`, `--log-level`, and `--container` before subcommands, and its
  token helpers match OpenClaw's handling of negative numeric values, `--`
  terminators, `--flag=value` forms, and missing values. Verified with
  `python -m pytest
  tests\test_cli.py::test_root_option_token_consumption_matches_openclaw_reference_cases
  tests\test_cli.py::test_root_openclaw_compat_options_are_accepted_before_command
  -q`, adjacent `python -m pytest tests\test_cli.py -q -k "root_option or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_sandbox_contribution or
  health_json_surfaces_gateway_health_snapshot"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the repair-mode `doctor:startup-channel-maintenance` seam from
  OpenClaw `doctor-startup-channel-maintenance.ts`: `doctor --fix` / `--repair`
  now calls a fakeable native channel startup maintenance adapter with
  `trigger="doctor-fix"` and `logPrefix="doctor"`, while non-repair doctor
  reports the contribution as skipped and repair mode without an adapter keeps
  an honest unavailable boundary. Verified with `python -m pytest
  tests\test_cli.py::test_doctor_fix_runs_startup_channel_maintenance_adapter
  tests\test_cli.py::test_doctor_skips_startup_channel_maintenance_without_fix
  -q`, adjacent `python -m pytest tests\test_cli.py -q -k
  "startup_channel_maintenance or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution or
  root_openclaw_compat"`, `ruff check src\openzues\cli.py tests\test_cli.py`,
  and `mypy src\openzues\cli.py`.
- Closed the structured `doctor:gateway-health` contribution seam from
  OpenClaw `doctor-gateway-health.ts` / `doctor-health-contributions.ts`:
  `doctor --json` now runs the native bounded health probe, calls
  `channels.status` with OpenClaw-shaped probe options when health is up, and
  returns channel warning metadata for degraded provider accounts without
  treating unsupported provider probe hooks as warnings. Verified with
  `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_gateway_health_contribution_and_channel_warnings
  -q`, adjacent `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_gateway_health_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution or
  startup_channel_maintenance or
  channels_status_json_calls_gateway_method_owner_with_probe"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the OpenCode provider override warning seam from OpenClaw
  `doctor.warns-state-directory-is-missing.e2e.test.ts`: `doctor --json` now
  reports `providerOverrides.opencode` and a top-level warning when legacy
  `models.providers.opencode` or `models.providers.opencode-go` config shadows
  bundled provider defaults. Verified with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_opencode_provider_overrides
  -q`, adjacent `python -m pytest tests\test_cli.py -q -k
  "doctor_json_warns_about_opencode_provider_overrides or
  doctor_json_warns_when_state_directory_is_missing or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the Codex OAuth provider override warning seam from OpenClaw
  `doctor-auth.ts` and
  `doctor.warns-state-directory-is-missing.e2e.test.ts`: `doctor --json` now
  reports `providerOverrides.openaiCodex` and a top-level warning when legacy
  `models.providers.openai-codex` OpenAI transport settings shadow configured
  or stored Codex OAuth profiles. Inline legacy model transport entries warn,
  while custom proxy, header-only, and no-OAuth overrides stay quiet. Verified
  with `python -m pytest tests\test_cli.py -q -k "codex_provider_override or
  codex_inline_model or codex_override_warning"`, adjacent `python -m pytest
  tests\test_cli.py -q -k "codex_provider_override or codex_inline_model or
  codex_override_warning or opencode_provider_overrides or
  state_directory_is_missing or sandbox_enabled_without_docker or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the local gateway-auth doctor warning seam from OpenClaw
  `doctor-health-contributions.ts` and
  `doctor.warns-state-directory-is-missing.e2e.test.ts`: `doctor --json` now
  reports `gatewayAuth` warnings for explicit local gateway configs with
  missing token auth, ambiguous token/password credentials without
  `gateway.auth.mode`, and unresolved SecretRef-managed gateway tokens.
  `OPENCLAW_GATEWAY_TOKEN` suppresses the missing-token warning. Verified with
  `python -m pytest tests\test_cli.py -q -k "gateway_auth_missing_local_token or
  gateway_auth_warning_when_env_token or gateway_auth_mode_is_ambiguous or
  secretref_gateway_token"`, adjacent `python -m pytest tests\test_cli.py -q -k
  "gateway_auth_missing_local_token or gateway_auth_warning_when_env_token or
  gateway_auth_mode_is_ambiguous or secretref_gateway_token or
  codex_provider_override or codex_inline_model or codex_override_warning or
  opencode_provider_overrides or state_directory_is_missing or
  sandbox_enabled_without_docker or doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the browser doctor facade fallback seam from OpenClaw
  `doctor-browser.ts` and
  `doctor.warns-state-directory-is-missing.e2e.test.ts`: top-level
  `doctor --json` now reports a structured `doctor:browser` unavailable
  contribution when browser health is configured via `browser.defaultProfile`
  or an `existing-session` profile but no native browser doctor facade/adapter
  is registered. Verified with `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_browser_health_unavailable_when_facade_missing
  -q`, adjacent `python -m pytest tests\test_cli.py -q -k
  "browser_health_unavailable or gateway_auth_missing_local_token or
  gateway_auth_warning_when_env_token or gateway_auth_mode_is_ambiguous or
  secretref_gateway_token or codex_provider_override or codex_inline_model or
  codex_override_warning or opencode_provider_overrides or
  state_directory_is_missing or sandbox_enabled_without_docker or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the `doctor:gateway-config` missing-mode warning seam from OpenClaw
  `doctor-health-contributions.ts`: explicit native gateway config without
  `gateway.mode` now produces a structured `gatewayConfig` warning with
  configure/setup-style repair guidance. Verified with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_gateway_mode_is_unset -q`,
  adjacent `python -m pytest tests\test_cli.py -q -k "gateway_mode_is_unset or
  browser_health_unavailable or gateway_auth_missing_local_token or
  gateway_auth_warning_when_env_token or gateway_auth_mode_is_ambiguous or
  secretref_gateway_token or codex_provider_override or codex_inline_model or
  codex_override_warning or opencode_provider_overrides or
  state_directory_is_missing or sandbox_enabled_without_docker or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the first `doctor:claude-cli` health seam from OpenClaw
  `doctor-claude-cli.ts`: top-level `doctor --json` now emits a structured
  `claudeCli` warning when Claude CLI models or backends are configured,
  reporting binary availability, headless-auth posture, missing
  `anthropic:claude-cli` auth profile guidance, and fix hints without opening
  an interactive credential prompt. Verified with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_claude_cli_model_is_configured_but_unavailable
  -q`, adjacent `python -m pytest tests\test_cli.py -q -k
  "claude_cli_model_is_configured or gateway_mode_is_unset or
  browser_health_unavailable or gateway_auth_missing_local_token or
  gateway_auth_warning_when_env_token or gateway_auth_mode_is_ambiguous or
  secretref_gateway_token or codex_provider_override or codex_inline_model or
  codex_override_warning or opencode_provider_overrides or
  state_directory_is_missing or sandbox_enabled_without_docker or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"`, `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Closed the provider-native `gatewayClientScopes` seam from OpenClaw
  `gateway/server-methods/send.ts`: direct send and poll now pass normalized
  gateway client scopes into provider runtime requests, route-backed provider
  event payloads, and persisted delivery payloads, including explicit empty
  arrays when the caller has no scopes. Verified with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_prefers_provider_runtime
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_poll_prefers_provider_runtime
  -q`, adjacent `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_message_prefers_provider_runtime or
  send_direct_channel_poll_prefers_provider_runtime or
  gateway_outbound_runtime_poll_defaults_max_selections_to_one or
  send_direct_channel_message_uses_native_adapter_binding or
  send_direct_channel_poll_uses_native_adapter_binding or
  send_direct_channel_message_uses_gateway_route_adapter or
  send_direct_channel_message_preserves_provider_native_options"`, `ruff check
  src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py`.
- Closed the provider-native requester context seam from OpenClaw
  `infra/outbound/outbound-send-service.ts`: direct send now distinguishes the
  runtime delivery `sessionKey` from requester metadata and forwards
  `requesterSessionKey`, `requesterAccountId`, `requesterSenderId`, and
  sender display fields into provider runtime requests, route-backed provider
  event payloads, and persisted delivery payloads. Verified with `python -m
  pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_forwards_requester_context
  -q`, adjacent `python -m pytest tests\test_ops_mesh.py -q -k
  "requester_context or send_direct_channel_message_mirrors_explicit_session_key
  or send_direct_channel_message_prefers_provider_runtime or
  send_direct_channel_message_preserves_provider_native_options or
  send_direct_channel_message_uses_native_adapter_binding"`, `ruff check
  src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py`.
- Closed the WhatsApp multi-media result seam from OpenClaw's outbound payload
  contract helper: multi-media WhatsApp sends now return the final provider
  message id as canonical `messageId` while preserving the ordered `mediaIds`
  list. Verified with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_splits_whatsapp_media
  -q`, adjacent `python -m pytest tests\test_ops_mesh.py -q -k
  "whatsapp_media or whatsapp_document_reply or whatsapp_gif or whatsapp_text
  or send_direct_channel_message_splits_whatsapp_media"`, `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Closed the Slack native media upload auth seam from OpenClaw
  `extensions/slack/src/send.ts`: route-backed media upload now passes the raw
  Slack route token into the upload helper and relies on the Slack form poster
  to apply a single `Bearer` wrapper, preserving thread/reply upload metadata
  without double-wrapping authorization. Verified with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_slack_native_route
  -q`, adjacent `python -m pytest tests\test_ops_mesh.py -q -k
  "slack_native_route or slack_reply_to or slack_media_download or
  send_direct_channel_message_uses_slack_native_route or
  message_action_dispatches_slack"`, `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Closed the Telegram route-backed media/force-document seam from OpenClaw
  `src/plugin-sdk/reply-payload.ts`, `extensions/telegram/src/outbound-adapter.ts`,
  and `extensions/telegram/src/send.ts`: native route-backed multi-media sends
  now use individual Telegram `sendPhoto`/`sendDocument` calls with the caption
  on the first send, return the final send's message id, preserve ordered media
  ids, and include `disable_content_type_detection` for forced document sends.
  Verified with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_telegram_native_options
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_telegram_media_group
  -q`, adjacent `python -m pytest tests\test_ops_mesh.py -q -k
  "telegram_native_route or telegram_native_options or telegram_topic or
  telegram_media_group or invalid_telegram_durations"`, `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- The queue head now tracks the remaining advertised runtime-control hard gaps,
  especially broader runtime/client integration, provider replay/direct
  announce consistency, remaining runtime bridge doctor/packaging checks, and
  session runtime methods (`chat.*`, `sessions.*`), rather than the older
  approval lifecycle/config/device-token/agent-mutation/memory-doctor/placeheld
  provenance/false steer-runtime/custom-agent-session/plugin-dependency
  placeholders.
