# OpenZues OpenClaw Parity Status

Agent report source: Gauss

Last updated: 2026-05-08

Primary ledgers:

- `docs/openclaw-parity-progress.md`
- `docs/openclaw-parity-unresolved-seams.md`

Use the progress ledger snapshot as the freshest percentage source. The README
may lag behind this tracker.

## Percentage Rollup

| Family | Percent | Confidence | Notes |
| --- | ---: | --- | --- |
| Repo-wide OpenClaw parity | ~99.9% | Medium | Breadth-weighted planning estimate, not generated metric; evidence band ~80-99.999999999999999999999999999999999999999999999995% |
| Active gateway/session/tool-contract family | ~99.9% | High for bounded local path | Does not mean whole product parity |
| Chat/session contract subfamily | ~99.98% | High for bounded local path | Current local session/chat contracts are near complete |
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

- [x] Imported plugin SDK provider web-search contract helper shim for
  scoped/top-level/keyless credential fields, configured web-search credential
  read/write helpers, scoped config merge, selection config application,
  scoped/unscoped SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `3dadf0fb`

- [x] Imported plugin SDK provider web facade helper shim for
  `provider-web-search` and `provider-web-fetch` imports, common web tool
  result/parameter helpers, markdown/text utilities, cache/timing helpers,
  search filter/date/freshness helpers, endpoint wrapper stubs, external
  content wrappers, the deprecated plugin-backed search provider error
  boundary, scoped/unscoped SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `0ba91657`

- [x] Imported plugin SDK device-bootstrap helper shim for setup bootstrap
  profile constants, role/scope normalization, fakeable bootstrap token issue/
  revoke/clear, native no-pairing list/approve boundary, scoped/unscoped SDK
  aliases, and generic SDK re-exports.
  - Status: checkpointed in `ae2fc79f`

- [x] Imported plugin SDK runtime-store helper shim for shared plugin/custom-key
  runtime slots, isolated legacy string stores, empty plugin-id rejection,
  falsy runtime preservation, scoped/unscoped SDK aliases, and generic SDK
  re-exports.
  - Status: checkpointed in `57cc0f37`

- [x] Imported plugin SDK runtime helper shim for logger-backed runtime
  adapters, runtime reuse/synthesis, custom exit errors, unavailable-exit
  projection, scoped/unscoped SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `5bd1435b`

- [x] Imported plugin SDK directory-runtime helper shim for default/empty
  directory adapters, user/group directory entry listing, query/limit filtering,
  resolved/inspected account listers, live runtime forwarding, scoped/unscoped
  SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `a354299e`

- [x] Imported plugin SDK directory-config-runtime helper shim for the slim
  config-backed directory facade, preserving query/limit filtering, directory
  entry projection, inspected/resolved listers, scoped/unscoped SDK aliases, and
  generic SDK re-exports without adapter-only exports.
  - Status: checkpointed in `335e215d`

- [x] Imported plugin SDK thread-bindings-runtime helper shim for binding-id
  parsing, channel/account timeout helpers, lifecycle/farewell helpers, and
  account-scoped conversation binding manager bind/touch/list/unbind/stop
  behavior.
  - Status: checkpointed in `06f36c6c`

- [x] Imported plugin SDK conversation-runtime helper shim for OpenClaw
  conversation label resolution, safe inbound-session recording with meta-task
  tracking and pinned main-DM route skip behavior, thread-binding helper reuse,
  scoped/unscoped SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `7c5271ba`

- [x] Imported plugin SDK outbound-runtime helper shim for fakeable outbound
  delegates, dynamic and legacy send-dep resolution, outbound identity/session
  context, plain-text sanitizer, payload planning/projection, fakeable delivery
  entry point, scoped/unscoped SDK aliases, and generic SDK re-exports.
  - Status: checkpointed in `a0df1bba`

- [x] Imported plugin SDK conversation-binding-runtime helper shim for session
  binding service access, adapter bind/list/resolve/touch/unbind, runtime route
  rewriting, plugin-owned no-rewrite behavior, configured binding route
  projection, readiness checks, pairing replies, scoped/unscoped SDK aliases,
  and generic SDK re-exports.
  - Status: checkpointed in `230ec9d2`

- [x] Imported plugin SDK session-binding/session-key runtime alias shim for
  narrow session-binding service access, test reset/inspection, thread binding
  lifecycle/farewell reuse, session-key agent-id resolution, scoped/unscoped SDK
  aliases, and generic SDK re-exports.
  - Status: checkpointed in `0307ca2f`

- [x] Imported plugin SDK session-store-runtime helper shim for normalized
  session-store entry lookup, legacy-key cleanup, agent-scoped store path
  resolution, group/direct/explicit/main session-key resolution, file-backed
  load/save/update helpers, inbound metadata recording, last-route delivery
  context updates, reset type/thread/channel config helpers, and freshness
  evaluation.
  - Status: checkpointed in `06e04786`

- [x] Imported plugin SDK account-id/configured-id subpath shim for slim
  `account-id` and `account-configured-ids` export surfaces, preserving
  account id normalization and configured account id listing without leaking
  the generic SDK object.
  - Status: checkpointed in `2e012bc2`

- [x] Imported plugin SDK agent-media-payload helper shim for legacy agent
  media payload field projection and agent-scoped media local roots across
  config/state media directories, canvas/workspace/sandbox roots, preferred
  temp root, and configured agent workspace.
  - Status: checkpointed in `21126502`

- [x] Imported plugin SDK agent-config-primitives helper shim for the narrow
  `ReplyRuntimeConfigSchemaShape` and `ToolPolicySchema` export surface,
  optional reply runtime primitive parsing, and the OpenClaw tool-policy
  `allow` plus `alsoAllow` conflict guard.
  - Status: checkpointed in `99bb3098`

- [x] Imported plugin SDK ACP binding resolve helper shim for
  `openclaw/plugin-sdk/acp-binding-resolve-runtime`, top-level typed ACP
  binding resolution, exact-account preference, parent conversation fallback,
  and deterministic ACP binding session-key metadata.
  - Status: checkpointed in `4c9ed6d6`

- [x] Imported plugin SDK Anthropic CLI facade shim for
  `CLAUDE_CLI_BACKEND_ID` and trimmed/case-insensitive Claude CLI provider
  detection through scoped and unscoped SDK aliases.
  - Status: checkpointed in `8289eaff`

- [x] Imported plugin SDK Anthropic Vertex auth-presence helper shim for
  metadata-server opt-in, Unicode-preserving explicit ADC credential paths, and
  direct ADC file-read probing.
  - Status: checkpointed in `f7c9e174`

- [x] Imported plugin SDK Anthropic Vertex facade helper shim for endpoint
  region precedence, env region validation, and env/ADC project ID resolution.
  - Status: checkpointed in `0ea37843`

- [x] Imported plugin SDK XAI model-id helper shim for the narrow
  `normalizeXaiModelId` alias and stale Grok model ID normalization.
  - Status: checkpointed in `6743ca28`

- [x] Imported plugin SDK channel pairing paths helper shim for the narrow
  `resolveChannelAllowFromPath` alias and sanitized allow-from file paths.
  - Status: checkpointed in `fa95764e`

- [x] Imported plugin SDK channel inbound roots helper shim for the narrow
  `mergeInboundPathRoots` alias and wildcard media-root deduping.
  - Status: checkpointed in `1e1d6c23`

- [x] Imported plugin SDK channel location helper shim for the narrow
  `formatLocationText` and `toLocationContext` aliases.
  - Status: checkpointed in `ad24fdc2`

- [x] Imported plugin SDK state paths helper shim for the narrow
  `STATE_DIR`, `resolveStateDir`, `resolveOAuthDir`, and
  `resolveRequiredHomeDir` aliases.
  - Status: checkpointed in `8c3128bf`

- [x] Imported plugin SDK setup adapter runtime helper shim for the narrow
  `createEnvPatchedAccountSetupAdapter` alias and scoped account setup config
  patching.
  - Status: checkpointed in `c0f33006`

- [x] Imported plugin SDK channel secret TTS runtime helper shim for the narrow
  `collectNestedChannelTtsAssignments` alias and nested voice TTS SecretRef
  assignment collection.
  - Status: checkpointed in `59936359`

- [x] Imported plugin SDK talk config runtime helper shim for the narrow
  `resolveActiveTalkProviderConfig` alias and active talk provider selection.
  - Status: checkpointed in `ef516298`

- [x] Imported plugin SDK GitHub Copilot token helper shim for the narrow
  `DEFAULT_COPILOT_API_BASE_URL`, `deriveCopilotApiBaseUrlFromToken`, and
  `resolveCopilotApiToken` aliases.
  - Status: checkpointed in `8ccd0928`

- [x] Imported plugin SDK channel plugin common/core helper shim for channel
  prelude exports, empty config schemas, channel metadata, account config
  mutation helpers, pairing approval text, and `createChannelPluginBase`.
  - Status: checkpointed in `b669ff0b`

- [x] Imported plugin SDK channel entry contract helper shim for bundled
  channel/setup entry definition, sidecar export loading, registration-mode
  behavior, and runtime setter wiring.
  - Status: checkpointed in `e0bb22bf`

- [x] Imported plugin SDK channel config primitives/schema helper shim for
  DM/group policy schemas, context visibility, tool policy, markdown and
  block-streaming schemas, nested DM config builders, multi-account extension
  helpers, `requireOpenAllowFrom`, and bundled provider schema handles.
  - Status: checkpointed in `7f046836`

- [x] Imported plugin SDK runtime-env helper shim for runtime IO, verbose/yes
  flags, sleep/timeout/retry, truthy env parsing, duration/backoff helpers,
  abort waiters, handler registration, subsystem logging facades, undici
  bootstrap posture, and WSL detection.
  - Status: checkpointed in `4e364149`

- [x] Imported plugin SDK channel-config-helpers shim for DM access
  normalization/migration helpers, config-write authorization helpers,
  allowFrom/default-target accessors, scoped/top-level/hybrid channel config
  adapters, and account-scoped DM security resolver helpers.
  - Status: checkpointed in `02ec0b78`

- [x] Imported plugin SDK channel-config-writes alias shim for the narrow
  config-write policy helper barrel.
  - Status: checkpointed in `7b668b3c`

- [x] Imported plugin SDK channel-lifecycle shim for account status sinks,
  abort/passive/server lifecycle waiters, run-state/keyed queues, finalizable
  draft stream controls, preview finalizers, and stall watchdogs.
  - Status: checkpointed in `d3bc5720`

- [x] Imported plugin SDK channel-core shim for exact channel plugin base,
  chat-channel composition, channel/setup entry registration, outbound route,
  thread-aware route recovery, target parsing, optional-entry parsing, and
  secret-file helper imports.
  - Status: checkpointed in `20c12150`

- [x] Imported plugin SDK channel-contract-testing shim for inbound context
  contract assertions, turn dispatch visible/final/count assertions, outbound
  send mock priming, inbound capture mock wiring, and pure type-only
  `channel-contract` runtime shape.
  - Status: checkpointed in `2fdb744c`

- [x] Imported plugin SDK channel-targets shim for channel entry matching,
  messaging target parsing, service-prefixed chat/allow target parsing,
  allowed sender matching, channel id/slug normalization, unresolved target
  fallback rows, and optional-token target resolution.
  - Status: checkpointed in `27bb6438`

- [x] Imported plugin SDK channel-streaming shim for streaming config object
  extraction, chunk-mode resolution, block-streaming enablement/coalescing,
  preview chunk config, preview tool-progress defaults, native transport flags,
  and preview stream-mode normalization.
  - Status: checkpointed in `9a9a6858`

- [x] Imported plugin SDK channel-envelope shim for inbound envelope
  formatting and envelope option helpers.
  - Status: checkpointed in `782e2591`

- [x] Imported plugin SDK channel-mention-gating shim for mention marker,
  mention regex/text utilities, and mention decision helpers.
  - Status: checkpointed in `22e17bc5`

- [x] Imported plugin SDK channel-runtime-context shim for register/get/watch
  runtime context helpers.
  - Status: checkpointed in `ced07255`

- [x] Imported plugin SDK channel-runtime compatibility facade shim for chat
  type normalization, reply prefix/typing helpers, channel id normalization,
  interactive reply reduction, poll normalization, system-event enqueue/reset,
  channel activity recording, heartbeat event/visibility helpers,
  transport-ready waits, and selected lifecycle helpers.
  - Status: checkpointed in `1cc947f3`

- [x] Imported plugin SDK compat facade shim for the deprecated broad
  migration barrel, including config-schema, channel policy/config/directory/
  reply-history helpers, channel reply pipeline aliases, runtime store/queue/
  temp/account helpers, provider auth helper aliases, command gating,
  diagnostics, context-engine registration, memory prompt addition delegation,
  BlueBubbles policy/status helpers, and selected channel lifecycle helpers.
  - Status: checkpointed in `f21a22bd`

- [x] Imported plugin SDK discord facade shim for the deprecated Discord
  compatibility barrel, including channel-common helpers, `DiscordConfigSchema`,
  status helpers, account/default-account inspection and resolution, target
  normalization, directory lists, component helpers, audit channel ids, group
  mention/tool policy resolution, runtime-config filled subagent thread
  auto-binding, thread binding list/unbind helpers, and fakeable bundled
  Discord public-surface delegation.
  - Status: checkpointed in `307777d8`

- [x] Imported plugin SDK extension-shared utility facade shim for schema
  parsing, timeout abort-signal construction, passive/probed/traffic status
  summaries, stoppable passive monitor lifecycle, logger-backed runtime
  fallback, open-DM allowlist issue projection, status issue field readers,
  deferred promise creation, plugin config issue mapping, read-only env secret
  provider gates, package-version candidate resolution, and no-proxy ambient
  proxy-agent resolution.
  - Status: checkpointed in `b56d15d7`

- [x] Imported plugin SDK channel-activity-runtime shim for
  `recordChannelActivity`.
  - Status: checkpointed in `89483357`

- [x] Imported plugin SDK inbound-envelope shim for route/envelope builder
  helpers.
  - Status: checkpointed in `d5ba314d`

- [x] Imported plugin SDK channel-secret-basic-runtime shim for channel/account
  surface helpers and secret assignment/warning collectors.
  - Status: checkpointed in `b2735360`

- [x] Imported plugin SDK channel-secret-runtime shim for the combined
  basic-plus-TTS channel secret helper barrel.
  - Status: checkpointed in `d192b523`

- [x] Imported plugin SDK secret-file-runtime shim for constants, sync
  readers, try-read behavior, and async private atomic writes.
  - Status: checkpointed in `fe13141a`

- [x] Imported plugin SDK secret-ref-runtime shim for the narrow
  `coerceSecretRef` helper barrel.
  - Status: checkpointed in `8b9f3671`

- [x] Imported plugin SDK secret-input-runtime shim for configured
  env-backed SecretRef resolution, fallback projection, and required SecretRef
  runtime helpers.
  - Status: checkpointed in `a3b36775`

- [x] Imported plugin SDK secret-input-schema shim plus `secret-input` schema
  builder re-exports for shared SecretInput validation helpers.
  - Status: checkpointed in `7935af8b`

- [x] Imported plugin SDK cron-store-runtime shim for cron store path
  resolution, split config/state persistence, and state merge-on-load helpers.
  - Status: checkpointed in `ded083a8`

- [x] Imported plugin SDK file-access-runtime shim for safe file URL handling,
  basename extraction, root-bounded writes, and root-bounded reads.
  - Status: checkpointed in `22e4455d`

- [x] Imported plugin SDK logging-core shim for subsystem logger creation,
  deterministic identifier redaction, and sensitive text redaction.
  - Status: checkpointed in `50142470`

- [x] Imported plugin SDK native-command-config-runtime shim for native
  command/skills enablement and explicit-disable helpers.
  - Status: checkpointed in `d2898256`

- [x] Imported plugin SDK host-runtime shim for hostname normalization and SCP
  remote host token sanitization helpers.
  - Status: checkpointed in `355ebc11`

- [x] Imported plugin SDK image-generation-core auth-runtime shim for the
  image-generation provider auth resolver alias.
  - Status: checkpointed in `532fd8de`

- [x] Imported plugin SDK model-session-runtime shim for agent concurrency,
  channel model override resolution, and session-entry model override mutation.
  - Status: checkpointed in `6f5096bc`

- [x] Imported plugin SDK process-runtime command helper shim for
  `runCommandWithTimeout`, command env/exit helpers, and child OOM wrapper
  helpers.
  - Status: checkpointed in `b5f485b3`; deeper process-runtime breadth remains
    open

- [x] Imported plugin SDK run-command normalized helper shim for
  `runPluginCommandWithTimeout`.
  - Status: checkpointed in `96c11a19`; deeper process/runtime breadth remains
    open

- [x] Imported plugin SDK string-coerce-runtime helper shim for primitive
  normalization and record detection helpers.
  - Status: checkpointed in `70df7410`; deeper SDK/runtime breadth remains open

- [x] Imported plugin SDK provider-auth-login runtime alias for the `.runtime`
  facade.
  - Status: checkpointed in `9c1a6b73`; deeper provider-auth runtime breadth
    remains open

- [x] Imported plugin SDK approval-auth-runtime helper shim for approver
  resolution and action authorization.
  - Status: checkpointed in `6cda257f`; deeper approval gateway runtime breadth
    remains open

- [x] Imported plugin SDK Telegram command config helper shim for slash command
  regex, normalization, and validation.
  - Status: checkpointed in `bd248520`; deeper provider command/runtime breadth
    remains open

- [x] Imported plugin SDK param-readers helper shim for common tool parameter
  coercion.
  - Status: checkpointed in `e7166e23`; deeper SDK/runtime breadth remains open

- [x] Imported plugin SDK provider-zai-endpoint helper shim for fakeable Z.AI
  endpoint probing and coding fallback metadata.
  - Status: checkpointed in `b3d88717`; deeper provider runtime breadth remains
    open

- [x] Imported plugin SDK provider-env-vars helper shim for provider auth env
  candidates, setup env overrides, and case-insensitive env scrubbing.
  - Status: checkpointed in `10d34034`; deeper provider/runtime breadth remains
    open

- [x] Imported plugin SDK session-visibility helper shim for session visibility
  defaults, sandbox clamps, A2A policy checks, and policy error messages.
  - Status: checkpointed in `4e95bfcb`; gateway-backed spawned listing depth
    remains open

- [x] Imported plugin SDK simple-completion-runtime helper shim for
  deterministic `extractAssistantText` behavior.
  - Status: checkpointed in `13a0fa6d`; broader completion model/auth
    transport helpers remain open

- [x] Imported plugin SDK approval-reply-runtime helper shim for approval
  action descriptors, command parsing, pending reply payloads, and metadata
  extraction.
  - Status: checkpointed in `2215e898`; broader approval gateway/client/
    delivery/native/handler runtimes remain open

- [x] Imported plugin SDK approval-client-helpers shim for channel approval
  enablement, target matching, request filtering, profile composition, and
  local-prompt suppression.
  - Status: checkpointed in `8a40507d`; broader approval gateway/delivery/
    native/handler runtimes remain open

- [x] Imported plugin SDK approval-delivery-helpers shim for channel approval
  capability creation/splitting, native DM/channel delivery availability,
  deprecated `approvals` surface aliasing, and forwarding fallback
  suppression.
  - Status: checkpointed in `d77756fa`; broader approval gateway/native/
    handler runtimes remain open

- [x] Imported plugin SDK approval-native-helpers shim for native approval
  target comparison, channel origin target resolution, target normalization,
  and approver-DM target mapping.
  - Status: checkpointed in `51d8ecdc`; broader approval native runtime/
    gateway/handler flows remain open

- [x] Imported plugin SDK approval-native-runtime delivery-helper shim for
  stable native target keys, origin/approver-DM delivery planning, target
  dedupe, DM-only origin notices, prepared-target delivery dedupe, and
  per-target error continuation.
  - Status: checkpointed in `424e376a`; broader
    `createChannelNativeApprovalRuntime` gateway/event lifecycle remains open

- [x] Imported plugin SDK approval-handler-adapter-runtime shim for lazy native
  runtime loading, eager availability checks, delegated presentation/
  transport/interaction hooks, and loaded-runtime-only observe hooks.
  - Status: checkpointed in `21aa746b`; broader approval handler runtime/
    gateway lifecycle remains open

- [x] Imported plugin SDK approval-handler-runtime adapter-factory shim for
  canonical native runtime adapter construction while keeping broader handler
  lifecycle functions fallback-safe and open.
  - Status: checkpointed in `3434972a`; broader handler lifecycle/gateway
    integration remains open

- [x] Imported plugin SDK approval-runtime aggregate shim for composing the
  already verified approval auth, reply, client, delivery, native helper, and
  filter helpers through the upstream aggregate barrel.
  - Status: checkpointed in `63554e0a`; broader approval gateway/native
    handler lifecycle remains open

- [x] Imported plugin SDK approval-gateway-runtime resolver shim for
  exec/plugin approval gateway method selection, default display-name
  projection, and not-found-only plugin fallback.
  - Status: checkpointed in `29c62d3f`; broader native approval runtime/
    handler lifecycle remains open

- [x] Imported plugin SDK approval-native-runtime factory shim for creating
  native approval runtimes with pending content delivery, active entry
  tracking, and resolved finalization.
  - Status: checkpointed in `67a72452`; expiration scheduling and capability
    handler wrapper remain open

- [x] Imported plugin SDK approval-handler-runtime wrapper shim for mapping
  the upstream handler adapter shape onto the native approval runtime factory.
  - Status: checkpointed in `e23b4e9e`; capability handler wrapper remains
    open

- [x] Imported plugin SDK approval-handler capability bridge shim for turning
  channel approval capabilities into native approval handlers with pending/
  resolved views, binding, observe hooks, and final update actions.
  - Status: checkpointed in `6ea77847`; native expiration scheduling remains
    open

- [x] Imported plugin SDK approval-native-runtime expiration scheduling for
  timer-based expiry finalization and timer cleanup on resolution/stop.
  - Status: checkpointed in `fa7cacbd`

- [x] Imported plugin SDK approval-renderers shim for scoped/unscoped
  `approval-renderers` imports, exec/plugin pending payloads, exec/plugin
  resolved payloads, `execApproval` channel data, and aggregate
  `approval-runtime` re-export coverage.
  - Status: checkpointed in `d6bb4129`

- [x] Imported plugin SDK approval-client-runtime alias shim for the exact
  runtime subpath re-exporting approval client enablement, target matching,
  request filters, profiles, and reply metadata.
  - Status: checkpointed in `f24a7746`

- [x] Imported plugin SDK approval-approvers alias shim for the exact
  `approval-approvers` subpath exposing only `resolveApprovalApprovers` with
  explicit precedence, fallback inference, normalization, and deduplication.
  - Status: checkpointed in `0740c2ab`

- [x] Imported plugin SDK approval-auth-helpers shim for exact helper imports,
  native auth adapter construction, and implicit same-chat authorization marker
  inspection.
  - Status: checkpointed in `8511485f`

- [x] Imported plugin SDK poll-runtime shim for exact poll helper imports,
  poll input normalization/validation, duration hour clamping, and multiselect
  max-selection resolution.
  - Status: checkpointed in `83f15bfa`

- [x] Imported plugin SDK lazy-runtime shim for exact cached module, surface,
  named-export, method, and method-binder helper imports.
  - Status: checkpointed in `6f66d9b8`

- [x] Imported plugin SDK config-paths shim for exact account-specific channel
  config base-path resolution and channel-root fallback.
  - Status: checkpointed in `c1a26ebe`

- [x] Imported plugin SDK context-visibility-runtime shim for default/channel/
  account visibility precedence plus supplemental-context decision/filter
  helpers.
  - Status: checkpointed in `1e503fde`

- [x] Imported plugin SDK heartbeat-runtime shim for indicator mapping, shared
  heartbeat event state/listeners, reset helpers, and visibility precedence.
  - Status: checkpointed in `a5863a1d`

- [x] Imported plugin SDK json-store shim for synchronous JSON load/save,
  fallback/existence reads, and atomic secure JSON writes.
  - Status: checkpointed in `9ba7a00e`

- [x] Imported plugin SDK diagnostic-runtime shim for diagnostic flag matching,
  public/internal event dispatch with trust metadata, reset helpers, and W3C
  traceparent helpers.
  - Status: checkpointed in `095e35fc`

- [x] Imported plugin SDK system-event-runtime shim for session-keyed ephemeral
  system-event queueing, duplicate suppression, cloned peeks, delivery-context
  normalization, and reset helpers.
  - Status: checkpointed in `5c49a1be`

- [x] Imported plugin SDK oauth-utils shim for form-url encoding and base64url/
  hex PKCE verifier/challenge generation.
  - Status: checkpointed in `210beb78`

- [x] Imported plugin SDK runtime-config-snapshot shim for activation-context
  runtime config access, snapshot set/get/clear, config-cache no-op, and
  source-snapshot selection.
  - Status: checkpointed in `39afd0ea`

- [x] Imported plugin SDK runtime-fetch shim for mocked-fetch detection,
  dispatcher-aware runtime fetch, and mocked-global fallback behavior.
  - Status: checkpointed in `14cdafc6`

- [x] Imported plugin SDK group-activation shim for activation mode
  normalization plus slash/colon activation command parsing.
  - Status: checkpointed in `48d912d7`

- [x] Imported plugin SDK media-store shim for file-backed media buffer saves,
  MIME/extension-aware IDs, safe path resolution, and max-byte rejection.
  - Status: checkpointed in `b45381ad`

- [x] Imported plugin SDK browser-security-runtime shim for proxy-env, safe
  file/path, SSRF, port, logging/redaction, external-content, and
  secret-equality helper exports.
  - Status: checkpointed in `66ee1a57`

- [x] Imported plugin SDK fetch-runtime shim for abort-safe fetch resolution,
  trusted-env proxy mode projection, HTTP proxy env precedence/NO_PROXY
  bypass checks, proxy-fetch metadata, and pinned DNS lookup helpers.
  - Status: checkpointed in `3aa66305`

- [x] Imported plugin SDK cli-backend shim for fresh/resume CLI watchdog
  default timeout windows and no-output timeout ratios.
  - Status: checkpointed in `be724e3f`

- [x] Imported plugin SDK type-only barrel shims for `config-types`,
  `document-extractor`, `music-generation`, `provider-model-types`,
  `qa-channel-protocol`, and `tts-runtime.types`, preserving empty runtime
  modules rather than broad generic SDK fallback exports.
  - Status: checkpointed in `fceeecc8`; exact `config-types` queue head
    reverified on 2026-05-07 with the focused type-only SDK barrel proof
    (`1 passed`)

- [x] Imported plugin SDK config-schema shim for root config object parsing and
  JSON Schema value validation with required/additional-property, enum
  allowed-values, and default-application behavior.
  - Status: checkpointed in `ae5489b2`

- [x] Imported plugin SDK entrypoints shim for canonical SDK entrypoint/subpath
  arrays, bundled-facade/public-owned entrypoint lists, source/specifier/export
  map builders, and expected dist artifact listing.
  - Status: checkpointed in `bd810f14`

- [x] Imported plugin SDK diffs shim for the narrow bundled-diffs helper
  surface, preserving exact `definePluginEntry` / temp-dir exports and cached
  lazy config-schema default behavior.
  - Status: checkpointed in `008c6120`

- [x] Imported plugin SDK ACPX shim for `AcpRuntimeError`, ACP backend
  registration/removal, Windows spawn helper exports, and provider-auth env
  filtering helpers.
  - Status: checkpointed in `c7541c95`

- [x] Imported plugin SDK ACP runtime backend shim for ACP runtime error checks,
  backend lookup/require/registration/removal, and lightweight reply-hook
  early-return behavior.
  - Status: checkpointed in `4833176b`

- [x] Imported plugin SDK ACP runtime facade shim for the ACP session-manager
  singleton, test-helper proxy surface, session-store entry reads, and shared
  ACP backend/error/reply-hook exports.
  - Status: checkpointed in `44166f55`

- [x] Imported plugin SDK ACP binding runtime shim for configured ACP binding
  resolution plus readiness ensure behavior through an injected ACP session
  manager.
  - Status: checkpointed in `37b428c1`

- [x] Imported plugin SDK CLI runtime shim for command formatting, duration
  parsing, parent-option inheritance, help examples, command-group
  registration, command runtime error handling, argv invocation projection,
  lazy-subcommand policy, note/theme helpers, and version metadata.
  - Status: checkpointed in `c052ce13`

- [x] Imported plugin SDK runtime-doctor shim for dangerous-name scope
  collection, legacy streaming/channel alias normalization, custom-path install
  issue detection/formatting, and pure plugin config uninstall mutation.
  - Status: checkpointed in `1a917206`

- [x] Imported plugin SDK provider-setup/self-hosted-provider-setup shim for
  self-hosted defaults, default model patching, OpenAI-compatible local
  discovery guards, provider discovery projection, interactive auth-result
  helpers, and non-interactive model/auth-profile/default-model config updates.
  - Status: checkpointed in `25ad92b6`

- [x] Imported plugin SDK LM Studio runtime shim for default constants,
  server/inference base URL normalization, provider config normalization,
  auth-header construction, loaded context-window resolution, reasoning
  capability/compat projection, and model wire entry mapping.
  - Status: checkpointed in `6f11c3fa`

- [x] Imported plugin SDK runtime-secret-resolution shim for resolver context,
  resolved assignment application, env-backed SecretRef maps, channel command
  secret target ids, and gateway command-secret unavailable projection.
  - Status: checkpointed in `d9574b0f`

- [x] Imported plugin SDK memory-core-host-query shim for keyword extraction,
  stop-word checks, duplicate/numeric filtering, and CJK trigram-tokenizer
  behavior.
  - Status: checkpointed in `0eaf8bf8`

- [x] Imported plugin SDK memory-core-host-multimodal shim for multimodal
  settings normalization and enabled-state checks.
  - Status: checkpointed in `5be944f7`

- [x] Imported plugin SDK memory-core-host-secret shim for configured-secret
  detection, env-backed SecretRef resolution, and unresolved-ref errors.
  - Status: checkpointed in `78f2a009`

- [x] Imported plugin SDK memory-core-host-events shim for memory event-log
  path resolution, append/read JSONL behavior, limit handling, and missing-log
  empty results.
  - Status: checkpointed in `d5695975`

- [x] Imported plugin SDK memory-core-host-status shim for vector, FTS, and
  cache status formatter projections.
  - Status: checkpointed in `bfcb12a2`

- [x] Imported plugin SDK memory-core-host-runtime-files shim for memory file
  listing, extra path normalization, safe agent memory reads, and QMD backend
  config projection.
  - Status: checkpointed in `a8d7b586`

- [x] Imported plugin SDK memory-host-files alias shim for the runtime-files
  helper surface.
  - Status: checkpointed in `857111d8`

- [x] Imported plugin SDK memory-core-host-runtime-core shim for runtime
  config, parameter readers, byte-size parsing, cron-style time projection,
  memory capability state, corpus supplements, public artifacts, and session
  transcript path helpers.
  - Status: checkpointed in `7b0703b7`

- [x] Imported plugin SDK memory-host-core alias shim for the runtime-core
  helper surface.
  - Status: checkpointed in `362efd71`

- [x] Imported plugin SDK memory-host-events alias shim for the events helper
  surface.
  - Status: checkpointed in `97885bb6`

- [x] Imported plugin SDK memory-host-markdown shim for trailing-newline and
  managed Markdown block replacement helpers.
  - Status: checkpointed in `4d8513b6`

- [x] Imported plugin SDK memory-host-search shim for active memory search
  manager lookup and cleanup delegation through the registered runtime.
  - Status: checkpointed in `a76a8d50`

- [x] Imported plugin SDK memory-host-status alias shim for the status helper
  surface.
  - Status: checkpointed in `2317c1e7`

- [x] Imported plugin SDK memory-core-host-runtime-cli shim for CLI helper
  exports and no-target command-secret resolution.
  - Status: checkpointed in `762da43c`

- [x] Imported plugin SDK memory-core-engine-runtime facade shim for
  engine-facing memory search, index-manager, embedding-provider doctor,
  audit, and repair exports with explicit unavailable backend projection.
  - Status: checkpointed in `ad4b05e5`

- [x] Imported plugin SDK memory-core-host-engine-embeddings shim for
  embedding provider registry, remote provider/fetch helpers, batch
  output/status/grouping helpers, vector/input normalization, cache headers,
  model-prefix normalization, multimodal classifiers, and local/upload
  unavailable boundaries.
  - Status: checkpointed in `4a1d82a8`

- [x] Imported plugin SDK memory-core-host-engine-foundation shim for agent
  scope/config/path helpers, memory search and sync config projection,
  duration parsing, SecretInput helpers, safe IO/logging/mime wrappers,
  transcript listener registration, global singletons, concurrency,
  shell-arg splitting, home path shortening, and UTF-16-safe truncation.
  - Status: checkpointed in `4d0b1103`

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

- [x] Companion QR human approval instructions, preserving OpenClaw's
  post-scan approval guidance with native OpenZues command names.
  - Status: checkpointed in `d6052fda`

- [x] Package distribution doctor diagnostics, preserving Windows-first
  package root, source-checkout, dist, and postinstall-inventory posture in
  `doctor --json`.
  - Status: checkpointed in `47d73351`

- [x] Package dist inventory drift diagnostics, preserving OpenClaw's
  missing/unexpected packaged-file warning contract.
  - Status: checkpointed in `69b23cb9`

- [x] Package dist legacy staging-debris diagnostics, preserving OpenClaw's
  `.openclaw-install-stage*` release guard warning.
  - Status: checkpointed in `b16db705`

- [x] Mixed-case package dist staging-debris proof, preserving OpenClaw's
  case-insensitive staging path matching.
  - Status: checkpointed in `9422c6b7`

- [x] Exact missing package dist inventory warning, preserving OpenClaw's
  fail-closed packaged install diagnostic.
  - Status: checkpointed in `76cdb404`

- [x] Package dist local metadata/dependency omission, preserving OpenClaw's
  inventory filters for local build stamps, source maps, and transient
  extension dependency trees.
  - Status: checkpointed in `6e8bb491`

- [x] Unsafe package dist symlink diagnostics, preserving OpenClaw's unsafe
  packaged path warning.
  - Status: checkpointed in `a9c7884f`

- [x] Externalized bundled extension dist omission, preserving OpenClaw's core
  package inventory boundary for publishable extensions.
  - Status: checkpointed in `06ba5480`

- [x] Private QA package dist artifact omission, preserving OpenClaw's private
  QA release filters.
  - Status: checkpointed in `bde731a9`

- [x] Package root resolves to source checkout warning, preserving OpenClaw's
  global install source-checkout guard.
  - Status: checkpointed in `912aee5e`

- [x] Bundled runtime sidecar enforcement, preserving OpenClaw's critical
  sidecar checks for installed bundled plugins.
  - Status: checkpointed in `07b17ad0`

- [x] Private QA bundled sidecar no-warning proof, preserving OpenClaw's
  non-packaged QA sidecar behavior.
  - Status: checkpointed in `ad248bf4`

- [x] Update dry-run preview package-spec mapping, preserving OpenClaw's
  non-mutating update preview contract with native OpenZues package identity.
  - Status: checkpointed in `08e8f76f`

- [x] Update-status timeout option, preserving OpenClaw's bounded status probe
  timeout surface.
  - Status: checkpointed in `6418d7f3`

- [x] Update package-spec env override, preserving OpenClaw's
  `OPENCLAW_UPDATE_PACKAGE_SPEC` root update behavior.
  - Status: checkpointed in `949de445`

- [x] Explicit update install-spec preservation, preserving raw GitHub/archive
  package spec behavior.
  - Status: checkpointed in `3227786a`

- [x] Root update runtime dispatch, preserving a native `openzues update`
  execution path instead of a placeholder unavailable response.
  - Status: checkpointed in `0c88812c`

- [x] Inherited update-status parent options, preserving OpenClaw's parent
  `update --json/--timeout status` option behavior.
  - Status: checkpointed in `f088293f`

- [x] Package update runtime path, preserving native global install execution
  for package-shaped root updates.
  - Status: checkpointed in `1291d361`

- [x] Npm update omit-optional fallback, preserving OpenClaw's package-update
  retry step after optional dependency failures.
  - Status: checkpointed in `f3177330`

- [x] Package update version verification, preserving OpenClaw's explicit
  version `global install verify` failure behavior.
  - Status: checkpointed in `1db09c3b`

- [x] Package update failedStep projection, preserving OpenClaw's failed-step
  result envelope for update failures.
  - Status: checkpointed in `98e4d5c9`

- [x] Package update Corepack prompt suppression, preserving OpenClaw's
  non-interactive global install environment default.
  - Status: checkpointed in `0f2cb0c1`

- [x] Package update Corepack prompt preservation, preserving caller-provided
  global install environment settings.
  - Status: checkpointed in `9fd00cad`

- [x] Windows package install env, preserving OpenClaw's npm prompt suppression
  and native dependency-download guard during global package updates.
  - Status: checkpointed in `80e49178`

- [x] Portable Git PATH prepending, preserving OpenClaw's Windows bundled Git
  helper path order for global package updates.
  - Status: checkpointed in `e692f8b6`

- [x] Owning npm command resolution, preserving OpenClaw's installed-prefix
  `npm.cmd` preference for global package updates.
  - Status: checkpointed in `de046811`

- [x] Ambient npm fallback when owner is absent, preserving OpenClaw's
  no-path-shape-only command ownership guard.
  - Status: checkpointed in `0826cfaa`

- [x] Missing package version verifier wording, preserving OpenClaw's
  `<missing>` package verification projection.
  - Status: checkpointed in `ad9ba5a5`

- [x] Source-checkout package update verifier, preserving OpenClaw's
  `collectInstalledGlobalPackageErrors` source-checkout package-root
  rejection before post-update doctor/swap.
  - Status: checkpointed in `a330fecc`

- [x] Package update missing dist-inventory gate, preserving OpenClaw's
  installed-package `dist/postinstall-inventory.json` requirement for
  versions at `2026.4.15` and newer.
  - Status: checkpointed in `d7e87c9b`

- [x] Package update invalid dist-inventory rejection, preserving OpenClaw's
  invalid package dist inventory verifier projection before doctor/swap.
  - Status: checkpointed in `2f59d485`

- [x] Package update dist inventory file drift, preserving OpenClaw's
  missing/unexpected packaged dist file verifier projection before doctor/swap.
  - Status: checkpointed in `1e373c7f`

- [x] Package update supplemental runtime sidecars, preserving OpenClaw's
  critical bundled plugin sidecar check when inventory omits those files.
  - Status: checkpointed in `9ba6843f`

- [x] Package update dist inventory omission filters, preserving OpenClaw's
  source map, local metadata, private QA, plugin SDK QA, and bundled plugin
  dependency exclusions before update verifier drift reporting.
  - Status: checkpointed in `e7d960e0`

- [x] Package update unsafe dist path rejection, preserving OpenClaw's unsafe
  symlinked dist entry verifier projection.
  - Status: checkpointed in `691fdabd`

- [x] Package update externalized extension omission, preserving OpenClaw's
  published external extension dist filter in update verifier inventory
  comparison.
  - Status: checkpointed in `a06dd570`

- [x] Package update legacy runtime sidecars, preserving OpenClaw's sidecar
  fallback for older installs without required package dist inventory.
  - Status: checkpointed in `603cdb2a`

- [x] Package update omitted-subtree safety ordering, preserving OpenClaw's
  externalized/dependency subtree omission before unsafe symlink checks.
  - Status: checkpointed in `2830b5ef`

- [x] Package update staged crash cleanup proof, preserving OpenClaw's staged
  npm prefix cleanup when the install command raises before verification/swap.
  - Status: checkpointed in `beadafaa`

- [x] Package update includeInCore inventory guard, preserving OpenClaw's
  publishable-but-core bundled extension package dist inventory behavior.
  - Status: checkpointed in `c83c2a72`

- [x] Package update private QA omission proof, preserving OpenClaw's private
  QA sidecar and stale metadata omissions in update verification.
  - Status: checkpointed in `b663e3e0`

- [x] Package update runtime staging debris verifier, preserving OpenClaw's
  installed-package `.openclaw-install-stage*` drift reporting.
  - Status: checkpointed in `d58b0879`

- [x] Package update malformed extension manifest rejection, preserving
  OpenClaw's non-`ENOENT` source extension manifest failure posture.
  - Status: checkpointed in `733c7b15`

- [x] Doctor malformed extension manifest warning, preserving package dist
  inventory diagnostics for invalid bundled extension manifests.
  - Status: checkpointed in `df582190`

- [x] Npm shim rollback during staged package swap, preserving OpenClaw's
  package-root and bin-shim restore behavior on staged shim replacement
  failure.
  - Status: checkpointed in `03f1ee46`

- [x] Git update control-ui clean-check exclusion, preserving OpenClaw's
  generated `dist/control-ui` dirty-file allowance.
  - Status: checkpointed in `5171f2f2`

- [x] Git release-channel tag checkout, preserving OpenClaw's stable/beta
  `v*` tag resolution, beta stable-fallback, detached checkout, and
  `no-release-tag` guard.
  - Status: checkpointed in `1f45d307`

- [x] Git preflight edge-failure proof, preserving OpenClaw's `no-target-sha`
  and `preflight-no-good-commit` result boundaries.
  - Status: checkpointed in `7b15fafc`

- [x] Startup auto-update dispatch, preserving config `update.auto.enabled`,
  stable/beta package target resolution with beta fallback, native package
  update dispatch, and `OPENCLAW_NO_AUTO_UPDATE` suppression.
  - Status: checkpointed in `822eb6a9`

- [x] Startup auto-update throttling state, preserving stable first-seen
  delay/jitter and beta recent-attempt suppression.
  - Status: checkpointed in `a1bb5d30`

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

- [x] Feishu/Lark route-backed account probe support, preserving OpenClaw's
  `probeFeishu` status hook over the Open API `openclaw_bot/ping` endpoint
  with bot name/open-id projection.
  - Status: checkpointed in `bf1d1d3c`

- [x] Mattermost route-backed account probe support, preserving OpenClaw's
  `probeMattermost` status hook over `/api/v4/users/me` with bot user
  projection.
  - Status: checkpointed in `ba0205fc`

- [x] Signal route-backed account probe support, preserving OpenClaw's
  `probeSignal` status hook over `/api/v1/check` plus JSON-RPC `version`,
  without requiring a route secret.
  - Status: checkpointed in `1af31a04`

- [x] IRC route-backed account probe support, preserving OpenClaw's `probeIrc`
  status hook over IRC PASS/NICK/USER readiness, PING/PONG handling, `001`
  welcome detection, and `QUIT :probe` cleanup.
  - Status: checkpointed in `fd5d246b`

- [x] Twitch route-backed account probe support, preserving OpenClaw's
  `probeTwitch` status hook over Twitch IRC OAuth PASS/NICK readiness,
  PING/PONG handling, `001` welcome detection, connected projection, and
  `QUIT :probe` cleanup.
  - Status: checkpointed in `5772e6a9`

- [x] BlueBubbles route-backed account probe support, preserving OpenClaw's
  `probeBlueBubbles` status hook over `/api/v1/ping`, provider HTTP status
  projection, and non-2xx error probe preservation.
  - Status: checkpointed in `7c9ffdcb`

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

- [x] Imported plugin SDK tool-send shim.
  - Source: `openclaw-main/src/plugin-sdk/tool-send.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `87450dcc`
  - Weight: 1
  - Last verified: 2026-05-07, focused tool-send proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1080 deselected`), adjacent
    imported-plugin proof (`272 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK webhook-ingress shim.
  - Source: `openclaw-main/src/plugin-sdk/webhook-ingress.ts`,
    `openclaw-main/src/gateway/auth-rate-limit.ts`,
    `openclaw-main/src/infra/ws.ts`,
    `openclaw-main/src/plugins/http-path.ts`, and
    `openclaw-main/src/infra/http-body.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `399e784a`
  - Weight: 1
  - Last verified: 2026-05-07, focused webhook-ingress proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1082 deselected`), adjacent
    imported-plugin proof (`273 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK web-media shim.
  - Source: `openclaw-main/src/plugin-sdk/web-media.ts`,
    `openclaw-main/src/media/web-media.ts`,
    `openclaw-main/src/media/local-media-access.ts`,
    `openclaw-main/src/media/local-roots.ts`,
    `openclaw-main/src/media/mime.ts`, and
    `openclaw-main/src/media/constants.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `a60b54f2`
  - Weight: 1
  - Last verified: 2026-05-07, focused web-media proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1082 deselected`), adjacent
    imported-plugin proof (`274 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK speech facade shim.
  - Source: `openclaw-main/src/plugin-sdk/speech.ts`,
    `openclaw-main/src/plugin-sdk/speech-core.ts`,
    `openclaw-main/src/tts/openai-compatible-speech-provider.ts`,
    `openclaw-main/src/tts/openai-compatible-speech-provider.test.ts`, and
    `openclaw-main/src/agents/provider-http-errors.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `97ec0d27`
  - Weight: 1
  - Last verified: 2026-05-07, focused speech facade proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1084 deselected`), adjacent
    imported-plugin proof (`275 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK zalouser compatibility facade shim.
  - Source: `openclaw-main/src/plugin-sdk/zalouser.ts`,
    `openclaw-main/src/plugin-sdk/command-auth.ts`, and
    `openclaw-main/src/plugin-sdk/command-auth.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `6f0c70b5`
  - Weight: 1
  - Last verified: 2026-05-07, focused zalouser proof (`1 passed`),
    adjacent command-auth proof (`3 passed, 1085 deselected`), adjacent
    imported-plugin proof (`276 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK zod facade shim.
  - Source: `openclaw-main/src/plugin-sdk/zod.ts`,
    `openclaw-main/extensions/acpx/src/config-schema.ts`, and
    `openclaw-main/extensions/feishu/src/config-schema.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `c49cbd4a`
  - Weight: 1
  - Last verified: 2026-05-07, focused zod proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1085 deselected`), adjacent
    imported-plugin proof (`277 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK web-content-extractor facade shim.
  - Source: `openclaw-main/src/plugin-sdk/web-content-extractor.ts`,
    `openclaw-main/src/agents/tools/web-fetch-utils.ts`, and
    `openclaw-main/src/agents/tools/web-fetch-visibility.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `563d69d7`
  - Weight: 1
  - Last verified: 2026-05-07, focused web-content-extractor proof (`1
    passed`), adjacent web/provider proof (`3 passed, 1087 deselected`),
    adjacent imported-plugin proof (`278 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK plugin-entry facade shim.
  - Source: `openclaw-main/src/plugin-sdk/plugin-entry.ts`,
    `openclaw-main/src/plugins/config-schema.ts`, and
    `openclaw-main/src/plugin-sdk/lazy-value.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `b1fd730f`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-entry proof (`1 passed`),
    adjacent entrypoint/facade proof (`5 passed, 1086 deselected`),
    adjacent imported-plugin proof (`279 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK optional-channel-setup facade shim.
  - Source: `openclaw-main/src/plugin-sdk/optional-channel-setup.ts`,
    `openclaw-main/src/routing/session-key.ts`, and
    `openclaw-main/src/terminal/links.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `34c792c1`
  - Weight: 1
  - Last verified: 2026-05-07, focused optional-channel-setup proof (`1
    passed`), adjacent setup/channel proof (`5 passed, 1087 deselected`),
    adjacent imported-plugin proof (`280 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK outbound-media facade shim.
  - Source: `openclaw-main/src/plugin-sdk/outbound-media.ts`,
    `openclaw-main/src/media/load-options.ts`, and
    `openclaw-main/src/plugin-sdk/web-media.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `49969f8f`
  - Weight: 1
  - Last verified: 2026-05-07, focused outbound-media proof (`1 passed`),
    adjacent media/reply proof (`3 passed, 1090 deselected`), adjacent
    imported-plugin proof (`281 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK delivery-queue-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/delivery-queue-runtime.ts`,
    `openclaw-main/src/infra/outbound/delivery-queue-recovery.ts`, and
    `openclaw-main/src/infra/outbound/deliver-runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `183c5a68`
  - Weight: 1
  - Last verified: 2026-05-07, focused delivery-queue-runtime proof (`1
    passed`), adjacent runtime proof (`3 passed, 1091 deselected`), adjacent
    imported-plugin proof (`282 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK migration-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/migration-runtime.ts`,
    `openclaw-main/src/plugin-sdk/migration.ts`, and
    `openclaw-main/src/plugins/types.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `7a9c8208`
  - Weight: 1
  - Last verified: 2026-05-07, focused migration-runtime proof (`1 passed`),
    adjacent runtime proof (`3 passed, 1092 deselected`), adjacent
    imported-plugin proof (`283 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK migration helper facade shim.
  - Source: `openclaw-main/src/plugin-sdk/migration.ts` and
    `openclaw-main/src/plugins/types.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `d4a72ad9`
  - Weight: 1
  - Last verified: 2026-05-07, focused migration helper proof (`1 passed`),
    adjacent migration/runtime proof (`3 passed, 1093 deselected`), adjacent
    imported-plugin proof (`284 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK outbound-send-deps facade shim.
  - Source: `openclaw-main/src/plugin-sdk/outbound-send-deps.ts` and
    `openclaw-main/src/infra/outbound/send-deps.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `90665ba5`
  - Weight: 1
  - Last verified: 2026-05-07, focused outbound-send-deps proof (`1 passed`),
    adjacent outbound/runtime proof (`3 passed, 1094 deselected`), adjacent
    imported-plugin proof (`285 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK command-status-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/command-status-runtime.ts` and
    `openclaw-main/src/plugin-sdk/command-status.runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `b0242a2c`
  - Weight: 1
  - Last verified: 2026-05-07, focused command-status-runtime proof
    (`1 passed`), adjacent command status proof (`2 passed, 1096 deselected`),
    adjacent imported-plugin proof (`286 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK reply-runtime aggregate facade shim.
  - Source: `openclaw-main/src/plugin-sdk/reply-runtime.ts` and adjacent
    `openclaw-main/src/auto-reply/*` helper modules
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `32213a5c`
  - Weight: 1
  - Last verified: 2026-05-07, focused reply-runtime proof (`1 passed`),
    adjacent reply facade proof (`6 passed, 1093 deselected`), adjacent
    imported-plugin proof (`287 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK reply-dispatch-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/reply-dispatch-runtime.ts` and
    adjacent `openclaw-main/src/auto-reply/*` helper modules
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `c587ef3e`
  - Weight: 1
  - Last verified: 2026-05-07, focused reply-dispatch-runtime proof
    (`1 passed`), adjacent reply dispatch proof (`4 passed, 1096 deselected`),
    adjacent imported-plugin proof (`288 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK inbound-reply-dispatch facade shim.
  - Source: `openclaw-main/src/plugin-sdk/inbound-reply-dispatch.ts` and
    adjacent `openclaw-main/src/channels/turn/*` helper modules
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `25231852`
  - Weight: 1
  - Last verified: 2026-05-07, focused inbound-reply-dispatch proof
    (`1 passed`), adjacent inbound/reply dispatch proof (`4 passed, 1097
    deselected`), adjacent imported-plugin proof (`289 passed, 812
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK interactive-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/interactive-runtime.ts` and
    adjacent `openclaw-main/src/interactive/payload.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `3781cad9`
  - Weight: 1
  - Last verified: 2026-05-07, focused interactive-runtime proof (`1 passed`),
    adjacent interactive/outbound payload proof (`3 passed, 1099 deselected`),
    adjacent imported-plugin proof (`290 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK infra-runtime compatibility facade shim.
  - Source: `openclaw-main/src/plugin-sdk/infra-runtime.ts` and adjacent
    `openclaw-main/src/infra/*` plus `openclaw-main/src/utils/*` helper
    modules
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `0ba78971`
  - Weight: 1
  - Last verified: 2026-05-07, focused infra-runtime proof (`1 passed`),
    adjacent infra/runtime proof (`6 passed, 1097 deselected`), adjacent
    imported-plugin proof (`291 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK media-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/media-runtime.ts` and adjacent
    `openclaw-main/src/media/*`, `openclaw-main/src/polls.ts`, and
    `openclaw-main/src/channels/plugins/outbound/direct-text-media.ts`
    helper modules
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `85e4b720`
  - Weight: 1
  - Last verified: 2026-05-07, focused media-runtime proof (`1 passed`),
    adjacent media/import proof (`7 passed, 1097 deselected`), adjacent
    imported-plugin proof (`292 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK plugin-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/plugin-runtime.ts` and adjacent
    `openclaw-main/src/plugins/*` command, HTTP route, interactive, lazy
    service, global hook, and gateway request-scope helper modules
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `eb39f899`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-runtime proof (`1 passed`),
    adjacent plugin-runtime proof (`9 passed, 1096 deselected`), adjacent
    imported-plugin proof (`293 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK security-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/security-runtime.ts` and adjacent
    `openclaw-main/src/secrets/*`, `openclaw-main/src/security/*`, and
    access-group helper modules
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `16f5ab50`
  - Weight: 1
  - Last verified: 2026-05-07, focused security-runtime proof (`1 passed`),
    adjacent security/import proof (`5 passed, 1101 deselected`), adjacent
    imported-plugin proof (`294 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK gateway-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/gateway-runtime.ts` and adjacent
    `openclaw-main/src/gateway/*`, `openclaw-main/src/cli/gateway-rpc.ts`,
    and `openclaw-main/src/infra/ws.ts` helper modules
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `dc028590`
  - Weight: 1
  - Last verified: 2026-05-07, focused gateway-runtime proof (`1 passed`),
    adjacent gateway/import proof (`3 passed, 1104 deselected`), adjacent
    imported-plugin proof (`295 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK hook-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/hook-runtime.ts` and adjacent
    `openclaw-main/src/hooks/*` plus
    `openclaw-main/src/plugins/hook-runner-global.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `89db1c12`
  - Weight: 1
  - Last verified: 2026-05-07, focused hook-runtime proof (`1 passed`),
    adjacent hook/plugin-runtime proof (`3 passed, 1105 deselected`),
    adjacent imported-plugin proof (`296 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime-test-contracts facade shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime-test-contracts.ts`
    and adjacent `openclaw-main/src/plugin-sdk/test-helpers/agents/*`
    runtime contract fixtures
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `0db396fe`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime-test-contracts proof
    (`1 passed`), adjacent agent-runtime proof (`14 passed, 1095 deselected`),
    adjacent imported-plugin proof (`297 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK channel-target-testing facade shim.
  - Source: `openclaw-main/src/plugin-sdk/channel-target-testing.ts` and
    `openclaw-main/src/test-helpers/resolve-target-error-cases.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `e6307d8a`
  - Weight: 1
  - Last verified: 2026-05-07, focused channel-target-testing proof
    (`1 passed`), adjacent channel target proof (`3 passed, 1107 deselected`),
    adjacent imported-plugin proof (`298 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK channel-test-helpers facade shim.
  - Source: `openclaw-main/src/plugin-sdk/channel-test-helpers.ts` and
    adjacent `openclaw-main/src/plugin-sdk/test-helpers/*` channel helper
    modules plus `openclaw-main/src/test-utils/channel-plugins.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `67872a14`
  - Weight: 1
  - Last verified: 2026-05-07, focused channel-test-helpers proof
    (`1 passed`), adjacent channel helper proof (`4 passed, 1107 deselected`),
    adjacent imported-plugin proof (`299 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK plugin-test-api facade shim.
  - Source: `openclaw-main/src/plugin-sdk/plugin-test-api.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `db9e84ac`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-test-api proof (`1 passed`),
    adjacent plugin-test-api proof (`2 passed, 1110 deselected`), adjacent
    imported-plugin proof (`300 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK plugin-test-contracts facade shim.
  - Source: `openclaw-main/src/plugin-sdk/plugin-test-contracts.ts` and
    adjacent `openclaw-main/src/plugin-sdk/test-helpers/*` contract modules
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `086382f8`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-test-contracts proof
    (`1 passed`), adjacent plugin-test-contracts/plugin-test-api proof
    (`2 passed, 1111 deselected`), adjacent imported-plugin proof
    (`301 passed, 812 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Imported plugin SDK plugin-test-runtime facade shim.
  - Source: `openclaw-main/src/plugin-sdk/plugin-test-runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `084da020`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-test-runtime proof
    (`1 passed`), adjacent plugin-test-runtime/plugin-test-contracts/
    plugin-test-api proof (`3 passed, 1111 deselected`), adjacent
    imported-plugin proof (`302 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK provider-test-contracts facade shim.
  - Source: `openclaw-main/src/plugin-sdk/provider-test-contracts.ts` and
    `openclaw-main/src/plugin-sdk/test-helpers/*provider*`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `7494160a`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-test-contracts proof
    (`1 passed`), adjacent provider-test-contracts/plugin-test-runtime/
    plugin-test-contracts proof (`3 passed, 1112 deselected`), adjacent
    imported-plugin proof (`303 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK test-env facade shim.
  - Source: `openclaw-main/src/plugin-sdk/test-env.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `e2368bf5`
  - Weight: 1
  - Last verified: 2026-05-07, focused test-env proof (`1 passed`),
    adjacent test-env/provider-test-contracts/plugin-test-runtime proof
    (`3 passed, 1113 deselected`), adjacent imported-plugin proof (`304
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK test-fixtures facade shim.
  - Source: `openclaw-main/src/plugin-sdk/test-fixtures.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `aa63f674`
  - Weight: 1
  - Last verified: 2026-05-07, focused test-fixtures proof (`1 passed`),
    system-event runtime regression proof (`1 passed`), adjacent
    test-fixtures/test-env/provider-test-contracts proof (`3 passed, 1114
    deselected`), adjacent imported-plugin proof (`305 passed, 812
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK test-node-mocks facade shim.
  - Source: `openclaw-main/src/plugin-sdk/test-node-mocks.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `b5b60a9e`
  - Weight: 1
  - Last verified: 2026-05-07, focused test-node-mocks proof (`1 passed`),
    adjacent test-node-mocks/test-fixtures/test-env proof (`3 passed, 1115
    deselected`), adjacent imported-plugin proof (`306 passed, 812
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK provider-http-test-mocks facade shim.
  - Source: `openclaw-main/src/plugin-sdk/provider-http-test-mocks.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `462e8f82`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-http-test-mocks proof (`1
    passed`), adjacent provider-http-test-mocks/test-node-mocks/test-fixtures
    proof (`3 passed, 1116 deselected`), adjacent imported-plugin proof (`307
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK testing compatibility facade shim.
  - Source: `openclaw-main/src/plugin-sdk/testing.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `e6747208`
  - Weight: 1
  - Last verified: 2026-05-07, focused testing compatibility proof (`1
    passed`), adjacent testing/provider-http-test-mocks/test-node-mocks proof
    (`3 passed, 1117 deselected`), adjacent imported-plugin proof (`308
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK setup facade shim.
  - Source: `openclaw-main/src/plugin-sdk/setup.ts`,
    `openclaw-main/src/channels/plugins/setup-helpers.ts`,
    `openclaw-main/src/channels/plugins/setup-wizard-helpers.ts`,
    `openclaw-main/src/channels/plugins/setup-wizard-binary.ts`,
    `openclaw-main/src/channels/plugins/setup-wizard-proxy.ts`,
    `openclaw-main/src/channels/plugins/setup-group-access.ts`, and
    `openclaw-main/src/plugin-sdk/resolution-notes.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `ec94f934`
  - Weight: 1
  - Last verified: 2026-05-07, focused setup facade proof (`1 passed`),
    adjacent setup facade/runtime/tools proof (`4 passed, 1117 deselected`),
    adjacent imported-plugin proof (`309 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK resolution-notes subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/resolution-notes.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `9c56ff39`
  - Weight: 1
  - Last verified: 2026-05-08, focused resolution-notes red/green proof
    (fallback behavior returned raw input objects before implementation, then
    `1 passed`), adjacent resolution/tool-send/web-media proof (`3 passed,
    1128 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK facade-loader subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/facade-loader.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `29aa7956`
  - Weight: 1
  - Last verified: 2026-05-08, focused facade-loader red/green proof
    (generic fallback returned empty/non-cached proxy behavior before
    implementation, then `1 passed`), adjacent facade/plugin-test/runtime proof
    (`3 passed, 1129 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Imported plugin SDK session-transcript-hit subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/session-transcript-hit.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `b294d317`
  - Weight: 1
  - Last verified: 2026-05-08, focused session-transcript-hit red/green proof
    (generic fallback returned raw inputs before implementation, then `1
    passed`), adjacent session-store/visibility proof (`3 passed, 1130
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK pairing-access subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/pairing-access.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `e04677d3`
  - Weight: 1
  - Last verified: 2026-05-08, focused pairing-access red/green proof
    (generic fallback returned raw params and failed with
    `access.readAllowFromStore is not a function` before implementation, then
    `1 passed`), adjacent channel-pairing proof (`3 passed, 1131
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK facade-resolution-shared subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/facade-resolution-shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `2938b03a`
  - Weight: 1
  - Last verified: 2026-05-08, focused facade-resolution-shared red/green
    proof (generic fallback returned objects into `path.relative` before
    implementation, then `1 passed`), adjacent facade/plugin proof (`3 passed,
    1132 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK facade-runtime subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/facade-runtime.ts`,
    `openclaw-main/src/plugin-sdk/facade-activation-check.runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `1e9b65f5`
  - Weight: 1
  - Last verified: 2026-05-08, focused facade-runtime red/green proof
    (`__testing.loadFacadeModuleAtLocationSync` was missing before
    implementation, then `1 passed`), adjacent facade proof (`3 passed, 1133
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK facade-activation-check.runtime subpath shim.
  - Source:
    `openclaw-main/src/plugin-sdk/facade-activation-check.runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `1f2ec91c`
  - Weight: 1
  - Last verified: 2026-05-08, focused facade-activation-check.runtime
    red/green proof (exact subpath returned generic passthrough functions
    before implementation, then `1 passed`), adjacent facade proof (`3 passed,
    1153 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK test-helpers/string-utils subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/test-helpers/string-utils.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `e2ba3082`
  - Weight: 1
  - Last verified: 2026-05-08, focused string-utils red/green proof
    (exact subpath returned the broad generic SDK export set before
    implementation, then `1 passed`), adjacent helper proof (`3 passed, 1134
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK test-helpers/envelope-timestamp subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/test-helpers/envelope-timestamp.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `54b47a45`
  - Weight: 1
  - Last verified: 2026-05-08, focused envelope-timestamp red/green proof
    (exact subpath returned the broad generic SDK export set before
    implementation, then `1 passed`), adjacent helper proof (`3 passed, 1135
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK test-helpers/pairing-reply subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/test-helpers/pairing-reply.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `75ac3561`
  - Weight: 1
  - Last verified: 2026-05-08, focused pairing-reply red/green proof
    (exact subpath returned the broad generic SDK export set before
    implementation, then `1 passed`), adjacent helper proof (`3 passed, 1136
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK github-copilot-login subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/github-copilot-login.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `0561baa6`
  - Weight: 1
  - Last verified: 2026-05-08, focused github-copilot-login red/green proof
    (exact subpath returned the broad generic SDK export set before
    implementation, then `1 passed`), adjacent provider-auth login proof (`2
    passed, 1138 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK copilot-proxy subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/copilot-proxy.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `808c9260`
  - Weight: 1
  - Last verified: 2026-05-08, focused copilot-proxy red/green proof
    (exact subpath returned the broad generic SDK export set before
    implementation, then `1 passed`), adjacent plugin-entry proof (`4 passed,
    1137 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK private-qa-bundled-env subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/private-qa-bundled-env.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `fc6c72d4`
  - Weight: 1
  - Last verified: 2026-05-08, focused private-qa-bundled-env red/green proof
    (exact subpath returned the broad generic SDK export set before
    implementation, then `1 passed`), adjacent QA/plugin proof (`5 passed,
    1137 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK diagnostics-otel subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/diagnostics-otel.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `1bc4c0f9`
  - Weight: 1
  - Last verified: 2026-05-08, focused diagnostics-otel red/green proof
    (exact subpath returned the broad generic SDK export set and eager
    transport side effect before implementation, then `1 passed`), adjacent
    diagnostic/logging proof (`6 passed, 1137 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK thread-ownership subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/thread-ownership.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `41dad57f`
  - Weight: 1
  - Last verified: 2026-05-08, focused thread-ownership red/green proof
    (exact subpath returned the broad generic SDK export set before
    implementation, then `1 passed`), adjacent SSRF/plugin-entry proof (`5
    passed, 1139 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK ssrf-dispatcher subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/ssrf-dispatcher.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `7b283bdc`
  - Weight: 1
  - Last verified: 2026-05-08, focused ssrf-dispatcher red/green proof
    (exact subpath returned the broad generic SDK export set before
    implementation, then `1 passed`), adjacent SSRF proof (`3 passed, 1142
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK bluebubbles-policy subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/bluebubbles-policy.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `0cfb2157`
  - Weight: 1
  - Last verified: 2026-05-08, focused bluebubbles-policy red/green proof
    (exact subpath returned the broad generic SDK export set and passthrough
    sender policy before implementation, then `1 passed`), adjacent
    BlueBubbles/compat proof (`4 passed, 1142 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK telegram-command-ui subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/telegram-command-ui.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `185f5b52`
  - Weight: 1
  - Last verified: 2026-05-08, focused telegram-command-ui red/green proof
    (exact subpath returned the broad generic SDK export set before
    implementation, then `1 passed`), adjacent Telegram command proof (`4
    passed, 1143 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK telegram-account subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/telegram-account.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `49838584`
  - Weight: 1
  - Last verified: 2026-05-08, focused telegram-account red/green proof
    (exact subpath returned generic passthrough data before implementation,
    then `1 passed`), adjacent Telegram/channel config proof (`3 passed, 1145
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK irc-surface subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/irc-surface.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `a2edff86`
  - Weight: 1
  - Last verified: 2026-05-08, focused irc-surface red/green proof
    (exact subpath returned generic passthrough data before implementation,
    then `1 passed`), adjacent provider/channel helper proof (`4 passed, 1145
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK mattermost-policy subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/mattermost-policy.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `f18197d2`
  - Weight: 1
  - Last verified: 2026-05-08, focused mattermost-policy red/green proof
    (exact subpath returned generic passthrough data before implementation,
    then `1 passed`), adjacent provider/channel policy proof (`4 passed, 1146
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK matrix-runtime-surface subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/matrix-runtime-surface.ts`,
    `openclaw-main/extensions/matrix/src/auth-precedence.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `f4473e05`
  - Weight: 1
  - Last verified: 2026-05-08, focused matrix-runtime-surface red/green proof
    (exact subpath returned generic passthrough data before implementation,
    then `1 passed`), adjacent Matrix/provider facade proof (`4 passed, 1147
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK matrix-thread-bindings subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/matrix-thread-bindings.ts`,
    `openclaw-main/extensions/matrix/src/matrix/thread-bindings-shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `61ade86a`
  - Weight: 1
  - Last verified: 2026-05-08, focused matrix-thread-bindings red/green
    proof (exact subpath returned generic passthrough data before
    implementation, then `1 passed`), adjacent Matrix/thread-binding proof (`4
    passed, 1148 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK matrix-surface subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/matrix-surface.ts`,
    `openclaw-main/extensions/matrix/src/matrix/thread-bindings.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `20eb2b27`
  - Weight: 1
  - Last verified: 2026-05-08, focused matrix-surface red/green proof (exact
    subpath fell through to generic SDK and produced a missing manager-method
    error before implementation, then `1 passed`), adjacent Matrix facade
    proof (`4 passed, 1149 deselected`), `ruff check`, `mypy`, and `git diff
    --check`.

- [x] Imported plugin SDK volc-model-catalog-shared subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/volc-model-catalog-shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `799fbdd4`
  - Weight: 1
  - Last verified: 2026-05-08, focused volc-model-catalog-shared red/green
    proof (exact subpath returned generic non-array catalog data before
    implementation, then `1 passed`), adjacent provider/model catalog proof
    (`3 passed, 1151 deselected`), `ruff check`, `mypy`, and `git diff
    --check`.

- [x] Imported plugin SDK vercel-ai-gateway subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/vercel-ai-gateway.ts`,
    `openclaw-main/extensions/vercel-ai-gateway/models.ts`,
    `openclaw-main/extensions/vercel-ai-gateway/provider-catalog.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `c298b482`
  - Weight: 1
  - Last verified: 2026-05-08, focused vercel-ai-gateway red/green proof
    (exact subpath returned generic passthrough data and no provider model
    array before implementation, then `1 passed`), adjacent provider catalog
    proof (`4 passed, 1153 deselected`), `ruff check`, `mypy`, and `git diff
    --check`.

- [x] Imported plugin SDK minimax subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/minimax.ts`,
    `openclaw-main/extensions/minimax/provider-models.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `95d0e552`
  - Weight: 1
  - Last verified: 2026-05-08, focused minimax red/green proof (exact subpath
    returned the whole generic SDK surface before implementation, then `1
    passed`), adjacent provider/model proof (`5 passed, 1153 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK openrouter subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/openrouter.ts`,
    `openclaw-main/extensions/openrouter/provider-catalog.ts`,
    `openclaw-main/extensions/openrouter/onboard.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `fad79376`
  - Weight: 1
  - Last verified: 2026-05-08, focused openrouter red/green proof (exact
    subpath returned generic passthrough data and no provider envelope before
    implementation, then `1 passed`), adjacent provider/onboard proof (`5
    passed, 1154 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK litellm subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/litellm.ts`,
    `openclaw-main/extensions/litellm/onboard.ts`,
    `openclaw-main/extensions/litellm/provider-catalog.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `d7c42aed`
  - Weight: 1
  - Last verified: 2026-05-08, focused litellm red/green proof (exact subpath
    returned the generic SDK and passthrough appliers before implementation,
    then `1 passed`), adjacent provider/onboard proof (`5 passed, 1155
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK llm-task subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/llm-task.ts`,
    `openclaw-main/src/auto-reply/thinking.ts`,
    `openclaw-main/src/auto-reply/thinking.shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `1a223530`
  - Weight: 1
  - Last verified: 2026-05-08, focused llm-task red/green proof (exact
    subpath returned generic passthrough thinking helpers before
    implementation, then `1 passed`), adjacent plugin-entry/diffs/provider
    proof (`5 passed, 1156 deselected`), `ruff check`, `mypy`, and `git diff
    --check`.

- [x] Imported plugin SDK test-utils compatibility alias.
  - Source: `openclaw-main/src/plugin-sdk/test-utils.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `992457ac`
  - Weight: 1
  - Last verified: 2026-05-08, focused test-utils compatibility red/green
    proof (exact subpath returned the whole generic SDK surface before
    implementation, then `1 passed`), adjacent testing-barrel proof (`2
    passed, 1153 deselected`), `ruff check`, `mypy`, and `git diff --check`.

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

- [x] Imported plugin SDK speech-core helper shim.
  - Source: `openclaw-main/src/plugin-sdk/speech-core.ts`, adjacent
    `openclaw-main/src/tts/*` helpers, and
    `openclaw-main/src/agents/provider-http-errors.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `ff03eba7`
  - Weight: 1
  - Last verified: 2026-05-06, focused speech-core helper proof (`1
    passed`), adjacent SDK helper proof (`3 passed, 1016 deselected`),
    adjacent imported-plugin proof (`207 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK video-generation-core helper shim.
  - Source: `openclaw-main/src/plugin-sdk/video-generation-core.ts`,
    adjacent `openclaw-main/src/video-generation/*`,
    `openclaw-main/src/media-generation/runtime-shared.ts`,
    `openclaw-main/src/config/model-input.ts`,
    `openclaw-main/src/agents/failover-error.ts`,
    `openclaw-main/src/logging/subsystem.ts`, and
    `openclaw-main/src/secrets/provider-env-vars.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `f85c7465`
  - Weight: 1
  - Last verified: 2026-05-06, focused video-generation-core helper proof
    (`1 passed`), adjacent SDK helper proof (`3 passed, 1017 deselected`),
    adjacent imported-plugin proof (`208 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK image-generation-core helper shim.
  - Source: `openclaw-main/src/plugin-sdk/image-generation-core.ts`,
    adjacent `openclaw-main/src/image-generation/*`,
    `openclaw-main/src/media-generation/runtime-shared.ts`,
    `openclaw-main/src/config/model-input.ts`,
    `openclaw-main/src/agents/failover-error.ts`,
    `openclaw-main/src/infra/gemini-auth.ts`,
    `openclaw-main/src/plugin-sdk/provider-model-shared.ts`,
    `openclaw-main/src/logging/subsystem.ts`, and
    `openclaw-main/src/secrets/provider-env-vars.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `1a128fa5`
  - Weight: 1
  - Last verified: 2026-05-06, focused image-generation-core helper proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1017 deselected`),
    adjacent imported-plugin proof (`209 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK music-generation-core helper shim.
  - Source: `openclaw-main/src/plugin-sdk/music-generation-core.ts`,
    adjacent `openclaw-main/src/music-generation/*`,
    `openclaw-main/src/config/model-input.ts`,
    `openclaw-main/src/agents/failover-error.ts`,
    `openclaw-main/src/logging/subsystem.ts`, and
    `openclaw-main/src/secrets/provider-env-vars.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `a17da4e3`
  - Weight: 1
  - Last verified: 2026-05-06, focused music-generation-core helper proof
    (`1 passed`), adjacent SDK helper proof (`5 passed, 1017 deselected`),
    adjacent imported-plugin proof (`210 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK media-generation-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/media-generation-runtime.ts`,
    `openclaw-main/src/plugin-sdk/media-generation-runtime-shared.ts`, and
    `openclaw-main/src/media-generation/runtime-shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `f475d85a`
  - Weight: 1
  - Last verified: 2026-05-06, focused media-generation-runtime helper proof
    (`1 passed`), adjacent SDK helper proof (`6 passed, 1017 deselected`),
    adjacent imported-plugin proof (`211 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK image-generation-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/image-generation-runtime.ts` and
    `openclaw-main/src/image-generation/runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `719fcee8`
  - Weight: 1
  - Last verified: 2026-05-06, focused image-generation-runtime helper proof
    (`1 passed`), adjacent SDK helper proof (`6 passed, 1018 deselected`),
    adjacent imported-plugin proof (`212 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK video-generation-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/video-generation-runtime.ts`,
    `openclaw-main/src/video-generation/runtime.ts`,
    `openclaw-main/src/video-generation/normalization.ts`,
    `openclaw-main/src/video-generation/capabilities.ts`, and
    `openclaw-main/src/video-generation/duration-support.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `2cf18309`
  - Weight: 1
  - Last verified: 2026-05-06, focused video-generation-runtime helper proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1021 deselected`),
    adjacent imported-plugin proof (`213 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK realtime-transcription helper shim.
  - Source: `openclaw-main/src/plugin-sdk/realtime-transcription.ts`,
    `openclaw-main/src/realtime-transcription/provider-registry.ts`,
    `openclaw-main/src/plugins/provider-registry-shared.ts`, and
    `openclaw-main/src/realtime-transcription/websocket-session.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `18a7e15b`
  - Weight: 1
  - Last verified: 2026-05-06, focused realtime-transcription helper proof
    (`1 passed`), adjacent SDK helper proof (`2 passed, 1024 deselected`),
    adjacent imported-plugin proof (`214 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK realtime-voice helper shim.
  - Source: `openclaw-main/src/plugin-sdk/realtime-voice.ts`,
    `openclaw-main/src/realtime-voice/provider-types.ts`,
    `openclaw-main/src/realtime-voice/provider-registry.ts`,
    `openclaw-main/src/realtime-voice/provider-resolver.ts`,
    `openclaw-main/src/realtime-voice/agent-consult-tool.ts`,
    `openclaw-main/src/realtime-voice/agent-consult-runtime.ts`,
    `openclaw-main/src/realtime-voice/session-runtime.ts`, and
    `openclaw-main/src/realtime-voice/audio-codec.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `0f6e62d7`
  - Weight: 1
  - Last verified: 2026-05-07, focused realtime-voice helper proof
    (`1 passed`), adjacent SDK helper proof (`3 passed, 1024 deselected`),
    adjacent imported-plugin proof (`215 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK media-understanding-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/media-understanding-runtime.ts`,
    `openclaw-main/src/media-understanding/runtime.ts`,
    `openclaw-main/src/media-understanding/runtime-types.ts`,
    `openclaw-main/src/media-understanding/runner.ts`,
    `openclaw-main/src/media-understanding/runner.entries.ts`,
    `openclaw-main/src/media-understanding/runner.attachments.ts`,
    `openclaw-main/src/media-understanding/attachments.normalize.ts`,
    `openclaw-main/src/media-understanding/attachments.select.ts`,
    `openclaw-main/src/media-understanding/attachments.cache.ts`,
    `openclaw-main/src/media-understanding/provider-registry.ts`, and
    `openclaw-main/src/media-understanding/resolve.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `65d2ce12`
  - Weight: 1
  - Last verified: 2026-05-07, focused media-understanding-runtime helper
    proof (`1 passed`), adjacent SDK helper proof (`4 passed, 1024
    deselected`), adjacent imported-plugin proof (`216 passed, 812
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK media-understanding provider-helper shim.
  - Source: `openclaw-main/src/plugin-sdk/media-understanding.ts`,
    `openclaw-main/src/media-understanding/openai-compatible-video.ts`,
    `openclaw-main/src/media-understanding/openai-compatible-audio.ts`, and
    `openclaw-main/src/media-understanding/shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `4a383013`
  - Weight: 1
  - Last verified: 2026-05-07, focused media-understanding helper proof
    (`1 passed`), adjacent SDK helper proof (`3 passed, 1026 deselected`),
    adjacent imported-plugin proof (`217 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK messaging-targets helper shim.
  - Source: `openclaw-main/src/plugin-sdk/messaging-targets.ts` and
    `openclaw-main/src/channels/targets.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `cd85f7f5`
  - Weight: 1
  - Last verified: 2026-05-07, focused messaging-targets helper proof (`1
    passed`), adjacent SDK helper proof (`3 passed, 1027 deselected`),
    adjacent imported-plugin proof (`218 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK request-url helper shim.
  - Source: `openclaw-main/src/plugin-sdk/request-url.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: verified; source/test behavior checkpointed in `f4a23a25`
  - Weight: 1
  - Last verified: 2026-05-07, focused request-url/fetch-SSRF proof (`1
    passed`), adjacent SDK helper proof (`2 passed, 1028 deselected`),
    adjacent imported-plugin proof (`218 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] Imported plugin SDK persistent-dedupe helper shim.
  - Source: `openclaw-main/src/plugin-sdk/persistent-dedupe.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `cfe26bca`
  - Weight: 1
  - Last verified: 2026-05-07, focused persistent-dedupe proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1027 deselected`), adjacent
    imported-plugin proof (`219 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK qa-runner-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/qa-runner-runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `f9d46a8f`
  - Weight: 1
  - Last verified: 2026-05-07, focused qa-runner-runtime proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1029 deselected`), adjacent
    imported-plugin proof (`220 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK models-provider-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/models-provider-runtime.ts`,
    `openclaw-main/src/auto-reply/reply/commands-models.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `695de78b`
  - Weight: 1
  - Last verified: 2026-05-07, focused models-provider-runtime proof (`1
    passed`), adjacent SDK helper proof (`6 passed, 1027 deselected`),
    adjacent imported-plugin proof (`221 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK skill-commands-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/skill-commands-runtime.ts`,
    `openclaw-main/src/auto-reply/skill-commands.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `14864460`
  - Weight: 1
  - Last verified: 2026-05-07, focused skill-commands-runtime proof (`1
    passed`), adjacent SDK helper proof (`5 passed, 1029 deselected`),
    adjacent imported-plugin proof (`222 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK skills-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/skills-runtime.ts`,
    `openclaw-main/src/agents/skills/refresh-state.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `106ddcb8`
  - Weight: 1
  - Last verified: 2026-05-07, focused skills-runtime proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1032 deselected`), adjacent
    imported-plugin proof (`223 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime core helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/agent-scope.ts`,
    `openclaw-main/src/agents/agent-paths.ts`,
    `openclaw-main/src/agents/current-time.ts`,
    `openclaw-main/src/agents/date-time.ts`,
    `openclaw-main/src/agents/defaults.ts`,
    `openclaw-main/src/agents/identity.ts`,
    `openclaw-main/src/agents/provider-id.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `a8e871a3`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime core proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1033 deselected`), adjacent
    imported-plugin proof (`224 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime model-selection helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/model-selection.ts`,
    `openclaw-main/src/agents/model-selection-normalize.ts`,
    `openclaw-main/src/agents/model-selection-shared.ts`,
    `openclaw-main/src/agents/model-selection-resolve.ts`,
    `openclaw-main/src/agents/model-ref-shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `0d009e7d`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime model-selection proof
    (`1 passed`), adjacent SDK helper proof (`3 passed, 1034 deselected`),
    adjacent imported-plugin proof (`225 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime tool bridge helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/tools/common.ts`,
    `openclaw-main/src/tools/index.ts`,
    `openclaw-main/src/tools/availability.ts`,
    `openclaw-main/src/tools/descriptors.ts`,
    `openclaw-main/src/tools/diagnostics.ts`,
    `openclaw-main/src/tools/execution.ts`,
    `openclaw-main/src/tools/planner.ts`,
    `openclaw-main/src/tools/protocol.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `01653787`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime tool bridge proof (`1
    passed`), adjacent SDK helper proof (`3 passed, 1035 deselected`),
    adjacent imported-plugin proof (`226 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime facade utility helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/model-auth-markers.ts`,
    `openclaw-main/src/agents/sandbox-paths.ts`,
    `openclaw-main/src/agents/identity-avatar.ts`,
    `openclaw-main/src/agents/simple-completion-runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `a6d70a6f`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime facade utility proof (`1
    passed`), adjacent SDK helper proof (`4 passed, 1035 deselected`),
    adjacent imported-plugin proof (`227 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime model-catalog lookup helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/model-catalog.ts`,
    `openclaw-main/src/agents/model-catalog-lookup.ts`,
    `openclaw-main/src/agents/model-catalog.types.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `a5794303`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime model-catalog proof (`1
    passed`), adjacent SDK helper proof (`5 passed, 1035 deselected`),
    adjacent imported-plugin proof (`228 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime PI embedded utility helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/pi-embedded-utils.ts`,
    `openclaw-main/src/shared/text/assistant-visible-text.ts`,
    `openclaw-main/src/shared/text/reasoning-tags.ts`,
    `openclaw-main/src/shared/chat-message-content.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `db2affa5`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime PI utility proof (`1
    passed`), adjacent SDK helper proof (`7 passed, 1034 deselected`),
    adjacent imported-plugin proof (`229 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime embedded block chunker shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/pi-embedded-block-chunker.ts`,
    `openclaw-main/src/markdown/fences.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `da591809`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime block chunker proof (`1
    passed`), adjacent SDK helper proof (`8 passed, 1034 deselected`),
    adjacent imported-plugin proof (`230 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime model-auth helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/model-auth.ts`,
    `openclaw-main/src/agents/model-auth-env.ts`,
    `openclaw-main/src/agents/model-auth-runtime-shared.ts`,
    `openclaw-main/src/agents/auth-profiles.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `b93c187b`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime model-auth proof (`1
    passed`), adjacent SDK helper proof (`9 passed, 1034 deselected`),
    adjacent imported-plugin proof (`231 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime schema/typebox helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/schema/typebox.ts`,
    `openclaw-main/src/agents/schema/string-enum.ts`,
    `openclaw-main/src/infra/outbound/channel-target.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `0884d4f3`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime schema/typebox proof (`1
    passed`), adjacent SDK helper proof (`10 passed, 1034 deselected`),
    adjacent imported-plugin proof (`232 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime web-tool helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/tools/web-shared.ts`,
    `openclaw-main/src/agents/tools/web-fetch-utils.ts`,
    `openclaw-main/src/agents/tools/web-guarded-fetch.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `9bc67f5e`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime web-tool proof (`1
    passed`), adjacent SDK helper proof (`11 passed, 1034 deselected`),
    adjacent imported-plugin proof (`233 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime provider-auth alias helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/provider-auth-aliases.ts`,
    `openclaw-main/src/plugins/plugin-config-trust.ts`,
    `openclaw-main/src/plugins/plugin-control-plane-context.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `61731b33`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime provider-auth alias proof
    (`1 passed`), adjacent SDK helper proof (`12 passed, 1034 deselected`),
    adjacent imported-plugin proof (`234 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime TTS helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/tts/tts.ts`,
    `openclaw-main/src/plugin-sdk/tts-runtime.ts`,
    `openclaw-main/extensions/speech-core/src/tts.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `9b328bbd`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime TTS proof (`1 passed`),
    adjacent SDK helper proof (`13 passed, 1034 deselected`), adjacent
    imported-plugin proof (`235 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-runtime command entrypoint shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/agent-command.ts`,
    `openclaw-main/src/agents/agent-runtime-config.ts`,
    `openclaw-main/src/agents/command/types.ts`,
    `openclaw-main/src/commands/agent.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `9e6496fb`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime command entrypoint proof
    (`1 passed`), adjacent SDK helper proof (`14 passed, 1034 deselected`),
    adjacent imported-plugin proof (`236 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK file-lock helper shim.
  - Source: `openclaw-main/src/plugin-sdk/file-lock.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `ed03c127`
  - Weight: 1
  - Last verified: 2026-05-07, focused file-lock proof (`1 passed`),
    adjacent SDK helper proof (`15 passed, 1034 deselected`), adjacent
    imported-plugin proof (`237 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK google-model-id alias shim.
  - Source: `openclaw-main/src/plugin-sdk/google-model-id.ts`,
    `openclaw-main/src/plugin-sdk/provider-model-shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `67db67b5`
  - Weight: 1
  - Last verified: 2026-05-07, focused google-model-id proof (`1 passed`),
    adjacent SDK helper proof (`16 passed, 1034 deselected`), adjacent
    imported-plugin proof (`238 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK googlechat-runtime-shared schema shim.
  - Source: `openclaw-main/src/plugin-sdk/googlechat-runtime-shared.ts`,
    `openclaw-main/src/config/zod-schema.providers-core.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `f721b7e3`
  - Weight: 1
  - Last verified: 2026-05-07, focused googlechat-runtime-shared proof (`1
    passed`), adjacent SDK helper proof (`17 passed, 1034 deselected`),
    adjacent imported-plugin proof (`239 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK open-prose exact plugin-entry shim.
  - Source: `openclaw-main/src/plugin-sdk/open-prose.ts`,
    `openclaw-main/src/plugin-sdk/plugin-entry.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `ef8830b1`
  - Weight: 1
  - Last verified: 2026-05-07, focused open-prose proof (`1 passed`),
    adjacent SDK helper proof (`18 passed, 1034 deselected`), adjacent
    imported-plugin proof (`240 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK runtime-group-policy helper shim.
  - Source: `openclaw-main/src/plugin-sdk/runtime-group-policy.ts`,
    `openclaw-main/src/config/runtime-group-policy.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `b11adc13`
  - Weight: 1
  - Last verified: 2026-05-07, focused runtime-group-policy proof (`1
    passed`), adjacent SDK helper proof (`20 passed, 1033 deselected`),
    adjacent imported-plugin proof (`241 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-cdp helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-cdp.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `4e15c3c2`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-cdp proof (`1 passed`),
    adjacent SDK helper proof (`22 passed, 1032 deselected`), adjacent
    imported-plugin proof (`242 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-config-support helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-config-support.ts`,
    `openclaw-main/src/config/paths.ts`,
    `openclaw-main/extensions/browser/src/sdk-config.ts`,
    `openclaw-main/src/gateway/net.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `33463b7c`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-config-support proof (`1
    passed`), adjacent SDK helper proof (`23 passed, 1032 deselected`),
    adjacent imported-plugin proof (`243 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-config facade shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-config.ts`,
    `openclaw-main/src/plugin-sdk/browser-profiles.ts`,
    `openclaw-main/src/plugin-sdk/browser-cdp.ts`,
    `openclaw-main/src/plugin-sdk/browser-control-auth.ts`,
    `openclaw-main/src/plugin-sdk/browser-trash.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `300224b7`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-config facade proof (`1
    passed`), adjacent SDK helper proof (`24 passed, 1032 deselected`),
    adjacent imported-plugin proof (`244 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-control-auth helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-control-auth.ts`,
    `openclaw-main/extensions/browser/src/browser/control-auth.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `d1d7b371`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-control-auth proof (`1
    passed`), focused entrypoints proof (`1 passed`), adjacent SDK helper
    proof (`26 passed, 1031 deselected`), adjacent imported-plugin proof (`245
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-profiles helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-profiles.ts`,
    `openclaw-main/extensions/browser/browser-profiles.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `73d20703`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-profiles proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`27
    passed, 1031 deselected`), adjacent imported-plugin proof (`246 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-config-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-config-runtime.ts`,
    `openclaw-main/src/config/config.ts`,
    `openclaw-main/src/config/paths.ts`,
    `openclaw-main/src/plugins/config-state.ts`,
    `openclaw-main/src/utils/boolean.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `7a4ef6f0`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-config-runtime proof (`1
    passed`), focused entrypoints proof (`1 passed`), adjacent SDK helper
    proof (`28 passed, 1031 deselected`), adjacent imported-plugin proof (`247
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-trash helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-trash.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `9a90555e`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-trash proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`29
    passed, 1031 deselected`), adjacent imported-plugin proof (`248 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-maintenance helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-maintenance.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `ce39d8c6`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-maintenance proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`30
    passed, 1031 deselected`), adjacent imported-plugin proof (`249 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-host-inspection helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-host-inspection.ts`,
    `openclaw-main/extensions/browser/src/browser/chrome.executables.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `bf5ce3f0`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-host-inspection proof (`1
    passed`), focused entrypoints proof (`1 passed`), adjacent SDK helper proof
    (`31 passed, 1031 deselected`), adjacent imported-plugin proof (`250
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-node-host helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-node-host.ts`,
    `openclaw-main/extensions/browser/src/node-host/invoke-browser.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `2ef00b04`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-node-host proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`32
    passed, 1031 deselected`), adjacent imported-plugin proof (`251 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-node-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-node-runtime.ts`,
    `openclaw-main/extensions/browser/src/sdk-node-runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `bc7ef301`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-node-runtime proof (`1
    passed`), focused entrypoints proof (`1 passed`), adjacent SDK helper proof
    (`33 passed, 1031 deselected`), adjacent imported-plugin proof (`252
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-setup-tools helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-setup-tools.ts`,
    `openclaw-main/extensions/browser/src/sdk-setup-tools.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `50876922`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-setup-tools proof (`1
    passed`), focused entrypoints proof (`1 passed`), adjacent SDK helper proof
    (`34 passed, 1031 deselected`), adjacent imported-plugin proof (`253
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-support helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-support.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `37eec77e`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-support proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`35
    passed, 1031 deselected`), adjacent imported-plugin proof (`254 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK browser-bridge helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-bridge.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `f0635cce`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-bridge proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`36
    passed, 1031 deselected`), adjacent imported-plugin proof (`255 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK agent-harness-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/agent-harness-runtime.ts`,
    `openclaw-main/src/plugin-sdk/agent-harness.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `ee7f5c49`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-harness-runtime proof (`1
    passed`), adjacent SDK helper proof (`6 passed, 1062 deselected`),
    adjacent imported-plugin proof (`256 passed, 812 deselected`), `ruff
    check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK sandbox helper shim.
  - Source: `openclaw-main/src/plugin-sdk/sandbox.ts`,
    `openclaw-main/src/agents/sandbox.ts`,
    `openclaw-main/src/agents/sandbox/ssh.ts`,
    `openclaw-main/src/agents/sandbox/sanitize-env-vars.ts`,
    `openclaw-main/src/agents/sandbox/backend.ts`, and
    `openclaw-main/src/agents/sandbox/fs-bridge-rename-targets.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `2aba5dbc`
  - Weight: 1
  - Last verified: 2026-05-07, focused sandbox proof (`1 passed`), adjacent
    SDK helper proof (`7 passed, 1062 deselected`), adjacent imported-plugin
    proof (`257 passed, 812 deselected`), `ruff check`, `mypy`, and `git diff
    --check`.

- [x] Imported plugin SDK proxy-capture helper shim.
  - Source: `openclaw-main/src/plugin-sdk/proxy-capture.ts`,
    `openclaw-main/src/proxy-capture/env.ts`,
    `openclaw-main/src/proxy-capture/store.sqlite.ts`,
    `openclaw-main/src/proxy-capture/runtime.ts`,
    `openclaw-main/src/proxy-capture/blob-store.ts`, and
    `openclaw-main/src/proxy-capture/paths.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `84300681`
  - Weight: 1
  - Last verified: 2026-05-07, focused proxy-capture proof (`1 passed`),
    adjacent SDK helper proof (`6 passed, 1064 deselected`), adjacent
    imported-plugin proof (`258 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK setup-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/setup-runtime.ts`,
    `openclaw-main/src/channels/plugins/setup-helpers.ts`,
    `openclaw-main/src/channels/plugins/setup-wizard-helpers.ts`,
    `openclaw-main/src/channels/plugins/setup-wizard-binary.ts`, and
    `openclaw-main/src/channels/plugins/setup-wizard-proxy.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `252f28fe`
  - Weight: 1
  - Last verified: 2026-05-07, focused setup-runtime proof (`1 passed`),
    adjacent SDK helper proof (`6 passed, 1065 deselected`), adjacent
    imported-plugin proof (`259 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK setup-tools helper shim.
  - Source: `openclaw-main/src/plugin-sdk/setup-tools.ts`,
    `openclaw-main/src/cli/command-format.ts`,
    `openclaw-main/src/infra/archive.ts`,
    `openclaw-main/src/infra/brew.ts`,
    `openclaw-main/src/infra/detect-binary.ts`,
    `openclaw-main/src/terminal/links.ts`, and
    `openclaw-main/src/utils.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `e0f1e72c`
  - Weight: 1
  - Last verified: 2026-05-07, focused setup-tools proof (`1 passed`),
    adjacent SDK helper proof (`8 passed, 1064 deselected`), adjacent
    imported-plugin proof (`260 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK config-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/config-runtime.ts`,
    `openclaw-main/src/plugin-sdk/plugin-config-runtime.ts`,
    `openclaw-main/src/config/io.ts`,
    `openclaw-main/src/config/mutate.ts`,
    `openclaw-main/src/config/logging.ts`,
    `openclaw-main/src/config/sessions/store.ts`,
    `openclaw-main/src/config/sessions/reset.ts`, and adjacent config policy
    helpers re-exported by the upstream barrel
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `74fd1711`
  - Weight: 1
  - Last verified: 2026-05-07, focused config-runtime proof (`1 passed`),
    adjacent SDK helper proof (`7 passed, 1066 deselected`), adjacent
    imported-plugin proof (`261 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK plugin-config-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/plugin-config-runtime.ts`,
    `openclaw-main/src/plugins/config-state.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `458d6c7f`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-config-runtime proof (`1
    passed`), adjacent SDK helper proof (`8 passed, 1066 deselected`),
    adjacent imported-plugin proof (`262 passed, 812 deselected`), `ruff
    check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK config-mutation helper shim.
  - Source: `openclaw-main/src/plugin-sdk/config-mutation.ts`,
    `openclaw-main/src/config/mutate.ts`,
    `openclaw-main/src/config/io.ts`,
    `openclaw-main/src/config/logging.ts`, and
    `openclaw-main/src/commands/models/shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `a9813667`
  - Weight: 1
  - Last verified: 2026-05-07, focused config-mutation proof (`1 passed`),
    adjacent SDK helper proof (`9 passed, 1066 deselected`), adjacent
    imported-plugin proof (`263 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK provider-tools helper shim.
  - Source: `openclaw-main/src/plugin-sdk/provider-tools.ts`,
    `openclaw-main/src/agents/schema/clean-for-gemini.ts`, and
    `openclaw-main/src/plugins/provider-model-compat.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `2762ee46`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-tools proof (`1 passed`),
    adjacent SDK helper proof (`7 passed, 1069 deselected`), adjacent
    imported-plugin proof (`264 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK provider-stream-shared helper shim.
  - Source: `openclaw-main/src/plugin-sdk/provider-stream-shared.ts`,
    `openclaw-main/src/agents/pi-embedded-runner/stream-payload-utils.ts`,
    `openclaw-main/src/agents/pi-embedded-runner/zai-stream-wrappers.ts`,
    `openclaw-main/src/agents/pi-embedded-runner/moonshot-thinking-stream-wrappers.ts`,
    and `openclaw-main/src/shared/message-content-blocks.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `711865e0`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-stream-shared proof (`1
    passed`), adjacent SDK helper proof (`8 passed, 1069 deselected`),
    adjacent imported-plugin proof (`265 passed, 812 deselected`), `ruff
    check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK provider-stream helper shim.
  - Source: `openclaw-main/src/plugin-sdk/provider-stream.ts` and
    `openclaw-main/src/plugin-sdk/provider-stream-family.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `da9a3e66`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-stream proof (`1 passed`),
    adjacent SDK helper proof (`5 passed, 1073 deselected`), adjacent
    imported-plugin proof (`266 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK provider-transport-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/provider-transport-runtime.ts`,
    `openclaw-main/src/agents/transport-stream-shared.ts`,
    `openclaw-main/src/agents/transport-message-transform.ts`,
    `openclaw-main/src/agents/system-prompt-cache-boundary.ts`, and
    `openclaw-main/src/agents/openai-transport-stream.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `dd8bcfd8`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-transport-runtime proof (`1
    passed`), adjacent SDK helper proof (`4 passed, 1075 deselected`),
    adjacent imported-plugin proof (`267 passed, 812 deselected`), `ruff
    check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK provider-http helper shim.
  - Source: `openclaw-main/src/plugin-sdk/provider-http.ts`,
    `openclaw-main/src/agents/provider-http-errors.ts`,
    `openclaw-main/src/media-understanding/shared.ts`,
    `openclaw-main/src/agents/provider-attribution.ts`, and
    `openclaw-main/src/agents/provider-request-config.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `750bbf71`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-http proof (`1 passed`),
    adjacent SDK helper proof (`5 passed, 1075 deselected`), adjacent
    imported-plugin proof (`268 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK provider-catalog-runtime helper shim.
  - Source: `openclaw-main/src/plugin-sdk/provider-catalog-runtime.ts`,
    `openclaw-main/src/plugins/provider-runtime.ts`,
    `openclaw-main/src/plugins/providers.ts`, and
    `openclaw-main/src/plugins/providers.runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `2ede5f0d`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-catalog-runtime proof (`1
    passed`), adjacent SDK helper proof (`5 passed, 1076 deselected`),
    adjacent imported-plugin proof (`269 passed, 812 deselected`), `ruff
    check`, `mypy`, and `git diff --check`.

- [x] Imported plugin SDK provider-onboard helper shim.
  - Source: `openclaw-main/src/plugin-sdk/provider-onboard.ts`,
    `openclaw-main/src/agents/model-allowlist-entry.ts`,
    `openclaw-main/src/agents/model-ref-shared.ts`, and
    `openclaw-main/src/config/model-input.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `2c994a4c`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-onboard proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1078 deselected`), adjacent
    imported-plugin proof (`270 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Imported plugin SDK provider-usage helper shim.
  - Source: `openclaw-main/src/plugin-sdk/provider-usage.ts`,
    `openclaw-main/src/infra/provider-usage.fetch.ts`,
    `openclaw-main/src/infra/provider-usage.fetch.shared.ts`,
    `openclaw-main/src/infra/provider-usage.shared.ts`, and provider-specific
    usage fetch helpers under `openclaw-main/src/infra/`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Test: `tests/test_gateway_node_methods.py`
  - Status: checkpointed in `cbc85bd2`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-usage proof (`1 passed`),
    adjacent SDK helper proof (`5 passed, 1078 deselected`), adjacent
    imported-plugin proof (`271 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

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

- [x] Package dist inventory drift diagnostics.
  - Source: `openclaw-main/src/infra/package-dist-inventory.ts`,
    `openclaw-main/src/infra/package-dist-inventory.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `69b23cb9`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_doctor_json_warns_on_package_dist_inventory_file_drift
    -q` (`1 failed` before implementation, then `1 passed`), adjacent package
    doctor proof (`4 passed, 530 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Package dist legacy staging-debris diagnostics.
  - Source: `openclaw-main/src/infra/package-dist-inventory.ts`,
    `openclaw-main/src/infra/package-dist-inventory.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `b16db705`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_doctor_json_warns_on_package_dist_legacy_staging_debris
    -q` (`1 failed` before implementation, then `1 passed`), adjacent package
    doctor proof (`5 passed, 530 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Mixed-case package dist staging-debris proof.
  - Source: `openclaw-main/src/infra/package-dist-inventory.ts`,
    `openclaw-main/src/infra/package-dist-inventory.test.ts`
  - Target: `tests/test_cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `9422c6b7`.
  - Weight: 1
  - Last verified: 2026-05-08, focused `python -m pytest
    tests\test_cli.py::test_doctor_json_detects_mixed_case_package_dist_staging_debris
    -q` (`1 passed`), adjacent package doctor proof (`6 passed, 530
    deselected`), `ruff check`, and `git diff --check`.

- [x] Exact missing package dist inventory warning.
  - Source: `openclaw-main/src/infra/package-dist-inventory.ts`,
    `openclaw-main/src/infra/package-dist-inventory.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `76cdb404`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_doctor_json_warns_on_missing_package_dist_inventory_with_openclaw_message
    -q` (`1 failed` before implementation, then `1 passed`), adjacent package
    doctor proof (`7 passed, 530 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Package dist local metadata/dependency omission.
  - Source: `openclaw-main/src/infra/package-dist-inventory.ts`,
    `openclaw-main/src/infra/package-dist-inventory.test.ts`,
    `openclaw-main/scripts/lib/local-build-metadata-paths.mjs`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `6e8bb491`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_doctor_json_omits_local_build_metadata_and_plugin_dependency_debris
    -q` (`1 failed` before implementation, then `1 passed`), adjacent package
    doctor proof (`8 passed, 530 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Unsafe package dist symlink diagnostics.
  - Source: `openclaw-main/src/infra/package-dist-inventory.ts`,
    `openclaw-main/src/infra/package-dist-inventory.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `a9c7884f`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_doctor_json_warns_on_unsafe_package_dist_symlink
    -q` (`1 failed` before implementation, then `1 passed`), adjacent package
    doctor proof (`9 passed, 530 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Externalized bundled extension dist omission.
  - Source: `openclaw-main/src/infra/package-dist-inventory.ts`,
    `openclaw-main/src/infra/package-dist-inventory.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `06ba5480`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_doctor_json_omits_externalized_bundled_extension_dist_trees
    -q` (`1 failed` before implementation, then `1 passed`), adjacent package
    doctor proof (`10 passed, 530 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Private QA package dist artifact omission.
  - Source: `openclaw-main/src/infra/package-dist-inventory.ts`,
    `openclaw-main/src/infra/package-dist-inventory.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `bde731a9`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_doctor_json_omits_private_qa_package_dist_artifacts
    -q` (`1 failed` before implementation, then `1 passed`), adjacent package
    doctor proof (`11 passed, 530 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Package root resolves to source checkout warning.
  - Source: `openclaw-main/src/infra/update-global.ts`,
    `openclaw-main/src/infra/update-global.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `912aee5e`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_doctor_json_flags_package_root_resolving_to_source_checkout
    -q` (`1 failed` before implementation, then `1 passed`), adjacent package
    doctor proof (`12 passed, 530 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Bundled runtime sidecar enforcement.
  - Source: `openclaw-main/src/infra/update-global.ts`,
    `openclaw-main/src/infra/update-global.test.ts`,
    `openclaw-main/scripts/lib/bundled-runtime-sidecar-paths.json`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `07b17ad0`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_doctor_json_enforces_missing_bundled_runtime_sidecar
    -q` (`1 failed` before implementation, then `1 passed`), adjacent package
    doctor proof (`13 passed, 530 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Private QA bundled sidecar no-warning proof.
  - Source: `openclaw-main/src/infra/update-global.ts`,
    `openclaw-main/src/infra/update-global.test.ts`,
    `openclaw-main/scripts/lib/bundled-runtime-sidecar-paths.json`
  - Target: `tests/test_cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `ad248bf4`.
  - Weight: 1
  - Last verified: 2026-05-08, focused `python -m pytest
    tests\test_cli.py::test_doctor_json_ignores_private_qa_bundled_runtime_sidecars
    -q` (`1 passed`), adjacent sidecar/QA proof (`3 passed, 541
    deselected`), `ruff check`, and `git diff --check`.

- [x] Update dry-run preview package-spec mapping.
  - Source: `openclaw-main/src/cli/update-cli/update-command.ts`,
    `openclaw-main/src/infra/update-global.ts`,
    `openclaw-main/src/infra/update-global.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `08e8f76f`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_update_dry_run_json_maps_main_package_install_spec
    -q` (`1 failed` before implementation, then `1 passed`), adjacent update
    proof (`13 passed, 532 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Update-status timeout option.
  - Source: `openclaw-main/src/cli/update-cli.ts`,
    `openclaw-main/src/cli/update-cli/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `6418d7f3`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_update_status_timeout_option_reaches_live_probe
    -q` (`1 failed` before implementation, then `1 passed`), adjacent update
    proof (`14 passed, 532 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Update package-spec env override.
  - Source: `openclaw-main/src/cli/update-cli/update-command.ts`,
    `openclaw-main/src/infra/update-global.ts`,
    `openclaw-main/src/infra/update-global.test.ts`
  - Target: `tests/test_cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `949de445`.
  - Weight: 1
  - Last verified: 2026-05-08, focused `python -m pytest
    tests\test_cli.py::test_update_dry_run_json_honors_openclaw_package_spec_override
    -q` (`1 passed`), adjacent update proof (`15 passed, 532 deselected`),
    `ruff check`, and `git diff --check`.

- [x] Explicit update install-spec preservation.
  - Source: `openclaw-main/src/cli/update-cli/update-command.ts`,
    `openclaw-main/src/infra/update-global.ts`,
    `openclaw-main/src/infra/update-global.test.ts`
  - Target: `tests/test_cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `3227786a`.
  - Weight: 1
  - Last verified: 2026-05-08, focused `python -m pytest
    tests\test_cli.py::test_update_dry_run_json_preserves_explicit_package_install_spec
    -q` (`1 passed`), adjacent update proof (`16 passed, 532 deselected`),
    `ruff check`, and `git diff --check`.

- [x] Root update runtime dispatch.
  - Source: `openclaw-main/src/cli/update-cli.ts`,
    `openclaw-main/src/cli/update-cli/update-command.ts`,
    `openclaw-main/src/infra/update-runner.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `0c88812c`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_update_json_dispatches_runtime_update_service
    -q` (`1 failed` before implementation, then `1 passed`), adjacent update
    proof (`17 passed, 532 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Inherited update-status parent options.
  - Source: `openclaw-main/src/cli/update-cli.ts`,
    `openclaw-main/src/cli/update-cli.option-collisions.test.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `f088293f`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_update_status_inherits_parent_json_and_timeout_options
    -q` (`1 failed` before implementation, then `1 passed`), adjacent update
    proof (`18 passed, 532 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] Package update runtime path.
  - Source: `openclaw-main/src/infra/package-update-steps.ts`,
    `openclaw-main/src/infra/update-global.ts`,
    `openclaw-main/src/cli/update-cli/update-command.ts`
  - Target: `src/openzues/services/runtime_updates.py`, `src/openzues/cli.py`
  - Test: `tests/test_runtime_updates.py`, `tests/test_cli.py`
  - Status: checkpointed in `1291d361`.
  - Weight: 2
  - Last verified: 2026-05-08, focused service/CLI proof (`2 passed`),
    adjacent runtime/update proof (`20 passed, 536 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] Npm update omit-optional fallback.
  - Source: `openclaw-main/src/infra/package-update-steps.ts`,
    `openclaw-main/src/infra/update-global.ts`
  - Target: `src/openzues/services/runtime_updates.py`
  - Test: `tests/test_runtime_updates.py`
  - Status: checkpointed in `f3177330`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green package fallback proof,
    adjacent package-update proof (`2 passed, 4 deselected`), full runtime
    update suite (`6 passed`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Package update version verification.
  - Source: `openclaw-main/src/infra/package-update-steps.ts`,
    `openclaw-main/src/infra/update-global.ts`
  - Target: `src/openzues/services/runtime_updates.py`
  - Test: `tests/test_runtime_updates.py`
  - Status: checkpointed in `1db09c3b`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green package verify proof,
    adjacent package-update proof (`3 passed, 4 deselected`), full runtime
    update suite (`7 passed`), `ruff check`, `mypy`, and `git diff --check`.

- [x] Package update failedStep projection.
  - Source: `openclaw-main/src/infra/package-update-steps.ts`,
    `openclaw-main/src/infra/update-runner.ts`
  - Target: `src/openzues/services/runtime_updates.py`
  - Test: `tests/test_runtime_updates.py`
  - Status: checkpointed in `98e4d5c9`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green failedStep proof, full
    runtime update suite (`7 passed`), `ruff check`, `mypy`, and
    `git diff --check`.

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

- [x] Companion QR human approval instructions.
  - Source: `openclaw-main/src/cli/qr-cli.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `d6052fda`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green `python -m pytest
    tests\test_cli.py::test_qr_human_output_includes_openclaw_approval_instructions
    -q` (`1 failed` before implementation, then `1 passed`), adjacent QR
    proof (`5 passed, 528 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

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

- [x] Google Chat route-backed account probe.
  - Source: `openclaw-main/extensions/googlechat/src/api.ts`,
    `openclaw-main/extensions/googlechat/src/channel.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `816d97c4`.
  - Weight: 1
  - Last verified: 2026-05-07, focused
    `python -m pytest tests\test_cli.py::test_channels_status_json_uses_route_backed_googlechat_probe -q`
    (`1 passed`), adjacent channel-probe proof (`9 passed, 506 deselected`),
    `ruff check`, and `mypy`.

- [x] Feishu/Lark route-backed account probe.
  - Source: `openclaw-main/extensions/feishu/src/probe.ts`,
    `openclaw-main/extensions/feishu/src/channel.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `bf1d1d3c`.
  - Weight: 1
  - Last verified: 2026-05-08, focused
    `python -m pytest tests\test_cli.py::test_channels_status_json_uses_route_backed_feishu_probe -q`
    (`1 passed`), adjacent channel-probe proof (`10 passed, 506 deselected`),
    `ruff check`, and `mypy`.

- [x] Mattermost route-backed account probe.
  - Source: `openclaw-main/extensions/mattermost/src/mattermost/probe.ts`,
    `openclaw-main/extensions/mattermost/src/channel.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `ba0205fc`.
  - Weight: 1
  - Last verified: 2026-05-08, focused
    `python -m pytest tests\test_cli.py::test_channels_status_json_uses_route_backed_mattermost_probe -q`
    (`1 passed`), adjacent channel-probe proof (`11 passed, 506 deselected`),
    `ruff check`, and `mypy`.

- [x] Signal route-backed account probe.
  - Source: `openclaw-main/extensions/signal/src/probe.ts`,
    `openclaw-main/extensions/signal/src/channel.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `1af31a04`.
  - Weight: 1
  - Last verified: 2026-05-08, focused
    `python -m pytest tests\test_cli.py::test_channels_status_json_uses_route_backed_signal_probe -q`
    (`1 passed`), adjacent channel-probe proof (`12 passed, 506 deselected`),
    `ruff check`, and `mypy`.

- [x] IRC route-backed account probe.
  - Source: `openclaw-main/extensions/irc/src/probe.ts`,
    `openclaw-main/extensions/irc/src/channel.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_cli.py`, `tests/test_ops_mesh.py`
  - Status: checkpointed in `fd5d246b`.
  - Weight: 1
  - Last verified: 2026-05-08, focused
    `python -m pytest tests\test_cli.py::test_channels_status_json_uses_route_backed_irc_probe tests\test_ops_mesh.py::test_ops_mesh_service_irc_probe_waits_for_ready_and_quits -q`
    (`2 passed`), adjacent channel-probe proof (`13 passed, 506 deselected`),
    adjacent IRC ops proof (`2 passed, 375 deselected`), `ruff check`, and
    `mypy`.

- [x] Twitch route-backed account probe.
  - Source: `openclaw-main/extensions/twitch/src/probe.ts`,
    `openclaw-main/extensions/twitch/src/plugin.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_cli.py`, `tests/test_ops_mesh.py`
  - Status: checkpointed in `5772e6a9`.
  - Weight: 1
  - Last verified: 2026-05-08, focused
    `python -m pytest tests\test_cli.py::test_channels_status_json_uses_route_backed_twitch_probe tests\test_ops_mesh.py::test_ops_mesh_service_twitch_probe_waits_for_ready_and_quits -q`
    (`2 passed`), adjacent channel-probe proof (`14 passed, 506 deselected`),
    adjacent Twitch ops proof (`3 passed, 375 deselected`), `ruff check`, and
    `mypy`.

- [x] BlueBubbles route-backed account probe.
  - Source: `openclaw-main/extensions/bluebubbles/src/probe.ts`,
    `openclaw-main/extensions/bluebubbles/src/channel.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_cli.py`, `tests/test_ops_mesh.py`
  - Status: checkpointed in `7c9ffdcb`.
  - Weight: 1
  - Last verified: 2026-05-08, focused
    `python -m pytest tests\test_cli.py::test_channels_status_json_uses_route_backed_bluebubbles_probe tests\test_ops_mesh.py::test_ops_mesh_service_bluebubbles_probe_preserves_http_status -q`
    (`2 passed`), adjacent channel-probe proof (`15 passed, 506 deselected`),
    adjacent BlueBubbles ops proof (`6 passed, 373 deselected`), `ruff
    check`, and `mypy`.

- [x] Tlon native route-backed text send.
  - Source: `openclaw-main/extensions/tlon/src/channel.runtime.ts`,
    `openclaw-main/extensions/tlon/src/targets.ts`,
    `openclaw-main/extensions/tlon/src/urbit/send.ts`,
    `openclaw-main/extensions/tlon/src/urbit/story.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `bab52a95`.
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green Tlon native route proof
    (`1 failed` before implementation, then `1 passed`), helper proof (`2
    passed`), final focused proof (`3 passed`), adjacent native-provider proof
    (`7 passed, 376 deselected`), adjacent CLI proof (`3 passed, 520
    deselected`), `ruff check`, and `mypy`.

- [x] Tlon group/thread reply proof.
  - Source: `openclaw-main/extensions/tlon/src/urbit/send.ts`,
    `openclaw-main/extensions/tlon/src/targets.ts`
  - Target: `tests/test_ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `0fd7cbb8`.
  - Weight: 1
  - Last verified: 2026-05-08, focused Tlon group reply proof (`1 passed`),
    adjacent native-provider proof (`8 passed, 376 deselected`), `ruff check`,
    and `mypy`.

- [x] Tlon image-media upload hook.
  - Source: `openclaw-main/extensions/tlon/src/channel.runtime.ts`,
    `openclaw-main/extensions/tlon/src/urbit/upload.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `0c18844d`.
  - Weight: 1
  - Last verified: 2026-05-08, focused media red/green proof (`1 failed`
    before implementation, then `1 passed`), helper proof (`2 passed`),
    adjacent native-provider proof (`10 passed, 376 deselected`), `ruff
    check`, and `mypy`.

- [x] Tlon hosted Memex media upload.
  - Source: `openclaw-main/extensions/tlon/src/tlon-api.ts`,
    `openclaw-main/extensions/tlon/src/tlon-api.test.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `f742ba8a`.
  - Weight: 1
  - Last verified: 2026-05-08, focused hosted Memex red/green proof (`1
    failed` before implementation, then `1 passed`), trusted-domain proof (`2
    passed`), adjacent native-provider proof (`12 passed, 376 deselected`),
    `ruff check`, and `mypy`.

- [x] Tlon custom S3 media upload.
  - Source: `openclaw-main/extensions/tlon/src/tlon-api.ts`,
    `openclaw-main/extensions/tlon/src/tlon-api.test.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `dc999418`.
  - Weight: 1
  - Last verified: 2026-05-08, focused custom S3 red/green proof (`1
    failed` before implementation, then `1 passed`), adjacent native-provider
    proof (`13 passed, 376 deselected`), `ruff check`, and `mypy`.

- [x] Tlon DM inbound firehose session routing.
  - Source: `openclaw-main/extensions/tlon/src/monitor/index.ts`,
    `openclaw-main/extensions/tlon/src/monitor/utils.ts`,
    `openclaw-main/extensions/tlon/src/session-route.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `51e6b618`.
  - Weight: 1
  - Last verified: 2026-05-08, focused DM inbound red/green proof (`1
    failed` before implementation, then `1 passed`), adjacent provider/session
    proof (`12 passed, 378 deselected`), `ruff check`, and `mypy`.

- [x] Tlon group/thread inbound firehose session routing.
  - Source: `openclaw-main/extensions/tlon/src/monitor/index.ts`,
    `openclaw-main/extensions/tlon/src/monitor/utils.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `b3b06972`.
  - Weight: 1
  - Last verified: 2026-05-08, focused group/thread inbound red/green proof
    (`1 failed` before implementation, then `1 passed`), paired inbound proof
    (`2 passed`), adjacent provider/session proof (`13 passed, 378
    deselected`), `ruff check`, and `mypy`.

- [x] Tlon inbound image media staging.
  - Source: `openclaw-main/extensions/tlon/src/monitor/media.ts`,
    `openclaw-main/extensions/tlon/src/monitor/media.test.ts`,
    `openclaw-main/extensions/tlon/src/monitor/index.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `d7556229`.
  - Weight: 1
  - Last verified: 2026-05-08, focused inbound media red/green proof (`1
    failed` before implementation, then `1 passed`), paired inbound proof (`3
    passed`), adjacent provider/session proof (`14 passed, 378 deselected`),
    `ruff check`, and `mypy`.

- [x] Tlon inbound authorization and pending approvals.
  - Source: `openclaw-main/extensions/tlon/src/monitor/authorization.ts`,
    `openclaw-main/extensions/tlon/src/monitor/approval.ts`,
    `openclaw-main/extensions/tlon/src/monitor/approval-runtime.ts`,
    `openclaw-main/extensions/tlon/src/monitor/index.ts`,
    `openclaw-main/extensions/tlon/src/security.test.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `d7bd3f7d`.
  - Weight: 1
  - Last verified: 2026-05-08, focused Tlon authorization cluster (`5
    passed` after focused failures), adjacent provider/session proof (`19
    passed, 378 deselected`), `ruff check`, and `mypy`.

- [x] Tlon owner approval response replay.
  - Source: `openclaw-main/extensions/tlon/src/monitor/approval.ts`,
    `openclaw-main/extensions/tlon/src/monitor/approval-runtime.ts`,
    `openclaw-main/extensions/tlon/src/monitor/index.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `265b0a10`.
  - Weight: 1
  - Last verified: 2026-05-08, focused owner approval response proof (`1
    failed` before implementation, then `1 passed`), focused Tlon inbound
    proof (`9 passed`), adjacent provider/session proof (`20 passed, 378
    deselected`), `ruff check`, and `mypy`.

- [x] Tlon approval block/admin handling.
  - Source: `openclaw-main/extensions/tlon/src/monitor/approval.ts`,
    `openclaw-main/extensions/tlon/src/monitor/approval-runtime.ts`,
    `openclaw-main/extensions/tlon/src/monitor/index.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `800d2ab6`.
  - Weight: 1
  - Last verified: 2026-05-08, focused block/admin red/green proofs (`1
    failed` before each implementation path, then `1 passed`), focused
    approval/admin cluster (`4 passed`), adjacent provider/session proof (`23
    passed, 378 deselected`), `ruff check`, and `mypy`.

- [x] Tlon production SSE monitor lifecycle.
  - Source: `openclaw-main/extensions/tlon/src/channel.runtime.ts`,
    `openclaw-main/extensions/tlon/src/monitor/index.ts`,
    `openclaw-main/extensions/tlon/src/urbit/sse-client.ts`,
    `openclaw-main/extensions/tlon/src/settings.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `726f03cb`.
  - Weight: 1
  - Last verified: 2026-05-08, focused monitor lifecycle red/green proof
    (`1 failed` before implementation, then `1 passed`), native fake-transport
    proof (`1 passed`), focused pair (`2 passed`), adjacent provider/session
    proof (`25 passed, 378 deselected`), `ruff check`, and `mypy`.

- [x] `channels.start` native Tlon runtime start.
  - Source: `openclaw-main/src/gateway/server-methods/channels.ts`,
    `openclaw-main/src/gateway/server-methods/channels.start.test.ts`,
    `openclaw-main/extensions/tlon/src/channel.runtime.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/ops_mesh.py`, `src/openzues/app.py`
  - Test: `tests/test_gateway_node_methods.py`, `tests/test_ops_mesh.py`,
    `tests/test_gateway_nodes_api.py`
  - Status: checkpointed in `810a6af0`.
  - Weight: 1
  - Last verified: 2026-05-08, focused gateway/ops red-green proofs (`1
    failed` each before implementation, then `1 passed` each), API
    unsupported-boundary proof (`1 passed`), adjacent gateway method proof (`8
    passed, 1118 deselected`), adjacent Tlon monitor proof (`3 passed, 401
    deselected`), `ruff check`, and `mypy`.

- [x] `channels.stop` native Tlon runtime stop.
  - Source: `openclaw-main/src/gateway/server-methods/channels.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/ops_mesh.py`, `src/openzues/app.py`
  - Test: `tests/test_gateway_node_methods.py`, `tests/test_ops_mesh.py`
  - Status: checkpointed in `1365c028`.
  - Weight: 1
  - Last verified: 2026-05-08, focused gateway/ops red-green proofs (`1
    failed` each before implementation, then `1 passed` each), idempotent stop
    proof (`1 passed`), adjacent gateway method proof (`9 passed, 1118
    deselected`), adjacent Tlon monitor proof (`4 passed, 401 deselected`),
    `ruff check`, and `mypy`.

- [x] Telegram `channels.logout` runtime config cleanup.
  - Source: `openclaw-main/src/gateway/server-methods/channels.ts`,
    `openclaw-main/extensions/telegram/src/channel.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/ops_mesh.py`, `src/openzues/app.py`
  - Test: `tests/test_gateway_node_methods.py`, `tests/test_ops_mesh.py`,
    `tests/test_gateway_nodes_api.py`
  - Status: checkpointed in `2d26bdc4`.
  - Weight: 1
  - Last verified: 2026-05-08, focused gateway/ops red-green proofs (`1
    failed` each before implementation, then `1 passed` each), adjacent gateway
    method proof (`10 passed, 1118 deselected`), adjacent OpsMesh lifecycle
    proof (`5 passed, 401 deselected`), adjacent API proof (`4 passed, 424
    deselected`), `ruff check`, and `mypy`.

- [x] LINE `channels.logout` runtime config cleanup.
  - Source: `openclaw-main/src/gateway/server-methods/channels.ts`,
    `openclaw-main/extensions/line/src/gateway.ts`,
    `openclaw-main/extensions/line/src/accounts.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `9674493d`.
  - Weight: 1
  - Last verified: 2026-05-08, focused LINE red-green proof (`1 failed`
    before implementation, then `1 passed`), paired Telegram regression proof
    (`1 passed`), adjacent OpsMesh lifecycle proof (`4 passed, 403
    deselected`), adjacent gateway method proof (`5 passed, 1123 deselected`),
    adjacent API proof (`4 passed, 424 deselected`), `ruff check`, and `mypy`.

- [x] Nextcloud Talk `channels.logout` runtime config cleanup.
  - Source: `openclaw-main/src/gateway/server-methods/channels.ts`,
    `openclaw-main/extensions/nextcloud-talk/src/gateway.ts`,
    `openclaw-main/extensions/nextcloud-talk/src/accounts.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `13de6593`.
  - Weight: 1
  - Last verified: 2026-05-08, focused Nextcloud Talk red-green proof (`1
    failed` before implementation, then `1 passed`), paired LINE/Telegram
    regression proofs (`1 passed` each), adjacent OpsMesh lifecycle proof (`5
    passed, 403 deselected`), adjacent gateway method proof (`5 passed, 1123
    deselected`), adjacent API proof (`4 passed, 424 deselected`), `ruff
    check`, and `mypy`.

- [x] WhatsApp `channels.logout` runtime auth cleanup.
  - Source: `openclaw-main/src/gateway/server-methods/channels.ts`,
    `openclaw-main/extensions/whatsapp/src/channel.ts`,
    `openclaw-main/extensions/whatsapp/src/auth-store.ts`
  - Target: `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_ops_mesh.py`
  - Status: checkpointed in `3e99a587`.
  - Weight: 1
  - Last verified: 2026-05-08, focused WhatsApp red-green proof (`1 failed`
    before implementation, then `1 passed`), adjacent OpsMesh lifecycle proof
    (`6 passed, 403 deselected`), adjacent gateway method proof (`5 passed,
    1123 deselected`), adjacent API proof (`4 passed, 424 deselected`), `ruff
    check`, and `mypy`.

- [x] QQBot `channels.logout` runtime config cleanup.
  - Source: `openclaw-main/src/gateway/server-methods/channels.ts`,
    `openclaw-main/extensions/qqbot/src/channel.ts`,
    `openclaw-main/extensions/qqbot/src/engine/config/credentials.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_config.py`,
    `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_gateway_node_methods.py`, `tests/test_ops_mesh.py`
  - Status: checkpointed in `aac53b3b`.
  - Weight: 1
  - Last verified: 2026-05-08, focused QQBot red-green proof (`1 failed`
    before implementation, then `1 passed`), focused gateway method acceptance
    proof (`1 passed`), adjacent OpsMesh lifecycle proof (`7 passed, 403
    deselected`), adjacent gateway method proof (`6 passed, 1123 deselected`),
    adjacent API proof (`4 passed, 424 deselected`), `ruff check`, and `mypy`.

- [x] Zalo user `channels.logout` runtime profile cleanup.
  - Source: `openclaw-main/src/gateway/server-methods/channels.ts`,
    `openclaw-main/extensions/zalouser/src/channel.ts`,
    `openclaw-main/extensions/zalouser/src/zalo-js.ts`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_config.py`,
    `src/openzues/services/ops_mesh.py`
  - Test: `tests/test_gateway_node_methods.py`, `tests/test_ops_mesh.py`
  - Status: checkpointed in `4d67d5a6`.
  - Weight: 1
  - Last verified: 2026-05-08, focused Zalo user red-green proofs (`1 failed`
    each before implementation, then `1 passed` each), adjacent OpsMesh
    lifecycle proof (`8 passed, 403 deselected`), adjacent gateway method proof
    (`7 passed, 1123 deselected`), adjacent API proof (`4 passed, 424
    deselected`), `ruff check`, and `mypy`.

- [x] Source-install package doctor warnings.
  - Source: `openclaw-main/src/commands/doctor-install.ts`,
    `openclaw-main/src/flows/doctor-health.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `4c1d7a2a`.
  - Weight: 1
  - Last verified: 2026-05-08, focused source-install red-green proof (`1
    failed` before implementation, then `1 passed`), paired package
    distribution regressions (`2 passed`), adjacent update/package doctor proof
    (`7 passed, 517 deselected`), `ruff check`, and `mypy`.

- [x] Update-status git-tag channel projection.
  - Source: `openclaw-main/src/infra/update-channels.ts`,
    `openclaw-main/src/cli/update-cli/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `dce24b5e`.
  - Weight: 1
  - Last verified: 2026-05-08, focused git-tag update-status red-green proof
    (`1 failed` before implementation, then `1 passed`), adjacent
    update/package doctor proof (`7 passed, 518 deselected`), `ruff check`,
    and `mypy`.

- [x] Packed git-tag update-status channel projection.
  - Source: `openclaw-main/src/infra/update-check.ts`,
    `openclaw-main/src/infra/update-channels.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `71029a02`.
  - Weight: 1
  - Last verified: 2026-05-08, focused packed git-tag update-status red-green
    proof (`1 failed` before implementation, then `1 passed`), adjacent
    update/package doctor proof (`8 passed, 518 deselected`), `ruff check`,
    and `mypy`.

- [x] Update-status git metadata envelope.
  - Source: `openclaw-main/src/infra/update-check.ts`,
    `openclaw-main/src/cli/update-cli/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `b31d8f41`.
  - Weight: 1
  - Last verified: 2026-05-08, focused git metadata update-status red-green
    proof (`1 failed` before implementation, then `1 passed`), adjacent
    update/package doctor proof (`9 passed, 518 deselected`), `ruff check`,
    and `mypy`.

- [x] Update-status registry availability projection.
  - Source: `openclaw-main/src/commands/status.update.ts`,
    `openclaw-main/src/infra/update-check.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `55a785a8`.
  - Weight: 1
  - Last verified: 2026-05-08, focused registry availability update-status
    red-green proof (`1 failed` before implementation, then `1 passed`),
    adjacent update/package doctor proof (`10 passed, 518 deselected`), `ruff
    check`, and `mypy`.

- [x] Update-status git availability projection.
  - Source: `openclaw-main/src/commands/status.update.ts`,
    `openclaw-main/src/infra/update-check.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `de37e6f8`.
  - Weight: 1
  - Last verified: 2026-05-08, focused git availability update-status
    red-green proof (`1 failed` before implementation, then `1 passed`),
    adjacent update/package doctor proof (`11 passed, 518 deselected`), `ruff
    check`, and `mypy`.

- [x] Update-status config channel precedence over git tag.
  - Source: `openclaw-main/src/infra/update-channels.ts`,
    `openclaw-main/src/cli/update-cli/status.ts`
  - Target: `tests/test_cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `d9150777`.
  - Weight: 1
  - Last verified: 2026-05-08, focused config-over-tag update-status proof
    (`1 passed`), adjacent update-status proof (`9 passed, 521 deselected`),
    `ruff check`, and focused `git diff --check`.

- [x] Human update-status update-available hint.
  - Source: `openclaw-main/src/commands/status.update.ts`,
    `openclaw-main/src/cli/update-cli/status.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `20e9c885`.
  - Weight: 1
  - Last verified: 2026-05-08, focused human update hint red-green proof (`1
    failed` before implementation, then `1 passed`), adjacent update-status
    proof (`10 passed, 521 deselected`), `ruff check`, and `mypy`.

- [x] Human update-status git-behind hint proof.
  - Source: `openclaw-main/src/commands/status.update.ts`,
    `openclaw-main/src/cli/update-cli/status.ts`
  - Target: `tests/test_cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `d5ea6096`.
  - Weight: 1
  - Last verified: 2026-05-08, focused human git update hint proof (`1
    passed`), adjacent human/update proof (`5 passed, 527 deselected`), `ruff
    check`, and focused `git diff --check`.

- [x] Human update-status combined git/npm hint separator.
  - Source: `openclaw-main/src/commands/status.update.ts`
  - Target: `src/openzues/cli.py`
  - Test: `tests/test_cli.py`
  - Status: checkpointed in `1d19a46c`.
  - Weight: 1
  - Last verified: 2026-05-08, focused combined hint red-green proof (`1
    failed` before implementation, then `1 passed`), adjacent update-status
    proof (`3 passed, 559 deselected`), `ruff check`, `mypy`, and focused
    `git diff --check`.

- [ ] Packaging, companion apps, setup/onboarding, memory/media generation, and
  file-store-only transcript edge cases.
  - Source: OpenClaw repo-wide domains.
  - Status: open
  - Weight: 5+

- [x] Imported plugin SDK command-status.runtime subpath shim.
  - Source: `openclaw-main/src/plugin-sdk/command-status.runtime.ts`,
    `openclaw-main/src/plugin-sdk/command-status-runtime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `command-status.runtime` imports expose the
    same `resolveDirectStatusReplyForSession` helper as
    `command-status-runtime`, preserving blank-session `undefined`, runtime
    delegation, and unavailable-runtime error behavior.
  - Evidence required: focused command-status runtime import test, adjacent
    command-status proof, ruff, mypy
  - Status: checkpointed in `e9c42307`
  - Weight: 1
  - Last verified: 2026-05-08, focused command-status.runtime red/green proof
    (dotted import exposed generic SDK exports before implementation, then
    `1 passed`), adjacent command-status proof (`2 passed, 1159 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK image-generation provider/asset shim.
  - Source: `openclaw-main/src/plugin-sdk/image-generation.ts`,
    `openclaw-main/src/image-generation/image-assets.ts`,
    `openclaw-main/src/image-generation/openai-compatible-image-provider.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `image-generation` imports expose the
    OpenAI-compatible provider factory and image asset helpers for data URLs,
    base64 response parsing, MIME sniffing, upload filenames, provider model
    copy semantics, edit support errors, and missing API-key errors.
  - Evidence required: focused image-generation import test, adjacent
    image/media helper proof, ruff, mypy
  - Status: checkpointed in `8457701d`
  - Weight: 1
  - Last verified: 2026-05-08, focused image-generation red/green proof
    (exact import returned generic passthrough objects before implementation,
    then `1 passed`), adjacent image/media helper proof (`5 passed, 1157
    deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK video-generation Dashscope helper shim.
  - Source: `openclaw-main/src/plugin-sdk/video-generation.ts`,
    `openclaw-main/src/video-generation/dashscope-compatible.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `video-generation` imports expose Dashscope
    WAN model/capability constants, reference URL resolution, input/parameter
    builders, URL extraction, task polling, generated-video download
    projection, and task-run metadata behavior.
  - Evidence required: focused video-generation import test, adjacent
    generation helper proof, ruff, mypy
  - Status: checkpointed in `69e092b5`
  - Weight: 1
  - Last verified: 2026-05-08, focused video-generation red/green proof
    (exact import returned generic passthrough objects before implementation,
    then `1 passed`), adjacent generation helper proof (`4 passed, 1159
    deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK memory-host-search.runtime shim.
  - Source: `openclaw-main/src/plugin-sdk/memory-host-search.runtime.ts`,
    `openclaw-main/src/plugins/memory-runtime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `memory-host-search.runtime` imports expose
    active search-manager lookup, active backend-config resolution, and manager
    cleanup while the non-runtime `memory-host-search` facade remains narrower.
  - Evidence required: focused memory-host-search import test, adjacent memory
    helper proof, ruff, mypy
  - Status: checkpointed in `96722388`
  - Weight: 1
  - Last verified: 2026-05-08, focused memory-host-search.runtime red/green
    proof (exact runtime import returned generic SDK facade before
    implementation, then `1 passed`), adjacent memory helper proof (`4 passed,
    1159 deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK opencode shim.
  - Source: `openclaw-main/src/plugin-sdk/opencode.ts`,
    `openclaw-main/src/plugin-sdk/provider-onboard.ts`,
    `openclaw-main/src/plugin-sdk/provider-auth-api-key.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `opencode` imports expose OpenClaw's
    `createOpencodeCatalogApiKeyAuthMethod`, `applyOpencodeZenModelDefault`,
    and `OPENCODE_ZEN_DEFAULT_MODEL`, including shared Zen/Go wizard metadata,
    shared profile ids, and `OPENCODE_API_KEY` auth posture.
  - Evidence required: focused opencode import test, adjacent provider-onboard
    and provider-auth proof, ruff, mypy
  - Status: checkpointed in `114dc40a`
  - Weight: 1
  - Last verified: 2026-05-08, focused opencode red/green proof (exact import
    returned a helper without OpenClaw's non-interactive auth method shape
    before implementation, then `1 passed`), adjacent provider/onboard proof
    (`3 passed, 1161 deselected`), `ruff check`, `mypy`, and focused
    `git diff --check`.

- [x] Imported plugin SDK ollama/ollama-runtime shim.
  - Source: `openclaw-main/src/plugin-sdk/ollama.ts`,
    `openclaw-main/src/plugin-sdk/ollama-runtime.ts`,
    `openclaw-main/extensions/ollama/src/provider-models.ts`,
    `openclaw-main/extensions/ollama/src/stream.ts`,
    `openclaw-main/extensions/ollama/src/embedding-provider.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `ollama`/`ollama-runtime` imports expose
    API-base normalization, chat request shaping, model id prefix trimming,
    OpenAI-compatible `num_ctx` detection, message/tool-call conversion with
    unsafe integer preservation, assistant message projection, tolerant NDJSON
    parsing, and embedding-provider export posture.
  - Evidence required: focused Ollama runtime import test, adjacent
    provider/runtime proof, ruff, mypy
  - Status: checkpointed in `2b1e3865`
  - Weight: 1
  - Last verified: 2026-05-08, focused Ollama red/green proof (exact import
    returned generic/passthrough data before implementation, then `1 passed`),
    adjacent provider/runtime proof (`4 passed, 1161 deselected`), `ruff
    check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK line-surface/action helper shim.
  - Source: `openclaw-main/src/plugin-sdk/line-surface.ts`,
    `openclaw-main/src/plugin-sdk/line-runtime.ts`,
    `openclaw-main/extensions/line/src/accounts.ts`,
    `openclaw-main/extensions/line/src/group-keys.ts`,
    `openclaw-main/extensions/line/src/flex-templates/basic-cards.ts`,
    `openclaw-main/extensions/line/src/markdown-to-line.ts`,
    `openclaw-main/extensions/line/src/actions.ts`,
    `openclaw-main/extensions/line/src/send.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `line-surface` imports expose account/default
    resolution, group key lookup, basic Flex card builders, and
    `processLineMessage`; `line-runtime` exposes action, quick-reply, and
    directive helper functions used by imported LINE runtime tools.
  - Evidence required: focused LINE surface import test, adjacent provider
    facade proof, ruff, mypy
  - Status: checkpointed in `fee011e1`
  - Weight: 1
  - Last verified: 2026-05-08, focused LINE surface red/green proof (exact
    imports returned generic or wrong-shaped data before implementation, then
    `1 passed`), adjacent provider facade proof (`4 passed, 1162 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK line root/core barrel shim.
  - Source: `openclaw-main/src/plugin-sdk/line.ts`,
    `openclaw-main/src/plugin-sdk/line-core.ts`,
    `openclaw-main/src/plugin-sdk/channel-plugin-common.ts`,
    `openclaw-main/src/plugin-sdk/status-helpers.ts`,
    `openclaw-main/src/plugin-sdk/setup.ts`,
    `openclaw-main/extensions/line/src/accounts.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `line`/`line-core` imports expose exact
    root/core barrel keys for channel config helpers, credential cleanup,
    status summaries, runtime group policy helpers, LINE surface reexports,
    setup helpers, and docs-link formatting.
  - Evidence required: focused LINE root/core import test, adjacent LINE/setup
    proof, ruff, mypy
  - Status: checkpointed in `696e61f2`
  - Weight: 1
  - Last verified: 2026-05-08, focused LINE root/core red/green proof (exact
    imports returned generic or wrong-shaped data before implementation, then
    `1 passed`), adjacent LINE/setup proof (`4 passed, 1163 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK matrix-helper shim.
  - Source: `openclaw-main/src/plugin-sdk/matrix-helper.ts`,
    `openclaw-main/extensions/matrix/src/account-selection.ts`,
    `openclaw-main/extensions/matrix/src/env-vars.ts`,
    `openclaw-main/extensions/matrix/src/storage-paths.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `matrix-helper` imports expose Matrix
    channel config lookup, normalized account entry/default resolution,
    explicit default-account detection, scoped env var names, credential paths,
    legacy flat-store paths, and account storage-root derivation.
  - Evidence required: focused Matrix helper import test, adjacent Matrix
    helper proof, ruff, mypy
  - Status: checkpointed in `1717d1c2`
  - Weight: 1
  - Last verified: 2026-05-08, focused Matrix helper red/green proof (exact
    import returned the generic SDK facade before implementation, then `1
    passed`), adjacent Matrix helper proof (`4 passed, 1164 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK talk-voice shim.
  - Source: `openclaw-main/src/plugin-sdk/talk-voice.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `talk-voice` imports expose only the bundled
    talk-voice `definePluginEntry` helper facade, preserving lazy
    `configSchema` resolution and plugin `register` behavior.
  - Evidence required: focused talk-voice import test, adjacent plugin-entry
    facade proof, ruff, mypy
  - Status: checkpointed in `114f60ec`
  - Weight: 1
  - Last verified: 2026-05-08, focused talk-voice red/green proof (exact
    import returned the generic SDK facade before implementation, then `1
    passed`), adjacent plugin-entry facade proof (`3 passed, 1166
    deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK memory-lancedb shim.
  - Source: `openclaw-main/src/plugin-sdk/memory-lancedb.ts`,
    `openclaw-main/src/plugin-sdk/state-paths.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `memory-lancedb` imports expose only the
    bundled memory-lancedb `definePluginEntry` and `resolveStateDir` helpers,
    preserving plugin registration and OpenClaw state-dir resolution.
  - Evidence required: focused memory-lancedb import test, adjacent
    state-paths/plugin-entry proof, ruff, mypy
  - Status: checkpointed in `beac73d9`
  - Weight: 1
  - Last verified: 2026-05-08, focused memory-lancedb red/green proof (exact
    import returned the generic SDK facade before implementation, then `1
    passed`), adjacent state-paths/plugin-entry proof (`3 passed, 1167
    deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK phone-control shim.
  - Source: `openclaw-main/src/plugin-sdk/phone-control.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `phone-control` imports expose only the
    bundled phone-control `definePluginEntry` helper facade, preserving plugin
    registration and `nodeHostCommands` projection.
  - Evidence required: focused phone-control import test, adjacent plugin-entry
    facade proof, ruff, mypy
  - Status: checkpointed in `93b139e3`
  - Weight: 1
  - Last verified: 2026-05-08, focused phone-control red/green proof (exact
    import returned the generic SDK facade before implementation, then `1
    passed`), adjacent plugin-entry facade proof (`3 passed, 1168
    deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK matrix-runtime-shared shim.
  - Source: `openclaw-main/src/plugin-sdk/matrix-runtime-shared.ts`,
    `openclaw-main/src/infra/format-time/format-datetime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `matrix-runtime-shared` imports expose only
    the runtime `formatZonedTimestamp` helper, preserving UTC formatting,
    optional seconds, and invalid-timezone undefined projection.
  - Evidence required: focused Matrix runtime-shared import test, adjacent
    Matrix/time proof, ruff, mypy
  - Status: checkpointed in `c34a2d10`
  - Weight: 1
  - Last verified: 2026-05-08, focused Matrix runtime-shared red/green proof
    (exact import returned the generic SDK facade before implementation, then
    `1 passed`), adjacent Matrix/time proof (`4 passed, 1168 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK lobster shim.
  - Source: `openclaw-main/src/plugin-sdk/lobster.ts`,
    `openclaw-main/src/plugin-sdk/windows-spawn.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `lobster` imports expose only the bundled
    Lobster `definePluginEntry`, `resolveWindowsSpawnProgramCandidate`,
    `applyWindowsSpawnProgramPolicy`, and `materializeWindowsSpawnProgram`
    helpers.
  - Evidence required: focused Lobster import test, adjacent
    Windows-spawn/plugin-entry proof, ruff, mypy
  - Status: checkpointed in `0beb9dbc`
  - Weight: 1
  - Last verified: 2026-05-08, focused Lobster red/green proof (exact import
    returned the generic SDK facade before implementation, then `1 passed`),
    adjacent Windows-spawn/plugin-entry proof (`3 passed, 1170 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK voice-call shim.
  - Source: `openclaw-main/src/plugin-sdk/voice-call.ts`,
    `openclaw-main/src/config/zod-schema.core.ts`,
    `openclaw-main/src/infra/http-body.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `voice-call` imports expose bundled
    voice-call `definePluginEntry`, TTS schema helpers, HTTP body limit
    helpers, SSRF fetch helper, and `sleep`.
  - Evidence required: focused voice-call import test, adjacent webhook/TTS
    proof, ruff, mypy
  - Status: checkpointed in `bdbc7724`
  - Weight: 1
  - Last verified: 2026-05-08, focused voice-call red/green proof (fallback
    returned schema passthrough functions without `safeParse` before
    implementation, then `1 passed`), adjacent webhook/TTS/Lobster proof (`4
    passed, 1170 deselected`), `ruff check`, `mypy`, and focused `git diff
    --check`.

- [x] Imported plugin SDK matrix-deps shim.
  - Source: `openclaw-main/src/plugin-sdk/matrix-deps.ts`,
    `openclaw-main/extensions/matrix/src/matrix/deps.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `matrix-deps` imports expose
    `isMatrixSdkAvailable` and `ensureMatrixSdkInstalled`, including Matrix
    package availability probing and OpenClaw-shaped confirmation-denied
    install error text.
  - Evidence required: focused Matrix deps import test, adjacent Matrix helper
    proof, ruff, mypy
  - Status: checkpointed in `3cdfebfd`
  - Weight: 1
  - Last verified: 2026-05-08, focused Matrix deps red/green proof (exact
    import returned generic SDK keys before implementation, then `1 passed`),
    adjacent Matrix helper proof (`4 passed, 1171 deselected`), `ruff check`,
    `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK feishu-security shim.
  - Source: `openclaw-main/src/plugin-sdk/feishu-security.ts`,
    `openclaw-main/extensions/feishu/src/security-audit-shared.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `feishu-security` imports expose
    `collectFeishuSecurityAuditFindings`, including the Feishu doc tool
    document-owner permission warning and disabled/no-finding paths.
  - Evidence required: focused Feishu security import test, adjacent security
    and secret proof, ruff, mypy
  - Status: checkpointed in `a7ea60d4`
  - Weight: 1
  - Last verified: 2026-05-08, focused Feishu security red/green proof (exact
    import returned generic passthrough values before implementation, then `1
    passed`), adjacent security/secret proof (`6 passed, 1170 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK synology-chat shim.
  - Source: `openclaw-main/src/plugin-sdk/synology-chat.ts`,
    `openclaw-main/extensions/synology-chat/src/security-audit.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `synology-chat` imports expose
    `collectSynologyChatSecurityAuditFindings`, including the Synology Chat
    dangerous username/nickname matching warning, account-note formatting, and
    disabled/no-finding paths.
  - Evidence required: focused Synology Chat import test, adjacent provider
    security proof, ruff, mypy
  - Status: checkpointed in `eaf176bb`
  - Weight: 1
  - Last verified: 2026-05-08, focused Synology Chat red/green proof (exact
    import returned the generic SDK facade before implementation, then `1
    passed`), adjacent provider/security proof (`3 passed, 1174 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK qa-runtime shim.
  - Source: `openclaw-main/src/plugin-sdk/qa-runtime.ts`,
    `openclaw-main/src/plugin-sdk/private-qa-bundled-env.ts`,
    `openclaw-main/src/plugin-sdk/facade-runtime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `qa-runtime` imports expose only
    `loadQaRuntimeModule` and `isQaRuntimeAvailable`, preserving cold loading,
    private-QA env propagation, qa-lab `runtime-api.js` loading, and
    missing-artifact unavailable projection.
  - Evidence required: focused QA runtime import test, adjacent QA/facade
    proof, ruff, mypy
  - Status: checkpointed in `a20434e1`
  - Weight: 1
  - Last verified: 2026-05-08, focused QA runtime red/green proof (exact
    import returned the generic SDK facade before implementation, then `1
    passed`), adjacent QA/facade proof (`4 passed, 1174 deselected`), `ruff
    check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK qa-lab shim.
  - Source: `openclaw-main/src/plugin-sdk/qa-lab.ts`,
    `openclaw-main/src/plugin-sdk/facade-loader.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `qa-lab` imports expose only
    `registerQaLabCli` and `isQaLabCliAvailable`, preserving cold loading,
    `qa-lab/cli.js` public-surface delegation, and missing-artifact
    unavailable projection.
  - Evidence required: focused QA Lab import test, adjacent QA proof, ruff,
    mypy
  - Status: checkpointed in `d187a8ce`
  - Weight: 1
  - Last verified: 2026-05-08, focused QA Lab red/green proof (exact import
    returned the generic SDK facade before implementation, then `1 passed`),
    adjacent QA proof (`4 passed, 1175 deselected`), `ruff check`, `mypy`, and
    focused `git diff --check`.

- [x] Imported plugin SDK feishu-setup shim.
  - Source: `openclaw-main/src/plugin-sdk/feishu-setup.ts`,
    `openclaw-main/extensions/feishu/setup-api.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `feishu-setup` imports expose lazy
    `feishuSetupAdapter` and `feishuSetupWizard` facade objects backed by
    `feishu/setup-api.js`, preserving cold loading and adapter/wizard property
    passthrough.
  - Evidence required: focused Feishu setup import test, adjacent Feishu/setup
    proof, ruff, mypy
  - Status: checkpointed in `5bd3b500`
  - Weight: 1
  - Last verified: 2026-05-08, focused Feishu setup red/green proof (exact
    import returned the generic SDK facade before implementation, then `1
    passed`), adjacent Feishu/setup proof (`4 passed, 1176 deselected`), `ruff
    check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK zalo-setup shim.
  - Source: `openclaw-main/src/plugin-sdk/zalo-setup.ts`,
    `openclaw-main/extensions/zalo/setup-api.ts`,
    `openclaw-main/extensions/zalo/contract-api.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `zalo-setup` imports expose direct
    `evaluateZaloGroupAccess` and `resolveZaloRuntimeGroupPolicy` facade
    functions plus lazy `zaloSetupAdapter` and `zaloSetupWizard` objects backed
    by Zalo public-surface artifacts.
  - Evidence required: focused Zalo setup import test, adjacent provider/setup
    proof, ruff, mypy
  - Status: checkpointed in `759e64fe`
  - Weight: 1
  - Last verified: 2026-05-08, focused Zalo setup red/green proof (exact import
    returned the generic SDK facade before implementation, then `1 passed`),
    adjacent Zalo/setup proof (`6 passed, 1175 deselected`), `ruff check`,
    `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK feishu-conversation shim.
  - Source: `openclaw-main/src/plugin-sdk/feishu-conversation.ts`,
    `openclaw-main/extensions/feishu/contract-api.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `feishu-conversation` imports expose direct
    Feishu conversation parsing/building and thread-binding manager facade
    functions plus lazy binding-channel/testing surfaces backed by
    `feishu/contract-api.js`.
  - Evidence required: focused Feishu conversation import test, adjacent
    provider/setup proof, ruff, mypy
  - Status: checkpointed in `16442d3d`
  - Weight: 1
  - Last verified: 2026-05-08, focused Feishu conversation red/green proof
    (exact import returned the generic SDK facade before implementation, then
    `1 passed`), adjacent Feishu/Zalo proof (`4 passed, 1178 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK slack shim.
  - Source: `openclaw-main/src/plugin-sdk/slack.ts`,
    `openclaw-main/extensions/slack/interactive-replies-api.ts`,
    `openclaw-main/extensions/slack/security-contract-api.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `slack` imports expose
    `compileSlackInteractiveReplies` and `collectSlackSecurityAuditFindings`,
    preserving the interactive-replies and security public-surface loader
    boundaries.
  - Evidence required: focused Slack import test, adjacent provider/runtime
    proof, ruff, mypy
  - Status: checkpointed in `4221913e`
  - Weight: 1
  - Last verified: 2026-05-08, focused Slack red/green proof (exact import
    returned the generic SDK facade before implementation, then `1 passed`),
    adjacent provider/runtime proof (`4 passed, 1179 deselected`), `ruff
    check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK xiaomi shim.
  - Source: `openclaw-main/src/plugin-sdk/xiaomi.ts`,
    `openclaw-main/extensions/xiaomi/api.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `xiaomi` imports expose
    `applyXiaomiConfig`, `applyXiaomiProviderConfig`, `buildXiaomiProvider`,
    `XIAOMI_DEFAULT_MODEL_ID`, and `XIAOMI_DEFAULT_MODEL_REF`, preserving the
    `xiaomi/api.js` facade boundary.
  - Evidence required: focused Xiaomi import test, adjacent provider proof,
    ruff, mypy
  - Status: checkpointed in `04c0b54d`
  - Weight: 1
  - Last verified: 2026-05-08, focused Xiaomi red/green proof (exact import
    returned the generic SDK facade before implementation, then `1 passed`),
    adjacent provider proof (`3 passed, 1181 deselected`), `ruff check`,
    `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK matrix-runtime-heavy shim.
  - Source: `openclaw-main/src/plugin-sdk/matrix-runtime-heavy.ts`,
    `openclaw-main/extensions/matrix/runtime-heavy-api.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `matrix-runtime-heavy` imports expose Matrix
    legacy crypto/state detection, migration, pending/actionable checks, and
    migration snapshot delegates backed by `matrix/runtime-heavy-api.js`.
  - Evidence required: focused Matrix runtime-heavy import test, adjacent
    Matrix proof, ruff, mypy
  - Status: checkpointed in `d3619058`
  - Weight: 1
  - Last verified: 2026-05-08, focused Matrix runtime-heavy red/green proof
    (exact import returned the generic SDK facade before implementation, then
    `1 passed`), adjacent Matrix proof (`4 passed, 1181 deselected`), `ruff
    check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK memory-core-bundled-runtime shim.
  - Source: `openclaw-main/src/plugin-sdk/memory-core-bundled-runtime.ts`,
    `openclaw-main/extensions/memory-core/api.ts`,
    `openclaw-main/extensions/memory-core/runtime-api.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `memory-core-bundled-runtime` imports expose
    memory-core embedding-provider, dream-artifact repair, grounded REM,
    backfill, recall filtering, and REM harness facade delegates backed by
    memory-core API/runtime public surfaces.
  - Evidence required: focused memory-core bundled import test, adjacent memory
    proof, ruff, mypy
  - Status: checkpointed in `280e6b6c`
  - Weight: 1
  - Last verified: 2026-05-08, focused memory-core bundled red/green proof
    (exact import returned the generic SDK facade before implementation, then
    `1 passed`), adjacent memory proof (`4 passed, 1182 deselected`), `ruff
    check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK twitch setup shim.
  - Source: `openclaw-main/src/plugin-sdk/twitch.ts`,
    `openclaw-main/src/plugin-sdk/channel-setup.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `twitch` imports expose root
    `twitchSetupAdapter` and `twitchSetupWizard` optional-channel setup
    surfaces while inherited generic SDK helper exports remain reachable.
  - Evidence required: focused Twitch import test, adjacent optional setup
    proof, ruff, mypy
  - Status: checkpointed in `24f8edee`
  - Weight: 1
  - Last verified: 2026-05-08, focused Twitch red/green proof (exact root
    import returned generic placeholders before implementation, then `1
    passed`), adjacent optional setup proof (`4 passed, 1183 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK tlon setup shim.
  - Source: `openclaw-main/src/plugin-sdk/tlon.ts`,
    `openclaw-main/src/plugin-sdk/channel-setup.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `tlon` imports expose root
    `tlonSetupAdapter` and `tlonSetupWizard` optional-channel setup surfaces
    while inherited generic SDK helper exports remain reachable.
  - Evidence required: focused Tlon import test, adjacent optional setup proof,
    ruff, mypy
  - Status: checkpointed in `2c3feae2`
  - Weight: 1
  - Last verified: 2026-05-08, focused Tlon red/green proof (exact root import
    returned generic placeholders before implementation, then `1 passed`),
    adjacent optional setup proof (`4 passed, 1184 deselected`), `ruff check`,
    `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK nostr setup shim.
  - Source: `openclaw-main/src/plugin-sdk/nostr.ts`,
    `openclaw-main/src/plugin-sdk/channel-setup.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `nostr` imports expose root
    `nostrSetupAdapter` and `nostrSetupWizard` optional-channel setup surfaces
    while inherited generic SDK helper exports remain reachable.
  - Evidence required: focused Nostr import test, adjacent optional setup
    proof, ruff, mypy
  - Status: checkpointed in `70792d82`
  - Weight: 1
  - Last verified: 2026-05-08, focused Nostr red/green proof (exact root
    import returned generic placeholders before implementation, then `1
    passed`), adjacent optional setup proof (`5 passed, 1184 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK msteams setup shim.
  - Source: `openclaw-main/src/plugin-sdk/msteams.ts`,
    `openclaw-main/src/plugin-sdk/channel-setup.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `msteams` imports expose root
    `msteamsSetupAdapter` and `msteamsSetupWizard` optional-channel setup
    surfaces while inherited generic SDK helper exports remain reachable.
  - Evidence required: focused Microsoft Teams import test, adjacent optional
    setup proof, ruff, mypy
  - Status: checkpointed in `09d036fd`
  - Weight: 1
  - Last verified: 2026-05-08, focused Microsoft Teams red/green proof (exact
    root import returned generic placeholders before implementation, then `1
    passed`), adjacent optional setup proof (`6 passed, 1184 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK googlechat root shim.
  - Source: `openclaw-main/src/plugin-sdk/googlechat.ts`,
    `openclaw-main/src/plugin-sdk/channel-setup.ts`,
    `openclaw-main/src/plugin-sdk/channel-policy.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `googlechat` imports expose root
    `googlechatSetupAdapter`, `googlechatSetupWizard`, and
    `resolveGoogleChatGroupRequireMention`, while inherited generic SDK helper
    exports remain reachable.
  - Evidence required: focused Google Chat import test, adjacent setup/policy
    proof, ruff, mypy
  - Status: checkpointed in `37ec6cd2`
  - Weight: 1
  - Last verified: 2026-05-08, focused Google Chat red/green proof (exact root
    import returned generic placeholders before implementation, then `1
    passed`), adjacent setup/policy proof (`4 passed, 1187 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK telegram root shim.
  - Source: `openclaw-main/src/plugin-sdk/telegram.ts`,
    `openclaw-main/extensions/telegram/contract-api.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `telegram` imports expose
    `parseTelegramTopicConversation`, `singleAccountKeysToMove`,
    `mergeTelegramAccountConfig`, and `collectTelegramSecurityAuditFindings`
    with OpenClaw-shaped parsed topic, merge, and audit result behavior.
  - Evidence required: focused Telegram import test, adjacent Telegram proof,
    ruff, mypy
  - Status: checkpointed in `2723c527`
  - Weight: 1
  - Last verified: 2026-05-08, focused Telegram red/green proof (exact root
    import returned generic placeholder behavior before implementation, then
    `1 passed`), adjacent Telegram proof (`3 passed, 1189 deselected`), `ruff
    check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK feishu root shim.
  - Source: `openclaw-main/src/plugin-sdk/feishu.ts`,
    `openclaw-main/src/plugin-sdk/feishu-setup.ts`,
    `openclaw-main/src/plugin-sdk/feishu-conversation.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `feishu` imports expose root
    `feishuSetupAdapter`, `feishuSetupWizard`, Feishu conversation parsing and
    thread-binding helpers, and inherited generic SDK helper exports.
  - Evidence required: focused Feishu root import test, adjacent Feishu proof,
    ruff, mypy
  - Status: checkpointed in `45877663`
  - Weight: 1
  - Last verified: 2026-05-08, focused Feishu root red/green proof (exact root
    import returned generic placeholders before implementation, then `1
    passed`), adjacent Feishu proof (`4 passed, 1189 deselected`), `ruff
    check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK root shim.
  - Source: `openclaw-main/src/plugin-sdk/index.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped root imports expose the upstream tiny
    enumerable helper set (`emptyPluginConfigSchema`, context-engine helpers,
    diagnostic event subscription, and schema enum helpers) while inherited
    generic SDK properties remain reachable for legacy consumers.
  - Evidence required: focused root SDK import test, adjacent root/compat
    proof, ruff, mypy
  - Status: checkpointed in `b0df7421`
  - Weight: 1
  - Last verified: 2026-05-08, focused root SDK red/green proof (root import
    returned the broad generic enumerable surface before implementation, then
    `1 passed`), adjacent root/compat proof (`2 passed, 1192 deselected`),
    `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK QA runtime test helper shim.
  - Source: `openclaw-main/src/plugin-sdk/qa-runtime.test-helpers.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `qa-runtime.test-helpers` imports expose
    upstream-shaped temp private-QA source-root creation, temp-dir cleanup, env
    restore, and QA runtime surface-load expectation helpers.
  - Evidence required: focused QA runtime test-helper import test, adjacent QA
    runtime proof, ruff, mypy
  - Status: checkpointed in `a15dc5d5`
  - Weight: 1
  - Last verified: 2026-05-08, focused QA runtime test-helper red/green proof
    (exact helper import returned generic placeholder behavior before
    implementation, then `1 passed`), adjacent QA runtime proof (`3 passed,
    1192 deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK browser facade test helper shim.
  - Source: `openclaw-main/src/plugin-sdk/browser-facade-test-helpers.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `browser-facade-test-helpers` imports expose
    upstream-shaped browser host-inspection facade mocking, delegation
    assertions, and unavailable-facade checks.
  - Evidence required: focused browser facade test-helper import test,
    adjacent browser host/node proof, ruff, mypy
  - Status: checkpointed in `4e950ba5`
  - Weight: 1
  - Last verified: 2026-05-08, focused browser facade test-helper red/green
    proof (exact helper import returned generic placeholder behavior before
    implementation, then `1 passed`), adjacent browser facade proof (`3
    passed, 1193 deselected`), `ruff check`, `mypy`, and focused `git diff
    --check`.

- [x] Imported plugin SDK API baseline hash helper shim.
  - Source: `openclaw-main/src/plugin-sdk/api-baseline.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `api-baseline` imports expose the upstream
    value export names and exact
    `computePluginSdkApiBaselineHashFileContent(rendered)` SHA-256 hash-file
    formatting for rendered JSON/JSONL artifacts.
  - Evidence required: focused API baseline import test, adjacent root SDK
    proof, ruff, mypy
  - Status: checkpointed in `bcf2185c`
  - Weight: 1
  - Last verified: 2026-05-08, focused API baseline hash-helper red/green
    proof (exact helper import returned broad generic placeholders before
    implementation, then `1 passed`), adjacent root SDK proof (`2 passed,
    1195 deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK Nextcloud Talk root shim.
  - Source: `openclaw-main/src/plugin-sdk/nextcloud-talk.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `nextcloud-talk` imports expose the bundled
    private helper barrel for auth-rate-limiting, channel config/setup, secret
    input, group policy, reply payload, inbound dispatch, status, and runtime
    logger helpers.
  - Evidence required: focused Nextcloud Talk root import test, adjacent
    channel/setup proof, ruff, mypy
  - Status: checkpointed in `b76a0b47`
  - Weight: 1
  - Last verified: 2026-05-08, focused Nextcloud Talk root red/green proof
    (exact root import returned broad generic placeholders before
    implementation, then `1 passed`), adjacent channel/setup proof (`4 passed,
    1194 deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK root test-helper harness shim.
  - Source: `openclaw-main/src/plugin-sdk/test-helpers.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped root `test-helpers` imports expose
    `createPluginSdkTestHarness()` with OpenClaw-style fixture-root temp
    directory sequencing for async and sync test cases.
  - Evidence required: focused root test-helper import test, adjacent
    test-helper subpath proof, ruff, mypy
  - Status: checkpointed in `2af9f158`
  - Weight: 1
  - Last verified: 2026-05-08, focused root test-helper red/green proof (root
    import returned no usable harness before implementation, then `1 passed`),
    adjacent test-helper proof (`4 passed, 1195 deselected`), `ruff check`,
    `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK QA channel facade shim.
  - Source: `openclaw-main/src/plugin-sdk/qa-channel.ts`,
    `openclaw-main/extensions/qa-channel/src/bus-client.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `qa-channel` imports expose exact target
    normalization/parsing/building helpers, the QA channel plugin object,
    runtime setter, and JSON bus method exports.
  - Evidence required: focused QA channel import test, adjacent QA runtime/lab
    proof, ruff, mypy
  - Status: checkpointed in `fda1c201`
  - Weight: 1
  - Last verified: 2026-05-08, focused QA channel red/green proof (exact
    facade import returned generic placeholder behavior before implementation,
    then `1 passed`), adjacent QA proof (`4 passed, 1196 deselected`), `ruff
    check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK IRC root shim.
  - Source: `openclaw-main/src/plugin-sdk/irc.ts`,
    `openclaw-main/extensions/irc/package.json`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `irc` imports expose the bundled private IRC
    helper barrel for channel config, setup, pairing, reply payload, inbound
    dispatch, account resolution, status, runtime logger, and policy helpers.
  - Evidence required: focused IRC root import test, adjacent IRC/channel
    proof, ruff, mypy
  - Status: checkpointed in `16b12bb8`
  - Weight: 1
  - Last verified: 2026-05-08, focused IRC root red/green proof (exact root
    import returned generic placeholder/meta behavior before implementation,
    then `1 passed`), adjacent IRC/channel proof (`4 passed, 1197
    deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK Matrix root shim.
  - Source: `openclaw-main/src/plugin-sdk/matrix.ts`,
    `openclaw-main/extensions/matrix/src/setup-contract.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `matrix` imports expose Matrix setup
    adapter/wizard, single-account migration keys, named-account promotion
    keys, and the promotion-target resolver while inherited shared SDK helpers
    remain reachable.
  - Evidence required: focused Matrix root import test, adjacent Matrix helper
    proof, ruff, mypy
  - Status: checkpointed in `a00b4035`
  - Weight: 1
  - Last verified: 2026-05-08, focused Matrix root red/green proof (exact
    root import returned generic placeholder array/function behavior before
    implementation, then `1 passed`), adjacent Matrix proof (`5 passed, 1197
    deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK memory-core root shim.
  - Source: `openclaw-main/src/plugin-sdk/memory-core.ts`,
    `openclaw-main/src/memory-host-sdk/dreaming.ts`,
    `openclaw-main/src/plugin-sdk/memory-core-host-status.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `memory-core` imports expose the root
    memory-core barrel by composing engine, runtime-core, CLI, events, status,
    and runtime-files helpers, including OpenClaw dreaming config/day/workspace
    helpers.
  - Evidence required: focused memory-core root import test, adjacent
    memory-core host/status/files/engine proof, ruff, mypy
  - Status: checkpointed in `21cbfac2`
  - Weight: 1
  - Last verified: 2026-05-08, focused memory-core root red/green proof
    (exact root import returned generic placeholder status/config behavior
    before implementation, then `1 passed`), adjacent memory-core proof (`6
    passed, 1197 deselected`), `ruff check`, `mypy`, and focused `git diff
    --check`.

- [x] Imported plugin SDK Mattermost root shim.
  - Source: `openclaw-main/src/plugin-sdk/mattermost.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `mattermost` imports expose the bundled
    private Mattermost helper barrel for channel config, pairing, reply
    history, single-channel secret, status, media, group policy, request-body,
    and proxy/client-IP helpers.
  - Evidence required: focused Mattermost root import test, adjacent
    Mattermost policy/reply proof, ruff, mypy
  - Status: checkpointed in `5500bc77`
  - Weight: 1
  - Last verified: 2026-05-08, focused Mattermost root red/green proof (exact
    root import returned generic placeholder helper behavior before
    implementation, then `1 passed`), adjacent Mattermost proof (`3 passed,
    1201 deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK Zalo root shim.
  - Source: `openclaw-main/src/plugin-sdk/zalo.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `zalo` imports expose the root bundled Zalo
    helper barrel for setup, allow-from, command-auth, channel config, pairing,
    reply payload, status, webhook ingress, outbound media, and proxy/client-IP
    helpers.
  - Evidence required: focused Zalo root import test, adjacent
    Zalo/setup/zalouser/channel-send/webhook proof, ruff, mypy
  - Status: checkpointed in `e789e816`
  - Weight: 1
  - Last verified: 2026-05-08, focused Zalo root red/green proof (exact root
    import returned broad generic fallback behavior before implementation,
    then `1 passed`), adjacent Zalo/setup/webhook proof (`5 passed, 1200
    deselected`), `ruff check`, `mypy`, and focused `git diff --check`.

- [x] Imported plugin SDK BlueBubbles root shim.
  - Source: `openclaw-main/src/plugin-sdk/bluebubbles.ts`,
    `openclaw-main/extensions/bluebubbles/src/actions-contract.ts`,
    `openclaw-main/extensions/bluebubbles/src/conversation-id.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: scoped and unscoped `bluebubbles` imports expose the root
    BlueBubbles helper barrel, including the lazy bundled `api.js` facade for
    conversation binding/status helpers, action constants, channel config,
    policy, media, command/tool, webhook, text, and routing helpers.
  - Evidence required: focused BlueBubbles root import test, adjacent
    BlueBubbles policy/channel/webhook proof, ruff, mypy
  - Status: checkpointed in `f5b4121a`
  - Weight: 1
  - Last verified: 2026-05-08, focused BlueBubbles root red/green proof
    (exact root import returned broad generic fallback behavior before
    implementation, then `1 passed`), adjacent BlueBubbles/channel/webhook
    proof (`5 passed, 1201 deselected`), `ruff check`, `mypy`, and focused
    `git diff --check`.

- [x] `chat.history` large-limit cap.
  - Source: `openclaw-main/src/gateway/server-methods/chat.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: RPC `chat.history` floors numeric `limit` values and clamps
    values above OpenClaw's 1000-message hard cap instead of rejecting them
    before transcript projection.
  - Evidence required: focused `chat.history` large-limit test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `6a964896`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_caps_large_limit_like_openclaw -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`32 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` base64 audio redaction.
  - Source: `openclaw-main/src/gateway/chat-display-projection.ts`,
    `openclaw-main/src/gateway/server-methods/server-methods.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: structured chat-history audio blocks with
    `source.type="base64"` remove the embedded `source.data`, surface
    `source.omitted=true`, and retain encoded byte length under
    `source.bytes`.
  - Evidence required: focused `chat.history` audio-redaction test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `d8fe12d3`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_redacts_base64_audio_content_blocks -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`33 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` inline image data redaction.
  - Source: `openclaw-main/src/gateway/chat-display-projection.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: structured chat-history image blocks remove embedded `data`,
    surface `omitted=true`, and retain encoded byte length under `bytes`.
  - Evidence required: focused `chat.history` image-redaction test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `cd286b80`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_redacts_inline_image_data_blocks -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`34 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` structured partial JSON field caps.
  - Source: `openclaw-main/src/gateway/chat-display-projection.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: non-tool structured chat-history content blocks apply the
    effective `maxChars` cap to string `partialJson` and `arguments` fields,
    while tool block payloads are left for exact tool-display preservation.
  - Evidence required: focused structured field-cap test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `812f50de`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_truncates_structured_partial_json_fields -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`35 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` exact tool block payload preservation.
  - Source: `openclaw-main/src/gateway/chat-display-projection.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: structured content blocks whose type is a tool-history block
    preserve exact `text` and `content` payloads under `maxChars`, while still
    stripping display-only inline directives.
  - Evidence required: focused exact tool-block payload test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `ec0a6950`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_preserves_exact_tool_block_payloads -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`36 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` heartbeat and empty-row filtering.
  - Source: `openclaw-main/src/gateway/chat-display-projection.ts`,
    `openclaw-main/src/auto-reply/heartbeat-filter.ts`,
    `openclaw-main/src/auto-reply/heartbeat.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected `chat.history` rows hide empty user content,
    OpenClaw heartbeat poll/configured/task prompts, and short
    `HEARTBEAT_OK` assistant acknowledgements while keeping ordinary assistant
    responses visible.
  - Evidence required: focused heartbeat/empty-row test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `7e480dec`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_hides_empty_user_and_heartbeat_rows -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`37 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `sessions.history` heartbeat and empty-row filtering.
  - Source: `openclaw-main/src/gateway/session-history-state.test.ts`,
    `openclaw-main/src/gateway/chat-display-projection.ts`,
    `openclaw-main/src/auto-reply/heartbeat-filter.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected `sessions.history` rows hide empty user content,
    configured/task heartbeat prompts, and short `HEARTBEAT_OK` assistant
    acknowledgements while keeping meaningful assistant alerts visible.
  - Evidence required: focused sessions-history heartbeat/empty-row test,
    adjacent transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `7d8e6b3b`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_sessions_history_hides_empty_user_and_heartbeat_rows -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`38 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` structured empty-user filtering.
  - Source: `openclaw-main/src/gateway/chat-display-projection.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected `chat.history` rows hide user content arrays made only
    of empty/whitespace text blocks while preserving non-empty content.
  - Evidence required: focused structured empty-user test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `5230af34`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_hides_empty_structured_user_content -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`39 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `sessions.history` structured empty-user filtering.
  - Source: `openclaw-main/src/gateway/session-history-state.test.ts`,
    `openclaw-main/src/gateway/chat-display-projection.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected `sessions.history` rows hide user content arrays made
    only of empty/whitespace text blocks while preserving non-empty content.
  - Evidence required: focused sessions structured empty-user test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `e38d7753`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_sessions_history_hides_empty_structured_user_content -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`40 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` structured heartbeat-user filtering.
  - Source: `openclaw-main/src/gateway/chat-display-projection.ts`,
    `openclaw-main/src/auto-reply/heartbeat-filter.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected `chat.history` rows resolve text blocks from
    structured user content arrays before heartbeat prompt filtering.
  - Evidence required: focused structured heartbeat-user test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `0041dded`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_hides_structured_heartbeat_user_content -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`41 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `sessions.history` structured heartbeat-user filtering.
  - Source: `openclaw-main/src/gateway/session-history-state.test.ts`,
    `openclaw-main/src/gateway/chat-display-projection.ts`,
    `openclaw-main/src/auto-reply/heartbeat-filter.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected `sessions.history` rows resolve text blocks from
    structured user content arrays before heartbeat prompt filtering.
  - Evidence required: focused sessions structured heartbeat-user test,
    adjacent transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `8b4c51e5`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_sessions_history_hides_structured_heartbeat_user_content -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`42 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` empty assistant structured content.
  - Source: `openclaw-main/src/gateway/chat-display-projection.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected `chat.history` rows preserve assistant empty content
    arrays while keeping hidden commentary/suppressed rows hidden.
  - Evidence required: focused empty assistant structured-content test,
    adjacent transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `25900ca9`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_preserves_empty_structured_assistant_content -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`43 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` assistant usage/cost sanitizer.
  - Source: `openclaw-main/src/gateway/chat-display-projection.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected `chat.history` assistant metadata retains only known
    numeric usage fields, nested `usage.cost.total`, and top-level
    `cost.total`.
  - Evidence required: focused usage/cost sanitizer test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `3817410c`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_sanitizes_assistant_usage_and_cost_metadata -q`
    (`1 failed` before implementation, then `1 passed`), valid metadata proof
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_preserves_assistant_usage_and_cost_metadata -q`
    (`1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`44 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` internal runtime-context stripping.
  - Source: `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/agents/internal-runtime-context.ts`,
    `openclaw-main/src/gateway/session-history-state.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected `chat.history` text removes legacy internal runtime
    context delimiter blocks before display.
  - Evidence required: focused internal-context stripping test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `b6d1b5b1`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_strips_structured_internal_runtime_context -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`45 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `sessions.history` internal runtime-context stripping.
  - Source: `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/agents/internal-runtime-context.ts`,
    `openclaw-main/src/gateway/session-history-state.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected `sessions.history` structured text/content blocks
    remove legacy internal runtime context delimiter blocks before display.
  - Evidence required: focused sessions internal-context stripping test,
    adjacent transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `b16e8234`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_sessions_history_strips_structured_internal_runtime_context -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`46 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` user envelope/message-id stripping.
  - Source: `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/shared/chat-envelope.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected raw user text strips recognized channel envelope
    headers and standalone message-id hint lines.
  - Evidence required: focused user envelope/message-id test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `e5586d6e`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_strips_user_channel_envelope_and_message_id -q`
    (`1 failed` before implementation, then `1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`47 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` structured user envelope stripping.
  - Source: `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/shared/chat-envelope.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected structured user text strips recognized channel
    envelope headers and standalone message-id hints without corrupting JSON.
  - Evidence required: focused structured user envelope test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `cfec33ca`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_strips_structured_user_channel_envelope -q`
    (`1 failed` before implementation, then `1 passed`), raw/heartbeat
    regression proofs (`2 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`48 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `sessions.history` user envelope/message-id stripping.
  - Source: `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/shared/chat-envelope.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected raw user session rows strip recognized channel
    envelope headers and standalone message-id hint lines.
  - Evidence required: focused sessions envelope/message-id test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `abd535b3`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_sessions_history_strips_user_channel_envelope_and_message_id -q`
    (`1 failed` before implementation, then `1 passed`), structured
    internal-context regression proof (`1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`49 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `sessions.history` structured user envelope stripping.
  - Source: `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/shared/chat-envelope.ts`,
    `openclaw-main/src/gateway/session-history-state.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected structured user session rows strip recognized channel
    envelope headers and standalone message-id hint lines.
  - Evidence required: focused sessions structured envelope test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `0802c431`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_sessions_history_strips_structured_user_channel_envelope -q`
    (`1 failed` before implementation, then `1 passed`), raw/chat structured
    envelope regression proof (`2 passed`), structured internal-context
    regression proof (`1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`50 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` inbound metadata prefix stripping.
  - Source: `openclaw-main/src/auto-reply/reply/strip-inbound-meta.ts`,
    `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/gateway/chat-sanitize.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected raw user chat rows strip OpenClaw-injected inbound
    metadata prefix blocks and weekday timestamp prefixes.
  - Evidence required: focused chat inbound metadata test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `fc562e74`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_strips_inbound_metadata_prefix -q`
    (`1 failed` before implementation, then `1 passed`), envelope regression
    proof (`3 passed`), structured internal-context regression proof
    (`1 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`51 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` inbound sender label projection.
  - Source: `openclaw-main/src/auto-reply/reply/strip-inbound-meta.ts`,
    `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/gateway/chat-sanitize.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected raw user chat rows carry `senderLabel` from inbound
    sender or conversation metadata while hiding the metadata blocks from
    visible content.
  - Evidence required: focused chat sender-label test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `ee8a3679`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_projects_inbound_sender_label -q`
    (`1 failed` before implementation, then `1 passed`),
    inbound-prefix/structured chat regression proof (`3 passed`), sessions
    envelope regression proof (`2 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`52 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `sessions.history` inbound sender label projection.
  - Source: `openclaw-main/src/auto-reply/reply/strip-inbound-meta.ts`,
    `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/gateway/chat-sanitize.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected raw user session rows carry `senderLabel` from inbound
    sender or conversation metadata while hiding the metadata blocks from
    visible content.
  - Evidence required: focused sessions sender-label test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `858df20e`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_sessions_history_projects_inbound_sender_label -q`
    (`1 failed` before implementation, then `1 passed`), chat
    sender/inbound/structured regression proof (`3 passed`), session
    envelope/internal-context regression proof (`2 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`53 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` structured inbound sender label projection.
  - Source: `openclaw-main/src/auto-reply/reply/strip-inbound-meta.ts`,
    `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/gateway/chat-sanitize.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected structured user chat rows carry `senderLabel` from
    inbound metadata inside text/content blocks while hiding the metadata from
    visible content.
  - Evidence required: focused structured chat sender-label test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `666db310`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_projects_structured_inbound_sender_label -q`
    (`1 failed` before implementation, then `1 passed`), raw chat/session
    sender regression proof (`3 passed`), session envelope regression proof
    (`2 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`54 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `sessions.history` structured inbound sender label projection.
  - Source: `openclaw-main/src/auto-reply/reply/strip-inbound-meta.ts`,
    `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/gateway/chat-sanitize.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected structured user session rows carry `senderLabel` from
    inbound metadata inside text/content blocks while hiding the metadata from
    visible content.
  - Evidence required: focused structured sessions sender-label test, adjacent
    transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `22940711`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_sessions_history_projects_structured_inbound_sender_label -q`
    (`1 failed` before implementation, then `1 passed`), chat/session sender
    regression proof (`3 passed`), session envelope regression proof
    (`2 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`55 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` / `sessions.history` runtime-context prompt-preface
  stripping.
  - Source: `openclaw-main/src/agents/internal-runtime-context.ts`,
    `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/gateway/session-history-state.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected user chat rows and session snapshots remove the
    OpenClaw runtime-context prompt-preface headers plus privacy notice before
    returning visible history.
  - Evidence required: focused chat/session runtime-context preface tests,
    adjacent transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `11c597b7`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_strips_internal_runtime_context_prompt_preface tests\test_gateway_node_methods.py::test_sessions_history_strips_internal_runtime_context_prompt_preface -q`
    (`2 failed` before implementation, then `2 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`57 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

- [x] `chat.history` / `sessions.history` legacy runtime-context event
  stripping.
  - Source: `openclaw-main/src/agents/internal-runtime-context.ts`,
    `openclaw-main/src/gateway/chat-sanitize.ts`,
    `openclaw-main/src/gateway/session-history-state.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: projected user chat rows and session snapshots remove legacy
    internal runtime-context event blocks, including untrusted child-result and
    action sections, before returning visible history.
  - Evidence required: focused chat/session legacy runtime-context event tests,
    adjacent transcript/read-model proof, ruff, mypy
  - Status: checkpointed in `dff892b6`
  - Weight: 1
  - Last verified: 2026-05-08, focused red/green
    `python -m pytest tests\test_gateway_node_methods.py::test_chat_history_strips_legacy_internal_runtime_context_event tests\test_gateway_node_methods.py::test_sessions_history_strips_legacy_internal_runtime_context_event -q`
    (`2 failed` before implementation, then `2 passed`), adjacent
    `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_history or sessions_get or sessions_history"`
    (`59 passed, 1175 deselected`), `ruff check
    src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
    `mypy src\openzues\services\gateway_node_methods.py`, and focused
    `git diff --check`.

## Update Rule

Only move a row to `[x]` when implementation, focused proof, adjacent proof,
lint/type checks, ledger update, and checkpoint evidence are all recorded.
