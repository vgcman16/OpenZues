# OpenZues OpenClaw Parity Status

Agent report source: Gauss

Last updated: 2026-05-02

Primary ledgers:

- `docs/openclaw-parity-progress.md`
- `docs/openclaw-parity-unresolved-seams.md`

Use the progress ledger snapshot as the freshest percentage source. The README
may lag behind this tracker.

## Percentage Rollup

| Family | Percent | Confidence | Notes |
| --- | ---: | --- | --- |
| Repo-wide OpenClaw parity | ~59.1% | Medium | Breadth-weighted planning estimate, not generated metric |
| Active gateway/session/tool-contract family | ~99.6% | High for bounded local path | Does not mean whole product parity |
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
  - Status: verified pending checkpoint

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
  - Status: open
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
    activation checkpointed in `b8f39fe3`, but deeper module import/runtime
    activation remains.
  - Weight: 5

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
    checkpointed in `fb9c9763`
  - Weight: 3

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
