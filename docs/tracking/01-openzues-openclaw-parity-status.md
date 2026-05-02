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
| Repo-wide OpenClaw parity | ~53.5% | Medium | Breadth-weighted planning estimate, not generated metric |
| Active gateway/session/tool-contract family | ~99.0% | High for bounded local path | Does not mean whole product parity |
| Chat/session contract subfamily | ~98.3% | High for bounded local path | Current local session/chat contracts are near complete |
| Browser/canvas/nodes/voice bounded command family | ~99% | High for bounded local path | No longer active queue head |
| Runtime/CLI/doctor native bridge | ~99.9% | High for bounded native bridge | Packaging, ACP bridge depth, installed plugin activation remain |
| CLI/operator control plane | ~99.9% | High for bounded native path | Remaining gaps are plugin import/activation and packaging surfaces |

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
  - Status: verified; checkpoint pending

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
  - Status: open
  - Weight: 5

- [~] Provider-native adapter breadth.
  - Source: OpenClaw channel/provider send, poll, replay, direct announce, media,
    reply, thread, and result metadata behavior.
  - Status: mapped; Slack thread timestamp fallback checkpointed in
    `a461e5eb`; Slack media result checkpointed in `e3b5bbc0`
  - Weight: 3

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
