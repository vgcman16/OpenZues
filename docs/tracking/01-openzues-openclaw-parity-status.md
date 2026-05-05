# OpenZues OpenClaw Parity Status

Agent report source: Gauss

Last updated: 2026-05-05

Primary ledgers:

- `docs/openclaw-parity-progress.md`
- `docs/openclaw-parity-unresolved-seams.md`

Use the progress ledger snapshot as the freshest percentage source. The README
may lag behind this tracker.

## Percentage Rollup

| Family | Percent | Confidence | Notes |
| --- | ---: | --- | --- |
| Repo-wide OpenClaw parity | ~77.7% | Medium | Breadth-weighted planning estimate, not generated metric |
| Active gateway/session/tool-contract family | ~99.9% | High for bounded local path | Does not mean whole product parity |
| Chat/session contract subfamily | ~98.3% | High for bounded local path | Current local session/chat contracts are near complete |
| Browser/canvas/nodes/voice bounded command family | ~99% | High for bounded local path | No longer active queue head |
| Runtime/CLI/doctor native bridge | ~99.9% | High for bounded native bridge | Packaging, ACP bridge depth, and deeper installed plugin activation remain |
| CLI/operator control plane | ~99.9% | High for bounded native path | Remaining gaps are deeper plugin import/activation and packaging surfaces |

## Implemented / Locked Bounded Areas

- [x] Gateway method registry, policy wiring, strict parameter guards, config
  lookup/mutation, node invoke guards, device pairing, approvals, and node/global
  exec policies.
  - Status: verified in ledger
  - Last verified: see `docs/openclaw-parity-progress.md`

- [x] Cron local scheduling, due-run detection, delivery status, fallback
  announcement, session delivery fallback, system-event session wake routing,
  retry/backoff, one-shot cleanup, and OpenClaw-style CLI schedule parsing.
  - Status: verified in ledger

- [x] Browser/canvas/nodes/voice bounded bridge, including native browser
  commands, APNS wake paths, canvas/A2UI/live reload, scoped capability URLs,
  managed attachments, and iOS provider command bridges.
  - Status: verified in ledger

- [x] Chat transcript and `chat.*` local contracts for history projection, usage
  metadata, abort metadata, text caps, oversized placeholders, untrusted suffix
  stripping, directive cleanup, schema/provenance/timeout/session-key guards,
  inject guards, and abort ownership validation.
  - Status: verified in ledger

- [x] Session tool contracts for `sessions_history`, `session_status`,
  `sessions_list`, `sessions_send`, `sessions_yield`, `sessions.create`,
  `sessions.patch`, `sessions.pluginPatch`, `sessions.delete`,
  `sessions.preview`, and direct session REST/SSE behavior.
  - Status: verified in ledger

- [x] `tools.invoke` core bridge for allow/deny policy, owner-only controls,
  before-call hooks, ordered registry-backed plugin runtime service envelopes,
  safe core mappings, plugin error projection, and related session tool
  projection.
  - Status: verified in ledger

- [x] `plugins.uiDescriptors` plugin-host gateway method for active registry
  control UI descriptor projection, empty-param validation, descriptor
  `pluginId`/`pluginName` stamping, JSON-compatible schema preservation, and
  valid required-scope projection.
  - Status: checkpointed in `9fb5098b`

- [x] Plugin manifest activation-plan reason projection in `plugins doctor
  --json`, covering command aliases, providers, setup providers, agent
  harnesses, channels, routes, and capability triggers with upstream
  `activation-*` and `manifest-*` reason strings.
  - Status: checkpointed in `721ec0f2`

- [x] Plugin registry inspect/refresh CLI parity for persisted native plugin
  registry state, including `missing`/`fresh`/`stale` state projection,
  refresh reasons, and JSON-capable registry refresh persistence.
  - Status: checkpointed in `cdb3035e`

- [x] Plugin list persisted-registry source projection in `plugins list
  --json`, including persisted/derived registry source metadata and
  OpenClaw-shaped registry diagnostics.
  - Status: checkpointed in `6468e305`

- [x] Plugin inspect runtime-inspection flag in `plugins inspect --runtime`,
  including explicit runtime posture and imported-state projection for loaded
  non-bundle metadata rows.
  - Status: checkpointed in `5fce4371`

- [x] Plugin inspect runtime missing-target static preflight, preserving the
  OpenClaw guard that avoids runtime inspection when the target plugin is
  absent.
  - Status: checkpointed in `9a9e89f2`

- [x] Plugin inspect runtime target-scoped inventory, matching OpenClaw's
  `onlyPluginIds` diagnostics-report posture for `plugins inspect --runtime`.
  - Status: checkpointed in `c412b98b`

- [x] Installed plugin activation-state projection for config/install records,
  preserving OpenClaw-shaped `activated`, `explicitlyEnabled`,
  `activationSource`, and `activationReason` fields.
  - Status: checkpointed in `78658f29`

- [x] Installed plugin allowlist activation guard for config/install records,
  preserving OpenClaw's `not in allowlist` activation decision.
  - Status: checkpointed in `73089117`

- [x] Installed plugin slot activation reasons for config/install records,
  preserving OpenClaw's `selected memory slot` activation decision.
  - Status: checkpointed in `209dced0`

- [x] Bundled plugin env discovery/default-disable gate, discovering
  `OPENCLAW_BUNDLED_PLUGINS_DIR` manifests while keeping bundled plugins
  disabled by default unless upstream activation rules enable them.
  - Status: checkpointed in `3de3621e`

- [x] Installed plugin runtime entry-source metadata, exposing
  `runtimeEntrySource` / `runtimeEntrySources` from package
  `openclaw.extensions` or default `index.*` candidates to native activation
  adapters.
  - Status: checkpointed in `4f732754`

- [x] Bundled plugin runtime entry import without a fake activation adapter,
  including CommonJS OpenClaw plugin-SDK alias shims and native
  `register`/`activate` tool collection.
  - Status: checkpointed in `8cb314f4`

- [x] Imported CommonJS plugin runtime execution through `tools.invoke`,
  preserving registered tool `execute(toolCallId, args)` behavior with a
  bounded native Node bridge.
  - Status: checkpointed in `d80b0252`

- [x] Imported ESM-style plugin runtime execution through `tools.invoke`,
  preserving transformed `export default` runtime entries and
  `openclaw/plugin-sdk/text-runtime` alias behavior through the bounded native
  Node bridge.
  - Status: checkpointed in `311f37e1`

- [x] Imported plugin runtime tool factory context through `tools.invoke`,
  preserving `api.registerTool(factory, { name })` discovery and passing
  OpenClaw-shaped config, workspace, agent/session, sender ownership, and
  delivery route metadata to request-time factories.
  - Status: checkpointed in `ef254cbf`

- [x] Imported plugin SDK text-runtime helper shim for common string-coerce
  helpers, preserving `normalizeOptionalString`, `normalizeNullableString`,
  `normalizeStringifiedOptionalString`, and `hasNonEmptyString` for imported
  runtime tools.
  - Status: checkpointed in `91918c38`

- [x] Imported plugin SDK error-runtime helper shim for common error
  formatting and extraction helpers, preserving `formatErrorMessage`,
  `formatUncaughtError`, `extractErrorCode`, and `readErrorName` for imported
  runtime tools.
  - Status: checkpointed in `7888c8de`

- [x] Imported plugin SDK temp-path helper shim for temp filename
  sanitization, deterministic temp path construction, preferred temp roots, and
  download-target cleanup helpers.
  - Status: checkpointed in `d6a73b21`

- [x] Imported plugin SDK secret-input helper shim for literal secret
  normalization, SecretRef coercion, inspect-mode resolution, and configured
  secret detection.
  - Status: checkpointed in `76e3c638`

- [x] Imported plugin SDK routing helper shim for common routing/session
  helpers, preserving account and agent id normalization, session key
  parsing/building, thread suffix handling, account lookup, message-channel
  normalization, and outbound thread id normalization for imported runtime
  tools.
  - Status: checkpointed in `2cf7fb27`

- [x] Imported plugin SDK reply-chunking helper shim for length/newline text
  chunking, provider/account chunk limit and mode resolution, and silent reply
  token helpers.
  - Status: checkpointed in `b000f51c`

- [x] Imported plugin SDK reply-payload helper shim for outbound payload
  normalization, media URL extraction/counting, sendable content projection,
  reasoning payload detection, attachment-link formatting, and source-shaped
  media/text send helper exports.
  - Status: checkpointed in `5d628f16`

- [x] Imported plugin SDK account-helper shim for account list/default
  resolution, normalized account lookup, merged account config projection,
  account/webhook snapshots, and account action gates.
  - Status: checkpointed in `6d2cf33b`

- [x] Imported plugin SDK account-core/account-resolution shim for
  account-core reexports, configured id listing, default-account credential
  fallback, chat-type normalization, E.164 normalization, home-relative path
  resolution, and path existence checks.
  - Status: checkpointed in `47fa2f39`

- [x] Imported plugin SDK tool-payload shim for structured tool result payload
  extraction and standalone plain-text tool-call block parsing/stripping.
  - Status: checkpointed in `387717ed`

- [x] Imported plugin SDK boolean-param shim for loose boolean tool parameter
  reading.
  - Status: checkpointed in `65bd842f`

- [x] Imported plugin SDK channel-actions shim for action gates, parameter
  readers, reaction id fallback, result/schema helpers, timestamp
  normalization, media guards, poll selection limits, and available-tag
  parsing.
  - Status: checkpointed in `447d15ff`

- [x] Imported plugin SDK status-helper shim for channel/account status summary
  defaults, runtime snapshots, token/webhook summaries, issue collection, and
  match metadata helpers.
  - Status: checkpointed in `41323ea2`

- [x] Imported plugin SDK channel-status shim for credential snapshot field
  projection, configured-status resolution, pairing-approved message, and
  channel status helper reexports.
  - Status: checkpointed in `14ff20a1`

- [x] Imported plugin SDK text-chunking shim for outbound text chunking with
  newline/space boundary preference and hard-limit fallback.
  - Status: checkpointed in `20267310`

- [x] Imported plugin SDK string-normalization shim for string list
  normalization, slug normalization, and `text-runtime` reexports.
  - Status: checkpointed in `06cd452d`

- [x] Imported plugin SDK dangerous-name shim for provider/account
  break-glass dangerous-name matching flag resolution.
  - Status: checkpointed in `01473fb4`

- [x] Imported plugin SDK channel-logging shim for inbound-drop, typing
  failure, and ack-cleanup failure log message formatting.
  - Status: checkpointed in `c42b0d77`

- [x] Imported plugin SDK time-runtime shim for timezone validation plus UTC
  and zoned timestamp formatting.
  - Status: checkpointed in `eb944ee1`

- [x] Imported plugin SDK number-runtime shim for `parseFiniteNumber`
  coercion of finite numbers and `parseFloat`-style numeric strings.
  - Status: checkpointed in `7e272081`

- [x] Imported plugin SDK secure-random-runtime shim for base64url secure token
  generation and UUID generation.
  - Status: checkpointed in `78d458e7`

- [x] Imported plugin SDK collection-runtime shim for bounded map-cache
  pruning.
  - Status: checkpointed in `624e55e4`

- [x] Imported plugin SDK async-lock-runtime shim for serializing async
  critical sections and releasing the lock after rejections.
  - Status: checkpointed in `9cc677fe`

- [x] Imported plugin SDK transport-ready-runtime shim for success polling,
  timeout logging/error, abort return, and polling interval floor behavior.
  - Status: checkpointed in `dc7e76c6`

- [x] Imported plugin SDK target-resolver-runtime shim for unresolved-target
  row projection and token-trimmed resolver mapping.
  - Status: checkpointed in `4ea6901b`

- [x] Imported plugin SDK response-limit-runtime shim for bounded Response
  buffer reads and custom overflow errors.
  - Status: checkpointed in `7c0035bf`

- [x] Imported plugin SDK text-autolink-runtime shim for file-ref autolink
  detection, including protocol stripping, allowed extension matching, dotted
  parent-segment rejection, and the matching `text-runtime` reexport.
  - Status: checkpointed in `bcce41be`

- [x] Imported plugin SDK dedupe-runtime shim for ttl/max-size in-memory
  dedupe caches and process-global dedupe cache resolution.
  - Status: checkpointed in `865c9df0`

- [x] Imported plugin SDK retry-runtime shim for retry config coercion,
  retry-loop execution, retry-after handling, and rate-limit/Telegram retry
  runner factories.
  - Status: checkpointed in `4608fbc7`

- [x] Imported plugin SDK keyed-async-queue shim for per-key async task
  serialization, queue hooks, failure recovery, and tail-map observability.
  - Status: checkpointed in `4307d460`

- [x] Imported plugin SDK lazy-value shim for memoized lazy factories, literal
  lazy values, and nullish fallback resolution.
  - Status: checkpointed in `ef545716`

- [x] Imported plugin SDK command-primitives-runtime shim for abort and BTW
  command detection, including command-body normalization, bot mentions, and
  abort punctuation handling.
  - Status: checkpointed in `a39876b1`

- [x] Imported plugin SDK media-mime shim for MIME normalization, extension
  mapping, media-kind classification, CAF/PDF/image/ZIP detection, and generic
  SDK / `media-runtime` MIME helper availability.
  - Status: checkpointed in `ad1d6cee`

- [x] Imported plugin SDK command-detection shim for control-command and inline
  command-token detection, including bot-addressed slash normalization,
  inbound metadata stripping, and command authorization gates.
  - Status: checkpointed in `c0c5e8fa`

- [x] Imported plugin SDK global-singleton shim for process-global
  singleton/map resolution and scoped expiring ID caches.
  - Status: checkpointed in `d773e608`

- [x] Imported plugin SDK concurrency-runtime shim for bounded async task
  execution, ordered results, first-error tracking, and stop/continue error
  modes.
  - Status: checkpointed in `e6bd981e`

- [x] Imported plugin SDK channel-inbound-debounce shim for inbound debounce
  config resolution, keyed buffering, forced flushes, saturated-key fallback,
  and non-throwing error reporting.
  - Status: checkpointed in `9ac09500`

- [x] Imported plugin SDK markdown-table-runtime shim for markdown table mode
  resolution and code/bullet table conversion.
  - Status: checkpointed in `6e51b8a9`

- [x] Imported plugin SDK reply-history shim for bounded per-thread history
  recording, context assembly, clearing, enabled guards, and LRU key eviction.
  - Status: checkpointed in `738186ae`

- [x] Imported plugin SDK reply-reference shim for reply/thread reference
  planning, single-use mode detection, and batched threading policy.
  - Status: checkpointed in `3bdeeac0`

- [x] Imported plugin SDK reply-dedupe shim for resetting shared inbound
  dedupe cache and in-flight state.
  - Status: checkpointed in `e3ec8d6c`

- [x] Imported plugin SDK channel-reply-options-runtime shim for reply prefix
  option construction and typing lifecycle callbacks.
  - Status: checkpointed in `61357e44`

- [x] Imported plugin SDK channel-reply-pipeline shim for reply pipeline
  assembly and source reply delivery-mode resolution.
  - Status: checkpointed in `f9f1bf6a`

- [x] Imported plugin SDK channel-feedback shim for ack reaction gates,
  cleanup handles, status reaction controllers, and missing-target errors.
  - Status: checkpointed in `7c188623`

- [x] Imported plugin SDK channel-inbound shim for mention gates, inbound
  envelopes, location context, inbound path roots, and debouncer wrapping.
  - Status: checkpointed in `aa9825e0`

- [x] Imported plugin SDK channel-route shim for route identity keys,
  target/thread normalization, exact route matching, shared-conversation
  checks, parser-backed target resolution, and generic SDK re-exports.
  - Status: checkpointed in `0f67c4a0`

- [x] Imported plugin SDK channel-policy shim for DM/group access decisions,
  command gating, sender/group route policies, tools-by-sender, channel group
  policy/mention/tool resolution, warning collectors, and generic SDK
  re-exports.
  - Status: checkpointed in `9f7b7abd`

- [x] Imported plugin SDK allow-from shim for normalized allowFrom formatting,
  chat-aware sender matching, simple/compiled allowlist matching, DM/group
  allowFrom source merging, allowlist resolution summaries, patch helpers, and
  generic SDK re-exports.
  - Status: checkpointed in `bc6e1344`

- [x] Imported plugin SDK access-groups shim for allowFrom access-group prefix
  parsing, message-sender group matching, async membership resolver fallback,
  matched group projection, allowFrom expansion, and generic SDK re-exports.
  - Status: checkpointed in `93a4347c`

- [x] Imported plugin SDK direct-DM access shim for pairing-store allowlists,
  access-group expansion, open-DM allowlist blocking, command authorization
  runtime delegation, pairing callbacks, blocked-sender callbacks, and generic
  SDK re-exports.
  - Status: checkpointed in `5258f537`

- [x] Imported plugin SDK direct-DM guard-policy shim for pre-crypto guard
  policy defaults/overrides, rate-limit default merging, channel-inbound
  re-export, and generic SDK re-exports.
  - Status: checkpointed in `02803c84`

- [x] Imported plugin SDK direct-DM shim for direct-DM access/guard
  re-exports, route/envelope/session-record/reply-dispatch helper behavior,
  channel-inbound re-export, and generic SDK re-exports.
  - Status: checkpointed in `6534f0db`

- [x] Imported plugin SDK channel-send-result shim for channel result stamping,
  empty result construction, raw send result normalization, attached/raw
  adapter wrapping, and generic SDK re-exports.
  - Status: checkpointed in `c73fb961`

- [x] Imported plugin SDK channel-pairing shim for scoped pairing controllers,
  challenge issuers, prefix-stripping/text/log pairing adapters, allowFrom
  store path/read helpers, and generic SDK re-exports.
  - Status: checkpointed in `f0a21c8c`

- [x] Imported plugin SDK command-auth shim for DM/group/access-group sender
  command authorization, runtime-backed wrappers, direct-DM outcomes,
  command-gating/detection re-exports, deprecated command-status builders, and
  generic SDK re-exports.
  - Status: checkpointed in `d06e2c42`

- [x] Imported plugin SDK channel-setup shim for optional setup
  adapters/wizards/surfaces, unavailable setup messages, docs links, setup
  entry splitting, enabled patches, top-level DM policy helpers, and generic
  SDK re-exports.
  - Status: checkpointed in `0b86d5ea`

- [x] Imported plugin SDK allowlist-config-edit shim for DM/group and legacy-DM
  config paths, entry coercion, override collectors/resolvers, token-gated name
  resolution, account-scoped edits, default-account writes, legacy cleanup, and
  generic SDK re-exports.
  - Status: checkpointed in `37677120`

- [x] Imported plugin SDK group-access shim for sender-scoped group policy
  downgrade, route/matched/sender allowlist decisions, missing-provider
  fail-closed fallback policy, and generic SDK re-exports.
  - Status: checkpointed in `88510816`

- [x] Imported plugin SDK provider-selection-runtime shim for explicit
  provider selection, auto-select ordering, raw config merging, configured
  capability resolution, failure codes, and generic SDK re-exports.
  - Status: checkpointed in `395d23fc`

- [x] Imported plugin SDK windows-spawn shim for PATH/PATHEXT executable
  resolution, Node entrypoint wrapping, CMD/BAT shim inspection, package.json
  `bin` fallback, fail-closed wrapper policy, opt-in shell fallback,
  materialized argv construction, and generic SDK re-exports.
  - Status: checkpointed in `1c172bde`

- [x] Imported plugin SDK command-status shim for help text, slash-command
  lists, config/debug flag filtering, skill-command projection, category
  grouping, paginated command lists, scoped/unscoped SDK aliases, deprecated
  `command-auth` compatibility exports, generic SDK re-exports, and
  UTF-8-safe native Node bridge output.
  - Status: checkpointed in `6c22af79`

- [x] Imported plugin SDK command-auth native shim for mode-aware command
  authorization, control-command gates, dual text-command gates, native session
  target resolution, command body alias normalization, text-command routing,
  native command specs, command text serialization, Telegram command
  pagination keyboards, stored model override lookup, scoped/unscoped SDK
  aliases, and generic SDK re-exports.
  - Status: checkpointed in `1bbd7ed9`

- [x] Imported plugin SDK webhook helper shim for path normalization/resolution,
  fixed-window rate limits, bounded counters, anomaly tracking, JSON
  content-type checks, request guard rejection responses, in-flight request
  limits, target registration/lifecycle cleanup, request-path target
  resolution, request pipeline dispatch/release behavior, sync/async
  single-target matching, auth rejection responses, non-POST rejection,
  scoped/unscoped SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `98a00cc5`

- [x] Imported plugin SDK fetch/SSRF helper shim for bearer-scope fetch retry
  fallback, request URL extraction, private-network opt-in policies, legacy
  private-network alias migration, SSRF policy merging, HTTP private-network
  target checks, hostname suffix allowlists, hostname allowlist policy
  expansion, private/internal host detection, pinned-host policy checks,
  guarded-fetch stubs, scoped/unscoped SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `f4a23a25`

- [x] Imported plugin SDK provider model/catalog helper shim for preview model
  ID normalization, provider-hint detection, Claude thinking profiles,
  replay-family hook policies, Google Gemini replay sanitation/reasoning mode,
  canonical replay hook exports, configured model catalog entries, manifest
  catalog-to-provider config conversion, native streaming usage compatibility,
  scoped/unscoped SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `903343d0`

- [x] Imported plugin SDK provider entry/enable/auth-result helper shim for
  single-provider entry registration, auth-method wizard/env-var defaults,
  API-key provider catalogs with explicit base-URL overrides, static catalogs,
  provider-plugin enable config without channel normalization, web-fetch/
  web-search enable-contract aliases, OAuth auth profiles/config patches,
  scoped/unscoped SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `0887e67a`

- [x] Imported plugin SDK provider-auth-runtime helper shim for OAuth state
  generation, OAuth callback URL parsing with upstream diagnostics, runtime
  auth/API-key helper export availability, scoped/unscoped SDK aliases, and
  generic SDK re-exports.
  - Status: checkpointed in `cfaae804`

- [x] Imported plugin SDK provider-auth API-key helper shim for API-key input
  normalization, validation, preview formatting, secret-input mode resolution,
  plaintext/ref API-key credential construction, auth-profile config patching
  with mixed-mode order handling, API-key auth method export availability,
  scoped/unscoped SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `af3d97ea`

- [x] Imported plugin SDK provider-auth-login helper shim for
  `loginOpenAICodexOAuth`, `loginChutes`, and
  `githubCopilotLoginCommand` export availability, scoped/unscoped SDK
  aliases, generic SDK re-exports, and a precise native unavailable boundary
  for interactive OpenClaw login runtime calls.
  - Status: checkpointed in `9186faf7`

- [x] Imported plugin SDK provider-auth facade helper shim for Copilot IDE
  headers, Copilot API-base derivation, fakeable Copilot token cache/fetch
  exchange, provider env API-key detection, scoped/unscoped SDK aliases, and
  generic SDK re-exports.
  - Status: checkpointed in `35ca435d`

- [x] ESM bundled plugin runtime entry import without a fake activation
  adapter, transforming common OpenClaw `import ... from
  "openclaw/plugin-sdk/*"` and `export default` syntax to a temporary CommonJS
  module while preserving SDK alias shims and registered tool collection.
  - Status: checkpointed in `eb11e22f`

- [x] Plugin provider metadata projection, preserving OpenClaw
  `providerEndpoints` suffix/Vertex metadata plus provider-scoped
  `modelIdNormalization` and `providerRequest` rows.
  - Status: checkpointed in `9b2bf4fc`

- [x] Persisted plugin registry provider metadata, preserving provider
  metadata through `plugins registry --refresh --json` and later registry
  inspect payloads.
  - Status: checkpointed in `54c2fd49`

- [x] Google Chat native outbound route support, preserving OpenClaw
  target-normalization, text/thread message-create payloads, reply fallback
  query semantics, bearer auth, provider result metadata, and CLI/app route
  affordances.
  - Status: checkpointed in `edb67dfc`

- [x] Google Chat media and DM-resolution support, preserving OpenClaw
  `spaces:findDirectMessage`, attachment upload, message attachment refs,
  caption handling, and ordered media result metadata.
  - Status: checkpointed in `7086dcb3`

- [x] Nextcloud Talk native outbound route support, preserving OpenClaw
  room-token normalization, HMAC bot signature headers, Spreed bot message
  endpoint payloads, `replyTo`, media URL fallback text, and provider result
  metadata.
  - Status: checkpointed in `a6732846`

- [x] Synology Chat native outbound route support, preserving OpenClaw
  form-encoded incoming webhook payloads, numeric `user_ids`, media URL
  `file_url` delivery, and direct-send result metadata.
  - Status: checkpointed in `b69d5489`

- [x] Mattermost native outbound route support, preserving OpenClaw
  `/api/v4/posts` channel-id text/reply payloads, bearer bot auth, and provider
  result metadata.
  - Status: checkpointed in `44541ef9`

- [x] Signal native outbound route support, preserving OpenClaw JSON-RPC
  `send` payloads, recipient/group/username target params, media attachments,
  and timestamp result metadata.
  - Status: checkpointed in `81491ab7`

- [x] IRC native outbound route support, preserving OpenClaw
  `irc://`/`ircs://` server targets, `irc:`/`channel:`/`user:` target
  normalization, `replyToId` text suffixes, native `PRIVMSG` delivery, and
  generated result metadata.
  - Status: checkpointed in `8726ab49`

- [x] Twitch native outbound route support, preserving OpenClaw channel
  normalization, markdown stripping, media URL text fallback, native Twitch
  chat delivery, and result metadata.
  - Status: checkpointed in `6185301b`

- [x] Twitch send message action support, preserving OpenClaw required
  message/optional target handling, default route channel fallback,
  route-backed chat sender reuse, markdown stripping, and
  `{channel,messageId,timestamp}` result projection.
  - Status: checkpointed in `9baee646`

- [x] Signal native reaction action support, preserving OpenClaw JSON-RPC
  `sendReaction` payloads, direct/group target normalization, target-author
  fallback and required group-author behavior, `remove=true`, and
  `toolContext.currentMessageId` fallback.
  - Status: checkpointed in `c9b45ffb`

- [x] Microsoft Teams native outbound route support, preserving OpenClaw Bot
  Framework proactive text delivery for explicit conversation ids, route
  `appId`/`tenantId` service URL metadata, app-password or bearer-token auth,
  `msteams:`/`teams:`/`conversation:` target normalization, `;messageid=...`
  stripping, AI-generated entity metadata, and message/conversation result
  metadata.
  - Status: checkpointed in `79258ec2`

- [x] Microsoft Teams native poll support, preserving OpenClaw Adaptive Card
  choice-set polls, `openclawPollId` / `pollId` submit metadata, Teams
  `messageBack` action data, provider `pollId` / `messageId` / conversation
  metadata, and CLI poll capability projection.
  - Status: checkpointed in `b0ad5491`

- [x] Microsoft Teams reaction-list action support, preserving OpenClaw Graph
  message-action target resolution, app-token auth, grouped reaction summaries,
  known emoji labels, and anonymous/deleted-user reaction counts.
  - Status: checkpointed in `4996cf5c`

- [x] Microsoft Teams read message action support, preserving OpenClaw Graph
  message-action target fallback, route-backed Graph auth, delegated-token
  preference, chat/team-channel endpoint selection, and `id`/`text`/`from`/
  `createdAt` result projection.
  - Status: checkpointed in `4d3635c3`

- [x] Microsoft Teams pin message action support, preserving OpenClaw Graph
  chat pin payloads, `message@odata.bind`, pinned-message id projection,
  delegated-token preference, and the upstream Graph v1.0 channel pinning
  unavailable boundary.
  - Status: checkpointed in `1a99d147`

- [x] Microsoft Teams unpin message action support, preserving OpenClaw Graph
  chat pinned-resource DELETEs, `pinnedMessageId` / `messageId` fallback, and
  the upstream Graph v1.0 channel unpinning unavailable boundary.
  - Status: checkpointed in `dafcd607`

- [x] Microsoft Teams list-pins action support, preserving OpenClaw Graph chat
  pin listing, `$expand=message`, bounded `@odata.nextLink` pagination, and
  pinned-message summary projection.
  - Status: checkpointed in `9531fbe3`

- [x] Microsoft Teams search action support, preserving OpenClaw Graph
  `$search`, 1..50 limit clamping, quote stripping, sender filter escaping,
  `ConsistencyLevel=eventual`, and message summary projection.
  - Status: checkpointed in `29547a56`

- [x] Microsoft Teams member-info action support, preserving OpenClaw Graph
  user profile lookup, `$select` field coverage, route-backed Graph auth, and
  user profile projection.
  - Status: checkpointed in `8aa5f0a6`

- [x] Microsoft Teams channel-list action support, preserving OpenClaw Graph
  team channel listing, `$select` field coverage, bounded pagination, and
  `truncated` projection.
  - Status: checkpointed in `cf1b7f18`

- [x] Microsoft Teams channel-info action support, preserving OpenClaw Graph
  team channel lookup, `$select` field coverage, and `channelInfo` projection.
  - Status: checkpointed in `4e6fc71a`

- [x] Microsoft Teams edit message action support, preserving OpenClaw Bot
  Framework proactive updateActivity behavior, content fallback, route-backed
  bot auth, and conversation result projection.
  - Status: checkpointed in `df3f4f0d`

- [x] Microsoft Teams delete message action support, preserving OpenClaw Bot
  Framework proactive deleteActivity behavior, route-backed bot auth, and
  conversation result projection.
  - Status: checkpointed in `fd98306a`

- [x] Microsoft Teams upload-file message action support, preserving OpenClaw
  file-source aliases, filename/title metadata, Bot Framework send routing,
  Graph/FileConsent upload metadata, and action result projection.
  - Status: checkpointed in `86be3a2c`

- [x] Microsoft Teams adaptive-card send action support, preserving OpenClaw
  `send` plus `card` handling, Bot Framework Adaptive Card activity shape,
  and conversation result projection.
  - Status: checkpointed in `30fbcc69`

- [x] Microsoft Teams native readiness probe support, preserving OpenClaw Bot
  Framework credential posture, Graph app-token posture metadata, optional
  token roles/scopes projection, and `channels status --probe --json`
  readiness output.
  - Status: checkpointed in `50d05198`

- [x] Microsoft Teams delegated-auth probe posture, preserving OpenClaw's
  safe `delegatedAuth` status projection for configured stored delegated
  tokens.
  - Status: checkpointed in `2f4e2496`

- [x] Microsoft Teams inbound attachment URL metadata, preserving OpenClaw
  downloadable `content.downloadUrl` / `contentUrl` candidates as deduped
  native inbound `mediaUrls` while session delivery continues to receive the
  existing media placeholder.
  - Status: checkpointed in `2205ca86`

- [x] Microsoft Teams inbound media staging, preserving OpenClaw downloadable
  attachment fetch/store payload projection through native `MediaUrl(s)`,
  `MediaPath(s)`, and `MediaType(s)` result metadata.
  - Status: checkpointed in `eda4db73`

- [x] Microsoft Teams inbound media auth fallback, preserving OpenClaw
  401/403 retry behavior with Graph-first bearer auth for Graph/SharePoint
  media URLs and Bot Framework bearer fallback for Bot Framework media URLs.
  - Status: checkpointed in `5460ebf5`

- [x] Microsoft Teams user-reference routing, preserving OpenClaw
  `msteams:user:<aad-id>` session routing, stored personal conversation id
  resolution, and the non-personal DM leakage guard.
  - Status: checkpointed in `b88c540d`

- [x] Microsoft Teams reaction write actions, preserving OpenClaw Graph beta
  `setReaction` / `unsetReaction`, delegated token posture, legacy reaction
  type normalization, and `remove=true` result projection.
  - Status: checkpointed in `02ae95da`

- [x] Microsoft Teams stored delegated-token reaction writes, preserving
  OpenClaw's `preferDelegated` Graph token behavior for `react` / `unreact`
  when a persisted SSO token exists for the requester.
  - Status: checkpointed in `507c90ad`

- [x] Microsoft Teams expired delegated-token fallback, preserving OpenClaw's
  delegated-preferred/app-token fallback behavior when a stored SSO token is
  stale.
  - Status: checkpointed in `ddbeb84f`

- [x] Microsoft Teams delegated refresh-token flow, preserving OpenClaw's
  expired delegated-token refresh, old-refresh-token preservation, and
  refreshed access-token persistence before app-token fallback.
  - Status: checkpointed in `34a34a44`

- [x] Microsoft Teams delegated OAuth setup bootstrap, preserving OpenClaw's
  PKCE/state-protected Azure authorization URL, localhost redirect metadata,
  default delegated scopes, and setup-time `delegatedAuth.enabled` config
  patch without leaking the app password.
  - Status: checkpointed in `6f368d37`

- [x] Microsoft Teams delegated OAuth completion, preserving OpenClaw's full
  redirect URL parsing, state verification, authorization-code token exchange,
  refresh-token requirement, expiry buffer, native token persistence, and
  secret-free CLI output.
  - Status: checkpointed in `3695ca29`

- [x] Microsoft Teams threaded replies, preserving OpenClaw Bot Framework
  channel thread routing via `<conversationId>;messageid=<thread-root>` and
  `replyToId` result metadata.
  - Status: checkpointed in `927d5787`

- [x] Microsoft Teams file info card media, preserving OpenClaw native Teams
  file-card attachment projection from Graph DriveItem metadata, raw text
  captions, eTag-derived `uniqueId`, filename-derived `fileType`, and
  `mediaUrls` / `filenames` / `fileIds` result metadata.
  - Status: checkpointed in `eb663838`

- [x] Microsoft Teams poll vote storage, preserving OpenClaw adaptive-card
  vote extraction from `openclawPollId` / `pollId` plus `choices`, sender-id
  voter mapping, option/max-selection normalization, unknown-poll no-error
  consumption, and persisted vote metadata on the saved outbound poll record.
  - Status: checkpointed in `b3726879`

- [x] Microsoft Teams FileConsent card emission, preserving OpenClaw Bot
  Framework FileConsentCard payloads with `description`, `sizeInBytes`,
  `acceptContext`, `declineContext`, no top-level consent text, and
  `pendingUploadId` / `mediaUrls` / `filenames` result metadata.
  - Status: checkpointed in `ad3c8a5c`

- [x] Microsoft Teams FileConsent accept/upload handling, preserving OpenClaw
  `fileConsent/invoke` accept parsing, pending upload lookup by `uploadId`,
  conversation mismatch guard, upload URL validation, byte upload with
  `Content-Range`, FileInfoCard replacement, and saved completion metadata.
  - Status: checkpointed in `709fcf4d`

- [x] Microsoft Teams Graph media upload, preserving OpenClaw SharePoint Graph
  upload, organization sharing link creation, DriveItem `eTag` / `webDavUrl`
  lookup, native FileInfoCard emission, and saved upload metadata.
  - Status: checkpointed in `a220db23`

- [x] Microsoft Teams adaptive-card inbound monitor/session routing,
  preserving OpenClaw `adaptiveCard/action` invoke serialization,
  `;messageid=...` conversation normalization, channel thread-root session
  isolation, and session-backed inbound delivery.
  - Status: checkpointed in `5462df49`

- [x] Microsoft Teams inbound message text normalization, preserving
  OpenClaw mention stripping and `text/html` attachment fallback before
  session routing.
  - Status: checkpointed in `65daf165`

- [x] Microsoft Teams feedback invoke recording, preserving OpenClaw
  thumbs-up/thumbs-down normalization, optional comment parsing, thread-aware
  session routing, and durable feedback metadata.
  - Status: checkpointed in `7a545faf`

- [x] Microsoft Teams feedback-disabled invoke handling, preserving OpenClaw's
  `feedbackEnabled: false` consume-without-transcript-write branch.
  - Status: checkpointed in `34346a60`

- [x] Microsoft Teams feedback reflection learning/follow-up, preserving
  OpenClaw negative-feedback reflection prompting, bounded session learning
  storage, cooldown, and optional personal-chat follow-up delivery.
  - Status: checkpointed in `45c4ca7a`

- [x] Microsoft Teams SSO no-config invoke acknowledgement, preserving
  OpenClaw's immediate Bot Framework `invokeResponse` for
  `signin/tokenExchange` and `signin/verifyState` while projecting native
  unavailable SSO metadata without leaking tokens or magic-code state.
  - Status: checkpointed in `49ebe481`

- [x] Microsoft Teams configured SSO token exchange/store, preserving
  OpenClaw's `/api/usertoken/exchange` Bot Framework call, route-backed app
  credential bearer acquisition, `(connectionName, userId)` token persistence,
  and safe no-token result metadata.
  - Status: checkpointed in `1bf6ab5b`

- [x] Microsoft Teams configured SSO verify-state magic-code flow, preserving
  OpenClaw's `/api/usertoken/GetToken` Bot Framework call, persisted delegated
  token, and safe no-state/no-token result metadata.
  - Status: checkpointed in `0ecfab4c`

- [x] Microsoft Teams SSO DM allowlist authorization/drop handling, preserving
  OpenClaw's immediate `invokeResponse` ACK while blocking non-allowlisted
  personal-chat sign-in token exchange before Bot Framework User Token service
  calls or delegated-token persistence.
  - Status: checkpointed in `b9f2f404`

- [x] Microsoft Teams SSO route allowlist authorization/drop handling,
  preserving OpenClaw's nested `channels.msteams.teams` team/channel gate
  before configured sign-in token exchange.
  - Status: checkpointed in `5c54430c`

- [x] Microsoft Teams SSO group sender allowlist authorization/drop handling,
  preserving OpenClaw's non-DM `groupPolicy` plus
  `groupAllowFrom`/`allowFrom` sender gate before configured sign-in
  verify-state dispatch.
  - Status: checkpointed in `a203f34e`

- [x] Microsoft Teams Bot Framework `/api/messages` webhook dispatch,
  preserving OpenClaw's bearer pre-gate before JSON parsing and native inbound
  activity routing into Ops Mesh.
  - Status: checkpointed in `b162bc17`

- [x] Microsoft Teams Bot Framework configured webhook-path fallback,
  preserving OpenClaw's `channels.msteams.webhook.path` primary route plus
  standard `/api/messages` fallback registration.
  - Status: checkpointed in `91e854a0`

- [x] Microsoft Teams Bot Framework webhook JWT validation, preserving
  OpenClaw's issuer-specific JWKS, RS256 signature, audience, issuer, and
  app-id binding checks before webhook body parsing.
  - Status: checkpointed in `b3f911d2`

- [x] Microsoft Teams attachment-only inbound placeholders, preserving
  OpenClaw's `<media:image>` / `<media:document>` fallback before deeper
  attachment download staging.
  - Status: checkpointed in `86f9fa74`

- [x] Microsoft Teams personal welcome-card lifecycle, preserving OpenClaw's
  bot-added `conversationUpdate` Adaptive Card welcome send with configured
  prompt starters.
  - Status: checkpointed in `72b1e637`

- [x] Microsoft Teams group welcome lifecycle, preserving OpenClaw's
  non-personal bot-added `conversationUpdate` text welcome send when
  `groupWelcomeCard` is enabled.
  - Status: checkpointed in `299a8655`

- [x] Bundled channel explicit activation, preserving OpenClaw's
  `channel enabled in config` activation reason and allowlist bypass for
  configured bundled channel plugins.
  - Status: checkpointed in `e92cfcae`

- [x] Bundled channel auto-enable activation, preserving OpenClaw's
  `<channel> configured` auto activation reason for meaningful bundled channel
  config without `enabled=true`.
  - Status: checkpointed in `f1de1e28`

- [x] Bundled channel manifest env-var activation, preserving
  `channelEnvVars` as auto-enable triggers for bundled channel plugins.
  - Status: checkpointed in `f39ca17c`

- [x] Auto-enabled plugin runtime load-context reasons, preserving
  OpenClaw's `autoEnabledReasons` map when runtime activation adapters load
  bundled channel plugins auto-enabled from channel config/env discovery.
  - Status: checkpointed in `b44685b1`

- [x] Runtime text-transform plugin projection, preserving standalone
  `textTransforms` registrations from activation adapter registries in plugin
  doctor runtime activation metadata.
  - Status: checkpointed in `5216fb70`

- [x] Auto-enabled runtime resolved config, preserving OpenClaw's post-auto
  enable `config` snapshot while keeping `activationSourceConfig` raw for
  activation adapter loads.
  - Status: checkpointed in `5cfbf4fe`

- [x] Bundled runtime plugin-SDK import metadata, preserving
  `openclaw/plugin-sdk` and `@openclaw/plugin-sdk` specifiers from runtime
  entries for native adapter alias resolution.
  - Status: checkpointed in `54fb7bf8`

- [x] Bundled plugin-SDK alias context, preserving dist package SDK root and
  extension-local alias root metadata for native activation adapters.
  - Status: checkpointed in `e6b506db`

- [x] Source plugin-SDK subpath alias context, preserving source/git-style
  bundled plugin SDK alias maps for native activation adapters.
  - Status: checkpointed in `55e1fb28`

- [x] Manifest document extractor contract metadata, preserving
  `contracts.documentExtractors` in `plugins list --json` records and
  capability strings.
  - Status: checkpointed in `2196c65e`

- [x] Manifest web-content extractor contract metadata, preserving
  `contracts.webContentExtractors` in `plugins list --json` records and
  capability strings.
  - Status: checkpointed in `3b392789`

- [x] Manifest migration provider contract metadata, preserving
  `contracts.migrationProviders` in `plugins list --json` records and
  capability strings.
  - Status: checkpointed in `17e62174`

- [x] Manifest external auth provider contract metadata, preserving
  `contracts.externalAuthProviders` in `plugins list --json` records and
  capability strings.
  - Status: checkpointed in `5fdfb23c`

- [x] Manifest runtime-extension contract metadata, preserving
  `contracts.embeddedExtensionFactories` and
  `contracts.agentToolResultMiddleware` in `plugins list --json` records and
  capability strings.
  - Status: checkpointed in `cbd59d1d`

- [x] Canvas shortcode text normalization, preserving OpenClaw's visible
  assistant-message cleanup after valid `[embed ...]` removals.
  - Status: checkpointed in `c34e4a77`

- [x] Package distribution inventory validation, preserving OpenClaw's
  invalid-inventory warning posture in `doctor --json`.
  - Status: checkpointed in `3bf0ff86`

- [x] Telegram audio/voice media send routing, preserving OpenClaw's
  `sendAudio`/`sendVoice` Bot API split for native provider routes.
  - Status: checkpointed in `9e1743fb`

- [x] Telegram raw media-caption metadata, preserving OpenClaw's first-media
  raw caption without appended delivery-summary `Media:` URL inventory.
  - Status: checkpointed in `b2bc7fb7`

- [x] Update status channel projection, preserving OpenClaw's `update`,
  `channel`, and conservative `availability` JSON fields.
  - Status: checkpointed in `e32d4d47`

- [x] Update status git branch channel label, preserving OpenClaw's
  `dev (<branch>)` channel source projection.
  - Status: checkpointed in `8673e35d`

- [x] Update status package-manager dependency posture, preserving OpenClaw's
  `packageManager` detection and `deps` lockfile/install-marker metadata.
  - Status: checkpointed in `f1ac67da`

- [x] Companion remote macOS bin discovery, preserving OpenClaw's
  `system.which`/`system.run command -v` probe, paired-node `bins`
  persistence, and node-pair metadata exposure.
  - Status: checkpointed in `7dcce35d`

- [x] Companion QR setup-code bootstrap handoff, preserving OpenClaw's
  base64url `{url, bootstrapToken}` payload and file-backed node/operator
  bootstrap token profile for `qr --setup-code-only --url ...`.
  - Status: checkpointed in `5262359f`

- [x] Companion QR invalid URL preflight, preserving OpenClaw's
  `Configured publicUrl is invalid.` guard before bootstrap token issue.
  - Status: checkpointed in `f21c799c`

- [x] Companion QR remote fail-closed preflight, preserving OpenClaw's
  `qr --remote requires gateway.remote.url` guard before bootstrap token issue.
  - Status: checkpointed in `12dee789`

- [x] Companion QR JSON setup-code contract, preserving OpenClaw's four-field
  `setupCode` / `gatewayUrl` / `auth` / `urlSource` response shape.
  - Status: checkpointed in `b79b87c3`

- [x] Package distribution doctor diagnostics, preserving Windows-first
  package root, source-checkout, dist, and postinstall-inventory posture in
  `doctor --json`.
  - Status: checkpointed in `47d73351`

- [x] Companion node presence alive lifecycle, preserving authenticated
  background beacon persistence and upstream-shaped handled/reason results.
  - Status: checkpointed in `caded84a`

- [x] Telegram GIF media send animation routing, preserving OpenClaw's
  `sendAnimation` behavior for GIF media while keeping document forcing,
  caption, reply, silent, thread, and animation `mediaIds` metadata.
  - Status: checkpointed in `51ee9573`

- [x] WhatsApp audio/voice media send payload, preserving OpenClaw's audio
  media behavior by sending Cloud API `type="audio"` payloads and splitting
  visible text into a follow-up text message.
  - Status: checkpointed in `c27d3439`

- [x] WhatsApp split-media result metadata, preserving OpenClaw-style
  first/last/all message id observability for multi-media sends.
  - Status: checkpointed in `7e549c1e`

- [x] Discord thread result fallback, preserving OpenClaw's requested-thread
  `chatId`/`channelId` fallback when webhook responses omit `channel_id`.
  - Status: checkpointed in `e47324f4`

- [x] Plugin doctor failure-phase projection for loader error records,
  preserving OpenClaw's `validation`/`load`/`register` failure phases in JSON
  and human doctor output.
  - Status: checkpointed in `0dc9fc27`

- [x] Plugin inspect failure-phase projection for loader error records,
  preserving `plugin.failurePhase` in JSON and printing the OpenClaw-style
  `Failure phase: <phase>` line in human inspect output.
  - Status: checkpointed in `6f4d1ad8`

- [x] Plugin inspect failed-at timestamp projection for loader error records,
  preserving `plugin.failedAt` in JSON and printing the OpenClaw-style
  `Failed at: <timestamp>` line in human inspect output.
  - Status: checkpointed in `b3bf64a5`

- [x] Plugin inspect loader error text projection for loader error records,
  preserving `plugin.error` in JSON and printing the OpenClaw-style
  `Error: <text>` line in human inspect output.
  - Status: checkpointed in `88ff1768`

- [x] Plugin inspect human base metadata, rendering description, origin,
  version, capability mode, and legacy `before_agent_start` posture.
  - Status: checkpointed in `c11085d1`

- [x] Plugin inspect human capability sections, rendering bundle capabilities
  and capability rows from the inspect payload.
  - Status: checkpointed in `2b161d5a`

- [x] Plugin inspect human runtime surface sections, rendering commands, CLI
  commands, services, and gateway methods.
  - Status: checkpointed in `f2221877`

- [x] Plugin inspect human tools section, rendering runtime tools plus optional
  markers.
  - Status: checkpointed in `5ac316c1`

- [x] Plugin inspect human MCP/LSP sections, rendering server names from bundle
  and native inspect payloads.
  - Status: checkpointed in `6fc67848`

- [x] Plugin inspect human HTTP routes section, rendering a positive route
  count from the inspect payload.
  - Status: checkpointed in `efef8270`

- [x] Plugin inspect human policy section, rendering native inspect policy
  fields.
  - Status: checkpointed in `e0af8199`

- [x] Plugin inspect human diagnostics section, rendering scoped diagnostic
  rows.
  - Status: checkpointed in `667182c7`

- [x] Plugin inspect human install section, rendering saved install record
  rows.
  - Status: checkpointed in `5ca0a5f2`

- [x] Plugin inspect human compatibility warnings section, rendering
  compatibility rows without doctor-only severity markers.
  - Status: checkpointed in `38b85a1a`

- [x] Plugin inspect typed/custom hook sections, projecting hook metadata in
  JSON and human output.
  - Status: checkpointed in `0a6e8bcd`

- [x] Plugin inspect human header/bundle-format labels, matching OpenClaw
  capitalized label output.
  - Status: checkpointed in `df4d586c`

- [x] Plugin list verbose activation/import state, rendering activation and
  import metadata rows.
  - Status: checkpointed in `83146bc1`

- [x] Plugin list human enabled label, rendering active registry rows as
  `enabled` instead of leaking the internal `loaded` status label.
  - Status: checkpointed in `bc362484`

- [x] Plugin list human enabled count, rendering the header count as
  `Plugins (enabled/total enabled)`.
  - Status: checkpointed in `cc9983c3`

- [x] Manifest load-path activation-state projection for OpenClaw plugin and
  bundle records discovered through `plugins.load.paths`.
  - Status: checkpointed in `54bf33aa`

- [x] Errored runtime-imported plugin projection for runtime diagnostics and
  inspect paths.
  - Status: checkpointed in `cc2da90c`

- [x] Public-surface/runtime-sidecar artifact metadata for manifest/load-path
  OpenClaw plugin records.
  - Status: checkpointed in `2acd2736`

- [x] Configured-channel plugin owner activation projection in `plugins
  doctor --json`.
  - Status: checkpointed in `ae5c3986`

- [x] Configured-channel disabled-owner policy in runtime activation planning.
  - Status: checkpointed in `d2d0e9c3`

- [x] Configured-channel bundled-owner allowlist bypass in runtime activation
  planning.
  - Status: checkpointed in `6ad518d4`

- [x] Configured-channel config/global owner trust gate in runtime activation
  planning.
  - Status: checkpointed in `0e6ce093`

- [x] Configured-channel workspace owner activation gate in runtime activation
  planning.
  - Status: checkpointed in `bb9ef28a`

- [x] Manifest toolMetadata availability gate in runtime activation posture.
  - Status: checkpointed in `78d905c6`

- [x] Installed plugin runtime activation adapter in plugin doctor/list
  posture.
  - Status: checkpointed in `26e55209`

- [x] Installed plugin disabled activation gate in plugin doctor/list posture.
  - Status: checkpointed in `457021d6`

- [x] Installed plugin inspect runtime activation adapter tool projection.
  - Status: checkpointed in `fb4fca1b`

- [x] Installed plugin scoped runtime activation load context.
  - Status: checkpointed in `0ebf7884`

- [x] Installed plugin activation adapter failure diagnostic projection.
  - Status: checkpointed in `baa32232`

- [x] Installed activation-adapter manifest tool contract enforcement.
  - Status: checkpointed in `aac25d80`

- [x] Installed activation-adapter OpenClaw runtime load options.
  - Status: checkpointed in `ee12d2d4`

- [x] Installed-record manifest runtime activation.
  - Status: checkpointed in `b8f39fe3`

- [x] TTS persona gateway and CLI methods for `tts.personas`,
  `tts.setPersona`, status persona projection, prefs-backed selected persona,
  and `capability/infer tts personas` plus `set-persona` JSON output.
  - Status: checkpointed in `3819d03a`

- [x] Realtime voice gateway methods for `talk.realtime.session`,
  `relayAudio`, `relayMark`, `relayStop`, and `relayToolResult`, including
  fakeable adapter dispatch and upstream-shaped unavailable boundaries.
  - Status: checkpointed in `75d03a6c`

- [x] `channels.stop` admin-scoped gateway method with native idempotent stop
  projection and invalid-channel guards.
  - Status: checkpointed in `64f6937a`

- [x] `node.pair.remove` pairing-scoped gateway method with paired-node removal,
  `{nodeId}` projection, unknown-node guard, and `node.pair.resolved` removal
  broadcasts.
  - Status: checkpointed in `8a0e6ac6`

- [x] Slack provider-native route sends with OpenClaw-shaped `thread_ts`
  validation and fallback from internal `replyToId` values to valid Slack
  `threadId` timestamps.
  - Status: checkpointed in `a461e5eb`

- [x] Slack provider-native media sends with OpenClaw-shaped iterated media
  uploads, first-upload captioning, final-id `messageId`, and ordered media
  metadata projection.
  - Status: checkpointed in `e3b5bbc0`

- [x] Slack agent-request route metadata forwarding for direct announce-style
  delivery, including `accountId` and Slack `threadId` propagation into the
  fakeable chat runtime path.
  - Status: checkpointed in `e3671d6f`

- [x] Feishu/Lark provider-native direct text sends with OpenClaw-shaped
  message-create payloads, target normalization, bearer auth, and provider
  message/chat metadata persistence.
  - Status: checkpointed in `d1515da1`

- [x] Feishu/Lark send message action support, preserving OpenClaw `to` /
  `target`, `text` / `message`, `toolContext.currentChannelId` fallback,
  route-backed Feishu sender reuse, bearer auth, and message/chat result
  projection.
  - Status: checkpointed in `249f3dbf`

- [x] Feishu/Lark thread-reply message action support, preserving OpenClaw
  `messageId` aliases, Feishu reply endpoint routing, `reply_in_thread=true`,
  bearer auth, and reply result projection.
  - Status: checkpointed in `641c8fc7`

- [x] Feishu/Lark read message action support, preserving OpenClaw message-id
  aliases, Feishu message GET routing, text/post/card content parsing,
  message metadata projection, and not-found error envelope.
  - Status: checkpointed in `38f27358`

- [x] Feishu/Lark edit message action support, preserving OpenClaw message-id
  aliases, exactly-one text/card validation, Feishu message PATCH routing, and
  `contentType` result projection.
  - Status: checkpointed in `2203efa7`

- [x] Feishu/Lark pin message action support, preserving OpenClaw message-id
  aliases, Feishu pin-create routing, pin metadata normalization, and pin
  result projection.
  - Status: checkpointed in `1615bdf6`

- [x] Feishu/Lark unpin message action support, preserving OpenClaw
  message-id aliases, Feishu pin-delete routing, and message-id result
  projection.
  - Status: checkpointed in `4f42eae0`

- [x] Feishu/Lark list-pins message action support, preserving OpenClaw
  chat/channel aliases, time/page query options, page-size clamping, pin
  metadata normalization, and pagination result projection.
  - Status: checkpointed in `b1bfb9e2`

- [x] Feishu/Lark channel-info message action support, preserving OpenClaw
  chat/channel aliases, Feishu chat GET routing, and chat metadata projection.
  - Status: checkpointed in `f0bd7837`

- [x] Feishu/Lark member-info message action support, preserving OpenClaw
  member id aliases, Feishu id-type inference, direct profile routing,
  chat-member listing, page-size clamping, and member metadata projection.
  - Status: checkpointed in `ff50511d`

- [x] Feishu/Lark channel-list message action support, preserving OpenClaw
  live directory discovery, group/user scope aliases, query filtering, provider
  page-size caps, and directory metadata projection.
  - Status: checkpointed in `dd915f30`

- [x] Feishu/Lark reaction message action support, preserving OpenClaw
  add/remove-own/clear-all reaction behavior and reaction listing projection.
  - Status: checkpointed in `1c6b44af`

- [x] Feishu/Lark presentation-card send support, preserving OpenClaw
  presentation fallback rendering, Feishu interactive-card payloads, and
  reply-in-thread/fallback routing.
  - Status: checkpointed in `75edc136`

- [x] Feishu/Lark image media send support, preserving OpenClaw image upload,
  image-key message sends, and route-backed send metadata.
  - Status: checkpointed in `64375b92`

- [x] Feishu/Lark file media send support, preserving OpenClaw file upload,
  file-key message sends, provider file-type routing, and route-backed send
  metadata.
  - Status: checkpointed in `152dcb38`

- [x] Feishu/Lark audio/video media send support, preserving OpenClaw
  Ogg/Opus audio routing, MP4 video routing, file-key message sends, and
  threaded reply media payloads.
  - Status: checkpointed in `6e99a40b`

- [x] Feishu/Lark mediaLocalRoots local-path guard support, preserving
  OpenClaw fail-closed local media reads and configured root allowlisting.
  - Status: checkpointed in `78cfda1f`

- [x] Feishu/Lark audioAsVoice transcode support, preserving OpenClaw
  voice-compatible audio conversion, native Feishu audio payloads, and
  fallback-to-file behavior when conversion is unavailable.
  - Status: checkpointed in `81c93c0e`

- [x] Feishu/Lark mediaMaxMb support, preserving OpenClaw account/channel
  media-size caps before upload.
  - Status: checkpointed in `45d6a6bc`

- [x] Feishu/Lark channel capability discovery support, preserving OpenClaw
  media, thread/reply, reaction/edit, and voice-transcode capability metadata.
  - Status: checkpointed in `326f471f`

- [x] Feishu/Lark direct provider-route media send support, preserving
  OpenClaw media upload/send behavior for direct `gateway.send`, ordered
  `mediaIds`/`mediaUrls`, and delivery provider metadata.
  - Status: checkpointed in `77149f94`

- [x] Feishu/Lark message-resource read hydration support, preserving
  OpenClaw `file_key` precedence, file-to-media retry behavior, inbound
  attachment storage, and read action media metadata projection.
  - Status: checkpointed in `65da0455`

- [x] Feishu/Lark post/rich-text embedded media hydration support,
  preserving OpenClaw localized post parsing, embedded image/media key
  collection, resource downloads, and ordered read action media metadata.
  - Status: checkpointed in `ed3aedb5`

- [x] Discord provider-native webhook sends with OpenClaw-shaped thread
  execution query placement, preserving reply message references and silent
  flags in the body while omitting `thread_id` from the body.
  - Status: checkpointed in `0d40be27`

- [x] WhatsApp provider-native document sends with OpenClaw-shaped filename
  derivation from outbound media URLs, including reply-context preservation.
  - Status: checkpointed in `05c4f0fc`

- [x] Discord provider-native media sends with OpenClaw-shaped per-media
  webhook iteration, first-send captioning, final-id `messageId`, and ordered
  provider `messageIds`.
  - Status: checkpointed in `b5371fd9`

- [x] Native runtime seams for ACP spawn dispatch/tracking, delete/reset cleanup,
  app-wired sandbox-required child turns, route-backed thread-bound spawn
  binding, shared provider-native send metadata, and Telegram native document,
  reply, silent, and thread payloads.
  - Status: verified in ledger

## Active / Remaining Queue Heads

- [x] Sandboxed remote inbound provider media staging.
  - Source: `openclaw-main/src/auto-reply/reply/stage-sandbox-media.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed and pushed in `2e6a3ed8`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_gateway_node_methods.py::test_chat_send_sandboxed_remote_provider_attachment_stages_allowed_media
    -q` (`1 passed`), adjacent sandbox attachment proof (`6 passed`), `ruff
    check`, and `mypy`.

- [x] Runtime-control `sessions.pluginPatch` registered plugin session
  extension state.
  - Source: `openclaw-main/src/gateway/server-methods/sessions.ts`,
    `openclaw-main/src/plugins/host-hook-state.ts`,
    `openclaw-main/src/plugins/host-hook-json.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_plugin_runtime.py`,
    `src/openzues/services/gateway_sessions.py`,
    `src/openzues/services/gateway_method_policy.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `e0c02761`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_gateway_node_methods.py::test_sessions_plugin_patch_persists_registered_extension_state
    -q` (`1 passed`), adjacent `python -m pytest
    tests\test_gateway_node_methods.py -q -k "sessions_plugin_patch or
    sessions_patch or sessions_resolve"` (`27 passed`), `ruff check`, and
    `mypy`.

- [x] Plugin-host `plugins.uiDescriptors` control UI descriptor gateway method.
  - Source: `openclaw-main/src/gateway/server-methods/plugin-host-hooks.ts`,
    `openclaw-main/src/gateway/protocol/schema/plugins.ts`, and
    `openclaw-main/src/plugins/registry.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_plugin_runtime.py`,
    `src/openzues/services/gateway_method_policy.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `9fb5098b`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_gateway_node_methods.py::test_plugins_ui_descriptors_returns_registered_control_ui_descriptors
    -q` (`1 passed`), adjacent `python -m pytest
    tests\test_gateway_node_methods.py -q -k "plugins_ui_descriptors or
    tools_invoke_uses_plugin_runtime or tools_invoke_runs_registry_plugin_executor
    or tools_invoke_keeps_registry_owner_only or sessions_plugin_patch"` (`5
    passed`), `ruff check`, and `mypy`.

- [x] TTS persona gateway and CLI methods.
  - Source: `openclaw-main/src/gateway/server-methods/tts.ts`,
    `openclaw-main/src/config/types.tts.ts`, and
    `openclaw-main/src/cli/capability-cli.ts`
  - Target: `src/openzues/services/gateway_tts.py`,
    `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_method_policy.py`, `src/openzues/cli.py`
  - Test: `tests/test_gateway_node_methods.py`,
    `tests/test_gateway_method_policy.py`, `tests/test_cli.py`
  - Status: checkpointed in `3819d03a`.
  - Weight: 1
  - Last verified: 2026-05-02, focused gateway persona tests (`2 passed`),
    focused policy test (`1 passed`), focused CLI tests (`2 passed`),
    adjacent gateway TTS tests (`9 passed`), adjacent CLI TTS tests (`11
    passed`), adjacent API TTS tests (`6 passed`), `ruff check`, and `mypy`.

- [x] Realtime voice gateway session and relay methods.
  - Source: `openclaw-main/src/gateway/server-methods/talk.ts`,
    `openclaw-main/src/gateway/protocol/schema/channels.ts`,
    `openclaw-main/src/gateway/method-scopes.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_method_policy.py`
  - Test: `tests/test_gateway_node_methods.py`,
    `tests/test_gateway_method_policy.py`
  - Status: checkpointed in `75d03a6c`.
  - Weight: 1
  - Last verified: 2026-05-02, focused gateway realtime tests (`2 passed`),
    focused talk/TTS policy proof (`2 passed`), adjacent gateway talk tests (`6
    passed`), `ruff check`, and `mypy`. Broader policy selection exposed
    unrelated existing gaps for `channels.stop` and `node.pair.remove`.

- [x] `channels.stop` gateway method.
  - Source: `openclaw-main/src/gateway/server-methods/channels.ts`,
    `openclaw-main/src/gateway/method-scopes.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_method_policy.py`
  - Test: `tests/test_gateway_node_methods.py`,
    `tests/test_gateway_method_policy.py`
  - Status: checkpointed in `64f6937a`.
  - Weight: 1
  - Last verified: 2026-05-02, focused gateway stop tests (`2 passed`),
    focused channel policy proof (`1 passed`), adjacent start/logout/stop tests
    (`7 passed`), `ruff check`, and `mypy`.

- [x] `node.pair.remove` gateway method.
  - Source: `openclaw-main/src/gateway/server-methods/nodes.ts`,
    `openclaw-main/src/gateway/method-scopes.ts`
  - Target: `src/openzues/services/gateway_node_pairing.py`,
    `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_method_policy.py`
  - Test: `tests/test_gateway_node_methods.py`,
    `tests/test_gateway_method_policy.py`
  - Status: checkpointed in `8a0e6ac6`.
  - Weight: 1
  - Last verified: 2026-05-02, focused gateway remove tests (`2 passed`),
    focused node/voice policy proof (`1 passed`), adjacent node-pair lifecycle
    tests (`13 passed`), `ruff check`, and `mypy`.

- [ ] Runtime command/packaging breadth.
  - Source: OpenClaw runtime, CLI, package, and doctor surfaces.
  - Status: open; package distribution doctor diagnostics checkpointed in
    `47d73351`, package dist inventory validation checkpointed in `3bf0ff86`,
    update status channel projection checkpointed in `e32d4d47`, update status
    git branch channel label checkpointed in `8673e35d`, and update status
    package-manager dependency posture checkpointed in `f1ac67da`.
  - Weight: 5

- [ ] Runtime-control hard gaps.
  - Source: broader OpenClaw runtime/client integration and session runtime
    methods, especially `chat.*` and `sessions.*`.
  - Status: open
  - Weight: 3

- [ ] Real installed plugin module import/activation.
  - Source: OpenClaw plugin lifecycle and activation runtime.
  - Status: open; manifest activation-plan reason projection child slice
    checkpointed in `721ec0f2`, plugin registry inspect/refresh child slice
    checkpointed in `cdb3035e`, and plugin list registry-source child slice
    checkpointed in `6468e305`, plugin inspect runtime flag child slice
    checkpointed in `5fce4371`, and missing-target static preflight child
    slice checkpointed in `9a9e89f2`, and runtime target-scoped inventory
    child slice checkpointed in `c412b98b`, and installed plugin
    activation-state child slice checkpointed in `78658f29`, and installed
    plugin allowlist activation guard child slice checkpointed in `73089117`,
    and installed plugin slot activation reason child slice checkpointed in
    `209dced0`, plugin doctor failure-phase projection checkpointed in
    `0dc9fc27`, plugin inspect failure-phase projection checkpointed in
    `6f4d1ad8`, plugin inspect failed-at timestamp projection checkpointed in
    `b3bf64a5`, plugin inspect loader error text projection checkpointed in
    `88ff1768`, plugin inspect human base metadata checkpointed in
    `c11085d1`, plugin inspect human capability sections checkpointed in
    `2b161d5a`, plugin inspect human runtime surface sections checkpointed in
    `f2221877`, plugin inspect human tools section checkpointed in `5ac316c1`,
    plugin inspect human MCP/LSP sections checkpointed in `6fc67848`, and
    plugin inspect human HTTP routes section checkpointed in `efef8270`, and
    plugin inspect human policy section checkpointed in `e0af8199`, and plugin
    inspect human diagnostics section checkpointed in `667182c7`, and plugin
    inspect human install section checkpointed in `5ca0a5f2`, and plugin
    inspect human compatibility warnings section checkpointed in `38b85a1a`,
    plugin inspect typed/custom hook sections checkpointed in `0a6e8bcd`, and
    plugin inspect human header/bundle-format labels checkpointed in
    `df4d586c`, plugin list verbose activation/import state checkpointed
    in `83146bc1`, plugin list human enabled label checkpointed in
    `bc362484`, plugin list human enabled count checkpointed in `cc9983c3`,
    manifest load-path activation-state projection checkpointed in
    `54bf33aa`, and errored runtime-imported plugin projection checkpointed
    in `cc2da90c`, and public-surface/runtime-sidecar artifact metadata
    checkpointed in `2acd2736`, and configured-channel owner activation
    projection checkpointed in `ae5c3986`, and configured-channel disabled
    owner policy checkpointed in `d2d0e9c3`, and configured-channel bundled
    owner allowlist bypass checkpointed in `6ad518d4`, and configured-channel
    config/global owner trust gate checkpointed in `0e6ce093`, and
    configured-channel workspace owner activation gate checkpointed in
    `bb9ef28a`, and manifest toolMetadata availability gate checkpointed in
    `78d905c6`, and installed plugin runtime activation adapter checkpointed
    in `26e55209`, and installed plugin disabled activation gate checkpointed
    in `457021d6`, installed plugin inspect runtime activation adapter
    tool projection checkpointed in `fb4fca1b`, and installed plugin scoped
    runtime activation load context checkpointed in `0ebf7884`, and installed
    plugin activation adapter failure diagnostics checkpointed in `baa32232`,
    and installed activation-adapter manifest tool contract enforcement
    checkpointed in `aac25d80`, and installed activation-adapter runtime load
    options checkpointed in `ee12d2d4`, and installed-record manifest runtime
    activation checkpointed in `b8f39fe3`, bundled runtime plugin-SDK import
    metadata checkpointed in `54fb7bf8`, bundled plugin-SDK alias context
    checkpointed in `e6b506db`, source plugin-SDK subpath aliases checkpointed
    in `55e1fb28`, manifest document extractor contract metadata checkpointed
    in `2196c65e`, bundled plugin runtime entry import checkpointed in
    `8cb314f4`, ESM plugin runtime entry import checkpointed in `eb11e22f`,
    imported CommonJS runtime execution checkpointed in `d80b0252`, ESM
    runtime execution checkpointed in `311f37e1`, and runtime tool factory
    context checkpointed in `ef254cbf`, text-runtime helper shim checkpointed
    in `91918c38`, error-runtime helper shim checkpointed in `7888c8de`, and
    temp-path helper shim checkpointed in `d6a73b21`, and secret-input helper
    shim checkpointed in `76e3c638`, routing helper shim checkpointed in
    `2cf7fb27`, reply-chunking helper shim checkpointed in `b000f51c`,
    reply-payload helper shim checkpointed in `5d628f16`, account-helper
    shim checkpointed in `6d2cf33b`, account-core/account-resolution shim
    checkpointed in `47fa2f39`, tool-payload shim checkpointed in
    `387717ed`, boolean-param shim checkpointed in `65bd842f`,
    channel-actions shim checkpointed in `447d15ff`, status-helper shim
    checkpointed in `41323ea2`, channel-status shim checkpointed in
    `14ff20a1`, text-chunking shim checkpointed in `20267310`,
    string-normalization shim checkpointed in `06cd452d`, dangerous-name shim
    checkpointed in `01473fb4`, channel-logging shim checkpointed in
    `c42b0d77`, and time-runtime shim checkpointed in `eb944ee1`, but broader
    plugin SDK helper/runtime surface breadth remains.
  - Weight: 5

- [x] Imported plugin SDK time-runtime shim.
  - Source: `openclaw-main/src/plugin-sdk/time-runtime.ts` and
    `openclaw-main/src/infra/format-time/format-datetime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `eb944ee1`
  - Weight: 1
  - Last verified: 2026-05-05, focused time-runtime proof (`1 passed`),
    adjacent plugin invoke proof (`31 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK channel-logging shim.
  - Source: `openclaw-main/src/plugin-sdk/channel-logging.ts` and
    `openclaw-main/src/channels/logging.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `c42b0d77`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-logging proof (`1 passed`),
    adjacent plugin invoke proof (`30 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK dangerous-name shim.
  - Source: `openclaw-main/src/plugin-sdk/dangerous-name-runtime.ts` and
    `openclaw-main/src/config/dangerous-name-matching.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `01473fb4`
  - Weight: 1
  - Last verified: 2026-05-05, focused dangerous-name proof (`1 passed`),
    adjacent plugin invoke proof (`29 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK string-normalization shim.
  - Source: `openclaw-main/src/plugin-sdk/string-normalization-runtime.ts`
    and `openclaw-main/src/shared/string-normalization.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `06cd452d`
  - Weight: 1
  - Last verified: 2026-05-05, focused string-normalization proof (`1
    passed`), adjacent plugin invoke proof (`28 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] Imported plugin SDK text-chunking shim.
  - Source: `openclaw-main/src/plugin-sdk/text-chunking.ts` and
    `openclaw-main/src/shared/text-chunking.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `20267310`
  - Weight: 1
  - Last verified: 2026-05-05, focused text-chunking proof (`1 passed`),
    adjacent plugin invoke proof (`27 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK channel-status shim.
  - Source: `openclaw-main/src/plugin-sdk/channel-status.ts`,
    `openclaw-main/src/channels/account-snapshot-fields.ts`, and
    `openclaw-main/src/channels/plugins/pairing-message.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `14ff20a1`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-status proof (`1 passed`),
    adjacent plugin invoke proof (`26 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK status-helper shim.
  - Source: `openclaw-main/src/plugin-sdk/status-helpers.ts`,
    `openclaw-main/src/channels/plugins/status-issues/shared.ts`, and
    `openclaw-main/src/plugin-sdk/status-helpers.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `41323ea2`
  - Weight: 1
  - Last verified: 2026-05-05, focused status-helper proof (`1 passed`),
    adjacent plugin invoke proof (`25 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK channel-actions shim.
  - Source: `openclaw-main/src/plugin-sdk/channel-actions.ts`,
    `openclaw-main/src/agents/tools/common.ts`,
    `openclaw-main/src/channels/plugins/actions/shared.ts`,
    `openclaw-main/src/channels/plugins/actions/reaction-message-id.ts`,
    `openclaw-main/src/agents/date-time.ts`,
    `openclaw-main/src/agents/sandbox-paths.ts`, `openclaw-main/src/polls.ts`,
    and `openclaw-main/src/agents/schema/typebox.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `447d15ff`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-actions proof (`1 passed`),
    adjacent plugin invoke proof (`24 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK boolean-param shim.
  - Source: `openclaw-main/src/plugin-sdk/boolean-param.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `65bd842f`
  - Weight: 1
  - Last verified: 2026-05-05, focused boolean-param proof (`1 passed`),
    adjacent plugin invoke proof (`23 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK tool-payload shim.
  - Source: `openclaw-main/src/plugin-sdk/tool-payload.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `387717ed`
  - Weight: 1
  - Last verified: 2026-05-05, focused tool-payload proof (`1 passed`),
    adjacent plugin invoke proof (`22 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK account-core/account-resolution shim.
  - Source: `openclaw-main/src/plugin-sdk/account-core.ts`,
    `openclaw-main/src/plugin-sdk/account-resolution.ts`,
    `openclaw-main/src/plugin-sdk/account-resolution-runtime.ts`,
    `openclaw-main/src/plugin-sdk/account-configured-ids.ts`,
    `openclaw-main/src/channels/chat-type.ts`, and
    `openclaw-main/src/utils.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `47fa2f39`
  - Weight: 1
  - Last verified: 2026-05-05, focused account-core proof (`1 passed`),
    adjacent plugin invoke proof (`21 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK account-helper shim.
  - Source: `openclaw-main/src/plugin-sdk/account-helpers.ts`,
    `openclaw-main/src/channels/plugins/account-helpers.ts`, and
    `openclaw-main/src/channels/plugins/account-action-gate.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `6d2cf33b`
  - Weight: 1
  - Last verified: 2026-05-05, focused account-helper proof (`1 passed`),
    adjacent plugin invoke proof (`20 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK reply-payload helper shim.
  - Source: `openclaw-main/src/plugin-sdk/reply-payload.ts` and
    `openclaw-main/src/channels/plugins/media-payload.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `5d628f16`
  - Weight: 1
  - Last verified: 2026-05-05, focused reply-payload helper proof (`1
    passed`), adjacent plugin invoke proof (`19 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] Imported plugin SDK reply-chunking helper shim.
  - Source: `openclaw-main/src/plugin-sdk/reply-chunking.ts`,
    `openclaw-main/src/auto-reply/chunk.ts`, and
    `openclaw-main/src/auto-reply/tokens.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `b000f51c`
  - Weight: 1
  - Last verified: 2026-05-05, focused reply-chunking helper proof (`1
    passed`), adjacent plugin invoke proof (`18 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] Imported plugin SDK routing helper shim.
  - Source: `openclaw-main/src/plugin-sdk/routing.ts`,
    `openclaw-main/src/routing/session-key.ts`,
    `openclaw-main/src/sessions/session-key-utils.ts`,
    `openclaw-main/src/routing/account-id.ts`,
    `openclaw-main/src/routing/account-lookup.ts`, and
    `openclaw-main/src/infra/outbound/thread-id.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `2cf7fb27`
  - Weight: 1
  - Last verified: 2026-05-05, focused routing helper proof (`1 passed`),
    adjacent plugin invoke proof (`17 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK secret-input helper shim.
  - Source: `openclaw-main/src/plugin-sdk/secret-input.ts` and
    `openclaw-main/src/config/types.secrets.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `76e3c638`
  - Weight: 1
  - Last verified: 2026-05-05, focused secret-input helper proof (`1
    passed`), adjacent plugin invoke proof (`16 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] Imported plugin SDK temp-path helper shim.
  - Source: `openclaw-main/src/plugin-sdk/temp-path.ts` and
    `openclaw-main/src/infra/temp-download.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `d6a73b21`
  - Weight: 1
  - Last verified: 2026-05-05, focused temp-path helper proof (`1 passed`),
    adjacent plugin invoke proof (`15 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] Imported plugin SDK error-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/error-runtime.ts` and
    `openclaw-main/src/infra/errors.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `7888c8de`
  - Weight: 1
  - Last verified: 2026-05-05, focused error-runtime helper proof (`1
    passed`), adjacent plugin invoke proof (`14 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] Imported plugin SDK text-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/text-runtime.ts` and
    `openclaw-main/src/shared/string-coerce.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `91918c38`
  - Weight: 1
  - Last verified: 2026-05-05, focused text-runtime helper proof (`1
    passed`), adjacent plugin invoke proof (`13 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] Imported plugin runtime tool factory context.
  - Source: `openclaw-main/src/plugins/tool-types.ts`,
    `openclaw-main/src/plugins/registry.ts`,
    `openclaw-main/src/plugins/tools.ts`, and
    `openclaw-main/src/gateway/tools-invoke-shared.ts`
  - Target: `src/openzues/cli.py`,
    `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_plugin_runtime.py`,
    `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `ef254cbf`
  - Weight: 1
  - Last verified: 2026-05-05, focused runtime tool factory-context proof (`1
    passed`), adjacent plugin invoke proof (`12 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] Imported ESM plugin runtime execution.
  - Source: `openclaw-main/src/plugins/loader.ts`,
    `openclaw-main/src/plugins/sdk-alias.ts`,
    `openclaw-main/src/plugins/tools.ts`, and
    `openclaw-main/src/gateway/tools-invoke-shared.ts`
  - Target: `tests/test_gateway_node_methods.py` plus the native runtime
    executor bridge in `src/openzues/cli.py` from `d80b0252`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `311f37e1`
  - Weight: 1
  - Last verified: 2026-05-05, focused ESM runtime invoke proof (`1
    passed`), adjacent plugin invoke proof (`11 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] Imported CommonJS plugin runtime execution.
  - Source: `openclaw-main/src/plugins/registry.ts`,
    `openclaw-main/src/plugins/tools.ts`, and
    `openclaw-main/src/gateway/tools-invoke-shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `d80b0252`
  - Weight: 1
  - Last verified: 2026-05-05, focused imported runtime invoke proof (`1
    passed`), adjacent plugin invoke proof (`10 passed, 803 deselected`),
    adjacent runtime import proof (`2 passed, 512 deselected`), `ruff check`,
    and `mypy`.

- [x] ESM bundled plugin runtime entry import.
  - Source: `openclaw-main/src/plugins/loader.ts`,
    `openclaw-main/src/plugins/sdk-alias.ts`, and
    `openclaw-main/src/plugins/loader.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `eb11e22f`
  - Weight: 1
  - Last verified: 2026-05-04, focused ESM plugin runtime import proof (`1
    passed`), adjacent plugin activation/import proof (`8 passed, 488
    deselected`), gateway plugin runtime proof (`3 passed`), `ruff check`,
    and `mypy`.

- [x] Bundled plugin runtime entry import.
  - Source: `openclaw-main/src/plugins/loader.ts`,
    `openclaw-main/src/plugins/registry.ts`, and
    `openclaw-main/src/plugins/loader.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `8cb314f4`
  - Weight: 1
  - Last verified: 2026-05-04, focused plugin runtime import proof (`1
    passed`), adjacent activation/import proof (`7 passed, 488 deselected`),
    gateway plugin runtime proof (`3 passed`), `ruff check`, and `mypy`.

- [x] Installed-record manifest runtime activation.
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/plugins/loader.ts`,
    `openclaw-main/src/plugins/discovery.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `b8f39fe3`.
  - Weight: 1
  - Last verified: 2026-05-02, focused installed-record activation test (`1
    passed`), adjacent installed-plugin CLI proof (`7 passed`), `ruff check`,
    and `mypy`.

- [x] Source plugin-SDK subpath alias context.
  - Source: `openclaw-main/src/plugins/sdk-alias.ts` and
    `openclaw-main/src/plugins/sdk-alias.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `55e1fb28`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_passes_source_plugin_sdk_subpath_aliases_to_activation_adapter
    -q` (`1 passed`), adjacent plugin SDK/runtime-entry proof (`6 passed`),
    `ruff check`, and `mypy`.

- [x] Manifest document extractor contract metadata.
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/contracts/inventory/bundled-capability-metadata.ts`,
    `openclaw-main/src/plugins/document-extractors.runtime.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `2196c65e`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_plugins_list_json_preserves_manifest_document_extractor_contracts
    -q` (`1 passed`), adjacent plugin manifest inventory proof (`9 passed`),
    `ruff check`, and `mypy`.

- [x] Manifest web-content extractor contract metadata.
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/contracts/inventory/bundled-capability-metadata.ts`,
    `openclaw-main/src/plugins/web-content-extractors.runtime.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `3b392789`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_plugins_list_json_preserves_manifest_web_content_extractor_contracts
    -q` (`1 passed`), adjacent plugin manifest inventory proof (`10 passed`),
    `ruff check`, and `mypy`.

- [x] Manifest migration provider contract metadata.
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/contracts/inventory/bundled-capability-metadata.ts`,
    `openclaw-main/src/plugins/contracts/registry.ts`,
    `openclaw-main/src/plugins/migration-provider-runtime.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `17e62174`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_plugins_list_json_preserves_manifest_migration_provider_contracts
    -q` (`1 passed`), adjacent plugin manifest inventory proof (`11 passed`),
    `ruff check`, and `mypy`.

- [x] Manifest external auth provider contract metadata.
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/manifest-registry.ts`,
    `openclaw-main/src/plugins/providers.ts`,
    `openclaw-main/src/plugins/provider-runtime.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `5fdfb23c`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_plugins_list_json_preserves_manifest_external_auth_provider_contracts
    -q` (`1 passed`), adjacent plugin manifest inventory proof (`12 passed`),
    `ruff check`, and `mypy`.

- [x] Manifest runtime-extension contract metadata.
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/registry.ts`,
    `openclaw-main/src/plugins/agent-tool-result-middleware-loader.ts`,
    `openclaw-main/src/agents/codex-app-server.extensions.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `cbd59d1d`
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_plugins_list_json_preserves_manifest_runtime_extension_contracts
    -q` (`1 passed`), adjacent plugin manifest contract proof (`6 passed,
    486 deselected`), `ruff check`, and `mypy`.

- [x] Canvas shortcode text normalization.
  - Source: `openclaw-main/src/chat/canvas-render.ts`
  - Target: `src/openzues/services/gateway_canvas_render.py`
  - Test: `tests/test_gateway_canvas_render.py`, `tests/test_app.py`
  - Status: checkpointed in `c34e4a77`.
  - Weight: 1
  - Last verified: 2026-05-04, focused canvas normalization test (`1 passed`),
    full canvas-render tests (`4 passed`), adjacent control-chat canvas preview
    proof (`1 passed, 194 deselected`), `ruff check`, and `mypy`.

- [x] Package distribution inventory validation.
  - Source: `openclaw-main/src/infra/package-dist-inventory.ts`,
    `openclaw-main/src/infra/update-global.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `3bf0ff86`.
  - Weight: 1
  - Last verified: 2026-05-04, focused package inventory test (`1 passed`),
    adjacent package/runtime doctor proof (`3 passed`), `ruff check`, and
    `mypy`.

- [x] Telegram audio/voice media send routing.
  - Source: `openclaw-main/extensions/telegram/src/outbound-adapter.ts`,
    `openclaw-main/extensions/telegram/src/send.ts`,
    `openclaw-main/extensions/telegram/src/voice.ts`,
    `openclaw-main/src/media/audio.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `9e1743fb`.
  - Weight: 1
  - Last verified: 2026-05-04, focused Telegram audio/voice test (`1 passed`),
    adjacent Telegram native-route proof (`6 passed`), `ruff check`, and
    `mypy`.

- [x] Telegram raw media-caption metadata.
  - Source: `openclaw-main/extensions/telegram/src/outbound-adapter.ts`,
    `openclaw-main/src/plugin-sdk/reply-payload.ts`,
    `openclaw-main/extensions/telegram/src/send.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `b2bc7fb7`
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_telegram_media_group
    -q` (`1 passed`), adjacent Telegram native-options/media proof (`2
    passed, 277 deselected`), `ruff check`, and `mypy`.

- [x] Update status channel projection.
  - Source: `openclaw-main/src/cli/update-cli/status.ts`,
    `openclaw-main/src/infra/update-channels.ts`,
    `openclaw-main/src/commands/status.update.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `e32d4d47`.
  - Weight: 1
  - Last verified: 2026-05-04, focused update-status test (`1 passed`),
    adjacent update/package doctor proof (`3 passed`), `ruff check`, and
    `mypy`.

- [x] Update status git branch channel label.
  - Source: `openclaw-main/src/infra/update-channels.ts`,
    `openclaw-main/src/cli/update-cli/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `8673e35d`.
  - Weight: 1
  - Last verified: 2026-05-04, focused update-status pair (`2 passed`),
    adjacent update/package doctor proof (`4 passed`), `ruff check`, and
    `mypy`.

- [x] Update status package-manager dependency posture.
  - Source: `openclaw-main/src/infra/detect-package-manager.ts`,
    `openclaw-main/src/infra/update-check.ts`, and
    `openclaw-main/src/cli/update-cli/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `f1ac67da`.
  - Weight: 1
  - Last verified: 2026-05-04, focused update-status package-manager test (`1
    passed`), adjacent update/package doctor proof (`5 passed, 488
    deselected`), `ruff check`, and `mypy`.

- [x] Package distribution doctor diagnostics.
  - Source: `openclaw-main/src/flows/doctor-health.ts`,
    `openclaw-main/src/commands/doctor-install.ts`,
    `openclaw-main/src/infra/update-global.ts`,
    `openclaw-main/src/infra/package-dist-inventory.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `47d73351`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_doctor_json_includes_windows_package_distribution_diagnostics
    -q` (`1 passed`), adjacent doctor/runtime bridge proof (`3 passed`),
    `ruff check`, and `mypy`.

- [x] Companion node presence alive lifecycle.
  - Source: `openclaw-main/src/gateway/server-node-events.ts`,
    `openclaw-main/src/shared/node-presence.ts`,
    `openclaw-main/apps/ios/Sources/Push/BackgroundAliveBeacon.swift`,
    Android gateway session invoke tests
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_node_pairing.py`, `src/openzues/database.py`
  - Test: `tests/test_gateway_node_methods.py`, `tests/test_gateway_nodes_api.py`
  - Status: checkpointed in `caded84a`.
  - Weight: 1
  - Last verified: 2026-05-04, focused service/API presence tests (`1 passed`
    each), adjacent node pairing/event API proof (`3 passed` each),
    `ruff check`, and `mypy`.

- [x] Companion remote macOS bin discovery.
  - Source: `openclaw-main/src/infra/skills-remote.ts`,
    `openclaw-main/src/infra/node-pairing.ts`,
    `openclaw-main/src/gateway/server/ws-connection/message-handler.ts`
  - Target: `src/openzues/services/gateway_remote_node_bins.py`,
    `src/openzues/services/gateway_skill_bins.py`,
    `src/openzues/services/gateway_node_pairing.py`,
    `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_node_service.py`, `src/openzues/database.py`,
    `src/openzues/app.py`
  - Test: `tests/test_gateway_node_methods.py`,
    `tests/test_gateway_node_pairing_refresh.py`, `tests/test_gateway_nodes_api.py`
  - Status: checkpointed in `7dcce35d`.
  - Weight: 1
  - Last verified: 2026-05-04, focused remote-bin node method test
    (`1 passed`), adjacent node method proof (`5 passed`), adjacent node API
    proof (`4 passed`), pairing refresh proof (`5 passed`), `ruff check`, and
    `mypy`.

- [x] Companion QR setup-code bootstrap handoff.
  - Source: `openclaw-main/src/cli/qr-cli.ts`,
    `openclaw-main/src/pairing/setup-code.ts`,
    `openclaw-main/src/infra/device-bootstrap.ts`
  - Target: `src/openzues/cli.py`,
    `src/openzues/services/device_bootstrap_tokens.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `5262359f`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_qr_setup_code_only_emits_openclaw_base64url_bootstrap_payload
    -q` (`1 passed`), adjacent setup/bootstrap CLI proof (`3 passed, 494
    deselected`), `ruff check`, and `mypy`.

- [x] Companion QR invalid URL preflight.
  - Source: `openclaw-main/src/cli/qr-cli.test.ts`,
    `openclaw-main/src/pairing/setup-code.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `f21c799c`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_qr_setup_code_only_rejects_invalid_override_url_before_token_issue
    -q` (`1 passed`), adjacent QR setup-code proof (`2 passed, 496
    deselected`), `ruff check`, and `mypy`.

- [x] Companion QR remote fail-closed preflight.
  - Source: `openclaw-main/src/cli/qr-cli.ts`,
    `openclaw-main/src/cli/qr-cli.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `12dee789`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_qr_remote_requires_explicit_remote_url_before_token_issue
    -q` (`1 passed`), adjacent QR proof (`3 passed, 496 deselected`), `ruff
    check`, and `mypy`.

- [x] Companion QR JSON setup-code contract.
  - Source: `openclaw-main/src/cli/qr-cli.ts`,
    `openclaw-main/src/cli/qr-cli.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `b79b87c3`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_qr_json_output_matches_openclaw_setup_code_contract
    -q` (`1 passed`), adjacent QR proof (`4 passed, 496 deselected`), `ruff
    check`, and `mypy`.

- [x] Plugin provider metadata projection.
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/manifest-registry.ts`,
    `openclaw-main/src/plugins/manifest-registry.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `9b2bf4fc`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_plugins_list_json_preserves_manifest_auth_and_env_metadata
    -q` (`1 passed`), adjacent manifest metadata proof (`6 passed, 494
    deselected`), `ruff check`, and `mypy`.

- [x] Persisted plugin registry provider metadata.
  - Source: `openclaw-main/src/plugins/manifest-registry.ts`,
    `openclaw-main/src/plugins/manifest-registry.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `54c2fd49`.
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_plugins_registry_refresh_json_persists_provider_metadata
    -q` (`1 passed`), adjacent registry proof (`4 passed, 497 deselected`),
    `ruff check`, and `mypy`.

- [x] Installed activation-adapter OpenClaw runtime load options.
  - Source: `openclaw-main/src/plugins/runtime/load-context.ts`,
    `openclaw-main/src/plugins/runtime/load-context.test.ts`,
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.ts`,
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `ee12d2d4`.
  - Weight: 1
  - Last verified: 2026-05-02, focused installed activation-adapter
    load-options test (`1 passed`), adjacent plugin runtime CLI proof (`7
    passed`), `ruff check`, and `mypy`.

- [x] Installed activation-adapter manifest tool contract enforcement.
  - Source: `openclaw-main/src/plugins/registry.ts`,
    `openclaw-main/src/plugins/loader.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `aac25d80`.
  - Weight: 1
  - Last verified: 2026-05-02, focused installed activation-adapter contract
    test (`1 passed`), adjacent plugin runtime CLI proof (`7 passed`), `ruff
    check`, and `mypy`.

- [x] Installed plugin activation adapter failure diagnostic projection.
  - Source: `openclaw-main/src/plugins/loader.ts`,
    `openclaw-main/src/plugins/status.ts`,
    `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `baa32232`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin doctor activation adapter error
    test (`1 passed`), adjacent plugin runtime CLI proof (`7 passed`), `ruff
    check`, and `mypy`.

- [x] Installed plugin scoped runtime activation load context.
  - Source: `openclaw-main/src/plugins/runtime/load-context.ts`,
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.ts`,
    `openclaw-main/src/plugins/status.ts`,
    `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `0ebf7884`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect scoped activation
    context test (`1 passed`), adjacent plugin runtime CLI proof (`7 passed`),
    `ruff check`, and `mypy`.

- [x] Installed plugin inspect runtime adapter tool projection.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`,
    `openclaw-main/src/plugins/status.ts`,
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `fb4fca1b`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect installed activation
    adapter tool projection test (`1 passed`), adjacent plugin runtime CLI
    proof (`6 passed`), `ruff check`, and `mypy`.

- [x] Installed plugin disabled activation gate.
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/plugins/config-state.ts`,
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `457021d6`.
  - Weight: 1
  - Last verified: 2026-05-02, focused disabled activation adapter test (`1
    passed`), adjacent plugin runtime CLI proof (`7 passed`), `ruff check`,
    and `mypy`.

- [x] Installed plugin runtime activation adapter.
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/plugins/registry.ts`,
    `openclaw-main/src/plugins/runtime.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `26e55209`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin doctor installed activation
    adapter test (`1 passed`), adjacent plugin runtime CLI proof (`6 passed`),
    `ruff check`, and `mypy`.

- [x] Manifest toolMetadata availability gate.
  - Source: `openclaw-main/src/plugins/tools.optional.test.ts`,
    `openclaw-main/src/plugins/tools.ts`,
    `openclaw-main/src/plugins/manifest-tool-availability.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `78d905c6`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin doctor toolMetadata
    availability test (`1 passed`), adjacent plugin doctor/list manifest proof
    (`5 passed`), `ruff check`, and `mypy`.

- [x] Configured-channel workspace owner activation gate.
  - Source: `openclaw-main/src/plugins/channel-presence-policy.ts`,
    `openclaw-main/src/plugins/config-activation-shared.ts`
  - Target: `src/openzues/services/gateway_plugin_activation.py`
  - Test: `tests/test_gateway_plugin_activation.py`, `tests/test_cli.py`
  - Status: checkpointed in `bb9ef28a`.
  - Weight: 1
  - Last verified: 2026-05-02, focused workspace-owner activation helper test
    (`1 passed`), full activation helper suite (`9 passed`), adjacent plugin
    doctor proof (`3 passed`), `ruff check`, and `mypy`.

- [x] Configured-channel config/global owner trust gate.
  - Source: `openclaw-main/src/plugins/channel-presence-policy.ts`,
    `openclaw-main/src/plugins/manifest-owner-policy.ts`
  - Target: `src/openzues/services/gateway_plugin_activation.py`
  - Test: `tests/test_gateway_plugin_activation.py`, `tests/test_cli.py`
  - Status: checkpointed in `0e6ce093`.
  - Weight: 1
  - Last verified: 2026-05-02, focused config-owner trust helper test (`1
    passed`), full activation helper suite (`8 passed`), adjacent plugin
    doctor proof (`3 passed`), `ruff check`, and `mypy`.

- [x] Configured-channel bundled-owner allowlist bypass.
  - Source: `openclaw-main/src/plugins/channel-presence-policy.ts`,
    `openclaw-main/src/plugins/manifest-owner-policy.ts`
  - Target: `src/openzues/services/gateway_plugin_activation.py`
  - Test: `tests/test_gateway_plugin_activation.py`, `tests/test_cli.py`
  - Status: checkpointed in `6ad518d4`.
  - Weight: 1
  - Last verified: 2026-05-02, focused bundled-owner allowlist-bypass helper
    test (`1 passed`), full activation helper suite (`7 passed`), adjacent
    plugin doctor proof (`3 passed`), `ruff check`, and `mypy`.

- [x] Configured-channel disabled-owner policy.
  - Source: `openclaw-main/src/plugins/channel-presence-policy.ts`,
    `openclaw-main/src/plugins/manifest-owner-policy.ts`, and
    `openclaw-main/src/plugins/activation-context.ts`
  - Target: `src/openzues/services/gateway_plugin_activation.py`
  - Test: `tests/test_gateway_plugin_activation.py`, `tests/test_cli.py`
  - Status: checkpointed in `d2d0e9c3`.
  - Weight: 1
  - Last verified: 2026-05-02, focused disabled-owner helper test (`1
    passed`), full activation helper suite (`6 passed`), adjacent plugin
    doctor proof (`3 passed`), `ruff check`, and `mypy`.

- [x] Configured-channel plugin owner activation projection.
  - Source: `openclaw-main/src/plugins/runtime/runtime-registry-loader.test.ts`,
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.ts`,
    `openclaw-main/src/plugins/channel-presence-policy.ts`, and
    `openclaw-main/src/plugins/activation-context.ts`
  - Target: `src/openzues/services/gateway_plugin_activation.py`,
    `src/openzues/cli.py`
  - Test: `tests/test_cli.py`, `tests/test_gateway_plugin_activation.py`
  - Status: checkpointed in `ae5c3986`.
  - Weight: 1
  - Last verified: 2026-05-02, focused configured-channel doctor test (`1
    passed`), adjacent plugin doctor/manifest proof (`5 passed`), activation
    helper focused proof (`1 passed`), full activation helper proof (`5
    passed`), `ruff check`, and `mypy`.

- [x] Public-surface/runtime-sidecar artifact metadata.
  - Source: `openclaw-main/src/plugins/bundled-plugin-metadata.test.ts`,
    `openclaw-main/src/plugins/bundled-plugin-scan.ts`, and
    `openclaw-main/src/plugins/public-surface-runtime.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `2acd2736`.
  - Weight: 1
  - Last verified: 2026-05-02, focused manifest load-path test (`1 passed`),
    adjacent manifest/bundle inventory proof (`7 passed`), `ruff check`, and
    `mypy`.

- [x] Errored runtime-imported plugin projection.
  - Source: `openclaw-main/src/plugins/status.test.ts`,
    `openclaw-main/src/plugins/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `cc2da90c`.
  - Weight: 1
  - Last verified: 2026-05-02, focused runtime inspect error-import test (`1
    passed`), adjacent loader-error/workspace-status proof (`7 passed`),
    `ruff check`, and `mypy`.

- [x] Manifest load-path activation-state projection.
  - Source: `openclaw-main/src/plugins/status.ts`,
    `openclaw-main/src/plugins/config-state.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `54bf33aa`.
  - Weight: 1
  - Last verified: 2026-05-02, focused manifest load-path test (`1 passed`),
    adjacent plugin activation/manifest inventory proof (`8 passed`), `ruff
    check`, and `mypy`.

- [x] Plugin list human enabled count.
  - Source: `openclaw-main/src/cli/plugins-list-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `cc9983c3`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin list runtime-inventory test (`1
    passed`), adjacent plugin list/runtime proof (`6 passed`), `ruff check`,
    and `mypy`.

- [x] Plugin list human enabled label.
  - Source: `openclaw-main/src/cli/plugins-list-format.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `bc362484`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin list runtime-inventory test (`1
    passed`), adjacent plugin list/runtime proof (`6 passed`), `ruff check`,
    and `mypy`.

- [x] Plugin list verbose activation/import state.
  - Source: `openclaw-main/src/cli/plugins-list-format.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `83146bc1`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin list activation-state test (`1
    passed`), adjacent plugin list/runtime proof (`6 passed`), `ruff check`,
    and `mypy`.

- [x] Plugin inspect human header/bundle-format labels.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `df4d586c`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect Claude bundle test (`1
    passed`), adjacent plugin inspect/doctor proof (`12 passed`), `ruff
    check`, and `mypy`.

- [x] Plugin inspect typed/custom hook sections.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `0a6e8bcd`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect hook-section test (`1
    passed`), adjacent plugin inspect/doctor proof (`11 passed`), `ruff
    check`, and `mypy`.

- [x] Plugin inspect human compatibility warnings section.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `38b85a1a`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect human metadata test (`1
    passed`), adjacent plugin inspect/doctor proof (`10 passed`), `ruff
    check`, and `mypy`.

- [x] Plugin inspect human install section.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `5ca0a5f2`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect saved-install test (`1
    passed`), adjacent plugin inspect proof (`9 passed`), `ruff check`, and
    `mypy`.

- [x] Plugin inspect human diagnostics section.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `667182c7`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect scoped-diagnostics test
    (`1 passed`), adjacent plugin inspect proof (`8 passed`), `ruff check`,
    and `mypy`.

- [x] Plugin inspect human policy section.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `e0af8199`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect config-policy test (`1
    passed`), adjacent plugin inspect proof (`7 passed`), `ruff check`, and
    `mypy`.

- [x] Plugin inspect human HTTP routes section.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `efef8270`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect runtime-surface test (`1
    passed`), adjacent plugin inspect proof (`7 passed`), `ruff check`, and
    `mypy`.

- [x] Plugin inspect human MCP/LSP sections.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `6fc67848`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect MCP/LSP test (`1
    passed`), adjacent plugin inspect bundle/runtime proof (`7 passed`),
    `ruff check`, and `mypy`.

- [x] Plugin inspect human tools section.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `5ac316c1`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect human tools test (`1
    passed`), adjacent plugin inspect/doctor proof (`13 passed`), `ruff
    check`, and `mypy`.

- [x] Plugin inspect human runtime surface sections.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `f2221877`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect human runtime-surface
    test (`1 passed`), adjacent plugin inspect/doctor proof (`11 passed`),
    `ruff check`, and `mypy`.

- [x] Plugin inspect human capability sections.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `2b161d5a`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect human capability test
    (`1 passed`), adjacent plugin inspect/doctor proof (`10 passed`), `ruff
    check`, and `mypy`.

- [x] Plugin inspect human base metadata.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `c11085d1`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect human metadata test (`1
    passed`), adjacent plugin inspect/doctor proof (`9 passed`), `ruff
    check`, and `mypy`.

- [x] Plugin inspect loader error text projection.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`,
    `openclaw-main/src/plugins/loader-records.ts`,
    `openclaw-main/src/plugins/registry-types.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `88ff1768`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect loader-error test (`1
    passed`), adjacent plugin inspect/doctor proof (`8 passed`), `ruff
    check`, and `mypy`.

- [x] Plugin inspect failed-at timestamp projection.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`,
    `openclaw-main/src/plugins/loader-records.ts`,
    `openclaw-main/src/plugins/registry-types.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `b3bf64a5`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect failed-at test (`1
    passed`), adjacent plugin inspect/doctor proof (`7 passed`), `ruff
    check`, and `mypy`.

- [x] Plugin inspect failure-phase projection.
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`,
    `openclaw-main/src/plugins/loader-records.ts`,
    `openclaw-main/src/plugins/registry-types.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `6f4d1ad8`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin inspect failure-phase test (`1
    passed`), adjacent plugin inspect/doctor proof (`6 passed`), `ruff
    check`, and `mypy`.

- [x] Plugin doctor failure-phase projection.
  - Source: `openclaw-main/src/plugins/loader-records.ts`,
    `openclaw-main/src/plugins/registry-types.ts`,
    `openclaw-main/src/cli/plugins-cli.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `0dc9fc27`.
  - Weight: 1
  - Last verified: 2026-05-02, focused plugin doctor failure-phase test (`1
    passed`), adjacent plugin doctor/activation proof (`5 passed`), `ruff
    check`, and `mypy`.

- [x] Installed plugin slot activation reason.
  - Source: `openclaw-main/src/plugins/config-activation-shared.ts`,
    `openclaw-main/src/plugins/config-state.test.ts`,
    `openclaw-main/src/plugins/loader-records.ts`,
    `openclaw-main/src/plugins/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `209dced0`.
  - Weight: 1
  - Last verified: 2026-05-02, focused installed plugin slot activation test
    (`1 passed`), adjacent plugin config/install list and doctor proof (`8
    passed`), `ruff check`, and `mypy`.

- [x] Installed plugin allowlist activation guard.
  - Source: `openclaw-main/src/plugins/config-activation-shared.ts`,
    `openclaw-main/src/plugins/config-state.test.ts`,
    `openclaw-main/src/plugins/loader-records.ts`,
    `openclaw-main/src/plugins/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `73089117`.
  - Weight: 1
  - Last verified: 2026-05-02, focused installed plugin allowlist activation
    test (`1 passed`), adjacent plugin config/install list and doctor proof
    (`7 passed`), `ruff check`, and `mypy`.

- [x] Installed plugin activation-state projection.
  - Source: `openclaw-main/src/plugins/config-activation-shared.ts`,
    `openclaw-main/src/plugins/loader-records.ts`,
    `openclaw-main/src/plugins/status.ts`,
    `openclaw-main/src/cli/plugins-cli.list.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `78658f29`.
  - Weight: 1
  - Last verified: 2026-05-02, focused installed plugin activation-state test
    (`1 passed`), adjacent plugin config/install list and doctor proof (`6
    passed`), `ruff check`, and `mypy`.

- [x] Plugin inspect runtime target-scoped inventory.
  - Source: `openclaw-main/src/cli/plugins-cli.list.test.ts`,
    `openclaw-main/src/plugins/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `c412b98b`.
  - Weight: 1
  - Last verified: 2026-05-02, focused scoped runtime inspect test (`1
    passed`), focused runtime inspect trio (`3 passed`), adjacent plugin
    inspect/runtime inventory proof (`8 passed`), `ruff check`, and `mypy`.

- [x] Plugin inspect runtime missing-target static preflight.
  - Source: `openclaw-main/src/cli/plugins-cli.list.test.ts`,
    `openclaw-main/src/cli/plugins-cli.ts`,
    `openclaw-main/src/plugins/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `9a9e89f2`.
  - Weight: 1
  - Last verified: 2026-05-02, focused missing-target runtime inspect test
    (`1 passed`), focused runtime inspect pair (`2 passed`), adjacent plugin
    inspect/runtime inventory proof (`7 passed`), `ruff check`, and `mypy`.

- [x] Plugin inspect runtime-inspection flag.
  - Source: `openclaw-main/src/cli/plugins-cli.ts`,
    `openclaw-main/src/cli/plugins-cli.list.test.ts`,
    `openclaw-main/src/plugins/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `5fce4371`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_cli.py::test_plugins_inspect_runtime_json_uses_runtime_loaded_import_state
    -q` (`1 passed`), adjacent plugin inspect/runtime inventory proof (`6
    passed`), `ruff check`, and `mypy`.

- [x] Plugin list persisted-registry source projection.
  - Source: `openclaw-main/src/cli/plugins-list-command.ts`,
    `openclaw-main/src/plugins/status.ts`,
    `openclaw-main/src/plugins/status.registry-snapshot.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `6468e305`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_cli.py::test_plugins_list_json_reports_persisted_registry_source_after_refresh
    -q` (`1 passed`), adjacent plugin CLI proof (`6 passed`), `ruff check`,
    and `mypy`.

- [x] Plugin registry inspect/refresh CLI.
  - Source: `openclaw-main/src/cli/plugins-cli.ts`,
    `openclaw-main/src/cli/plugins-cli.list.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `cdb3035e`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_cli.py::test_plugins_registry_json_reports_missing_persisted_registry
    -q` (`1 passed`), focused `python -m pytest
    tests\test_cli.py::test_plugins_registry_refresh_json_persists_current_index
    -q` (`1 passed`), adjacent plugin CLI proof (`4 passed`), `ruff check`,
    and `mypy`.

- [~] Provider-native adapter breadth.
  - Source: OpenClaw channel/provider send, poll, replay, direct announce, media,
    reply, thread, and result metadata behavior.
  - Status: mapped; Slack thread timestamp fallback checkpointed in
    `a461e5eb`; Slack media result checkpointed in `e3b5bbc0`; Discord thread
    query placement checkpointed in `0d40be27`; WhatsApp document filename
    projection checkpointed in `05c4f0fc`; Discord media iteration
    checkpointed in `b5371fd9`; native provider result metadata passthrough
    checkpointed in `fb9c9763`; Telegram GIF media send checkpointed in
    `51ee9573`; WhatsApp audio/voice media send checkpointed in `c27d3439`;
    WhatsApp split-media result metadata checkpointed in `7e549c1e`; Discord
    thread result fallback checkpointed in `e47324f4`; Slack agent-request
    thread metadata checkpointed in `e3671d6f`; Feishu/Lark native outbound
    route checkpointed in `d1515da1`; Google Chat native/media route
    checkpoints in `edb67dfc` and `7086dcb3`; Nextcloud Talk native route
    checkpointed in `a6732846`; Synology Chat native route checkpointed in
    `b69d5489`; Mattermost native route checkpointed in `44541ef9`; Signal
    native route checkpointed in `81491ab7`; IRC native route checkpointed in
    `8726ab49`; Twitch native route checkpointed in `6185301b`; Twitch send
    action checkpointed in `9baee646`; Feishu/Lark send action checkpointed
    in `249f3dbf`; Feishu/Lark thread-reply action checkpointed in
    `641c8fc7`; Feishu/Lark read action checkpointed in `38f27358`;
    Feishu/Lark edit action checkpointed in `2203efa7`; Feishu/Lark pin
    action checkpointed in `1615bdf6`; Feishu/Lark unpin action checkpointed
    in `4f42eae0`; Feishu/Lark list-pins action checkpointed in `b1bfb9e2`;
    Feishu/Lark channel-info action checkpointed in `f0bd7837`; Feishu/Lark
    member-info action checkpointed in `ff50511d`; Feishu/Lark channel-list
    action checkpointed in `dd915f30`; Feishu/Lark reaction actions
    checkpointed in `1c6b44af`; Feishu/Lark presentation-card sends
    checkpointed in `75edc136`; Feishu/Lark image media sends checkpointed in
    `64375b92`; Feishu/Lark file media sends checkpointed in `152dcb38`;
    Feishu/Lark audio/video media sends checkpointed in `6e99a40b`;
    Feishu/Lark mediaLocalRoots local-path guard checkpointed in `78cfda1f`;
    Feishu/Lark audioAsVoice transcode checkpointed in `81c93c0e`;
    Feishu/Lark mediaMaxMb limits checkpointed in `45d6a6bc`; Feishu/Lark
    channel capability discovery checkpointed in `326f471f`; Feishu/Lark
    direct provider-route media sends checkpointed in `77149f94`; Feishu/Lark
    read-media resource hydration checkpointed in `65da0455`; Feishu/Lark
    post-media resource hydration checkpointed in `ed3aedb5`; Signal native
    reaction action checkpointed in `c9b45ffb`
  - Weight: 3

- [x] Feishu/Lark native outbound route.
  - Source: `openclaw-main/extensions/feishu/src/send-target.ts`,
    `openclaw-main/extensions/feishu/src/send.ts`,
    `openclaw-main/extensions/feishu/src/send-result.ts`, and
    `openclaw-main/extensions/feishu/src/outbound.ts`
  - Target: `src/openzues/schemas.py`, `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_channels.py`, and `src/openzues/cli.py`
  - Test: `tests/test_ops_mesh.py`, `tests/test_cli.py`
  - Status: checkpointed in `d1515da1`
  - Weight: 1
  - Last verified: 2026-05-04, focused Feishu service proof (`2 passed`),
    focused CLI proof (`1 passed`), adjacent provider send proof (`6 passed,
    275 deselected`), adjacent route-create proof (`5 passed, 489
    deselected`), `ruff check`, and `mypy`.

- [x] Slack agent-request thread metadata.
  - Source: `openclaw-main/src/agents/subagent-announce-delivery.ts`,
    `openclaw-main/extensions/slack/src/outbound-adapter.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/app.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `e3671d6f`
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_gateway_node_methods.py::test_node_event_agent_request_forwards_slack_account_and_thread_to_chat_runtime
    -q` (`1 passed`), adjacent gateway proof (`5 passed, 807 deselected`),
    adjacent Slack provider proof (`3 passed, 276 deselected`), `ruff check`,
    and `mypy`.

- [x] Discord thread result fallback.
  - Source: `openclaw-main/extensions/discord/src/send.webhook.ts`,
    `openclaw-main/extensions/discord/src/outbound-adapter.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `e47324f4`
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_discord_thread_query
    -q` (`1 passed`), adjacent Discord native route proof (`4 passed, 275
    deselected`), `ruff check`, and `mypy`.

- [x] WhatsApp audio/voice media send payload.
  - Source: `openclaw-main/extensions/whatsapp/src/send.ts`,
    `openclaw-main/extensions/whatsapp/src/send.test.ts`, and
    `openclaw-main/extensions/whatsapp/src/outbound-media-contract.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `c27d3439`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_whatsapp_audio_voice_payload
    -q` (`1 passed`), adjacent WhatsApp native media/reply/gif/poll proof (`5
    passed`), `ruff check`, and `mypy`.

- [x] WhatsApp split-media result metadata.
  - Source: `openclaw-main/src/infra/outbound/message-plan.ts`,
    `openclaw-main/src/infra/outbound/deliver.ts`,
    `openclaw-main/src/gateway/server-methods/send.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `7e549c1e`
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_splits_whatsapp_media
    -q` (`1 passed`), adjacent WhatsApp media/reply/audio proof (`4 passed,
    275 deselected`), `ruff check`, and `mypy`.

- [x] Telegram GIF media send animation routing.
  - Source: `openclaw-main/extensions/telegram/src/send.ts`,
    `openclaw-main/extensions/telegram/src/send.test.ts`, and
    `openclaw-main/extensions/telegram/src/outbound-adapter.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `51ee9573`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_telegram_animation_for_gif_media
    -q` (`1 passed`), adjacent Telegram native send/poll/media proof (`5
    passed`), `ruff check`, and `mypy`.

- [x] Native provider result metadata passthrough.
  - Source: `openclaw-main/src/infra/outbound/deliver.ts`,
    `openclaw-main/src/infra/outbound/message-action-param-keys.ts`,
    `openclaw-main/src/channels/plugins/types.core.ts`, and
    `openclaw-main/src/cli/send-runtime/channel-outbound-send.test.ts`
  - Target: `src/openzues/services/gateway_outbound_runtime.py`,
    `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `fb9c9763`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_ops_mesh.py::test_provider_result_persistence_keeps_native_extended_metadata
    -q` (`1 passed`), adjacent provider metadata/native binding proof (`3
    passed`), `ruff check`, and `mypy`.

- [x] Plugin manifest activation-plan reason projection.
  - Source: `openclaw-main/src/plugins/activation-planner.ts`,
    `openclaw-main/src/plugins/activation-planner.test.ts`,
    `openclaw-main/src/plugins/cli-registry-loader.ts`,
    `openclaw-main/src/plugins/providers.runtime.ts`,
    `openclaw-main/src/plugins/channel-presence-policy.ts`
  - Target: `src/openzues/cli.py`,
    `src/openzues/services/gateway_plugin_activation.py`
  - Test: `tests/test_cli.py`, `tests/test_gateway_plugin_activation.py`
  - Status: checkpointed in `721ec0f2`.
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_projects_manifest_activation_plan_reasons
    -q` (`1 passed`), service proof `python -m pytest
    tests\test_gateway_plugin_activation.py::test_resolve_manifest_activation_plan_projects_reason_entries
    -q` (`1 passed`), adjacent plugin CLI proof (`5 passed`), adjacent
    activation service proof (`4 passed`), `ruff check`, and `mypy`.

- [x] Slack native route `thread_ts` fallback.
  - Source: `openclaw-main/extensions/slack/src/thread-ts.ts`,
    `openclaw-main/extensions/slack/src/thread-ts.test.ts`,
    `openclaw-main/extensions/slack/src/outbound-adapter.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `a461e5eb`.
  - Weight: 1
  - Last verified: 2026-05-02, focused Slack native route tests (`2 passed`),
    adjacent Slack native route tests (`5 passed`), `ruff check`, and `mypy`.

- [x] Slack native multi-media result metadata.
  - Source: `openclaw-main/test/helpers/channels/outbound-payload-contract.ts`,
    `openclaw-main/src/channels/plugins/outbound/direct-text-media.ts`,
    `openclaw-main/extensions/slack/src/outbound-adapter.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `e3b5bbc0`.
  - Weight: 1
  - Last verified: 2026-05-02, focused Slack media route tests (`2 passed`),
    adjacent Slack native/media route tests (`7 passed`), `ruff check`, and
    `mypy`.

- [ ] Packaging, companion apps, setup/onboarding, memory/media generation, and
  file-store-only transcript edge cases.
  - Source: OpenClaw repo-wide domains.
  - Status: open
  - Weight: 5+

## Update Rule

Only move a row to `[x]` when implementation, focused proof, adjacent proof,
lint/type checks, ledger update, and checkpoint evidence are all recorded.
