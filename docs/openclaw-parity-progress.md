# OpenClaw Parity Progress

## Snapshot

- Updated: 2026-05-02.
- Estimated repo-wide parity: ~56.5% overall, with a reasonable band of ~49-58%.
- Estimated active gateway/session/tool-contract family parity: ~99.1% for the bounded local OpenZues path.
- Estimated chat/session contract subfamily parity: ~98.3% after the latest `chat.send`, `chat.inject` live-event, `chat.abort`, `sessions.create`, `sessions.patch`, `sessions.pluginPatch`, `sessions.delete`, `sessions.spawn`, sandboxed remote media staging, and `tools.invoke` slices.
- Estimated browser/canvas/nodes/voice bounded-command family parity: ~99%; it is no longer the active queue head.
- Estimated runtime/CLI/doctor native-bridge parity: ~99.9% after the runtime bridge doctor posture, native ACP client interactive replay, secrets reload CLI surface, provider route send/poll alias-precedence, plugin runtime executor inventory, plugin imported-state projection, facade-loaded plugin imported-state preservation, diagnostics-loaded plugin imported-state counts, bundled plugin reported-version normalization, plugin inspect scoped diagnostics, plugin registry inspect/refresh persistence, plugin list registry-source projection, plugin inspect runtime-inspection flag, missing-target static preflight, target-scoped runtime inventory, installed plugin activation-state projection, installed plugin allowlist activation guard, installed plugin slot activation reason, manifest load-path activation-state projection, plugin list verbose activation/import state, plugin list human enabled label, plugin list human enabled count, plugin doctor failure-phase projection, plugin inspect failure-phase projection, plugin inspect failed-at timestamp projection, plugin inspect loader error text projection, plugin inspect human base metadata, plugin inspect human header/bundle-format labels, plugin inspect human capability sections, plugin inspect human runtime surface sections, plugin inspect human tools section, plugin inspect human MCP/LSP sections, plugin inspect human HTTP route count, plugin inspect human policy section, plugin inspect human diagnostics section, plugin inspect human install section, plugin inspect human compatibility warnings section, plugin inspect typed/custom hook sections, doctor workspaceStatus imported-state counts, doctor-contract artifact projection/touched-path narrowing, channel-plugin doctor compatibility/sequence/stale-cleanup/preview/repair/mutable-allowlist/empty-allowlist-extra/empty-group-skip hooks, exec safe-bin coverage/repair/trusted-dir hints, packaged bundled runtime root preference, and manifest command/activation/setup/auth/QA/channel-config/model-support/config-contract/root/package/min-host plus JSON5-capable explicit/manifestless bundle metadata, Claude bundle command projection, bundle MCP/LSP server projection, known Claude marketplace shortcut, remote marketplace listing, remote marketplace path-entry install/update, Git/GitHub entry-source install, URL/archive entry-source install, local path link/copy install, missing local-looking install-spec guard, bundled pre-npm install, explicit and preferred ClawHub install/fallback, production-wired ClawHub API/archive install/update, fakeable plus production-wired npm install/update, npm-not-found bundled fallback, hook-pack npm update, hook-pack npm install fallback, native manifest activation-planner reason projection, active-registry executor projection, and runtime activation doctor posture slices; remaining gaps are packaging/distribution breadth, standalone ACP bridge lifecycle depth, real installed plugin module import/activation, and broader runtime command ergonomics.
- Estimated CLI/operator control-plane parity: ~99.9% after closing the bundle metadata mini-queue, marketplace source-shape install/update queue, native ACP client interactive replay, secrets reload CLI surface, plugin imported-state projection, facade-loaded plugin imported-state preservation, diagnostics-loaded plugin imported-state counts, bundled plugin reported-version normalization, plugin inspect scoped diagnostics, plugin registry inspect/refresh persistence, plugin list registry-source projection, plugin inspect runtime-inspection flag, missing-target static preflight, target-scoped runtime inventory, installed plugin activation-state projection, installed plugin allowlist activation guard, installed plugin slot activation reason, manifest load-path activation-state projection, plugin list verbose activation/import state, plugin list human enabled label, plugin list human enabled count, plugin doctor failure-phase projection, plugin inspect failure-phase projection, plugin inspect failed-at timestamp projection, plugin inspect loader error text projection, plugin inspect human base metadata, plugin inspect human header/bundle-format labels, plugin inspect human capability sections, plugin inspect human runtime surface sections, plugin inspect human tools section, plugin inspect human MCP/LSP sections, plugin inspect human HTTP route count, plugin inspect human policy section, plugin inspect human diagnostics section, plugin inspect human install section, plugin inspect human compatibility warnings section, plugin inspect typed/custom hook sections, doctor workspaceStatus imported-state counts, doctor-contract artifact projection/touched-path narrowing, channel-plugin doctor compatibility/sequence/stale-cleanup/preview/repair/mutable-allowlist/empty-allowlist-extra/empty-group-skip hooks, exec safe-bin coverage/repair/trusted-dir hints, packaged bundled runtime root preference, local path/copy installs, missing local-looking install-spec guard, bundled pre-npm install, explicit/preferred plus production-wired ClawHub API/archive install/update, fakeable plus production-wired npm install/update, npm-not-found bundled fallback, hook-pack npm update, hook-pack npm install fallback, native manifest activation-planner reason projection, active-registry executor projection, and runtime activation doctor posture; remaining CLI gaps are now dominated by real installed plugin module import/activation and packaging surfaces.
- This is a planning rollup, not a generated metric or a claim of feature-complete parity.

## Methodology Note

- Estimates are hand-scored from the primary parity ledger and the unresolved seam queue.
- Repo-wide parity is breadth-weighted. Packaging, companion apps, broader provider runtimes, ACP harness spawning, and full OpenClaw runtime/CLI breadth still keep the overall number below the local gateway/control-plane score.
- Active-family parity tracks the current source-backed gateway/session/tool-contract family, not the whole product.

## Fully Completed / Locked Bounded Slices

These are complete within the bounded OpenZues-local parity contract verified in this repo. They are not a claim that every OpenClaw product behavior is finished.

- Gateway method registry, method policy wiring, strict parameter guards, config lookup/mutation, node invoke guard rails, device pairing, device-token rotation/revoke, plugin approval lifecycle, exec approval lifecycle, and node/global exec approval policy are landed and verified.
- Cron local scheduling now covers expression schedules, due-run detection, delivery status, fallback announcement, session delivery fallback, system-event session-key wake routing, retry/backoff, one-shot cleanup, and OpenClaw-style CLI add/edit schedule parsing.
- Browser/canvas/nodes/voice bounded command coverage is effectively locked for the local bridge: native browser commands, action grammar, storage/cookies/HAR, auth profile login/delete/save, batch execution, dashboard lifecycle, plugin node-host browser command/cap inventory, canvas/A2UI/live reload, APNS wake paths, managed attachments, scoped capability URLs, and iOS provider command bridges all have concrete gateway runtimes or honest unavailable boundaries.
- Chat transcript contracts are locked for the current SQLite-backed store: `chat.history` projection, usage/cost metadata, abort partial metadata, text caps, oversized payload placeholders, untrusted suffix stripping, skip-only hiding, directive cleanup, `chat.send` schema/provenance/timeout/session-key guards, `chat.inject` schema guards, and `chat.abort` run-id plus requester ownership validation.
- Session tool contracts are locked across the bounded local path for `sessions_history`, `session_status`, `sessions_list`, `sessions_send`, `sessions_yield`, `sessions.create`, `sessions.patch`, `sessions.pluginPatch`, `sessions.delete`, `sessions.preview`, and direct session-history REST/SSE behavior.
- Custom-agent control-plane ownership is landed for persisted agent create/update/delete, identity lookup, workspace file ownership, session creation/filtering, alias resolution, and deleted-agent send/steer guards.
- `tools.invoke` core bridge is landed for allow/deny policy, owner-only controls, before-call hooks, ordered registry-backed plugin runtime service envelopes, safe core mappings, plugin error projection, plugin-published `tools.catalog` and `tools.effective` groups, plugin-host `plugins.uiDescriptors` control UI descriptor projection, and OpenClaw-style projection/visibility for neighboring session tools.
- Native runtime seams are now landed for ACP spawn dispatch/tracking plus delete/reset cleanup, app-wired sandbox-required child-turn dispatch through Codex app-server workspace-write policy, route-backed thread-bound spawn binding, shared provider-native send metadata, and Telegram native document/reply/silent/thread payloads.
- TTS control-plane parity now includes `tts.personas`, `tts.setPersona`,
  status persona projection, config/fakeable persona descriptors, prefs-backed
  selected persona persistence, and JSON-capable `capability` / `infer` Typer
  commands for listing and setting personas.
- Realtime voice gateway parity now includes `talk.realtime.session`,
  `talk.realtime.relayAudio`, `talk.realtime.relayMark`,
  `talk.realtime.relayStop`, and `talk.realtime.relayToolResult` over a
  fakeable runtime adapter, with OpenClaw-shaped unavailable errors when no
  realtime provider/relay runtime is wired.
- Channel runtime control now includes `channels.stop` as an admin-scoped,
  idempotent native stop boundary with normalized channel/account projection.
- Node pairing lifecycle parity now includes `node.pair.remove` as a
  pairing-scoped removal boundary that revokes paired nodes, returns
  `{nodeId}`, and publishes the OpenClaw-shaped `node.pair.resolved` removal
  event.
- Provider-native Slack route parity now validates Slack `thread_ts` values
  before setting `thread_ts`, falls back from internal reply ids to valid Slack
  thread ids, and leaves invalid internal ids out of Slack API payloads.
- Provider-native Slack media parity now iterates multi-media uploads with the
  caption on the first upload, returns the final media id as `messageId`, and
  preserves the ordered `mediaIds`/`mediaUrls` result metadata.
- Provider-native Discord webhook parity now sends `threadId` as the webhook
  execution query parameter `thread_id`, keeps `wait=true` in the URL, and
  leaves reply message references plus silent flags in the JSON body without a
  body-level `thread_id`.
- Provider-native WhatsApp document parity now derives and includes document
  filenames from outbound media URLs while preserving reply context and split
  media delivery behavior.
- Provider-native Discord media parity now follows OpenClaw's shared outbound
  media sequence contract with one webhook send per media URL, text only on the
  first media send, final-id projection, and ordered provider `messageIds`.
- Sandboxed `chat.send` now stages managed path-backed inbound media that the
  app/API already persisted as `openzuesSavedPath`, copying the file into the
  child workspace's `media/inbound` directory and rewriting the runtime
  attachment metadata to sandbox-relative media refs.
- Verified the sandbox saved-path media slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k "saved_path_attachment_stages"` (`1
  passed`), adjacent sandbox attachment proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sandboxed_attachment_stages_media_in_session_workspace or
  saved_path_attachment_stages"` (`5 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py`.
- Runtime-control `sessions.pluginPatch` now mirrors OpenClaw's registered
  plugin session extension mutation path: the method is admin-only, rejects
  unregistered plugin/namespace pairs, validates plugin JSON values with the
  upstream depth/node/string/byte limits, persists extension state by plugin id
  and namespace, projects registered extension values on session rows, and
  removes state on explicit `unset=true`.
- Verified the `sessions.pluginPatch` slice with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_plugin_patch_persists_registered_extension_state
  -q` (`1 passed`), adjacent session-control proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_plugin_patch or
  sessions_patch or sessions_resolve"` (`27 passed`), `ruff check
  src\openzues\services\gateway_plugin_runtime.py
  src\openzues\services\gateway_sessions.py
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_plugin_runtime.py
  src\openzues\services\gateway_sessions.py
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py`.
- Plugin-host `plugins.uiDescriptors` now mirrors OpenClaw's active-registry
  control UI descriptor gateway method: params must be `{}`, descriptors come
  from the fakeable plugin runtime registry, projected rows are stamped with
  registry-owned `pluginId` and optional `pluginName`, JSON-compatible
  descriptor schemas and valid required scopes are preserved, and invalid or
  disabled descriptor registrations are skipped before clients see them. This
  slice is checkpointed in `9fb5098b`.
- Verified the `plugins.uiDescriptors` slice with `python -m pytest
  tests\test_gateway_node_methods.py::test_plugins_ui_descriptors_returns_registered_control_ui_descriptors
  -q` (`1 passed`), adjacent plugin-runtime proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k "plugins_ui_descriptors or
  tools_invoke_uses_plugin_runtime or tools_invoke_runs_registry_plugin_executor
  or tools_invoke_keeps_registry_owner_only or sessions_plugin_patch"` (`5
  passed`), `ruff check src\openzues\services\gateway_plugin_runtime.py
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_plugin_runtime.py
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py`.
- Plugin runtime activation doctor parity now mirrors OpenClaw's manifest
  activation planner reason vocabulary for installed manifests: `plugins
  doctor --json` projects activation plans for command aliases, providers,
  setup providers, agent harnesses, channels, routes, and capability triggers,
  including the upstream-shaped `activation-*` and `manifest-*` reason strings
  without importing the TypeScript plugin runtime. This slice is checkpointed
  in `721ec0f2`.
- Verified the plugin activation-plan slice with `python -m pytest
  tests\test_cli.py::test_plugins_doctor_json_projects_manifest_activation_plan_reasons
  -q` (`1 passed`), service reason-plan proof `python -m pytest
  tests\test_gateway_plugin_activation.py::test_resolve_manifest_activation_plan_projects_reason_entries
  -q` (`1 passed`), adjacent plugin CLI proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_doctor_json_reports_metadata_only_tool_activation or
  plugins_doctor_json_projects_manifest_activation_plan_reasons or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_projects_runtime_executor_inventory or
  plugins_list_json_marks_runtime_executor_plugins_imported"` (`5 passed`),
  adjacent activation service proof `python -m pytest
  tests\test_gateway_plugin_activation.py -q` (`4 passed`), `ruff check`, and
  `mypy src\openzues\cli.py
  src\openzues\services\gateway_plugin_activation.py`.
- Plugin registry inspect/refresh CLI parity now mirrors OpenClaw's `plugins
  registry` command: `plugins registry --json` compares the current native
  manifest/load-path inventory with a persisted settings index and reports
  `missing`, `fresh`, or `stale` plus refresh reasons, while `plugins registry
  --refresh --json` writes the current index and returns the refreshed
  registry payload. This slice is checkpointed in `cdb3035e`.
- Verified the plugin registry slice with `python -m pytest
  tests\test_cli.py::test_plugins_registry_json_reports_missing_persisted_registry
  -q` (`1 passed`), `python -m pytest
  tests\test_cli.py::test_plugins_registry_refresh_json_persists_current_index
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_registry or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_doctor_json_projects_manifest_activation_plan_reasons"` (`4
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin list persisted-registry source projection now mirrors OpenClaw's
  `plugins list --json` registry block: the native list payload reports
  `registry.source` as `persisted` after a fresh registry refresh, and reports
  OpenClaw-shaped derived-source diagnostics when the persisted index is
  missing or stale.
  This slice is checkpointed in `6468e305`.
- Verified the plugin list registry-source slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_reports_persisted_registry_source_after_refresh
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_registry or
  plugins_list_json_reports_persisted_registry_source_after_refresh or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_doctor_json_projects_manifest_activation_plan_reasons or
  plugins_list_json_discovers_openclaw_manifest_load_paths"` (`6 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect runtime-inspection flag parity now mirrors OpenClaw's
  `plugins inspect --runtime` operator surface: the flag is accepted by
  `inspect` and `info`, runtime inspection is explicit, and loaded non-bundle
  metadata rows are marked imported only in that native runtime-inspection
  posture. This slice is checkpointed in `5fce4371`.
- Verified the plugin inspect runtime flag slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_runtime_json_uses_runtime_loaded_import_state
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_runtime_json_uses_runtime_loaded_import_state or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_list_json_marks_runtime_executor_plugins_imported or
  plugins_list_json_projects_runtime_executor_inventory or
  plugins_doctor_json_reports_metadata_only_tool_activation"` (`6 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect runtime missing-target preflight now mirrors OpenClaw's guard
  that checks the static plugin snapshot before runtime inspection: missing
  targets return `Plugin not found` without entering the runtime-inspection
  inventory path.
  This slice is checkpointed in `9a9e89f2`.
- Verified the missing-target runtime inspect slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_runtime_missing_target_uses_static_inventory
  -q` (`1 passed`), focused runtime inspect pair (`2 passed`), adjacent
  `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_runtime_json_uses_runtime_loaded_import_state or
  plugins_inspect_runtime_missing_target_uses_static_inventory or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_list_json_marks_runtime_executor_plugins_imported or
  plugins_list_json_projects_runtime_executor_inventory or
  plugins_doctor_json_reports_metadata_only_tool_activation"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect runtime target-scoped inventory now mirrors OpenClaw's
  `buildPluginDiagnosticsReport({ onlyPluginIds })` inspect path: after static
  target preflight, the native runtime-inspection inventory is filtered to the
  requested plugin id.
  This slice is checkpointed in `c412b98b`.
- Verified the scoped runtime inspect slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_runtime_scopes_runtime_inventory_to_target
  -q` (`1 passed`), focused runtime inspect trio (`3 passed`), adjacent
  `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_runtime_json_uses_runtime_loaded_import_state or
  plugins_inspect_runtime_missing_target_uses_static_inventory or
  plugins_inspect_runtime_scopes_runtime_inventory_to_target or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_list_json_marks_runtime_executor_plugins_imported or
  plugins_list_json_projects_runtime_executor_inventory or
  plugins_doctor_json_reports_metadata_only_tool_activation"` (`8 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Installed plugin activation-state projection now mirrors OpenClaw's
  activation decision fields for config/install-backed plugin records:
  `plugins list --json` includes `activated`, `explicitlyEnabled`,
  `activationSource`, and `activationReason`, and globally disabled plugin
  activation turns an explicitly enabled installed record into a disabled row.
  This slice is checkpointed in `78658f29`.
- Verified the installed activation-state slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_projects_installed_plugin_activation_state
  -q` (`1 passed`), adjacent plugin config/install list and doctor proof
  (`6 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Installed plugin allowlist activation now mirrors OpenClaw's authoritative
  `plugins.allow` guard for config/install-backed plugin records: explicitly
  enabled installed plugins outside the allowlist project disabled activation
  state with `activationReason="not in allowlist"` while preserving
  `explicitlyEnabled=true`.
  This slice is checkpointed in `73089117`.
- Verified the installed allowlist activation slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_keeps_installed_plugin_allowlist_authoritative
  -q` (`1 passed`), adjacent plugin config/install list and doctor proof
  (`7 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Installed plugin slot activation reasons now mirror OpenClaw's explicit slot
  selection path: `plugins.slots.memory` and `plugins.slots.contextEngine`
  activate matching config/install-backed plugin records before the allowlist
  guard and project upstream reasons such as `selected memory slot`.
  This slice is checkpointed in `209dced0`.
- Verified the installed slot activation slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_projects_installed_plugin_slot_activation_reason
  -q` (`1 passed`), adjacent plugin config/install list and doctor proof
  (`8 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- TTS persona gateway/CLI methods now mirror OpenClaw's
  `tts.personas`/`tts.setPersona` contract: configured personas are projected
  with `id`, `label`, `description`, `provider`, `fallbackPolicy`, and
  provider-binding ids, selected persona state persists with TTS prefs,
  `off`/`none`/`default` clears the selection, unknown personas return the
  upstream-shaped invalid-persona error, and `capability tts personas` /
  `capability tts set-persona` share the gateway runtime. This slice is
  checkpointed in `3819d03a`.
- Verified the TTS persona slice with focused gateway persona tests (`2
  passed`), focused policy test (`1 passed`), focused CLI tests (`2 passed`),
  adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "tts_"`
  (`9 passed`), adjacent `python -m pytest tests\test_cli.py -q -k "tts_"`
  (`11 passed`), adjacent `python -m pytest tests\test_gateway_nodes_api.py
  -q -k "tts"` (`6 passed`), `ruff check
  src\openzues\services\gateway_tts.py
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py src\openzues\cli.py
  tests\test_gateway_node_methods.py tests\test_gateway_method_policy.py
  tests\test_cli.py`, and `mypy src\openzues\services\gateway_tts.py
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py src\openzues\cli.py`.
- Realtime voice gateway methods now mirror OpenClaw's gateway method layer:
  session creation and relay operations validate the same params, dispatch to
  a registered native realtime adapter, return `{ok: true}` relay results, and
  keep precise unavailable responses for missing provider/relay runtime. This
  slice is checkpointed in `75d03a6c`.
- Verified the realtime voice gateway slice with focused gateway tests (`2
  passed`), focused talk/TTS policy tests (`2 passed`), adjacent `python -m
  pytest tests\test_gateway_node_methods.py -q -k "talk_realtime or talk_speak
  or talk_config"` (`6 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py
  tests\test_gateway_node_methods.py tests\test_gateway_method_policy.py`, and
  `mypy src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py`. A broader policy selection
  exposed unrelated existing gaps for `channels.stop` and `node.pair.remove`.
- `channels.stop` now mirrors OpenClaw's gateway method layer: admin scope,
  strict `channel`/`accountId` params, channel normalization, invalid-channel
  errors, and idempotent `{channel, accountId, stopped: true}` native stop
  projection. This slice is checkpointed in `64f6937a`.
- Verified the `channels.stop` slice with focused gateway stop tests (`2
  passed`), focused channel policy test (`1 passed`), adjacent `python -m
  pytest tests\test_gateway_node_methods.py -q -k "channels_stop or
  channels_start or channels_logout"` (`7 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py
  tests\test_gateway_node_methods.py tests\test_gateway_method_policy.py`, and
  `mypy src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py`.
- `node.pair.remove` now mirrors OpenClaw's gateway method layer: pairing
  scope, strict `nodeId` params, paired-node removal through the native pairing
  store, `{nodeId}` response projection, unknown-node errors, and
  `node.pair.resolved` broadcasts with `decision="removed"`. This slice is
  checkpointed in `8a0e6ac6`.
- Verified the `node.pair.remove` slice with focused gateway remove tests (`2
  passed`), focused node/voice policy test (`1 passed`), adjacent `python -m
  pytest tests\test_gateway_node_methods.py -q -k "node_pair_remove or
  node_pair_approve or node_pair_reject or node_pair_list or node_pair_request
  or node_pair_verify or node_rename"` (`13 passed`), `ruff check
  src\openzues\services\gateway_node_pairing.py
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py
  tests\test_gateway_node_methods.py tests\test_gateway_method_policy.py`, and
  `mypy src\openzues\services\gateway_node_pairing.py
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_method_policy.py`.
- Native configured ACP binding helpers now mirror OpenClaw's
  `persistent-bindings.types.ts` and `persistent-bindings.lifecycle.ts`
  key/record/parse/resolve/ensure contract: session keys use the
  16-character SHA-256 hash of
  `channel:accountId:conversationId`, config-sourced binding records persist
  `targetKind="session"`, `boundAt=0`, conversation ids, and ACP metadata, and
  stored records can be parsed back into normalized configured binding specs.
  The fakeable native lifecycle adapter now keeps matching ready ACP sessions,
  closes/reinitializes mismatched or errored sessions, and initializes runtime
  sessions with the configured ACP harness agent override. Native reset-in-place
  handling now clears metadata for configured ACP binding sessions so the next
  turn can recreate them, keeps metadata for ordinary ACP binding sessions, and
  treats configured bindings with no ACP metadata as already reset. The native
  resolver now also materializes top-level `type="acp"` `bindings[]` config
  entries into configured ACP binding specs/records, prefers exact accounts
  over wildcard bindings, and resolves configured ACP session keys back to the
  matching config-derived spec.
- Verified the configured ACP binding helper slice with `python -m pytest
  tests\test_acp_persistent_bindings.py -q` (`14 passed`), adjacent ACP spawn
  proof `python -m pytest tests\test_acp_persistent_bindings.py
  tests\test_gateway_acp_spawn.py -q` (`33 passed`), adjacent gateway ACP
  proof `python -m pytest tests\test_gateway_node_methods.py -q -k "acp and
  thread"` (`7 passed`), `ruff check
  src\openzues\services\acp_persistent_bindings.py
  tests\test_acp_persistent_bindings.py`, and `mypy
  src\openzues\services\acp_persistent_bindings.py`.
- Route-backed thread-bound spawn binding now includes LINE current-conversation
  routes. The shared binder accepts LINE notification route views, keeps the
  provider target for delivery, and stores normalized LINE conversation ids in
  the persisted `sessionBinding` record. The native CLI now accepts
  `routes create --kind line`, applies default `gateway/send` and
  `gateway/poll` subscriptions, and persists LINE conversation targets for that
  route-backed binder path. The native gateway channel API now classifies LINE
  as a known route channel with the upstream `LINE` label, and the web
  notification-route form exposes LINE with gateway send/poll default events.
  Matrix route-backed child-thread binders are now configurable through the
  native CLI and web/API operator surfaces as native gateway send/poll routes.
  Native Zalo direct/media send routes are now configurable through the same
  CLI and web/API route setup surfaces.
- Verified the LINE route-backed binder slice with `python -m pytest
  tests\test_gateway_thread_binding.py -k "line_current_conversation" -q` (`1
  passed`), full binder proof `python -m pytest tests\test_gateway_thread_binding.py
  -q` (`5 passed`), adjacent route-backed spawn proof `python -m pytest
  tests\test_gateway_node_methods.py -k "thread_mode_uses_route_backed_thread_binder
  or thread_mode_uses_matrix_route_backed_thread_binder or
  thread_mode_delivers_initial_child_run_to_bound_origin" -q` (`3 passed`),
  `ruff check src\openzues\services\gateway_thread_binding.py
  src\openzues\schemas.py tests\test_gateway_thread_binding.py`, and `mypy
  src\openzues\services\gateway_thread_binding.py src\openzues\schemas.py`.
- Verified the LINE route-create CLI slice with `python -m pytest
  tests\test_cli.py -k
  "routes_create_command_accepts_line_current_conversation_route" -q` (`1
  passed`), adjacent route-create proof `python -m pytest tests\test_cli.py -k
  "routes_create_command_productizes_native_provider_routes or
  routes_create_command_accepts_line_current_conversation_route" -q` (`2
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Verified the LINE web/API operator-surface slice with `python -m pytest
  tests\test_app.py -k
  "gateway_channels_endpoint_classifies_line_native_route or
  notification_route_operator_form_offers_line_native_routes" -q` (`2
  passed`), adjacent channel endpoint proof `python -m pytest tests\test_app.py
  -k "gateway_channels_endpoint or
  notification_route_operator_form_offers_line_native_routes" -q` (`3
  passed`), `ruff check src\openzues\services\gateway_channels.py
  tests\test_app.py`, and `mypy src\openzues\services\gateway_channels.py`.
- Verified the Matrix route setup slice with `python -m pytest
  tests\test_cli.py -k "routes_create_command_accepts_matrix_thread_route" -q`
  (`1 passed`), `python -m pytest tests\test_app.py -k
  "gateway_channels_endpoint_classifies_matrix_native_route or
  notification_route_operator_form_offers_matrix_native_routes" -q` (`2
  passed`), adjacent route/channel/binder proof `python -m pytest
  tests\test_cli.py -k "routes_create_command_productizes_native_provider_routes
  or routes_create_command_accepts_line_current_conversation_route or
  routes_create_command_accepts_matrix_thread_route" -q` (`3 passed`),
  `python -m pytest tests\test_app.py -k "gateway_channels_endpoint or
  notification_route_operator_form_offers_line_native_routes or
  notification_route_operator_form_offers_matrix_native_routes" -q` (`5
  passed`), `python -m pytest tests\test_gateway_thread_binding.py -k
  "matrix_provider_thread or line_current_conversation" -q` (`2 passed`),
  `ruff check src\openzues\cli.py src\openzues\services\gateway_channels.py
  tests\test_cli.py tests\test_app.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_channels.py`.
- Verified the Zalo route setup slice with `python -m pytest
  tests\test_cli.py -k "routes_create_command_accepts_zalo_native_route" -q`
  (`1 passed`), `python -m pytest tests\test_app.py -k
  "gateway_channels_endpoint_classifies_zalo_native_route or
  notification_route_operator_form_offers_zalo_native_routes" -q` (`2
  passed`), adjacent route/channel/runtime proof `python -m pytest
  tests\test_cli.py -k "routes_create_command_productizes_native_provider_routes
  or routes_create_command_accepts_line_current_conversation_route or
  routes_create_command_accepts_matrix_thread_route or
  routes_create_command_accepts_zalo_native_route or
  channels_capabilities_json_reports_zalo_support" -q` (`5 passed`),
  `python -m pytest tests\test_app.py -k "gateway_channels_endpoint or
  notification_route_operator_form_offers_line_native_routes or
  notification_route_operator_form_offers_matrix_native_routes or
  notification_route_operator_form_offers_zalo_native_routes" -q` (`7
  passed`), `python -m pytest tests\test_ops_mesh.py -k
  "notification_route_create_accepts_zalo_native_route or
  uses_zalo_native_route or splits_zalo_media" -q` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_channels.py
  tests\test_cli.py tests\test_app.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_channels.py`.
- Native LINE route-backed direct sends now dispatch through LINE's Bot API
  push endpoint with OpenClaw's target normalization, HTTPS image media payload
  shape, text payload shape, five-message batching, bearer-token auth, and
  provider metadata persistence.
- Verified the LINE native-send slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "line_native_route"` (`1 passed`), adjacent
  provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "direct_channel_message or route_provider_send or route_provider_poll or
  gateway_send or gateway_poll or replay_outbound_deliveries"` (`44 passed`),
  `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and
  `mypy src\openzues\services\ops_mesh.py`.
- Native Matrix route-backed direct text sends now dispatch through Matrix
  Client-Server `m.room.message` events with OpenClaw's room target
  normalization, reply/thread relation payload, 4000-character text splitting,
  bearer-token auth, and ordered event-id metadata persistence.
- Verified the Matrix native-send slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_native_route"` (`1 passed`), adjacent
  provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "line_native_route or matrix_native_route or direct_channel_message or
  route_provider_send or route_provider_poll or gateway_send or gateway_poll or
  replay_outbound_deliveries"` (`45 passed`), `ruff check
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- Native Matrix route-backed polls now dispatch OpenClaw-style `m.poll.start`
  events with disclosed/undisclosed max-selection handling, answer ids,
  fallback text, thread relation metadata, bearer-token auth, and `pollId`
  provider metadata.
- Verified the Matrix native-poll slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_native_route"` (`2 passed`), adjacent
  provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "matrix_native_route or line_native_route or direct_channel_message or
  route_provider_send or route_provider_poll or gateway_send or gateway_poll or
  replay_outbound_deliveries"` (`46 passed`), `ruff check
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- Matrix `message.action send` now maps through the native provider route,
  preserving OpenClaw's `send` / `sendMessage` action aliases, `message` /
  `content` text aliases, reply/thread metadata, guarded media aliases, and
  idempotency key as the Matrix transaction id.
- Verified the Matrix action-send slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_send_route"` (`1 passed`), adjacent
  action/provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_matrix_send_route or
  message_action_dispatches_zalo_send_route or
  message_action_dispatches_zalo_send_media_route or matrix_native_route or
  message_action_dispatches_discord_send_route or
  message_action_dispatches_slack_send_route or
  message_action_dispatches_telegram_send_document_alias or
  message_action_dispatches_whatsapp_send_document_reply"` (`9 passed`),
  `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and
  `mypy src\openzues\services\ops_mesh.py`.
- Native `routes send` / `routes poll` now accept OpenClaw-compatible outbound
  CLI aliases: `routes send --media` maps to the same native media list as
  `--media-url`, and both send/poll accept `--thread-id` alongside
  `--thread`.
- Verified the provider CLI alias slice with `python -m pytest
  tests\test_cli.py -k "openclaw_media_and_thread_id_aliases or
  openclaw_thread_id_alias" -q` (`2 passed`), adjacent route send/poll CLI
  proof `python -m pytest tests\test_cli.py -k
  "routes_send_json_calls_native_direct_send_runtime or
  routes_send_accepts_openclaw_media_and_thread_id_aliases or
  routes_poll_human_output_calls_native_direct_poll_runtime or
  routes_poll_accepts_openclaw_thread_id_alias" -q` (`4 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Native `routes poll` now also accepts the OpenClaw poll option spellings:
  `--poll-question`, repeatable `--poll-option`, `--poll-multi`,
  `--poll-duration-seconds`, `--poll-duration-hours`, and
  `--poll-anonymous` / `--poll-public`.
- Verified the poll CLI alias slice with `python -m pytest tests\test_cli.py
  -k "openclaw_poll_option_aliases" -q` (`1 passed`), adjacent route poll CLI
  proof `python -m pytest tests\test_cli.py -k
  "routes_poll_human_output_calls_native_direct_poll_runtime or
  routes_poll_accepts_openclaw_thread_id_alias or
  routes_poll_accepts_openclaw_poll_option_aliases" -q` (`3 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Matrix route-backed thread-bound subagent bindings now persist
  OpenClaw's bundled child-placement default in `sessionBinding.metadata`, and
  the gateway `sessions.spawn` path preserves that metadata on the child
  session.
- Verified the Matrix child-placement metadata slice with `python -m pytest
  tests\test_gateway_thread_binding.py -k "matrix_provider_thread" -q` (`1
  passed`), full binder proof `python -m pytest tests\test_gateway_thread_binding.py
  -q` (`5 passed`), adjacent gateway spawn proof `python -m pytest
  tests\test_gateway_node_methods.py -k
  "thread_mode_uses_matrix_route_backed_thread_binder or
  thread_mode_uses_route_backed_thread_binder or
  thread_mode_delivers_initial_child_run_to_bound_origin" -q` (`3 passed`),
  `ruff check src\openzues\services\gateway_thread_binding.py
  tests\test_gateway_thread_binding.py tests\test_gateway_node_methods.py`, and
  `mypy src\openzues\services\gateway_thread_binding.py`.
- ACP `sessions.spawn streamTo="parent"` now uses the full accepted-run
  tracking path: OpenZues persists the child session metadata, stores
  `streamTo` / `streamLogPath`, registers the run for `agent.wait`, applies
  terminal cleanup, and preserves the parent completion announcement while
  returning the stream log/note envelope. The RuntimeManager ACP adapter now
  also rejects `streamTo="parent"` without requester session context before
  starting any runtime thread.
- Verified the ACP parent-stream tracking slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_acp_stream_to_parent_tracks_child_run"` (`1 passed`) and
  `python -m pytest tests\test_gateway_acp_spawn.py -k
  "rejects_parent_stream_without_requester" -q` (`1 passed`),
  adjacent ACP pack `python -m pytest tests\test_gateway_node_methods.py
  tests\test_gateway_acp_spawn.py -q -k "sessions_spawn_acp or acp_spawn or
  agent_wait_applies_spawn_cleanup_delete_on_terminal_child_run or
  agent_wait_announces_spawn_completion_to_parent_session"` (`12 passed`),
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py tests\test_gateway_acp_spawn.py`, and
  `mypy src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_acp_spawn.py`.
- RuntimeManager-backed ACP child turns now prepend OpenClaw's prompt cwd
  presentation line when `cwd` is present, including home-directory redaction
  to `~` and preservation of Windows backslash separators.
- Verified the ACP prompt cwd presentation slice with `python -m pytest
  tests\test_gateway_acp_spawn.py -q -k
  "prefixes_cwd_like_openclaw"` (`1 passed`), full ACP adapter proof
  `python -m pytest tests\test_gateway_acp_spawn.py -q` (`6 passed`),
  adjacent gateway ACP spawn proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_spawn_acp"` (`5
  passed`), `ruff check src\openzues\services\gateway_acp_spawn.py
  tests\test_gateway_acp_spawn.py`, and `mypy
  src\openzues\services\gateway_acp_spawn.py`.
- RuntimeManager-backed ACP accepted payloads now include OpenClaw's
  mode-specific accepted notes: ordinary run spawns return the isolated-session
  follow-up note, while `mode="session"` / `thread=true` spawns return the
  persistent in-thread follow-up note.
- Verified the ACP accepted-note slice with `python -m pytest
  tests\test_gateway_acp_spawn.py -q -k "accepted_note"` (`2 passed`), full
  ACP adapter proof `python -m pytest tests\test_gateway_acp_spawn.py -q` (`8
  passed`), adjacent gateway ACP spawn proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_spawn_acp"` (`5
  passed`), `ruff check src\openzues\services\gateway_acp_spawn.py
  tests\test_gateway_acp_spawn.py`, and `mypy
  src\openzues\services\gateway_acp_spawn.py`.
- RuntimeManager-backed ACP `thread=true` session spawns now synthesize
  OpenClaw-shaped current-conversation binding metadata for current-placement
  provider contexts such as LINE: accepted responses include `threadBinding`,
  `sessionBinding` with `targetKind="session"` / `placement="current"`, and
  `completionDelivery` for the bound provider target. LINE group/current
  contexts now also prefer `agentGroupId` over the direct sender target, so
  group replies bind and deliver to the current group conversation. The
  gateway method owner now preserves LINE as a routable channel context and
  forwards requester group ids into the production ACP adapter only when present.
- Verified the ACP current-conversation binding slice with `python -m pytest
  tests\test_gateway_acp_spawn.py -k "binds_line_current_conversation or
  prefers_line_group_current_conversation" -q` (`2 passed`), full ACP adapter
  proof `python -m pytest
  tests\test_gateway_acp_spawn.py -q` (`11 passed`), adjacent gateway ACP
  proof `python -m pytest tests\test_gateway_node_methods.py -k
  "acp_thread_mode_passes_group_context or
  sessions_spawn_acp_thread_mode_persists_session_binding_metadata or
  sessions_spawn_acp_thread_mode_uses_channel_default_account or
  sessions_spawn_acp_thread_mode_uses_target_agent_bound_account or
  sessions_spawn_acp_runtime_tracks_wait_cleanup_and_completion" -q` (`5
  passed`), `ruff check src\openzues\services\gateway_acp_spawn.py
  tests\test_gateway_acp_spawn.py`, and `mypy
  src\openzues\services\gateway_acp_spawn.py`.
- RuntimeManager-backed ACP `thread=true` session spawns now also synthesize
  OpenClaw-shaped child-placement binding metadata for Matrix requester
  contexts. Accepted responses include `threadBinding`, `completionDelivery`,
  and `sessionBinding` records with `placement="child"`, the native ACP runtime
  thread id as the local child-thread handle, the parent Matrix room preserved
  with canonical casing, and the requester thread id recorded as
  `parentThreadId`.
- Verified the ACP Matrix child-thread metadata slice with `python -m pytest
  tests\test_gateway_acp_spawn.py -k "matrix_child_thread_metadata" -q` (`1
  passed`), full ACP adapter proof `python -m pytest
  tests\test_gateway_acp_spawn.py -q` (`13 passed`), adjacent gateway ACP
  proof `python -m pytest tests\test_gateway_node_methods.py -k
  "sessions_spawn_acp_thread_mode_persists_session_binding_metadata or
  sessions_spawn_acp_thread_mode_uses_channel_default_account or
  sessions_spawn_acp_thread_mode_uses_target_agent_bound_account or
  sessions_spawn_acp_runtime_tracks_wait_cleanup_and_completion" -q` (`4
  passed`), `ruff check src\openzues\services\gateway_acp_spawn.py
  tests\test_gateway_acp_spawn.py`, and `mypy
  src\openzues\services\gateway_acp_spawn.py`.
- Matrix ACP child-placement delivery now mirrors OpenClaw's Matrix delivery
  resolver for top-level room targets: requester `channel:<room>` contexts are
  delivered back as `room:<room>` while the child ACP runtime thread id remains
  the local thread handle in `threadBinding` and `completionDelivery`.
- Verified the Matrix ACP top-level delivery target slice with `python -m
  pytest tests\test_gateway_acp_spawn.py -k "matrix_top_level_delivery_target"
  -q` (`1 passed`), full ACP adapter proof `python -m pytest
  tests\test_gateway_acp_spawn.py -q` (`14 passed`), adjacent gateway ACP proof
  `python -m pytest tests\test_gateway_node_methods.py -k
  "sessions_spawn_acp_thread_mode_persists_session_binding_metadata or
  sessions_spawn_acp_thread_mode_uses_channel_default_account or
  sessions_spawn_acp_thread_mode_uses_target_agent_bound_account or
  sessions_spawn_acp_runtime_tracks_wait_cleanup_and_completion" -q` (`4
  passed`), `ruff check src\openzues\services\gateway_acp_spawn.py
  tests\test_gateway_acp_spawn.py`, and `mypy
  src\openzues\services\gateway_acp_spawn.py`.
- Discord ACP child-placement delivery now mirrors OpenClaw's child-channel
  fallback for newly bound threads: accepted `threadBinding` and
  `completionDelivery` target `channel:<child-runtime-thread>` instead of the
  requester parent channel, while the parent channel remains on the
  `sessionBinding` conversation as context.
- Verified the Discord ACP child delivery target slice with `python -m pytest
  tests\test_gateway_acp_spawn.py -k "discord_child_delivery_target" -q` (`1
  passed`), adjacent ACP child-target proof `python -m pytest
  tests\test_gateway_acp_spawn.py -k "matrix_child_thread_metadata or
  matrix_top_level_delivery_target or discord_child_delivery_target" -q` (`3
  passed`), full ACP adapter proof `python -m pytest
  tests\test_gateway_acp_spawn.py -q` (`15 passed`), adjacent gateway ACP proof
  `python -m pytest tests\test_gateway_node_methods.py -k
  "sessions_spawn_acp_thread_mode_persists_session_binding_metadata or
  sessions_spawn_acp_thread_mode_uses_channel_default_account or
  sessions_spawn_acp_thread_mode_uses_target_agent_bound_account or
  sessions_spawn_acp_runtime_tracks_wait_cleanup_and_completion" -q` (`4
  passed`), `ruff check src\openzues\services\gateway_acp_spawn.py
  tests\test_gateway_acp_spawn.py`, and `mypy
  src\openzues\services\gateway_acp_spawn.py`.
- RuntimeManager-backed ACP thread-binding records now carry OpenClaw-shaped
  intro metadata. `sessionBinding.metadata` includes `threadName`,
  `introText`, optional `label`, and the runtime cwd line when `cwd` is present,
  matching the upstream thread intro banner contract while staying native to the
  Codex app-server runtime.
- Verified the ACP cwd intro metadata slice with `python -m pytest
  tests\test_gateway_acp_spawn.py -k "cwd_in_thread_binding_intro" -q` (`1
  passed`), full ACP adapter proof `python -m pytest
  tests\test_gateway_acp_spawn.py -q` (`16 passed`), adjacent gateway ACP proof
  `python -m pytest tests\test_gateway_node_methods.py -k
  "sessions_spawn_acp_thread_mode_persists_session_binding_metadata or
  sessions_spawn_acp_thread_mode_uses_channel_default_account or
  sessions_spawn_acp_thread_mode_uses_target_agent_bound_account or
  sessions_spawn_acp_runtime_tracks_wait_cleanup_and_completion" -q` (`4
  passed`), `ruff check src\openzues\services\gateway_acp_spawn.py
  tests\test_gateway_acp_spawn.py`, and `mypy
  src\openzues\services\gateway_acp_spawn.py`.
- Gateway ACP spawns now inherit the target custom agent workspace when `cwd`
  is omitted, matching OpenClaw's cross-agent ACP workspace resolution. Missing
  inherited workspaces fall back to the ACP backend default cwd, while
  non-missing access failures return `errorCode="cwd_resolution_failed"` before
  runtime dispatch.
- Verified the ACP cwd inheritance seam with `python -m pytest
  tests\test_gateway_node_methods.py -k "acp_inherits_target_agent_workspace
  or acp_omits_missing_inherited_target_workspace or
  acp_reports_inherited_workspace_access_failure" -q` (`3 passed`), adjacent
  ACP gateway coverage `python -m pytest tests\test_gateway_node_methods.py -k
  "sessions_spawn_acp_inherits_target_agent_workspace or
  sessions_spawn_acp_omits_missing_inherited_target_workspace or
  sessions_spawn_acp_reports_inherited_workspace_access_failure or
  sessions_spawn_acp_uses_configured_default_agent or
  sessions_spawn_acp_requires_target_agent_without_default or
  sessions_spawn_acp_rejects_agent_outside_acp_allowlist or
  sessions_spawn_acp_runtime_tracks_wait_cleanup_and_completion or
  sessions_spawn_acp_stream_to_parent_tracks_child_run" -q` (`8 passed`),
  `python -m pytest tests\test_gateway_acp_spawn.py -q` (`9 passed`), `ruff
  check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Top-level `doctor` now reports OpenClaw-style session lock health for
  `agents/*/sessions/*.jsonl.lock` files in human and JSON output, including
  pid liveness, age labels, stale posture, read-only guidance, and `--fix`
  removal of stale locks while preserving fresh locks.
- Verified the doctor session-lock slice with `python -m pytest
  tests\test_cli.py -q -k "doctor_human_output_reports_session_lock_files or
  doctor_fix_removes_stale_session_lock_files"` (`2 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now reports the OpenClaw state-integrity warning
  for a missing configured state/data directory, including a structured
  `stateDirectory` payload and the CRITICAL warning text from
  `C:\Users\skull\OneDrive\Documents\openclaw-main\src\commands\doctor.warns-state-directory-is-missing.e2e.test.ts`.
- Verified the missing-state-directory doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_state_directory_is_missing -q`
  (`1 passed`), adjacent doctor proof `python -m pytest tests\test_cli.py -q
  -k "doctor_json_warns_when_state_directory_is_missing or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"` (`6 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Top-level `doctor --json` now also mirrors OpenClaw's OpenCode legacy
  provider override warning: configured `models.providers.opencode` and
  `models.providers.opencode-go` entries produce a structured
  `providerOverrides.opencode` payload plus a top-level warning.
- Verified the OpenCode provider override doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_opencode_provider_overrides -q`
  (`1 passed`), adjacent doctor proof `python -m pytest tests\test_cli.py -q
  -k "doctor_json_warns_about_opencode_provider_overrides or
  doctor_json_warns_when_state_directory_is_missing or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"` (`7 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Top-level `doctor --json` now mirrors OpenClaw's Codex OAuth provider
  override warning: legacy `models.providers.openai-codex` OpenAI transport
  settings warn only when configured or stored Codex OAuth exists, inline
  legacy model transports are detected, and custom proxy/header-only/no-OAuth
  cases stay quiet.
- Verified the Codex OAuth provider override doctor slice with `python -m
  pytest tests\test_cli.py -q -k "codex_provider_override or
  codex_inline_model or codex_override_warning"` (`4 passed`), adjacent doctor
  proof `python -m pytest tests\test_cli.py -q -k "codex_provider_override or
  codex_inline_model or codex_override_warning or opencode_provider_overrides or
  state_directory_is_missing or sandbox_enabled_without_docker or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"` (`11 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Top-level `doctor --json` now includes OpenClaw's local gateway-auth warning
  contribution: explicit local gateway config warns for missing token auth,
  ambiguous token/password config without `gateway.auth.mode`, and unresolved
  SecretRef-managed tokens, while `OPENCLAW_GATEWAY_TOKEN` suppresses the
  missing-token warning.
- Verified the gateway-auth doctor slice with `python -m pytest tests\test_cli.py
  -q -k "gateway_auth_missing_local_token or gateway_auth_warning_when_env_token
  or gateway_auth_mode_is_ambiguous or secretref_gateway_token"` (`4 passed`),
  adjacent doctor proof `python -m pytest tests\test_cli.py -q -k
  "gateway_auth_missing_local_token or gateway_auth_warning_when_env_token or
  gateway_auth_mode_is_ambiguous or secretref_gateway_token or
  codex_provider_override or codex_inline_model or codex_override_warning or
  opencode_provider_overrides or state_directory_is_missing or
  sandbox_enabled_without_docker or doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"` (`15 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Top-level `doctor --json` now routes configured browser-health checks through
  a native `doctor:browser` contribution boundary: configured default profiles
  or `existing-session` browser profiles produce a structured unavailable
  fallback when no browser doctor facade/adapter is registered, matching
  OpenClaw's graceful browser facade failure path.
- Verified the browser doctor facade fallback slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_browser_health_unavailable_when_facade_missing
  -q` (`1 passed`), adjacent doctor proof `python -m pytest tests\test_cli.py
  -q -k "browser_health_unavailable or gateway_auth_missing_local_token or
  gateway_auth_warning_when_env_token or gateway_auth_mode_is_ambiguous or
  secretref_gateway_token or codex_provider_override or codex_inline_model or
  codex_override_warning or opencode_provider_overrides or
  state_directory_is_missing or sandbox_enabled_without_docker or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"` (`16 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Top-level `doctor --json` now includes OpenClaw's `doctor:gateway-config`
  missing-mode warning for explicit gateway config without `gateway.mode`,
  including configure/setup-style fix guidance and a structured
  `gatewayConfig` warning payload.
- Verified the gateway-config missing-mode slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_gateway_mode_is_unset -q` (`1
  passed`), adjacent doctor proof `python -m pytest tests\test_cli.py -q -k
  "gateway_mode_is_unset or browser_health_unavailable or
  gateway_auth_missing_local_token or gateway_auth_warning_when_env_token or
  gateway_auth_mode_is_ambiguous or secretref_gateway_token or
  codex_provider_override or codex_inline_model or codex_override_warning or
  opencode_provider_overrides or state_directory_is_missing or
  sandbox_enabled_without_docker or doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"` (`17 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Top-level `doctor --json` now includes an OpenClaw-shaped
  `doctor:claude-cli` contribution when Claude CLI models or backends are
  configured, reporting binary availability, headless-auth posture, missing
  `anthropic:claude-cli` auth profile guidance, and fix hints without requiring
  an interactive Claude credential prompt.
- Verified the Claude CLI doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_claude_cli_model_is_configured_but_unavailable
  -q` (`1 passed`), adjacent doctor proof `python -m pytest tests\test_cli.py
  -q -k "claude_cli_model_is_configured or gateway_mode_is_unset or
  browser_health_unavailable or gateway_auth_missing_local_token or
  gateway_auth_warning_when_env_token or gateway_auth_mode_is_ambiguous or
  secretref_gateway_token or codex_provider_override or codex_inline_model or
  codex_override_warning or opencode_provider_overrides or
  state_directory_is_missing or sandbox_enabled_without_docker or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections"` (`18 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Top-level `doctor --json` now includes OpenClaw's `doctor:oauth-tls`
  contribution for configured `openai-codex` OAuth profiles. The native
  fakeable preflight probes the OpenAI auth endpoint, classifies TLS
  certificate-chain failures, and returns the upstream Homebrew CA remediation
  guidance as a structured `oauthTls` warning.
- Verified the OAuth TLS doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_openai_codex_oauth_tls_preflight_fails
  -q` (`1 passed`), adjacent Codex/auth proof `python -m pytest
  tests\test_cli.py -q -k "openai_codex_oauth_tls or codex_provider_override
  or codex_inline_model or codex_override_warning or
  claude_cli_model_is_configured"` (`6 passed`), broader doctor warning/repair
  proof `python -m pytest tests\test_cli.py -q -k "doctor_json_warns or
  doctor_fix_rewrites or doctor_fix_normalizes_legacy_cron_store"` (`32
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Top-level `doctor --json` now includes OpenClaw's `doctor:hooks-model`
  contribution when `hooks.gmail.model` is configured. It resolves raw model
  ids and aliases against `agents.defaults.models`, reports allowlist drift,
  and warns when the resolved hook model is absent from the configured model
  catalog.
- Verified the hooks-model doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_hooks_gmail_model_is_not_allowed_or_cataloged
  -q` (`1 passed`), adjacent model/doctor proof `python -m pytest
  tests\test_cli.py -q -k "hooks_gmail_model or models_aliases or
  models_list_json or models_status"` (`9 passed`), broader doctor
  warning/repair proof `python -m pytest tests\test_cli.py -q -k
  "doctor_json_warns or doctor_fix_rewrites or
  doctor_fix_normalizes_legacy_cron_store"` (`33 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now includes OpenClaw's `doctor:bootstrap-size`
  contribution for configured workspace directories. It scans `AGENTS.md`
  against `agents.defaults.bootstrapMaxChars` /
  `bootstrapTotalMaxChars`, reports truncation/near-limit statistics, and
  emits the upstream max/file and max/total tuning hints without mutating
  workspace files.
- Verified the bootstrap-size doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_bootstrap_file_exceeds_limits
  -q` (`1 passed`), adjacent doctor proof `python -m pytest tests\test_cli.py
  -q -k "bootstrap_file_exceeds_limits or hooks_gmail_model or
  doctor_json_warns or doctor_fix_rewrites or
  doctor_fix_normalizes_legacy_cron_store"` (`34 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now includes the first OpenClaw
  `doctor:workspace-status` native read model. It summarizes manifest-backed
  plugin registry records into loaded/imported/disabled/error/bundle counts,
  matching the upstream workspace-status plugin note surface while leaving
  deeper skill/task-flow recovery hints as separate seams.
- Verified the workspace-status plugin-summary slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_workspace_status_plugin_counts
  -q` (`1 passed`), adjacent workspace/plugin doctor proof `python -m pytest
  tests\test_cli.py -q -k "workspace_status_plugin_counts or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  bootstrap_file_exceeds_limits or doctor_json_warns"` (`33 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- `doctor --json` now carries the upstream `doctor:workspace-status` TaskFlow
  recovery hint path. Native task-blueprint-backed flows are scanned for broken
  blocked flows with missing `blockedTaskId` links and running managed flows
  without linked tasks/wait state, then exposed through
  `workspaceStatus.taskFlowRecovery` and top-level warnings with the OpenClaw
  `openclaw tasks flow show <flow-id>` / `cancel <flow-id>` guidance.
- Verified the workspace-status TaskFlow recovery slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_adds_task_flow_recovery_hints_for_broken_blocked_flows
  -q` (`1 passed`), adjacent doctor/task-flow proof `python -m pytest
  tests\test_cli.py -q -k "workspace_status_plugin_counts or
  task_flow_recovery_hints or tasks_flow_list_json_projects_task_blueprint_flows
  or tasks_flow_show_json_resolves_task_blueprint_flow or
  tasks_flow_cancel_disables_task_blueprint_and_pauses_linked_missions or
  doctor_json_warns"` (`44 passed`), `ruff check src\openzues\cli.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now includes OpenClaw's
  `doctor:device-pairing` gateway-backed pending request warning. It calls
  `device.pair.list` through the native gateway method owner, summarizes
  pending/paired counts, sanitizes request/device labels, and projects the
  upstream `openclaw devices list` / `openclaw devices approve <requestId>`
  guidance into the structured doctor warnings.
- Verified the device-pairing doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_pending_device_pairing_from_gateway
  -q` (`1 passed`), adjacent gateway doctor proof `python -m pytest
  tests\test_cli.py -q -k "pending_device_pairing or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_json_includes_gateway_memory_probe_contribution or doctor_json_warns"`
  (`34 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- The same native `doctor:device-pairing` contribution now classifies
  OpenClaw's paired-device follow-up states from the gateway snapshot:
  public-key repair, role upgrade, scope upgrade, already-paired repair, missing
  approved-role token, missing operator scope baseline, and token scopes outside
  the approved baseline. Suggested `openclaw devices ...` repair commands quote
  untrusted request/device/role arguments before they enter doctor output.
- Verified the device-pairing classification slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_classifies_device_pairing_repairs_and_token_gaps
  -q` (`1 passed`), adjacent device/gateway doctor proof `python -m pytest
  tests\test_cli.py -q -k "device_pairing or pending_device_pairing or
  gateway_memory_probe or gateway_health_contribution"` (`4 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- CLI service construction now wires the native `GatewayNodePairingService`
  into `GatewayNodeMethodService`, matching the app-server graph so
  `device.pair.list` / `node.pair.*` are available to real `doctor` runs and
  device commands instead of only injected test fakes.
- Verified the CLI device-pairing runtime wiring with `python -m pytest
  tests\test_cli.py::test_cli_services_wire_device_pairing_runtime_for_doctor
  -q` (`1 passed`), adjacent CLI/device doctor proof `python -m pytest
  tests\test_cli.py -q -k "cli_services_wire_device_pairing_runtime_for_doctor
  or device_pairing or pending_device_pairing or gateway_memory_probe or
  gateway_health_contribution"` (`5 passed`), adjacent gateway pairing proof
  `python -m pytest tests\test_gateway_node_methods.py -q -k "device_pair or
  device_token"` (`6 passed`), `ruff check src\openzues\cli.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- `doctor:device-pairing` now also reads OpenClaw-shaped local
  `identity/device.json` and `identity/device-auth.json` files when present
  under the native data directory, warning when cached local device auth
  predates gateway token rotation, no longer has a matching active gateway
  token, or has cached scopes that differ from the gateway record.
- Verified the local device-auth doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_local_device_auth_token_is_stale
  -q` (`1 passed`), adjacent doctor/gateway proof `python -m pytest
  tests\test_cli.py -q -k "local_device_auth_token or device_pairing or
  pending_device_pairing or gateway_memory_probe or gateway_health_contribution
  or doctor_json_warns"` (`37 passed`), adjacent gateway pairing proof
  `python -m pytest tests\test_gateway_node_methods.py -q -k "device_pair or
  device_token"` (`6 passed`), `ruff check src\openzues\cli.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now includes OpenClaw's `doctor:legacy-cron`
  contribution for configured file-backed `cron.store` paths. It reports
  legacy `jobId`, `schedule.cron`, top-level payload/delivery fields, and
  `notify: true` fallback issues, and `doctor --fix` normalizes the store while
  migrating notify-only jobs to `cron.webhook` delivery.
- Verified the legacy-cron doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_cron_store
  tests\test_cli.py::test_doctor_fix_normalizes_legacy_cron_store -q` (`2
  passed`), adjacent cron/CLI proof `python -m pytest tests\test_cli.py -q -k
  "legacy_cron_store or cron_add_payload_extra_flags or
  cron_edit_payload_extra_flags or cron_add_at_timezone"` (`7 passed`), broader
  doctor warning/repair proof `python -m pytest tests\test_cli.py -q -k
  "doctor_json_warns or doctor_fix_rewrites or
  doctor_fix_normalizes_legacy_cron_store"` (`31 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Gateway `poll` now rejects `isAnonymous` for non-Telegram channels before
  runtime dispatch, matching OpenClaw's provider capability guard while leaving
  Telegram's anonymous-poll path available.
- Verified the poll anonymous-capability slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "poll_rejects_is_anonymous_for_non_telegram_like_openclaw or
  poll_uses_channel_poll_runtime"` (`2 passed`), adjacent poll proof `python
  -m pytest tests\test_gateway_node_methods.py -q -k "poll_"` (`11 passed`),
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Native plugin runtime executor specs now preserve OpenClaw's `optional`
  metadata and `tools.invoke` can expose optional registry executors through
  exact tool-name, plugin-id, or `group:plugins` allowlist tokens.
- Verified the optional plugin allowlist slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "optional_registry_plugin_executor_by_plugin_id_allowlist"` (`1 passed`),
  adjacent plugin-runtime executor proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k "tools_invoke_runs_configured_plugin_executor
  or tools_invoke_hides_plugin_executor_without_config_allow or
  tools_invoke_runs_registry_plugin_executor_in_registration_order or
  optional_registry_plugin_executor_by_plugin_id_allowlist or
  tools_invoke_keeps_core_mapping_before_registry_plugin_executor or
  tools_invoke_skips_disabled_registry_plugin_executor or
  tools_invoke_keeps_registry_owner_only_executor_hidden_from_non_owner"` (`7
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_plugin_runtime.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_plugin_runtime.py`.
- `plugins inspect --json` now preserves runtime plugin executor optional
  metadata in its `tools` projection instead of merging all runtime tools into
  an always-required group, matching OpenClaw's registered tool status shape.
- Verified the plugin inspect optional-metadata slice with `python -m pytest
  tests\test_cli.py -q -k "runtime_executor_optional_metadata"` (`1 passed`),
  adjacent inspect proof `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_preserves_runtime_executor_optional_metadata or
  plugins_inspect_json_projects_record_runtime_surfaces"` (`3 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- `plugins list --json` now also includes a top-level
  `runtimeExecutors` inventory from the native
  `GatewayPluginRuntimeService.catalog_specs()` projection, using the same
  `status`, `count`, `ownerOnlyCount`, and per-tool provider metadata shape as
  the runtime bridge doctor surface. `plugins list --verbose` now also prints
  the same registered runtime executor tools, including plugin id, source,
  optional, and owner-only markers, for human operator parity.
- Verified the plugin list runtime-executor inventory slice with `python -m
  pytest
  tests\test_cli.py::test_plugins_list_json_projects_runtime_executor_inventory
  -q` (`1 passed`), human-output proof `python -m pytest
  tests\test_cli.py::test_plugins_list_verbose_reports_runtime_executor_inventory
  -q` (`1 passed`), adjacent plugin CLI proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_projects_runtime_executor_inventory or
  plugins_list_verbose_reports_runtime_executor_inventory or
  plugins_list_json_projects_hermes_plugin_inventory or
  plugins_list_enabled_filters_loaded_plugins or
  plugins_list_json_includes_saved_config_install_records or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_preserves_runtime_executor_optional_metadata"` (`8
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Metadata-only `plugins.load.paths` discovery now also preserves OpenClaw
  manifest-owned `commandAliases` entries, normalizing string aliases and
  object aliases with `kind="runtime-slash"` / `cliCommand` metadata so CLI
  diagnostics and plugin inventory can distinguish plugin ids from runtime
  slash-command aliases before importing plugin code.
- Verified the manifest command-alias metadata slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_preserves_manifest_command_aliases
  -q` (`1 passed`), adjacent metadata proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_preserves_manifest_command_aliases or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_all_json_includes_saved_install_records"` (`6 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Metadata-only plugin discovery now also preserves OpenClaw manifest
  `activation` and `setup` descriptors, including provider/agent-harness/
  command/channel/route/capability activation hints plus setup provider auth
  methods, env vars, CLI backend ids, config migration ids, and
  `requiresRuntime` posture.
- Verified the manifest activation/setup descriptor slice with `python -m
  pytest
  tests\test_cli.py::test_plugins_list_json_preserves_manifest_activation_and_setup
  -q` (`1 passed`), adjacent metadata proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_preserves_manifest_command_aliases or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_all_json_includes_saved_install_records"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Metadata-only plugin discovery now also preserves OpenClaw manifest auth/env
  metadata: provider auth env vars, provider endpoint hints with lowercased
  hosts, synthetic auth refs, non-secret auth markers, provider auth aliases,
  provider auth choices, and channel env vars.
- Verified the manifest auth/env metadata slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_preserves_manifest_auth_and_env_metadata
  -q` (`1 passed`), adjacent metadata proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_preserves_manifest_auth_and_env_metadata or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_preserves_manifest_command_aliases or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_all_json_includes_saved_install_records"` (`8 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Metadata-only plugin discovery now also preserves OpenClaw manifest
  `qaRunners` descriptors, including the QA command name and optional
  description used by QA fallback host stubs.
- Verified the manifest QA runner descriptor slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_preserves_manifest_qa_runners -q`
  (`1 passed`), adjacent metadata proof `python -m pytest tests\test_cli.py
  -q -k
  "plugins_list_json_preserves_manifest_qa_runners or
  plugins_list_json_preserves_manifest_auth_and_env_metadata or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_preserves_manifest_command_aliases or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_all_json_includes_saved_install_records"` (`9 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Metadata-only plugin discovery now also preserves OpenClaw manifest
  `channelConfigs` entries with required schemas plus UI hints, labels,
  descriptions, and `preferOver` fallback ordering.
- Verified the manifest channel-config metadata slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_preserves_manifest_channel_configs
  -q` (`1 passed`), adjacent metadata proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_preserves_manifest_channel_configs or
  plugins_list_json_preserves_manifest_qa_runners or
  plugins_list_json_preserves_manifest_auth_and_env_metadata or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_preserves_manifest_command_aliases or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_all_json_includes_saved_install_records"` (`10 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Metadata-only plugin discovery now also preserves OpenClaw manifest
  `modelSupport` entries, including model-prefix and regex-pattern metadata
  used for pre-runtime model-family ownership.
- Verified the manifest model-support metadata slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_preserves_manifest_model_support
  -q` (`1 passed`), adjacent metadata proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_preserves_manifest_model_support or
  plugins_list_json_preserves_manifest_channel_configs or
  plugins_list_json_preserves_manifest_qa_runners or
  plugins_list_json_preserves_manifest_auth_and_env_metadata or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_preserves_manifest_command_aliases or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_all_json_includes_saved_install_records"` (`11 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Metadata-only plugin discovery now also preserves OpenClaw manifest
  `configContracts` entries, including compatibility migration/runtime paths,
  dangerous literal config flags, and secret input materialization hints for
  pre-runtime config ownership.
- Verified the manifest config-contract metadata slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_preserves_manifest_config_contracts
  -q` (`1 passed`), adjacent metadata proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_preserves_manifest_config_contracts or
  plugins_list_json_preserves_manifest_model_support or
  plugins_list_json_preserves_manifest_channel_configs or
  plugins_list_json_preserves_manifest_qa_runners or
  plugins_list_json_preserves_manifest_auth_and_env_metadata or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_preserves_manifest_command_aliases or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_all_json_includes_saved_install_records"` (`12 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Metadata-only plugin discovery now also preserves OpenClaw manifest root
  identity/classification metadata: `enabledByDefault`, `legacyPluginIds`,
  `autoEnableWhenConfiguredProviders`, `kind`, `channels`, `providers`,
  `providerDiscoverySource` resolved from `providerDiscoveryEntry`,
  `cliBackends`, `skills`, and `configUiHints` projected from top-level
  `uiHints`.
- Verified the manifest root metadata slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_preserves_manifest_identity_and_classification
  -q` (`1 passed`), adjacent metadata proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_preserves_manifest_identity_and_classification or
  plugins_list_json_preserves_manifest_config_contracts or
  plugins_list_json_preserves_manifest_model_support or
  plugins_list_json_preserves_manifest_channel_configs or
  plugins_list_json_preserves_manifest_qa_runners or
  plugins_list_json_preserves_manifest_auth_and_env_metadata or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_preserves_manifest_command_aliases or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_all_json_includes_saved_install_records"` (`13 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Metadata-only plugin discovery now also reads adjacent `package.json`
  OpenClaw metadata for package name/version/description fallbacks,
  `setupSource`, startup deferral, channel catalog metadata, and package-owned
  channel label/description/prefer-over hydration.
- Verified the package manifest runtime metadata slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_preserves_package_manifest_runtime_metadata
  -q` (`1 passed`), adjacent metadata proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_preserves_package_manifest_runtime_metadata or
  plugins_list_json_preserves_manifest_identity_and_classification or
  plugins_list_json_preserves_manifest_config_contracts or
  plugins_list_json_preserves_manifest_model_support or
  plugins_list_json_preserves_manifest_channel_configs or
  plugins_list_json_preserves_manifest_qa_runners or
  plugins_list_json_preserves_manifest_auth_and_env_metadata or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_preserves_manifest_command_aliases or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_all_json_includes_saved_install_records"` (`14 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Package manifest `openclaw.install.minHostVersion` now gates metadata-only
  plugin discovery with OpenClaw-shaped skip diagnostics for incompatible,
  invalid, or indeterminate host versions.
- Verified the package min-host metadata slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_skips_incompatible_package_manifest_min_host_version
  -q` (`1 passed`), adjacent metadata proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_skips_incompatible_package_manifest_min_host_version or
  plugins_list_json_preserves_package_manifest_runtime_metadata or
  plugins_list_json_preserves_manifest_identity_and_classification or
  plugins_list_json_preserves_manifest_config_contracts or
  plugins_list_json_preserves_manifest_model_support or
  plugins_list_json_preserves_manifest_channel_configs or
  plugins_list_json_preserves_manifest_qa_runners or
  plugins_list_json_preserves_manifest_auth_and_env_metadata or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_preserves_manifest_command_aliases or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or
  plugins_inspect_json_projects_runtime_executor_tools or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_all_json_includes_saved_install_records"` (`15 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins list --json`, `plugins inspect --json`, and `plugins doctor --json`
  now project OpenClaw-style bundled plugin runtime dependency inventory from
  `package.json` `dependencies` / `optionalDependencies`, compute bundled
  install roots, skip source checkouts, honor enabled channel plugin config,
  and report missing dependency sentinels plus conflicting versions.
- Verified the bundled plugin runtime dependency slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies
  tests\test_cli.py::test_plugins_doctor_json_reports_missing_bundled_runtime_dependencies
  tests\test_cli.py::test_plugins_doctor_json_limits_runtime_deps_to_enabled_channel_plugins
  -q` (`3 passed`), adjacent plugin CLI proof `python -m pytest
  tests\test_cli.py -q -k "plugins_list_json_discovers_openclaw_manifest_load_paths
  or runtime_deps or runtime_dependencies or plugins_doctor or
  plugins_inspect_json_projects_runtime_executor_tools"` (`8 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now includes the OpenClaw
  `doctor:bundled-plugin-runtime-deps` contribution, reusing the native
  bundled plugin dependency scanner and reporting `ok` / `error` posture,
  missing deps, conflicts, diagnostics, and the current no-install repair
  boundary.
- Verified the top-level bundled plugin runtime dependency doctor contribution
  with `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_bundled_plugin_runtime_dependency_contribution
  -q` (`1 passed`), adjacent doctor/plugin proof `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_includes_bundled_plugin_runtime_dependency_contribution or
  doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_and_update_status_json_include_hermes_sections or
  plugins_doctor_json_reports_missing_bundled_runtime_dependencies or
  plugins_doctor_json_limits_runtime_deps_to_enabled_channel_plugins"` (`5
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Top-level `doctor --json` now also includes the OpenClaw `doctor:sandbox`
  contribution as structured data, including resolved sandbox mode/backend,
  Docker availability, warnings for missing Docker or ignored shared-scope
  overrides, status, summary, and the current no-install repair boundary.
- Verified the structured sandbox doctor contribution with `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_sandbox_contribution -q` (`1
  passed`), adjacent doctor proof `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_sandbox_contribution or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_warns_about_shared_sandbox_agent_overrides or
  doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution or
  doctor_and_update_status_json_include_hermes_sections"` (`6 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now includes the OpenClaw `doctor:memory-search`
  gateway memory probe contribution: it calls `doctor.memory.status` through
  the native gateway method owner when available, reports checked/ready/error
  state, and projects the OpenClaw-style "Gateway memory probe for default
  agent is not ready" warning into structured JSON.
- Verified the gateway memory probe doctor contribution with `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_gateway_memory_probe_contribution
  -q` (`1 passed`), adjacent doctor proof `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_sandbox_contribution or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution or
  doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_and_update_status_json_include_hermes_sections"` (`6 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- The CLI root now accepts OpenClaw-compatible `--dev`, `--no-color`,
  `--profile`, `--log-level`, and `--container` flags before subcommands, and
  native token-consumption helpers match OpenClaw's value-token behavior for
  negative numeric values and `--` terminators.
- Verified the CLI root option compatibility slice with `python -m pytest
  tests\test_cli.py::test_root_option_token_consumption_matches_openclaw_reference_cases
  tests\test_cli.py::test_root_openclaw_compat_options_are_accepted_before_command
  -q` (`2 passed`), adjacent CLI parser/doctor proof `python -m pytest
  tests\test_cli.py -q -k "root_option or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_sandbox_contribution or
  health_json_surfaces_gateway_health_snapshot"` (`3 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Top-level `doctor --fix` now exposes the OpenClaw
  `doctor:startup-channel-maintenance` repair-mode contribution: normal doctor
  marks it skipped, while repair mode calls a fakeable native adapter with
  `trigger="doctor-fix"` and `logPrefix="doctor"` and reports the adapter
  result or unavailable boundary.
- Verified the startup-channel maintenance doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_fix_runs_startup_channel_maintenance_adapter
  tests\test_cli.py::test_doctor_skips_startup_channel_maintenance_without_fix
  -q` (`2 passed`), adjacent doctor/CLI proof `python -m pytest
  tests\test_cli.py -q -k "startup_channel_maintenance or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution or
  root_openclaw_compat"` (`6 passed`), `ruff check src\openzues\cli.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Native WhatsApp route sends now split text-only payloads into OpenClaw-style
  4000-character chunks instead of truncating at 4096 characters, and return
  the last provider message id from the chunked send sequence.
- Verified the WhatsApp long-text chunking slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "chunks_whatsapp_long_text"` (`1 passed`),
  adjacent WhatsApp provider proof `python -m pytest tests\test_ops_mesh.py -q
  -k "send_direct_channel_message_uses_whatsapp_native_route or
  chunks_whatsapp_long_text or splits_whatsapp_media or
  preserves_whatsapp_reply_document or uses_whatsapp_gif_video_payload"` (`5
  passed`), `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py`.
- Native WhatsApp media sends now use the original outbound text as the leading
  media caption instead of appending OpenZues' generated media URL/settings
  summary into provider-visible captions; delivery logs still retain the
  formatted summary separately.
- Verified the WhatsApp media-caption slice with `python -m pytest
  tests\test_ops_mesh.py -q -k
  "send_direct_channel_message_uses_whatsapp_native_route or
  splits_whatsapp_media or preserves_whatsapp_reply_document or
  uses_whatsapp_gif_video_payload"` (`4 passed`), adjacent WhatsApp provider
  proof `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_message_uses_whatsapp_native_route or
  chunks_whatsapp_long_text or splits_whatsapp_media or
  preserves_whatsapp_reply_document or uses_whatsapp_gif_video_payload"` (`5
  passed`), `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py`.
- Native Zalo route sends now use OpenClaw's Bot API shape
  (`/bot{token}/sendMessage`) and split text-only payloads into
  2000-character chunks instead of treating Zalo as an unsupported webhook-only
  route kind.
- Verified the Zalo native-route slice with `pytest tests/test_ops_mesh.py::
  test_ops_mesh_service_send_direct_channel_message_uses_zalo_native_route -q`
  (`1 passed`), adjacent provider-native proof `pytest tests/test_ops_mesh.py
  -q -k "native_route or native_provider or provider_runtime or
  provider_native_options or provider_result_persistence or
  chunks_whatsapp_long_text or splits_whatsapp_media or whatsapp_document_reply
  or whatsapp_gif_video or discord_reply_silent or telegram_media_group or
  telegram_force_document"` (`20 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Native Zalo media sends now use OpenClaw's `sendPhoto` Bot API path, preserve
  the original outbound text as the first media caption, iterate multiple media
  URLs, and return the last provider message id with `mediaIds` / `mediaUrls`
  metadata.
- Verified the Zalo media slice with `pytest tests/test_ops_mesh.py::
  test_ops_mesh_service_send_direct_channel_message_splits_zalo_media -q` (`1
  passed`), adjacent provider-native proof `pytest tests/test_ops_mesh.py -q
  -k "zalo or native_route or native_provider or provider_runtime or
  provider_native_options or provider_result_persistence or
  chunks_whatsapp_long_text or splits_whatsapp_media or whatsapp_document_reply
  or whatsapp_gif_video or discord_reply_silent or telegram_media_group or
  telegram_force_document"` (`21 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Gateway `message.action` now dispatches valid channel actions through a
  fakeable native runtime hook instead of hard-stopping every supported channel,
  while preserving the existing unsupported-channel/action errors when no
  dispatcher is registered.
- Verified the `message.action` dispatcher slice with `pytest
  tests/test_gateway_node_methods.py::test_message_action_dispatches_registered_native_action_runtime
  -q` (`1 passed`), adjacent message-action proof `pytest
  tests/test_gateway_node_methods.py -q -k "message_action"` (`9 passed`),
  `ruff check src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_message_actions.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_message_actions.py`.
- Route-backed Slack `message.action react` now dispatches through the native
  Slack Web API route token, normalizes `channel:` ids and colon-wrapped emoji
  names, and supports both `reactions.add` and explicit `reactions.remove`
  payloads from the production app and CLI gateway method owners.
- Verified the Slack action-adapter slice with `pytest
  tests/test_ops_mesh.py::test_ops_mesh_service_message_action_dispatches_slack_react_route
  -q` (`1 passed`), adjacent provider/action proof `pytest
  tests/test_ops_mesh.py -q -k "message_action or slack_native_route or
  native_route or provider_runtime or provider_native_options"` (`17 passed`),
  adjacent gateway proof `pytest tests/test_gateway_node_methods.py -q -k
  "message_action"` (`9 passed`), `ruff check
  src\openzues\services\ops_mesh.py src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_message_actions.py src\openzues\app.py
  src\openzues\cli.py tests\test_ops_mesh.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_message_actions.py src\openzues\app.py
  src\openzues\cli.py`.
- Slack `message.action reactions` now dispatches through the same route-backed
  native Slack adapter, calling `reactions.get` with `full=true` and returning
  the upstream-shaped `message.reactions ?? []` payload.
- Verified the Slack reactions-list slice with `pytest
  tests/test_ops_mesh.py::test_ops_mesh_service_message_action_dispatches_slack_reactions_list_route
  -q` (`1 passed`), adjacent provider/action proof `pytest
  tests/test_ops_mesh.py -q -k "message_action or slack_native_route or
  native_route or provider_runtime or provider_native_options"` (`18 passed`),
  adjacent gateway proof `pytest tests/test_gateway_node_methods.py -q -k
  "message_action"` (`9 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action edit` now follows OpenClaw's Slack adapter mapping by
  translating route-backed action calls into Slack `chat.update`, normalizing
  `channel:` targets, forwarding `messageId` as `ts`, and returning native
  provider message/channel metadata.
- Verified the Slack edit-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_edit_route"` (`1 passed`), adjacent
  Slack action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`5 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action delete` now follows OpenClaw's Slack adapter mapping by
  translating route-backed action calls into Slack `chat.delete`, accepting
  `channelId` or `to` targets, forwarding `messageId` as `ts`, and returning
  native provider message/channel metadata.
- Verified the Slack delete-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_delete_route"` (`1 passed`), adjacent
  Slack action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`6 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action pin` now follows OpenClaw's Slack adapter mapping by
  translating route-backed action calls into Slack `pins.add`, normalizing
  channel targets, forwarding `messageId` as `timestamp`, and returning native
  provider message/channel metadata.
- Verified the Slack pin-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_pin_route"` (`1 passed`), adjacent Slack
  action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`7 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action unpin` now follows OpenClaw's Slack adapter mapping by
  translating route-backed action calls into Slack `pins.remove`, normalizing
  channel targets, forwarding `messageId` as `timestamp`, and returning native
  provider message/channel metadata.
- Verified the Slack unpin-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_unpin_route"` (`1 passed`), adjacent
  Slack action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`8 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action list-pins` now follows OpenClaw's Slack adapter mapping
  by translating route-backed action calls into Slack `pins.list`, normalizing
  `channelId` / `to` targets, and returning provider-shaped pin items.
- Verified the Slack list-pins action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_list_pins_route"` (`1 passed`),
  adjacent Slack action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`9 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action read` now follows OpenClaw's Slack adapter channel
  history mapping by translating route-backed action calls into
  `conversations.history`, preserving `limit`, `before` -> `latest`, and
  `after` -> `oldest`, and returning provider-shaped messages plus `hasMore`.
- Verified the Slack read-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_read_route"` (`1 passed`), adjacent
  Slack action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`10 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action read threadId=...` now mirrors OpenClaw's threaded
  read path by calling `conversations.replies`, passing `threadId` as `ts`,
  and dropping the parent message from returned replies.
- Verified the Slack threaded-read slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_thread_read_route"` (`1 passed`),
  adjacent Slack read/action proof `python -m pytest tests\test_ops_mesh.py -q
  -k "slack_read_route or slack_thread_read_route or
  message_action_dispatches_slack"` (`11 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action member-info` now follows OpenClaw's Slack adapter
  mapping by translating route-backed action calls into Slack `users.info` and
  returning the provider info envelope under `info`.
- Verified the Slack member-info slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_member_info_route"` (`1 passed`),
  adjacent Slack action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`12 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action emoji-list` now follows OpenClaw's Slack adapter
  mapping by calling Slack `emoji.list` through the native route token and
  applying optional sorted-name limiting to the returned emoji map locally.
- Verified the Slack emoji-list slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_emoji_list_route"` (`1 passed`),
  adjacent Slack action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`13 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action upload-file` now follows OpenClaw's Slack adapter
  mapping by accepting `filePath` / `path` / `media`, caption and thread
  aliases, explicit filename/title overrides, and route-backed Slack external
  file upload with local path reads.
- Verified the Slack upload-file slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_upload_file_route"` (`1 passed`),
  adjacent Slack action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`14 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action download-file` now follows OpenClaw's Slack adapter
  mapping by fetching fresh `files.info` metadata, honoring channel/thread
  share scope evidence, downloading private Slack file URLs with the saved
  route token, and returning saved local media path metadata.
- Verified the Slack download-file slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_download_file"` (`2 passed`),
  adjacent Slack action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`15 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action send` now follows OpenClaw's generic Slack action
  entrypoint by dispatching route-backed `chat.postMessage` sends with
  `threadId` / `replyTo` aliases, block payload validation, and the same native
  external-upload helper for media sends.
- Verified the Slack send-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_send_route"` (`1 passed`), adjacent
  Slack action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_slack"` (`16 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack empty-emoji `message.action react` now mirrors OpenClaw's remove-own
  path: the native route resolves the bot user with `auth.test`, reads
  `reactions.get full=true`, removes only reaction names owned by that bot via
  `reactions.remove`, and returns the ordered removed names.
- Verified the Slack remove-own reaction slice with `pytest
  tests/test_ops_mesh.py::test_ops_mesh_service_message_action_dispatches_slack_react_remove_own_route
  -q` (`1 passed`), adjacent provider/action proof `pytest
  tests/test_ops_mesh.py -q -k "message_action or slack_native_route or
  native_route or provider_runtime or provider_native_options"` (`19 passed`),
  adjacent gateway proof `pytest tests/test_gateway_node_methods.py -q -k
  "message_action"` (`9 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Telegram `message.action react` now dispatches through the native Bot API
  route using `setMessageReaction`, adding `[{type:"emoji", emoji}]` for
  non-empty reactions and sending an empty `reaction` array for explicit remove
  or empty-emoji clear paths.
- Verified the Telegram reaction-action slice with `pytest
  tests/test_ops_mesh.py -q -k "telegram_react"` (`3 passed`), adjacent
  provider/action proof `pytest tests/test_ops_mesh.py -q -k "message_action or
  telegram_native_route or telegram_media_group or native_route or
  provider_runtime or provider_native_options"` (`23 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action react` add now uses the route-backed bot token
  against Discord REST `PUT /channels/{channel}/messages/{message}/reactions/{emoji}/@me`,
  including OpenClaw-style unicode/custom emoji normalization through the
  encoded reaction identifier.
- Verified the Discord reaction-add slice with `pytest
  tests/test_ops_mesh.py::test_ops_mesh_service_message_action_dispatches_discord_react_route
  -q` (`1 passed`), adjacent provider/action proof `pytest
  tests/test_ops_mesh.py -q -k "message_action or discord_native_route or
  native_route or provider_runtime or provider_native_options"` (`23 passed`),
  adjacent gateway proof `pytest tests/test_gateway_node_methods.py -q -k
  "message_action"` (`9 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord explicit `message.action react remove=true` now uses the same
  route-backed bot token and encoded emoji identifier with Discord REST
  own-reaction `DELETE`, returning the upstream-shaped removed emoji payload.
- Verified the Discord reaction-remove slice with `pytest tests/test_ops_mesh.py
  -q -k "discord_react"` (`2 passed`), adjacent provider/action proof `pytest
  tests/test_ops_mesh.py -q -k "message_action or discord_native_route or
  native_route or provider_runtime or provider_native_options"` (`24 passed`),
  adjacent gateway proof `pytest tests/test_gateway_node_methods.py -q -k
  "message_action"` (`9 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord empty-emoji `message.action react` now mirrors OpenClaw's remove-own
  behavior by fetching the message reactions, building unicode/custom reaction
  identifiers, deleting each own reaction, and returning the removed identifier
  list.
- Verified the Discord remove-own reaction slice with `pytest
  tests/test_ops_mesh.py -q -k "discord_react"` (`3 passed`), adjacent
  provider/action proof `pytest tests/test_ops_mesh.py -q -k "message_action or
  discord_native_route or native_route or provider_runtime or
  provider_native_options"` (`25 passed`), adjacent gateway proof `pytest
  tests/test_gateway_node_methods.py -q -k "message_action"` (`9 passed`),
  `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and
  `mypy src\openzues\services\ops_mesh.py`.
- Discord `message.action reactions` now mirrors OpenClaw's list fanout by
  fetching message reaction summaries, fetching users for each encoded reaction
  with a bounded `limit`, and returning emoji/count/user summaries.
- Verified the Discord reactions-list slice with `pytest
  tests/test_ops_mesh.py::test_ops_mesh_service_message_action_dispatches_discord_reactions_list_route
  -q` (`1 passed`), focused Discord reaction proof `pytest
  tests/test_ops_mesh.py -q -k "discord_react or discord_reactions"` (`4
  passed`), adjacent provider/action proof `pytest tests/test_ops_mesh.py -q -k
  "message_action or discord_native_route or native_route or provider_runtime or
  provider_native_options"` (`26 passed`), adjacent gateway proof `pytest
  tests/test_gateway_node_methods.py -q -k "message_action"` (`9 passed`),
  `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and
  `mypy src\openzues\services\ops_mesh.py`.
- Discord `message.action send` now follows OpenClaw's generic Discord action
  entrypoint by dispatching route-backed webhook sends through the native
  provider owner, preserving `to`, `message`, `replyTo`, `threadId`, `silent`,
  and media/path/filePath aliases.
- Verified the Discord send-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_send_route"` (`1 passed`), adjacent
  Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`5 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action edit` now follows OpenClaw's messaging runtime by
  translating route-backed action calls into Discord REST message `PATCH`
  requests with `channelId` / `to`, `messageId`, and `message` parameters.
- Verified the Discord edit-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_edit_route"` (`1 passed`), adjacent
  Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`6 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action delete` now follows OpenClaw's messaging runtime by
  translating route-backed action calls into Discord REST message `DELETE`
  requests with `channelId` / `to` plus `messageId`.
- Verified the Discord delete-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_delete_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`7 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action pin`, `unpin`, and `list-pins` now follow
  OpenClaw's messaging runtime by dispatching route-backed bot-token REST
  requests to Discord pins endpoints, returning `{ok: true}` for pin/unpin and
  normalized pinned-message timestamps for `list-pins`.
- Verified the Discord pins-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_pin_mutation_route or
  discord_list_pins_route"` (`3 passed`), adjacent Discord action proof
  `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`10 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action read` now follows OpenClaw's messaging runtime by
  dispatching route-backed bot-token REST history reads with `limit`, `before`,
  `after`, and `around` query params, including upstream-style integer parsing,
  1-100 limit clamping, and normalized message timestamps.
- Verified the Discord read-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_read_route"` (`1 passed`), adjacent
  Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`11 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action permissions` now follows OpenClaw's messaging
  runtime by fetching the route-backed Discord channel, bot identity, guild,
  and member records, then applying guild, role, and member permission
  overwrites into the upstream-shaped permission summary.
- Verified the Discord permissions-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_permissions_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`12 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action thread-create` now follows OpenClaw's messaging
  runtime by dispatching route-backed bot-token REST thread creation, including
  standalone channel-type lookup, default public thread creation for non-forum
  channels, auto-archive duration mapping, and starter-message delivery into
  the created thread.
- Verified the Discord thread-create-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_thread_create_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`13 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action sticker` now follows OpenClaw's messaging runtime by
  dispatching route-backed bot-token REST channel messages with `sticker_ids`
  from upstream `stickerId` / `stickerIds` params and optional `message`
  content.
- Verified the Discord sticker-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_sticker_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`14 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action set-presence` now follows OpenClaw's gateway-backed
  presence runtime shape with a fakeable native adapter, upstream status and
  activity validation, projected presence payloads, and the honest gateway-not-
  available error when no Discord Gateway adapter is registered.
- Verified the Discord set-presence-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_set_presence or
  discord_presence_unavailable"` (`2 passed`), adjacent Discord action proof
  `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`16 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action member-info` now follows OpenClaw's guild-admin
  runtime by dispatching route-backed bot-token REST member reads and returning
  the upstream `{ok: true, member}` payload.
- Verified the Discord member-info-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_member_info_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`17 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action role-info` now follows OpenClaw's guild-admin
  runtime by dispatching route-backed bot-token REST guild role reads and
  returning the upstream `{ok: true, roles}` payload.
- Verified the Discord role-info-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_role_info_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`18 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action emoji-list` now follows OpenClaw's guild-admin
  runtime by dispatching route-backed bot-token REST guild emoji reads and
  returning the upstream `{ok: true, emojis}` payload.
- Verified the Discord emoji-list-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_emoji_list_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`19 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action channel-info` and `channel-list` now follow
  OpenClaw's guild-admin runtime by dispatching route-backed bot-token REST
  channel metadata reads and returning upstream `{ok: true, channel}` /
  `{ok: true, channels}` payloads.
- Verified the Discord channel metadata-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_channel_info_route or
  discord_channel_list_route"` (`2 passed`), adjacent Discord action proof
  `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`21 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action role-add` and `role-remove` now follow OpenClaw's
  guild-admin runtime by dispatching route-backed bot-token REST member-role
  `PUT` / `DELETE` mutations and returning `{ok: true}`.
- Verified the Discord role mutation-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_role_mutation_route"` (`2 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`23 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action channel-create` now follows OpenClaw's guild-admin
  runtime by dispatching route-backed bot-token REST channel creation with
  `name`, `type`, `parentId`, `topic`, `position`, and `nsfw` body mapping.
- Verified the Discord channel-create-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_channel_create_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`24 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action channel-edit` now follows OpenClaw's guild-admin
  runtime by dispatching route-backed bot-token REST channel PATCH requests,
  including `clearParent` / null parent handling plus rate-limit, archive, lock,
  auto-archive, and forum/media `availableTags` body mapping.
- Verified the Discord channel-edit-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_channel_edit_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`25 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action channel-delete` now follows OpenClaw's guild-admin
  runtime by dispatching route-backed bot-token REST channel deletion and
  returning the upstream `{ok: true, channelId}` payload.
- Verified the Discord channel-delete-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_channel_delete_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`26 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action channel-move` now follows OpenClaw's guild-admin
  runtime by PATCHing the guild channel positions endpoint with normalized
  channel ids, optional parent clearing/assignment, integer position coercion,
  and the upstream `{ok: true}` result.
- Verified the Discord channel-move-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_channel_move_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`27 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action category-create` now follows OpenClaw's guild-admin
  runtime by creating a type `4` Discord category through the route-backed
  guild channels endpoint and returning the upstream `{ok: true, category}`
  payload.
- Verified the Discord category-create-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_category_create_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`28 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action category-edit` now follows OpenClaw's guild-admin
  runtime by PATCHing the category channel with optional name and integer
  position fields and returning the upstream `{ok: true, category}` payload.
- Verified the Discord category-edit-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_category_edit_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`29 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action category-delete` now follows OpenClaw's guild-admin
  runtime by deleting the category channel through the route-backed bot-token
  REST path and returning the upstream `{ok: true, channelId}` payload.
- Verified the Discord category-delete-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_category_delete_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`30 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action voice-status` now follows OpenClaw's guild-admin
  runtime by reading the guild voice-state endpoint through the route-backed
  bot-token REST path and returning the upstream `{ok: true, voice}` payload.
- Verified the Discord voice-status-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_voice_status_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`31 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action event-list` now follows OpenClaw's guild-admin
  runtime by reading the guild scheduled-events endpoint through the
  route-backed bot-token REST path and returning the upstream
  `{ok: true, events}` payload.
- Verified the Discord event-list-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_event_list_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`32 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action event-create` now covers OpenClaw's core scheduled
  event creation body without cover-image media resolution, including
  description/end-time/channel/location fields, external/stage/voice entity
  type mapping, privacy level `2`, and the upstream `{ok: true, event}`
  payload.
- Verified the Discord event-create-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_event_create_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`33 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action timeout` now covers OpenClaw's explicit-until,
  `durationMin`/`durationMinutes`, and audit-log reason moderation paths by
  PATCHing the member endpoint with `communication_disabled_until`, encoded
  `X-Audit-Log-Reason` when present, and the upstream `{ok: true, member}`
  payload.
- Verified the Discord timeout explicit-until slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_timeout_route"` (`1 passed`),
  duration alias slice with `python -m pytest tests\test_ops_mesh.py -q -k
  "discord_timeout_duration_route"` (`1 passed`),
  audit-reason slice with `python -m pytest tests\test_ops_mesh.py -q -k
  "discord_timeout_reason_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`36 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action kick` now follows OpenClaw's moderation runtime by
  deleting the guild member through the route-backed bot-token REST path,
  including encoded audit-log reason headers, and returning `{ok: true}`.
- Verified the Discord kick-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_kick_route"` (`1 passed`), adjacent
  Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`37 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action ban` now follows OpenClaw's moderation runtime by
  PUTing the guild ban endpoint with clamped `delete_message_days`, encoded
  audit-log reason headers, and the upstream `{ok: true}` payload.
- Verified the Discord ban-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_ban_route"` (`1 passed`), adjacent
  Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`38 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action thread-list` now covers OpenClaw's active-thread
  path by reading the guild active threads endpoint through the route-backed
  bot-token REST path and returning the upstream `{ok: true, threads}`
  payload.
- Verified the Discord active thread-list slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_thread_list_active_route"` (`1
  passed`), adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py
  -q -k "message_action_dispatches_discord"` (`39 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action thread-list` now also covers OpenClaw's archived
  channel-thread path, requiring a channel id when `includeArchived=true` and
  forwarding optional `before` and integer `limit` query parameters to
  `/channels/{channelId}/threads/archived/public`.
- Verified the Discord archived thread-list slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_thread_list_archived_route"` (`1
  passed`), combined thread-list proof `python -m pytest tests\test_ops_mesh.py
  -q -k "discord_thread_list_active_route or discord_thread_list_archived_route"`
  (`2 passed`), adjacent Discord action proof `python -m pytest
  tests\test_ops_mesh.py -q -k "message_action_dispatches_discord"` (`40
  passed`), `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py`.
- Discord `message.action thread-reply` now covers OpenClaw's core text/reply
  path by POSTing to the thread channel messages endpoint, carrying
  `message_reference` when `replyTo` is provided, and returning the upstream
  `{ok: true, result}` payload with message/channel ids.
- Verified the Discord thread-reply slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_thread_reply_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`41 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action search` now follows OpenClaw's message search
  runtime by querying guild message search with content, repeated
  channel/author filters, clamped limit, and the upstream
  `{ok: true, results}` payload.
- Verified the Discord search-action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_search_route"` (`1 passed`), adjacent
  Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`42 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Re-verified the Discord channel-edit `availableTags` expansion with
  `python -m pytest tests\test_ops_mesh.py -q -k "discord_channel_edit_route"`
  (`1 passed`), adjacent Discord action proof `python -m pytest
  tests\test_ops_mesh.py -q -k "message_action_dispatches_discord"` (`42
  passed`), `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py`.
- Discord `message.action emoji-upload` now follows OpenClaw's guild-admin
  emoji upload runtime by loading data URL/local/canvas/HTTP media, validating
  PNG/JPG/GIF content, posting Discord's `image` data URI with normalized name
  and filtered role ids, and returning `{ok: true, emoji}`.
- Verified the Discord emoji-upload slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_emoji_upload_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`43 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action sticker-upload` now follows OpenClaw's guild-admin
  sticker upload runtime by loading data URL/local/canvas/HTTP media,
  validating PNG/APNG/Lottie JSON content, sending Discord's multipart sticker
  create request, and returning `{ok: true, sticker}`.
- Verified the Discord sticker-upload slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_sticker_upload_route"` (`1 passed`),
  adjacent Discord action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`44 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- WhatsApp `message.action react` now dispatches through the native WhatsApp
  Cloud API route, normalizing direct WhatsApp JIDs to E.164 recipients and
  sending `type="reaction"` payloads for add, empty-emoji clear, and explicit
  `remove=true` paths. The dispatcher also mirrors OpenClaw's scoped current
  message fallback: `toolContext.currentMessageId` is accepted only for
  WhatsApp-origin, same-chat actions and is ignored for cross-chat targets.
- Verified the WhatsApp reaction-action slice with `pytest
  tests\test_ops_mesh.py -q -k "whatsapp_react or whatsapp_cross_chat"` (`5
  passed`), adjacent provider/action proof `pytest tests\test_ops_mesh.py -q -k
  "message_action or
  whatsapp_native_route or native_route or provider_runtime or
  provider_native_options"` (`31 passed`), adjacent gateway proof `pytest
  tests\test_gateway_node_methods.py -q -k "message_action"` (`9 passed`),
  `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and
  `mypy src\openzues\services\ops_mesh.py`.
- Zalo `message.action send` now routes through the same native
  provider-backed Zalo send owner used by direct sends, preserving the upstream
  `to` / `message` / optional `media` action shape and returning `{ok, to,
  messageId}`. The public notification-route schema now also accepts
  `kind="zalo"` so the native route can be created through normal route
  surfaces.
- Verified the Zalo send-action slice with `pytest tests\test_ops_mesh.py -q
  -k "zalo_send or notification_route_create_accepts_zalo"` (`3 passed`),
  adjacent provider/action proof `pytest tests\test_ops_mesh.py -q -k
  "message_action or zalo or native_route or provider_runtime or
  provider_native_options"` (`35 passed`), adjacent gateway proof `pytest
  tests\test_gateway_node_methods.py -q -k "message_action"` (`10 passed`),
  `ruff check src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py
  tests\test_ops_mesh.py tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py`.
- CLI `channels capabilities` now reports official Zalo support with
  direct/group chat types, media enabled, and reactions/polls/threads disabled
  when a native Zalo route is configured.
- Verified the Zalo capability slice with `pytest tests\test_cli.py::
  test_channels_capabilities_json_reports_zalo_support -q` (`1 passed`),
  adjacent channel proof `pytest tests\test_cli.py -q -k
  "channels_capabilities_json or channels_status_json or route_backed"` (`18
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Gateway `poll` now rejects `durationSeconds` for non-Telegram channels before
  dispatch, matching OpenClaw's `supportsPollDurationSeconds` adapter opt-in
  guard while preserving `durationHours` for Slack/Discord-style poll paths.
- Verified the poll duration-seconds capability slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "duration_seconds_for_non_telegram"` (`1 passed`), adjacent poll proof
  `python -m pytest tests\test_gateway_node_methods.py -q -k "poll_"` (`12
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Telegram gateway poll requests now mirror OpenClaw's duration option
  validation: `durationSeconds` must be 5-600, and `durationHours` is rejected
  unless the caller supplies valid second-granularity duration instead.
- Verified the Telegram poll duration-option slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "telegram_duration_seconds_outside_openclaw_range or
  telegram_duration_hours_like_openclaw or poll_uses_channel_poll_runtime"` (`3
  passed`), adjacent poll proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k "poll_"` (`14 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py`.
- OpsMesh route-backed Telegram polls now enforce the same OpenClaw duration
  contract for direct CLI/runtime sends and replays, rejecting invalid
  `durationSeconds` and Telegram `durationHours` before any provider post.
- Verified the OpsMesh Telegram duration guard with `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_native_poll or
  rejects_invalid_telegram_durations"` (`2 passed`), adjacent Telegram poll
  provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_uses_telegram_native_route or
  rejects_invalid_telegram_durations or parses_telegram_topic_target"` (`5
  passed`), `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py`.
- Gateway `poll` now applies OpenClaw's channel-specific poll option caps:
  Telegram and Discord reject more than 10 options while WhatsApp retains its
  12-option cap.
- Verified the gateway poll option-cap slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "channel_specific_option_limit or poll_uses_channel_poll_runtime"` (`3
  passed`), adjacent poll proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k "poll_"` (`16 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py`.

## Feature Families

| Family | Status | Estimate | Current Read |
| --- | --- | --- | --- |
| Gateway + gateway methods | Near-complete bounded local path | ~99% | Gateway method registry, config lookups/mutation, model/session inventory, node invoke guards, native browser command productization, plugin/exec approval lifecycles, exec approval policy config, device-pair lifecycle, device token rotate/revoke, agent registry mutation, memory-doctor mutation, OpenClaw bootstrap/memory agent files, and strict chat/session validation are heavily covered. |
| Gateway session/tool contracts | Active | ~97.4% | `sessions_history`, `session_status`, `sessions_list`, `sessions_send`, `sessions_spawn`, `sessions_yield`, `sessions.create`, `sessions.patch`, `sessions.pluginPatch`, `sessions.delete`, `tools.invoke`, `plugins.uiDescriptors`, plugin-published `tools.catalog` / `tools.effective` groups, optional plugin executor allowlist aliases, registered plugin session extension state, active-registry control UI descriptors, visibility policy, ACP spawn dispatch/tracking plus `mode="session"` thread-required guard and delete/reset runtime cleanup, app-wired sandbox-required Codex app-server dispatch, route-backed thread adapters with bound initial child-run and terminal completion delivery, configured and omitted subagent timeout defaults, completion-expectation metadata, lightweight bootstrap context, child task envelopes, lifecycle policy metadata, terminal cleanup consumption, wait-consumed completion announcements, completion-announcement idempotency, tracked-run freshness guards, `agent.wait` zero-timeout polling, exact run-id wait precedence, recovered-run tracking cleanup, exact-run tracker isolation, sanitized attachment mount-path hints, sandboxed remote provider media staging, and chat/session transcript contracts are now the live queue head; config-driven sandbox target selection and broader native executor/provider hooks remain. |
| Chat + transcript contracts | Strong partial | ~97% | `chat.history`, direct session history REST/SSE, `chat.send`, `chat.inject`, `chat.abort` run ownership and partial persistence, live `session.message`, `sessions.changed`, transcript metadata, usage/cost, text caps, and sanitizer parity are verified against OpenClaw-shaped behavior where they map to SQLite-backed storage. |
| Cron wake/delivery | Strong partial | ~99% | Direct send/poll, provider route callbacks, native route setup, replay/test dispatch, direct-announce provider metadata, provider error/result metadata, OpenClaw-style cron-expression schedules, due-run behavior, session-key wake routing, retry/backoff, one-shot delete-after-run cleanup, the CLI simple command group, and add/edit schedule/payload breadth are verified. |
| Onboarding + setup | Partial | ~70% | QuickStart, gateway bootstrap, saved-lane handling, degraded bootstrap boundaries, remote saved-lane wizard progression, and broken-default repair posture are real, with broader OpenClaw setup breadth still open. |
| CLI + operator control plane | Strong partial | ~98.7% | Health, status JSON breadth flags with fakeable usage/security adapters, text `status --all`, native `acp client` interactive replay, continue, queue, recover/harden, gateway doctor, top-level sandbox/Docker doctor warning plus session-lock health notes, delivery replay, route creation, direct route send/poll, sandbox inventory/config-backed explain/recreate plus human summaries, sessions inventory/spawn/wait plus cleanup dry-run/no-op apply, `--fix-missing` metadata pruning, stale `updatedAt` preview/enforce, count-cap preview/enforce, native disk-budget preview/enforce, and all-agent grouped cleanup JSON, read-only `tasks`/`tasks list`/`tasks show` inspection plus `tasks audit`, `tasks maintenance`, metadata-backed `tasks notify`, mission-backed `tasks cancel`, and `tasks flow list/show/cancel` over native mission/task-blueprint state, cron status/list/runs/run/rm/enable/disable plus add/edit schedule, delivery, payload, failure-alert, and one-shot cleanup flags, models list/status plus auth-status probe fallback, root `models set` / `models set-image` mutations, `models scan` metadata/no-probe/non-interactive/live probe posture, aliases list/add/remove, fallbacks list/add/remove/clear, image fallback list/add/remove/clear, auth order get/set/clear, and auth add/login/login-github-copilot/setup-token/paste-token with fakeable auth probes/check exits, `infer`/`capability` metadata list/inspect plus model run/list/inspect/providers/auth status/login/logout, image providers/generate/edit/describe/describe-many, audio providers/transcribe, video providers/generate/describe, web providers/search/fetch, embedding providers/create, and TTS providers/status/personas/voices/enable/disable/set-provider/set-persona/convert, channel status/probe/capabilities/resolve/logs, plugins list with saved install records, metadata-only `plugins.load.paths` manifest discovery with command aliases, activation/setup descriptors, auth/env metadata, QA runner descriptors, channel config metadata, model-support metadata, config-contract metadata, root identity/classification metadata, package manifest setup/startup/channel metadata, package min-host skip diagnostics, explicit Codex/Claude/Cursor bundle manifest metadata, manifestless Claude bundle metadata, JSON5 bundle manifest parsing, Claude bundle command projection, and bundle MCP/LSP server projection, top-level runtime executor inventory, runtime-backed inspect tool projection with optional metadata, doctor with compatibility notices, inspect/info/marketplace list/local marketplace install/update/uninstall/enable/disable, local path link/copy install, ClawHub/npm install, npm-not-found bundled fallback, npm install-record update with explicit npm spec override selection, and operator monitor surfaces exist; broader runtime CLI/TUI breadth remains. |
| Routing + session identity | Strong partial | ~84% | Session keys, routed targeting, custom-agent session creation/filtering/identity/workspace files, snapshot filtering, compaction inventory, spawned-session visibility, parent/child aliases, and direct session-history replay are real; provider-owned routing remains open. |
| Skills + Ops Mesh | Partial | ~72% | Skill pins, skillbooks, inbox/snapshots/inventory, Hermes-inspired toolsets, recall/learning surfaces, and lane-aware supervision are useful but not complete OpenClaw/Hermes parity. |
| Channels + direct announce delivery | Strong partial | ~97% | Shared outbound runtime ownership spans direct send/poll, explicit announce, saved replays, direct-announce provider metadata/replay, native adapters, Slack/Telegram/Discord/WhatsApp/Zalo routes, CLI route send/poll commands, gateway-owned channel status/capability probe metadata with route-backed Slack/Telegram/Discord account probes, Zalo capability reporting, and WhatsApp's upstream no-hook probe posture, saved-target plus route-backed Slack channel/user resolve with OpenClaw-style auto-kind grouping, route-backed Telegram username resolve, route-backed Discord channel-id/guild-qualified/global channel-name and user resolve, fakeable live channel resolve, fakeable `message.action` dispatch, route-backed Slack `send`, `react` add/remove/remove-own, `reactions` list, `edit`, `delete`, `pin`, `unpin`, `list-pins`, channel-history `read`, threaded `read`, `member-info`, `emoji-list`, local-path-backed `upload-file`, and scoped `download-file` action dispatch, route-backed Discord `send`, `edit`, `delete`, `pin`, `unpin`, `list-pins`, channel-history `read`, `permissions`, `thread-create`, active/archived `thread-list`, core `thread-reply`, `search`, `sticker`, `sticker-upload`, gateway-backed `set-presence`, guild-admin `member-info`, `role-info`, `emoji-list`, `emoji-upload`, `channel-info`, `channel-list`, `channel-create`, `channel-edit`, `channel-delete`, `channel-move`, `category-create`, `category-edit`, `category-delete`, `voice-status`, `event-list`, core `event-create`, `timeout`, `kick`, `ban`, `role-add`, and `role-remove`, `react` add/remove/remove-own plus `reactions` list action dispatch, route-backed Telegram `react` add/remove/clear action dispatch, route-backed WhatsApp `react` add/remove plus scoped current-message fallback action dispatch, route-backed Zalo `send` text/media action dispatch, structured channel log tailing, provider result metadata, OpenClaw-style send reply/thread/silent/document fields, Telegram native document/reply/silent/thread payloads plus topic-qualified send target parsing, parent-route matching, and poll duration validation, anonymous and duration-seconds poll capability guarding, Telegram/Discord poll option caps, WhatsApp native reply/document/gif-video payloads plus long-text chunking and upstream-style media captions, admin-scoped chat origin/system provenance, A2A announce/reply loops, and idle `sessions.steer` runtime sends; other production per-provider action adapters and broader provider option coverage remain open. |
| Browser/canvas/nodes/voice | Locked bounded family | ~99% | Canvas documents/A2UI/live-reload/capability routing, node event wakes, APNS wake paths, managed attachments, native browser runtimes, guarded artifacts, action grammar, scoped settings, batch execution, dashboard lifecycle, AI chat command routing, iOS provider command bridges, clipboard controls, storage/cookie mutation, HAR capture, confirmation handling, auth profile login/delete, and password-safe auth save are now landed. |
| Packaging + companion apps | Minimal | ~5% | Still largely outside the current shipped OpenZues surface. |

## Remaining Not-Fully-Complete Areas

- Config-driven sandboxed target runtimes beyond the app-wired Codex workspace-write path plus deeper persistent thread unbind/end-hook behavior.
- Broader provider-native outbound runtime breadth for remaining provider-specific edge cases and production `message.action` adapters beyond the verified Telegram topic-qualified send/poll paths, Telegram reaction actions, Discord send/edit/delete/pin/unpin/list-pins/read/fetch-message/permissions/thread-create/active+archived thread-list/thread-reply/search/sticker/sticker-upload/poll/set-presence/member-info/role-info/emoji-list/emoji-upload/channel-info/channel-list/channel-create/channel-edit/channel-delete/channel-move/channel-permission-set/channel-permission-remove/category-create/category-edit/category-delete/voice-status/event-list/event-create/timeout/kick/ban/role-add/role-remove/reaction action adapters, WhatsApp reaction action adapter, Zalo send action adapter, WhatsApp/Zalo media payloads, fakeable action dispatch hook, and Slack send/reaction/reactions/edit/delete/pin/unpin/list-pins/read/member-info/emoji-list/upload-file/download-file action adapters.
- Remote marketplace clone/update breadth and deeper runtime plugin activation/import metadata beyond metadata-only config load-path discovery and the fakeable ordered executor registry.
- Broader OpenClaw companion apps, packaging/distribution, full CLI/TUI ergonomics, and non-Windows host parity.
- OpenClaw file-store-only edge cases that do not cleanly map to OpenZues' current SQLite-backed transcript source of truth.

## Latest Browser Family Evidence

- Browser command runtimes now cover status, doctor, verify, tabs, profiles, screenshot, PDF, get/is, history navigation, stream lifecycle, network read diagnostics, cookie/storage reads, session reads, diff diagnostics, download/upload guards, trace/profiler/record artifacts, highlight/inspect, and open/navigate/focus/close/start/stop.
- `browser.act` now covers wait, click, double-click, type, fill, press, hover, focus, check, uncheck, select, scroll, scroll-into-view, evaluate, resize, close, drag, mouse move/down/up/wheel, focused keyboard insert-text, and semantic find locators.
- `browser.set` now covers guarded settings: viewport, device, geo, offline, media, scoped headers, and HTTP credentials. Secret-bearing header values and passwords are redacted from runtime payloads.
- `browser.clipboard.read`, `browser.clipboard.write`, `browser.clipboard.copy`, and `browser.clipboard.paste` now expose the installed clipboard bridge through structured gateway methods.
- `browser.storage.set` and `browser.storage.clear` now mutate localStorage/sessionStorage through a typed browser storage bridge.
- `browser.cookies.set` and `browser.cookies.clear` now mutate browser cookies through a typed cookie bridge that avoids echoing real cookie values from the runtime payload.
- `browser.network.har.start` and `browser.network.har.stop` now capture browser HAR artifacts through controlled OpenZues temp paths.
- `browser.confirm` and `browser.deny` now route pending browser action decisions through structured methods.
- `browser.auth.login` and `browser.auth.delete` now mutate saved auth profiles without introducing password-bearing payloads.
- `browser.auth.save` now creates saved auth profiles through `agent-browser auth save --password-stdin`, keeping passwords out of argv and redacting noisy runtime output.
- `browser.batch` now executes bounded one-line agent-browser command sequences through structured JSON, with `bail` support and no shell invocation.
- `browser.dashboard.start` and `browser.dashboard.stop` now control the local agent-browser observability dashboard with bounded port validation.
- `browser.chat` now routes single-shot natural-language browser instructions through structured gateway params with optional model and quiet/verbose controls; missing AI Gateway credentials surface as runtime unavailable.
- `browser.ios.device.list`, `browser.ios.swipe`, and `browser.ios.tap` now bridge installed iOS provider commands through structured gateway methods; Windows/non-Xcode hosts surface unavailable at runtime.
- Persistent proxy/profile mutation remains intentionally guarded instead of productized as a native gateway method.

## Latest Verification

- `python -m pytest tests\test_cli.py -q -k "plugins_inspect_json_projects_config_policy"`: 1 passed after projecting configured plugin inspect policy from `plugins.entries`.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 17 passed after rechecking plugin CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin inspect policy slice.
- `mypy src\openzues\cli.py`: clean after the plugin inspect policy slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_inspect_json_projects_runtime_executor_tools"`: 1 passed after projecting native plugin runtime executor tools through `plugins inspect --json`.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 16 passed after rechecking plugin list/inspect/doctor/marketplace/install/update/uninstall/toggle surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin runtime inspect projection slice.
- `mypy src\openzues\cli.py`: clean after the plugin runtime inspect projection slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_projects_runtime_executor_inventory -q`: 1 passed after projecting top-level plugin runtime executor inventory through `plugins list --json`.
- `python -m pytest tests\test_cli.py::test_plugins_list_verbose_reports_runtime_executor_inventory -q`: 1 passed after adding verbose human output for the same runtime executor inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_projects_runtime_executor_inventory or plugins_list_verbose_reports_runtime_executor_inventory or plugins_list_json_projects_hermes_plugin_inventory or plugins_list_enabled_filters_loaded_plugins or plugins_list_json_includes_saved_config_install_records or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_preserves_runtime_executor_optional_metadata"`: 8 passed after rechecking adjacent plugin list/inspect runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin list runtime executor inventory slice.
- `mypy src\openzues\cli.py`: clean after the plugin list runtime executor inventory slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_preserves_manifest_command_aliases -q`: 1 passed after preserving OpenClaw manifest command aliases in plugin inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_preserves_manifest_command_aliases or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_projects_record_runtime_surfaces or plugins_inspect_all_json_includes_saved_install_records"`: 6 passed after rechecking adjacent plugin metadata inventory/inspect surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the manifest command-alias metadata slice.
- `mypy src\openzues\cli.py`: clean after the manifest command-alias metadata slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_preserves_manifest_activation_and_setup -q`: 1 passed after preserving OpenClaw manifest activation/setup descriptors in plugin inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_preserves_manifest_activation_and_setup or plugins_list_json_preserves_manifest_command_aliases or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_projects_record_runtime_surfaces or plugins_inspect_all_json_includes_saved_install_records"`: 7 passed after rechecking adjacent plugin metadata inventory/inspect surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the manifest activation/setup descriptor slice.
- `mypy src\openzues\cli.py`: clean after the manifest activation/setup descriptor slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_preserves_manifest_auth_and_env_metadata -q`: 1 passed after preserving OpenClaw manifest auth/env metadata in plugin inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_preserves_manifest_auth_and_env_metadata or plugins_list_json_preserves_manifest_activation_and_setup or plugins_list_json_preserves_manifest_command_aliases or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_projects_record_runtime_surfaces or plugins_inspect_all_json_includes_saved_install_records"`: 8 passed after rechecking adjacent plugin metadata inventory/inspect surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the manifest auth/env metadata slice.
- `mypy src\openzues\cli.py`: clean after the manifest auth/env metadata slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_preserves_manifest_qa_runners -q`: 1 passed after preserving OpenClaw manifest QA runner descriptors in plugin inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_preserves_manifest_qa_runners or plugins_list_json_preserves_manifest_auth_and_env_metadata or plugins_list_json_preserves_manifest_activation_and_setup or plugins_list_json_preserves_manifest_command_aliases or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_projects_record_runtime_surfaces or plugins_inspect_all_json_includes_saved_install_records"`: 9 passed after rechecking adjacent plugin metadata inventory/inspect surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the manifest QA runner descriptor slice.
- `mypy src\openzues\cli.py`: clean after the manifest QA runner descriptor slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_preserves_manifest_channel_configs -q`: 1 passed after preserving OpenClaw manifest channel config metadata in plugin inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_preserves_manifest_channel_configs or plugins_list_json_preserves_manifest_qa_runners or plugins_list_json_preserves_manifest_auth_and_env_metadata or plugins_list_json_preserves_manifest_activation_and_setup or plugins_list_json_preserves_manifest_command_aliases or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_projects_record_runtime_surfaces or plugins_inspect_all_json_includes_saved_install_records"`: 10 passed after rechecking adjacent plugin metadata inventory/inspect surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the manifest channel-config metadata slice.
- `mypy src\openzues\cli.py`: clean after the manifest channel-config metadata slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_preserves_manifest_model_support -q`: 1 passed after preserving OpenClaw manifest model-support metadata in plugin inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_preserves_manifest_model_support or plugins_list_json_preserves_manifest_channel_configs or plugins_list_json_preserves_manifest_qa_runners or plugins_list_json_preserves_manifest_auth_and_env_metadata or plugins_list_json_preserves_manifest_activation_and_setup or plugins_list_json_preserves_manifest_command_aliases or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_projects_record_runtime_surfaces or plugins_inspect_all_json_includes_saved_install_records"`: 11 passed after rechecking adjacent plugin metadata inventory/inspect surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the manifest model-support metadata slice.
- `mypy src\openzues\cli.py`: clean after the manifest model-support metadata slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_preserves_manifest_config_contracts -q`: 1 passed after preserving OpenClaw manifest config-contract metadata in plugin inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_preserves_manifest_config_contracts or plugins_list_json_preserves_manifest_model_support or plugins_list_json_preserves_manifest_channel_configs or plugins_list_json_preserves_manifest_qa_runners or plugins_list_json_preserves_manifest_auth_and_env_metadata or plugins_list_json_preserves_manifest_activation_and_setup or plugins_list_json_preserves_manifest_command_aliases or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_projects_record_runtime_surfaces or plugins_inspect_all_json_includes_saved_install_records"`: 12 passed after rechecking adjacent plugin metadata inventory/inspect surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the manifest config-contract metadata slice.
- `mypy src\openzues\cli.py`: clean after the manifest config-contract metadata slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_preserves_manifest_identity_and_classification -q`: 1 passed after preserving OpenClaw manifest root identity/classification metadata in plugin inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_preserves_manifest_identity_and_classification or plugins_list_json_preserves_manifest_config_contracts or plugins_list_json_preserves_manifest_model_support or plugins_list_json_preserves_manifest_channel_configs or plugins_list_json_preserves_manifest_qa_runners or plugins_list_json_preserves_manifest_auth_and_env_metadata or plugins_list_json_preserves_manifest_activation_and_setup or plugins_list_json_preserves_manifest_command_aliases or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_projects_record_runtime_surfaces or plugins_inspect_all_json_includes_saved_install_records"`: 13 passed after rechecking adjacent plugin metadata inventory/inspect surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the manifest root metadata slice.
- `mypy src\openzues\cli.py`: clean after the manifest root metadata slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_preserves_package_manifest_runtime_metadata -q`: 1 passed after preserving OpenClaw package manifest runtime metadata in plugin inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_preserves_package_manifest_runtime_metadata or plugins_list_json_preserves_manifest_identity_and_classification or plugins_list_json_preserves_manifest_config_contracts or plugins_list_json_preserves_manifest_model_support or plugins_list_json_preserves_manifest_channel_configs or plugins_list_json_preserves_manifest_qa_runners or plugins_list_json_preserves_manifest_auth_and_env_metadata or plugins_list_json_preserves_manifest_activation_and_setup or plugins_list_json_preserves_manifest_command_aliases or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_projects_record_runtime_surfaces or plugins_inspect_all_json_includes_saved_install_records"`: 14 passed after rechecking adjacent plugin metadata inventory/inspect surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the package manifest runtime metadata slice.
- `mypy src\openzues\cli.py`: clean after the package manifest runtime metadata slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_skips_incompatible_package_manifest_min_host_version -q`: 1 passed after adding OpenClaw package min-host skip diagnostics.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_skips_incompatible_package_manifest_min_host_version or plugins_list_json_preserves_package_manifest_runtime_metadata or plugins_list_json_preserves_manifest_identity_and_classification or plugins_list_json_preserves_manifest_config_contracts or plugins_list_json_preserves_manifest_model_support or plugins_list_json_preserves_manifest_channel_configs or plugins_list_json_preserves_manifest_qa_runners or plugins_list_json_preserves_manifest_auth_and_env_metadata or plugins_list_json_preserves_manifest_activation_and_setup or plugins_list_json_preserves_manifest_command_aliases or plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies or plugins_inspect_json_projects_runtime_executor_tools or plugins_inspect_json_projects_record_runtime_surfaces or plugins_inspect_all_json_includes_saved_install_records"`: 15 passed after rechecking adjacent plugin metadata inventory/inspect surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the package min-host metadata slice.
- `mypy src\openzues\cli.py`: clean after the package min-host metadata slice.
- `python -m pytest tests\test_cli.py::test_plugins_list_json_surfaces_openclaw_manifest_runtime_dependencies tests\test_cli.py::test_plugins_doctor_json_reports_missing_bundled_runtime_dependencies tests\test_cli.py::test_plugins_doctor_json_limits_runtime_deps_to_enabled_channel_plugins -q`: 3 passed after adding bundled plugin runtime dependency inventory and doctor diagnostics.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_discovers_openclaw_manifest_load_paths or runtime_deps or runtime_dependencies or plugins_doctor or plugins_inspect_json_projects_runtime_executor_tools"`: 8 passed after rechecking adjacent plugin CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the bundled plugin runtime dependency doctor slice.
- `mypy src\openzues\cli.py`: clean after the bundled plugin runtime dependency doctor slice.
- `python -m pytest tests\test_cli.py::test_doctor_json_includes_bundled_plugin_runtime_dependency_contribution -q`: 1 passed after adding the top-level `doctor:bundled-plugin-runtime-deps` contribution.
- `python -m pytest tests\test_cli.py -q -k "doctor_json_includes_bundled_plugin_runtime_dependency_contribution or doctor_json_includes_security_and_shell_completion_surfaces or doctor_and_update_status_json_include_hermes_sections or plugins_doctor_json_reports_missing_bundled_runtime_dependencies or plugins_doctor_json_limits_runtime_deps_to_enabled_channel_plugins"`: 5 passed after rechecking adjacent top-level doctor/plugin surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the top-level bundled plugin runtime dependency doctor contribution slice.
- `mypy src\openzues\cli.py`: clean after the top-level bundled plugin runtime dependency doctor contribution slice.
- `python -m pytest tests\test_cli.py::test_doctor_json_includes_sandbox_contribution -q`: 1 passed after adding the structured `doctor:sandbox` contribution.
- `python -m pytest tests\test_cli.py -q -k "doctor_json_includes_sandbox_contribution or doctor_json_warns_when_sandbox_enabled_without_docker or doctor_json_warns_about_shared_sandbox_agent_overrides or doctor_json_includes_security_and_shell_completion_surfaces or doctor_json_includes_bundled_plugin_runtime_dependency_contribution or doctor_and_update_status_json_include_hermes_sections"`: 6 passed after rechecking adjacent top-level doctor surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the structured sandbox doctor contribution slice.
- `mypy src\openzues\cli.py`: clean after the structured sandbox doctor contribution slice.
- `python -m pytest tests\test_cli.py::test_doctor_json_includes_gateway_memory_probe_contribution -q`: 1 passed after adding the structured `doctor:memory-search` gateway memory probe contribution.
- `python -m pytest tests\test_cli.py -q -k "doctor_json_includes_gateway_memory_probe_contribution or doctor_json_includes_sandbox_contribution or doctor_json_warns_when_sandbox_enabled_without_docker or doctor_json_includes_bundled_plugin_runtime_dependency_contribution or doctor_json_includes_security_and_shell_completion_surfaces or doctor_and_update_status_json_include_hermes_sections"`: 6 passed after rechecking adjacent top-level doctor surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the memory-search gateway probe doctor contribution slice.
- `mypy src\openzues\cli.py`: clean after the memory-search gateway probe doctor contribution slice.
- `python -m pytest tests\test_cli.py::test_root_option_token_consumption_matches_openclaw_reference_cases tests\test_cli.py::test_root_openclaw_compat_options_are_accepted_before_command -q`: 2 passed after adding OpenClaw-compatible root flag parsing.
- `python -m pytest tests\test_cli.py -q -k "root_option or doctor_json_includes_gateway_memory_probe_contribution or doctor_json_includes_sandbox_contribution or health_json_surfaces_gateway_health_snapshot"`: 3 passed after rechecking adjacent CLI parser/doctor smoke.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the root option compatibility slice.
- `mypy src\openzues\cli.py`: clean after the root option compatibility slice.
- `python -m pytest tests\test_cli.py::test_doctor_fix_runs_startup_channel_maintenance_adapter tests\test_cli.py::test_doctor_skips_startup_channel_maintenance_without_fix -q`: 2 passed after adding repair-mode startup channel maintenance doctor wiring.
- `python -m pytest tests\test_cli.py -q -k "startup_channel_maintenance or doctor_json_includes_gateway_memory_probe_contribution or doctor_json_includes_sandbox_contribution or doctor_json_includes_bundled_plugin_runtime_dependency_contribution or root_openclaw_compat"`: 6 passed after rechecking adjacent doctor/CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the startup channel maintenance doctor slice.
- `mypy src\openzues\cli.py`: clean after the startup channel maintenance doctor slice.
- `python -m pytest tests\test_cli.py -q -k "sandbox_explain_json_projects_config_sandbox_tool_policy"`: 1 passed after adding config-backed `sandbox explain` mode/scope/workspace/tool-policy projection.
- `python -m pytest tests\test_cli.py -q -k "sandbox_explain or sandbox_list or sandbox_recreate"`: 8 passed after rechecking adjacent sandbox CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the config-backed sandbox explain slice.
- `mypy src\openzues\cli.py`: clean after the config-backed sandbox explain slice.
- `python -m pytest tests\test_cli.py -q -k "doctor_json_warns_when_sandbox_enabled_without_docker"`: 1 passed after adding top-level Sandbox doctor warning parity for enabled Docker-backed sandbox mode without Docker.
- `python -m pytest tests\test_cli.py -q -k "doctor_json_warns_when_sandbox_enabled_without_docker or doctor_and_update_status_json_include_hermes_sections or gateway_doctor_human_output_summarizes_sections"`: 3 passed after rechecking top-level and gateway doctor output.
- `python -m pytest tests\test_cli.py -q -k "sandbox_list_json_returns_openclaw_shaped_inventory or sandbox_list_json_surfaces_saved_sandbox_runtime_metadata or sandbox_list_human_output_includes_total_summary or sandbox_explain_json_uses_saved_sandbox_metadata or sandbox_recreate_session_force_json_forgets_saved_sandbox_metadata"`: 5 passed after rechecking adjacent sandbox CLI projections.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the Sandbox doctor warning slice.
- `mypy src\openzues\cli.py`: clean after the Sandbox doctor warning slice.
- `python -m pytest tests\test_cli.py -q -k "models_status_probe_json_uses_gateway_auth_status_when_runtime_missing or models_status_probe_json_uses_model_auth_runtime or models_status_json_reports_default_and_auth_posture"`: 2 passed after adding the gateway `models.authStatus` fallback for `models status --probe`.
- `python -m pytest tests\test_cli.py -q -k "models_status or models_auth or infer_model_auth"`: 14 passed after rechecking model status/auth CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q -k "auth_status"`: 5 passed after rechecking gateway model auth-status normalization.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 31 passed after rechecking all model CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the model auth-status fallback slice.
- `mypy src\openzues\cli.py`: clean after the model auth-status fallback slice.
- `python -m pytest tests\test_gateway_model_scan.py -q`: 1 passed after adding live OpenRouter tool/image probe HTTP behavior with a fake transport.
- `python -m pytest tests\test_cli.py -q -k "models_scan"`: 3 passed after rechecking scan CLI behavior.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 30 passed after rechecking model list/status/set/set-image/scan/auth/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py tests\test_gateway_model_scan.py -q`: 20 passed after rechecking gateway model catalog plus model scan service behavior.
- `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py src\openzues\services\gateway_model_scan.py tests\test_cli.py tests\test_gateway_model_scan.py`: clean after the live model scan probe slice.
- `mypy src\openzues\cli.py src\openzues\services\gateway_config.py src\openzues\services\gateway_model_scan.py`: clean after the live model scan probe slice.
- `python -m pytest tests\test_cli.py -q -k "models_scan_no_probe_json_calls_scan_runtime_with_options or models_scan_yes_applies_default_and_image_model_choices or models_scan_human_noninteractive_requires_yes"`: 3 passed after adding non-interactive `models scan` posture.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 30 passed after rechecking model list/status/set/set-image/scan/auth/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py src\openzues\services\gateway_model_scan.py tests\test_cli.py`: clean after the model scan slice.
- `mypy src\openzues\cli.py src\openzues\services\gateway_config.py src\openzues\services\gateway_model_scan.py`: clean after the model scan slice.
- `python -m pytest tests\test_cli.py -q -k "models_set_image_updates_image_model_preserving_fallbacks or models_set_image_normalizes_provider_alias"`: 2 passed after adding `models set-image`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 27 passed after rechecking model list/status/set/set-image/auth/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model set-image slice.
- `mypy src\openzues\cli.py src\openzues\services\gateway_config.py`: clean after the model set-image slice.
- `python -m pytest tests\test_cli.py -q -k "models_set_updates_default_model_preserving_fallbacks or models_set_normalizes_provider_alias_and_legacy_openrouter_key"`: 2 passed after adding `models set`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 25 passed after rechecking model list/status/set/auth/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model set slice.
- `mypy src\openzues\cli.py src\openzues\services\gateway_config.py`: clean after the model set slice.
- `python -m pytest tests\test_cli.py -q -k "models_auth_add_calls_model_auth_runtime"`: 1 passed after adding `models auth add`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 23 passed after rechecking model list/status/auth/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_auth or models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 23 passed after rechecking adjacent auth/image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model auth add slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model auth add slice.
- `python -m pytest tests\test_cli.py -q -k "models_auth_paste_token_calls_model_auth_runtime"`: 1 passed after adding `models auth paste-token`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 22 passed after rechecking model list/status/auth/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_auth or models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 22 passed after rechecking adjacent auth/image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model auth paste-token slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model auth paste-token slice.
- `python -m pytest tests\test_cli.py -q -k "models_auth_setup_token_calls_model_auth_runtime"`: 1 passed after adding `models auth setup-token`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 21 passed after rechecking model list/status/auth/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_auth or models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 21 passed after rechecking adjacent auth/image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model auth setup-token slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model auth setup-token slice.
- `python -m pytest tests\test_cli.py -q -k "models_auth_login_github_copilot_calls_device_login"`: 1 passed after adding `models auth login-github-copilot`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 20 passed after rechecking model list/status/auth/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_auth or models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 20 passed after rechecking adjacent auth/image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model auth GitHub Copilot login slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model auth GitHub Copilot login slice.
- `python -m pytest tests\test_cli.py -q -k "models_auth_login_calls_model_auth_runtime_with_options"`: 1 passed after adding `models auth login`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 19 passed after rechecking model list/status/auth/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_auth or models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 19 passed after rechecking adjacent auth/image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model auth login slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model auth login slice.
- `python -m pytest tests\test_cli.py -q -k "models_auth_order_clear_removes_provider_order"`: 1 passed after adding `models auth order clear`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 18 passed after rechecking model list/status/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_auth_order or models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 18 passed after rechecking adjacent auth-order/image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the auth order clear slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the auth order clear slice.
- `python -m pytest tests\test_cli.py -q -k "models_auth_order_set_writes_agent_auth_state"`: 1 passed after adding `models auth order set`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 17 passed after rechecking model list/status/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_auth_order or models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 17 passed after rechecking adjacent auth-order/image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the auth order set slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the auth order set slice.
- `python -m pytest tests\test_cli.py -q -k "models_auth_order_get_json_reads_agent_auth_state"`: 1 passed after adding `models auth order get --json`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 16 passed after rechecking model list/status/auth-order/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_auth_order or models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 16 passed after rechecking adjacent auth-order/image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the auth order get slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the auth order get slice.
- `python -m pytest tests\test_cli.py -q -k "models_image_fallbacks_clear_empties_config_fallbacks"`: 1 passed after adding `models image-fallbacks clear`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 15 passed after rechecking model list/status/auth/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 15 passed after rechecking adjacent image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the image fallback clear slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the image fallback clear slice.
- `python -m pytest tests\test_cli.py -q -k "models_image_fallbacks_remove_updates_config"`: 1 passed after adding `models image-fallbacks remove`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 14 passed after rechecking model list/status/auth/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 14 passed after rechecking adjacent image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the image fallback remove slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the image fallback remove slice.
- `python -m pytest tests\test_cli.py -q -k "models_image_fallbacks_add_updates_config"`: 1 passed after adding `models image-fallbacks add`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 13 passed after rechecking model list/status/auth/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 13 passed after rechecking adjacent image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the image fallback add slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the image fallback add slice.
- `python -m pytest tests\test_cli.py -q -k "models_image_fallbacks_list_json_projects_config_fallbacks"`: 1 passed after adding `models image-fallbacks list --json`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 12 passed after rechecking model list/status/auth/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_image_fallbacks or models_fallbacks or models_aliases or capability_model"`: 12 passed after rechecking adjacent image fallback/fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the image fallback list slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the image fallback list slice.
- `python -m pytest tests\test_cli.py -q -k "models_fallbacks_clear_empties_config_fallbacks"`: 1 passed after adding `models fallbacks clear`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 11 passed after rechecking model list/status/auth/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_fallbacks or models_aliases or capability_model"`: 11 passed after rechecking adjacent fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model fallback clear slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model fallback clear slice.
- `python -m pytest tests\test_cli.py -q -k "models_fallbacks_remove_resolves_alias_and_updates_config"`: 1 passed after adding `models fallbacks remove` with alias resolution.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 10 passed after rechecking model list/status/auth/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_fallbacks or models_aliases or capability_model"`: 10 passed after rechecking adjacent fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model fallback remove slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model fallback remove slice.
- `python -m pytest tests\test_cli.py -q -k "models_fallbacks_add_resolves_alias_and_updates_config"`: 1 passed after adding `models fallbacks add` with alias resolution.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 9 passed after rechecking model list/status/auth/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_fallbacks or models_aliases or capability_model"`: 9 passed after rechecking adjacent fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model fallback add slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model fallback add slice.
- `python -m pytest tests\test_cli.py -q -k "models_fallbacks_list_json_projects_config_fallbacks"`: 1 passed after adding `models fallbacks list --json` over `agents.defaults.model.fallbacks`.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 8 passed after rechecking model list/status/auth/aliases/fallbacks CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_fallbacks or models_aliases or capability_model"`: 8 passed after rechecking adjacent fallback/alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model fallback list slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model fallback list slice.
- `python -m pytest tests\test_cli.py -q -k "models_aliases_remove_clears_config_model_alias"`: 1 passed after adding `models aliases remove` over the native config owner.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 7 passed after rechecking model list/status/auth/aliases CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_aliases or capability_model"`: 7 passed after rechecking adjacent alias/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model aliases remove slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model aliases remove slice.
- `python -m pytest tests\test_cli.py -q -k "models_aliases_add_updates_config_model_alias"`: 1 passed after adding `models aliases add` over the native config owner.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 6 passed after rechecking model list/status/auth/aliases CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_aliases_add_updates_config_model_alias or models_aliases_list_json_projects_config_aliases"`: 2 passed after rechecking alias list/add.
- `python -m pytest tests\test_cli.py -q -k "models_ or capability_model"`: 10 passed after rechecking adjacent model/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the model aliases add slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py src\openzues\services\gateway_config.py`: clean after the model aliases add slice.
- `python -m pytest tests\test_cli.py -q -k "models_aliases_list_json_projects_config_aliases"`: 1 passed after adding `models aliases list --json` over OpenClaw-shaped `agents.defaults.models[*].alias` config.
- `python -m pytest tests\test_cli.py -q -k "models_"`: 5 passed after rechecking model list/status/auth/aliases CLI surfaces.
- `python -m pytest tests\test_gateway_models.py -q`: 19 passed after rechecking the native model catalog read model.
- `python -m pytest tests\test_cli.py -q -k "models_ or capability_model"`: 9 passed after rechecking adjacent model/capability CLI surfaces.
- `ruff check src\openzues\cli.py src\openzues\schemas.py tests\test_cli.py`: clean after the model aliases CLI slice.
- `mypy src\openzues\cli.py src\openzues\schemas.py`: clean after the model aliases CLI slice.
- `python -m pytest tests\test_cli.py -q -k "tasks_flow_cancel_disables_task_blueprint_and_pauses_linked_missions"`: 1 passed after mapping `tasks flow cancel` to native task-blueprint disable plus linked mission pause.
- `python -m pytest tests\test_cli.py -q -k "tasks_"`: 9 passed after rechecking task list/show/audit/maintenance/flow/cancel/notify CLI surfaces.
- `python -m pytest tests\test_cli.py -q -k "tasks_ or sessions_ or cron_ or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 42 passed after rechecking adjacent CLI runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the tasks flow cancel CLI slice.
- `mypy src\openzues\cli.py`: clean after the tasks flow cancel CLI slice.
- `python -m pytest tests\test_cli.py -q -k "tasks_notify_persists_native_session_notify_policy"`: 1 passed after mapping `tasks notify` to gateway session metadata and projecting saved `taskNotifyPolicy`.
- `python -m pytest tests\test_cli.py -q -k "tasks_"`: 8 passed after rechecking task list/show/audit/maintenance/flow/cancel/notify CLI surfaces.
- `python -m pytest tests\test_cli.py -q -k "tasks_ or sessions_ or cron_ or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 41 passed after rechecking adjacent CLI runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the tasks notify CLI slice.
- `mypy src\openzues\cli.py`: clean after the tasks notify CLI slice.
- `python -m pytest tests\test_cli.py -q -k "tasks_cancel_pauses_native_mission_task"`: 1 passed after mapping `tasks cancel` to native `MissionService.pause()` for active mission-backed task records.
- `python -m pytest tests\test_cli.py -q -k "tasks_"`: 7 passed after rechecking task list/show/audit/maintenance/flow/cancel CLI surfaces.
- `python -m pytest tests\test_cli.py -q -k "tasks_ or sessions_ or cron_ or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 40 passed after rechecking adjacent CLI runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the tasks cancel CLI slice.
- `mypy src\openzues\cli.py`: clean after the tasks cancel CLI slice.
- `python -m pytest tests\test_cli.py -q -k "tasks_flow_list_json_projects_task_blueprint_flows or tasks_flow_show_json_resolves_task_blueprint_flow or tasks_list_json_filters_native_background_tasks"`: 3 passed after projecting task-blueprint-backed TaskFlows and linking mission task records with `parentFlowId`.
- `python -m pytest tests\test_cli.py -q -k "tasks_"`: 6 passed after rechecking task list/show/audit/maintenance/flow CLI surfaces.
- `python -m pytest tests\test_cli.py -q -k "tasks_ or sessions_ or cron_ or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 39 passed after rechecking adjacent CLI runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the tasks flow CLI slice.
- `mypy src\openzues\cli.py`: clean after the tasks flow CLI slice.
- `python -m pytest tests\test_cli.py -q -k "tasks_maintenance_json_previews_native_cleanup_accounting"`: 1 passed after adding the OpenClaw-shaped `tasks maintenance --json` preview envelope over native task audit findings.
- `python -m pytest tests\test_cli.py -q -k "tasks_"`: 4 passed after rechecking task list/show/audit/maintenance CLI surfaces.
- `python -m pytest tests\test_cli.py -q -k "tasks_ or sessions_ or cron_ or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 37 passed after rechecking adjacent CLI runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the tasks maintenance CLI slice.
- `mypy src\openzues\cli.py`: clean after the tasks maintenance CLI slice.
- `python -m pytest tests\test_cli.py -q -k "tasks_audit_json_filters_native_stale_running_tasks"`: 1 passed after adding OpenClaw-shaped `tasks audit` filters and summary projection over native task records.
- `python -m pytest tests\test_cli.py -q -k "tasks_"`: 3 passed after rechecking task list/show/audit CLI surfaces.
- `python -m pytest tests\test_cli.py -q -k "tasks_ or sessions_ or cron_ or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 36 passed after rechecking adjacent CLI runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the tasks audit CLI slice.
- `mypy src\openzues\cli.py`: clean after the tasks audit CLI slice.
- `python -m pytest tests\test_cli.py -q -k "tasks_list_json_filters_native_background_tasks or tasks_show_json_resolves_session_key"`: 2 passed after adding OpenClaw-shaped read-only `tasks` inspection over native mission/task-blueprint state.
- `python -m pytest tests\test_cli.py -q -k "tasks_ or sessions_ or cron_ or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 35 passed after rechecking adjacent CLI runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the tasks inspection CLI slice.
- `mypy src\openzues\cli.py`: clean after the tasks inspection CLI slice.
- `python -m pytest tests\test_cli.py -q -k "sessions_cleanup_dry_run_json_reports_stale_and_capped_rows or sessions_cleanup_enforce_deletes_stale_and_capped_metadata_rows"`: 2 passed after adding OpenClaw-shaped stale `updatedAt` and `session.maintenance.maxEntries` cleanup planning/enforce deletion over native session metadata rows.
- `python -m pytest tests\test_cli.py -q -k "sessions_cleanup"`: 5 passed after rechecking cleanup dry-run, no-op apply, fix-missing, stale pruning, and count-cap paths.
- `python -m pytest tests\test_cli.py -q -k "sessions_"`: 9 passed after rechecking adjacent session CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sessions cleanup stale/count slice.
- `mypy src\openzues\cli.py`: clean after the sessions cleanup stale/count slice.
- `python -m pytest tests\test_cli.py -q -k "sessions_cleanup_dry_run_json_reports_native_disk_budget_evictions or sessions_cleanup_enforce_deletes_disk_budget_evicted_metadata_rows"`: 2 passed after adding native disk-budget cleanup previews and enforce deletion for oldest non-active session metadata rows.
- `python -m pytest tests\test_cli.py -q -k "sessions_cleanup"`: 7 passed after rechecking cleanup dry-run, no-op apply, fix-missing, stale/count, and disk-budget paths.
- `python -m pytest tests\test_cli.py -q -k "sessions_"`: 11 passed after rechecking adjacent session CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sessions cleanup disk-budget slice.
- `mypy src\openzues\cli.py`: clean after the sessions cleanup disk-budget slice.
- `python -m pytest tests\test_cli.py -q -k "sessions_cleanup_all_agents_dry_run_json_groups_native_agent_summaries"`: 1 passed after adding OpenClaw-shaped grouped `stores` summaries for `sessions cleanup --all-agents --dry-run --json`.
- `python -m pytest tests\test_cli.py -q -k "sessions_cleanup"`: 8 passed after rechecking cleanup dry-run, no-op apply, fix-missing, stale/count, disk-budget, and all-agent grouped JSON paths.
- `python -m pytest tests\test_cli.py -q -k "sessions_"`: 12 passed after rechecking adjacent session CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sessions cleanup all-agents grouping slice.
- `mypy src\openzues\cli.py`: clean after the sessions cleanup all-agents grouping slice.
- `python -m pytest tests\test_cli.py -q -k "sessions_cleanup_fix_missing_enforce_deletes_metadata_rows"`: 1 passed after mapping `sessions cleanup --enforce --fix-missing` to native metadata pruning.
- `python -m pytest tests\test_cli.py -q -k "sessions_cleanup"`: 3 passed after rechecking cleanup dry-run, no-op apply, and fix-missing paths.
- `python -m pytest tests\test_cli.py -q -k "sessions_ or sandbox_list_json or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 11 passed after rechecking adjacent session/runtime CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sessions cleanup fix-missing slice.
- `mypy src\openzues\cli.py`: clean after the sessions cleanup fix-missing slice.
- `python -m pytest tests\test_cli.py -q -k "sessions_cleanup_enforce_json_returns_applied_noop_summary or sessions_cleanup_dry_run_json_calls_sessions_list_owner"`: 2 passed after adding cleanup enforce/apply no-op summaries.
- `python -m pytest tests\test_cli.py -q -k "sessions_ or sandbox_list_json or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 10 passed after rechecking adjacent session/runtime CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sessions cleanup no-op apply slice.
- `mypy src\openzues\cli.py`: clean after the sessions cleanup no-op apply slice.
- `python -m pytest tests\test_cli.py -q -k "sessions_cleanup_dry_run_json_calls_sessions_list_owner"`: 1 passed after adding `sessions cleanup --dry-run --json` preview over `sessions.list`.
- `python -m pytest tests\test_cli.py -q -k "sessions_inventory_json_calls_gateway_method_owner or sessions_spawn_json_calls_gateway_method_owner or sessions_wait_human_output_calls_agent_wait"`: 3 passed after rechecking adjacent session subcommands.
- `python -m pytest tests\test_cli.py -q -k "sessions_ or sandbox_list_json or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 9 passed after rechecking adjacent session/runtime CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sessions cleanup dry-run slice.
- `mypy src\openzues\cli.py`: clean after the sessions cleanup dry-run slice.
- `python -m pytest tests\test_cli.py -q -k "sessions_inventory_json_calls_gateway_method_owner"`: 1 passed after adding top-level `sessions --json` over `sessions.list`.
- `python -m pytest tests\test_cli.py -q -k "sessions_inventory_rejects_invalid_active_minutes"`: 1 passed after matching OpenClaw's positive `--active` validation.
- `python -m pytest tests\test_cli.py -q -k "sessions_ or sandbox_list_json or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 8 passed after rechecking adjacent session/runtime CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sessions inventory CLI slice.
- `mypy src\openzues\cli.py`: clean after the sessions inventory CLI slice.
- `python -m pytest tests\test_cli.py -q -k "cron_add_at_timezone_normalizes_offsetless_datetime or cron_add_at_timezone_rejects_nonexistent_dst_gap or cron_add_at_timezone_allows_relative_duration or cron_add_at_offsetless_datetime_without_timezone_defaults_to_utc"`: 4 passed after matching OpenClaw `cron add --at` timezone/date parsing.
- `python -m pytest tests\test_cli.py -q -k "cron_"`: 24 passed after rechecking adjacent cron CLI surfaces.
- `ruff check pyproject.toml src\openzues\cli.py tests\test_cli.py`: clean after adding native `tzdata` timezone support for Windows cron CLI parsing.
- `mypy src\openzues\cli.py`: clean after the cron `--at` parser slice.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_abort_persists_partial_assistant_transcript_like_openclaw or chat_send_stop_persists_abort_partial_with_stop_command_origin or chat_abort"`: 11 passed after persisting OpenClaw-shaped abort partials.
- `python -m pytest tests\test_gateway_nodes_api.py -q -k "chat_abort"`: 2 passed after rechecking HTTP abort paths with the metadata-backed transcript store.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_abort or chat_history or sessions_history"`: 31 passed after rechecking adjacent transcript projections.
- `python -m pytest tests\test_gateway_sessions.py -q -k "message_payloads_surface or transcript_usage or control_chat"`: 5 passed after rechecking shared transcript/session read-model paths.
- `ruff check src\openzues\database.py src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`: clean after the abort partial persistence slice.
- `mypy src\openzues\database.py src\openzues\services\gateway_node_methods.py`: clean after the abort partial persistence slice.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_abort"`: 9 passed after adding OpenClaw-shaped `chat.abort` requester ownership checks.
- `python -m pytest tests\test_gateway_nodes_api.py -q -k "chat_abort"`: 2 passed after rechecking HTTP gateway abort paths.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "chat_abort or sessions_steer or sessions_abort or compaction_restore"`: 27 passed after rechecking adjacent internal abort callers.
- `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`: clean after the abort ownership slice.
- `mypy src\openzues\services\gateway_node_methods.py`: clean after the abort ownership slice.
- `python -m pytest tests\test_codex_rpc.py -q`: 9 passed after adding the explicit workspace-write sandbox override for Windows child turns.
- `python -m pytest tests\test_gateway_sandbox_spawn.py -q`: 2 passed after adding the production RuntimeManager-backed sandbox child-turn adapter.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_rejects_required_sandbox or sessions_spawn_required_sandbox"`: 3 passed after persisting sandbox runtime policy metadata through `sessions.spawn`.
- `python -m pytest tests\test_gateway_thread_binding.py -q`: 3 passed after requiring `threadBindingReady=true` for successful route-backed subagent thread binding results.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_thread_mode or sessions_spawn_session_mode"`: 5 passed after wiring the production binder while preserving the no-hook error.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "thread_mode"`: 4 passed after rechecking thread-mode gateway rejection and binding paths.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "thread_mode_delivers_initial_child_run"`: 1 passed after sending initial thread-bound child runs with bound route kwargs.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_thread_mode or thread_mode_delivers_initial_child_run or sessions_spawn_session_mode"`: 6 passed after rechecking adjacent thread-mode spawn paths.
- `ruff check src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_node_methods.py`: clean after the thread-bound initial delivery slice.
- `mypy src\openzues\services\gateway_node_methods.py src\openzues\app.py`: clean after the thread-bound initial delivery slice.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "thread_bound_completion_uses_completion_delivery_route"`: 1 passed after routing thread-bound completion announcements through direct channel delivery.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_announces_spawn_completion or thread_bound_completion_uses_completion_delivery_route or no_completion_announce or completion_dedupe or sessions_spawn_thread_mode"`: 7 passed after rechecking adjacent completion and thread-mode paths.
- `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`: clean after the thread-bound completion delivery slice.
- `mypy src\openzues\services\gateway_node_methods.py`: clean after the thread-bound completion delivery slice.
- `ruff check src\openzues\services\gateway_thread_binding.py src\openzues\services\gateway_node_methods.py src\openzues\app.py tests\test_gateway_thread_binding.py tests\test_gateway_node_methods.py`: clean after the route-backed thread binder slice.
- `mypy src\openzues\services\gateway_thread_binding.py src\openzues\services\gateway_node_methods.py src\openzues\app.py`: clean after the route-backed thread binder slice.
- `python -m pytest tests\test_gateway_acp_spawn.py -q`: 2 passed after adding the native ACP spawn service.
- `python -m pytest tests\test_gateway_acp_spawn.py -q`: 3 passed after adding the ACP `mode="session"` / `thread=true` guard.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "acp and spawn"`: 4 passed after rechecking the gateway ACP spawn projection.
- `ruff check src\openzues\services\gateway_acp_spawn.py tests\test_gateway_acp_spawn.py`: clean after the ACP session-mode guard.
- `mypy src\openzues\services\gateway_acp_spawn.py`: clean after the ACP session-mode guard.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_reset_closes_acp_runtime_before_resetting_metadata or sessions_delete_closes_acp_runtime_before_metadata_delete"`: 2 passed after adding ACP runtime cleanup before session reset/delete mutation.
- `python -m pytest tests\test_gateway_acp_spawn.py -q`: 4 passed after adding RuntimeManager ACP cleanup adapter coverage.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_reset or sessions_delete"`: 11 passed after rechecking adjacent session reset/delete paths.
- `ruff check src\openzues\services\gateway_acp_spawn.py src\openzues\services\gateway_node_methods.py tests\test_gateway_acp_spawn.py tests\test_gateway_node_methods.py`: clean after the ACP cleanup slice.
- `mypy src\openzues\services\gateway_acp_spawn.py src\openzues\services\gateway_node_methods.py`: clean after the ACP cleanup slice.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn or agent_wait or send_uses_channel_message_runtime or send_preserves_provider_native or tools_invoke"`: 98 passed after ACP, sandbox, thread-binder, provider-send, and plugin-runtime slices.
- `python -m pytest tests\test_ops_mesh.py -q -k "send_direct_channel_message"`: 15 passed after preserving provider-native send options and Telegram document/reply/silent/thread payloads.
- `python -m pytest tests\test_ops_mesh.py -q -k "send_direct_channel_message or send_direct_channel_poll or replay_outbound_deliveries_retries_saved_failed"`: 34 passed after widening provider result metadata, Slack/Discord native option handling, and provider-backed saved send/poll replay.
- `python -m pytest tests\test_ops_mesh.py -q`: 96 passed after the provider-native outbound replay and metadata slice.
- `ruff check src\openzues\services\gateway_outbound_runtime.py src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`: clean after the provider-native outbound replay and metadata slice.
- `mypy src\openzues\services\gateway_outbound_runtime.py src\openzues\services\ops_mesh.py`: clean after the provider-native outbound replay and metadata slice.
- `python -m pytest tests\test_cli.py -q -k "route_backed_slack_probe"`: 1 passed after adding the route-backed Slack channel probe.
- `python -m pytest tests\test_cli.py -q -k "route_backed_telegram_probe"`: 1 passed after adding the route-backed Telegram channel probe.
- `python -m pytest tests\test_cli.py -q -k "route_backed_discord_probe"`: 1 passed after adding the route-backed Discord channel probe.
- `python -m pytest tests\test_cli.py -q -k "whatsapp_no_hook_probe"`: 1 passed after aligning WhatsApp with upstream's no-account-probe posture.
- `python -m pytest tests\test_cli.py -q -k "route_backed_slack_probe or route_backed_telegram_probe or route_backed_discord_probe or whatsapp_no_hook_probe or channels_status_json or channels_capabilities_json"`: 9 passed after rechecking channel probe CLI surfaces.
- `python -m pytest tests\test_cli.py -q -k "channels_status_json or channels_capabilities_json or channels_resolve_json"`: 8 passed after rechecking channel CLI surfaces.
- `python -m pytest tests\test_cli.py -q -k "route_backed_slack_channel_resolver"`: 1 passed after adding route-backed Slack channel resolution.
- `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_slack_channel_resolver or channels_status_json or route_backed_slack_probe"`: 10 passed after rechecking adjacent channel CLI paths.
- `ruff check src\openzues\services\ops_mesh.py src\openzues\app.py src\openzues\cli.py tests\test_cli.py`: clean after the Slack channel resolver slice.
- `mypy src\openzues\services\ops_mesh.py src\openzues\app.py src\openzues\cli.py`: clean after the Slack channel resolver slice.
- `python -m pytest tests\test_cli.py -q -k "route_backed_slack_user_resolver"`: 1 passed after adding route-backed Slack user resolution.
- `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json or route_backed_slack_probe"`: 11 passed after rechecking adjacent channel CLI paths.
- `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`: clean after the Slack user resolver slice.
- `mypy src\openzues\services\ops_mesh.py`: clean after the Slack user resolver slice.
- `python -m pytest tests\test_cli.py -q -k "auto_groups_route_backed_slack_targets"`: 1 passed after adding OpenClaw-style auto-kind live resolver grouping.
- `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json or route_backed_slack_probe"`: 12 passed after rechecking adjacent channel CLI paths.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the auto-kind resolver grouping slice.
- `mypy src\openzues\cli.py`: clean after the auto-kind resolver grouping slice.
- `python -m pytest tests\test_cli.py -q -k "route_backed_telegram_user_resolver"`: 1 passed after adding route-backed Telegram username resolution.
- `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_telegram_user_resolver or route_backed_telegram_probe or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json"`: 13 passed after rechecking adjacent channel CLI paths.
- `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`: clean after the Telegram username resolver slice.
- `mypy src\openzues\services\ops_mesh.py`: clean after the Telegram username resolver slice.
- `python -m pytest tests\test_cli.py -q -k "route_backed_discord_channel_resolver"`: 1 passed after adding route-backed Discord channel-id resolution.
- `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_discord_channel_resolver or route_backed_discord_probe or route_backed_telegram_user_resolver or route_backed_telegram_probe or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json"`: 14 passed after rechecking adjacent channel CLI paths.
- `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`: clean after the Discord channel resolver slice.
- `mypy src\openzues\services\ops_mesh.py`: clean after the Discord channel resolver slice.
- `python -m pytest tests\test_cli.py -q -k "route_backed_discord_guild_channel_resolver"`: 1 passed after adding route-backed Discord guild-qualified channel-name resolution.
- `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_discord_channel_resolver or route_backed_discord_guild_channel_resolver or route_backed_discord_probe or route_backed_telegram_user_resolver or route_backed_telegram_probe or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json"`: 15 passed after rechecking adjacent channel CLI paths.
- `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`: clean after the Discord guild-channel resolver slice.
- `mypy src\openzues\services\ops_mesh.py`: clean after the Discord guild-channel resolver slice.
- `python -m pytest tests\test_cli.py -q -k "route_backed_discord_global_channel_resolver"`: 1 passed after adding route-backed Discord global channel-name resolution.
- `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_discord_channel_resolver or route_backed_discord_guild_channel_resolver or route_backed_discord_global_channel_resolver or route_backed_discord_probe or route_backed_telegram_user_resolver or route_backed_telegram_probe or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json"`: 16 passed after rechecking adjacent channel CLI paths.
- `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`: clean after the Discord global-channel resolver slice.
- `mypy src\openzues\services\ops_mesh.py`: clean after the Discord global-channel resolver slice.
- `python -m pytest tests\test_cli.py -q -k "route_backed_discord_user_resolver"`: 1 passed after adding route-backed Discord guild-member user resolution.
- `python -m pytest tests\test_cli.py -q -k "channels_resolve_json or route_backed_discord_user_resolver or route_backed_discord_channel_resolver or route_backed_discord_guild_channel_resolver or route_backed_discord_global_channel_resolver or route_backed_discord_probe or route_backed_telegram_user_resolver or route_backed_telegram_probe or auto_groups_route_backed_slack_targets or route_backed_slack_channel_resolver or route_backed_slack_user_resolver or channels_status_json"`: 17 passed after rechecking adjacent channel CLI paths.
- `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`: clean after the Discord user resolver slice.
- `mypy src\openzues\services\ops_mesh.py`: clean after the Discord user resolver slice.
- `python -m pytest tests\test_ops_mesh.py -q -k "telegram_topic_target"`: 1 passed after parsing Telegram topic-qualified send targets.
- `python -m pytest tests\test_ops_mesh.py -q -k "send_direct_channel_message_uses_telegram_native or telegram_topic_target or send_direct_channel_poll_uses_telegram"`: 4 passed after rechecking adjacent Telegram direct send/poll paths.
- `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`: clean after the Telegram topic-target slice.
- `mypy src\openzues\services\ops_mesh.py`: clean after the Telegram topic-target slice.
- `python -m pytest tests\test_ops_mesh.py -q -k "topic_to_parent"`: 1 passed after allowing Telegram parent supergroup routes to match topic-qualified targets.
- `python -m pytest tests\test_ops_mesh.py -q -k "send_direct_channel_message_uses_telegram_native or telegram_topic_target or topic_to_parent or send_direct_channel_poll_uses_telegram"`: 5 passed after rechecking adjacent Telegram direct send/poll paths.
- `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`: clean after the Telegram topic parent-route slice.
- `mypy src\openzues\services\ops_mesh.py`: clean after the Telegram topic parent-route slice.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "channels_status"`: 2 passed after rechecking the gateway method projection.
- `ruff check src\openzues\app.py src\openzues\cli.py src\openzues\services\gateway_channels.py src\openzues\services\ops_mesh.py tests\test_cli.py`: clean after the Slack probe slice.
- `mypy src\openzues\app.py src\openzues\cli.py src\openzues\services\gateway_channels.py src\openzues\services\ops_mesh.py`: clean after the Slack probe slice.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "registry_plugin_executor or core_mapping_before_registry_plugin or registry_owner_only or skips_disabled_registry_plugin_executor"`: 4 passed after adding ordered registry-backed plugin executor resolution.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_invoke"`: 54 passed after rechecking plugin/core `tools.invoke` behavior.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "config_get_returns_control_ui_bootstrap_snapshot or config_open_file_returns_snapshot_path_when_owner_is_wired"`: 2 passed after omitting absent `session`/`tools` sections from bootstrap config snapshots.
- `python -m pytest tests\test_gateway_node_methods.py -q`: 682 passed after the ordered plugin registry slice and adjacent config snapshot cleanup.
- `ruff check src\openzues\services\gateway_config.py src\openzues\services\gateway_plugin_runtime.py tests\test_gateway_node_methods.py`: clean after the ordered plugin registry slice and config snapshot cleanup.
- `mypy src\openzues\services\gateway_config.py src\openzues\services\gateway_plugin_runtime.py src\openzues\services\gateway_node_methods.py`: clean after the ordered plugin registry slice and config snapshot cleanup.
- `python -m pytest tests\test_cli.py -q -k "routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 2 passed after adding `routes send` / `routes poll`.
- `python -m pytest tests\test_cli.py -q -k "routes_"`: 18 passed after rechecking adjacent route CLI surfaces; existing aiosqlite closed-loop warnings remain.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the direct route send/poll CLI slice.
- `mypy src\openzues\cli.py`: clean after the direct route send/poll CLI slice.
- `python -m pytest tests\test_cli.py -q -k "sandbox_list_json"`: 2 passed after adding OpenClaw-shaped `sandbox list --json` inventory from saved sandbox runtime metadata.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sandbox inventory CLI slice.
- `mypy src\openzues\cli.py`: clean after the sandbox inventory CLI slice.
- `python -m pytest tests\test_cli.py -q -k "sessions_spawn_json_calls_gateway_method_owner or sessions_wait_human_output_calls_agent_wait"`: 2 passed after adding `sessions spawn` / `sessions wait` wrappers around `GatewayNodeMethodService`.
- `python -m pytest tests\test_cli.py -q -k "sessions_ or sandbox_list_json or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 6 passed after rechecking adjacent CLI runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sessions spawn/wait CLI slice.
- `mypy src\openzues\cli.py`: clean after the sessions spawn/wait CLI slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_projects_hermes_plugin_inventory or plugins_list_enabled_filters_loaded_plugins"`: 2 passed after adding `plugins list` over the Hermes/OpenZues plugin inventory deck.
- `python -m pytest tests\test_cli.py -q -k "plugins_list or sessions_ or sandbox_list_json or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 8 passed after rechecking adjacent CLI runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin list CLI slice.
- `mypy src\openzues\cli.py`: clean after the plugin list CLI slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_doctor_human_reports_no_plugin_issues or plugins_doctor_human_reports_error_plugins"`: 2 passed after adding `plugins doctor` over the projected plugin inventory.
- `python -m pytest tests\test_cli.py -q -k "plugins_ or sessions_ or sandbox_list_json or routes_send_json_calls_native_direct_send_runtime or routes_poll_human_output_calls_native_direct_poll_runtime"`: 10 passed after rechecking adjacent CLI runtime surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin doctor CLI slice.
- `mypy src\openzues\cli.py`: clean after the plugin doctor CLI slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_inspect_json_returns_plugin_detail or plugins_info_alias_json_uses_inspect_payload"`: 2 passed after adding `plugins inspect` and the `plugins info` alias.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 6 passed after rechecking plugin list/doctor/inspect/info together.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin inspect/info CLI slice.
- `mypy src\openzues\cli.py`: clean after the plugin inspect/info CLI slice.
- `python -m pytest tests\test_cli.py -q -k "sandbox_explain_json_uses_saved_sandbox_metadata"`: 1 passed after adding metadata-backed `sandbox explain`.
- `python -m pytest tests\test_cli.py -q -k "sandbox_ or sessions_ or plugins_"`: 11 passed after rechecking adjacent sandbox/session/plugin CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sandbox explain CLI slice.
- `mypy src\openzues\cli.py`: clean after the sandbox explain CLI slice.
- `python -m pytest tests\test_cli.py -q -k "sandbox_recreate"`: 2 passed after adding `sandbox recreate` target validation and `--force` cleanup for saved sandbox runtime metadata.
- `python -m pytest tests\test_cli.py -q -k "sandbox_ or sessions_ or plugins_"`: 13 passed after rechecking adjacent sandbox/session/plugin CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sandbox recreate CLI slice.
- `mypy src\openzues\cli.py`: clean after the sandbox recreate CLI slice.
- `python -m pytest tests\test_cli.py -q -k "models_list_json"`: 1 passed after adding `models list --json` over the production gateway method owner.
- `python -m pytest tests\test_cli.py -q -k "models_list_json or sandbox_ or sessions_ or plugins_"`: 14 passed after rechecking adjacent CLI runtime command registration.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the models list CLI slice.
- `mypy src\openzues\cli.py`: clean after the models list CLI slice.
- `python -m pytest tests\test_cli.py -q -k "health_json_surfaces"`: 1 passed after adding top-level `health --json` over the live gateway health/readiness API owners.
- `python -m pytest tests\test_cli.py -q -k "health_json_surfaces or status_json or gateway_doctor"`: 9 passed after rechecking adjacent top-level health/status/gateway CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the health CLI slice.
- `mypy src\openzues\cli.py`: clean after the health CLI slice.
- `python -m pytest tests\test_cli.py -q -k "models_status_json"`: 1 passed after adding bounded `models status --json` default/resolved/allowed/auth projection.
- `python -m pytest tests\test_cli.py -q -k "models_ or health_json_surfaces or sandbox_ or sessions_ or plugins_"`: 16 passed after rechecking adjacent CLI runtime command surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the models status CLI slice.
- `mypy src\openzues\cli.py`: clean after the models status CLI slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_marketplace_list"`: 1 passed after adding local `plugins marketplace list --json` manifest parsing.
- `python -m pytest tests\test_cli.py -q -k "plugins_ or models_ or health_json_surfaces"`: 10 passed after rechecking adjacent plugin/model/health CLI command surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin marketplace list CLI slice.
- `mypy src\openzues\cli.py`: clean after the plugin marketplace list CLI slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_enable_disable_json"`: 1 passed after adding `plugins enable` / `plugins disable` JSON config mutation.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 8 passed after rechecking plugin list/doctor/inspect/info/marketplace/toggle CLI surfaces.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "config_write_methods or config_schema_lookup_accepts_scoped_plugin_entry_paths"`: 5 passed after rechecking adjacent config mutation/schema behavior.
- `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py src\openzues\schemas.py tests\test_cli.py`: clean after the plugin toggle CLI slice.
- `mypy src\openzues\cli.py src\openzues\services\gateway_config.py src\openzues\schemas.py`: clean after the plugin toggle CLI slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_install_marketplace_json_persists_local_manifest_entry"`: 1 passed after adding local marketplace plugin install persistence.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 9 passed after rechecking plugin list/doctor/inspect/info/marketplace/install/toggle CLI surfaces.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "config_write_methods or config_schema_lookup_accepts_scoped_plugin_entry_paths"`: 5 passed after rechecking adjacent config mutation/schema behavior.
- `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the local marketplace plugin install slice.
- `mypy src\openzues\cli.py src\openzues\services\gateway_config.py`: clean after the local marketplace plugin install slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_uninstall_json_removes_native_install_metadata"`: 1 passed after adding native plugin uninstall metadata cleanup.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 10 passed after rechecking plugin list/doctor/inspect/info/marketplace/install/uninstall/toggle CLI surfaces.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "config_write_methods or config_schema_lookup_accepts_scoped_plugin_entry_paths"`: 5 passed after rechecking adjacent config mutation/schema behavior.
- `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the native plugin uninstall slice.
- `mypy src\openzues\cli.py src\openzues\services\gateway_config.py`: clean after the native plugin uninstall slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_update_json_refreshes_local_marketplace_install"`: 1 passed after adding local marketplace plugin update dry-run/apply behavior.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 11 passed after rechecking plugin list/doctor/inspect/info/marketplace/install/update/uninstall/toggle CLI surfaces.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "config_write_methods or config_schema_lookup_accepts_scoped_plugin_entry_paths"`: 5 passed after rechecking adjacent config mutation/schema behavior.
- `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py tests\test_cli.py`: clean after the local marketplace plugin update slice.
- `mypy src\openzues\cli.py src\openzues\services\gateway_config.py`: clean after the local marketplace plugin update slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_doctor_human_reports_compatibility_notices"`: 1 passed after adding plugin doctor compatibility notices.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 12 passed after rechecking plugin list/doctor/inspect/info/marketplace/install/update/uninstall/toggle CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin doctor compatibility slice.
- `mypy src\openzues\cli.py`: clean after the plugin doctor compatibility slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_includes_saved_config_install_records"`: 1 passed after merging saved plugin config/install records into `plugins list`.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 13 passed after rechecking plugin list/doctor/inspect/info/marketplace/install/update/uninstall/toggle CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin saved-record inventory slice.
- `mypy src\openzues\cli.py`: clean after the plugin saved-record inventory slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_inspect_all_json_includes_saved_install_records"`: 1 passed after preserving saved plugin install metadata in `plugins inspect --all --json`.
- `python -m pytest tests\test_cli.py -q -k "plugins_inspect or plugins_info or plugins_list_json_includes_saved_config_install_records"`: 4 passed after rechecking adjacent inspect/info/list plugin CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin inspect install metadata slice.
- `mypy src\openzues\cli.py`: clean after the plugin inspect install metadata slice.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_discovers_openclaw_manifest_load_paths"`: 1 passed after adding metadata-only `openclaw.plugin.json` discovery for configured `plugins.load.paths`.
- `python -m pytest tests\test_cli.py -q -k "plugins_list_json_discovers_openclaw_manifest_load_paths or plugins_list_json_includes_saved_config_install_records or plugins_inspect_json_returns_plugin_detail"`: 3 passed after rechecking adjacent list/inspect behavior.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 15 passed after rechecking plugin list/doctor/inspect/info/marketplace/install/update/uninstall/toggle CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin load-path manifest metadata slice.
- `mypy src\openzues\cli.py`: clean after the plugin load-path manifest metadata slice.
- `python -m pytest tests\test_cli.py -q -k "status_json_breadth_flags"`: 1 passed after adding top-level `status --json` breadth flags and timeout forwarding.
- `python -m pytest tests\test_cli.py -q -k "status_json or health_json"`: 8 passed after rechecking adjacent status and health JSON surfaces.
- `python -m pytest tests\test_cli.py -q -k "emit_status_human_output or status_json_reuses_gateway_contract"`: 2 passed after rechecking adjacent status output behavior.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the status JSON breadth slice.
- `mypy src\openzues\cli.py`: clean after the status JSON breadth slice.
- `python -m pytest tests\test_cli.py -q -k "status_all_human_output"`: 1 passed after adding OpenClaw-shaped text `status --all` report output.
- `python -m pytest tests\test_cli.py -q -k "status_all_human_output or status_json or emit_status_human_output"`: 9 passed after rechecking adjacent status human/JSON emitters.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the text `status --all` slice.
- `mypy src\openzues\cli.py`: clean after the text `status --all` slice.
- `python -m pytest tests\test_cli.py -q -k "sandbox_list_human_output"`: 1 passed after adding OpenClaw's human sandbox list total/running summary.
- `python -m pytest tests\test_cli.py -q -k "sandbox_list or sandbox_recreate or sandbox_explain"`: 6 passed after rechecking adjacent sandbox CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sandbox list summary slice.
- `mypy src\openzues\cli.py`: clean after the sandbox list summary slice.
- `python -m pytest tests\test_cli.py -q -k "sandbox_list_human_output_warns"`: 1 passed after adding OpenClaw's sandbox list config-mismatch recreate hint.
- `python -m pytest tests\test_cli.py -q -k "sandbox_list or sandbox_recreate or sandbox_explain"`: 7 passed after rechecking adjacent sandbox CLI surfaces with mismatch metadata.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the sandbox mismatch summary slice.
- `mypy src\openzues\cli.py`: clean after the sandbox mismatch summary slice.
- `python -m pytest tests\test_cli.py -q -k "acp_bridge_command or acp_client_command"`: 2 passed after adding top-level ACP bridge/client command boundaries.
- `python -m pytest tests\test_cli.py -q -k "acp_ or sessions_spawn_json_calls_gateway_method_owner or sessions_wait_human_output_calls_agent_wait"`: 4 passed after rechecking adjacent ACP/session CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the ACP CLI boundary slice.
- `mypy src\openzues\cli.py`: clean after the ACP CLI boundary slice.
- `python -m pytest tests\test_cli.py -q -k "acp_bridge_rejects_mixed_token_sources or acp_bridge_reports_missing_token_file or acp_bridge_warns_for_inline_secrets"`: 3 passed after adding ACP CLI secret-source validation and inline secret warnings.
- `python -m pytest tests\test_cli.py -q -k "acp_ or sessions_spawn_json_calls_gateway_method_owner or sessions_wait_human_output_calls_agent_wait"`: 7 passed after rechecking adjacent ACP/session CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the ACP CLI option validation slice.
- `mypy src\openzues\cli.py`: clean after the ACP CLI option validation slice.
- `python -m pytest tests\test_cli.py -q -k "acp_client"`: 4 passed after adding the native ACP client spawn-plan helper and fakeable runner seam.
- `python -m pytest tests\test_cli.py -q -k "acp_bridge or acp_client"`: 8 passed after rechecking adjacent ACP bridge/client CLI boundaries.
- `ruff check src\openzues\cli.py src\openzues\services\acp_client_runtime.py tests\test_cli.py`: clean after the ACP client spawn-plan slice.
- `mypy src\openzues\cli.py src\openzues\services\acp_client_runtime.py`: clean after the ACP client spawn-plan slice.
- `python -m pytest tests\test_cli.py -q -k "capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 2 passed after adding OpenClaw's metadata-only `infer` / `capability` list and inspect surfaces.
- `python -m pytest tests\test_cli.py -q -k "capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias or models_list or models_status"`: 4 passed after rechecking adjacent CLI model/runtime metadata commands.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer` / `capability` metadata slice.
- `mypy src\openzues\cli.py`: clean after the `infer` / `capability` metadata slice.
- `python -m pytest tests\test_cli.py -q -k "infer_model_list_json_uses_openclaw_catalog_shape or capability_model_inspect_json_matches_provider_model_ref or infer_model_providers_json_groups_catalog_by_provider"`: 3 passed after adding OpenClaw's nested `infer` / `capability model` catalog commands.
- `python -m pytest tests\test_cli.py -q -k "infer_model or capability_model or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias or models_list or models_status"`: 7 passed after rechecking adjacent CLI model/capability metadata commands.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer` / `capability model` catalog slice.
- `mypy src\openzues\cli.py`: clean after the `infer` / `capability model` catalog slice.
- `python -m pytest tests\test_cli.py -q -k "infer_model_auth_status_json_reuses_model_status_payload"`: 1 passed after adding OpenClaw's nested `infer model auth status` alias over the native model status projection.
- `python -m pytest tests\test_cli.py -q -k "infer_model or capability_model or models_status or models_list"`: 6 passed after rechecking adjacent model/capability CLI commands.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer model auth status` slice.
- `mypy src\openzues\cli.py`: clean after the `infer model auth status` slice.
- `python -m pytest tests\test_cli.py -q -k "capability_model_run_rejects_local_and_gateway_together or infer_model_run_json_wraps_local_control_chat_reply or capability_model_run_gateway_json_wraps_agent_payloads"`: 3 passed after adding OpenClaw's `infer` / `capability model run` transport resolution and capability envelope.
- `python -m pytest tests\test_cli.py -q -k "infer_model or capability_model or models_status or models_list or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 11 passed after rechecking adjacent model/capability CLI commands.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer model run` envelope slice.
- `mypy src\openzues\cli.py`: clean after the `infer model run` envelope slice.
- `python -m pytest tests\test_cli.py -q -k "infer_tts_providers_json_projects_native_provider_catalog or capability_tts_providers_rejects_local_and_gateway_together"`: 2 passed after adding OpenClaw's `infer` / `capability tts providers` catalog surface.
- `python -m pytest tests\test_cli.py -q -k "infer_tts or capability_tts or infer_model or capability_model or models_status or models_list"`: 11 passed after rechecking adjacent provider/model CLI commands.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer tts providers` slice.
- `mypy src\openzues\cli.py`: clean after the `infer tts providers` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_tts_status_json_tags_gateway_transport"`: 1 passed after adding OpenClaw's `infer` / `capability tts status` command.
- `python -m pytest tests\test_cli.py -q -k "infer_tts or capability_tts or infer_model or capability_model or models_status or models_list"`: 12 passed after rechecking adjacent provider/model CLI commands.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer tts status` slice.
- `mypy src\openzues\cli.py`: clean after the `infer tts status` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_tts_enable_disable_json_calls_native_state_methods or capability_tts_set_provider_json_calls_native_state_method"`: 2 passed after adding OpenClaw's `infer` / `capability tts` state mutation commands.
- `python -m pytest tests\test_cli.py -q -k "infer_tts or capability_tts or infer_model or capability_model or models_status or models_list"`: 14 passed after rechecking adjacent provider/model CLI commands.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer tts` state mutation slice.
- `mypy src\openzues\cli.py`: clean after the `infer tts` state mutation slice.
- `python -m pytest tests\test_cli.py -q -k "infer_tts_convert_gateway_json_wraps_native_audio_result"`: 1 passed after adding OpenClaw's `infer` / `capability tts convert` envelope over the native TTS runtime method.
- `python -m pytest tests\test_cli.py -q -k "infer_tts or capability_tts or infer_model or capability_model or models_status or models_list"`: 15 passed after rechecking adjacent provider/model CLI commands.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer tts convert` slice.
- `mypy src\openzues\cli.py`: clean after the `infer tts convert` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_tts_voices_json_filters_projected_provider_voices"`: 1 passed after adding OpenClaw's `infer` / `capability tts voices` provider projection.
- `python -m pytest tests\test_cli.py -q -k "infer_tts or capability_tts or infer_model or capability_model or models_status or models_list"`: 16 passed after rechecking adjacent provider/model CLI commands.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer tts voices` slice.
- `mypy src\openzues\cli.py`: clean after the `infer tts voices` slice.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_launch_applies_provider_model_override_before_dispatch or agent_launch_applies_model_only_override_before_dispatch"`: 2 passed after making gateway `agent` persist OpenClaw-style model-only and provider/model overrides before dispatch.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_launch_applies_provider_model_override_before_dispatch or agent_launch_applies_model_only_override_before_dispatch or agent_launch_ignores_blank_optional_unsupported_string_fields or agent_launch_treats_last_channel_hints_as_omitted or agent_launch_accepts_matching_session_key_and_session_id_selectors"`: 6 passed after rechecking adjacent gateway `agent` launch behavior.
- `python -m pytest tests\test_cli.py -q -k "capability_model_run_gateway_json_wraps_agent_payloads or infer_model_run_json_wraps_local_control_chat_reply or capability_model_run_rejects_local_and_gateway_together"`: 3 passed after rechecking the `infer` / `capability model run` CLI envelope against gateway agent dispatch.
- `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py tests\test_cli.py src\openzues\cli.py`: clean after the gateway `agent` provider/model override dispatch slice.
- `mypy src\openzues\services\gateway_node_methods.py src\openzues\cli.py`: clean after the gateway `agent` provider/model override dispatch slice.
- `python -m pytest tests\test_cli.py -q -k "capability_model_run_gateway_json_wraps_agent_payloads"`: 1 passed after gateway `infer` / `capability model run` began waiting on `agent.wait` for final payloads.
- `python -m pytest tests\test_cli.py -q -k "capability_model_run_gateway_json_wraps_agent_payloads or infer_model_run_json_wraps_local_control_chat_reply or capability_model_run_rejects_local_and_gateway_together"`: 3 passed after rechecking adjacent model-run transport behavior.
- `python -m pytest tests\test_cli.py -q -k "infer_model or capability_model or models_status or models_list or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 11 passed after rechecking adjacent model/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the gateway `model.run` final-wait slice.
- `mypy src\openzues\cli.py`: clean after the gateway `model.run` final-wait slice.
- `python -m pytest tests\test_cli.py -q -k "infer_model_auth_login_calls_model_auth_runtime or capability_model_auth_logout_json_calls_model_auth_runtime"`: 2 passed after adding OpenClaw's nested `infer` / `capability model auth login|logout` commands over a fakeable native model-auth runtime hook.
- `python -m pytest tests\test_cli.py -q -k "infer_model_auth or capability_model_auth or infer_model or capability_model or models_status or models_list"`: 11 passed after rechecking adjacent model auth/catalog/run CLI commands.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer model auth login|logout` command slice.
- `mypy src\openzues\cli.py`: clean after the `infer model auth login|logout` command slice.
- `python -m pytest tests\test_cli.py -q -k "infer_image_providers_json_projects_native_image_registry"`: 1 passed after adding OpenClaw's `infer` / `capability image providers` projection over a fakeable native image registry.
- `python -m pytest tests\test_cli.py -q -k "infer_image_providers or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias or infer_model or capability_model or infer_tts or capability_tts"`: 19 passed after rechecking adjacent capability metadata/model/TTS/image CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer image providers` slice.
- `mypy src\openzues\cli.py`: clean after the `infer image providers` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_image_describe_json_wraps_native_media_understanding"`: 1 passed after adding OpenClaw's `infer` / `capability image describe` envelope over a fakeable native media-understanding runtime.
- `python -m pytest tests\test_cli.py -q -k "infer_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias or infer_model or capability_model"`: 13 passed after rechecking adjacent image/model/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer image describe` slice.
- `mypy src\openzues\cli.py`: clean after the `infer image describe` slice.
- `python -m pytest tests\test_cli.py -q -k "capability_image_describe_many_json_wraps_each_image"`: 1 passed after adding OpenClaw's repeated-file `infer` / `capability image describe-many` envelope.
- `python -m pytest tests\test_cli.py -q -k "infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias or infer_model or capability_model"`: 14 passed after rechecking adjacent image/model/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer image describe-many` slice.
- `mypy src\openzues\cli.py`: clean after the `infer image describe-many` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_image_generate_json_wraps_native_image_generation"`: 1 passed after adding OpenClaw's `infer` / `capability image generate` command over a fakeable native image-generation runtime.
- `python -m pytest tests\test_cli.py -q -k "infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias or infer_model or capability_model"`: 15 passed after rechecking adjacent image/model/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer image generate` slice.
- `mypy src\openzues\cli.py`: clean after the `infer image generate` slice.
- `python -m pytest tests\test_cli.py -q -k "capability_image_edit_json_wraps_native_image_generation"`: 1 passed after adding OpenClaw's `infer` / `capability image edit` command over the fakeable native image-generation runtime.
- `python -m pytest tests\test_cli.py -q -k "infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias or infer_model or capability_model"`: 16 passed after rechecking adjacent image/model/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer image edit` slice.
- `mypy src\openzues\cli.py`: clean after the `infer image edit` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_audio_providers_json_filters_audio_capable_registry"`: 1 passed after adding OpenClaw's `infer` / `capability audio providers` projection over the fakeable media-understanding registry.
- `python -m pytest tests\test_cli.py -q -k "infer_audio or capability_audio or infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 8 passed after rechecking adjacent audio/image/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer audio providers` slice.
- `mypy src\openzues\cli.py`: clean after the `infer audio providers` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_audio_transcribe_json_wraps_native_media_understanding"`: 1 passed after adding OpenClaw's `infer` / `capability audio transcribe` envelope over the fakeable media-understanding runtime.
- `python -m pytest tests\test_cli.py -q -k "infer_audio or capability_audio or infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 9 passed after rechecking adjacent audio/image/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer audio transcribe` slice.
- `mypy src\openzues\cli.py`: clean after the `infer audio transcribe` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_video_providers_json_projects_generation_and_description"`: 1 passed after adding OpenClaw's `infer` / `capability video providers` projection over fakeable video-generation and media-understanding registries.
- `python -m pytest tests\test_cli.py -q -k "infer_video or capability_video or infer_audio or capability_audio or infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 10 passed after rechecking adjacent video/audio/image/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer video providers` slice.
- `mypy src\openzues\cli.py`: clean after the `infer video providers` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_video_describe_json_wraps_native_media_understanding"`: 1 passed after adding OpenClaw's `infer` / `capability video describe` envelope over the fakeable media-understanding runtime.
- `python -m pytest tests\test_cli.py -q -k "infer_video or capability_video or infer_audio or capability_audio or infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 11 passed after rechecking adjacent video/audio/image/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer video describe` slice.
- `mypy src\openzues\cli.py`: clean after the `infer video describe` slice.
- `python -m pytest tests\test_cli.py -q -k "capability_video_generate_json_wraps_native_video_generation"`: 1 passed after adding OpenClaw's `infer` / `capability video generate` envelope over the fakeable video-generation runtime.
- `python -m pytest tests\test_cli.py -q -k "infer_video or capability_video or infer_audio or capability_audio or infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 12 passed after rechecking adjacent video/audio/image/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer video generate` slice.
- `mypy src\openzues\cli.py`: clean after the `infer video generate` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_web_providers_json_projects_search_and_fetch"`: 1 passed after adding OpenClaw's `infer` / `capability web providers` projection over fakeable search/fetch provider registries.
- `python -m pytest tests\test_cli.py -q -k "infer_web or capability_web or infer_video or capability_video or infer_audio or capability_audio or infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 13 passed after rechecking adjacent web/video/audio/image/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer web providers` slice.
- `mypy src\openzues\cli.py`: clean after the `infer web providers` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_web_search_json_wraps_native_web_runtime"`: 1 passed after adding OpenClaw's `infer` / `capability web search` envelope over the fakeable web runtime.
- `python -m pytest tests\test_cli.py -q -k "infer_web or capability_web or infer_video or capability_video or infer_audio or capability_audio or infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 14 passed after rechecking adjacent web/video/audio/image/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer web search` slice.
- `mypy src\openzues\cli.py`: clean after the `infer web search` slice.
- `python -m pytest tests\test_cli.py -q -k "capability_web_fetch_json_wraps_native_web_runtime"`: 1 passed after adding OpenClaw's `infer` / `capability web fetch` envelope over the fakeable web runtime.
- `python -m pytest tests\test_cli.py -q -k "infer_web or capability_web or infer_video or capability_video or infer_audio or capability_audio or infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 15 passed after rechecking adjacent web/video/audio/image/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer web fetch` slice.
- `mypy src\openzues\cli.py`: clean after the `infer web fetch` slice.
- `python -m pytest tests\test_cli.py -q -k "infer_embedding_providers_json_projects_native_registry"`: 1 passed after adding OpenClaw's `infer` / `capability embedding providers` projection over the fakeable embedding runtime.
- `python -m pytest tests\test_cli.py -q -k "infer_embedding or capability_embedding or infer_web or capability_web or infer_video or capability_video or infer_audio or capability_audio or infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 16 passed after rechecking adjacent embedding/web/video/audio/image/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer embedding providers` slice.
- `mypy src\openzues\cli.py`: clean after the `infer embedding providers` slice.
- `python -m pytest tests\test_cli.py -q -k "capability_embedding_create_json_wraps_native_embedding_runtime"`: 1 passed after adding OpenClaw's `infer` / `capability embedding create` envelope over the fakeable embedding runtime.
- `python -m pytest tests\test_cli.py -q -k "infer_embedding or capability_embedding or infer_web or capability_web or infer_video or capability_video or infer_audio or capability_audio or infer_image or capability_image or capability_list_json_surfaces_openclaw_capability_metadata or infer_inspect_json_uses_capability_alias"`: 17 passed after rechecking adjacent embedding/web/video/audio/image/capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the `infer embedding create` slice.
- `mypy src\openzues\cli.py`: clean after the `infer embedding create` slice.
- `python -m pytest tests\test_cli.py -q -k "models_status_probe_json_uses_model_auth_runtime"`: 1 passed after making `models status --probe --json` consume a fakeable native model-auth status/probe runtime.
- `python -m pytest tests\test_cli.py -q -k "models_status or infer_model_auth or capability_model_auth or infer_model_providers or capability_model_inspect or infer_model_list or model_run"`: 11 passed after rechecking adjacent model/auth capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the model auth probe-status slice.
- `mypy src\openzues\cli.py`: clean after the model auth probe-status slice.
- `python -m pytest tests\test_cli.py -q -k "models_status_check_exits_nonzero_for_known_auth_problem"`: 1 passed after making `models status --check` return OpenClaw-style non-zero status for known auth failures.
- `python -m pytest tests\test_cli.py -q -k "models_status or infer_model_auth or capability_model_auth or infer_model_providers or capability_model_inspect or infer_model_list or model_run"`: 12 passed after rechecking adjacent model/auth capability CLI surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the model auth check-exit slice.
- `mypy src\openzues\cli.py`: clean after the model auth check-exit slice.
- `python -m pytest tests\test_cli.py -q -k "status_json_uses_registered_usage_and_security_runtime_adapters"`: 1 passed after making `status --json --usage --all` consume fakeable provider-usage and security-audit runtime adapters.
- `python -m pytest tests\test_cli.py -q -k "status_json_uses_registered_usage_and_security_runtime_adapters or status_json_breadth_flags_add_runtime_sections_with_timeout or status_all_human_output_renders_pasteable_diagnosis"`: 3 passed after rechecking adjacent status breadth output.
- `python -m pytest tests\test_cli.py -q -k "status_json_prefers_live_status_payload_when_available"` and `python -m pytest tests\test_cli.py -q -k "status_json_reuses_gateway_contract_and_surfaces_queue_plan"`: each 1 passed; a broader `status_json` keyword selection timed out after collecting slower unrelated status tests.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the status usage/security adapter slice.
- `mypy src\openzues\cli.py`: clean after the status usage/security adapter slice.
- `python -m pytest tests\test_cli.py -q -k "channels_status_json_accepts_probe_timeout_options"`: 1 passed after adding `channels status --probe --timeout` option metadata.
- `python -m pytest tests\test_cli.py -q -k "channels_status"`: 2 passed after rechecking adjacent channel status CLI output.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the channels status probe-option slice.
- `mypy src\openzues\cli.py`: clean after the channels status probe-option slice.
- `python -m pytest tests\test_cli.py -q -k "channels_capabilities_json_filters_channel_and_account"`: 1 passed after adding the native `channels capabilities` report surface.
- `python -m pytest tests\test_cli.py -q -k "channels_status or channels_capabilities"`: 3 passed after rechecking adjacent channel status/capabilities CLI output.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the channels capabilities slice.
- `mypy src\openzues\cli.py`: clean after the channels capabilities slice.
- `python -m pytest tests\test_cli.py -q -k "channels_resolve_json_uses_saved_conversation_targets"`: 1 passed after adding route-backed `channels resolve` JSON output.
- `python -m pytest tests\test_cli.py -q -k "channels_status or channels_capabilities or channels_resolve"`: 4 passed after rechecking adjacent channel CLI output.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the channels resolve slice.
- `mypy src\openzues\cli.py`: clean after the channels resolve slice.
- `python -m pytest tests\test_cli.py -q -k "channels_logs_json_filters_channel_and_limits_lines"`: 1 passed after adding structured `channels logs` JSON output.
- `python -m pytest tests\test_cli.py -q -k "channels_status or channels_capabilities or channels_resolve or channels_logs"`: 5 passed after rechecking adjacent channel CLI output.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the channels logs slice.
- `mypy src\openzues\cli.py`: clean after the channels logs slice.
- `python -m pytest tests\test_cli.py -q -k "channels_status_json_calls_gateway_method_owner_with_probe"`: 1 passed after routing `channels status --probe` through the gateway method owner.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "channels_status_probe_uses_registered_account_probe"`: 1 passed after adding the fakeable account-probe adapter.
- `python -m pytest tests\test_cli.py -q -k "channels_status or channels_capabilities or channels_resolve or channels_logs"`: 6 passed after rechecking adjacent channel CLI output.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "channels_status"`: 2 passed after rechecking gateway channel inventory/probe behavior.
- `ruff check src\openzues\cli.py src\openzues\services\gateway_channels.py src\openzues\services\gateway_node_methods.py tests\test_cli.py tests\test_gateway_node_methods.py`: clean after the channel status probe-owner slice.
- `mypy src\openzues\cli.py src\openzues\services\gateway_channels.py src\openzues\services\gateway_node_methods.py`: clean after the channel status probe-owner slice.
- `python -m pytest tests\test_cli.py -q -k "channels_capabilities_json_uses_account_probe_result"`: 1 passed after projecting account probe results into `channels capabilities`.
- `python -m pytest tests\test_cli.py -q -k "channels_status or channels_capabilities or channels_resolve or channels_logs"`: 7 passed after rechecking adjacent channel CLI output.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the channel capabilities probe slice.
- `mypy src\openzues\cli.py`: clean after the channel capabilities probe slice.
- `python -m pytest tests\test_cli.py -q -k "channels_resolve_json_uses_registered_live_resolver"`: 1 passed after adding the fakeable live target resolver fallback.
- `python -m pytest tests\test_cli.py -q -k "channels_status or channels_capabilities or channels_resolve or channels_logs"`: 8 passed after rechecking adjacent channel CLI output.
- `ruff check src\openzues\cli.py src\openzues\services\gateway_channels.py tests\test_cli.py`: clean after the live channel resolve adapter slice.
- `mypy src\openzues\cli.py src\openzues\services\gateway_channels.py`: clean after the live channel resolve adapter slice.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_catalog_projects_plugin_groups"`: 1 passed after adding plugin-published `tools.catalog` groups.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_catalog or tools_effective"`: 7 passed after rechecking adjacent tool catalog/effective behavior.
- `python -m pytest tests\test_gateway_nodes_api.py -q -k "tools_catalog or tools_effective"`: 3 passed after rechecking HTTP gateway tool catalog/effective behavior.
- `ruff check src\openzues\services\gateway_tools_catalog.py src\openzues\services\gateway_plugin_runtime.py src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`: clean after the plugin catalog visibility slice.
- `mypy src\openzues\services\gateway_tools_catalog.py src\openzues\services\gateway_plugin_runtime.py src\openzues\services\gateway_node_methods.py`: clean after the plugin catalog visibility slice.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_effective_projects_plugin_group_from_runtime_specs"`: 1 passed after adding plugin-published `tools.effective` groups.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "tools_catalog or tools_effective"`: 8 passed after rechecking adjacent tool catalog/effective behavior.
- `python -m pytest tests\test_gateway_nodes_api.py -q -k "tools_catalog or tools_effective"`: 3 passed after rechecking HTTP gateway tool catalog/effective behavior.
- `ruff check src\openzues\services\gateway_tools_catalog.py src\openzues\services\gateway_plugin_runtime.py src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`: clean after the plugin effective visibility slice.
- `mypy src\openzues\services\gateway_tools_catalog.py src\openzues\services\gateway_plugin_runtime.py src\openzues\services\gateway_node_methods.py`: clean after the plugin effective visibility slice.
- `ruff check src\openzues\services\gateway_acp_spawn.py src\openzues\services\gateway_node_methods.py src\openzues\services\gateway_outbound_runtime.py src\openzues\services\gateway_plugin_runtime.py src\openzues\services\ops_mesh.py src\openzues\app.py tests\test_gateway_acp_spawn.py tests\test_gateway_node_methods.py tests\test_ops_mesh.py`: clean.
- `mypy src\openzues\services\gateway_acp_spawn.py src\openzues\services\gateway_node_methods.py src\openzues\services\gateway_outbound_runtime.py src\openzues\services\gateway_plugin_runtime.py src\openzues\services\ops_mesh.py src\openzues\app.py`: clean.
- `pytest tests/test_gateway_node_methods.py -q -k cron`: 48 passed after adding cron-expression schedule create/update/due-run coverage.
- `pytest tests/test_gateway_nodes_api.py -q -k cron`: 35 passed after adding HTTP method cron-expression round-trip coverage.
- `pytest tests/test_ops_mesh.py -q -k "cron or scheduled or due"`: 23 passed after wiring cron-expression due detection into Ops Mesh.
- `pytest tests/test_gateway_node_methods.py -q -k agents_files`: 5 passed after widening `agents.files.*` to OpenClaw bootstrap/memory filenames.
- `pytest tests/test_gateway_nodes_api.py -q -k "agents_files or agents_memory_file"`: 3 passed after HTTP coverage for `MEMORY.md`.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k plugin_approval`: 2 passed after replacing the `plugin.approval.*` hard-503 placeholder with a bounded in-memory approval lifecycle.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after adding the plugin approval manager.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k device_pair`: 3 passed after wiring `device.pair.*` to persisted node pairing state.
- `pytest tests/test_gateway_node_methods.py -q -k "node_pair or device_pair"`: 15 passed, proving the device alias did not regress the existing node-pair lifecycle.
- `mypy src/openzues/database.py src/openzues/services/gateway_node_pairing.py src/openzues/services/gateway_node_methods.py`: clean after adding paired-device removal and gateway aliases.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k exec_approval`: 12 passed after replacing the `exec.approval.*` hard-503 placeholder with a bounded local approval lifecycle.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "exec_approval or plugin_approval or device_pair"`: 17 passed after combining the approval/device runtime seams.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k exec_approvals`: 5 passed after adding persisted global/node exec approval policy config.
- `mypy src/openzues/services/gateway_node_methods.py src/openzues/app.py`: clean after wiring the policy config path.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k device_token`: 6 passed after replacing the `device.token.rotate/revoke` hard-503 placeholders with persisted SQLite role-scoped device auth tokens.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "device_pair or device_token or node_pair"`: 27 passed after rechecking the adjacent pairing lifecycle.
- `ruff check src/openzues/database.py src/openzues/services/gateway_node_pairing.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the device-token runtime.
- `mypy src/openzues/database.py src/openzues/services/gateway_node_pairing.py src/openzues/services/gateway_node_methods.py`: clean after the device-token runtime.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "agents_mutate or agents_mutation or agents_list_returns"`: 6 passed after adding persisted custom-agent create/update/delete.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "agents_list or agents_files or agents_mutate or agents_mutation or agent_identity"`: 23 passed after rechecking adjacent agent inventory/file/identity surfaces.
- `mypy src/openzues/database.py src/openzues/services/gateway_agents.py src/openzues/services/gateway_node_methods.py`: clean after the agent registry mutation runtime.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "config_get or config_open_file or config_write or control_ui_config"`: 12 passed after adding base-hash guarded config set/patch/apply over the control-UI config file.
- `ruff check src/openzues/services/gateway_config.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the config mutation runtime.
- `mypy src/openzues/services/gateway_config.py src/openzues/services/gateway_node_methods.py`: clean after the config mutation runtime.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k doctor_memory`: 6 passed after replacing the memory-doctor mutation placeholders with bounded workspace mutation helpers.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the memory-doctor mutation runtime.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the memory-doctor mutation runtime.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "originating_fields or originating_route or system_provenance"`: 8 passed after wiring admin-scoped `chat.send` origin-route provenance into the runtime prompt while keeping the non-admin gate intact.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "originating_fields or originating_route or system_provenance"`: 8 passed again after wiring admin-scoped `chat.send` system provenance into the runtime prompt.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `chat.send` origin/system provenance seams.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `chat.send` origin/system provenance seams.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k sessions_steer`: 19 passed after allowing idle `sessions.steer` sends without requiring an abort runtime.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the idle `sessions.steer` runtime seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the idle `sessions.steer` runtime seam.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_create or sessions_list_filters_by_agent"`: 4 passed after bridging persisted custom agents into `sessions.create` and `sessions.list agentId` filtering.
- `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py src/openzues/services/gateway_agents.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the custom-agent session bridge.
- `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py src/openzues/services/gateway_agents.py`: clean after the custom-agent session bridge.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "agent_identity or agents_mutation_lifecycle or sessions_create"`: 16 passed after resolving persisted custom-agent rows through `agent.identity.get`.
- `ruff check src/openzues/services/gateway_agents.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the custom-agent identity bridge.
- `mypy src/openzues/services/gateway_agents.py src/openzues/services/gateway_node_methods.py`: clean after the custom-agent identity bridge.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "agent_files or agents_files or agents_mutation_lifecycle or agent_identity"`: 21 passed after routing `agents.files.*` through persisted custom-agent workspaces.
- `ruff check src/openzues/services/gateway_agent_files.py src/openzues/services/gateway_agents.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the custom-agent file bridge.
- `mypy src/openzues/services/gateway_agent_files.py src/openzues/services/gateway_agents.py src/openzues/services/gateway_node_methods.py`: clean after the custom-agent file bridge.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_send or sessions_steer"`: 41 passed after adding the deleted custom-agent owner guard for `sessions.send` / `sessions.steer`.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the deleted-agent session guard.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the deleted-agent session guard.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_history"`: 4 passed after hiding assistant skip-only entries and stripping inline reply/audio directives from `chat.history`.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `chat.history` projection seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `chat.history` projection seam.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_history"`: 5 passed after adding optional persisted assistant usage/cost metadata to `chat.history`.
- `ruff check src/openzues/database.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the usage/cost history metadata seam.
- `mypy src/openzues/database.py src/openzues/services/gateway_node_methods.py`: clean after the usage/cost history metadata seam.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_history"`: 5 passed after changing `maxChars` to OpenClaw-style per-message prefix truncation markers.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `chat.history` truncation seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `chat.history` truncation seam.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_history"`: 6 passed after adding the OpenClaw default `chat.history` text cap.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the default history cap.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the default history cap.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_preview"`: 3 passed after applying chat-history skip/directive hygiene to `sessions.preview` items.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the preview sanitization seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the preview sanitization seam.
- `pytest tests/test_gateway_node_methods.py -q -k "chat_inject_sanitizes_live_session_message_events"`: 1 passed after applying OpenClaw live-event display hygiene to `session.message` / `sessions.changed`.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_inject or session_message or chat_history or sessions_preview"`: 14 passed after rechecking adjacent transcript projections.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the live session-event sanitization seam.
- `mypy src/openzues/services/gateway_sessions.py`: clean after the live session-event sanitization seam.
- `pytest tests/test_gateway_sessions.py -q -k "live_usage_metadata"`: 1 passed after projecting message-level usage/cost snapshots onto live `session.message` and `sessions.changed` events.
- `pytest tests/test_gateway_sessions.py tests/test_gateway_node_methods.py -q -k "message_payloads_surface or chat_inject_sanitizes_live_session_message_events or chat_inject_appends"`: 4 passed after rechecking adjacent session event builders.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_sessions.py tests/test_gateway_node_methods.py`: clean after the live usage metadata seam.
- `mypy src/openzues/services/gateway_sessions.py`: clean after the live usage metadata seam.
- `pytest tests/test_gateway_sessions.py -q -k "spawn_and_route_metadata"`: 1 passed after copying spawned-session and last-route metadata onto transcript `session.message` / `sessions.changed` events.
- `pytest tests/test_gateway_sessions.py tests/test_gateway_node_methods.py -q -k "message_payloads_surface or chat_inject_sanitizes_live_session_message_events or chat_inject_appends or sessions_patch_persists_current_session_metadata"`: 6 passed after rechecking adjacent metadata/event paths.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_sessions.py tests/test_gateway_node_methods.py`: clean after the session event metadata breadth seam.
- `mypy src/openzues/services/gateway_sessions.py`: clean after the session event metadata breadth seam.
- Live `session.message`, message-phase `sessions.changed`, and mutation
  `sessions.changed` events now include the nested OpenClaw-shaped
  `deliveryContext` object already present on session snapshots, preserving
  `channel`, `to`, `accountId`, and numeric/string `threadId` values alongside
  the existing flattened last-route fields.
- `python -m pytest tests\test_gateway_sessions.py::test_message_payloads_surface_spawn_and_route_metadata -q`
  and `python -m pytest tests\test_gateway_sessions.py::test_route_metadata_preserves_string_thread_ids -q`:
  both passed after extending event payload coverage.
- `python -m pytest tests\test_gateway_sessions.py -q -k "message_payloads_surface_spawn_and_route_metadata or route_metadata_preserves_string_thread_ids or build_snapshot_surfaces_delivery_context_from_route_metadata or build_snapshot_derives_delivery_context_from_origin_metadata or changed_event_payload_surfaces_session_setting_route_metadata or changed_event_payload_surfaces_transcript_usage_metadata"`:
  6 passed after rechecking session snapshot and event route metadata.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "session_message or sessions_changed or message_event or changed_event"`:
  3 passed after rechecking the adjacent gateway-method event publisher paths.
- `ruff check src\openzues\services\gateway_sessions.py
  tests\test_gateway_sessions.py` and `mypy
  src\openzues\services\gateway_sessions.py`: clean after the live
  `deliveryContext` event seam.
- Session snapshots, mutation `sessions.changed`, live `session.message`, and
  message-phase `sessions.changed` events now surface persisted lifecycle
  metadata (`status`, `startedAt`, `endedAt`, `runtimeMs`, and
  `abortedLastRun`) in the same event snapshot path OpenClaw uses for session
  run state.
- `python -m pytest tests\test_gateway_sessions.py::test_session_snapshot_and_events_surface_lifecycle_status_metadata -q`:
  1 passed after adding native lifecycle metadata projection.
- `python -m pytest tests\test_gateway_sessions.py -q -k "lifecycle_status_metadata or message_payloads_surface_spawn_and_route_metadata or route_metadata_preserves_string_thread_ids or changed_event_payload_surfaces_session_setting_route_metadata or build_snapshot_surfaces_delivery_context_from_route_metadata or changed_event_payload_surfaces_transcript_usage_metadata"`:
  6 passed after rechecking adjacent snapshot/event fields.
- `python -m pytest tests\test_gateway_node_methods.py -q -k "session_message or sessions_changed or message_event or changed_event"`:
  3 passed after rechecking gateway-method event publication, with `ruff check
  src\openzues\services\gateway_sessions.py tests\test_gateway_sessions.py`
  and `mypy src\openzues\services\gateway_sessions.py` clean.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_get_supports_cursor_pagination"`: 1 passed after adding cursor pagination metadata and string `nextCursor` round-trip support to `sessions.get`.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_get"`: 5 passed after rechecking legacy flat responses and API coverage.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `sessions.get` cursor seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.get` cursor seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_patch_persists_metadata_backed_child_session"`: 1 passed after allowing `sessions.patch` to target resolved metadata-backed child sessions.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_patch"`: 3 passed after rechecking current-session and API patch coverage.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `sessions.patch` target-session seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.patch` target-session seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_create_scopes_main_alias"`: 1 passed after scoping `sessions.create key=main` to the requested custom agent.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_create"`: 5 passed after rechecking generated custom-agent sessions and initial send behavior.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `sessions.create` agent-main alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.create` agent-main alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_create_preserves_global_and_unknown_sentinel_keys"`: 1 passed after preserving OpenClaw sentinel keys during custom-agent session creation.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_create"`: 6 passed after rechecking the full bounded session-create family.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `sessions.create` sentinel-key seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.create` sentinel-key seam.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_create_registers_metadata_session_and_sends_initial_message or sessions_create_api_registers_session_and_sends_initial_message"`: 2 passed after adding OpenClaw-style `messageSeq` to initial `sessions.create` runs.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_send or sessions_steer or sessions_create"`: 47 passed after proving `sessions.send` / `sessions.steer` response shapes did not regress.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `sessions.create` initial-turn `messageSeq` seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.create` initial-turn `messageSeq` seam.
- `pytest tests/test_gateway_sessions.py -q -k "transcript_usage_and_model_fallbacks or discovers_mission_and_transcript_sessions_without_metadata or agent_filter_includes_main_legacy_sessions"`: 3 passed after adding transcript usage/model fallback coverage and re-locking current-main list behavior.
- `pytest tests/test_gateway_sessions.py -q -k "snapshot or message_payloads_surface or live_usage_metadata or spawn_and_route_metadata"`: 18 passed after rechecking adjacent session snapshots and live events.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_list or sessions_create or chat_history"`: 32 passed after rechecking method/API session listing, create, and history paths.
- `ruff check src/openzues/database.py src/openzues/services/gateway_sessions.py tests/test_gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `sessions.list` transcript usage/model fallback seam.
- `mypy src/openzues/database.py src/openzues/services/gateway_sessions.py`: clean after the `sessions.list` transcript usage/model fallback seam.
- `pytest tests/test_gateway_sessions.py -q -k "changed_event_payload_surfaces_transcript_usage_metadata"`: 1 passed after copying fresh transcript usage/cost fields into mutation `sessions.changed` payloads.
- `pytest tests/test_gateway_sessions.py -q -k "snapshot or changed_event_payload_surfaces_transcript_usage_metadata or message_payloads_surface or live_usage_metadata or spawn_and_route_metadata"`: 19 passed after rechecking snapshot and live-event paths.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_list or sessions_create or chat_history or sessions_patch"`: 35 passed after rechecking method/API session list/create/history/patch paths.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_sessions.py`: clean after the mutation `sessions.changed` usage metadata seam.
- `mypy src/openzues/database.py src/openzues/services/gateway_sessions.py`: clean after the mutation `sessions.changed` usage metadata seam.
- `pytest tests/test_gateway_sessions.py -q -k "changed_event_payload_surfaces_session_setting_route_metadata"`: 1 passed after copying session setting and route metadata into mutation `sessions.changed` payloads.
- `pytest tests/test_gateway_sessions.py -q -k "snapshot or changed_event_payload_surfaces or message_payloads_surface or live_usage_metadata or spawn_and_route_metadata"`: 20 passed after rechecking all focused session snapshot/event seams.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_list or sessions_create or chat_history or sessions_patch"`: 35 passed after rechecking method/API session list/create/history/patch paths.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_sessions.py`: clean after the mutation `sessions.changed` setting/route metadata seam.
- `mypy src/openzues/database.py src/openzues/services/gateway_sessions.py`: clean after the mutation `sessions.changed` setting/route metadata seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_patch_uses_resolved_subagent_store_key"`: 1 passed after making `sessions.patch` write/respond under the resolved agent-store subagent key.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_patch or sessions_reset or sessions_delete"`: 8 passed after rechecking adjacent session mutation methods.
- `pytest tests/test_gateway_sessions.py -q -k "changed_event_payload_surfaces_session_setting_route_metadata or spawn_and_route_metadata"`: 2 passed after rechecking subagent metadata event payloads.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the subagent alias mutation seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the subagent alias mutation seam.
- `pytest tests/test_gateway_sessions.py -q -k "delivery_context_from_route_metadata"`: 1 passed after deriving `deliveryContext` from persisted last-route metadata.
- `pytest tests/test_gateway_sessions.py -q -k "snapshot or delivery_context_from_route_metadata or changed_event_payload_surfaces or message_payloads_surface"`: 21 passed after rechecking session snapshot/event projections.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_list or sessions_patch or sessions_create"`: 30 passed after rechecking method/API list/patch/create paths.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_sessions.py`: clean after the `deliveryContext` read-model seam.
- `mypy src/openzues/database.py src/openzues/services/gateway_sessions.py`: clean after the `deliveryContext` read-model seam.
- `pytest tests/test_gateway_sessions.py -q -k "route_metadata_preserves_string_thread_ids"`: 1 passed after preserving OpenClaw-style string `lastThreadId` values in session payloads and mutation events.
- `pytest tests/test_gateway_sessions.py -q -k "snapshot or route_metadata_preserves_string_thread_ids or delivery_context_from_route_metadata or changed_event_payload_surfaces or message_payloads_surface"`: 22 passed after rechecking snapshot/event projections.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_list or sessions_reset or sessions_patch"`: 26 passed after rechecking public RPC/API paths that surface session route metadata.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_sessions.py`: clean after the string `lastThreadId` route-metadata seam.
- `mypy src/openzues/services/gateway_sessions.py`: clean after the string `lastThreadId` route-metadata seam.
- `pytest tests/test_gateway_sessions.py -q -k "includes_current_main_session_without_persisted_rows"`: 1 passed after adding OpenClaw-style `defaults.modelProvider` to session snapshots.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_list_returns_bounded_singleton_control_chat_inventory"`: 1 passed after updating the method-level `sessions.list` defaults contract.
- `pytest tests/test_gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_list"`: 20 passed after rechecking all focused service/method/API `sessions.list` tests.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `defaults.modelProvider` seam.
- `mypy src/openzues/services/gateway_sessions.py`: clean after the `defaults.modelProvider` seam.
- `pytest tests/test_gateway_sessions.py -q -k "includes_current_main_session_without_persisted_rows"`: 1 passed after making no-usage session snapshots carry `totalTokensFresh: false`.
- `pytest tests/test_gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_list or changed_event_payload_surfaces or message_payloads_surface or route_metadata_preserves_string_thread_ids"`: 26 passed after rechecking snapshot/event/API payload shapes.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `totalTokensFresh: false` seam.
- `mypy src/openzues/services/gateway_sessions.py`: clean after the `totalTokensFresh: false` seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_patch_preserves_provider_model_override_split"`: 1 passed after splitting provider-qualified session model overrides into `providerOverride` / `modelOverride`.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_sessions.py -q -k "sessions_patch or sessions_list or sessions_reset or provider_model_override_split"`: 27 passed after rechecking patch/list/reset session payloads.
- `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_sessions.py`: clean after the provider/model override seam.
- `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py`: clean after the provider/model override seam.
- `pytest tests/test_gateway_node_methods.py -q -k "reset_discards_stale_runtime_model_metadata or reset_marks_legacy_provider_model_override_as_user"`: 2 passed after normalizing reset model metadata.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_sessions.py -q -k "sessions_reset or sessions_patch or sessions_list or reset_discards_stale_runtime_model_metadata or reset_marks_legacy_provider_model_override_as_user"`: 29 passed after rechecking reset/patch/list session model behavior.
- `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_sessions.py`: clean after the reset model metadata seam.
- `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py`: clean after the reset model metadata seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_reset_preserves_owned_child_metadata"`: 1 passed after projecting owned child session metadata through reset payloads.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_sessions.py -q -k "sessions_reset or sessions_patch or sessions_list or changed_event_payload_surfaces or message_payloads_surface or owned_child_metadata"`: 35 passed after rechecking reset/list/event session metadata projections.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py tests/test_gateway_sessions.py`: clean after the owned-child reset metadata seam.
- `mypy src/openzues/services/gateway_sessions.py src/openzues/services/gateway_node_methods.py`: clean after the owned-child reset metadata seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_preview_resolves_mixed_case_main_alias_duplicates"`: 1 passed after making `sessions.preview` choose the freshest mixed-case alias row.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_preview"`: 4 passed after rechecking method/API preview behavior.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the preview alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the preview alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_delete_uses_resolved_subagent_store_key"`: 1 passed after making `sessions.delete` resolve request aliases before deleting.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_delete or sessions_patch or sessions_reset or sessions_compact"`: 27 passed after rechecking adjacent session mutation methods.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the delete alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the delete alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_compact_uses_resolved_subagent_store_key"`: 1 passed after making `sessions.compact` resolve request aliases before compacting.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_compact or sessions_delete or sessions_patch or sessions_reset"`: 28 passed after rechecking adjacent session mutation/compaction methods.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the compact alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the compact alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_compaction_restore_uses_resolved_subagent_store_key"`: 1 passed after making `sessions.compaction.restore` resolve request aliases before checkpoint restore.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_compaction or sessions_compact"`: 16 passed after rechecking compaction restore/list/get/branch coverage.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the restore alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the restore alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_compaction_inventory_reads_use_resolved_subagent_store_key"`: 1 passed after making `sessions.compaction.list/get` resolve request aliases before checkpoint inventory reads.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_compaction or sessions_compact or sessions_delete or sessions_patch or sessions_reset"`: 30 passed after rechecking compaction plus adjacent mutation methods.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the compaction inventory alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the compaction inventory alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_compaction_branch_uses_resolved_subagent_store_key"`: 1 passed after making `sessions.compaction.branch` resolve request aliases before checkpoint branching.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_compaction or sessions_compact or sessions_delete or sessions_patch or sessions_reset"`: 31 passed after rechecking the full compaction alias cluster plus adjacent mutations.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the compaction branch alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the compaction branch alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_messages_subscribe_uses_resolved_subagent_store_key"`: 1 passed after making `sessions.messages.subscribe/unsubscribe` resolve request aliases before hub filter updates.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_messages_subscribe or sessions_messages_unsubscribe or sessions_compaction or sessions_compact"`: 26 passed after rechecking scoped message subscriptions plus shared resolver compaction paths.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the message subscription alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the message subscription alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_get_uses_resolved_subagent_store_key"`: 1 passed after making `sessions.get` resolve request aliases before transcript lookup.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_get or sessions_messages_subscribe or sessions_messages_unsubscribe or sessions_compaction"`: 27 passed after rechecking session reads, scoped subscriptions, and compaction paths.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the session-get alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the session-get alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_usage_summary_uses_resolved_subagent_store_key or sessions_usage_timeseries_uses_resolved_subagent_store_key or sessions_usage_logs_uses_resolved_subagent_store_key"`: 3 passed after making `sessions.usage*` methods resolve request aliases before usage reads.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_usage or sessions_get or sessions_messages_subscribe or sessions_messages_unsubscribe"`: 23 passed after rechecking usage, transcript, and scoped subscription read models.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the session usage alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the session usage alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "chat_history_uses_resolved_subagent_store_key"`: 1 passed after making `chat.history` resolve request aliases before transcript/metadata lookup.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_history or sessions_get or sessions_usage"`: 22 passed after rechecking chat history plus session read/usage models.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the chat-history alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the chat-history alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "chat_send_uses_resolved_subagent_store_key"`: 1 passed after making `chat.send` resolve request aliases before runtime dispatch.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_send_and_steer_use_resolved_subagent_store_key"`: 2 passed after making `sessions.send/steer` resolve request aliases before runtime dispatch.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_send or sessions_send or sessions_steer or chat_history or sessions_get or sessions_usage"`: 106 passed after rechecking send/steer plus adjacent session read models.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the send/steer alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the send/steer alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "chat_abort_uses_resolved_subagent_store_key"`: 1 passed after making `chat.abort` resolve request aliases before interrupting tracked runs.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_abort or chat_send or sessions_send or sessions_steer"`: 91 passed after rechecking abort plus adjacent runtime dispatch paths.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the abort alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the abort alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_abort_uses_resolved_subagent_store_key"`: 1 passed after making `sessions.abort` resolve request aliases before interrupting tracked runs.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_abort or chat_abort or chat_send or sessions_send or sessions_steer"`: 96 passed after rechecking session abort plus adjacent runtime dispatch paths.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the session-abort alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the session-abort alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_preview_uses_resolved_subagent_store_key"`: 1 passed after making `sessions.preview` resolve request aliases before reading transcript previews.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_preview or sessions_get or chat_history or sessions_usage"`: 27 passed after rechecking preview plus adjacent read models.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the preview alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the preview alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "tools_effective_uses_resolved_subagent_store_key"`: 1 passed after making `tools.effective` resolve request aliases before deriving effective toolsets.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "tools_effective or tools_catalog or sessions_preview"`: 12 passed after rechecking effective tools plus adjacent catalog/preview paths.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the effective-tools alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the effective-tools alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "send_uses_resolved_subagent_store_key_for_delivery_provenance"`: 1 passed after making direct `send` resolve known source session aliases before channel delivery.
- `pytest tests/test_gateway_nodes_api.py -q -k "send_endpoint_delivers_channel_target_message_and_records_outbound_delivery or send_endpoint_delivers_channel_target_media_and_records_outbound_delivery"`: 2 passed after preserving unknown structural source-session casing.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "send_ or poll_ or message_action"`: 140 passed after rechecking direct send, poll, and message-action routing.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the direct-send provenance alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the direct-send provenance alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "plugin_approval_request_uses_resolved_subagent_store_key"`: 1 passed after making plugin approval requests resolve known source session aliases.
- `pytest tests/test_gateway_node_methods.py -q -k "exec_approval_request_uses_resolved_subagent_store_key"`: 1 passed after making exec approval requests resolve known source session aliases.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "plugin_approval or exec_approval or send_uses_resolved_subagent_store_key_for_delivery_provenance"`: 12 passed after rechecking approval lifecycle records and direct-send provenance.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the approval provenance alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the approval provenance alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "node_event_chat_subscribe_uses_resolved_subagent_store_key"`: 1 passed after making internal node-event routing resolve known session aliases.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "node_event or node_invoke"`: 37 passed after rechecking node event/invoke routing.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the node-event alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the node-event alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "wake_uses_resolved_subagent_store_key"`: 1 passed after making `wake` resolve known session aliases before queueing.
- `pytest tests/test_gateway_nodes_api.py -q -k "wake_now_auto_retries_after_submit_error"`: 1 passed on rerun after one timing-sensitive broad-selection failure.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "wake or cron_wake"`: 50 passed after rechecking wake and cron-wake routing.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the wake alias seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the wake alias seam.
- `pytest tests/test_gateway_node_methods.py -q -k "browser or commands_list_returns_bounded_native_operator_inventory"`: 86 passed.
- `pytest tests/test_gateway_nodes_api.py -q -k browser`: 46 passed.
- `pytest tests/test_gateway_method_policy.py -q`: 18 passed after adding auth save/login/delete methods to the OpenZues-only method registry proof.
- `ruff check` on the touched cron/browser command/method/policy/test files: clean.
- `mypy` on the touched cron/browser command/method/policy files: clean.
- `pytest tests/test_gateway_capability.py::test_gateway_capability_browser_runtime_projects_plugin_node_host_inventory tests/test_gateway_bootstrap.py::test_get_view_surfaces_browser_service_inventory_from_runtime_status -q`: 2 passed after surfacing plugin-published browser node-host commands/caps through native capability/bootstrap inventory and keeping saved-launch browser method counts tied to plugin runtime methods.
- `pytest tests/test_gateway_capability.py -q -k "browser_runtime or callable_method_catalog or catalog_item_name"`: 8 passed.
- `pytest tests/test_gateway_bootstrap.py -q -k "runtime_inventory or browser_service_inventory or cached_mcp_plugin_source"`: 3 passed.
- `ruff check src/openzues/schemas.py src/openzues/services/gateway_capability.py src/openzues/services/gateway_bootstrap.py tests/test_gateway_capability.py tests/test_gateway_bootstrap.py`: clean.
- `mypy src/openzues/schemas.py src/openzues/services/gateway_capability.py src/openzues/services/gateway_bootstrap.py`: clean.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "session_message or chat_inject"`: 6 passed after adding OpenClaw nested transcript identity metadata to live `session.message` payloads.
- `ruff check src/openzues/services/gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the nested `session.message` metadata seam.
- `mypy src/openzues/services/gateway_sessions.py`: clean after the nested `session.message` metadata seam.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_subscribe or sessions_messages_subscribe or session_message"`: 16 passed after making broad `sessions.subscribe` clients receive live `session.message` events.
- `ruff check src/openzues/services/hub.py src/openzues/services/gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the broad session subscription transcript seam.
- `mypy src/openzues/services/hub.py src/openzues/services/gateway_sessions.py`: clean after the broad session subscription transcript seam.
- `pytest tests/test_gateway_nodes_api.py tests/test_gateway_node_methods.py -q -k "sessions_get or session_history_rest or session_message or sessions_subscribe"`: 21 passed after adding the direct `/sessions/{key}/history` REST history endpoint with cursor pagination, initial SSE history events, default REST text caps, lenient invalid-cursor handling, and OpenClaw-style unknown-session 404s.
- `ruff check src/openzues/app.py src/openzues/services/hub.py src/openzues/services/gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the direct session-history REST seam.
- `mypy src/openzues/app.py src/openzues/services/hub.py src/openzues/services/gateway_sessions.py`: clean after the direct session-history REST seam.
- `pytest tests/test_gateway_nodes_api.py tests/test_gateway_node_methods.py -q -k "sessions_get or session_history_rest or session_message or sessions_subscribe"`: 22 passed after changing RPC `sessions.get` to OpenClaw's default 200-message limit.
- `ruff check src/openzues/app.py src/openzues/services/gateway_node_methods.py src/openzues/services/hub.py src/openzues/services/gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `sessions.get` default-limit seam.
- `mypy src/openzues/app.py src/openzues/services/gateway_node_methods.py src/openzues/services/hub.py src/openzues/services/gateway_sessions.py`: clean after the `sessions.get` default-limit seam.
- `pytest tests/test_gateway_nodes_api.py -q -k "session_history_rest_endpoint"`: 8 passed after making direct session-history SSE streams stay live for inline `message` updates, bounded `history` refreshes, and non-message session-change refreshes.
- `pytest tests/test_gateway_nodes_api.py tests/test_gateway_node_methods.py -q -k "sessions_get or session_history_rest or session_message or sessions_subscribe"`: 25 passed after rechecking adjacent session read/event/subscription paths.
- `ruff check src/openzues/app.py src/openzues/services/gateway_node_methods.py src/openzues/services/hub.py src/openzues/services/gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the live direct-history SSE seam.
- `mypy src/openzues/app.py src/openzues/services/gateway_node_methods.py src/openzues/services/hub.py src/openzues/services/gateway_sessions.py`: clean after the live direct-history SSE seam.
- Direct `/sessions/{sessionKey}/history` no-query REST/SSE loads now request a
  full initial history window instead of inheriting the RPC `sessions.get`
  200-message default, preserving raw `__openclaw.seq` coverage and omitting
  cursor metadata until pagination is explicitly requested.
- `python -m pytest tests\test_gateway_nodes_api.py::test_gateway_session_history_rest_endpoint_full_initial_sse_without_query -q`:
  1 passed after proving a 201-message no-query initial `history` SSE event
  returns seq `1..201`, `hasMore: false`, and no `nextCursor`.
- `python -m pytest tests\test_gateway_nodes_api.py -q -k "session_history_rest_endpoint"`:
  16 passed after rechecking direct history REST/SSE behavior. `ruff check
  src\openzues\app.py tests\test_gateway_nodes_api.py` and `mypy
  src\openzues\app.py` were clean.
- Direct `/sessions/{sessionKey}/history` now mirrors OpenClaw's duplicate
  row resolution for mixed-case session aliases by keeping the freshest exact
  stored alias transcript before sequence/cursor projection, while
  `sessions.preview` continues to use the same alias-selection behavior.
- Verified the direct history freshest-alias slice with `python -m pytest
  tests\test_gateway_nodes_api.py::test_gateway_session_history_rest_endpoint_prefers_freshest_alias_transcript
  -q` (`1 passed`), adjacent `python -m pytest
  tests\test_gateway_nodes_api.py -q -k "session_history_rest_endpoint"` (`17
  passed`), adjacent preview alias proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_preview_resolves_mixed_case_main_alias_duplicates or
  sessions_preview_preserves_duplicate_keys_like_openclaw or
  sessions_preview_uses_resolved_subagent_store_key"` (`3 passed`), `ruff
  check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_nodes_api.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Direct session-history and adjacent `chat.history` projection now sanitize
  structured assistant content arrays with OpenClaw's phase rules: commentary
  only entries are hidden, mixed explicit phase text keeps the
  `final_answer` blocks, and raw `__openclaw.seq` still reflects the source
  transcript row.
- Verified the phased assistant history slice with `python -m pytest
  tests\test_gateway_nodes_api.py::test_gateway_session_history_rest_endpoint_sanitizes_phased_assistant_content
  -q` (`1 passed`), adjacent direct-history proof `python -m pytest
  tests\test_gateway_nodes_api.py -q -k "session_history_rest_endpoint"` (`18
  passed`), adjacent projection proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k "chat_history or sessions_history"`
  (`24 passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_nodes_api.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_get_honors_explicit_limits_above_direct_rest_cap or sessions_get_uses_openclaw_default_limit_of_200 or sessions_get_supports_cursor_pagination"`: 3 passed after separating RPC `sessions.get` explicit limits from the direct REST 1000-row cap.
- `pytest tests/test_gateway_nodes_api.py tests/test_gateway_node_methods.py -q -k "sessions_get or session_history_rest or session_message or sessions_subscribe"`: 26 passed after rechecking the session read/event/subscription pack.
- `ruff check src/openzues/app.py src/openzues/services/gateway_node_methods.py src/openzues/services/hub.py src/openzues/services/gateway_sessions.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the RPC `sessions.get` large-limit seam.
- `mypy src/openzues/app.py src/openzues/services/gateway_node_methods.py src/openzues/services/hub.py src/openzues/services/gateway_sessions.py`: clean after the RPC `sessions.get` large-limit seam.
- `pytest tests/test_gateway_nodes_api.py -q -k "session_history_rest_endpoint"`: 9 passed after making non-GET direct session-history calls return OpenClaw's plain-text `405` with `Allow: GET`.
- `ruff check src/openzues/app.py tests/test_gateway_nodes_api.py`: clean after the direct history method guard seam.
- `mypy src/openzues/app.py`: clean after the direct history method guard seam.
- `pytest tests/test_gateway_nodes_api.py -q -k "session_history_rest_endpoint"`: 10 passed after making blank decoded direct history session keys return OpenClaw's `invalid_request_error`.
- `ruff check src/openzues/app.py tests/test_gateway_nodes_api.py`: clean after the direct history blank-key guard seam.
- `mypy src/openzues/app.py`: clean after the direct history blank-key guard seam.
- `pytest tests/test_gateway_nodes_api.py tests/test_gateway_node_methods.py -q -k "sessions_get or session_history_rest or session_message or sessions_subscribe"`: 28 passed after rechecking adjacent session read/event/subscription paths.
- `pytest tests/test_gateway_nodes_api.py -q -k "session_history_rest_endpoint"`: 11 passed after making remote direct history calls honor declared `x-openclaw-scopes`.
- `pytest tests/test_gateway_nodes_api.py tests/test_gateway_node_methods.py -q -k "sessions_get or session_history_rest or session_message or sessions_subscribe"`: 29 passed after rechecking adjacent session read/event/subscription paths.
- `ruff check src/openzues/app.py tests/test_gateway_nodes_api.py`: clean after the declared direct-history scope seam.
- `mypy src/openzues/app.py`: clean after the declared direct-history scope seam.
- `pytest tests/test_gateway_nodes_api.py -q -k "session_history_rest_endpoint"`: 14 passed after proving silent `NO_REPLY` SSE suppression, bounded silent-refresh windows, and raw sequence resync after transcript-only refreshes.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_history or sessions_preview or session_message"`: 18 passed after tightening the default history text cap to upstream OpenClaw's 8,000-character default.
- `ruff check src/openzues/app.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the silent-refresh and default-cap seams.
- `mypy src/openzues/app.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py`: clean after the silent-refresh and default-cap seams.
- `pytest tests/test_gateway_nodes_api.py -q -k "session_history_rest_endpoint"`: 15 passed after direct REST history started honoring `gateway.webchat.chatHistoryMaxChars`.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_history or sessions_preview or session_message or config_get_returns_control_ui_bootstrap_snapshot or config_write or control_ui_config"`: 26 passed after wiring the same config cap into `chat.history` and preserving control-UI config serialization.
- `ruff check src/openzues/app.py src/openzues/schemas.py src/openzues/services/gateway_config.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the configured history cap seam.
- `mypy src/openzues/app.py src/openzues/schemas.py src/openzues/services/gateway_config.py src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_sessions.py`: clean after the configured history cap seam.
- `pytest tests/test_gateway_node_methods.py -q -k "chat_history_keeps_messages_under_openclaw_single_message_cap or chat_history_replaces_single_oversized_message_with_placeholder or chat_history_keeps_recent_small_messages_under_total_byte_cap"`: 3 passed after aligning `chat.history` payload budgets with OpenClaw's 128 KiB single-message / 6 MiB total defaults.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "chat_history or sessions_preview or session_message or config_get_returns_control_ui_bootstrap_snapshot or config_write or control_ui_config"`: 27 passed after rechecking adjacent history/config projections.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_history or tools_catalog_returns_bounded_openzues_toolset_inventory or tools_effective_exposes_explicit_sessions_history_toolset"`: 6 passed after adding the explicit `sessions_history` tool posture and `sessions.history` redacted transcript gateway read.
- `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/hermes_toolsets.py src/openzues/services/gateway_tools_catalog.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `sessions_history` tool/gateway read seam.
- `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/hermes_toolsets.py src/openzues/services/gateway_tools_catalog.py`: clean after the `sessions_history` tool/gateway read seam.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_history or session_status or tools_catalog_returns_bounded_openzues_toolset_inventory or tools_effective_exposes_explicit_sessions_history_toolset"`: 10 passed after adding the explicit `session_status` posture plus `session.status` status-card read/model override.
- `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/hermes_toolsets.py src/openzues/services/gateway_tools_catalog.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `session_status` adjacent seam.
- `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/hermes_toolsets.py src/openzues/services/gateway_tools_catalog.py`: clean after the `session_status` adjacent seam.
- `pytest tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py -q -k "sessions_history or session_status or sessions_send_resolves_label or tools_catalog_returns_bounded_openzues_toolset_inventory or tools_effective_exposes_explicit_sessions_history_toolset"`: 12 passed after making `sessions.send` resolve OpenClaw-style label targets before runtime dispatch.
- `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/hermes_toolsets.py src/openzues/services/gateway_tools_catalog.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean after the `sessions_send` label-target seam.
- `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/hermes_toolsets.py src/openzues/services/gateway_tools_catalog.py`: clean after the `sessions_send` label-target seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_list_toolset or openclaw_kind_and_message_limit_filters or tools_catalog_returns_bounded_openzues_toolset_inventory"`: 3 passed after adding explicit `sessions_list` posture plus `sessions.list` `kinds` / `messageLimit` projection parity.
- `ruff check src/openzues/services/gateway_sessions.py src/openzues/services/gateway_node_methods.py src/openzues/services/hermes_toolsets.py tests/test_gateway_node_methods.py`: clean after the `sessions_list` tool/projection seam.
- `mypy src/openzues/services/gateway_sessions.py src/openzues/services/gateway_node_methods.py src/openzues/services/hermes_toolsets.py`: clean after the `sessions_list` tool/projection seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_creates_openclaw_style_subagent_session or tools_catalog_returns_bounded_openzues_toolset_inventory"`: 2 passed after adding explicit `sessions_spawn` posture and a bounded `sessions.spawn` subagent-style launch method.
- `pytest tests/test_app.py tests/test_cli.py -q -k "gateway_capability_falls_back_to_staged_local_registry_when_lane_catalogs_are_offline or gateway_capability_falls_back_to_staged_registry_without_cached_catalogs or gateway_doctor_human_output_summarizes_sections"`: 3 passed after realigning staged gateway registry counts for the newly classified `sessions.spawn` method.
- `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/hermes_toolsets.py tests/test_gateway_node_methods.py tests/test_app.py tests/test_cli.py`: clean after the `sessions_spawn` seam.
- `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/gateway_method_policy.py src/openzues/services/hermes_toolsets.py`: clean after the `sessions_spawn` seam.
- `pytest tests/test_gateway_node_methods.py -q -k "agents_list_supports_sessions_spawn_tool_projection or tools_catalog_returns_bounded_openzues_toolset_inventory"`: 2 passed after adding explicit `agents_list` posture and an OpenClaw-style `agents.list toolProjection=sessions_spawn` response.
- `ruff check src/openzues/services/gateway_node_methods.py src/openzues/services/hermes_toolsets.py tests/test_gateway_node_methods.py`: clean after the `agents_list` tool-projection seam.
- `mypy src/openzues/services/gateway_node_methods.py src/openzues/services/hermes_toolsets.py`: clean after the `agents_list` tool-projection seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_materializes_inline_attachments or sessions_spawn_creates_openclaw_style_subagent_session"`: 2 passed after materializing inline `sessions.spawn` attachments into workspace `.openclaw/attachments/<id>` directories with receipts and prompt suffixes.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the `sessions.spawn` attachment seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.spawn` attachment seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_rejects_requesters_at_max_spawn_depth or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_materializes_inline_attachments"`: 3 passed after adding `requesterSessionKey` context and default max-depth rejection to `sessions.spawn`.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the `sessions.spawn` depth guard seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.spawn` depth guard seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_derives_requester_depth_from_spawned_by_ancestry or sessions_spawn_rejects_requesters_at_max_spawn_depth or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_materializes_inline_attachments"`: 4 passed after teaching `sessions.spawn` to derive requester depth from legacy `spawnedBy` / `parentSessionKey` ancestry when `spawnDepth` is missing.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the `sessions.spawn` ancestry-depth seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.spawn` ancestry-depth seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_honors_configured_max_spawn_depth or sessions_spawn_derives_requester_depth_from_spawned_by_ancestry or sessions_spawn_rejects_requesters_at_max_spawn_depth or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_materializes_inline_attachments"`: 5 passed after wiring `gateway.agents.defaults.subagents.maxSpawnDepth` through the control config schema and `sessions.spawn` depth guard.
- `ruff check src/openzues/schemas.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the configurable `sessions.spawn` depth seam.
- `mypy src/openzues/schemas.py src/openzues/services/gateway_node_methods.py`: clean after the configurable `sessions.spawn` depth seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_honors_configured_max_children_per_agent or sessions_spawn_honors_configured_max_spawn_depth or sessions_spawn_derives_requester_depth_from_spawned_by_ancestry or sessions_spawn_rejects_requesters_at_max_spawn_depth or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_materializes_inline_attachments"`: 6 passed after enforcing `gateway.agents.defaults.subagents.maxChildrenPerAgent` against live tracked child runs.
- `ruff check src/openzues/schemas.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the `sessions.spawn` active-child cap seam.
- `mypy src/openzues/schemas.py src/openzues/services/gateway_node_methods.py`: clean after the `sessions.spawn` active-child cap seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_persists_depth_role_and_control_scope or sessions_spawn_honors_configured_max_children_per_agent or sessions_spawn_honors_configured_max_spawn_depth or sessions_spawn_derives_requester_depth_from_spawned_by_ancestry or sessions_spawn_rejects_requesters_at_max_spawn_depth or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_materializes_inline_attachments"`: 7 passed after persisting depth-derived `subagentRole` and `subagentControlScope` metadata on spawned sessions.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the `sessions.spawn` role/control-scope seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.spawn` role/control-scope seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_rejects_required_sandbox_without_sandbox_runtime or sessions_spawn_persists_depth_role_and_control_scope or sessions_spawn_honors_configured_max_children_per_agent or sessions_spawn_honors_configured_max_spawn_depth or sessions_spawn_derives_requester_depth_from_spawned_by_ancestry or sessions_spawn_rejects_requesters_at_max_spawn_depth or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_materializes_inline_attachments"`: 8 passed after adding the upstream-shaped `sandbox="require"` forbidden response when OpenZues has no sandboxed target runtime.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the `sessions.spawn` sandbox-required seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.spawn` sandbox-required seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_session_mode_requires_thread_binding or sessions_spawn_rejects_required_sandbox_without_sandbox_runtime or sessions_spawn_persists_depth_role_and_control_scope or sessions_spawn_honors_configured_max_children_per_agent or sessions_spawn_honors_configured_max_spawn_depth or sessions_spawn_derives_requester_depth_from_spawned_by_ancestry or sessions_spawn_rejects_requesters_at_max_spawn_depth or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_materializes_inline_attachments"`: 9 passed after adding the upstream-shaped `mode="session"` / `thread=true` guard.
- `ruff check src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the `sessions.spawn` session-mode guard seam.
- `mypy src/openzues/services/gateway_node_methods.py`: clean after the `sessions.spawn` session-mode guard seam.
- `pytest tests/test_gateway_node_methods.py -q -k "agents_list_sessions_spawn_projection_honors_allowlist or agents_list_supports_sessions_spawn_tool_projection or sessions_spawn_rejects_agent_id_outside_configured_allowlist or sessions_spawn_requires_explicit_agent_id_when_configured or sessions_spawn_session_mode_requires_thread_binding or sessions_spawn_rejects_required_sandbox_without_sandbox_runtime or sessions_spawn_persists_depth_role_and_control_scope or sessions_spawn_honors_configured_max_children_per_agent or sessions_spawn_honors_configured_max_spawn_depth or sessions_spawn_derives_requester_depth_from_spawned_by_ancestry or sessions_spawn_rejects_requesters_at_max_spawn_depth or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_materializes_inline_attachments"`: 13 passed after wiring `requireAgentId`, `allowAgents`, and the matching `agents.list toolProjection=sessions_spawn` policy projection.
- `ruff check src/openzues/schemas.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the `sessions.spawn` target-policy seam.
- `mypy src/openzues/schemas.py src/openzues/services/gateway_node_methods.py`: clean after the `sessions.spawn` target-policy seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_thread_mode_requires_thread_binding_hook or agents_list_sessions_spawn_projection_honors_allowlist or agents_list_supports_sessions_spawn_tool_projection or sessions_spawn_rejects_agent_id_outside_configured_allowlist or sessions_spawn_requires_explicit_agent_id_when_configured or sessions_spawn_session_mode_requires_thread_binding or sessions_spawn_rejects_required_sandbox_without_sandbox_runtime or sessions_spawn_persists_depth_role_and_control_scope or sessions_spawn_honors_configured_max_children_per_agent or sessions_spawn_honors_configured_max_spawn_depth or sessions_spawn_derives_requester_depth_from_spawned_by_ancestry or sessions_spawn_rejects_requesters_at_max_spawn_depth or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_materializes_inline_attachments"`: 14 passed after adding the upstream-shaped `thread=true` no-hook rejection and moving the success proof to run-mode spawn.
- `ruff check src/openzues/schemas.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the `sessions.spawn` thread-binding hook seam.
- `mypy src/openzues/schemas.py src/openzues/services/gateway_node_methods.py`: clean after the `sessions.spawn` thread-binding hook seam.
- `pytest tests/test_gateway_node_methods.py -q -k "sessions_spawn_rejects_acp_required_sandbox_policy or sessions_spawn_thread_mode_requires_thread_binding_hook or agents_list_sessions_spawn_projection_honors_allowlist or agents_list_supports_sessions_spawn_tool_projection or sessions_spawn_rejects_agent_id_outside_configured_allowlist or sessions_spawn_requires_explicit_agent_id_when_configured or sessions_spawn_session_mode_requires_thread_binding or sessions_spawn_rejects_required_sandbox_without_sandbox_runtime or sessions_spawn_persists_depth_role_and_control_scope or sessions_spawn_honors_configured_max_children_per_agent or sessions_spawn_honors_configured_max_spawn_depth or sessions_spawn_derives_requester_depth_from_spawned_by_ancestry or sessions_spawn_rejects_requesters_at_max_spawn_depth or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_materializes_inline_attachments"`: 15 passed after adding the upstream-shaped `runtime="acp" sandbox="require"` policy response before the generic ACP-unavailable boundary.
- `ruff check src/openzues/schemas.py src/openzues/services/gateway_node_methods.py tests/test_gateway_node_methods.py`: clean after the ACP sandbox-policy seam.
- `mypy src/openzues/schemas.py src/openzues/services/gateway_node_methods.py`: clean after the ACP sandbox-policy seam.
- `pytest tests/test_gateway_node_methods.py -q`: 563 passed after restoring `sessions.list agentId="main"` matching for launch-style OpenZues session keys.
- `ruff check src/openzues/services/gateway_sessions.py src/openzues/services/gateway_node_methods.py src/openzues/services/hermes_toolsets.py src/openzues/schemas.py tests/test_gateway_node_methods.py`: clean after the main-agent session filter fix.
- `mypy src/openzues/services/gateway_sessions.py src/openzues/services/gateway_node_methods.py src/openzues/services/hermes_toolsets.py src/openzues/schemas.py`: clean after the main-agent session filter fix.

## Current Queue Head

- Browser command productization is now effectively closed for the current installed-command queue, with persistent proxy/profile mutation left intentionally guarded.
- Cron expression schedules now create, update, list, compute due state, and launch through `cron.run mode=due`; richer upstream cron runtime semantics such as full Croner expression breadth and persisted scheduler error telemetry remain future hardening.
- `agents.files.*` now covers OpenClaw bootstrap and memory filenames (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`, `HEARTBEAT.md`, `BOOTSTRAP.md`, `MEMORY.md`, `memory.md`) while retaining the existing OpenZues `.codex/AGENTS.md` path.
- `plugin.approval.request/list/resolve/waitDecision` now has a bounded OpenClaw-shaped local lifecycle with request/resolved gateway events instead of returning hard 503s.
- `device.pair.list/approve/reject/remove` now operate through persisted node-pair state with OpenClaw-shaped `deviceId` payloads and token redaction.
- `exec.approval.request/list/get/resolve/waitDecision` now has a bounded local lifecycle with ask-aware allowed decisions and request/resolved gateway events instead of returning hard 503s.
- `exec.approvals.get/set/node.get/node.set` now persist redacted JSON policy files under the OpenZues data dir with base-hash guards.
- `device.token.rotate/revoke` now persist role-scoped device auth tokens in SQLite, expose token summaries through `device.pair.list`, reject unknown devices, and revoke by device/role.
- `agents.create/update/delete` now persist custom agents in SQLite, materialize/update workspace `IDENTITY.md`, and surface custom agents through `agents.list`.
- `config.set/patch/apply` now persist the OpenZues control-UI config file with base-hash guards, patch merging, and `config.get` reading back the durable config.
- `doctor.memory.backfillDreamDiary/resetDreamDiary/resetGroundedShortTerm/repairDreamingArtifacts/dedupeDreamDiary` now mutate bounded workspace dreaming artifacts instead of returning hard 503s.
- Admin-scoped `chat.send` origin-route fields now preserve OpenClaw route provenance in the submitted runtime message instead of returning hard 503s.
- Admin-scoped `chat.send` system provenance now preserves OpenClaw input-provenance context and receipt text in the submitted runtime message instead of returning hard 503s.
- `sessions.steer` no longer requires an abort runtime when there is no tracked active run to interrupt; it can safely send through the chat runtime.
- `sessions.create` now accepts persisted custom agents, generates custom-agent session keys, and `sessions.list agentId=...` can filter those sessions.
- `agent.identity.get` now resolves persisted custom agents by explicit `agentId` or `agent:<id>:main` session keys while preserving malformed-key and mismatch guards.
- `agents.files.list/get/set` now use persisted custom-agent workspaces instead of forcing every file request through the main OpenZues workspace.
- `sessions.send` and `sessions.steer` now reject custom-agent session keys after the owning agent has been deleted instead of submitting orphaned runtime messages.
- `chat.history` now hides assistant-only `NO_REPLY` / announce-skip / reply-skip rows and strips inline reply/audio directives from displayed content.
- `chat.history` can now preserve optional assistant usage/cost metadata from persisted control-chat rows without exposing arbitrary debug details.
- `chat.history maxChars` now truncates each displayed text field from the front with an OpenClaw-style `...(truncated)...` marker instead of dropping older rows through a global tail budget.
- `chat.history` now applies the OpenClaw default 8,000-character display cap when callers omit `maxChars`.
- `chat.history` now replaces any single oversized projected message with `[chat.history omitted: message too large]` and OpenClaw truncation metadata before returning the response.
- `chat.history` now keeps messages below OpenClaw's 128 KiB single-message cap, replaces larger projected messages with `[chat.history omitted: message too large]`, and enforces the upstream 6 MiB total response byte budget while keeping the newest messages that fit.
- `tools.catalog` / `tools.effective` now advertise an explicit `sessions_history` tool posture, and `sessions.history` now returns an agent-tool-style redacted transcript projection with default tool-row suppression, `includeTools`, alias resolution, usage/cost stripping, a 4k text cap, and an 80 KiB payload cap.
- `tools.catalog` now advertises `session_status`, and `session.status` now returns an OpenClaw-style status-card payload with `content` / `details`, session snapshot fields, usage/cost summary, and optional provider/model override updates.
- `tools.catalog` now advertises `sessions_send`, and `sessions.send` now accepts `label` plus optional `agentId`, rejects ambiguous key+label selectors, resolves labels through session inventory, and dispatches to the canonical session key through both service and API paths.
- `tools.catalog` / `tools.effective` now advertise `sessions_list`, and `sessions.list` accepts OpenClaw-style `kinds` plus `messageLimit`, filtering `main`/`other` aliases and attaching bounded non-tool recent message context.
- `tools.catalog` now advertises `sessions_spawn`, and `sessions.spawn` creates a bounded subagent-style child session from `task`, persists spawn metadata, sends the initial task with optional thinking/timeout, rejects channel-delivery params, and returns an OpenClaw-style accepted payload.
- `tools.catalog` now advertises `agents_list`, and `agents.list toolProjection=sessions_spawn` returns OpenClaw-style requester, allowAny, and agent target rows while preserving the existing default OpenZues inventory shape.
- `sessions.spawn` now materializes inline attachments under `.openclaw/attachments/<id>`, writes a manifest, returns a receipt, persists it in session metadata, and appends an untrusted-attachment location note to the child task.
- `sessions.spawn requesterSessionKey=...` now resolves the requester session, reads stored `spawnDepth`, and returns OpenClaw-style forbidden status when the caller is already at the default max spawn depth.
- `sessions.spawn requesterSessionKey=...` now also derives requester depth from legacy `spawnedBy` / `parentSessionKey` ancestry when stored `spawnDepth` is absent, so older spawned sessions cannot bypass the default max-depth guard.
- `sessions.spawn` now honors `gateway.agents.defaults.subagents.maxSpawnDepth` from persisted control config, allowing bounded nested subagent launches when configured while preserving the default max depth of 1.
- `sessions.spawn` now honors `gateway.agents.defaults.subagents.maxChildrenPerAgent` by counting live tracked child runs for the requester and returning OpenClaw-style forbidden status before submitting an extra child when the cap is reached.
- `sessions.spawn` now persists depth-derived `subagentRole` (`orchestrator` or `leaf`) and `subagentControlScope` (`children` or `none`) on new child sessions.
- `sessions.spawn sandbox="require"` now returns the OpenClaw-style forbidden response before runtime dispatch when no sandboxed target runtime exists.
- `sessions.spawn mode="session"` now returns the upstream-shaped error unless `thread=true` is also supplied.
- `sessions.spawn` now honors persisted `requireAgentId` and `allowAgents` target policy, and `agents.list toolProjection=sessions_spawn` now projects requester/allowed targets through the same allowlist instead of always returning `allowAny=true`.
- `sessions.spawn thread=true` now returns the upstream-shaped no-hook error before runtime dispatch because OpenZues has no channel plugin `subagent_spawning` hook wired for thread binding.
- `sessions.spawn runtime="acp" sandbox="require"` now returns the upstream-shaped ACP sandbox policy error before the generic ACP-unavailable response.
- `sessions.list agentId="main"` once again includes launch-style OpenZues main/thread session keys instead of treating them as agentless and filtering them out.
- `sessions.preview` now hides assistant skip-only rows and strips inline reply/audio directives before rendering preview items.
- live `session.message` events now strip inline reply/audio directives and suppress assistant-only `NO_REPLY` / `ANNOUNCE_SKIP` / `REPLY_SKIP` rows, with matching suppression of the paired message-phase `sessions.changed` event.
- live `session.message` and `sessions.changed` transcript events now project assistant message usage/cost metadata into fresh top-level token/cost fields.
- live `session.message` and `sessions.changed` transcript events now carry spawned-session metadata, `forkedFromParent`, and last-route thread metadata from persisted session metadata.
- `sessions.get` now supports OpenClaw-style cursor pagination when the visible transcript spans multiple pages, preserving the `messages` field while adding `items`, `hasMore`, `nextCursor`, raw `__openclaw.seq` metadata, and direct string cursor round-trips.
- `sessions.get` now accepts OpenClaw `seq:<n>` cursor strings in addition to bare numeric cursors.
- `sessions.patch` now patches any resolved metadata/message-backed session instead of only the current session, and returns the patched target entry.
- `sessions.create key=main agentId=<custom>` now scopes the main alias to `agent:<id>:main` and persists custom-agent metadata instead of rejecting it as a mismatched `agentId` / `sessionKey` pair.
- `sessions.create key=global|unknown agentId=<custom>` now preserves the literal sentinel keys and avoids creating agent-scoped sentinel records.
- `sessions.create` initial-message / initial-task runs now return the pending `messageSeq` while keeping existing `sessions.send` / `sessions.steer` response shapes stable.
- `sessions.list` snapshots now derive fresh transcript usage totals, estimated cost, assistant model identity, and known Anthropic 1M context from persisted assistant transcript rows.
- mutation `sessions.changed` payloads now carry `totalTokensFresh` and `estimatedCostUsd` alongside the transcript-derived token/model fields.
- mutation `sessions.changed` payloads now carry persisted setting and route fields such as `responseUsage`, `fastMode`, `lastChannel`, `lastTo`, `lastAccountId`, and `lastThreadId`.
- `sessions.patch` now mutates and publishes under resolved agent-store aliases such as `agent:main:subagent:child` when callers use request keys like `subagent:child`.
- session snapshots now include an OpenClaw-shaped `deliveryContext` object derived from persisted `lastChannel` / `lastTo` / `lastAccountId` / `lastThreadId` metadata.
- session snapshots and mutation `sessions.changed` events now preserve string `lastThreadId` values such as Slack decimal thread IDs instead of treating route thread ids as integer-only.
- `sessions.list` defaults now include `modelProvider` alongside `model`, `contextTokens`, and `mainSessionKey`.
- session snapshots now emit `totalTokensFresh: false` for stale/no-usage rows instead of omitting the freshness marker.
- `sessions.patch model=<provider>/<model-id>` now stores `providerOverride` and `modelOverride`, returns OpenClaw-style patch `entry` shape, and resolves/list rows under the split provider/model identity.
- `sessions.reset` now drops stale runtime model metadata while preserving explicit provider/model overrides as `modelOverrideSource: user`.
- `sessions.reset` and session payloads now preserve owned child metadata such as group/channel fields, queue settings, auth-profile overrides, CLI bindings, custom display name, and nested delivery context.
- `sessions.preview` now resolves mixed-case legacy main aliases by keeping the freshest exact stored alias row instead of merging stale duplicate alias transcripts.
- `sessions.delete` now resolves request aliases such as `subagent:child` before deleting metadata/transcript rows and returning the mutation key.
- `sessions.compact` now resolves request aliases such as `subagent:child` before checkpointing/transcript rewriting and returning the compaction key.
- `sessions.compaction.restore` now resolves request aliases such as `subagent:child` before checkpoint lookup, transcript restoration, and checkpoint-restore events.
- `sessions.compaction.list/get` now resolve request aliases such as `subagent:child` before reading checkpoint inventory or checkpoint details.
- `sessions.compaction.branch` now resolves request aliases such as `subagent:child` before copying metadata, branching checkpoint history, and publishing source/target change events.
- `sessions.messages.subscribe/unsubscribe` now resolve request aliases such as `subagent:child` before returning the subscribed key and updating the hub's session-message filter.
- `sessions.get` now resolves request aliases such as `subagent:child` before reading transcript rows.
- `sessions.usage`, `sessions.usage.timeseries`, and `sessions.usage.logs` now resolve request aliases such as `subagent:child` before reading usage summaries, mission points, or usage-linked transcript rows.
- `chat.history` now resolves request aliases such as `subagent:child` before reading transcript rows and session metadata.
- `chat.send`, `sessions.send`, and `sessions.steer` now resolve request aliases such as `subagent:child` before runtime dispatch, run tracking, pending-message counts, and session-change events.
- `chat.abort` now resolves request aliases such as `subagent:child` before interrupting tracked active runs.
- `sessions.abort` now resolves request aliases such as `subagent:child` before interrupting tracked active runs and publishing abort session-change events.
- `sessions.preview` now resolves request aliases such as `subagent:child` before reading transcript previews while preserving the caller's requested key in the multi-preview response slot.
- `tools.effective` now resolves request aliases such as `subagent:child` before deriving session-scoped toolsets and agent identity.
- direct channel `send` now resolves known request aliases such as `subagent:child` before passing source-session provenance to the delivery runtime, while preserving unknown structural route keys exactly.
- `plugin.approval.request` and `exec.approval.request` now resolve known request aliases such as `subagent:child` before storing durable approval provenance, while preserving unknown legacy session ids.
- internal `node.event` routing now resolves known request aliases such as `subagent:child` before chat subscriptions, exec/notification wake events, voice transcripts, and agent requests, while preserving the raw recorded node event.
- `wake` now resolves known request aliases such as `subagent:child` before deriving agent id and queueing wake requests.
- known `subagent:*` aliases now resolve through unique session-id lookup when the canonical store key belongs to a custom agent, so `agent.identity.get` and shared runtime resolvers do not collapse custom child sessions back to `main`.
- `agent` launches now accept persisted custom `agentId` values and resolve known short child aliases before runtime dispatch, so custom-agent child runs route to keys such as `agent:builder-prime:subagent:child`.
- `agent` launches with a persisted custom `agentId` and no explicit session selector now default to that agent's scoped main session, for example `agent:builder-prime:main`, and persist the agent metadata for session discovery.
- `sessions.patch` now uses the shared existing-session resolver, so short aliases can patch canonical custom-agent child sessions instead of failing lookup or writing a stray `subagent:*` metadata row.
- `sessions.reset` now uses the shared existing-session resolver before clearing transcript/runtime metadata, so custom-agent child aliases reset the canonical session while preserving durable agent metadata.
- `sessions.delete` now uses the shared existing-session resolver before archive/delete work, so custom-agent child aliases delete the canonical transcript and metadata instead of silently no-oping on the short key.
- `chat.inject` now resolves request aliases before appending assistant messages, so custom-agent child aliases persist injected notes on the canonical session.
- `sessions.create parentSessionKey` now resolves request aliases before deriving child thread keys, so custom-agent parent aliases spawn under the canonical custom parent.
- `sessions.create key=subagent:* agentId=<custom>` now scopes explicit child keys into the custom-agent store, for example `agent:builder-prime:subagent:child`, instead of rejecting them as main-agent mismatches.
- `sessions.resolve key=subagent:* agentId=<custom>` now uses the custom agent as the request-key scope, while `sessionId` and label agent filters reject legacy launch sessions unless the caller uses an explicit key lookup.
- live `session.message` payloads now carry nested OpenClaw transcript identity metadata (`message.__openclaw.id` / `message.__openclaw.seq`) alongside the existing top-level `messageId` / `messageSeq`.
- `sessions.subscribe` now receives live `session.message` transcript events as well as `sessions.changed`, matching OpenClaw's broad operator session stream while preserving narrower `sessions.messages.subscribe` filters.
- direct `GET /sessions/{sessionKey}/history` now exposes OpenClaw-style JSON/SSE history over REST, including cursor pagination, preserved `messages`, `items`, `hasMore`, `nextCursor`, raw `__openclaw.seq` metadata, default 8k text caps, lenient invalid-cursor handling, initial `history` SSE events, and `not_found` responses for unknown session keys.
- RPC `sessions.get` now defaults to OpenClaw's 200-message limit instead of clipping no-limit reads to 50 messages.
- direct session-history SSE streams now remain live: unbounded streams emit inline OpenClaw-style `message` events from `session.message`, bounded or cursor streams emit refreshed `history` snapshots, and non-message `sessions.changed` updates refresh history without duplicating normal message-phase changes.
- direct session-history SSE streams now suppress `NO_REPLY`-only live messages, keep bounded windows anchored on visible history after silent refreshes, and preserve raw `messageSeq` numbering after transcript-only refreshes.
- `chat.history` and direct session-history REST/SSE now honor persisted `gateway.webchat.chatHistoryMaxChars`, while explicit RPC `maxChars` still wins over config.
- RPC `sessions.get` now honors explicit limits above the direct REST history cap, matching OpenClaw's method behavior while the HTTP history endpoint still clamps REST `limit` to 1000.
- direct session-history HTTP now rejects non-GET methods with OpenClaw's `Allow: GET` plus plain-text `Method Not Allowed` response instead of FastAPI's default JSON 405.
- direct session-history HTTP now rejects blank decoded session keys with OpenClaw's `invalid_request_error` JSON before lookup or method-specific handling.
- remote direct session-history HTTP now honors declared `x-openclaw-scopes`, rejecting declared scope sets that omit `operator.read` while preserving loopback and no-header API-key behavior.
- direct `POST /tools/invoke` now exists with OpenClaw-shaped success/error payloads, maps safe core tool aliases such as `agents_list` into existing OpenZues gateway methods, denies high-risk tool names by default, and honors persisted `gateway.tools.allow` / `gateway.tools.deny` for the bounded `cron` action bridge.
- `tools.invoke` now has an injected before-call hook boundary: hook owners can block with OpenClaw-shaped `tool_call_blocked` errors or rewrite params before the mapped gateway method executes.
- `tools.invoke` now accepts injected plugin/non-core executors keyed by tool name, but keeps them hidden unless persisted `gateway.tools.allow` explicitly opens the tool; allowed executor calls receive the generated `toolCallId` and hook-rewritten params.
- Plugin executor failures now use OpenClaw-shaped `tool_error` envelopes: input/auth failures map to `400`/`403`, while unexpected crashes become sanitized `500 tool execution failed` responses.
- Owner-only `tools.invoke` filtering now survives `gateway.tools.allow`: scoped non-admin callers still cannot invoke owner-only control-plane tools such as `cron`, while admin/internal owner calls can.
- Injected plugin executors can now declare custom owner-only metadata for `tools.invoke`, keeping allowed custom tools hidden from scoped non-admin callers while preserving admin/internal owner execution.
- `chat.inject`, `chat.history`, and live session message projection now strip trailing OpenClaw external-untrusted metadata suffix blocks from visible transcript text.
- `chat.send` now strips trailing OpenClaw external-untrusted metadata suffix blocks from returned final payload text blocks while preserving normal run-ack payloads.
- `chat.send` now projects media-only final reply payloads with stale
  `NO_REPLY` text into OpenClaw-style `MEDIA:<url>` assistant transcript text.
- Verified the media-only final reply seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_chat_send_projects_media_only_final_payload_text_like_openclaw
  -q` (`1 passed`), adjacent chat-send proof `python -m pytest
  tests\test_gateway_node_methods.py -q -k "chat_send and (final_payload or
  returns_run_ack or attachment_runtime or inherited_delivery_context)"` (`4
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- `chat.send deliver=true` now inherits persisted channel-scoped `deliveryContext` routes when the session key is scoped to the same external channel.
- Gateway requester metadata now carries `clientMode`, allowing configured-main CLI `chat.send` delivery inheritance while keeping UI/webchat callers route-local.
- Session snapshots now derive missing delivery context from `origin.provider/accountId/threadId` metadata, allowing older configured-main routes to resume external delivery.
- Webchat `chat.send deliver=true` callers no longer inherit external delivery routes from channel-scoped sessions, preventing browser-origin cross-posts.
- `tools.invoke` now opens native `sessions_spawn` only when `gateway.tools.allow` explicitly allows it, while default-deny behavior remains intact.
- `tools.invoke` now opens native `sessions_send` only when `gateway.tools.allow` explicitly allows it, preserving default high-risk hiding.
- Direct `/tools/invoke` now propagates OpenClaw route headers
  (`x-openclaw-message-channel`, `x-openclaw-account-id`, `x-openclaw-message-to`,
  `x-openclaw-thread-id`) into allowed `sessions_spawn` calls, preserving
  `requesterOrigin` and child-session `deliveryContext`.
- Direct `/tools/invoke` now treats body `sessionKey` as the requester context
  for allowed `sessions_spawn`, so child sessions preserve the real
  `spawnedBy` / `parentSessionKey` instead of falling back to main.
- Direct `/tools/invoke` now preserves requester provenance for allowed
  `sessions_send`, mapping body `sessionKey` and route channel into the
  OpenClaw input-provenance envelope sent to the target runtime.
- `sessions_send` invoked through `/tools/invoke` now accepts OpenClaw's
  `timeoutSeconds` argument and converts it into native millisecond runtime
  dispatch timeouts, while preserving existing `timeoutMs` behavior.
- `sessions_send` with `timeoutSeconds: 0` now returns OpenClaw's no-wait
  accepted tool shape (`status: accepted`, target `sessionKey`, pending
  announce `delivery`) instead of leaking the raw internal chat runtime result.
- `sessions_send` through `tools.invoke` now accepts OpenClaw's target
  `sessionKey` argument and translates it to OpenZues' native `key` before
  dispatch.
- successful nonzero `sessions_send timeoutSeconds` calls now return
  OpenClaw-shaped `status: ok` results with optional `reply`, target
  `sessionKey`, and pending announce `delivery` when the runtime adapter
  supplies a fresh reply.
- nonzero `sessions_send timeoutSeconds` calls now wait for a fresh assistant
  transcript row after dispatch and return that reply in the OpenClaw-shaped
  tool result, instead of only succeeding when the runtime adapter inlines
  `reply`.
- `sessions_send timeoutSeconds` now accepts numeric OpenClaw values and floors
  them to whole seconds before converting to native milliseconds.
- `sessions_send` timeout/error results now preserve OpenClaw's target
  `sessionKey` envelope when the runtime returns timeout or error status.
- `sessions_spawn` now accepts numeric `runTimeoutSeconds` / `timeoutSeconds`
  values and floors them to whole seconds before runtime dispatch.
- `sessions_send` inter-session runtime prompts now include OpenClaw's
  agent-to-agent message context, naming requester session/channel and target
  session in addition to the provenance envelope.
- waited successful `sessions_send` calls now schedule OpenClaw-style
  agent-to-agent announce work after the target reply: the target receives the
  structured announce prompt, `ANNOUNCE_SKIP` suppresses output, and non-skip
  announce replies deliver to the target session's saved channel/thread route.
- no-wait `sessions_send timeoutSeconds=0` calls now start the same announce
  flow after a later assistant transcript reply appears, using OpenClaw's 30s
  announce wait budget while still returning the immediate accepted result.
- `sessions_send` A2A announce flow now runs OpenClaw's requester/target
  reply ping-pong loop before final announce, honoring `REPLY_SKIP` and the
  default five-turn cap.
- `session.agentToAgent.maxPingPongTurns` is now accepted by the control
  config schema and honored by the `sessions_send` A2A reply loop.
- top-level `tools.agentToAgent.enabled` now gates cross-agent
  `sessions_send` calls before runtime dispatch, returning OpenClaw-style
  forbidden results when cross-agent messaging is disabled.
- top-level `tools.sessions.visibility` is now accepted by the control config
  schema and enforced for `tools.invoke sessions_send`: the OpenClaw default
  `tree` visibility blocks cross-agent sends unless visibility is `all`, blocks
  unrelated same-agent sessions, allows spawned child sessions, and explicit
  `self` / `agent` visibility behaves distinctly before runtime dispatch.
- the same `tools.sessions.visibility` / `tools.agentToAgent` access guard now
  applies to neighboring `tools.invoke` session tools: `sessions_history` and
  `session_status` return OpenClaw-style forbidden results before lookup, while
  `sessions_list` filters invisible rows instead of leaking cross-agent
  sessions.
- `tools.invoke sessions_send` now applies OpenClaw's pre-resolution
  cross-agent `label + agentId` policy gate, so disabled A2A blocks label-based
  cross-agent sends before session lookup or runtime dispatch.
- `tools.invoke sessions_send` now resolves label targets before capturing the
  wait baseline, so label-based sends return the canonical target `sessionKey`
  and wait for the fresh target reply just like key-based sends.
- label-based `sessions_send timeoutSeconds=0` now uses the same resolved
  target key for the immediate accepted result and the later A2A announce flow.
- `sessions.history` now matches OpenClaw `sessions_history` tool-message
  filtering for `toolResult`: hidden by default and preserved only when
  `includeTools=true`.
- `sessions.history` now also applies OpenClaw's `session-transcript-repair`
  redaction for structured `sessions_spawn` tool-call inputs: inline
  `attachments[].content` is replaced with `__OPENCLAW_REDACTED__`, only safe
  attachment metadata is preserved, and the original attachment bytes do not
  replay through the history read model.
- `sessions.list` now accepts OpenClaw numeric filters for `limit`,
  `activeMinutes`, and `messageLimit`, flooring/clamping them instead of
  rejecting non-integer numbers.
- `session.status model=default` now mirrors OpenClaw reset semantics by
  clearing model/auth-profile override metadata, marking a live model switch
  pending when selection changed, and reporting `changedModel` from the actual
  metadata delta.
- `chat.history` and `sessions.history` now strip assistant-visible
  `<tool_result>...</tool_result>` XML blocks and dangling thinking blocks at
  the shared transcript display boundary.
- `sessions_yield` is now present in the native gateway, `tools.invoke`, and
  tool catalog surfaces with OpenClaw-compatible context/error/callback result
  shapes.
- `sessions.spawn` now cleans up provisional child sessions when runtime start
  fails: the failed child metadata/transcript/remembered run state are removed,
  attachment materialization is best-effort deleted, and the caller receives an
  OpenClaw-shaped error with the provisional `childSessionKey`.
- `sessions.spawn` now preserves OpenClaw's ACP preflight error order for
  unsupported `lightContext` and inline attachments before falling back to the
  local ACP-unavailable boundary.
- `chat.history` and `sessions.history` now accept finite numeric `limit`
  values and floor them like OpenClaw's session-history paths, instead of
  rejecting non-integer JSON numbers.
- `sessions.get` now matches OpenClaw's finite numeric `limit` behavior too,
  flooring values like `1.9` while preserving the existing high explicit-limit
  transcript read path.
- `sessions.preview` now mirrors OpenClaw key normalization: whitespace-only
  keys are filtered into an empty preview result, duplicate keys are preserved,
  and preview requests are capped to the first 64 normalized keys.
- `tools.invoke sessions_list` now recomputes `count` after OpenZues applies
  OpenClaw-style visibility filtering, so the result count matches the visible
  rows returned to the caller.
- `tools.invoke sessions_list` now also applies OpenClaw's agent-tool global
  row filter, dropping `unknown` and hiding `global` unless the requester is the
  global alias.
- `tools.invoke sessions_list` now ignores unsupported OpenClaw tool `kinds`
  values before native dispatch, so values like `global` do not accidentally
  filter away normal visible sessions.
- `tools.invoke sessions_list` now projects only OpenClaw-supported tool args
  (`limit`, `activeMinutes`, `messageLimit`, supported `kinds`) before native
  dispatch, so local-only filters such as `label` do not change agent-tool
  results.
- `tools.invoke sessions_history` now projects only OpenClaw-supported tool
  args (`sessionKey`, `limit`, `includeTools`) before native dispatch, ignoring
  local-only fields such as `maxChars`.
- `tools.invoke session_status` now projects only OpenClaw-supported tool args
  (`sessionKey`, `model`) before native dispatch, ignoring local-only fields
  such as `includeDebug`.
- `tools.invoke sessions_yield` now matches OpenClaw's context contract: only
  the requester session context can provide `sessionKey`, while tool args are
  projected down to the optional `message`.
- `tools.invoke sessions_send` now drops unknown tool args after session-key
  and requester-context translation, preserving supported OpenClaw/local
  compatibility fields while ignoring extra payload metadata.
- `tools.invoke sessions_spawn` now drops unknown tool args before native
  dispatch while preserving OpenClaw's explicit unsupported delivery-param
  errors for keys such as `target`.
- `tools.invoke sessions_spawn` now treats requester lineage like OpenClaw:
  only top-level runtime/requester context can supply `requesterSessionKey`,
  while raw tool args cannot spoof spawn parent metadata.
- accepted `sessions.spawn` results now include OpenClaw's push-based
  subagent note for run-mode spawns, reminding callers to wait for completion
  events instead of polling session tools.
- accepted `sessions.spawn` results now report `modelApplied: true` when an
  explicit model override is persisted for the child session.
- `sessions.create` now reports OpenClaw's specific key-agent mismatch error
  when an explicit `key` belongs to a different agent than `agentId`.
- `sessions.create` now keeps the created session durable and returns
  `runError` when the optional initial agent turn fails, instead of aborting
  the create call.
- `sessions.patch` now rejects spawn-lineage fields such as `spawnedBy` on
  non-subagent/non-ACP sessions, matching OpenClaw's lineage support gate.
- `sessions.patch` now preserves OpenClaw's spawn-lineage immutability, so
  already-set lineage fields cannot be changed or cleared.
- `sessions.patch` now rejects duplicate session labels before updating
  metadata, matching OpenClaw's `label already in use` guard.
- `sessions.patch` now normalizes `responseUsage` like OpenClaw, mapping
  `"on"` and aliases to `"tokens"` and using the upstream invalid-value
  message.
- `sessions.patch` now normalizes `execSecurity` case and rejects unsupported
  values with OpenClaw's `deny` / `allowlist` / `full` contract.
- `sessions.patch` now normalizes `execAsk` case and rejects unsupported
  values with OpenClaw's `off` / `on-miss` / `always` contract.
- `sessions.patch` now normalizes `execHost` case and rejects unsupported
  values with OpenClaw's `auto` / `sandbox` / `gateway` / `node` contract.
- `sessions.patch` now normalizes `elevatedLevel` aliases such as
  `auto-approve` to `full`, matching OpenClaw elevated-mode semantics.
- `sessions.patch` now normalizes `sendPolicy` case and rejects unsupported
  values with OpenClaw's `allow` / `deny` contract.
- `sessions.patch` now normalizes `groupActivation` case and rejects
  unsupported values with OpenClaw's `mention` / `always` contract.
- `sessions.delete deleteTranscript=false` now deletes the session entry while
  retaining transcript messages, matching OpenClaw's archive/delete split.
- `chat.send timeoutMs` now mirrors OpenClaw's timer-safe timeout resolver:
  zero becomes the no-timeout sentinel and oversized values clamp to
  `2_147_000_000` instead of being rejected.
- `chat.send sessionKey` now honors OpenClaw's 512-character protocol cap,
  rejecting oversized keys before they reach the chat runtime.
- `chat.send systemInputProvenance` now uses OpenClaw's strict schema
  validation, rejecting non-object values and unknown `kind` values before
  admin-scope checks or runtime dispatch.
- `chat.inject` now mirrors OpenClaw's compact schema by rejecting empty
  `message` values and labels longer than 100 characters.
- `chat.abort` now rejects present-but-empty `runId` values instead of
  treating them as broad session aborts.
- `agent.wait` now consumes spawned-run lifecycle metadata for the bounded
  local path: `cleanup: "delete"` removes ephemeral child session state, default
  completion announcements write parent-visible messages, and
  `completionAnnouncedRunId` prevents duplicate announcements when the same
  terminal run is observed again.
- Verified the spawn lifecycle wait/idempotency seams with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_does_not_duplicate_spawn_completion_announcement"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `agent.wait` now ignores stale terminal mission rows when their terminal
  timestamp predates the tracked run start, avoiding false completion of a
  newer run in a reused session.
- Verified the tracked-run freshness seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_ignores_stale_terminal_session_mission_for_tracked_run"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `agent.wait timeoutMs=0` now stays a no-wait poll instead of widening to the
  omitted-timeout default.
- Verified the `agent.wait` zero-timeout seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_zero_timeout_returns_without_sleeping"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `agent.wait` now prefers exact `swarm.run_id` mission matches before the
  session-level fallback, so active neighboring mission state cannot hide the
  requested terminal run.
- Verified the exact run-id wait precedence seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_prefers_exact_run_id_over_active_session_fallback"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `agent.wait` recovered from durable exact `swarm.run_id` metadata now uses
  the normal session alias tracker, so terminal wait consumption forgets the
  synthesized run id.
- Verified the recovered exact-run cleanup seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_forgets_recovered_exact_run_id_after_terminal_snapshot"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- historical exact `agent.wait` lookups now preserve a different current run
  already tracked for the same session.
- Verified the exact-run tracker isolation seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_exact_run_id_does_not_evict_different_active_session_run"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.spawn` active-child-cap pruning now observes terminal tracked
  children without consuming the `agent.wait` lifecycle. Parent completion
  announcements and cleanup remain attached to the later wait call instead of
  being triggered by max-child counting.
- Verified the child-cap pruning wait-lifecycle seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_child_cap_pruning_does_not_consume_wait_lifecycle"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero or sessions_spawn_child_cap_pruning_does_not_consume_wait_lifecycle"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- tracked `agent.wait` session fallback now resolves the latest terminal
  mission for the session instead of reusing the status-oriented lookup that
  prefers active rows. Stale active mission rows no longer mask completed or
  failed terminal state for a tracked run.
- Verified the terminal-over-active wait fallback seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_prefers_terminal_session_mission_over_stale_active"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_child_cap_pruning_does_not_consume_wait_lifecycle or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\database.py src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\database.py src\openzues\services\gateway_node_methods.py`.
- tracked `agent.wait` thread-child fallback now also resolves terminal child
  missions under the tracked parent session with terminal-only ordering, so
  stale active child rows cannot mask completed or failed child terminal state.
- Verified the terminal thread-child wait fallback seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_prefers_terminal_thread_child_mission_over_stale_active"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_child_cap_pruning_does_not_consume_wait_lifecycle or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\database.py src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\database.py src\openzues\services\gateway_node_methods.py`.
- exact `agent.wait` run-id lookup now prefers terminal `swarm.run_id`
  missions before falling back to the existing active-aware run lookup, so
  duplicate stale active rows cannot mask completed or failed exact-run state.
- Verified the terminal exact-run wait lookup seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_prefers_terminal_exact_run_id_over_stale_active"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_child_cap_pruning_does_not_consume_wait_lifecycle or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\database.py src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\database.py src\openzues\services\gateway_node_methods.py`.
- tracked `agent.wait` fallback now discards stale terminal candidates before
  continuing to the next source, so an old exact terminal row cannot block a
  fresher terminal session or child mission.
- Verified the stale-terminal fallback chain seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_ignores_stale_exact_terminal_before_session_fallback"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_child_cap_pruning_does_not_consume_wait_lifecycle or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\database.py src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\database.py src\openzues\services\gateway_node_methods.py`.
- after dropping a stale exact terminal candidate, tracked `agent.wait` now
  re-checks the active-aware exact run-id lookup before session fallback, so an
  active exact run cannot be completed by an unrelated session terminal row.
- Verified the active-exact-after-stale-terminal seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait_preserves_active_exact_run_after_stale_terminal"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "agent_wait or sessions_spawn_child_cap_pruning_does_not_consume_wait_lifecycle or sessions_spawn_creates_openclaw_style_subagent_session or sessions_spawn_persists_completion_expectation_override or sessions_spawn_defaults_omitted_run_timeout_to_zero"`, `ruff check src\openzues\database.py src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\database.py src\openzues\services\gateway_node_methods.py`.
- `sessions.spawn sandbox="require"` now resolves OpenClaw-style
  `agents.defaults.sandbox` and `agents.list[].sandbox` target posture before
  dispatch. Effective `mode="off"` targets return the existing precise
  forbidden response even when a native sandbox send adapter is wired, while
  `mode="all"` keeps the native workspace-write sandbox dispatch path.
- Verified the config-gated required-sandbox seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_rejects_required_sandbox_when_target_config_is_off"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn"`, `python -m pytest tests\test_gateway_sandbox_spawn.py -q`, `python -m pytest tests\test_cli.py -q -k "sandbox_explain or sandbox_list or sandbox_recreate"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\gateway_config.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\schemas.py src\openzues\services\gateway_config.py`.
- `sessions.spawn sandbox="inherit"` now preserves OpenClaw's sandbox escape
  guard: when the requester session is sandboxed by effective config, spawning
  an unsandboxed target agent returns the upstream forbidden message before any
  child dispatch.
- Verified the sandboxed-requester guard with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_rejects_sandboxed_requester_to_unsandboxed_target"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `sessions.spawn sandbox="inherit"` now also honors effective sandboxed child
  targets from `agents.defaults.sandbox.mode="all"` or `"non-main"` by routing
  through the native sandbox send adapter and persisting the same sandbox
  runtime metadata as explicit `sandbox="require"` spawns.
- Verified the inherited sandbox dispatch seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_inherit_dispatches_sandboxed_config_target"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn"`, `python -m pytest tests\test_gateway_sandbox_spawn.py -q`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `RuntimeManagerSandboxChatSendService` now reports a read-only sandbox policy
  when dispatched with `sandbox_mode="read-only"` instead of stamping every
  sandboxed turn as workspace-write.
- Verified the adapter policy seam with `python -m pytest tests\test_gateway_sandbox_spawn.py -q -k "read_only_policy"`, adjacent `python -m pytest tests\test_gateway_sandbox_spawn.py -q`, `ruff check src\openzues\services\gateway_sandbox_spawn.py tests\test_gateway_sandbox_spawn.py`, and `mypy src\openzues\services\gateway_sandbox_spawn.py`.
- `sessions.spawn` now maps explicit OpenClaw `workspaceAccess="ro"` / `"none"`
  sandbox config to native `read-only` Codex sandbox turns, preserving
  `sandboxWorkspaceAccess` and read-only runtime policy metadata on the child
  session; omitted or `"rw"` access stays on the writable workspace sandbox
  path.
- Verified the workspace-access mapping seam with `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_maps_read_only_workspace_access_to_sandbox_mode"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn"`, `python -m pytest tests\test_gateway_sandbox_spawn.py -q`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `agent` follow-up launches into sandboxed spawned sessions now mirror
  OpenClaw's spawned-workspace override: OpenZues resolves
  `spawnedWorkspaceDir` / `sandboxWorkspaceRoot`, dispatches through the native
  sandbox runtime with `sandbox="require"`, target `agentId`, and the saved
  sandbox mode, persists returned runtime/policy metadata, and keeps the run
  tracked for `agent.wait`.
- Verified the sandboxed spawned-session `agent` follow-up seam with `python -m
  pytest
  tests\test_gateway_node_methods.py::test_agent_launch_to_sandboxed_spawned_session_uses_child_workspace_runtime
  -q` (`1 passed`), adjacent launch/sandbox coverage `python -m pytest
  tests\test_gateway_node_methods.py::test_agent_launch_uses_resolved_custom_subagent_store_key
  tests\test_gateway_node_methods.py::test_agent_launch_to_sandboxed_spawned_session_uses_child_workspace_runtime
  tests\test_gateway_node_methods.py::test_agent_launch_defaults_custom_agent_to_scoped_main_session
  tests\test_gateway_node_methods.py::test_sessions_spawn_required_sandbox_dispatches_when_runtime_wired
  tests\test_gateway_node_methods.py::test_sessions_spawn_required_sandbox_persists_runtime_policy_metadata
  -q` (`5 passed`), wider targeted coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "agent_launch or
  sessions_spawn_required_sandbox or
  sessions_spawn_inherit_dispatches_sandboxed_config_target or
  sessions_spawn_maps_read_only_workspace_access_to_sandbox_mode"` (`25
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Sandboxed `sessions.spawn` calls that omit `cwd` now resolve the configured
  child sandbox `workspaceRoot` before staging inline attachments, persist that
  workspace as `spawnedWorkspaceDir`, pass it into the sandbox dispatch, and
  preserve the OpenClaw untrusted-attachment prompt suffix.
- Verified the sandbox attachment workspace-staging seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_sandboxed_attachments_stage_in_child_workspace_when_cwd_omitted
  -q`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_sandboxed_attachments_stage_in_child_workspace_when_cwd_omitted
  or sessions_spawn_materializes_inline_attachments or
  sessions_spawn_inherit_dispatches_sandboxed_config_target or
  sessions_spawn_rejects_acp_attachments_before_runtime_boundary"`,
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- `sessions.spawn` now also mirrors OpenClaw's materialized-attachment failure
  cleanup: if provisional child metadata/session materialization fails after
  inline attachments are staged but before runtime dispatch, OpenZues removes
  the attachment directory, deletes provisional metadata/messages, cleans
  thread binding state, and returns the spawn error envelope without starting
  the child runtime.
- Verified the attachment materialization failure cleanup seam with `python -m
  pytest tests\test_gateway_node_methods.py -q -k
  "removes_materialized_attachments_when_metadata_patch_fails"` (`1 passed`),
  adjacent spawn coverage `python -m pytest tests\test_gateway_node_methods.py
  -q -k "sessions_spawn_materializes_inline_attachments or
  sessions_spawn_sandboxed_attachments_stage_in_child_workspace_when_cwd_omitted
  or sessions_spawn_removes_materialized_attachments_when_metadata_patch_fails
  or sessions_spawn_cleans_up_provisional_child_when_runtime_start_fails or
  sessions_spawn_required_sandbox_dispatches_when_runtime_wired or
  sessions_spawn_required_sandbox_persists_runtime_policy_metadata"` (`6
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Tracked `sessions.spawn` attachment directories now participate in the
  OpenClaw terminal cleanup lifecycle: completed child runs remove staged
  attachment directories when `cleanup="delete"` or when the session is kept
  without `tools.sessions_spawn.attachments.retainOnSessionKeep=true`, while
  provisional child metadata and transcripts remain intact for kept sessions.
- Verified the attachment retention cleanup seam with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "agent_wait_removes_spawn_attachments_when_child_run_is_kept"` (`1 passed`),
  adjacent wait/spawn coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "agent_wait_removes_spawn_attachments_when_child_run_is_kept or
  sessions_spawn_materializes_inline_attachments or
  sessions_spawn_removes_materialized_attachments_when_metadata_patch_fails or
  sessions_spawn_sandboxed_attachments_stage_in_child_workspace_when_cwd_omitted
  or sessions_spawn_cleans_up_provisional_child_when_runtime_start_fails or
  agent_wait_applies_spawn_cleanup_delete_on_terminal_child_run or
  agent_wait_waits_for_tracked_gateway_run_completion or
  agent_wait_prefers_terminal_session_mission_over_stale_active or
  agent_wait_does_not_duplicate_spawn_completion_announcement"` (`9 passed`),
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- OpenClaw's `tools.sessions_spawn.attachments` config block is now preserved
  by the native control config schema and consumed by `sessions.spawn` for
  explicit `enabled=false`, `maxFiles`, `maxFileBytes`, `maxTotalBytes`, and
  `retainOnSessionKeep` attachment behavior while leaving absent config on the
  existing OpenZues-compatible enabled path.
- Verified the attachment config-limit seam with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "attachment_limits_follow_openclaw_config or
  rejects_attachments_when_openclaw_config_disables_them"` (`2 passed`),
  adjacent attachment coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "attachment_limits_follow_openclaw_config or
  rejects_attachments_when_openclaw_config_disables_them or
  sessions_spawn_materializes_inline_attachments or
  sessions_spawn_removes_materialized_attachments_when_metadata_patch_fails or
  agent_wait_removes_spawn_attachments_when_child_run_is_kept or
  sessions_spawn_sandboxed_attachments_stage_in_child_workspace_when_cwd_omitted
  or sessions_spawn_rejects_acp_attachments_before_runtime_boundary or
  sessions_spawn_cleans_up_provisional_child_when_runtime_start_fails"` (`8
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  src\openzues\schemas.py tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py`.
- Sandboxed `chat.send` attachment delivery now stages decoded base64 media
  inside the saved session workspace at `media/inbound/...`, strips inline
  payload bytes before attachment-runtime handoff, and carries sandbox-relative
  media paths in the runtime prompt so sandboxed turns can reference staged
  media without host gateway attachment paths.
- Verified the sandboxed chat-send media staging seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_chat_send_sandboxed_attachment_stages_media_in_session_workspace
  -q`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k
  "chat_send_sandboxed_attachment_stages_media_in_session_workspace or
  chat_send_uses_attachment_runtime_when_wired or
  chat_send_passes_image_order_for_mixed_inline_and_offloaded_attachments or
  chat_send_effective_attachments_fail_as_unavailable_runtime or
  chat_send_ignores_inert_attachments_without_effective_content"`, endpoint
  proof `python -m pytest tests\test_gateway_nodes_api.py -q -k
  "effective_chat_send_attachments or preserves_chat_send_attachment_image_order
  or sessions_send_effective_attachments"`, `ruff check
  src\openzues\services\gateway_node_methods.py src\openzues\app.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py src\openzues\app.py`.
- Sandboxed `sessions.send` attachment delivery now reuses the same
  `media/inbound/...` workspace staging path as `chat.send`, so inter-session
  sends into sandboxed sessions strip inline payload bytes before attachment
  runtime handoff and carry sandbox-relative media paths in the runtime prompt.
- Verified the sandboxed sessions-send media staging seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_send_sandboxed_attachment_stages_media_in_session_workspace
  -q`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k
  "sessions_send_sandboxed_attachment_stages_media_in_session_workspace or
  sessions_send_uses_attachment_runtime_when_wired or
  sessions_send_effective_attachments_fail_as_unavailable_runtime or
  sessions_send_ignores_inert_attachments_without_effective_content or
  chat_send_sandboxed_attachment_stages_media_in_session_workspace"`, endpoint
  proof `python -m pytest tests\test_gateway_nodes_api.py -q -k
  "sessions_send_effective_attachments or effective_chat_send_attachments"`,
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Sandboxed `sessions.steer` attachment delivery now reuses the same
  `media/inbound/...` workspace staging path for steered follow-up messages,
  preserving interruption behavior while giving the runtime sandbox-relative
  media paths instead of inline payload bytes.
- Verified the sandboxed sessions-steer media staging seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_steer_sandboxed_attachment_stages_media_in_session_workspace
  -q`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k
  "sessions_steer_sandboxed_attachment_stages_media_in_session_workspace or
  sessions_steer_uses_attachment_runtime_when_wired or
  sessions_steer_effective_attachments_fail_as_unavailable_runtime or
  sessions_steer_ignores_inert_attachments_without_effective_content or
  sessions_send_sandboxed_attachment_stages_media_in_session_workspace or
  chat_send_sandboxed_attachment_stages_media_in_session_workspace"`,
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Sandboxed node `agent.request` attachment delivery now stages decoded media
  into the target session workspace before runtime handoff, so iOS/node-origin
  share requests into sandboxed sessions carry `media/inbound/...` paths and no
  inline payload bytes.
- Verified the sandboxed node-agent-request media staging seam with `python -m
  pytest
  tests\test_gateway_node_methods.py::test_node_event_agent_request_sandboxed_attachment_stages_media_in_session_workspace
  -q`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k
  "node_event_agent_request_sandboxed_attachment_stages_media_in_session_workspace
  or node_event_agent_request_uses_attachment_runtime_when_wired or
  node_event_agent_request_effective_attachments_fail_as_unavailable_runtime or
  sessions_steer_sandboxed_attachment_stages_media_in_session_workspace or
  sessions_send_sandboxed_attachment_stages_media_in_session_workspace or
  chat_send_sandboxed_attachment_stages_media_in_session_workspace"`,
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Telegram native `sendPoll` topic-qualified targets are now covered by the
  same OpenClaw-shaped proof as topic-qualified sends: parent supergroup routes
  accept `telegram:group:<chatId>:topic:<threadId>` and the provider payload
  carries Bot API `message_thread_id`.
- Verified the Telegram topic poll proof with `python -m pytest tests\test_ops_mesh.py -q -k "send_direct_channel_poll_parses_telegram_topic_target"`, adjacent `python -m pytest tests\test_ops_mesh.py -q -k "telegram_topic_target or topic_to_parent or send_direct_channel_poll_uses_telegram_native_route or send_direct_channel_poll_parses_telegram_topic_target"`, and `ruff check tests\test_ops_mesh.py`.
- Provider-backed `gateway.send` now resolves sandbox container media paths
  from source-session metadata before runtime dispatch: `/workspace/...` and
  `file:///workspace/...` are mapped to the saved sandbox workspace root,
  equivalent aliases dedupe after mapping, and remote media URLs stay intact.
- Verified the sandbox outbound-media normalization seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_send_normalizes_sandbox_workspace_media_paths_from_session_metadata
  -q`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k
  "send_normalizes_sandbox_workspace_media_paths_from_session_metadata or
  send_uses_channel_message_runtime_for_media_payloads or
  send_preserves_provider_native_reply_thread_and_document_options"`,
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- `update.run` now returns the OpenClaw-shaped runtime update envelope with
  `ok`, native update result stats, restart scheduling metadata, and a restart
  sentinel payload/file carrying session delivery context, thread id, note, and
  the upstream 1000ms minimum timeout normalization.
- `update.run` now also executes a native fakeable update runner before
  restart projection: app/CLI construction wires
  `RuntimeUpdateService.run_update`, successful git/install/build results
  schedule restart payloads, and dirty worktrees return OpenClaw-shaped
  `status="skipped"` / `reason="dirty"`.
- Verified the update-run envelope/sentinel slice with `python -m pytest tests\test_gateway_node_methods.py -q -k "update_run"`, `python -m pytest tests\test_gateway_nodes_api.py -q -k "update_run"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "update_run or config_write_methods_persist_control_ui_config_with_base_hash or supports_config_set_patch_apply"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- Verified the native update-runner seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_update_run_executes_native_update_runner_before_restart_scheduling
  tests\test_runtime_updates.py::test_runtime_update_run_update_executes_native_git_install_build_steps
  tests\test_runtime_updates.py::test_runtime_update_run_update_skips_dirty_worktree_before_fetch
  -q` (`3 passed`), adjacent runtime proof `python -m pytest
  tests\test_runtime_updates.py -q` (`4 passed`), endpoint proof `python -m
  pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py
  -q -k "update_run"` (`6 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\runtime_updates.py src\openzues\app.py
  src\openzues\cli.py tests\test_gateway_node_methods.py
  tests\test_gateway_nodes_api.py tests\test_runtime_updates.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\runtime_updates.py src\openzues\app.py
  src\openzues\cli.py`.
- `config.patch` and `config.apply` now return OpenClaw-shaped restart
  sentinel payloads/files with `config-patch` / `config-apply` kind, session
  delivery context, thread id, note, config path stats, and the existing honest
  no-direct-restart result.
- Verified the config restart-sentinel slice with `python -m pytest tests\test_gateway_node_methods.py -q -k "config_write_methods_persist_control_ui_config_with_base_hash"`, `python -m pytest tests\test_gateway_nodes_api.py -q -k "config_write_lifecycle"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "config_write_methods_persist_control_ui_config_with_base_hash or config_write_lifecycle or update_run"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `config.patch` now returns the OpenClaw no-op response for validated patches
  that leave config unchanged, including `noop=true`, current hash/config/path,
  and no restart/sentinel payload.
- Verified the config no-op slice with `python -m pytest tests\test_gateway_node_methods.py -q -k "config_patch_noop_skips_restart_sentinel or config_write_methods_persist_control_ui_config_with_base_hash"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "config_patch_noop_skips_restart_sentinel or config_write_methods_persist_control_ui_config_with_base_hash or config_write_lifecycle or update_run"`, `ruff check src\openzues\services\gateway_node_methods.py src\openzues\services\gateway_config.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py src\openzues\services\gateway_config.py`.
- `secrets.resolve` now dispatches through a fakeable native resolver with
  OpenClaw command/target trimming, known target validation, and resolver-result
  shape projection into `{ok, assignments, diagnostics, inactiveRefPaths}`.
- Verified the secrets resolver slice with `python -m pytest tests\test_gateway_node_methods.py -q -k "secrets_resolve or secrets_reload"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "secrets_resolve or secrets_reload or config_patch_noop_skips_restart_sentinel or update_run"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
- `models.authStatus` now returns a native model-auth snapshot with a fakeable
  runtime hook, sanitized provider/profile projection, cache/refresh semantics,
  and configured refreshable-provider missing synthesis instead of the hard
  unavailable response.
- Verified the model-auth status slice with `python -m pytest tests\test_gateway_models.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "models_auth_status"`, adjacent `python -m pytest tests\test_gateway_models.py -q`, `python -m pytest tests\test_cli.py -q -k "model_auth_status or models_status or infer_model_auth"`, `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "models_auth_status or models_list or secrets_resolve or secrets_reload"`, `ruff check src\openzues\services\gateway_models.py src\openzues\services\gateway_node_methods.py tests\test_gateway_models.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_models.py src\openzues\services\gateway_node_methods.py`.
- `sessions.spawn runtime="acp"` now matches OpenClaw's target-agent policy
  slice: explicit `agentId` or configured `acp.defaultAgent` is required before
  RuntimeManager dispatch, `acp.allowedAgents` rejects forbidden targets with
  `agent_forbidden`, top-level `acp` config survives config validation, and
  accepted ACP child sessions/metadata are stamped with the resolved target
  agent id instead of always `main`.
- Verified the ACP target-agent policy slice with `python -m pytest tests\test_gateway_acp_spawn.py -q`, `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_acp_requires_target_agent_without_default or sessions_spawn_acp_uses_configured_default_agent or sessions_spawn_acp_rejects_agent_outside_acp_allowlist"`, adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k "sessions_spawn_acp or sessions_spawn_rejects_acp or sessions_spawn_session_mode_requires_thread_binding"`, `python -m pytest tests\test_gateway_acp_spawn.py tests\test_gateway_node_methods.py -q -k "acp_spawn or sessions_spawn_acp"`, `python -m pytest tests\test_gateway_node_methods.py -q -k "config_patch_noop_skips_restart_sentinel or config_write_methods_persist_control_ui_config_with_base_hash"`, `ruff check src\openzues\services\gateway_acp_spawn.py src\openzues\services\gateway_node_methods.py src\openzues\services\gateway_config.py src\openzues\schemas.py tests\test_gateway_acp_spawn.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\services\gateway_acp_spawn.py src\openzues\services\gateway_node_methods.py src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- `cron.add` and `cron.update` now accept OpenClaw-style per-job
  `failureAlert` objects instead of rejecting every object shape. The native
  cron owner persists `cron_failure_alert`, projects `failureAlert` through
  `cron.list`/job responses, and merges update patches while preserving the
  `failureAlert=false` override path.
- Verified the cron failure-alert persistence slice with `python -m pytest tests\test_gateway_node_methods.py -q -k "failure_alert_object_like_openclaw"` (`2 passed`), adjacent service cron pack `python -m pytest tests\test_gateway_node_methods.py -q -k "cron_add or cron_update or cron_list or cron_status or cron_runs or cron_run or cron_remove"` (`50 passed`), adjacent API cron pack `python -m pytest tests\test_gateway_nodes_api.py -q -k "cron_add or cron_update or cron_list or cron_status or cron_runs or cron_run or cron_remove"` (`24 passed`), `ruff check src\openzues\schemas.py src\openzues\services\gateway_cron.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\schemas.py src\openzues\services\gateway_cron.py`.
- `cron.update` now accepts OpenClaw-style `patch.state` objects, merges them
  into persisted native `cron_state`, and projects the sanitized runtime state
  fields through cron job snapshots while preserving OpenZues-derived local run
  status when execution data exists.
- Verified the cron state-patch slice with `python -m pytest tests\test_gateway_node_methods.py -q -k "cron_update_persists_state_patch_like_openclaw or cron_update_merges_state_patch_like_openclaw"` (`2 passed`), adjacent service cron pack `python -m pytest tests\test_gateway_node_methods.py -q -k "cron_update or cron_list or cron_status"` (`20 passed`), adjacent API cron pack `python -m pytest tests\test_gateway_nodes_api.py -q -k "cron_update or cron_list or cron_status"` (`11 passed`), `ruff check src\openzues\schemas.py src\openzues\services\gateway_cron.py tests\test_gateway_node_methods.py`, and `mypy src\openzues\schemas.py src\openzues\services\gateway_cron.py`.
- Ops Mesh mission-result handling now consumes per-job cron `failureAlert`
  policy for failed scheduled runs: it persists last run/error/duration/delivery
  state, increments `consecutiveErrors`, emits the OpenClaw-shaped thresholded
  failure-alert message through the native session delivery path, stamps
  `lastFailureAlertAtMs`, and suppresses repeats inside `cooldownMs`.
- Verified the cron failure-alert runtime slice with `python -m pytest tests\test_ops_mesh.py -q -k "cron_failure_alert_threshold"` (`1 passed`), adjacent Ops Mesh cron/failure pack `python -m pytest tests\test_ops_mesh.py -q -k "cron_failure or failure_destination or cron_run or scheduled"` (`13 passed`), adjacent gateway cron pack `python -m pytest tests\test_gateway_node_methods.py -q -k "cron_run or cron_runs or cron_update"` (`23 passed`), `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Main-session `systemEvent` cron dispatch now persists OpenClaw-style success
  state when the wake is queued, including `lastRunStatus="ok"`, duration,
  delivery status, and reset consecutive failure metadata.
- Verified the system-event wake state slice with `python -m pytest tests\test_ops_mesh.py -q -k "routes_due_main_system_event_task_through_wake_queue"` (`1 passed`), adjacent wake/cron pack `python -m pytest tests\test_ops_mesh.py -q -k "main_system_event or cron_failure_alert_threshold or cron_failure or scheduled"` (`16 passed`), adjacent API cron-run pack `python -m pytest tests\test_gateway_nodes_api.py -q -k "main_system_event_cron_run_routes_session_key_through_wake_queue or cron_run"` (`5 passed`), `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- `acp client` now builds an OpenClaw-shaped native spawn plan before handing
  off to a registered runner or returning the existing unavailable boundary:
  default OpenZues ACP launches use `openzues acp`, set
  `OPENCLAW_SHELL=acp-client`, strip provider auth and active-skill env keys,
  and preserve provider auth for explicit custom ACP servers.
- `acp client` spawn preflight now also mirrors OpenClaw's Windows-safe spawn
  invocation resolver by unwrapping `.cmd` shims to the Python executable with
  `windowsHide=true` and without shell execution.
- Verified the ACP client spawn-plan slice with `python -m pytest
  tests\test_cli.py -q -k "acp_client"` (`5 passed`), adjacent ACP CLI pack
  `python -m pytest tests\test_cli.py -q -k "acp_bridge or acp_client"` (`9
  passed`), `ruff check src\openzues\cli.py
  src\openzues\services\acp_client_runtime.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py src\openzues\services\acp_client_runtime.py`.
- Ops Mesh now applies production-wired global `cron.failureAlert` settings
  for jobs without a per-job alert policy, preserving the same
  threshold/cooldown state update path and leaving per-job overrides plus
  `failureAlert=false` suppression intact.
- Verified the global cron failure-alert slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "global_cron_failure_alert or
  cron_failure_alert_threshold"` (`2 passed`), adjacent Ops Mesh cron/failure
  pack `python -m pytest tests\test_ops_mesh.py -q -k "cron_failure or
  failure_destination or cron_run or scheduled"` (`14 passed`), adjacent
  gateway cron pack `python -m pytest tests\test_gateway_node_methods.py -q -k
  "cron_run or cron_runs or cron_update"` (`23 passed`), `ruff check
  src\openzues\services\ops_mesh.py src\openzues\app.py
  src\openzues\settings.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py src\openzues\app.py
  src\openzues\settings.py`.
- Transient failed one-shot cron jobs now consume production-wired
  `cron.retry` settings: Ops Mesh writes `state.nextRunAtMs` from
  `endedAt + backoff`, keeps retryable one-shot jobs enabled, disables
  permanent/exhausted failures, and both the scheduler and gateway due-run path
  honor the persisted retry timestamp.
- Verified the cron retry/backoff slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "one_shot_retry"` (`1 passed`), adjacent Ops
  Mesh cron pack `python -m pytest tests\test_ops_mesh.py -q -k "one_shot or
  cron_failure or scheduled"` (`18 passed`), adjacent gateway cron pack
  `python -m pytest tests\test_gateway_node_methods.py -q -k "cron_run or
  cron_runs or cron_update or cron_add"` (`46 passed`), adjacent API cron pack
  `python -m pytest tests\test_gateway_nodes_api.py -q -k "cron_run or
  cron_runs or cron_update or cron_add"` (`19 passed`), `ruff check
  src\openzues\services\ops_mesh.py src\openzues\services\gateway_cron.py
  src\openzues\app.py src\openzues\settings.py tests\test_ops_mesh.py`, and
  `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_cron.py src\openzues\app.py
  src\openzues\settings.py`.
- The CLI now exposes `cron status` and `cron list` as thin JSON/human wrappers
  over the production `cron.status` and `cron.list` gateway method owners,
  including upstream `list --all` request shaping and OpenClaw-style schedule,
  status, target, agent, and model row output for human lists.
- Verified the cron CLI status/list slice with `python -m pytest
  tests\test_cli.py -q -k "cron_status_json_calls_gateway_method_owner or
  cron_list_human_output_calls_gateway_method_owner"` (`2 passed`), adjacent
  CLI pack `python -m pytest tests\test_cli.py -q -k "cron_ or sessions_ or
  routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`6 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Provider-specific cron failure-alert result attribution was audited against
  upstream and skipped as a parity seam because OpenClaw's failure-alert owner
  is fire-and-forget.
- `cron runs` now wraps the production `cron.runs` gateway method owner,
  matching the upstream required `--id` plus positive parsed `--limit` request
  shape and emitting JSON/human run-history output.
- Verified the cron runs CLI slice with `python -m pytest tests\test_cli.py -q
  -k "cron_runs_json_calls_gateway_method_owner"` (`1 passed`), adjacent CLI
  pack `python -m pytest tests\test_cli.py -q -k "cron_ or sessions_ or
  routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron run` now wraps the production `cron.run` gateway method owner,
  preserving upstream `--due` request shaping and the CLI exit rule: success
  only when the result is `ok` and either `ran` or `enqueued`.
- Verified the cron run CLI slice with `python -m pytest tests\test_cli.py -q
  -k "cron_run_exits_success_when_gateway_runs_job or
  cron_run_exits_failure_when_gateway_does_not_run_job"` (`2 passed`),
  adjacent CLI pack `python -m pytest tests\test_cli.py -q -k "cron_ or
  sessions_ or routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`9 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron rm`, `cron remove`, `cron delete`, `cron enable`, and `cron disable`
  now wrap the production `cron.remove` and `cron.update` gateway method
  owners with the upstream id/patch request shapes.
- Verified the cron mutation CLI slice with `python -m pytest
  tests\test_cli.py -q -k "cron_rm_json_calls_gateway_method_owner or
  cron_remove_alias_calls_gateway_method_owner or
  cron_enable_disable_call_gateway_update"` (`3 passed`), adjacent CLI pack
  `python -m pytest tests\test_cli.py -q -k "cron_ or sessions_ or
  routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`12 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron add --name --cron --message` now shapes the same core upstream create
  request for isolated agent-turn cron jobs: cron schedule object, inferred
  `sessionTarget="isolated"`, `wakeMode="now"`, agent payload, enabled state,
  and default announce delivery through channel `last`.
- Verified the first cron add CLI slice with `python -m pytest
  tests\test_cli.py -q -k
  "cron_add_isolated_cron_message_json_calls_gateway_method_owner"` (`1
  passed`), adjacent CLI pack `python -m pytest tests\test_cli.py -q -k
  "cron_ or sessions_ or routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`13 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron add` now also covers upstream-supported main-session system-event
  creation with `--every`, `--description`, `--session-key`, `--wake
  next-heartbeat`, and `--disabled`, forwarding only the supported native
  `cron.add` fields.
- Verified the cron add system-event/options slice with `python -m pytest
  tests\test_cli.py -q -k
  "cron_add_main_system_event_every_options_call_gateway_method_owner"` (`1
  passed`), adjacent CLI pack `python -m pytest tests\test_cli.py -q -k
  "cron_ or sessions_ or routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`14 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron create` now aliases `cron add`, and `cron add/create --model` trims
  and forwards the model override into the agent-turn payload using the
  existing native cron method contract.
- Verified the cron create/model CLI slice with `python -m pytest
  tests\test_cli.py -q -k "cron_create_alias_trims_model_for_agent_turn_payload"`
  (`1 passed`), adjacent CLI pack `python -m pytest tests\test_cli.py -q -k
  "cron_ or sessions_ or routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`15 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron add` now preserves upstream delivery flag shaping for native-supported
  fields: `--announce`, `--no-deliver`, `--channel`, `--to`, `--account`, and
  `--best-effort-deliver` map into `delivery.mode`, `channel`, `to`,
  `accountId`, and `bestEffort`.
- Verified the cron add delivery flag slice with `python -m pytest
  tests\test_cli.py -q -k
  "cron_add_announce_delivery_options_call_gateway_method_owner or
  cron_add_no_deliver_sets_delivery_none"` (`2 passed`), adjacent CLI pack
  `python -m pytest tests\test_cli.py -q -k "cron_ or sessions_ or
  routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`17 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron add` now preserves upstream cron-schedule timezone and staggering
  flags for native-supported schedules: `--tz`, `--stagger`, and `--exact`
  populate `schedule.tz` and `schedule.staggerMs` with the same cron-only
  validation rules.
- Verified the cron add schedule breadth slice with `python -m pytest
  tests\test_cli.py -q -k
  "cron_add_cron_timezone_and_stagger_shape_schedule"` (`1 passed`), adjacent
  CLI pack `python -m pytest tests\test_cli.py -q -k "cron_ or sessions_ or
  routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`18 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron edit` now exists for the first supported upstream patch slice:
  `--name`, `--description`, `--enable` / `--disable`, and direct schedule
  changes dispatch to `cron.update` with a patch object.
- Verified the first cron edit CLI slice with `python -m pytest
  tests\test_cli.py -q -k "cron_edit_basic_patch_calls_gateway_method_owner"`
  (`1 passed`), adjacent CLI pack `python -m pytest tests\test_cli.py -q -k
  "cron_ or sessions_ or routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`19 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron edit` now also patches the native-supported upstream session, agent,
  payload, and delivery fields: `--session`, `--session-key`,
  `--clear-session-key`, `--wake`, `--agent`, `--clear-agent`,
  `--message`, `--system-event`, `--model`, `--announce`, `--deliver`,
  `--no-deliver`, `--channel`, `--to`, `--account`,
  `--best-effort-deliver`, and `--no-best-effort-deliver`.
- Verified the cron edit payload/session/delivery slice with `python -m pytest
  tests\test_cli.py -q -k
  "cron_edit_agent_turn_delivery_patch_calls_gateway_method_owner"` (`1
  passed`), adjacent CLI pack `python -m pytest tests\test_cli.py -q -k
  "cron_ or sessions_ or routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`20 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron edit` now patches upstream failure-alert settings through native
  `cron.update`: `--failure-alert`, `--no-failure-alert`,
  `--failure-alert-after`, `--failure-alert-channel`, `--failure-alert-to`,
  `--failure-alert-cooldown`, `--failure-alert-mode`, and
  `--failure-alert-account-id`.
- Verified the cron edit failure-alert slice with `python -m pytest
  tests\test_cli.py -q -k
  "cron_edit_failure_alert_patch_calls_gateway_method_owner"` (`1 passed`),
  adjacent CLI pack `python -m pytest tests\test_cli.py -q -k "cron_ or
  sessions_ or routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`21 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron edit --exact` now follows upstream's existing-cron schedule patch path:
  the CLI reads `cron.list` with disabled jobs included, finds the target job,
  preserves its cron expression/timezone, and sends a merged `cron.update`
  schedule with `staggerMs=0` instead of requiring `--cron`.
- Verified the existing-cron schedule patch slice with `python -m pytest
  tests\test_cli.py -q -k
  "cron_edit_exact_patches_existing_cron_schedule"` (`1 passed`), adjacent CLI
  pack `python -m pytest tests\test_cli.py -q -k "cron_ or sessions_ or
  routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`22 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron.update` now accepts and persists upstream agentTurn payload extras:
  `thinking`, `timeoutSeconds`, `lightContext`, and `toolsAllow`. The native
  task blueprint snapshot projects them back through `job.payload`, with
  `thinking` mapped to the task reasoning field and the remaining extras stored
  as cron payload metadata.
- Verified the backend cron update payload-extras slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "cron_update_patches_agent_turn_payload_extras_like_openclaw"` (`1 passed`),
  adjacent gateway cron pack `python -m pytest tests\test_gateway_node_methods.py
  -q -k "cron_update or cron_add or cron_list or cron_run"` (`48 passed`),
  `ruff check src\openzues\services\gateway_cron.py src\openzues\schemas.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_cron.py src\openzues\schemas.py`.
- `cron.add` now accepts the same upstream agentTurn payload extras
  (`thinking`, `timeoutSeconds`, `lightContext`, and `toolsAllow`) and persists
  them into the native task blueprint payload.
- Verified the backend cron add payload-extras slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "cron_add_accepts_agent_turn_payload_extras_like_openclaw"` (`1 passed`),
  adjacent gateway cron pack `python -m pytest tests\test_gateway_node_methods.py
  -q -k "cron_update or cron_add or cron_list or cron_run"` (`49 passed`),
  `ruff check src\openzues\services\gateway_cron.py src\openzues\schemas.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_cron.py src\openzues\schemas.py`.
- `cron add` now exposes upstream agent payload extra flags: `--thinking`,
  `--timeout-seconds`, `--light-context`, and `--tools`, shaping them into
  `payload.thinking`, `payload.timeoutSeconds`, `payload.lightContext`, and
  `payload.toolsAllow`.
- Verified the cron add payload-extra CLI slice with `python -m pytest
  tests\test_cli.py -q -k
  "cron_add_payload_extra_flags_shape_agent_turn_payload"` (`1 passed`),
  adjacent CLI pack `python -m pytest tests\test_cli.py -q -k "cron_ or
  sessions_ or routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`23 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `cron edit` now exposes the matching payload extra flags and clear forms:
  `--thinking`, `--timeout-seconds`, `--light-context`,
  `--no-light-context`, `--tools`, and `--clear-tools`.
- Verified the cron edit payload-extra CLI slice with `python -m pytest
  tests\test_cli.py -q -k
  "cron_edit_payload_extra_flags_shape_agent_turn_patch"` (`1 passed`),
  adjacent CLI pack `python -m pytest tests\test_cli.py -q -k "cron_ or
  sessions_ or routes_send_json_calls_native_direct_send_runtime or
  routes_poll_human_output_calls_native_direct_poll_runtime"` (`24 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins inspect --json` now carries OpenClaw plugin-record runtime surfaces:
  `commands`, `cliCommands`, `services`, `gatewayMethods`, `httpRouteCount`,
  and `bundleCapabilities` are projected from live inventory or metadata-only
  manifest records instead of being reset to empty report placeholders.
- Verified the plugin inspect runtime-surface slice with `python -m pytest
  tests\test_cli.py -q -k
  "plugins_inspect_json_projects_record_runtime_surfaces"` (`1 passed`),
  adjacent CLI plugin pack `python -m pytest tests\test_cli.py -q -k
  "plugins_"` (`18 passed`), `ruff check src\openzues\cli.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- `cron.add` / `cron.update` now accept and project `deleteAfterRun=true`, and
  successful one-shot system-event `cron.run` dispatch deletes the task
  blueprint when that flag is set.
- Verified the first delete-after-run runtime slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "cron_add_accepts_delete_after_run_true_like_openclaw or
  cron_run_deletes_successful_one_shot_when_delete_after_run_true"` (`2
  passed`), adjacent gateway cron pack `python -m pytest
  tests\test_gateway_node_methods.py -q -k "cron_update or cron_add or
  cron_list or cron_run"` (`51 passed`), `ruff check
  src\openzues\services\gateway_cron.py src\openzues\schemas.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_cron.py src\openzues\schemas.py`.
- OpsMesh mission completion now deletes consumed one-shot task blueprints when
  `cron_delete_after_run` is true, covering isolated agent cron jobs that only
  finish after `cron.run` has enqueued a mission.
- Verified the mission-completion delete-after-run slice with `python -m pytest
  tests\test_ops_mesh.py -q -k
  "deletes_consumed_one_shot_task_when_delete_after_run_true"` (`1 passed`),
  adjacent OpsMesh cron/one-shot pack `python -m pytest tests\test_ops_mesh.py
  -q -k "one_shot or cron_ or failure_alert"` (`22 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Gateway-created one-shot `cron.add` jobs now default `deleteAfterRun` to true
  when the caller does not explicitly set `--keep-after-run` /
  `deleteAfterRun=false`, matching upstream normalized one-shot behavior while
  preserving legacy manually-created local tasks that lack the metadata.
- Verified default one-shot delete-after-run with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "cron_add_defaults_one_shot_delete_after_run_like_openclaw"` (`1 passed`),
  adjacent gateway cron pack `python -m pytest tests\test_gateway_node_methods.py
  -q -k "cron_update or cron_add or cron_list or cron_run"` (`52 passed`),
  `ruff check src\openzues\services\gateway_cron.py src\openzues\schemas.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_cron.py src\openzues\schemas.py`.
- Next cron parity should cover the remaining direct `--at` timezone
  normalization breadth.
- OpsMesh direct/provider poll dispatch now enforces the OpenClaw
  channel-specific option caps before route lookup or native provider posts:
  Telegram and Discord reject more than 10 cleaned options, while the shared
  native-provider guard preserves the 12-option default used by the WhatsApp
  path.
- Verified the runtime poll option-cap slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "rejects_provider_option_caps"` (`2 passed`),
  adjacent native poll pack `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_uses_telegram_native_route or
  send_direct_channel_poll_uses_discord_native_route or
  send_direct_channel_poll_uses_whatsapp_native_route or
  rejects_provider_option_caps or rejects_invalid_telegram_durations"` (`7
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Gateway `poll` and OpsMesh direct/native provider poll dispatch now reject
  `maxSelections` values above the cleaned option count before runtime,
  route lookup, or replay/provider payload dispatch, matching OpenClaw's
  `normalizePollInput` guard.
- Verified the max-selection option-count slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "poll_rejects_max_selections_above_option_count"` (`1 passed`),
  `python -m pytest tests\test_ops_mesh.py -q -k
  "rejects_max_selections_above_options"` (`1 passed`), adjacent gateway poll
  pack `python -m pytest tests\test_gateway_node_methods.py -q -k
  "poll_rejects_max_selections_above_option_count or
  poll_rejects_channel_specific_option_limit_like_openclaw or
  poll_uses_channel_poll_runtime or
  poll_rejects_duration_seconds_for_non_telegram_like_openclaw or
  poll_rejects_telegram_duration"` (`7 passed`), adjacent OpsMesh poll pack
  `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_uses_telegram_native_route or
  send_direct_channel_poll_uses_discord_native_route or
  send_direct_channel_poll_uses_whatsapp_native_route or
  rejects_provider_option_caps or rejects_max_selections_above_options or
  rejects_invalid_telegram_durations"` (`8 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py tests\test_gateway_node_methods.py
  tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py`.
- Gateway `poll` and OpsMesh direct/native provider poll paths now reject
  requests that set both `durationSeconds` and `durationHours`, using the
  OpenClaw `normalizePollInput` mutual-exclusion error before runtime dispatch,
  route lookup, or replay/provider payload construction.
- Verified the duration mutual-exclusion slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "poll_rejects_mutual_duration_fields"` (`1 passed`), `python -m pytest
  tests\test_ops_mesh.py -q -k "rejects_invalid_telegram_durations"` (`3
  passed`), adjacent gateway poll pack `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "poll_rejects_mutual_duration_fields or poll_rejects_telegram_duration or
  poll_rejects_duration_seconds_for_non_telegram_like_openclaw or
  poll_uses_channel_poll_runtime or
  poll_rejects_max_selections_above_option_count"` (`6 passed`), adjacent
  OpsMesh poll pack `python -m pytest tests\test_ops_mesh.py -q -k
  "rejects_invalid_telegram_durations or
  send_direct_channel_poll_uses_telegram_native_route or
  send_direct_channel_poll_uses_discord_native_route or
  send_direct_channel_poll_uses_whatsapp_native_route or
  rejects_max_selections_above_options"` (`7 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py tests\test_gateway_node_methods.py
  tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py`.
- Gateway `poll` and OpsMesh direct/provider poll delivery now trim options and
  drop blank entries before validation, dispatch, persisted delivery payloads,
  and native provider payload construction, matching OpenClaw's
  `normalizePollInput` blank-option filtering.
- Verified the blank option filtering slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k "test_poll_uses_channel_poll_runtime"`
  (`1 passed`), `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_uses_telegram_native_route"` (`1 passed`),
  adjacent gateway poll pack `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "poll_uses_channel_poll_runtime or
  poll_rejects_channel_specific_option_limit_like_openclaw or
  poll_rejects_max_selections_above_option_count or
  poll_rejects_mutual_duration_fields or
  poll_returns_validated_unavailable_contract"` (`6 passed`), adjacent OpsMesh
  poll pack `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_uses_telegram_native_route or
  send_direct_channel_poll_uses_discord_native_route or
  send_direct_channel_poll_uses_whatsapp_native_route or
  rejects_provider_option_caps or rejects_max_selections_above_options or
  rejects_invalid_telegram_durations"` (`9 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py tests\test_gateway_node_methods.py
  tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py`.
- Gateway `poll`, OpsMesh direct/provider poll delivery, and the shared
  outbound runtime now normalize omitted `maxSelections` to `1` before runtime
  dispatch, persisted delivery payloads, and native/provider request
  construction, matching OpenClaw's `normalizePollInput` default.
- Verified the omitted max-selection default slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k "test_poll_uses_channel_poll_runtime"`
  (`1 passed`), `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_uses_gateway_route_adapter or
  gateway_outbound_runtime_poll_defaults_max_selections_to_one"` (`2 passed`),
  adjacent gateway poll pack `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "poll_uses_channel_poll_runtime or
  poll_rejects_channel_specific_option_limit_like_openclaw or
  poll_rejects_max_selections_above_option_count or
  poll_rejects_mutual_duration_fields or
  poll_returns_validated_unavailable_contract"` (`6 passed`), adjacent OpsMesh
  poll pack `python -m pytest tests\test_ops_mesh.py -q -k
  "gateway_outbound_runtime_poll_defaults_max_selections_to_one or
  send_direct_channel_poll_uses_gateway_route_adapter or
  send_direct_channel_poll_uses_telegram_native_route or
  send_direct_channel_poll_uses_discord_native_route or
  send_direct_channel_poll_uses_whatsapp_native_route or
  send_direct_channel_poll_uses_native_adapter_binding or
  rejects_provider_option_caps or rejects_max_selections_above_options"` (`9
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py
  tests\test_gateway_node_methods.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- OpsMesh direct/provider poll delivery now applies the remaining OpenClaw
  `normalizePollInput` shape guards for empty questions and fewer than two
  cleaned options before provider lookup, persisted delivery creation, route
  backed runtime posting, or native provider payload construction.
- Verified the OpsMesh poll shape guard slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "rejects_invalid_poll_shape"` (`2 passed`),
  adjacent provider poll pack `python -m pytest tests\test_ops_mesh.py -q -k
  "rejects_invalid_poll_shape or
  send_direct_channel_poll_uses_telegram_native_route or
  send_direct_channel_poll_uses_discord_native_route or
  send_direct_channel_poll_uses_whatsapp_native_route or
  send_direct_channel_poll_uses_gateway_route_adapter or
  gateway_outbound_runtime_poll_defaults_max_selections_to_one or
  rejects_provider_option_caps or rejects_max_selections_above_options or
  rejects_invalid_telegram_durations"` (`13 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- `agents.files.list` now mirrors OpenClaw's memory-file projection by showing
  `MEMORY.md` when the primary memory file exists, falling back to legacy
  `memory.md` only when the primary file is absent, instead of advertising both
  files when both are present.
- Verified the agent files primary-memory slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "agents_files_list_prefers_primary_memory_file_like_openclaw"` (`1 passed`),
  adjacent agent-files pack `python -m pytest tests\test_gateway_node_methods.py
  -q -k
  "agents_files_list_includes_openclaw_bootstrap_and_memory_files or
  agents_files_list_returns_bounded_workspace_instruction_inventory or
  agents_files_get_and_set_support_openclaw_memory_file"` (`3 passed`), `ruff
  check src\openzues\services\gateway_agent_files.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_agent_files.py`.
- `sessions.spawn runtime="acp"` now mirrors OpenClaw's requester sandbox
  policy guard: sandboxed requester sessions are rejected before ACP target
  resolution or runtime dispatch because ACP runs on the host, while the
  existing explicit `sandbox="require"` ACP error remains unchanged.
- Verified the ACP sandboxed-requester guard with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_rejects_sandboxed_requester_to_acp_runtime"` (`1 passed`),
  adjacent ACP spawn policy/runtime pack `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_rejects_acp_required_sandbox_policy or
  sessions_spawn_rejects_sandboxed_requester_to_acp_runtime or
  sessions_spawn_rejects_light_context_for_acp_before_runtime_boundary or
  sessions_spawn_rejects_acp_attachments_before_runtime_boundary or
  sessions_spawn_acp_requires_target_agent_without_default or
  sessions_spawn_acp_rejects_agent_outside_acp_allowlist or
  sessions_spawn_acp_runtime_tracks_wait_cleanup_and_completion or
  sessions_spawn_acp_stream_to_parent_tracks_child_run"` (`8 passed`), `ruff
  check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- `tools.invoke` plugin executor visibility now follows OpenClaw's scoped tool
  policy split: `gateway.tools.allow` still only relaxes the HTTP default-deny
  set for high-risk core tools, while non-core plugin executors can be exposed
  by the invoking agent's `tools.allow` policy. The config schema now preserves
  agent-level and top-level OpenClaw-style `tools.allow` / `tools.deny` blocks.
- Verified the scoped plugin executor slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "tools_invoke_runs_plugin_executor_from_agent_tool_allowlist"` (`1 passed`),
  adjacent `tools.invoke` plugin pack (`12 passed`), config smoke
  `python -m pytest tests\test_gateway_node_methods.py -q -k
  "config_get or config_set or config_patch or config_apply"` (`2 passed`),
  `ruff check src\openzues\services\gateway_node_methods.py
  src\openzues\schemas.py tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py`.
- `doctor --json` now mirrors OpenClaw's sandbox shared-scope warning for
  ignored per-agent sandbox overrides: when an agent-level `docker`, `browser`,
  or `prune` block resolves to `scope="shared"`, the doctor warnings list
  includes the upstream-shaped `agents.list (id "...") sandbox ... overrides
  ignored` note.
- Verified the doctor sandbox scope warning with `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_warns_about_shared_sandbox_agent_overrides"` (`1 passed`),
  adjacent doctor sandbox/lock pack `python -m pytest tests\test_cli.py -q -k
  "doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_warns_about_shared_sandbox_agent_overrides or
  doctor_human_output_reports_session_lock_files or
  doctor_json_includes_cli_runtime_surfaces"` (`3 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Sandboxed requester sessions now clamp `tools.invoke` session access to
  tree/spawned visibility when sandbox config leaves
  `sessionToolsVisibility` at the OpenClaw default `spawned`, even if
  `tools.sessions.visibility=all` would otherwise allow cross-agent access.
  Setting `agents.defaults.sandbox.sessionToolsVisibility="all"` preserves the
  broader visibility.
- Verified the sandboxed session-tools clamp with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_history_clamps_sandboxed_requester_to_tree_visibility or
  sessions_history_allows_sandboxed_requester_when_visibility_all"` (`2
  passed`), adjacent sessions visibility pack `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_history or session_status or sessions_list_filters_default_tree or
  sessions_send_default_tree or sessions_send_enforces_self_visibility"` (`21
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- `status --json` now always emits OpenClaw-shaped `gatewayService` and
  `nodeService` summaries for the native OpenZues runtime, with honest
  unmanaged status instead of dropping those top-level fields.
- Verified the CLI status managed-service summary seam with `python -m pytest
  tests\test_cli.py::test_status_json_includes_managed_service_summaries -q`
  (`1 passed`), adjacent status JSON/all coverage `python -m pytest
  tests\test_cli.py -q -k
  "status_json_includes_managed_service_summaries or
  status_json_breadth_flags_add_runtime_sections_with_timeout or
  status_json_uses_registered_usage_and_security_runtime_adapters or
  status_all_human_output_renders_pasteable_diagnosis"` (`4 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `doctor --json` and human doctor output now include stable OpenClaw doctor
  contribution surfaces for `doctor:security` and `doctor:shell-completion`.
  The native CLI returns a structured security read model and keeps shell
  completion as partial until production repair adapters are wired, while
  preserving any future real adapter payloads.
- Verified the doctor contribution-surface seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_security_and_shell_completion_surfaces -q`
  (`1 passed`), adjacent doctor coverage `python -m pytest tests\test_cli.py
  -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_warns_about_shared_sandbox_agent_overrides or
  doctor_human_output_reports_session_lock_files or
  doctor_json_includes_cli_runtime_surfaces"` (`4 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- The `doctor:security` contribution now implements OpenClaw's
  `approvals.exec.enabled=false` warning: doctor JSON reports that approval
  forwarding is disabled only for forwarding, points at the host
  `~/.openclaw/exec-approvals.json` policy, and suggests
  `openclaw approvals get --gateway`, while failing soft if legacy config must
  be reported by the earlier migrator first.
- Verified the security forwarding warning with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_approvals_exec_forwarding_is_disabled
  -q` (`1 passed`), adjacent security/shell/legacy proof `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_thread_binding_ttl_hours
  tests\test_cli.py::test_doctor_json_warns_when_approvals_exec_forwarding_is_disabled
  tests\test_cli.py::test_doctor_json_includes_security_and_shell_completion_surfaces
  -q` (`3 passed`), broader doctor proof `python -m pytest tests\test_cli.py
  -q -k "approvals_exec_forwarding or security_and_shell_completion_surfaces
  or doctor_json_warns or gateway_auth or gateway_mode_is_unset"` (`37
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `doctor:security` now also mirrors OpenClaw's implicit heartbeat
  direct-policy upgrade warning for configured default or per-agent heartbeat
  delivery whose `directPolicy` is unset, including the upstream
  `allow`/`block` pinning guidance.
- Verified the heartbeat direct-policy security slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_heartbeat_direct_policy_is_implicit
  -q` (`1 passed`), adjacent security/doctor proof `python -m pytest
  tests\test_cli.py -q -k "heartbeat_direct_policy or approvals_exec_forwarding
  or security_and_shell_completion_surfaces or doctor_json_warns or gateway_auth
  or gateway_mode_is_unset"` (`38 passed`), `ruff check src\openzues\cli.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- `doctor:security` now mirrors OpenClaw's gateway network-exposure warning
  for canonical non-loopback binds without configured auth, including the
  CRITICAL control warning, loopback fix, SSH tunnel guidance, remote docs link,
  and token-generation hints while leaving legacy raw bind aliases under the
  legacy-config migrator.
- Verified the gateway exposure security slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_when_gateway_bind_is_exposed_without_auth
  -q` (`1 passed`), legacy ownership proof `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_gateway_bind_host_alias
  tests\test_cli.py::test_doctor_json_warns_when_gateway_bind_is_exposed_without_auth
  -q` (`2 passed`), broader security/doctor proof `python -m pytest
  tests\test_cli.py -q -k "gateway_bind_is_exposed or heartbeat_direct_policy
  or approvals_exec_forwarding or security_and_shell_completion_surfaces or
  doctor_json_warns or gateway_auth or gateway_mode_is_unset"` (`39 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `doctor:security` now mirrors OpenClaw's `tools.exec` host-policy conflict
  warning. The native doctor reads the existing
  `settings/exec-approvals.json` runtime policy, compares global and per-agent
  requested `security`/`ask` values against the stricter host effective policy,
  reports the OpenClaw-shaped config/host/effective lines, and preserves
  `tools.exec` config through the native config snapshot schema.
- Verified the exec-policy security slice with `python -m pytest
  tests\test_cli.py -k "exec_policy_config_exceeds_host_policy or
  gateway_config_preserves_exec_policy_config_for_security_doctor"` (`2
  passed`) and adjacent security/doctor proof `python -m pytest
  tests\test_cli.py -k "doctor_json_warns_when_approvals_exec_forwarding_is_disabled
  or doctor_json_warns_when_heartbeat_direct_policy_is_implicit or
  doctor_json_warns_when_gateway_bind_is_exposed_without_auth or
  exec_policy_config_exceeds_host_policy or
  gateway_config_preserves_exec_policy_config_for_security_doctor or
  doctor_json_includes_security_and_shell_completion_surfaces or
  legacy_gateway_bind_host_alias or legacy_thread_binding_ttl_hours"` (`10
  passed`).
- `doctor:security` now mirrors OpenClaw's configured channel DM policy
  warnings. The native doctor reads enabled/configured channel snapshots,
  resolves the default account, preserves top-level and nested `dmPolicy` /
  `allowFrom` paths, consults the pairing allowFrom store, and reports OPEN,
  invalid-open, locked, disabled, and shared-main-session warnings with
  OpenClaw-shaped pairing and `session.dmScope` guidance.
- Verified the DM-policy security slice with `python -m pytest
  tests\test_cli.py -k "channel_dm_policy_security"` (`1 passed`), adjacent
  security/allowFrom proof `python -m pytest tests\test_cli.py -k
  "channel_dm_policy_security or exec_policy_config_exceeds_host_policy or
  gateway_config_preserves_exec_policy_config_for_security_doctor or
  doctor_json_warns_when_approvals_exec_forwarding_is_disabled or
  doctor_json_warns_when_heartbeat_direct_policy_is_implicit or
  doctor_json_warns_when_gateway_bind_is_exposed_without_auth or
  doctor_json_includes_security_and_shell_completion_surfaces or
  open_policy_allow_from or allowlist_policy_allow_from"` (`10 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `doctor:shell-completion` now has a native OpenClaw-shaped status and repair
  path for existing profile installations. The doctor detects the current
  shell, profile path, cache path, cache presence, and slow dynamic
  `openzues completion` profile lines; `doctor --fix` regenerates the local
  Typer completion cache and rewrites slow profile stanzas to source the cached
  file.
- Verified the shell-completion status/repair slice with `python -m pytest
  tests\test_cli.py -k "shell_completion_uses_slow_dynamic_profile or
  regenerates_shell_completion_cache"` (`2 passed`), adjacent doctor proof
  `python -m pytest tests\test_cli.py -k "shell_completion_uses_slow_dynamic_profile
  or regenerates_shell_completion_cache or security_and_shell_completion_surfaces
  or channel_dm_policy_security or exec_policy_config_exceeds_host_policy or
  doctor_json_warns_when_approvals_exec_forwarding_is_disabled or
  doctor_json_warns_when_heartbeat_direct_policy_is_implicit or
  doctor_json_warns_when_gateway_bind_is_exposed_without_auth or
  open_policy_allow_from or allowlist_policy_allow_from"` (`11 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `doctor:shell-completion --fix` now also covers first-time native
  installation when no profile completion exists. The doctor generates the
  cache, creates the shell profile if needed, writes an `# OpenZues Completion`
  cached-source stanza, and returns the recomputed healthy status.
- Verified the first-time completion install slice with `python -m pytest
  tests\test_cli.py -k "installs_shell_completion_when_profile_is_missing"`
  (`1 passed`), adjacent shell/doctor proof `python -m pytest
  tests\test_cli.py -k "shell_completion_uses_slow_dynamic_profile or
  regenerates_shell_completion_cache or installs_shell_completion_when_profile_is_missing
  or security_and_shell_completion_surfaces or channel_dm_policy_security or
  exec_policy_config_exceeds_host_policy or
  doctor_json_warns_when_approvals_exec_forwarding_is_disabled or
  doctor_json_warns_when_heartbeat_direct_policy_is_implicit or
  doctor_json_warns_when_gateway_bind_is_exposed_without_auth or
  open_policy_allow_from or allowlist_policy_allow_from"` (`12 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Provider-backed `gateway.send` now mirrors OpenClaw's explicit `sessionKey`
  behavior: OpenZues canonicalizes `sourceSessionKey`, passes it into the
  outbound runtime/mirror session, and keeps the delivery history row on the
  channel-derived target session so saved history and replay remain anchored to
  the external target.
- Verified the direct-send source-session seam with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_mirrors_explicit_session_key -q`
  (`1 passed`), adjacent direct-send runtime/idempotency/provider coverage
  `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_message_mirrors_explicit_session_key or
  send_direct_channel_message_uses_shared_outbound_runtime_owner or
  send_direct_channel_message_prefers_provider_runtime or
  send_direct_channel_message_uses_gateway_route_adapter or
  send_direct_channel_message_dedupes_inflight_idempotent_retries or
  send_direct_channel_message_uses_known_channel_default_account"` (`6
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- `sessions.patch` and `sessions.delete` now reject non-control webchat
  clients before storage mutation, matching OpenClaw's `use chat.send for
  session-scoped updates` policy boundary while allowing the control UI client
  ids to continue managing sessions.
- Verified the webchat session-mutation guard with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_mutations_reject_webchat_clients -q`
  (`2 passed`), adjacent sessions mutation coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_mutations_reject_webchat_clients or sessions_delete or
  sessions_patch"` (`22 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- `chat.inject` now records the current control-chat leaf as `parentId`
  metadata on injected assistant rows and projects that linkage through
  `chat.history` plus live/session message payloads, matching OpenClaw's
  SessionManager append behavior instead of creating orphan transcript entries.
- Verified the injected-chat parent-link seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_chat_inject_records_parent_id_from_current_transcript_leaf -q`
  (`1 passed`), adjacent transcript coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "chat_inject or chat_history"`
  (`17 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_sessions.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_sessions.py`.
- Cron failure announce deliveries now carry OpenClaw-style stable direct
  delivery idempotency keys, so replaying the same failed cron execution
  reuses the saved delivered row instead of sending a second channel announce;
  distinct runs still have separate runtime keys through the cron execution
  timestamp.
- Verified the cron direct-announce replay seam with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_dedupes_replayed_cron_failure_announce_delivery -q`
  (`1 passed`), adjacent cron/direct replay coverage `python -m pytest
  tests\test_ops_mesh.py -q -k
  "explicit_cron_failure_to_announce or replayed_cron_failure_announce or
  send_direct_channel_message_dedupes_inflight_idempotent_retries or
  replay_outbound_deliveries_retries_saved_failed_announce_delivery"` (`6
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- `chat.send` attachment dispatch now computes OpenClaw-style `imageOrder`
  for mixed inline/offloaded image attachments at the 2 MB decoded-size
  boundary and persists that ordering metadata on app-wired control-chat user
  turns, preserving the original attachment order for downstream native
  runtimes.
- Verified the mixed attachment ordering seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_chat_send_passes_image_order_for_mixed_inline_and_offloaded_attachments
  tests\test_gateway_nodes_api.py::test_gateway_node_method_call_endpoint_preserves_chat_send_attachment_image_order -q`
  (`2 passed`), adjacent attachment coverage `python -m pytest
  tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k
  "chat_send and attachment"` (`15 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\control_chat.py src\openzues\app.py
  tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and
  `mypy src\openzues\services\gateway_node_methods.py
  src\openzues\services\control_chat.py src\openzues\app.py`.
- `doctor --json` now includes the OpenClaw `doctor:gateway-health`
  contribution: it runs the bounded native health probe, calls
  `channels.status` with provider probes when health is up, and projects
  route-backed channel account probe failures into structured channel warnings
  while preserving unsupported provider hooks as non-degraded.
- Verified the gateway-health doctor seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_gateway_health_contribution_and_channel_warnings -q`
  (`1 passed`), adjacent doctor/channel coverage `python -m pytest
  tests\test_cli.py -q -k "doctor_json_includes_gateway_health_contribution or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution or
  startup_channel_maintenance or
  channels_status_json_calls_gateway_method_owner_with_probe"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Provider-native direct send/poll now carries OpenClaw-style
  `gatewayClientScopes` through the public OpsMesh direct delivery surface, the
  saved delivery payload, generic/native provider runtime requests, and
  route-backed provider event payloads, including explicit empty scope arrays.
- Verified the provider scope seam with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_prefers_provider_runtime
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_poll_prefers_provider_runtime -q`
  (`2 passed`), adjacent provider runtime coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "send_direct_channel_message_prefers_provider_runtime
  or send_direct_channel_poll_prefers_provider_runtime or
  gateway_outbound_runtime_poll_defaults_max_selections_to_one or
  send_direct_channel_message_uses_native_adapter_binding or
  send_direct_channel_poll_uses_native_adapter_binding or
  send_direct_channel_message_uses_gateway_route_adapter or
  send_direct_channel_message_preserves_provider_native_options"` (`7 passed`),
  `ruff check src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py`.
- Provider-native direct send now carries requester context separately from
  the runtime delivery session: `requesterSessionKey`, `requesterAccountId`,
  `requesterSenderId`, and sender display fields flow into provider runtime
  requests, route-backed provider event payloads, and saved delivery payloads
  while `sessionKey` remains the delivery/runtime session.
- Verified the requester-context seam with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_forwards_requester_context -q`
  (`1 passed`), adjacent provider send coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "requester_context or
  send_direct_channel_message_mirrors_explicit_session_key or
  send_direct_channel_message_prefers_provider_runtime or
  send_direct_channel_message_preserves_provider_native_options or
  send_direct_channel_message_uses_native_adapter_binding"` (`5 passed`),
  `ruff check src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py`.
- Provider-native direct media sends now preserve OpenClaw's `audioAsVoice`
  hint from gateway `send` through `OpsMeshService`, saved outbound payloads,
  `GatewayOutboundRuntimeMessageRequest`, route-backed provider events, and
  saved failed-send replay formatting. Source anchor:
  `C:\Users\skull\OneDrive\Documents\openclaw-main\src\infra\outbound\deliver.test.ts`
  and `payloads.ts`.
- Verified the audio-as-voice send seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_send_preserves_audio_as_voice_for_media_payloads
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_preserves_audio_as_voice -q`
  (`2 passed`), adjacent provider replay/send coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "send_direct_channel_message_preserves_provider_native_options
  or send_direct_channel_message_preserves_audio_as_voice or
  replay_outbound_deliveries_retries_saved_failed_gateway_send_via_provider_runtime"`
  (`3 passed`), gateway send coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "test_send_"` (`17 passed`),
  OpsMesh direct-send coverage `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_message"` (`27 passed`), `ruff check
  src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_node_methods.py tests\test_ops_mesh.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_node_methods.py`.
- Provider-native Slack direct send now mirrors OpenClaw's
  `extensions/slack/src/thread-ts.ts` thread resolution: `replyToId` is used
  only when it is a Slack timestamp string, otherwise a valid `threadId`
  supplies `thread_ts`, and internal message ids are never posted as Slack
  thread timestamps. This slice is checkpointed in `a461e5eb`.
- Verified the Slack thread timestamp slice with focused Slack native route
  tests (`2 passed`), adjacent `python -m pytest tests\test_ops_mesh.py -q -k
  "slack_native_route or direct_channel_message_uses_slack or
  slack_reply_to_thread"` (`5 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Provider-native Slack media sends now mirror OpenClaw's outbound payload
  media contract: `mediaUrls` are uploaded one at a time, only the first upload
  receives the text caption, Slack media captions use the raw payload text
  instead of the generic `Media:` fallback body, and the final media id becomes
  the canonical `messageId` while all media ids remain in `mediaIds`. This
  slice is checkpointed in `e3b5bbc0`.
- Verified the Slack multi-media slice with focused Slack media route tests (`2
  passed`), adjacent `python -m pytest tests\test_ops_mesh.py -q -k
  "slack_native_route or slack_media or direct_channel_message_uses_slack"` (`7
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Gateway `send` now runs the bounded OpenClaw outbound payload directive
  normalization for message-body `[[reply_to:...]]`, `[[reply_to_current]]`,
  `[[audio_as_voice]]`, and line-start `MEDIA:` entries before channel
  delivery, matching the upstream `createOutboundPayloadPlan` path in
  `C:\Users\skull\OneDrive\Documents\openclaw-main\src\gateway\server-methods\send.ts`
  and `infra\outbound\payloads.ts`.
- Verified the inline send-directive seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_send_parses_inline_reply_audio_and_media_directives -q`
  (`1 passed`), adjacent gateway send coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "test_send_"` (`18 passed`),
  adjacent OpsMesh direct-send coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "send_direct_channel_message"` (`27 passed`),
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- WhatsApp multi-media sends now report the final provider message id as the
  canonical `messageId` while preserving the full ordered `mediaIds` list,
  matching OpenClaw's outbound payload contract for iterated media sends.
- Verified the WhatsApp media result seam with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_splits_whatsapp_media -q`
  (`1 passed`), adjacent WhatsApp send coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "whatsapp_media or whatsapp_document_reply or
  whatsapp_gif or whatsapp_text or
  send_direct_channel_message_splits_whatsapp_media"` (`2 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack native media upload now passes the raw resolved route token into the
  upload helper and leaves `Authorization: Bearer ...` formatting to the Slack
  form poster, matching OpenClaw's WebClient-style raw-token upload flow and
  avoiding `Bearer Bearer ...` headers.
- Verified the Slack media auth seam with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_slack_native_route -q`
  (`1 passed`), adjacent Slack route/action coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "slack_native_route or slack_reply_to or
  slack_media_download or send_direct_channel_message_uses_slack_native_route
  or message_action_dispatches_slack"` (`9 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Telegram route-backed native multi-media sends now match OpenClaw's
  sequential media delivery contract: each media URL is sent individually,
  the caption rides on the first send, the final send's message id is the
  canonical `messageId`, and returned `mediaIds` stay ordered. Forced
  document sends also pass Telegram's `disable_content_type_detection` flag.
- Verified the Telegram media/force-document seam with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_telegram_native_options
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_telegram_media_group
  -q` (`2 passed`), adjacent Telegram coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_native_route or telegram_native_options
  or telegram_topic or telegram_media_group or invalid_telegram_durations"`
  (`10 passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Thread-bound `sessions.spawn` now mirrors OpenClaw's startup-failure cleanup
  path after a binding has been prepared: the fakeable
  `GatewaySubagentThreadBinder` protocol exposes `unbind`, route-backed
  stateless binders report a no-op cleanup result, and runtime startup failures
  invoke best-effort binding cleanup before deleting the provisional child
  session metadata/transcript while preserving the original spawn error.
- Verified the bound-thread failure cleanup seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_thread_mode_cleans_up_binding_when_runtime_start_fails -q`
  (`1 passed`), adjacent thread-bound coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_spawn_thread_mode"`
  (`6 passed`), route-binder coverage `python -m pytest
  tests\test_gateway_thread_binding.py -q` (`3 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_thread_binding.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_thread_binding.py`.
- RuntimeManager-backed ACP `thread=true` spawns now enforce OpenClaw's
  provider-context preflight: persistent thread-bound ACP sessions require a
  requester channel context and return `errorCode="thread_binding_invalid"`
  without starting a RuntimeManager thread/turn when that context is missing.
  Existing session-mode RuntimeManager tests now provide explicit requester
  route context when exercising accepted persistent ACP sessions.
- Verified the ACP channel-context guard with `python -m pytest
  tests\test_gateway_acp_spawn.py::test_runtime_manager_acp_spawn_rejects_thread_session_without_channel_context -q`
  (`1 passed`), adjacent ACP runtime coverage `python -m pytest
  tests\test_gateway_acp_spawn.py -q` (`9 passed`), node-method ACP coverage
  `python -m pytest tests\test_gateway_node_methods.py -q -k "acp_runtime or
  acp_stream or acp_default or acp_runtime_tracks_wait_cleanup_and_completion"`
  (`5 passed`), `ruff check src\openzues\services\gateway_acp_spawn.py
  tests\test_gateway_acp_spawn.py`, and `mypy
  src\openzues\services\gateway_acp_spawn.py`.
- Gateway-level ACP `thread=true` spawns now honor OpenClaw's explicit channel
  spawn policy before runtime dispatch: when
  `channels.<channel>.threadBindings.spawnAcpSessions=false`, `sessions.spawn`
  returns `errorCode="thread_binding_invalid"` and the native ACP spawn service
  is not called.
- Verified the ACP channel spawn-policy seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_thread_mode_honors_channel_spawn_policy -q`
  (`1 passed`), adjacent ACP gateway coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_spawn_acp"` (`6 passed`),
  ACP adapter coverage `python -m pytest tests\test_gateway_acp_spawn.py -q`
  (`9 passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py src\openzues\services\gateway_acp_spawn.py
  tests\test_gateway_acp_spawn.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_acp_spawn.py`.
- Gateway-level subagent `thread=true` spawns now honor OpenClaw's explicit
  channel spawn policy before route binding or child dispatch: when
  `channels.<channel>.threadBindings.spawnSubagentSessions=false`,
  `sessions.spawn` returns the upstream-shaped policy error and the native
  thread binder/runtime path is not called.
- Verified the subagent channel spawn-policy seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_thread_mode_honors_channel_spawn_policy -q`
  (`1 passed`), adjacent gateway coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_spawn_thread_mode or
  sessions_spawn_acp"` (`13 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py`.
- Gateway ACP and subagent `thread=true` spawn policy now also mirrors
  OpenClaw's child-placement default from channel plugins: Discord and Matrix
  require explicit `spawnAcpSessions=true` / `spawnSubagentSessions=true` when
  the spawn flag is unset, so top-level child-thread creation does not silently
  run on channels whose upstream placement policy requires an opt-in.
- Verified the child-placement spawn-policy seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_thread_mode_requires_spawn_policy_for_child_placement -q`
  (`1 passed`), `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_thread_mode_requires_spawn_policy_for_child_placement -q`
  (`1 passed`), adjacent gateway coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_spawn_thread_mode or
  sessions_spawn_acp"` (`15 passed`), ACP adapter coverage `python -m pytest
  tests\test_gateway_acp_spawn.py -q` (`9 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py`.
- Matrix existing-thread route contexts are now first-class thread-bound
  subagent targets: notification routes admit `kind="matrix"`, requester
  route normalization preserves Matrix channel context, and the route-backed
  binder accepts Matrix routes so `sessions.spawn thread=true` can persist
  Matrix thread binding/completion delivery metadata after the explicit
  `spawnSubagentSessions=true` opt-in required by child-placement policy.
- Verified the Matrix route-backed thread-binding seam with `python -m pytest
  tests\test_gateway_thread_binding.py::test_thread_binder_registry_resolves_matrix_provider_thread -q`
  (`1 passed`), `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_thread_mode_uses_matrix_route_backed_thread_binder -q`
  (`1 passed`), adjacent coverage `python -m pytest
  tests\test_gateway_thread_binding.py -q` (`4 passed`) and `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_spawn_thread_mode"` (`9
  passed`), `ruff check src\openzues\services\gateway_thread_binding.py
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py
  tests\test_gateway_thread_binding.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_thread_binding.py
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py`.
- Telegram native poll route sends now mirror OpenClaw's Bot API
  multi-select payload flag: `maxSelections > 1` sends
  `allows_multiple_answers=true`, default single-choice sends `false`, and the
  existing anonymous, duration, silent, result metadata, and topic-thread
  behavior remains intact.
- Verified the Telegram poll multi-select seam with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_poll_uses_telegram_native_route -q`
  (`1 passed`), topic/default coverage `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_poll_parses_telegram_topic_target -q`
  (`1 passed`), adjacent provider coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_native_route or telegram_topic or
  invalid_telegram_durations or poll_rejects_max_selections or
  provider_option_caps"` (`11 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Provider-native poll delivery now preserves OpenClaw-style reply context:
  gateway `poll` accepts `replyToId` / `replyToMessageId`, OpsMesh persists
  and replays the field, shared outbound runtime poll requests carry
  `reply_to_id`, CLI `routes poll --reply-to` forwards it, and Telegram native
  poll sends emit Bot API `reply_to_message_id`.
- Verified the poll reply-context seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_poll_uses_channel_poll_runtime -q`
  (`1 passed`), `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_poll_prefers_provider_runtime -q`
  (`1 passed`), `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_poll_uses_telegram_native_route -q`
  (`1 passed`), `python -m pytest
  tests\test_cli.py::test_routes_poll_human_output_calls_native_direct_poll_runtime -q`
  (`1 passed`), adjacent gateway coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "poll_uses_channel_poll_runtime or
  poll_allows_thread_id or poll_rejects"` (`14 passed`), adjacent OpsMesh
  coverage `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_prefers_provider_runtime or telegram_native_route
  or telegram_topic or replay_outbound_deliveries_retries_saved_failed_gateway_poll_via_provider_runtime"`
  (`7 passed`), `ruff check src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py src\openzues\cli.py
  tests\test_gateway_node_methods.py tests\test_ops_mesh.py tests\test_cli.py`,
  and `mypy src\openzues\services\gateway_node_methods.py
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py src\openzues\cli.py`.
- `/tools/invoke` plugin executor specs now preserve runtime `parameters`
  schema metadata, and top-level `action` is merged into plugin args only when
  that schema declares `properties.action`; explicit `args.action` wins, and
  schemas without `action` continue to receive the original args.
- Verified the plugin action-merge seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_tools_invoke_merges_top_level_action_for_plugin_schema
  -q` (`1 passed`), `python -m pytest
  tests\test_gateway_node_methods.py::test_tools_invoke_keeps_explicit_plugin_args_action
  -q` (`1 passed`), `python -m pytest
  tests\test_gateway_node_methods.py::test_tools_invoke_does_not_merge_top_level_action_without_plugin_schema
  -q` (`1 passed`), adjacent plugin coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "tools_invoke and plugin"` (`13
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_plugin_runtime.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py
  src\openzues\services\gateway_plugin_runtime.py`.
- Native config writes now preserve OpenClaw's canonical
  `session.threadBindings.enabled`, `idleHours`, and `maxAgeHours` keys and
  reject legacy `threadBindings.ttlHours` at the session, channel, and
  channel-account paths before snapshot validation.
- Verified the thread-binding config-key seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_config_set_rejects_legacy_thread_binding_ttl_hours
  tests\test_gateway_node_methods.py::test_config_set_preserves_session_thread_binding_idle_hours
  -q` (`4 passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "config_write_methods or
  config_patch_noop or config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or
  config_get_returns_control_ui_bootstrap_snapshot or config_open_file"` (`14
  passed`), adjacent thread-binding spawn policy coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_acp_thread_mode_honors_channel_spawn_policy or
  sessions_spawn_thread_mode_honors_channel_spawn_policy or
  sessions_spawn_thread_mode_rejects_omitted_spawn_policy_for_child_placement_channel
  or
  sessions_spawn_acp_thread_mode_rejects_omitted_spawn_policy_for_child_placement_channel"`
  (`2 passed`), adjacent doctor coverage `python -m pytest tests\test_cli.py
  -q -k "doctor_json_includes_sandbox_contribution or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_warns_about_shared_sandbox_agent_overrides or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`4
  passed`), `ruff check src\openzues\services\gateway_config.py
  src\openzues\schemas.py tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- `doctor --json` now includes a native OpenClaw-shaped `legacyConfig`
  contribution for persisted `threadBindings.ttlHours` config keys, warning
  operators to run `openzues doctor --fix`; repair mode rewrites session,
  channel, and channel-account `ttlHours` to `idleHours` before the rest of
  doctor reads the validated config snapshot.
- Verified the legacy thread-binding doctor repair seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_thread_binding_ttl_hours
  tests\test_cli.py::test_doctor_fix_migrates_legacy_thread_binding_ttl_hours
  -q` (`2 passed`), adjacent doctor coverage `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_warns_about_legacy_thread_binding_ttl_hours or
  doctor_fix_migrates_legacy_thread_binding_ttl_hours or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_sandbox_contribution or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_warns_about_shared_sandbox_agent_overrides or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`8
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop"` (`9 passed`), adjacent doctor contribution coverage
  `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- The native `legacyConfig` doctor contribution now also covers OpenClaw's
  nested channel allow-alias migration: Slack channel entries, Slack account
  channel entries, Google Chat groups, and Discord guild channels warn in
  `doctor --json` and rewrite `allow` to `enabled` in `doctor --fix`, preserving
  existing `enabled` values when both keys are present.
- Verified the channel allow-alias migration seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_channel_allow_aliases
  tests\test_cli.py::test_doctor_fix_migrates_legacy_channel_allow_aliases -q`
  (`2 passed`), regression coverage for the previous thread-binding legacy
  doctor seam `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_thread_binding_ttl_hours
  tests\test_cli.py::test_doctor_fix_migrates_legacy_thread_binding_ttl_hours
  -q` (`2 passed`), adjacent doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or doctor_fix_runs_startup_channel_maintenance_adapter
  or doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_sandbox_contribution or
  doctor_json_warns_when_sandbox_enabled_without_docker or
  doctor_json_warns_about_shared_sandbox_agent_overrides or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`10
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop"` (`9 passed`), `ruff check src\openzues\cli.py
  src\openzues\services\gateway_config.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py src\openzues\services\gateway_config.py`.
- The native `legacyConfig` doctor contribution now migrates the OpenClaw
  `tools.web.x_search.apiKey` legacy provider auth key into
  `plugins.entries.xai.config.webSearch.apiKey`, preserving non-auth
  `tools.web.x_search` knobs and keeping explicit plugin-owned auth when it is
  already configured.
- Verified the x-search legacy config seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_x_search_api_key
  tests\test_cli.py::test_doctor_fix_migrates_legacy_x_search_api_key -q` (`2
  passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`9
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop"` (`9 passed`), adjacent doctor contribution coverage
  `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  src\openzues\schemas.py tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- The native `legacyConfig` doctor contribution now normalizes Telegram
  streaming aliases into nested streaming config: `streamMode`, scalar/boolean
  `streaming`, `chunkMode`, `blockStreaming`, `draftChunk`, and
  `blockStreamingCoalesce` are migrated for both the root Telegram config and
  account-scoped entries, with `progress` mapped to OpenClaw's Telegram
  `partial` preview mode.
- Verified the Telegram streaming-key migration seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_telegram_streaming_keys
  tests\test_cli.py::test_doctor_fix_migrates_legacy_telegram_streaming_keys
  -q` (`2 passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  legacy_telegram_streaming_keys or doctor_fix_runs_startup_channel_maintenance_adapter
  or doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`11
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop"` (`9 passed`), adjacent doctor contribution coverage
  `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- The native `legacyConfig` doctor contribution now also normalizes Slack
  streaming aliases into nested streaming config: `streamMode`, scalar/boolean
  `streaming`, `chunkMode`, `blockStreaming`, `blockStreamingCoalesce`, and
  `nativeStreaming` are migrated for both root Slack config and account-scoped
  entries, including OpenClaw's `nativeTransport` preservation.
- Verified the Slack streaming-key migration seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_slack_streaming_keys
  tests\test_cli.py::test_doctor_fix_migrates_legacy_slack_streaming_keys -q`
  (`2 passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  legacy_telegram_streaming_keys or legacy_slack_streaming_keys or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`13
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop"` (`9 passed`), adjacent doctor contribution coverage
  `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- The native `legacyConfig` doctor contribution now also removes OpenClaw's
  unused Google Chat `streamMode` keys from root Google Chat config and
  account-scoped entries while preserving neighboring group/account settings.
- Verified the Google Chat streamMode removal seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_googlechat_stream_mode
  tests\test_cli.py::test_doctor_fix_removes_legacy_googlechat_stream_mode -q`
  (`2 passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  legacy_telegram_streaming_keys or legacy_slack_streaming_keys or
  legacy_googlechat_stream_mode or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`15
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop"` (`9 passed`), adjacent doctor contribution coverage
  `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- The native `legacyConfig` repair path now covers OpenClaw's runtime gateway
  config migrations: `doctor --fix` seeds
  `gateway.controlUi.allowedOrigins` for existing non-loopback bind modes with
  no configured origins, preserves gateway runtime fields through config
  validation, and normalizes legacy `gateway.bind` host aliases such as
  `0.0.0.0` / `localhost` to bind modes.
- Verified the runtime gateway legacy config seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_gateway_bind_host_alias
  tests\test_cli.py::test_doctor_fix_normalizes_legacy_gateway_bind_host_alias
  tests\test_cli.py::test_doctor_fix_seeds_gateway_control_ui_origins_for_non_loopback_bind
  -q` (`3 passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  legacy_telegram_streaming_keys or legacy_slack_streaming_keys or
  legacy_googlechat_stream_mode or legacy_gateway_bind_host_alias or
  gateway_control_ui_origins or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`18
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop or config_get_returns_control_ui_bootstrap_snapshot"`
  (`10 passed`), adjacent doctor contribution coverage `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  src\openzues\schemas.py tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- The native `legacyConfig` repair path now migrates OpenClaw's legacy
  `audio.transcription` config into `tools.media.audio.models`, mapping safe
  CLI commands with args/timeouts, preserving existing model lists by removing
  only the legacy key, and dropping invalid/unsafe commands with the
  OpenClaw-shaped repair note.
- Verified the audio transcription legacy config seam with `python -m pytest
  tests\test_cli.py::test_doctor_fix_migrates_legacy_audio_transcription
  tests\test_cli.py::test_doctor_fix_removes_legacy_audio_transcription_when_models_exist
  tests\test_cli.py::test_doctor_fix_removes_invalid_legacy_audio_transcription
  -q` (`3 passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  legacy_telegram_streaming_keys or legacy_slack_streaming_keys or
  legacy_googlechat_stream_mode or legacy_gateway_bind_host_alias or
  gateway_control_ui_origins or legacy_audio_transcription or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`21
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop or config_get_returns_control_ui_bootstrap_snapshot"`
  (`10 passed`), adjacent doctor contribution coverage `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  src\openzues\schemas.py tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- The native `legacyConfig` doctor contribution now migrates OpenClaw's
  `agents.defaults.sandbox.perSession` and
  `agents.list[].sandbox.perSession` aliases into `sandbox.scope`, mapping
  `true` to `session`, `false` to `shared`, and removing the legacy key when
  `scope` is already explicit.
- Verified the sandbox perSession legacy config seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_sandbox_per_session
  tests\test_cli.py::test_doctor_fix_migrates_legacy_sandbox_per_session -q`
  (`2 passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  legacy_telegram_streaming_keys or legacy_slack_streaming_keys or
  legacy_googlechat_stream_mode or legacy_gateway_bind_host_alias or
  gateway_control_ui_origins or legacy_audio_transcription or
  legacy_sandbox_per_session or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`23
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop or config_get_returns_control_ui_bootstrap_snapshot"`
  (`10 passed`), adjacent doctor contribution coverage `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  src\openzues\schemas.py tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- The native `legacyConfig` doctor contribution now migrates OpenClaw's
  top-level `memorySearch` config into `agents.defaults.memorySearch`,
  including recursive merge-missing behavior that preserves explicit
  `agents.defaults` values.
- Verified the memorySearch legacy config seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_memory_search
  tests\test_cli.py::test_doctor_fix_migrates_legacy_memory_search
  tests\test_cli.py::test_doctor_fix_merges_legacy_memory_search_into_defaults
  -q` (`3 passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  legacy_telegram_streaming_keys or legacy_slack_streaming_keys or
  legacy_googlechat_stream_mode or legacy_gateway_bind_host_alias or
  gateway_control_ui_origins or legacy_audio_transcription or
  legacy_sandbox_per_session or legacy_memory_search or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`26
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop or config_get_returns_control_ui_bootstrap_snapshot"`
  (`10 passed`), adjacent doctor contribution coverage `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  src\openzues\schemas.py tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- The native `legacyConfig` doctor contribution now migrates OpenClaw's
  top-level `heartbeat` config into `agents.defaults.heartbeat` and
  `channels.defaults.heartbeat`, splitting visibility keys from agent cadence
  settings, recursively filling only missing default fields, and removing empty
  legacy heartbeat blocks.
- Verified the heartbeat legacy config seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_heartbeat
  tests\test_cli.py::test_doctor_fix_splits_legacy_heartbeat_into_defaults
  tests\test_cli.py::test_doctor_fix_merges_legacy_heartbeat_into_defaults
  tests\test_cli.py::test_doctor_fix_removes_empty_legacy_heartbeat -q` (`4
  passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  legacy_telegram_streaming_keys or legacy_slack_streaming_keys or
  legacy_googlechat_stream_mode or legacy_gateway_bind_host_alias or
  gateway_control_ui_origins or legacy_audio_transcription or
  legacy_sandbox_per_session or legacy_memory_search or legacy_heartbeat or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`30
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop or config_get_returns_control_ui_bootstrap_snapshot"`
  (`10 passed`), adjacent doctor contribution coverage `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  src\openzues\schemas.py tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- The native `legacyConfig` doctor contribution now normalizes OpenClaw's
  legacy TTS provider config for `messages.tts` and the bundled `voice-call`
  plugin, moving `openai`, `elevenlabs`, `microsoft`, and `edge` provider keys
  into `tts.providers` and mapping `edge` to `microsoft` while preserving
  explicit provider fields.
- Verified the TTS provider legacy config seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_tts_provider_config
  tests\test_cli.py::test_doctor_fix_migrates_legacy_tts_provider_config -q`
  (`2 passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  legacy_telegram_streaming_keys or legacy_slack_streaming_keys or
  legacy_googlechat_stream_mode or legacy_gateway_bind_host_alias or
  gateway_control_ui_origins or legacy_audio_transcription or
  legacy_sandbox_per_session or legacy_memory_search or legacy_heartbeat or
  legacy_tts_provider_config or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`32
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop or config_get_returns_control_ui_bootstrap_snapshot"`
  (`10 passed`), adjacent doctor contribution coverage `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  src\openzues\schemas.py tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- The native `legacyConfig` doctor contribution now covers OpenClaw's
  `tools.web.search` provider-owned config migration. Global legacy
  `tools.web.search.apiKey` moves to `plugins.entries.brave.config.webSearch`;
  scoped provider records such as `grok` and `kimi` move through bundled
  provider ownership to `xai` and `moonshot`; existing plugin-owned config
  fields win; and modern `openaiCodex` search config stays on
  `tools.web.search`.
- Verified the web-search provider legacy config seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_web_search_provider_config
  tests\test_cli.py::test_doctor_fix_migrates_legacy_web_search_provider_config
  -q` (`2 passed`), adjacent legacy-config doctor coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_thread_binding_ttl_hours or
  legacy_channel_allow_aliases or legacy_x_search_api_key or
  legacy_web_search_provider_config or legacy_telegram_streaming_keys or
  legacy_slack_streaming_keys or legacy_googlechat_stream_mode or
  legacy_gateway_bind_host_alias or gateway_control_ui_origins or
  legacy_audio_transcription or legacy_sandbox_per_session or
  legacy_memory_search or legacy_heartbeat or legacy_tts_provider_config or
  doctor_fix_runs_startup_channel_maintenance_adapter or
  doctor_skips_startup_channel_maintenance_without_fix or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`34
  passed`), adjacent config coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "config_set_rejects_legacy_thread_binding_ttl_hours or
  config_set_preserves_session_thread_binding_idle_hours or config_write_methods
  or config_patch_noop or config_get_returns_control_ui_bootstrap_snapshot"`
  (`10 passed`), adjacent doctor contribution coverage `python -m pytest
  tests\test_cli.py -q -k
  "doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_memory_probe_contribution or
  doctor_json_includes_gateway_health_contribution"` (`3 passed`), `ruff check
  src\openzues\cli.py src\openzues\services\gateway_config.py
  src\openzues\schemas.py tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- Top-level `doctor --json` now includes OpenClaw's bundled plugin load-path
  repair contribution. It detects legacy source-style
  `plugins.load.paths=.../extensions/<plugin>` entries, reports the current
  packaged target, rewrites them to `dist/extensions` or `dist-runtime/extensions`
  during `doctor --fix`, and runs before stale plugin config cleanup.
- Verified the bundled plugin load-path doctor seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_bundled_plugin_load_paths
  tests\test_cli.py::test_doctor_fix_rewrites_legacy_bundled_plugin_load_paths_before_stale_scan
  -q` (`2 passed`), adjacent doctor/plugin coverage `python -m pytest
  tests\test_cli.py -q -k "bundled_plugin_load_paths or stale_plugin_config or
  bundled_plugin_runtime_dependency_contribution or
  plugins_list_json_discovers_openclaw_manifest_load_paths"` (`7 passed`),
  `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- Top-level `doctor --json` now includes OpenClaw's stale plugin config
  contribution. It scans `plugins.allow` and `plugins.entries.<id>` against
  native and manifest-backed plugin ids, formats the upstream warning/hint
  shape, removes stale refs during `doctor --fix`, and pauses auto-removal
  when manifest discovery reports errors.
- Verified the stale plugin config doctor seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_stale_plugin_config
  tests\test_cli.py::test_doctor_fix_removes_stale_plugin_config
  tests\test_cli.py::test_doctor_fix_pauses_stale_plugin_config_repair_when_discovery_has_errors
  -q` (`3 passed`), adjacent doctor/plugin coverage `python -m pytest
  tests\test_cli.py -q -k "stale_plugin_config or
  legacy_web_search_provider_config or legacy_tts_provider_config or
  bundled_plugin_runtime_dependency_contribution or
  doctor_json_includes_security_and_shell_completion_surfaces"` (`9 passed`),
  `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- Top-level `doctor --json` now includes OpenClaw's legacy plugin manifest
  contract-key contribution. It detects top-level `speechProviders`,
  `mediaUnderstandingProviders`, and `imageGenerationProviders` in
  `openclaw.plugin.json` files discovered through `plugins.load.paths`, reports
  OpenClaw-shaped migration lines, and rewrites those keys into
  `contracts.<key>` during `doctor --fix` before stale plugin config cleanup.
- Verified the legacy plugin manifest doctor seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_legacy_plugin_manifest_contract_keys
  tests\test_cli.py::test_doctor_fix_rewrites_legacy_plugin_manifest_contract_keys
  -q` (`2 passed`), adjacent doctor/plugin coverage `python -m pytest
  tests\test_cli.py -q -k "legacy_plugin_manifest_contract_keys or
  legacy_bundled_plugin_load_paths or stale_plugin_config"` (`7 passed`),
  broader doctor warning/repair coverage `python -m pytest tests\test_cli.py
  -q -k "doctor_json_warns or doctor_fix_rewrites"` (`29 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now also includes OpenClaw's open-policy
  `allowFrom` repair contribution. It reports pending wildcard additions for
  `dmPolicy="open"`, writes top-level or nested `allowFrom=["*"]` according to
  channel mode during `doctor --fix`, and canonicalizes nested `dm.policy` for
  top-level-capable channels.
- Verified the open-policy allowFrom doctor seam with `python -m pytest
  tests\test_cli.py::test_doctor_json_warns_about_open_policy_allow_from
  tests\test_cli.py::test_doctor_fix_repairs_open_policy_allow_from -q` (`2
  passed`), adjacent doctor repair coverage `python -m pytest tests\test_cli.py
  -q -k "open_policy_allow_from or bundled_plugin_load_paths or
  stale_plugin_config or legacy_channel_allow_aliases"` (`9 passed`), `ruff
  check src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- Top-level `doctor --fix` now also covers OpenClaw's allowlist-policy
  `allowFrom` recovery helper. It reads saved channel pairing stores, dedupes
  stored senders, restores missing allowlists for `dmPolicy="allowlist"` or
  nested `dm.policy="allowlist"`, and writes nested-only channel allowlists
  where OpenClaw keeps them.
- Verified the allowlist-policy allowFrom doctor seam with `python -m pytest
  tests\test_cli.py::test_doctor_fix_recovers_allowlist_policy_allow_from_from_store
  -q` (`1 passed`), adjacent doctor repair coverage `python -m pytest
  tests\test_cli.py -q -k "allowlist_policy_allow_from or
  open_policy_allow_from or bundled_plugin_load_paths or stale_plugin_config"`
  (`8 passed`), `ruff check src\openzues\cli.py
  src\openzues\services\gateway_config.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py src\openzues\services\gateway_config.py`.
- Route-backed `sessions.spawn thread=true` now persists an OpenClaw-shaped
  current-conversation `sessionBinding` record on child session metadata in
  addition to `threadBinding` and `completionDelivery`. Records include
  `bindingId`, `targetSessionKey`, `targetKind`, normalized `conversation`,
  `status`, `boundAt`, and `metadata.lastActivityAt` for Slack/Telegram/
  Discord/WhatsApp/Matrix route-backed binders.
- Verified the session-binding record seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_thread_mode_uses_route_backed_thread_binder
  -q` (`1 passed`), adjacent binder coverage `python -m pytest
  tests\test_gateway_thread_binding.py
  tests\test_gateway_node_methods.py::test_sessions_spawn_thread_mode_uses_route_backed_thread_binder
  -q` (`5 passed`), adjacent thread-spawn coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_thread_mode_uses_route_backed_thread_binder or
  sessions_spawn_thread_mode_uses_matrix_route_backed_thread_binder or
  sessions_spawn_thread_mode_requires_thread_binding_hook or
  sessions_spawn_thread_mode_uses_thread_binding_hook or
  sessions_spawn_thread_mode_cleans_up_binding_when_child_registration_fails or
  sessions_spawn_thread_mode_honors_channel_spawn_policy or
  sessions_spawn_thread_mode_requires_spawn_policy_for_child_placement"` (`6
  passed`), `ruff check src\openzues\services\gateway_thread_binding.py
  src\openzues\services\gateway_node_methods.py tests\test_gateway_thread_binding.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_thread_binding.py
  src\openzues\services\gateway_node_methods.py`.
- Cross-agent `sessions.spawn thread=true` now mirrors OpenClaw's
  `resolveRequesterOriginForChild` account selection for route bindings:
  top-level `bindings` survive the native config snapshot, Matrix-style
  `room:` targets are matched against configured peer ids, and the binder plus
  initial child run use the target agent's bound account when it differs from
  the caller account.
- Verified the target-agent bound-account seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_thread_mode_uses_target_agent_bound_account
  -q` (`1 passed`), adjacent thread-spawn coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "target_agent_bound_account or
  sessions_spawn_thread_mode_uses_matrix_route_backed_thread_binder or
  sessions_spawn_thread_mode_uses_route_backed_thread_binder or
  sessions_spawn_thread_mode_honors_channel_spawn_policy or
  sessions_spawn_thread_mode_requires_spawn_policy_for_child_placement"` (`5
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  src\openzues\schemas.py tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py`.
- Thread-bound `sessions.spawn` now also mirrors OpenClaw's generic-binding
  fallback: when a hook reports `threadBindingReady=true` but supplies no
  routable delivery origin, the initial child run is queued with
  `deliver=false` while carrying the requester channel/account target and
  leaving completion announcements enabled.
- Verified the generic thread-binding fallback seam with `python -m pytest
  tests\test_gateway_node_methods.py -k
  "thread_mode_without_delivery_origin_keeps_completion" -q` (`1 passed`),
  adjacent thread/completion coverage `python -m pytest
  tests\test_gateway_node_methods.py -k "thread_mode_without_delivery_origin_keeps_completion
  or thread_mode_delivers_initial_child_run_to_bound_origin or
  thread_mode_cleans_up_binding_when_runtime_start_fails or
  thread_mode_uses_route_backed_thread_binder or
  thread_mode_uses_matrix_route_backed_thread_binder or
  thread_mode_uses_target_agent_bound_account or
  agent_wait_thread_bound_completion_uses_completion_delivery_route or
  agent_wait_announces_spawn_completion_to_parent_session or
  agent_wait_skips_spawn_completion_announcement_when_not_expected" -q` (`10
  passed`), `python -m pytest tests\test_gateway_thread_binding.py -q` (`4
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Cross-agent ACP `sessions.spawn runtime="acp" thread=true` now uses that
  same OpenClaw `resolveRequesterOriginForChild` account selection before
  native thread-binding policy checks and ACP runtime dispatch, so
  account-scoped Matrix ACP spawn config can authorize the target agent's
  bound account even when the caller arrives from a different account.
- Verified the ACP target-agent bound-account seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_thread_mode_uses_target_agent_bound_account
  -q` (`1 passed`), adjacent ACP coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_acp_thread_mode_uses_target_agent_bound_account or
  sessions_spawn_acp_thread_mode_honors_channel_spawn_policy or
  sessions_spawn_acp_thread_mode_requires_spawn_policy_for_child_placement or
  sessions_spawn_acp_runtime_tracks_wait_cleanup_and_completion or
  sessions_spawn_acp_stream_to_parent_tracks_child_run"` (`5 passed`), `ruff
  check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- ACP accepted results that carry a prepared thread binding now persist the
  OpenClaw-shaped child metadata envelope: `threadBinding`, `sessionBinding`
  with `targetKind="session"`, derived `completionDelivery`, and bound
  delivery context / last-channel fields.
- Verified the ACP session-binding metadata seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_thread_mode_persists_session_binding_metadata
  -q` (`1 passed`), adjacent ACP lifecycle coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_acp_thread_mode_persists_session_binding_metadata or
  sessions_spawn_acp_thread_mode_uses_target_agent_bound_account or
  sessions_spawn_acp_runtime_tracks_wait_cleanup_and_completion or
  sessions_spawn_acp_stream_to_parent_tracks_child_run or
  sessions_reset_closes_acp_runtime_before_resetting_metadata or
  sessions_delete_closes_acp_runtime_before_metadata_delete"` (`6 passed`),
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- ACP `thread=true` spawns now also mirror OpenClaw's
  `resolveAcpSpawnChannelAccountId` fallback: when channel context omits an
  account id, `channels.<channel>.defaultAccount` is applied before
  account-scoped spawn policy checks and before the native ACP runtime context
  is dispatched.
- Verified the ACP default-account seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_thread_mode_uses_channel_default_account
  -q` (`1 passed`), adjacent ACP account-policy coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_acp_thread_mode_uses_channel_default_account or
  sessions_spawn_acp_thread_mode_uses_target_agent_bound_account or
  sessions_spawn_acp_thread_mode_persists_session_binding_metadata or
  sessions_spawn_acp_thread_mode_honors_channel_spawn_policy or
  sessions_spawn_acp_thread_mode_requires_spawn_policy_for_child_placement"`
  (`5 passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- RuntimeManager ACP `thread=true` bindings now preserve Telegram forum-topic
  current-conversation ids in both upstream shapes: topic-qualified `to`
  targets and `groupId` plus `threadId` contexts persist
  `conversationId="<chatId>:topic:<threadId>"` without a self-parent
  conversation field.
- Verified the ACP Telegram topic binding seam with `python -m pytest
  tests\test_gateway_acp_spawn.py::test_runtime_manager_acp_spawn_preserves_telegram_topic_target
  tests\test_gateway_acp_spawn.py::test_runtime_manager_acp_spawn_binds_telegram_forum_topic_from_thread_id
  -q` (`2 passed`), full ACP adapter coverage `python -m pytest
  tests\test_gateway_acp_spawn.py -q` (`18 passed`), adjacent gateway ACP
  persistence coverage `python -m pytest tests\test_gateway_node_methods.py -q
  -k "sessions_spawn_acp_thread_mode or
  sessions_spawn_acp_runtime_tracks_wait_cleanup_and_completion or
  sessions_spawn_acp_stream_to_parent_tracks_child_run or
  sessions_reset_closes_acp_runtime_before_resetting_metadata or
  sessions_delete_closes_acp_runtime_before_metadata_delete"` (`10 passed`),
  `ruff check src\openzues\services\gateway_acp_spawn.py
  tests\test_gateway_acp_spawn.py`, and `mypy
  src\openzues\services\gateway_acp_spawn.py`.
- Gateway ACP spawns now honor OpenClaw's `acp.enabled=false` runtime policy
  before the service boundary, returning `errorCode="acp_disabled"` and
  avoiding target/runtime dispatch.
- Verified the ACP disabled-policy seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_respects_disabled_policy
  -q` (`1 passed`), adjacent ACP policy coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_acp_respects_disabled_policy or
  sessions_spawn_acp_requires_target_agent_without_default or
  sessions_spawn_acp_uses_configured_default_agent or
  sessions_spawn_acp_rejects_agent_outside_acp_allowlist or
  sessions_spawn_rejects_acp_required_sandbox_policy"` (`5 passed`), `ruff
  check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- The ACP `mode="session"` guard now lives at the gateway method boundary as
  well as in the concrete RuntimeManager adapter, preserving OpenClaw's
  `thread_required` preflight even when a fakeable or alternate ACP service is
  registered.
- Verified the gateway ACP `thread_required` preflight with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_session_mode_requires_thread_before_runtime
  -q` (`1 passed`), adjacent ACP preflight coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sessions_spawn_acp_session_mode_requires_thread_before_runtime or
  sessions_spawn_acp_respects_disabled_policy or
  sessions_spawn_acp_requires_target_agent_without_default or
  sessions_spawn_acp_uses_configured_default_agent or
  sessions_spawn_acp_rejects_agent_outside_acp_allowlist or
  sessions_spawn_acp_thread_mode_honors_channel_spawn_policy"` (`6 passed`),
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Route-backed `sessions.reset` and `sessions.delete` now run binder `unbind`
  lifecycle cleanup for thread-bound child sessions using the saved
  `sessionBinding` and `threadBinding` metadata before mutating or deleting the
  local session. Reset also clears stale binding/completion metadata so a reset
  session does not continue advertising a bound conversation that has been
  unbound.
- Verified the route-backed unbind lifecycle seam with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_reset_delete_unbinds_thread_bound_sessions
  -q` (`2 passed`), adjacent reset/delete/thread-binding coverage `python -m
  pytest tests\test_gateway_node_methods.py -q -k "sessions_reset or
  sessions_delete or thread_binding"` (`20 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py`,
  and `mypy src\openzues\services\gateway_node_methods.py`.
- Route-backed `sessions.reset` and `sessions.delete` now also emit
  OpenClaw-shaped `subagent_ended` lifecycle events through a fakeable native
  service after session mutation, with `targetKind`, `sendFarewell=true`, and
  `outcome=reset/deleted`; `sessions.delete emitLifecycleHooks=false` skips
  only that hook.
- Verified the reset/delete subagent-ended lifecycle seam with `python -m
  pytest
  tests\test_gateway_node_methods.py::test_sessions_reset_delete_emit_subagent_ended_lifecycle_hook
  tests\test_gateway_node_methods.py::test_sessions_delete_emit_lifecycle_hooks_false_skips_subagent_ended_hook
  -q` (`3 passed`) and adjacent reset/delete/thread-binding coverage `python
  -m pytest tests\test_gateway_node_methods.py -q -k "sessions_reset or
  sessions_delete or thread_binding"` (`23 passed`).
- Discord guild-admin `event-create` now includes OpenClaw-style scheduled
  event cover-image resolution: `image` accepts data URLs, local/canvas paths,
  and HTTP media through the shared Discord media loader, enforces the upstream
  8 MB cap, validates PNG/JPG/GIF content types, and forwards a Discord data
  URI in the scheduled-event payload.
- Verified the Discord event-cover seam with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_event_create_cover_route"` (`1
  passed`), adjacent event-create coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_event_create"` (`2 passed`), adjacent
  Discord action coverage `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`45 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord guild-admin `channel-permission-set` and
  `channel-permission-remove` now follow OpenClaw's permission overwrite
  action contract through the route-backed bot-token REST path. Set maps
  `targetType=role/member` to Discord types `0/1`, preserves optional
  `allow`/`deny`, normalizes `channel:` ids, and remove deletes the overwrite
  while both return `{ok: true}`.
- Verified the Discord channel-permissions seam with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_channel_permissions_route"` (`1
  passed`), adjacent Discord action coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "message_action_dispatches_discord"` (`46
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Discord `thread-reply` now handles OpenClaw-style `mediaUrl` through the
  bot-token REST path. Media replies load data URLs/local/canvas/HTTP media
  with the upstream default 100 MB cap, derive a Discord upload filename,
  preserve `message_reference`, and POST multipart `payload_json` plus
  `files[0]` to the thread message endpoint.
- Verified the Discord thread-reply media seam with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_thread_reply_media_route"` (`1
  passed`), adjacent thread-reply coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_thread_reply"` (`2 passed`), adjacent
  Discord action coverage `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_discord"` (`47 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Discord `message.action poll` now dispatches through the bot-token REST
  path, preserving OpenClaw's `to`, `content`, `question`, `answers`,
  string/boolean `allowMultiselect`, and `durationHours` handling. Native
  Discord poll payloads now also include the upstream `layout_type=1` field.
- Verified the Discord poll action seam with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_poll_route"` (`1 passed`), adjacent
  direct Discord poll coverage `python -m pytest tests\test_ops_mesh.py -q -k
  "send_direct_channel_poll_uses_discord_native_route"` (`1 passed`),
  combined focused coverage `python -m pytest tests\test_ops_mesh.py -q -k
  "discord_poll_route or send_direct_channel_poll_uses_discord_native_route"`
  (`2 passed`), adjacent Discord action coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "message_action_dispatches_discord"` (`48
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Discord `fetch-message` now covers OpenClaw's single-message fetch runtime:
  it accepts either `messageLink` or explicit `guildId`/`channelId`/`messageId`,
  performs a route-backed bot-token REST GET, and returns the fetched message
  with normalized timestamp metadata.
- Verified the Discord fetch-message seam with `python -m pytest
  tests\test_ops_mesh.py -q -k "discord_fetch_message_route"` (`1 passed`),
  adjacent Discord action coverage `python -m pytest tests\test_ops_mesh.py -q
  -k "message_action_dispatches_discord"` (`49 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- ACP `streamTo="parent"` now has a native RuntimeManager parent-stream relay
  path: the service resolves a child JSONL stream log, starts a provisional
  parent relay before dispatch, restarts it when the returned Codex turn id
  differs from the provisional run id, notifies the accepted relay, and surfaces
  `streamLogPath` through the gateway metadata path. App and CLI construction
  now wire the file-backed relay under the OpenZues data dir.
- Verified the ACP parent-stream relay seam with `python -m pytest
  tests/test_gateway_acp_spawn.py::test_runtime_manager_acp_spawn_stream_to_parent_runs_parent_stream_relay
  -q` (`1 passed`), adjacent ACP spawn coverage `python -m pytest
  tests/test_gateway_acp_spawn.py -q` (`19 passed`),
  `tests/test_gateway_node_methods.py::test_sessions_spawn_acp_stream_to_parent_tracks_child_run`
  (`1 passed`), `tests/test_cli.py::test_sessions_spawn_json_calls_gateway_method_owner`
  (`1 passed`), `ruff check src\openzues\services\gateway_acp_spawn.py
  src\openzues\app.py src\openzues\cli.py tests\test_gateway_acp_spawn.py`,
  and `mypy src\openzues\services\gateway_acp_spawn.py src\openzues\app.py
  src\openzues\cli.py`.
- ACP run-mode spawns from canonical subagent requester sessions now mirror the
  upstream implicit parent-stream rule: when heartbeat delivery is
  session-local (`target="last"` with no explicit heartbeat route), the
  requester has a usable current delivery route, and the request is not
  thread-bound or already carrying thread context, the gateway passes
  `streamTo="parent"` into the ACP runtime and persists the returned stream log.
- Verified the implicit ACP parent-stream seam with `python -m pytest
  tests/test_gateway_node_methods.py::test_sessions_spawn_acp_run_from_subagent_requester_implicitly_streams_to_parent
  -q` (`1 passed`), adjacent explicit-stream coverage `python -m pytest
  tests/test_gateway_node_methods.py::test_sessions_spawn_acp_run_from_subagent_requester_implicitly_streams_to_parent
  tests/test_gateway_node_methods.py::test_sessions_spawn_acp_stream_to_parent_tracks_child_run
  -q` (`2 passed`), ACP spawn gateway coverage `python -m pytest
  tests/test_gateway_node_methods.py -q -k "sessions_spawn_acp"` (`17 passed`),
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- ACP implicit parent streaming now also honors OpenClaw's runtime heartbeat
  toggle: after `set-heartbeats enabled=false`, canonical subagent requester
  ACP run spawns no longer receive implicit `streamTo="parent"` and do not
  persist `streamTo` / `streamLogPath` metadata, while explicit stream
  requests keep their existing behavior.
- Verified the runtime-disabled heartbeat ACP stream gate with `python -m
  pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_run_from_subagent_requester_skips_stream_when_heartbeats_disabled
  -q` (`1 passed`), adjacent heartbeat/implicit-stream coverage `python -m
  pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_run_from_subagent_requester_implicitly_streams_to_parent
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_run_from_subagent_requester_skips_stream_when_heartbeats_disabled
  tests\test_gateway_node_methods.py::test_set_heartbeats_returns_ok_payload_when_runtime_is_wired
  -q` (`3 passed`), ACP spawn gateway coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_spawn_acp or
  set_heartbeats"` (`19 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Accepted ACP spawns now register a native OpenClaw-shaped running task record
  by persisting `taskRecord` and `taskDeliveryState` into the child session
  metadata. The record preserves `runtime="acp"`, `sourceId` / `runId`,
  requester/owner session keys, child session key, label, task text,
  `status="running"`, `deliveryStatus`, notify policy, and event timestamps.
  `openzues tasks --json` now projects those metadata-backed ACP records beside
  existing native mission and blueprint task records.
- Verified the ACP task-record registration slice with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_acp_accepted_run_persists_openclaw_task_record
  -q` (`1 passed`) and `python -m pytest
  tests\test_cli.py::test_tasks_list_json_projects_acp_task_records_from_session_metadata
  -q` (`1 passed`), adjacent ACP spawn coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_spawn_acp"` (`19 passed`),
  adjacent task CLI coverage `python -m pytest tests\test_cli.py -q -k
  "tasks_list_json or tasks_show_json or tasks_audit_json or
  tasks_maintenance_json"` (`5 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py src\openzues\cli.py
  tests\test_gateway_node_methods.py tests\test_cli.py`, and `mypy
  src\openzues\services\gateway_node_methods.py src\openzues\cli.py`.
- ACP terminal waits now update the metadata-backed OpenClaw task record for
  tracked child ACP runs: completed runs become `succeeded`, receive
  `terminalSummary`, `terminalOutcome="succeeded"`, `endedAt`, `lastEventAt`,
  and `deliveryStatus="session_queued"` when the completion is queued back to
  the parent session. Provider completion delivery can further promote the same
  record to `delivered` or `failed`.
- Verified the ACP terminal task-record lifecycle slice with `python -m pytest
  tests\test_gateway_node_methods.py::test_agent_wait_marks_acp_task_record_succeeded_on_completed_run
  -q` (`1 passed`), adjacent wait/completion coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "agent_wait_marks_acp_task_record or
  agent_wait_announces_spawn_completion_to_parent_session or
  agent_wait_thread_bound_completion_uses_completion_delivery_route or
  agent_wait_returns_failed_terminal_snapshot_for_tracked_run"` (`4 passed`),
  adjacent ACP/wait coverage `python -m pytest tests\test_gateway_node_methods.py
  -q -k "sessions_spawn_acp or agent_wait"` (`38 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- ACP in-flight runtime progress now updates the same metadata-backed
  OpenClaw task record before terminal wait. The app-wired gateway runtime
  event listener matches ACP app-server text deltas by run id or runtime thread
  id, appends normalized output into `progressSummary`, and advances
  `lastEventAt` while preserving `status="running"`.
- Verified the ACP runtime progress task-record slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "runtime_progress_appends_task_record_summary"` (`1 passed`), adjacent ACP
  spawn/wait coverage `python -m pytest tests\test_gateway_node_methods.py -q
  -k "sessions_spawn_acp or agent_wait"` (`39 passed`), runtime event-handler
  neighborhood `python -m pytest tests\test_manager.py -q -k
  "compact_event_payload or handle_event"` (`11 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py src\openzues\app.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py` plus `mypy
  src\openzues\app.py`. A broader exploratory manager filter
  `python -m pytest tests\test_manager.py -q -k "event or turn"` still exposes
  unrelated fake-client `sandbox_mode` failures in four existing `start_turn`
  tests.
- Metadata-backed ACP tasks now cancel through the native `tasks cancel` CLI
  path. The CLI resolves ACP task/run/session lookup tokens, calls the
  fakeable ACP runtime `cancel_session` hook with `reason="task-cancel"`, and
  patches the persisted task record to `status="cancelled"` with `endedAt`,
  `lastEventAt`, and `error="Cancelled by operator."`.
- Verified the ACP metadata task cancel slice with `python -m pytest
  tests\test_cli.py -q -k "tasks_cancel_cancels_metadata_backed_acp_task"` (`1
  passed`), adjacent CLI task coverage `python -m pytest tests\test_cli.py -q
  -k "tasks_cancel or tasks_notify or
  tasks_list_json_projects_acp_task_records_from_session_metadata or
  tasks_show_json or tasks_audit_json or tasks_maintenance_json"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Telegram `message.action send` now reaches the native route-backed Bot API
  runtime instead of falling through unsupported. The action forwards
  OpenClaw-style `to`, `message`, `media`, `replyTo`, `threadId`, `silent`, and
  `asDocument` (as `forceDocument`) into `gateway/send`, returning provider
  `messageId`, `channelId`, and `mediaIds` metadata.
- Verified the Telegram action-send slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_send_document_alias"` (`1 passed`),
  adjacent route/provider coverage `python -m pytest tests\test_ops_mesh.py -q
  -k "message_action_dispatches_slack_send_route or
  message_action_dispatches_telegram_send_document_alias or
  message_action_dispatches_telegram_react_route or
  message_action_dispatches_discord_send_route or
  send_direct_channel_message_uses_telegram_native_options"` (`5 passed`),
  `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and
  `mypy src\openzues\services\ops_mesh.py`.
- Telegram `message.action poll` now reaches the native route-backed Bot API
  runtime instead of falling through unsupported. The action forwards
  OpenClaw-style `to`, `pollQuestion`, `pollOption`, `pollMulti`, `replyTo`,
  `threadId`, and `silent` into `gateway/poll`, returning provider
  `messageId`, `channelId`, `conversationId`, and `pollId` metadata.
- Verified the Telegram action-poll slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_poll_route"` (`1 passed`),
  adjacent route/provider coverage `python -m pytest tests\test_ops_mesh.py -q
  -k "message_action_dispatches_telegram_poll_route or
  message_action_dispatches_telegram_send_document_alias or
  message_action_dispatches_telegram_react_route or
  send_direct_channel_poll_uses_telegram_native_route or
  message_action_dispatches_discord_poll_route"` (`5 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Slack `message.action poll` now matches OpenClaw's channel-actions contract:
  Slack message actions return unsupported for `poll` and do not post through
  the synthetic poll route, while the separate direct `gateway.poll` Slack
  runtime remains available for route-backed direct polls.
- Verified the Slack action-poll unsupported slice with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_message_action_rejects_slack_poll_like_openclaw
  -q` (`1 passed`), adjacent Slack action coverage `python -m pytest
  tests\test_ops_mesh.py -q -k "message_action_dispatches_slack or
  rejects_slack_poll"` (`17 passed`), direct Slack poll coverage
  `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_poll_uses_slack_native_route
  -q` (`1 passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- WhatsApp `message.action poll` now reaches the native Cloud API
  interactive-button poll runtime instead of falling through unsupported. The
  action forwards OpenClaw-style `to`, `pollQuestion`, `pollOption`, and
  `pollMulti` into `gateway/poll`, returning provider `messageId`,
  `channelId`, `conversationId`, and `pollId` metadata.
- Verified the WhatsApp action-poll slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "whatsapp_poll_route"` (`1 passed`), adjacent
  route/provider coverage `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_whatsapp_poll_route or
  message_action_dispatches_whatsapp_react_route or
  send_direct_channel_poll_uses_whatsapp_native_route or
  message_action_rejects_slack_poll_like_openclaw or
  message_action_dispatches_telegram_poll_route or
  message_action_dispatches_discord_poll_route"` (`6 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- WhatsApp `message.action send` now reaches the native Cloud API send runtime
  instead of falling through unsupported. The action forwards OpenClaw-style
  `to`, `message`, `media` / `mediaUrl`, `replyTo`, `gifPlayback`,
  `audioAsVoice`, and `forceDocument` / `asDocument` into `gateway/send`,
  returning provider `messageId`, `channelId`, `mediaIds`, and `mediaUrls`
  metadata.
- Verified the WhatsApp action-send slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "whatsapp_send_document_reply"` (`1 passed`),
  adjacent route/provider coverage `python -m pytest tests\test_ops_mesh.py -q
  -k "message_action_dispatches_whatsapp_send_document_reply or
  message_action_dispatches_whatsapp_poll_route or
  message_action_dispatches_whatsapp_react_route or
  send_direct_channel_message_preserves_whatsapp_reply_document or
  send_direct_channel_message_uses_whatsapp_gif_video_payload or
  send_direct_channel_message_uses_whatsapp_native_route"` (`6 passed`),
  `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and
  `mypy src\openzues\services\ops_mesh.py`.
- Sandbox `explain` now includes OpenClaw's read-only agent workspace mount
  hint: when the effective sandbox workspace access is `ro`, JSON and human
  output expose `agentWorkspaceMount="/agent"` so callers can distinguish the
  copied sandbox workspace from the mounted real agent workspace.
- Verified the sandbox mount projection with `python -m pytest
  tests\test_cli.py -q -k "read_only_agent_workspace_mount"` (`1 passed`),
  adjacent sandbox CLI/doctor coverage `python -m pytest tests\test_cli.py -q
  -k "sandbox_explain or sandbox_recreate or sandbox_inventory or
  doctor_sandbox"` (`5 passed`), `ruff check src\openzues\cli.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- The CLI now exposes `acp status [lookup]` as a native read-only ACP status
  surface. It resolves saved ACP sessions by session key, runtime thread id,
  runtime session id, label, task id, or run id, then projects backend, agent,
  session mode, state, runtime options, capabilities, identity, last activity,
  and linked metadata-backed task delivery/progress in JSON and upstream-style
  human `ACP status:` lines.
- Verified the ACP status CLI slice with `python -m pytest tests\test_cli.py
  -q -k "acp_status_json_and_human"` (`1 passed`), adjacent ACP/task CLI
  coverage `python -m pytest tests\test_cli.py -q -k
  "acp_status_json_and_human or acp_bridge_command_reports_native_runtime_unavailable
  or acp_client_command_reports_native_runtime_unavailable or
  acp_client_spawn_plan_strips_provider_auth_for_default_bridge or
  acp_client_command_passes_spawn_plan_to_registered_runner or
  tasks_cancel_cancels_metadata_backed_acp_task"` (`6 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- `agent.wait` now consumes cached native lifecycle runtime events in addition
  to mission-backed terminal snapshots. Runtime `lifecycle` `start` events
  record `startedAt`, terminal `end` events return OpenClaw-shaped
  `status="ok"`, `startedAt`, and `endedAt`, aborted terminal events map to
  `timeout`, and transient `error` events are kept behind the same short retry
  grace before becoming terminal snapshots.
- Verified the lifecycle-backed `agent.wait` slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "agent_wait_returns_cached_lifecycle_terminal_event"` (`1 passed`),
  adjacent wait/runtime-event coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "agent_wait_returns_cached_lifecycle_terminal_event or
  agent_wait_zero_timeout_returns_without_sleeping or
  agent_wait_waits_for_tracked_gateway_run_completion or
  agent_wait_returns_failed_terminal_snapshot_for_tracked_run or
  runtime_progress_appends_task_record_summary"` (`5 passed`), `ruff check
  src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Provider-backed `gateway.send` now mirrors OpenClaw's sandbox media bridge
  inbound fallback for staged media references: `@/.../media/inbound/<name>`
  resolves to the saved sandbox workspace's `media/inbound/<name>` file when
  that file exists, while existing `/workspace/...`, `file:///workspace/...`,
  dedupe, and remote URL behavior are preserved.
- Verified the sandbox inbound-media alias slice with `python -m pytest
  tests\test_gateway_node_methods.py::test_send_normalizes_sandbox_workspace_media_paths_from_session_metadata
  -q` (`1 passed`), adjacent send/media coverage `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "send_normalizes_sandbox_workspace_media_paths_from_session_metadata or
  send_uses_channel_message_runtime_for_media_payloads or
  send_preserves_provider_native_reply_thread_and_document_options or
  chat_send_sandboxed_saved_path_attachment_stages_media_in_session_workspace
  or chat_send_sandboxed_attachment_stages_media_in_session_workspace"` (`5
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- ACP client spawn planning now preserves provider auth when callers
  explicitly set the default executable (`openzues`) but change the server
  args, matching OpenClaw's default-executable/custom-entry guard while keeping
  the implicit default bridge on the provider-auth-stripping path.
- Verified the ACP client default-command override slice with `python -m pytest
  tests\test_cli.py -q -k
  "acp_client_spawn_plan_preserves_provider_auth_for_default_command_override
  or acp_client_spawn_plan_strips_provider_auth_for_default_bridge or
  acp_client_spawn_plan_preserves_provider_auth_for_custom_server or
  acp_client_spawn_invocation_unwraps_windows_cmd_shim or
  acp_client_command_passes_spawn_plan_to_registered_runner"` (`5 passed`),
  `ruff check src\openzues\services\acp_client_runtime.py tests\test_cli.py`,
  and `mypy src\openzues\services\acp_client_runtime.py`.
- ACP client spawn invocation now mirrors OpenClaw's optional spawn-option
  shape: non-Windows calls leave `shell` / `windowsHide` unset, resolved
  Windows `.cmd` shims still unwrap without shell execution and only set
  `windowsHide`, and unresolved Windows wrappers fail closed.
- Verified the ACP client invocation-option slice with `python -m pytest
  tests\test_cli.py -q -k "acp_client_spawn_invocation"` (`3 passed`),
  adjacent ACP client proof `python -m pytest tests\test_cli.py -q -k
  "acp_client_spawn_invocation or
  acp_client_spawn_plan_strips_provider_auth_for_default_bridge or
  acp_client_spawn_plan_preserves_provider_auth_for_default_command_override
  or acp_client_spawn_plan_preserves_provider_auth_for_custom_server or
  acp_client_command_passes_spawn_plan_to_registered_runner"` (`7 passed`),
  `ruff check src\openzues\services\acp_client_runtime.py tests\test_cli.py`,
  and `mypy src\openzues\services\acp_client_runtime.py`.
- The top-level ACP bridge command now accepts OpenClaw's gateway option
  aliases (`--gateway-url`, `--gateway-token`, `--gateway-token-file`,
  `--gateway-password`, and `--gateway-password-file`) while reusing the same
  native unavailable boundary, file-secret reads, and mixed inline/file secret
  validation.
- Verified the ACP bridge gateway-alias slice with `python -m pytest
  tests\test_cli.py -q -k "acp_bridge_command"` (`3 passed`), adjacent ACP
  CLI proof `python -m pytest tests\test_cli.py -q -k "acp_bridge_command or
  acp_client_command_reports_native_runtime_unavailable or
  acp_client_spawn_plan or acp_client_spawn_invocation or
  acp_client_command_passes_spawn_plan_to_registered_runner or
  acp_status_json_and_human"` (`12 passed`), `ruff check src\openzues\cli.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Native ACP client permission resolution now follows OpenClaw's
  `resolvePermissionRequest` contract for safe search/read auto-approval,
  spoofing guard rails, exec/control-plane/owner-only prompting, allow/reject
  option selection, cancellation when no options are available, and sanitized
  terminal titles before logging or prompting.
- Verified the ACP permission resolver slice with `python -m pytest
  tests\test_acp_client_runtime.py -q` (`7 passed`), adjacent ACP client proof
  `python -m pytest tests\test_acp_client_runtime.py tests\test_cli.py -q -k
  "acp_client or acp_bridge_command or acp_status_json_and_human"` (`19
  passed`), `ruff check src\openzues\services\acp_client_runtime.py
  tests\test_acp_client_runtime.py tests\test_cli.py`, and `mypy
  src\openzues\services\acp_client_runtime.py`.
- Native ACP event mapping now covers OpenClaw's prompt text/resource/resource
  link extraction, resource metadata control/delimiter escaping, max-byte
  accounting including newline separators, image-to-attachment projection, and
  control escaping in formatted tool titles.
- Verified the ACP event-mapper slice with `python -m pytest
  tests\test_acp_event_mapper.py -q` (`6 passed`), adjacent ACP runtime proof
  `python -m pytest tests\test_acp_event_mapper.py tests\test_acp_client_runtime.py
  tests\test_cli.py -q -k "acp_event_mapper or acp_permission or acp_client or
  acp_bridge_command or acp_status_json_and_human"` (`25 passed`), `ruff check
  src\openzues\services\acp_event_mapper.py tests\test_acp_event_mapper.py`,
  and `mypy src\openzues\services\acp_event_mapper.py`.
- ACP event mapping now also includes OpenClaw's tool-kind inference,
  tool-call content extraction from strings/content blocks/fallback text, and
  bounded file/media location extraction from tool args, file URLs, and
  `FILE:` / `MEDIA:` text markers.
- Verified the ACP tool-call mapper extension with `python -m pytest
  tests\test_acp_event_mapper.py -q -k "tool_call or tool_kinds or location"`
  (`4 passed`), adjacent ACP runtime proof `python -m pytest
  tests\test_acp_event_mapper.py tests\test_acp_client_runtime.py
  tests\test_cli.py -q -k "acp_event_mapper or acp_permission or acp_client or
  acp_bridge_command or acp_status_json_and_human"` (`29 passed`), `ruff check
  src\openzues\services\acp_event_mapper.py tests\test_acp_event_mapper.py`,
  and `mypy src\openzues\services\acp_event_mapper.py`.
- Native ACP session mapping now follows OpenClaw's `parseSessionMeta`,
  `resolveSessionKey`, and `resetSessionIfNeeded` contracts for session key
  aliases, label aliases, reset/require-existing/prefix-cwd booleans,
  explicit-label precedence, meta-key precedence over default labels,
  require-existing key lookups, and conditional `sessions.reset` dispatch.
- Verified the ACP session-mapper slice with `python -m pytest
  tests\test_acp_session_mapper.py -q` (`5 passed`), adjacent ACP support proof
  `python -m pytest tests\test_acp_session_mapper.py tests\test_acp_event_mapper.py
  tests\test_acp_client_runtime.py tests\test_cli.py -q -k
  "acp_session_mapper or acp_event_mapper or acp_permission or acp_client or
  acp_bridge_command or acp_status_json_and_human"` (`34 passed`), `ruff check
  src\openzues\services\acp_session_mapper.py tests\test_acp_session_mapper.py`,
  and `mypy src\openzues\services\acp_session_mapper.py`.
- Native ACP available commands now expose OpenClaw's base ACP slash-command
  catalog (`help`, `commands`, `status`, context/model/runtime/session commands,
  and `compact`) plus a fakeable extension hook for dock-style commands.
- Verified the ACP available-command slice with `python -m pytest
  tests\test_acp_commands.py -q` (`2 passed`), adjacent ACP support proof
  `python -m pytest tests\test_acp_commands.py tests\test_acp_session_mapper.py
  tests\test_acp_event_mapper.py tests\test_acp_client_runtime.py
  tests\test_cli.py -q -k "acp_available_commands or acp_session_mapper or
  acp_event_mapper or acp_permission or acp_client or acp_bridge_command or
  acp_status_json_and_human"` (`36 passed`), `ruff check
  src\openzues\services\acp_commands.py tests\test_acp_commands.py`, and
  `mypy src\openzues\services\acp_commands.py`.
- Native ACP session storage now follows OpenClaw's in-memory store behavior:
  create/update by session id, touch on reads, index active runs, clear or
  cancel active runs, abort on cancel/removal, reap idle sessions, evict the
  oldest idle session, and fail closed when all sessions are active at the
  configured limit.
- Verified the ACP session-store slice with `python -m pytest
  tests\test_acp_session_store.py -q` (`5 passed`), adjacent ACP support proof
  `python -m pytest tests\test_acp_session_store.py tests\test_acp_commands.py
  tests\test_acp_session_mapper.py tests\test_acp_event_mapper.py
  tests\test_acp_client_runtime.py tests\test_cli.py -q -k
  "acp_session_store or acp_available_commands or acp_session_mapper or
  acp_event_mapper or acp_permission or acp_client or acp_bridge_command or
  acp_status_json_and_human"` (`41 passed`), `ruff check
  src\openzues\services\acp_session_store.py tests\test_acp_session_store.py`,
  and `mypy src\openzues\services\acp_session_store.py`.
- Native ACP prompt request assembly now follows OpenClaw's translator prompt
  send contract for cwd prefixing, home redaction with Windows separator
  preservation, prompt attachment forwarding, `_meta` thinking/deliver/timeout
  options, and system provenance metadata/receipt construction.
- Verified the ACP translator prompt-send slice with `python -m pytest
  tests\test_acp_translator.py -q` (`4 passed`), adjacent ACP support proof
  `python -m pytest tests\test_acp_translator.py tests\test_acp_session_store.py
  tests\test_acp_commands.py tests\test_acp_session_mapper.py
  tests\test_acp_event_mapper.py tests\test_acp_client_runtime.py tests\test_cli.py
  -q -k "acp_translator or acp_session_store or acp_available_commands or
  acp_session_mapper or acp_event_mapper or acp_permission or acp_client or
  acp_bridge_command or acp_status_json_and_human"` (`45 passed`), `ruff check
  src\openzues\services\acp_translator.py tests\test_acp_translator.py`, and
  `mypy src\openzues\services\acp_translator.py`.
- Native `AcpGatewayAgent` lifecycle now covers OpenClaw's ACP
  `initialize`, `newSession`, and `loadSession` bridge behavior: advertised
  load/prompt/MCP/session-list capabilities, session store materialization via
  session meta, gateway-backed session presentation snapshots, usage updates,
  transcript replay for user/assistant/thinking text, and available command
  updates.
- Verified the ACP agent lifecycle-foundation slice with `python -m pytest
  tests\test_acp_agent.py -q` (`3 passed`), adjacent ACP support proof
  `python -m pytest tests\test_acp_agent.py tests\test_acp_translator.py
  tests\test_acp_session_store.py tests\test_acp_commands.py
  tests\test_acp_session_mapper.py tests\test_acp_event_mapper.py
  tests\test_acp_client_runtime.py tests\test_cli.py -q -k
  "acp_gateway_agent or acp_translator or acp_session_store or
  acp_available_commands or acp_session_mapper or acp_event_mapper or
  acp_permission or acp_client or acp_bridge_command or
  acp_status_json_and_human"` (`48 passed`), `ruff check
  src\openzues\services\acp_agent.py tests\test_acp_agent.py`, and `mypy
  src\openzues\services\acp_agent.py`.
- Native `AcpGatewayAgent.prompt` now follows OpenClaw's prompt lifecycle for
  gateway `chat.send` dispatch, active-run tracking, chat delta projection into
  assistant text/thinking ACP chunks, terminal chat-event stop reason mapping,
  session snapshot refresh on finish, and `cancel` scoping through
  `chat.abort`.
- Verified the ACP agent prompt/cancel slice with `python -m pytest
  tests\test_acp_agent.py -q` (`6 passed`), adjacent ACP support proof
  `python -m pytest tests\test_acp_agent.py tests\test_acp_translator.py
  tests\test_acp_session_store.py tests\test_acp_commands.py
  tests\test_acp_session_mapper.py tests\test_acp_event_mapper.py
  tests\test_acp_client_runtime.py tests\test_cli.py -q -k
  "acp_gateway_agent or acp_translator or acp_session_store or
  acp_available_commands or acp_session_mapper or acp_event_mapper or
  acp_permission or acp_client or acp_bridge_command or
  acp_status_json_and_human"` (`51 passed`), `ruff check
  src\openzues\services\acp_agent.py tests\test_acp_agent.py`, and `mypy
  src\openzues\services\acp_agent.py`.
- Native `AcpGatewayAgent.handle_gateway_event` now also mirrors OpenClaw's
  gateway `agent` tool stream mapping for tool start/update/result phases,
  preserving tool ids, titles, kind inference, raw input/output, textual
  content blocks, file/media locations, and completion/failure status.
- Verified the ACP agent tool-stream slice with `python -m pytest
  tests\test_acp_agent.py -q -k "tool_call_events"` (`1 passed`), full ACP
  agent proof `python -m pytest tests\test_acp_agent.py -q` (`7 passed`),
  adjacent ACP support proof `python -m pytest tests\test_acp_agent.py
  tests\test_acp_translator.py tests\test_acp_session_store.py
  tests\test_acp_commands.py tests\test_acp_session_mapper.py
  tests\test_acp_event_mapper.py tests\test_acp_client_runtime.py
  tests\test_cli.py -q -k "acp_gateway_agent or acp_translator or
  acp_session_store or acp_available_commands or acp_session_mapper or
  acp_event_mapper or acp_permission or acp_client or acp_bridge_command or
  acp_status_json_and_human"` (`52 passed`), `ruff check
  src\openzues\services\acp_agent.py tests\test_acp_agent.py`, and `mypy
  src\openzues\services\acp_agent.py`.
- Native `AcpGatewayAgent` session controls now follow OpenClaw's ACP
  `setSessionMode` and `setSessionConfigOption` behavior: mode changes patch
  `thinkingLevel`, config ids map to the corresponding `sessions.patch`
  fields, non-string config values fail closed, and ACP current-mode/config
  updates refresh from the gateway snapshot after each patch.
- Verified the ACP agent session-control slice with `python -m pytest
  tests\test_acp_agent.py -q -k "set_session"` (`2 passed`), full ACP agent
  proof `python -m pytest tests\test_acp_agent.py -q` (`9 passed`), adjacent
  ACP support proof `python -m pytest tests\test_acp_agent.py
  tests\test_acp_translator.py tests\test_acp_session_store.py
  tests\test_acp_commands.py tests\test_acp_session_mapper.py
  tests\test_acp_event_mapper.py tests\test_acp_client_runtime.py
  tests\test_cli.py -q -k "acp_gateway_agent or acp_translator or
  acp_session_store or acp_available_commands or acp_session_mapper or
  acp_event_mapper or acp_permission or acp_client or acp_bridge_command or
  acp_status_json_and_human"` (`54 passed`), `ruff check
  src\openzues\services\acp_agent.py tests\test_acp_agent.py`, and `mypy
  src\openzues\services\acp_agent.py`.
- Native `AcpGatewayAgent` now enforces OpenClaw's fixed-window ACP session
  creation rate limit for `newSession` and new `loadSession` ids while keeping
  existing `loadSession` refreshes outside the budget.
- Verified the ACP agent session-rate-limit slice with `python -m pytest
  tests\test_acp_agent.py -q -k "rate_limit"` (`2 passed`), full ACP agent
  proof `python -m pytest tests\test_acp_agent.py -q` (`11 passed`), adjacent
  ACP support proof `python -m pytest tests\test_acp_agent.py
  tests\test_acp_translator.py tests\test_acp_session_store.py
  tests\test_acp_commands.py tests\test_acp_session_mapper.py
  tests\test_acp_event_mapper.py tests\test_acp_client_runtime.py
  tests\test_cli.py -q -k "acp_gateway_agent or acp_translator or
  acp_session_store or acp_available_commands or acp_session_mapper or
  acp_event_mapper or acp_permission or acp_client or acp_bridge_command or
  acp_status_json_and_human"` (`56 passed`), `ruff check
  src\openzues\services\acp_agent.py tests\test_acp_agent.py`, and `mypy
  src\openzues\services\acp_agent.py`.
- Native `AcpGatewayAgent.prompt` now mirrors OpenClaw's admin-scope
  provenance fallback: when gateway `chat.send` rejects
  `systemInputProvenance` / `systemProvenanceReceipt` with the upstream
  `INVALID_REQUEST` shape, the prompt retries without those fields while
  keeping the same active run and pending ACP prompt.
- Verified the ACP prompt provenance fallback slice with `python -m pytest
  tests\test_acp_agent.py -q -k "provenance"` (`1 passed`), full ACP agent
  proof `python -m pytest tests\test_acp_agent.py -q` (`12 passed`), adjacent
  ACP support proof `python -m pytest tests\test_acp_agent.py
  tests\test_acp_translator.py tests\test_acp_session_store.py
  tests\test_acp_commands.py tests\test_acp_session_mapper.py
  tests\test_acp_event_mapper.py tests\test_acp_client_runtime.py
  tests\test_cli.py -q -k "acp_gateway_agent or acp_translator or
  acp_session_store or acp_available_commands or acp_session_mapper or
  acp_event_mapper or acp_permission or acp_client or acp_bridge_command or
  acp_status_json_and_human"` (`57 passed`), `ruff check
  src\openzues\services\acp_agent.py tests\test_acp_agent.py`, and `mypy
  src\openzues\services\acp_agent.py`.
- Native `AcpGatewayAgent` reconnect handling now covers OpenClaw's missed-final
  reconciliation for accepted prompts: reconnect clears the disconnect posture,
  rechecks each accepted pending run with `agent.wait timeoutMs=0`, and resolves
  the ACP prompt as `end_turn` when the gateway reports completion.
- Verified the ACP reconnect reconciliation slice with `python -m pytest
  tests\test_acp_agent.py -q -k "reconnect"` (`1 passed`), full ACP agent proof
  `python -m pytest tests\test_acp_agent.py -q` (`13 passed`), adjacent ACP
  support proof `python -m pytest tests\test_acp_agent.py
  tests\test_acp_translator.py tests\test_acp_session_store.py
  tests\test_acp_commands.py tests\test_acp_session_mapper.py
  tests\test_acp_event_mapper.py tests\test_acp_client_runtime.py
  tests\test_cli.py -q -k "acp_gateway_agent or acp_translator or
  acp_session_store or acp_available_commands or acp_session_mapper or
  acp_event_mapper or acp_permission or acp_client or acp_bridge_command or
  acp_status_json_and_human"` (`58 passed`), `ruff check
  src\openzues\services\acp_agent.py tests\test_acp_agent.py`, and `mypy
  src\openzues\services\acp_agent.py`.
- The top-level `openzues acp` command now has a native fakeable bridge-runner
  seam matching the existing ACP client runner path: resolved gateway URL,
  token/password sources, default session key/label, require/reset posture,
  cwd-prefix, provenance mode, and verbosity are passed to the registered
  runner before the legacy unavailable fallback is emitted.
- Verified the ACP bridge runner CLI slice with `python -m pytest
  tests\test_cli.py -q -k "acp_bridge_command"` (`4 passed`), adjacent ACP CLI
  and support proof `python -m pytest tests\test_cli.py tests\test_acp_agent.py
  tests\test_acp_translator.py tests\test_acp_session_store.py
  tests\test_acp_commands.py tests\test_acp_session_mapper.py
  tests\test_acp_event_mapper.py tests\test_acp_client_runtime.py -q -k
  "acp_bridge_command or acp_client_command or acp_status_json_and_human or
  acp_client_spawn_plan or acp_client_spawn_invocation or acp_gateway_agent or
  acp_translator or acp_session_store or acp_available_commands or
  acp_session_mapper or acp_event_mapper or acp_permission"` (`59 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Saved failed provider-backed `gateway/send` and `gateway/poll` replay now
  preserves OpenClaw's delivery-queue recovery context by forwarding stored
  `gatewayClientScopes`, requester session, requester account, and requester
  sender metadata back into the native outbound runtime request.
- Verified the provider replay context slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "retries_saved_failed_gateway_send_via_provider_runtime
  or retries_saved_failed_gateway_poll_via_provider_runtime"` (`2 passed`),
  adjacent OpsMesh outbound proof `python -m pytest tests\test_ops_mesh.py -q
  -k "replay_outbound_deliveries or direct_send or direct_channel or
  provider_result or gateway_poll or gateway_send"` (`62 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Provider-backed `gateway/send` replay now also preserves the explicit
  source-session runtime context saved by the first delivery attempt:
  `sourceSessionKey` / `runtime_session_key` drives native runtime dispatch
  while the announce delivery row remains attached to the channel-derived
  history session.
- Verified the provider replay source-session slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "retries_saved_failed_gateway_send_via_provider_runtime"`
  (`1 passed`), adjacent OpsMesh outbound proof `python -m pytest
  tests\test_ops_mesh.py -q -k "replay_outbound_deliveries or direct_send or
  direct_channel or provider_result or gateway_poll or gateway_send"` (`62
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Matrix route-backed `message.action edit` / `editMessage` now maps to
  OpenClaw-shaped `m.replace` replacement events, including `m.new_content`,
  replacement body prefixing, optional thread reply metadata, route token auth,
  and idempotency-key transaction ids.
- Verified the Matrix edit action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_edit_route"` (`1 passed`), adjacent
  action/provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_send_route or matrix_native_route or
  message_action_dispatches_discord_edit_route or
  message_action_dispatches_slack_edit_route or
  message_action_dispatches_zalo_send_route"` (`7 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix route-backed `message.action delete` / `deleteMessage` now maps to
  OpenClaw's `redactEvent` behavior through Matrix Client-Server `redact`
  requests, preserving optional reason payloads, route token auth, and
  idempotency-key transaction ids while returning `{ok:true, deleted:true}`.
- Verified the Matrix delete action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_delete_route"` (`1 passed`), adjacent
  action/provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_send_route or matrix_native_route or
  message_action_dispatches_discord_delete_route or
  message_action_dispatches_slack_delete_route"` (`7 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix route-backed reaction-add parity now maps `message.action react`
  through OpenClaw's `m.reaction` / `m.annotation` send shape, preserving route
  token auth, idempotency-key transaction ids, and `{ok:true, added:<emoji>}`
  action results.
- Verified the Matrix reaction-add slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_react_route"` (`1 passed`), adjacent
  action/provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_send_route or matrix_native_route or
  message_action_dispatches_discord_react_route or
  message_action_dispatches_slack_react_route or
  message_action_dispatches_telegram_react_route"` (`9 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix route-backed reaction remove/list parity now uses OpenClaw's relation
  history path: `message.action reactions` summarizes v1 relation chunks by key
  and unique sender, while `message.action react remove=true` resolves the bot
  through Matrix `whoami` and redacts only matching current-user reaction events.
- Verified the Matrix reaction remove/list slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_reactions_list_route or
  matrix_react_remove_route or matrix_react_route"` (`3 passed`), adjacent
  action/provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_send_route or matrix_native_route or
  message_action_dispatches_discord_reactions_list_route or
  message_action_dispatches_slack_reactions_list_route or
  message_action_dispatches_discord_react_remove_route or
  message_action_dispatches_slack_react_remove_route"` (`12 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix route-backed pin action parity now uses OpenClaw's
  `m.room.pinned_events` state behavior for `pinMessage`, `unpinMessage`, and
  `listPins`, including idempotent pin append, targeted unpin filtering, and
  pinned-event summaries for resolvable message events.
- Verified the Matrix pin action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_pin_mutation_route or
  matrix_list_pins_route"` (`3 passed`), adjacent action/provider proof
  `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_send_route or matrix_native_route or
  message_action_dispatches_discord_pin_mutation_route or
  message_action_dispatches_discord_list_pins_route or
  message_action_dispatches_slack_pin_route or
  message_action_dispatches_slack_unpin_route or
  message_action_dispatches_slack_list_pins_route"` (`17 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix route-backed `readMessages` action parity now uses OpenClaw's room
  history endpoint shape, including backward/forward cursor direction,
  bounded limits, optional `before` / `after` tokens, redaction filtering,
  message summaries, and `nextBatch` / `prevBatch` projection.
- Verified the Matrix read action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_read_messages_route"` (`1 passed`),
  adjacent action/provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_send_route or matrix_native_route or
  message_action_dispatches_discord_read_route or
  message_action_dispatches_slack_read_route or
  message_action_dispatches_slack_thread_read_route"` (`15 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix route-backed member/room probe parity now covers `memberInfo` and
  `channelInfo` with OpenClaw-shaped profile projection, room name/topic/canonical
  alias state reads, joined-member counts, and null membership/power-level fields.
- Verified the Matrix member/channel probe slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_member_info_route or
  matrix_channel_info_route"` (`2 passed`), adjacent action/provider proof
  `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_send_route or matrix_native_route or
  message_action_dispatches_discord_member_info_route or
  message_action_dispatches_discord_channel_info_route"` (`16 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix route-backed unencrypted media-send parity now uploads outbound media
  through the Matrix media repository, sends `m.image` / `m.video` / `m.audio` /
  `m.file` room messages with MXC URLs, caption text, relation metadata,
  mimetype/size info, and persisted media delivery metadata.
- Verified the Matrix media send slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_native_route and media"` (`1 passed`),
  adjacent Matrix route/action proof `python -m pytest tests\test_ops_mesh.py -q
  -k "matrix_native_route or message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route"` (`15 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix route-backed alias resolution now calls the Matrix directory endpoint
  for `#room:server` targets before native send/poll delivery, so provider
  results and room send endpoints use the resolved room id instead of the alias.
- Verified the Matrix alias-resolution slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_native_route and alias"` (`1 passed`),
  adjacent Matrix route/action proof `python -m pytest tests\test_ops_mesh.py -q
  -k "matrix_native_route or message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route"` (`16 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix direct-user routing now classifies `user:` / `matrix:user:` targets as
  direct peers and resolves the first OpenClaw direct-room path through Matrix
  `whoami`, `m.direct` account data, and strict two-member joined-room
  validation before native delivery.
- Verified the Matrix direct-room slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_direct_room"` (`1 passed`), adjacent
  Matrix route/action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "matrix_native_route or matrix_direct_room or
  message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route"` (`17 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix direct-user fallback now follows OpenClaw's joined-room repair path:
  stale or missing `m.direct` mappings fall back to joined-room inspection,
  strict two-member rooms are selected, and the primary `m.direct` account-data
  mapping is persisted before native delivery.
- Verified the Matrix direct-room fallback slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_direct_room"` (`2 passed`), adjacent
  Matrix route/action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "matrix_native_route or matrix_direct_room or
  message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route"` (`18 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix route-backed self-profile parity now covers `message.action
  setProfile`: Matrix `whoami` resolves the bot user, current profile reads
  suppress no-op writes, `displayname` / `avatar_url` profile PUTs update the
  live account, HTTP avatar URLs convert through Matrix media upload, and the
  native config owner persists `name` / `avatarUrl` under
  `channels.matrix.accounts.<accountId>`.
- Verified the Matrix profile slice with `python -m pytest tests\test_ops_mesh.py
  -q -k "matrix_set_profile"` (`2 passed`), adjacent Matrix route/action proof
  `python -m pytest tests\test_ops_mesh.py -q -k "matrix_native_route or
  matrix_direct_room or message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route or matrix_set_profile"`
  (`20 passed`), `ruff check src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_config.py src\openzues\app.py src\openzues\cli.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_config.py`.
- Matrix route-backed image media sends now add OpenClaw-style dimensional media
  metadata: native PNG/GIF/JPEG header parsing populates `info.w` / `info.h`
  alongside `size` and `mimetype` before sending the Matrix `m.room.message`
  media event.
- Verified the Matrix image-info slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_native_route and media"` (`1 passed`),
  adjacent Matrix route/action proof `python -m pytest tests\test_ops_mesh.py -q
  -k "matrix_native_route or matrix_direct_room or
  message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route or matrix_set_profile"`
  (`20 passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Matrix route-backed WAV audio media sends now add OpenClaw-style
  `info.duration` metadata by parsing native RIFF/WAVE headers, preserving the
  existing Matrix `m.audio` upload and provider result path.
- Verified the Matrix audio-duration slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_audio_includes_duration or
  matrix_native_route and media"` (`2 passed`), adjacent Matrix route/action
  proof `python -m pytest tests\test_ops_mesh.py -q -k "matrix_native_route or
  matrix_direct_room or matrix_audio_includes_duration or
  message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route or matrix_set_profile"`
  (`21 passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Matrix route-backed large-image media sends now mirror OpenClaw's
  unencrypted thumbnail metadata path: Pillow-backed native resizing creates an
  800px-bounded JPEG thumbnail, uploads it through the Matrix media repository,
  and adds `thumbnail_url` / `thumbnail_info` beside the primary image
  dimensions. `Pillow>=10.0.0` is now a runtime dependency for that native
  thumbnail branch.
- Verified the Matrix thumbnail slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_large_image_uploads_thumbnail"` (`1
  passed`), adjacent Matrix route/action proof `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_native_route or matrix_direct_room or
  matrix_audio_includes_duration or matrix_large_image_uploads_thumbnail or
  message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route or matrix_set_profile"`
  (`22 passed`), `ruff check pyproject.toml
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Matrix route-backed MP4/MOV-family video media sends now add OpenClaw-style
  `info.duration` metadata by parsing native ISO-BMFF `mvhd` timing, preserving
  the existing Matrix `m.video` upload and provider result path.
- Verified the Matrix video-duration slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_video_includes_duration or
  matrix_audio_includes_duration"` (`2 passed`), adjacent Matrix route/action
  proof `python -m pytest tests\test_ops_mesh.py -q -k "matrix_native_route or
  matrix_direct_room or matrix_audio_includes_duration or
  matrix_video_includes_duration or matrix_large_image_uploads_thumbnail or
  message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route or matrix_set_profile"`
  (`23 passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Matrix route-backed encrypted media sends now mirror OpenClaw's `file` /
  `thumbnail_file` branch: room media sends opportunistically probe
  `m.room.encryption`, encrypt the main media and generated large-image
  thumbnails with native AES-CTR encrypted-file metadata, upload encrypted bytes
  as `application/octet-stream`, and omit top-level `url` /
  `info.thumbnail_url` when encrypted file payloads are present.
- Verified the Matrix encrypted-media slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_encrypted_image_uses_file_payloads or
  matrix_large_image_uploads_thumbnail or matrix_native_route and media"` (`3
  passed`), adjacent Matrix route/action proof `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_native_route or matrix_direct_room or
  matrix_audio_includes_duration or matrix_video_includes_duration or
  matrix_large_image_uploads_thumbnail or
  matrix_encrypted_image_uses_file_payloads or
  message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route or matrix_set_profile"`
  (`24 passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Matrix route-backed MP3 audio media sends now add OpenClaw-style
  `info.duration` metadata by parsing common MPEG frame headers, completing the
  Matrix media-info duration queue for WAV, MP3, and MP4/MOV-family media in
  the native OpenZues path.
- Verified the Matrix MP3-duration slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_mp3_includes_duration or
  matrix_audio_includes_duration or matrix_video_includes_duration"` (`3
  passed`), adjacent Matrix route/action proof `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_native_route or matrix_direct_room or
  matrix_audio_includes_duration or matrix_mp3_includes_duration or
  matrix_video_includes_duration or matrix_large_image_uploads_thumbnail or
  matrix_encrypted_image_uses_file_payloads or
  message_action_dispatches_matrix_send_route or
  message_action_dispatches_matrix_edit_route or
  message_action_dispatches_matrix_delete_route or
  message_action_dispatches_matrix_react_route or
  message_action_dispatches_matrix_react_remove_route or
  message_action_dispatches_matrix_reactions_list_route or
  message_action_dispatches_matrix_pin_mutation_route or
  message_action_dispatches_matrix_list_pins_route or
  message_action_dispatches_matrix_read_messages_route or
  message_action_dispatches_matrix_member_info_route or
  message_action_dispatches_matrix_channel_info_route or matrix_set_profile"`
  (`25 passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Discord route-backed thread-bound subagent spawns now mirror OpenClaw's
  provider child-thread creation path: the production binder invokes the native
  `message.action thread-create` adapter with a 60-minute auto-archive default,
  delivers the initial child run to the parent route plus created thread id, and
  persists child-placement session binding metadata for
  `channel:<createdThreadId>`. App and CLI construction wire the binder to the
  same OpsMesh message-action dispatcher used by provider actions.
- Verified the Discord child-thread binding slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "creates_discord_child_thread_with_route_binder"` (`1 passed`), adjacent
  thread-binding proof `python -m pytest tests\test_gateway_node_methods.py -q
  -k "thread_mode_preserves_no_hook_with_unresolved_registry or
  thread_mode_uses_route_backed_thread_binder or
  creates_discord_child_thread_with_route_binder or
  thread_mode_uses_matrix_route_backed_thread_binder or
  thread_mode_uses_target_agent_bound_account or
  thread_mode_requires_spawn_policy_for_child_placement or
  thread_mode_delivers_initial_child_run_to_bound_origin or
  thread_bound_subagent_startup_failure_unbinds_prepared_binding"` (`9
  passed`), `ruff check src\openzues\services\gateway_thread_binding.py
  src\openzues\services\gateway_node_methods.py src\openzues\app.py
  src\openzues\cli.py tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_thread_binding.py
  src\openzues\services\gateway_node_methods.py`.
- Matrix route-backed thread-bound subagent spawns without an existing thread id
  now mirror OpenClaw's child-placement Matrix adapter: the native binder sends
  the intro root message through `message.action send`, uses the returned event
  id as the child thread id for initial delivery/completion delivery, and
  persists a Matrix session binding with `conversationId=<event id>` and
  `parentConversationId=<room id>`.
- Verified the Matrix child-thread binding slice with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "creates_matrix_child_thread_with_route_binder"` (`1 passed`), adjacent
  thread-binding proof `python -m pytest tests\test_gateway_node_methods.py -q
  -k "thread_mode_preserves_no_hook_with_unresolved_registry or
  thread_mode_uses_route_backed_thread_binder or
  creates_discord_child_thread_with_route_binder or
  creates_matrix_child_thread_with_route_binder or
  thread_mode_uses_matrix_route_backed_thread_binder or
  thread_mode_uses_target_agent_bound_account or
  thread_mode_requires_spawn_policy_for_child_placement or
  thread_mode_delivers_initial_child_run_to_bound_origin or
  thread_bound_subagent_startup_failure_unbinds_prepared_binding"` (`10
  passed`), `ruff check src\openzues\services\gateway_thread_binding.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_thread_binding.py`.
- Completion announcement delivery now has the OpenClaw bound-delivery fallback
  for saved session bindings: when a child session has an active
  `sessionBinding` but no persisted `completionDelivery`, `agent.wait` derives a
  provider delivery target from the binding conversation, persists that derived
  route, and sends the completion announcement through the same provider channel
  delivery owner.
- Verified the session-binding completion fallback with `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "completion_falls_back_to_session_binding"` (`1 passed`), adjacent completion
  proof `python -m pytest tests\test_gateway_node_methods.py -q -k
  "agent_wait_announces_spawn_completion or
  thread_bound_completion_uses_completion_delivery_route or
  completion_falls_back_to_session_binding or no_completion_announce or
  completion_dedupe or marks_acp_task_record_succeeded"` (`4 passed`), `ruff
  check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Matrix route-backed channel account probes now mirror OpenClaw's
  `createMatrixProbeAccount` / `probeMatrix` path: native Matrix routes are
  included in the probeable provider set, `channels status --probe --json`
  calls `/_matrix/client/v3/account/whoami` with the saved route access token,
  and the account probe result exposes the Matrix user/device identity.
- Verified the Matrix account-probe slice with `python -m pytest
  tests\test_cli.py -q -k "route_backed_matrix_probe"` (`1 passed`), adjacent
  status-probe proof `python -m pytest tests\test_cli.py -q -k
  "channels_status_json_uses_route_backed_slack_probe or
  channels_status_json_uses_route_backed_telegram_probe or
  channels_status_json_uses_route_backed_discord_probe or
  channels_status_json_uses_route_backed_matrix_probe or
  channels_status_json_keeps_whatsapp_no_hook_probe_non_degraded or
  channels_status_json_accepts_probe_timeout_options"` (`6 passed`), plus
  `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- Zalo route-backed channel account probes now mirror OpenClaw's
  `probeZaloAccount` / `probeZalo` path: native Zalo routes are included in the
  probeable provider set, `channels status --probe --json` calls Bot API
  `getMe` with the saved route token, and the account probe result exposes the
  returned bot object.
- Verified the Zalo account-probe slice with `python -m pytest
  tests\test_cli.py -q -k "route_backed_zalo_probe"` (`1 passed`) and adjacent
  status-probe proof `python -m pytest tests\test_cli.py -q -k
  "channels_status_json_uses_route_backed_slack_probe or
  channels_status_json_uses_route_backed_telegram_probe or
  channels_status_json_uses_route_backed_discord_probe or
  channels_status_json_uses_route_backed_matrix_probe or
  channels_status_json_uses_route_backed_zalo_probe or
  channels_status_json_keeps_whatsapp_no_hook_probe_non_degraded or
  channels_status_json_accepts_probe_timeout_options"` (`7 passed`), plus
  `ruff check src\openzues\services\ops_mesh.py tests\test_cli.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- LINE route-backed channel account probes now mirror OpenClaw's `probeLineBot`
  path: native LINE routes are included in the probeable provider set,
  `channels status --probe --json` calls Bot API `/v2/bot/info` with the saved
  route token, and the account probe result exposes `displayName`, `userId`,
  `basicId`, and `pictureUrl` bot metadata.
- Verified the LINE account-probe slice with `python -m pytest
  tests\test_cli.py -q -k "route_backed_line_probe"` (`1 passed`) and adjacent
  status-probe proof `python -m pytest tests\test_cli.py -q -k
  "route_backed_slack_probe or route_backed_telegram_probe or
  route_backed_discord_probe or route_backed_matrix_probe or
  route_backed_zalo_probe or route_backed_line_probe or
  whatsapp_no_hook_probe_non_degraded or channels_status_probe_timeout_options"`
  (`7 passed`), plus `ruff check src\openzues\services\ops_mesh.py
  tests\test_cli.py`, and `mypy src\openzues\services\ops_mesh.py`.
- LINE route-backed direct sends now carry OpenClaw's `replyToken` send option
  through `GatewayOutboundRuntimeMessageRequest`, persist it on saved outbound
  delivery payloads for replay, and use Bot API `/v2/bot/message/reply` with
  `messageId="reply"` instead of `/push` when the token is present.
- Verified the LINE reply-token slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "line_reply_token"` (`1 passed`), adjacent
  outbound runtime proof `python -m pytest tests\test_ops_mesh.py -q -k
  "line_native_route or line_reply_token or preserves_provider_native_options
  or shared_outbound_runtime_owner or prefers_provider_runtime"` (`6 passed`),
  `ruff check src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- LINE route-backed direct sends now carry OpenClaw's explicit video media
  options through the shared outbound runtime: `mediaKind="video"` and
  `previewImageUrl` persist on saved delivery payloads and the native LINE
  adapter emits Bot API video message payloads instead of default image media.
- Verified the LINE video media slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "line_video_media_kind"` (`1 passed`), adjacent
  outbound runtime proof `python -m pytest tests\test_ops_mesh.py -q -k
  "line_native_route or line_reply_token or line_video_media_kind or
  preserves_provider_native_options or shared_outbound_runtime_owner or
  prefers_provider_runtime"` (`7 passed`), `ruff check
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- LINE route-backed video sends now also carry OpenClaw's `trackingId` option
  through `GatewayOutboundRuntimeMessageRequest`, persist it on saved outbound
  delivery payloads, and emit LINE video `trackingId` only for user chat IDs
  while omitting it for group/room destinations.
- Verified the LINE video tracking slice with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_line_video_tracking_id_for_user_target
  tests\test_ops_mesh.py::test_ops_mesh_service_line_video_tracking_id_omitted_for_group_target
  -q` (`2 passed`), adjacent LINE direct proofs `python -m pytest
  tests\test_ops_mesh.py -q -k "line_video or line_audio_duration or
  line_native"` (`5 passed`) and `python -m pytest tests\test_ops_mesh.py -q
  -k "direct_channel_message and line"` (`10 passed`), `ruff check
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- LINE route-backed direct sends now carry OpenClaw's explicit audio media
  options through the shared outbound runtime: `mediaKind="audio"` and
  `durationMs` persist on saved delivery payloads and the native LINE adapter
  emits Bot API audio message payloads with the requested duration.
- Verified the LINE audio media slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "line_audio_duration"` (`1 passed`), adjacent
  outbound runtime proof `python -m pytest tests\test_ops_mesh.py -q -k
  "line_native_route or line_reply_token or line_video_media_kind or
  line_audio_duration or preserves_provider_native_options or
  shared_outbound_runtime_owner or prefers_provider_runtime"` (`8 passed`),
  `ruff check src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- LINE route-backed direct sends now carry OpenClaw's structured location
  payload through the shared outbound runtime, allow location-only sends, keep
  location payloads replayable, and emit Bot API location messages with
  title/address truncation plus latitude/longitude preservation.
- Verified the LINE location slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "line_location"` (`1 passed`), adjacent outbound
  runtime proof `python -m pytest tests\test_ops_mesh.py -q -k
  "line_native_route or line_reply_token or line_video_media_kind or
  line_audio_duration or line_location or preserves_provider_native_options or
  shared_outbound_runtime_owner or prefers_provider_runtime"` (`9 passed`),
  `ruff check src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- LINE route-backed direct sends now carry OpenClaw's `quickReplies` through the
  shared outbound runtime and attach LINE `quickReply` action items to the final
  outgoing message, preserving the upstream 13-item cap and 20-character label
  truncation while storing the source labels on the delivery payload.
- Verified the LINE quick-replies slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "line_quick_replies"` (`1 passed`), adjacent
  outbound runtime proof `python -m pytest tests\test_ops_mesh.py -q -k
  "line_native_route or line_reply_token or line_video_media_kind or
  line_audio_duration or line_location or line_quick_replies or
  preserves_provider_native_options or shared_outbound_runtime_owner or
  prefers_provider_runtime"` (`10 passed`), `ruff check
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- LINE route-backed direct sends now carry OpenClaw's `flexMessage` through the
  shared outbound runtime, keep the payload replayable, emit Bot API Flex
  messages with the upstream 400-character `altText` boundary, preserve
  `contents`, and leave companion text sends intact.
- Verified the LINE Flex slice with `python -m pytest tests\test_ops_mesh.py
  -q -k "line_flex_message"` (`1 passed`), adjacent outbound runtime proof
  `python -m pytest tests\test_ops_mesh.py -q -k "line_native_route or
  line_reply_token or line_video_media_kind or line_audio_duration or
  line_location or line_quick_replies or line_flex_message or
  preserves_provider_native_options or shared_outbound_runtime_owner or
  prefers_provider_runtime"` (`11 passed`), `ruff check
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- LINE route-backed direct sends now carry OpenClaw's confirm
  `templateMessage` through the shared outbound runtime, keep the payload
  replayable, map confirm/cancel data to URI, postback, or message actions, and
  emit Bot API confirm templates before companion text sends while enforcing
  OpenClaw/LINE truncation boundaries.
- Verified the LINE confirm-template slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "line_confirm_template"` (`1 passed`),
  adjacent outbound runtime proof `python -m pytest tests\test_ops_mesh.py -q
  -k "line_native_route or line_reply_token or line_video_media_kind or
  line_audio_duration or line_location or line_quick_replies or
  line_flex_message or line_confirm_template or preserves_provider_native_options
  or shared_outbound_runtime_owner or prefers_provider_runtime"` (`12 passed`),
  `ruff check src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- LINE route-backed direct sends now carry OpenClaw's buttons
  `templateMessage` through the shared outbound runtime, preserve source
  actions for replay, emit Bot API buttons templates with title/text/action
  truncation, default image layout options, optional thumbnails, and
  URI/postback/message action mapping before companion text sends.
- Verified the LINE buttons-template slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "line_buttons_template"` (`1 passed`),
  adjacent outbound runtime proof `python -m pytest tests\test_ops_mesh.py -q
  -k "line_native_route or line_reply_token or line_video_media_kind or
  line_audio_duration or line_location or line_quick_replies or
  line_flex_message or line_confirm_template or line_buttons_template or
  preserves_provider_native_options or shared_outbound_runtime_owner or
  prefers_provider_runtime"` (`13 passed`), `ruff check
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- LINE route-backed direct sends now carry OpenClaw's carousel
  `templateMessage` through the shared outbound runtime, preserve source
  columns/actions for replay, emit Bot API carousel templates with the upstream
  10-column and 3-action-per-column boundaries, title/text truncation, optional
  thumbnails, default image layout options, and URI/postback/message action
  mapping before companion text sends.
- Verified the LINE carousel-template slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "line_carousel_template"` (`1 passed`),
  adjacent outbound runtime proof `python -m pytest tests\test_ops_mesh.py -q
  -k "line_native_route or line_reply_token or line_video_media_kind or
  line_audio_duration or line_location or line_quick_replies or
  line_flex_message or line_confirm_template or line_buttons_template or
  line_carousel_template or preserves_provider_native_options or
  shared_outbound_runtime_owner or prefers_provider_runtime"` (`14 passed`),
  `ruff check src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py tests\test_ops_mesh.py`,
  and `mypy src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_outbound_runtime.py`.
- Telegram `message.action delete` / `deleteMessage` now dispatches through
  the native Bot API `deleteMessage` route with OpenClaw's chat-id aliases and
  returns the upstream-shaped `{ ok: true, deleted: true }` envelope.
- Verified the Telegram delete action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_delete_route"` (`1 passed`),
  adjacent Telegram action proofs `python -m pytest tests\test_ops_mesh.py -q
  -k "message_action_dispatches_telegram"` and `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram and message_action"` (`6 passed`
  each), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Telegram `message.action edit` / `editMessage` now dispatches through the
  native Bot API `editMessageText` route with OpenClaw's chat/content aliases,
  treats "message is not modified" as success, and returns the upstream-shaped
  top-level `messageId` / `chatId` result.
- Verified the Telegram edit action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_edit_route"` (`1 passed`), adjacent
  Telegram action proofs `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_telegram"` and `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram and message_action"` (`7 passed`
  each), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Telegram `message.action topic-create` / `createForumTopic` and
  `topic-edit` / `editForumTopic` now dispatch through the native Bot API forum
  topic routes, including base-chat normalization for topic-qualified targets,
  supported icon-color validation, custom icon emoji forwarding, and
  OpenClaw-shaped topic result envelopes.
- Verified the Telegram forum-topic action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_topic_create_route or
  telegram_topic_edit_route"` (`2 passed`), adjacent Telegram action proofs
  `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_telegram"` and `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram and message_action"` (`9 passed`
  each), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Matrix `message.action poll-vote` now dispatches through the native Matrix
  route path: it fetches the poll start event, resolves option ids and 1-based
  option indexes against the poll definition, enforces `max_selections`, sends
  `m.poll.response`, and returns OpenClaw-shaped answer metadata.
- Verified the Matrix poll-vote action slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_poll_vote_route"` (`1 passed`),
  adjacent Matrix action proofs `python -m pytest tests\test_ops_mesh.py -q -k
  "message_action_dispatches_matrix"` (`14 passed`) and `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix and message_action"` (`15 passed`),
  `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and
  `mypy src\openzues\services\ops_mesh.py`.
- Telegram direct sends now preserve OpenClaw's `channelData.telegram.pin`
  through gateway `send`, `GatewayOutboundRuntimeMessageRequest`, OpsMesh saved
  delivery payloads, and native Bot API route sends. The Telegram route-backed
  sender pins the first delivered message via `pinChatMessage` with
  `disable_notification=true`, and pin failures are logged as best-effort
  follow-up failures without changing the original delivery to failed.
- Verified the Telegram pin-on-delivery slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "pins_telegram_first_delivery or
  keeps_delivery_when_telegram_pin_fails"` (`2 passed`), `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "send_preserves_provider_native_reply_thread_and_document_options"` (`1
  passed`), adjacent send proofs `python -m pytest tests\test_ops_mesh.py -q -k
  "telegram_native_route or telegram_native_options or telegram_topic or
  telegram_media_group or pins_telegram_first_delivery or
  keeps_delivery_when_telegram_pin_fails"` (`11 passed`) and `python -m pytest
  tests\test_gateway_node_methods.py -q -k "send_preserves_provider_native_reply_thread_and_document_options
  or send_endpoint or direct_channel or send_uses"` (`7 passed`), `ruff check
  src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_node_methods.py tests\test_ops_mesh.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_outbound_runtime.py
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_node_methods.py`.
- Telegram direct sends now map OpenClaw's `channelData.telegram.buttons` to
  Bot API `reply_markup.inline_keyboard`, filtering button rows down to entries
  with `text` and `callback_data`, preserving optional `style`, attaching
  buttons to text sends, and attaching them only to the first media send.
- Verified the Telegram inline-buttons slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "forwards_telegram_buttons"` (`1 failed`
  before implementation, missing `reply_markup`), then `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_buttons"` (`2 passed`), adjacent
  Telegram send proof `python -m pytest tests\test_ops_mesh.py -q -k
  "telegram_native_route or telegram_native_options or telegram_topic or
  telegram_media_group or telegram_buttons or telegram_pin"` (`12 passed`),
  `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and
  `mypy src\openzues\services\ops_mesh.py`.
- Telegram `message.action send` now maps OpenClaw's action-level `buttons`
  parameter to native Bot API `reply_markup.inline_keyboard`, preserving
  callback data and optional styles while rejecting malformed rows/buttons,
  callback data over 64 UTF-8 bytes, and unsupported styles before dispatch.
- Verified the Telegram action-buttons slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_send_buttons"` (`1 failed` before
  implementation, missing `reply_markup`), then `python -m pytest
  tests\test_ops_mesh.py -q -k "telegram_send_buttons"` (`1 passed`),
  adjacent Telegram action proof `python -m pytest tests\test_ops_mesh.py -q
  -k "telegram_send_buttons or
  message_action_dispatches_telegram_send_document_alias or
  message_action_dispatches_telegram"` (`10 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- `sessions.send` follow-ups to completed child subagent sessions now mirror
  OpenClaw's `reactivateCompletedSubagentSession` path: a new started run
  replaces the completed task record's `runId` / `sourceId`, clears terminal
  fields, restores running lifecycle metadata, preserves the resolved timeout,
  and publishes `sessions.changed` after subscribers can observe the running
  child state.
- Verified the completed-child follow-up reactivation slice with `python -m
  pytest
  tests\test_gateway_node_methods.py::test_sessions_send_reactivates_completed_child_before_changed_event
  -q` (`1 failed` before implementation, child metadata still `done` on
  `run-old`), then the same command (`1 passed`), adjacent `sessions.send`
  proof `python -m pytest tests\test_gateway_node_methods.py -q -k
  "sessions_send_reactivates_completed_child or
  sessions_send_started_ack_attaches_pending_message_seq or
  sessions_send_publishes_openclaw_sessions_changed_gateway_event"` (`3
  passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Top-level `doctor --json` now includes an OpenClaw-shaped
  `doctor:gateway-runtime` contribution for service-audit rows that need Node
  runtime migration. The native probe reports too-old system Node with the
  upstream `below the required Node 22.14+` warning, reports missing system
  Node with the upstream Node 22 LTS / Node 24 guidance, and promotes the
  warning text into the top-level doctor warnings list.
- Verified the gateway-runtime Node doctor slice with `python -m pytest
  tests\test_cli.py -q -k "gateway_runtime_node"` (`2 failed` before
  implementation, missing `gatewayRuntime`), then the same command (`2
  passed`), adjacent doctor proof `python -m pytest tests\test_cli.py -q -k
  "gateway_runtime_node or gateway_mode_is_unset or
  gateway_auth_missing_local_token or
  doctor_and_update_status_json_include_hermes_sections"` (`5 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Matrix `message.action read` now matches OpenClaw's public Matrix action
  adapter by routing to the existing native `readMessages` room-history
  implementation with the same `roomId`, bounded `limit`, `before`, and
  `after` handling.
- Verified the Matrix read alias slice with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_message_action_dispatches_matrix_read_alias_route
  -q` (`1 failed` before implementation, `read` returned `None`), then the
  same command (`1 passed`), adjacent Matrix read proof `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_read_alias_route or
  matrix_read_messages_route or message_action_dispatches_matrix_read"` (`2
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Matrix `message.action pin`, `unpin`, and `list-pins` now match OpenClaw's
  public Matrix action adapter by routing to the existing native
  `pinMessage`, `unpinMessage`, and `listPins` room pin-state implementations.
- Verified the Matrix pin alias slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_pin_mutation_route or
  matrix_list_pins_route"` (`3 failed` before implementation for `pin`,
  `unpin`, and `list-pins`; internal names still passed), then the same command
  (`6 passed`), adjacent Matrix alias proof `python -m pytest
  tests\test_ops_mesh.py -q -k "matrix_pin_mutation_route or
  matrix_list_pins_route or matrix_read_alias_route"` (`7 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- BlueBubbles/iMessage `message.action unsend` now follows OpenClaw's
  BlueBubbles action adapter by accepting the public `imessage` gateway
  channel, resolving a route-backed `bluebubbles` provider account, and
  sending `POST /api/v1/message/{messageId}/unsend` with `partIndex` through
  OpenZues' native provider HTTP adapter.
- Verified the BlueBubbles unsend slice with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_message_action_dispatches_bluebubbles_unsend_route
  -q` (`1 failed` before implementation, action returned `None`), then the
  same command (`1 passed`), gateway channel proof `python -m pytest
  tests\test_gateway_node_methods.py::test_message_action_dispatches_imessage_native_action_runtime
  -q` (`1 failed` before implementation, unsupported `imessage` channel), then
  the same command (`1 passed`), adjacent message-action proofs `python -m
  pytest tests\test_ops_mesh.py -q -k "bluebubbles_unsend_route or
  message_action_dispatches_zalo_send_route or
  message_action_dispatches_matrix_read_alias_route"` (`3 passed`) and `python
  -m pytest tests\test_gateway_node_methods.py -q -k "imessage_native_action
  or message_action_dispatches_registered_native_action_runtime or
  message_action_dispatches_zalo_send_runtime"` (`3 passed`), `ruff check
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py
  tests\test_ops_mesh.py tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\ops_mesh.py
  src\openzues\services\gateway_node_methods.py src\openzues\schemas.py`.
- BlueBubbles/iMessage `message.action edit` now follows OpenClaw's
  BlueBubbles action adapter by routing `messageId` plus `text` / `newText` /
  `message`, `partIndex`, and `backwardsCompatMessage` to
  `POST /api/v1/message/{messageId}/edit`, preserving the OpenClaw-shaped
  `{ ok: true, edited: rawMessageId }` result.
- Verified the BlueBubbles edit slice with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_message_action_dispatches_bluebubbles_edit_route
  -q` (`1 failed` before implementation, action returned `None`), then the
  same command (`1 passed`), adjacent message-action proof `python -m pytest
  tests\test_ops_mesh.py -q -k "bluebubbles_edit_route or
  bluebubbles_unsend_route or message_action_dispatches_zalo_send_route or
  message_action_dispatches_matrix_read_alias_route"` (`4 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- BlueBubbles/iMessage `message.action react` now follows OpenClaw's
  BlueBubbles action adapter by routing `messageId`, `emoji`, `remove`,
  `partIndex`, and direct `chatGuid` / `chat_guid` targets to
  `POST /api/v1/message/react`, normalizing tapbacks to BlueBubbles reaction
  names and preserving the OpenClaw-shaped add/remove results.
- Verified the BlueBubbles reaction slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "bluebubbles_react_route or
  bluebubbles_remove_reaction_route"` (`2 failed` before implementation,
  actions returned `None`), then the same command (`2 passed`), adjacent
  message-action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "bluebubbles_react_route or bluebubbles_remove_reaction_route or
  bluebubbles_edit_route or bluebubbles_unsend_route"` (`4 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- BlueBubbles/iMessage `message.action reply` and `sendWithEffect` now follow
  OpenClaw's BlueBubbles send adapter by routing reply text, `messageId`,
  `partIndex`, target chat GUIDs, and short effect aliases through
  `POST /api/v1/message/text`, using Private API method payloads, temp GUIDs,
  and upstream-shaped `messageId`, `repliedTo`, and `effect` results.
- Verified the BlueBubbles reply/effect slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "bluebubbles_reply_route or
  bluebubbles_send_with_effect_route"` (`2 failed` before implementation,
  actions returned `None`), then the same command (`2 passed`), adjacent
  message-action proof `python -m pytest tests\test_ops_mesh.py -q -k
  "bluebubbles_reply_route or bluebubbles_send_with_effect_route or
  bluebubbles_react_route or bluebubbles_remove_reaction_route or
  bluebubbles_edit_route or bluebubbles_unsend_route"` (`6 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- BlueBubbles/iMessage group-management actions now follow OpenClaw's
  BlueBubbles chat adapter by routing `renameGroup`, `addParticipant`,
  `removeParticipant`, and `leaveGroup` through the native route-backed
  `/api/v1/chat/{chatGuid}` API with the upstream HTTP methods and result
  fields.
- Verified the BlueBubbles group-management slice with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_message_action_dispatches_bluebubbles_group_management_routes
  -q` (`1 failed` before implementation, action returned `None`), then the
  same command (`1 passed`), adjacent message-action proof `python -m pytest
  tests\test_ops_mesh.py -q -k "bluebubbles_group_management_routes or
  bluebubbles_reply_route or bluebubbles_send_with_effect_route or
  bluebubbles_react_route or bluebubbles_remove_reaction_route or
  bluebubbles_edit_route or bluebubbles_unsend_route"` (`7 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- BlueBubbles/iMessage media actions now follow OpenClaw's BlueBubbles
  attachment and group-icon adapters by routing `upload-file`, legacy
  `sendAttachment`, and `setGroupIcon` through multipart/form-data requests
  with decoded base64 buffers, filenames, content types, captions, temp GUIDs,
  and upstream-shaped message/icon results.
- Verified the BlueBubbles media/icon slice with `python -m pytest
  tests\test_ops_mesh.py -q -k "bluebubbles_upload_file_route or
  bluebubbles_set_group_icon_route"` (`2 failed` before implementation,
  actions returned `None`), then the same command (`2 passed`), adjacent
  BlueBubbles proof `python -m pytest tests\test_ops_mesh.py -q -k
  "bluebubbles_"` (`9 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- BlueBubbles/iMessage outbound text sends now participate in the shared
  route-backed provider runtime: `kind="bluebubbles"` routes are selected for
  `gateway.send`, direct `chat_guid` targets post to
  `POST /api/v1/message/text`, and native message id/chat metadata returns
  through `send_direct_channel_message` and saved outbound deliveries.
- Verified the BlueBubbles outbound text-send slice with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_bluebubbles_native_route
  -q` (`1 failed` before implementation, no provider route was subscribed),
  then the same command (`1 passed`), adjacent BlueBubbles proof `python -m
  pytest tests\test_ops_mesh.py -q -k "bluebubbles_"` (`10 passed`), `ruff
  check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- BlueBubbles/iMessage outbound media sends now follow OpenClaw's channel
  runtime by routing `gateway.send` media payloads through
  `POST /api/v1/message/attachment`, downloading media through a fakeable
  native helper, preserving reply threading fields, sending the leading
  caption as a follow-up BlueBubbles text message, and returning attachment
  ids, media ids, media URLs, and saved provider metadata.
- Verified the BlueBubbles outbound media-send slice with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_bluebubbles_native_media_route
  -q` (`1 failed` before implementation, media sends returned the caption
  text id and skipped the attachment endpoint), then the same command (`1
  passed`), adjacent BlueBubbles proof `python -m pytest tests\test_ops_mesh.py
  -q -k "bluebubbles_"` (`11 passed`), `ruff check
  src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
  src\openzues\services\ops_mesh.py`.
- BlueBubbles/iMessage outbound voice media now follows OpenClaw's attachment
  guard: `audioAsVoice=true` rejects non-audio media before upload, accepts
  only MP3/CAF voice media, normalizes valid voice filenames/content types,
  and keeps `isAudioMessage` scoped to valid native multipart sends.
- Verified the BlueBubbles outbound voice-media hardening slice with `python
  -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_rejects_bluebubbles_voice_non_audio
  -q` (`1 failed` before implementation, PNG media uploaded with
  `isAudioMessage`), then the same command (`1 passed`), adjacent BlueBubbles
  proof `python -m pytest tests\test_ops_mesh.py -q -k "bluebubbles_"` (`12
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- BlueBubbles/iMessage local outbound media now follows OpenClaw's
  `mediaLocalRoots` fail-closed policy: local paths and `file://` URLs are
  rejected by default, remote-host `file://` values are rejected, configured
  channel/account roots are read from the gateway config snapshot, and only
  files under those roots are read before the native multipart send.
- Verified the BlueBubbles local-media root slice with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_bluebubbles_local_media_requires_roots
  -q` (`1 failed` before implementation, local files uploaded without
  `mediaLocalRoots`), then the same command (`1 passed`), adjacent BlueBubbles
  proof `python -m pytest tests\test_ops_mesh.py -q -k "bluebubbles_"` (`13
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- BlueBubbles/iMessage outbound media now enforces OpenClaw's configured
  media-size limits: account-level, channel-level, and
  `agents.defaults.mediaMaxMb` values from the gateway config snapshot are
  converted to byte ceilings and oversized local or remote media is rejected
  before native multipart upload.
- Verified the BlueBubbles media max-size slice with `python -m pytest
  tests\test_ops_mesh.py::test_ops_mesh_service_send_bluebubbles_local_media_honors_media_max_mb
  -q` (`1 failed` before implementation, a 1MB+1 local file uploaded under a
  1MB limit), then the same command (`1 passed`), adjacent BlueBubbles proof
  `python -m pytest tests\test_ops_mesh.py -q -k "bluebubbles_"` (`14
  passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Saved native-provider media replays now preserve OpenClaw's original-caption
  behavior: BlueBubbles/LINE/Matrix/WhatsApp/Zalo-style media adapters receive
  the original payload `message` on replay instead of the generic formatted
  fallback that appends the `Media:` inventory, while generic provider/session
  replay remains unchanged.
- Verified the native media replay caption slice with `python -m pytest
  tests\test_ops_mesh.py::test_replay_outbound_deliveries_replays_native_media_with_original_caption
  -q` (`1 failed` before implementation, replay sent `Photo caption` plus the
  formatted media inventory), then the same command (`1 passed`), adjacent
  replay/provider proof `python -m pytest tests\test_ops_mesh.py -q -k
  "replay_outbound_deliveries_retries_saved_failed_gateway_send_via_provider_runtime
  or replay_outbound_deliveries_replays_native_media_with_original_caption or
  replay_outbound_deliveries_retries_saved_failed_gateway_poll_via_provider_runtime
  or bluebubbles_"` (`17 passed`), `ruff check src\openzues\services\ops_mesh.py
  tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.
- Direct-announce provider delivery now preserves OpenClaw-style outbound
  metadata across fresh sends, saved route scopes, delivery views, and replay:
  ad-hoc announce sends return the shared direct-channel result, persisted rows
  are tagged as `source="direct.announce"`, and provider-backed replays use the
  saved channel/target/account instead of falling back to session-only delivery.
- Progress estimates were adjusted after this slice: repo-wide parity moves
  from roughly 45% to 46%, cron wake/delivery from roughly 98% to 99%, and
  channels/direct announce from roughly 96% to 97%. These remain hand-scored
  planning estimates, not generated coverage metrics.
- Verified the direct-announce provider metadata slice with `python -m pytest
  tests\test_ops_mesh.py::test_send_ad_hoc_announce_delivery_returns_provider_transport_metadata
  -q` (`1 failed` before implementation because the ad-hoc announce owner
  delivered but returned `None`), then focused proof plus direct-announce replay
  `python -m pytest
  tests\test_ops_mesh.py::test_send_ad_hoc_announce_delivery_returns_provider_transport_metadata
  tests\test_ops_mesh.py::test_replay_outbound_deliveries_replays_direct_announce_via_provider_runtime
  -q` (`2 passed`), and adjacent replay/direct-provider proof `python -m pytest
  tests\test_ops_mesh.py -q -k
  "send_ad_hoc_announce_delivery_returns_provider_transport_metadata or
  replay_outbound_deliveries_replays_direct_announce_via_provider_runtime or
  delivers_explicit_cron_failure_to_announce_thread_target or
  dedupes_replayed_cron_failure_announce_delivery or
  replay_outbound_deliveries_retries_saved_failed_announce_delivery or
  replay_outbound_deliveries_retries_saved_failed_gateway_send_via_provider_runtime
  or replay_outbound_deliveries_replays_native_media_with_original_caption"` (`8
  passed`).
- Top-level `doctor --json` and human doctor output now include a native
  `runtimeBridge` posture rollup for the OpenClaw runtime/CLI packaging and
  doctor seam. The rollup reports Codex app-server command readiness, resolved
  sandbox posture, native provider route readiness, ordered plugin executor
  inventory, and ACP spawn-service availability without claiming non-Windows
  parity.
- Progress estimates were adjusted after this slice: repo-wide parity moves
  from roughly 46% to 47%, active gateway/session/tool-contract parity from
  roughly 97% to 98%, and runtime/CLI/doctor native-bridge parity is now
  tracked at roughly 96%. These remain hand-scored planning estimates, not
  generated coverage metrics.
- Verified the runtime bridge doctor posture slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_includes_runtime_bridge_posture -q` (`1
  failed` before implementation because `runtimeBridge` was absent), then the
  same command (`1 passed`), adjacent doctor/runtime proof `python -m pytest
  tests\test_cli.py -q -k
  "runtime_bridge_posture or gateway_runtime_node or
  doctor_json_includes_sandbox_contribution or
  doctor_json_includes_security_and_shell_completion_surfaces or
  doctor_json_includes_gateway_health_contribution_and_channel_warnings or
  doctor_and_update_status_json_include_hermes_sections or
  doctor_json_includes_bundled_plugin_runtime_dependency_contribution"` (`8
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Provider route `send` and `poll` CLI commands now accept OpenClaw's
  `messageThreadId` / `replyToMessageId` aliases as
  `--message-thread-id` / `--reply-to-message-id`, with the same precedence
  over `--thread` / `--reply-to` used by
  `src/cli/send-runtime/channel-outbound-send.ts`.
- Progress estimates were adjusted after this slice: runtime/CLI/doctor
  native-bridge parity moves from roughly 96% to 97%. Repo-wide parity remains
  roughly 47% because packaging/distribution and standalone ACP bridge breadth
  still dominate the whole-product estimate.
- Verified the provider route CLI alias slice with `python -m pytest
  tests\test_cli.py::test_routes_send_prefers_openclaw_message_thread_and_reply_aliases
  tests\test_cli.py::test_routes_poll_prefers_openclaw_message_thread_and_reply_aliases
  -q` (`2 failed` before implementation because the CLI rejected the aliases),
  then the same command (`2 passed`), adjacent route send/poll proof `python -m
  pytest tests\test_cli.py -q -k "routes_send or routes_poll"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins list --json` now also discovers explicit OpenClaw bundle manifests
  from configured `plugins.load.paths`: `.codex-plugin/plugin.json`,
  `.claude-plugin/plugin.json`, and `.cursor-plugin/plugin.json` are projected
  as native metadata-only `format="bundle"` records with bundle format,
  capability, skill, hook, and settings-file metadata, instead of falling back
  to bare `plugins.entries.<id>` configured rows.
- Progress estimates were adjusted after this slice: CLI + operator control
  plane parity moves from roughly 93% to 94%. Repo-wide parity remains roughly
  48% because packaging/distribution, companion app breadth, TUI surfaces, and
  standalone ACP bridge work still dominate the whole-product estimate.
- Verified the bundle-manifest inventory slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_discovers_openclaw_bundle_manifest_load_paths
  -q` (`1 failed` before implementation because bundle paths fell back to
  configured plugin rows), then the same command (`1 passed`), adjacent plugin
  inventory proof `python -m pytest tests\test_cli.py -q -k
  "plugins_list_json_discovers_openclaw_bundle_manifest_load_paths or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_preserves_manifest_identity_and_classification or
  plugins_list_json_preserves_package_manifest_runtime_metadata or
  plugins_list_json_skips_incompatible_package_manifest_min_host_version or
  plugins_inspect_json_projects_record_runtime_surfaces"` (`6 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins list --json` now also mirrors OpenClaw's manifestless Claude bundle
  detection: configured plugin roots with Claude bundle marker paths such as
  `skills`, `commands`, or `settings.json` become metadata-only
  `format="bundle"` / `bundleFormat="claude"` records when no native plugin
  manifest or default runtime entry file is present.
- Progress estimates remain at roughly 48% repo-wide and ~94% for the
  CLI/operator control plane after this adjacent sub-slice; the unresolved
  plugin-bundle queue now focuses on JSON5 parsing and runtime command/MCP/LSP
  projection.
- Verified the manifestless Claude bundle slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_discovers_manifestless_claude_bundle_load_paths
  -q` (`1 failed` before implementation because the marker-only root fell back
  to a configured plugin row), then the same command (`1 passed`), adjacent
  bundle inventory proof `python -m pytest tests\test_cli.py -q -k
  "plugins_list_json_discovers_manifestless_claude_bundle_load_paths or
  plugins_list_json_discovers_openclaw_bundle_manifest_load_paths or
  plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_preserves_package_manifest_runtime_metadata"` (`4 passed`),
  focused bundle recheck (`2 passed`), `ruff check src\openzues\cli.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Bundle manifest discovery now accepts the same JSON5-style syntax covered by
  OpenClaw's `bundle-manifest.test.ts` fixtures for metadata inventory:
  comments, unquoted object keys, and trailing commas are normalized on the
  bundle-manifest read path before projection.
- Progress estimates remain at roughly 48% repo-wide and ~94% for the
  CLI/operator control plane after this adjacent parsing slice; the next plugin
  bundle queue head is command/MCP/LSP runtime projection rather than metadata
  file discovery.
- Verified the JSON5 bundle manifest slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_accepts_json5_bundle_manifests -q`
  (`1 failed` before implementation because the row used the configured plugin
  fallback name), then the same command (`1 passed`), adjacent bundle inventory
  proof `python -m pytest tests\test_cli.py -q -k
  "plugins_list_json_accepts_json5_bundle_manifests or
  plugins_list_json_discovers_manifestless_claude_bundle_load_paths or
  plugins_list_json_discovers_openclaw_bundle_manifest_load_paths or
  plugins_list_json_discovers_openclaw_manifest_load_paths"` (`4 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Claude bundle command roots now project OpenClaw-style Markdown command
  metadata into native plugin records and `plugins inspect --json`: command
  names come from frontmatter `name` or relative path defaults, and
  `disable-model-invocation` entries are skipped.
- Progress estimates remain at roughly 48% repo-wide and ~94% for the
  CLI/operator control plane after this command-projection slice; remaining
  plugin-bundle runtime projection is now MCP/LSP breadth plus deeper activation
  and import behavior.
- Verified the Claude bundle command projection slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_json_projects_claude_bundle_commands
  -q` (`1 failed` before implementation because `commands` was absent), then
  the same command (`1 passed`), adjacent bundle/plugin proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_inspect_json_projects_claude_bundle_commands or
  plugins_list_json_accepts_json5_bundle_manifests or
  plugins_list_json_discovers_manifestless_claude_bundle_load_paths or
  plugins_list_json_discovers_openclaw_bundle_manifest_load_paths or
  plugins_inspect_json_projects_record_runtime_surfaces"` (`5 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Bundle MCP/LSP server names now project into native plugin records and
  `plugins inspect --json`, covering inline and file-backed server maps for the
  OpenClaw bundle config shapes (`mcpServers`, `servers`, and `lspServers`).
- Progress estimates were adjusted after closing the bundle metadata/projection
  mini-queue: CLI + operator control plane parity moves from roughly 94% to
  95%. Repo-wide parity remains roughly 48% while packaging/distribution,
  companion apps, TUI surfaces, and standalone ACP bridge work remain large.
- Verified the bundle MCP/LSP server projection slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_json_projects_bundle_mcp_and_lsp_servers
  -q` (`1 failed` before implementation because `mcpServers` was absent), then
  the same command (`1 passed`), adjacent bundle/plugin proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_inspect_json_projects_bundle_mcp_and_lsp_servers or
  plugins_inspect_json_projects_claude_bundle_commands or
  plugins_list_json_accepts_json5_bundle_manifests or
  plugins_list_json_discovers_manifestless_claude_bundle_load_paths or
  plugins_list_json_discovers_openclaw_bundle_manifest_load_paths or
  plugins_inspect_json_projects_record_runtime_surfaces"` (`6 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins install <plugin>@<known-marketplace>` now mirrors OpenClaw's Claude
  known marketplace shortcut for local `installLocation` records. The native
  CLI reads `~/.claude/plugins/known_marketplaces.json`, resolves the shortcut
  into the existing marketplace install flow, persists the known marketplace
  name as `marketplaceSource`, and keeps local update compatibility through the
  same resolver.
- Progress estimates were adjusted after this shortcut slice: CLI + operator
  control plane parity moves from roughly 95% to 96%. Repo-wide parity remains
  roughly 48% while remote marketplace clone/download/update behavior,
  packaging/distribution, companion apps, TUI surfaces, and standalone ACP
  bridge work remain large.
- Verified the known marketplace shortcut slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_json_resolves_known_marketplace_shortcut
  -q` (`1 failed` before implementation because `plugins install` still
  required `--marketplace`), then the same command (`1 passed`), adjacent
  marketplace/install/update proof `python -m pytest tests\test_cli.py -q -k
  "plugins_install_json_resolves_known_marketplace_shortcut or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_marketplace_list_json_reads_local_manifest or
  plugins_update_json_refreshes_local_marketplace_install or
  plugins_uninstall_json_removes_native_install_metadata"` (`5 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins marketplace list <github-source>` now follows OpenClaw's remote
  marketplace listing shape for GitHub/Git sources through a fakeable clone
  adapter. The native CLI resolves cloned `.claude-plugin/marketplace.json`
  files, preserves the remote source label, normalizes plugin sources to
  `kind` records, validates remote path entries stay inside the cloned root,
  and runs clone cleanup after JSON projection.
- Progress estimates remain roughly 48% repo-wide and ~96% for the
  CLI/operator control plane after this remote-listing slice; the remaining
  plugin marketplace queue is now remote install/download/update execution for
  Git/GitHub/URL plugin sources, not source listing.
- Verified the remote marketplace listing slice with `python -m pytest
  tests\test_cli.py::test_plugins_marketplace_list_json_reads_cloned_github_shorthand
  -q` (`1 failed` before implementation because the CLI only resolved local
  marketplace paths), then the same command (`1 passed`), adjacent marketplace
  proof `python -m pytest tests\test_cli.py -q -k
  "plugins_marketplace_list_json_reads_cloned_github_shorthand or
  plugins_marketplace_list_json_reads_local_manifest or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_install_json_resolves_known_marketplace_shortcut or
  plugins_update_json_refreshes_local_marketplace_install"` (`5 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins install <plugin> --marketplace <github-source>` now supports the
  first remote marketplace install path natively. The fakeable clone adapter is
  reused for Git/GitHub marketplace sources, remote path entries are resolved
  inside the cloned marketplace root, plugin directories/files are copied into
  a durable OpenZues data-dir install root before clone cleanup, and the saved
  `plugins.installs.<id>` record preserves the remote marketplace source label.
- Progress estimates were adjusted after this remote install slice: CLI +
  operator control plane parity moves from roughly 96% to 97%. Repo-wide parity
  remains roughly 48% while remote entry-source downloads/update,
  packaging/distribution, companion apps, TUI surfaces, and standalone ACP
  bridge work remain large.
- Verified the remote marketplace install slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_marketplace_json_persists_cloned_github_entry
  -q` (`1 failed` before implementation because `plugins install` still
  resolved only local marketplace manifests), then the same command (`1
  passed`), adjacent marketplace proof `python -m pytest tests\test_cli.py -q
  -k "plugins_install_marketplace_json_persists_cloned_github_entry or
  plugins_marketplace_list_json_reads_cloned_github_shorthand or
  plugins_marketplace_list_json_reads_local_manifest or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_install_json_resolves_known_marketplace_shortcut or
  plugins_update_json_refreshes_local_marketplace_install or
  plugins_uninstall_json_removes_native_install_metadata"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins update <plugin>` now refreshes saved remote marketplace path-entry
  installs through the same fakeable Git/GitHub marketplace source resolver.
  Remote path entries are recloned, version comparisons stay OpenClaw-shaped,
  changed non-dry-run updates copy the new plugin files into the durable
  OpenZues data-dir install root, and clone cleanup runs after refresh.
- Progress estimates remain roughly 48% repo-wide and ~97% for the
  CLI/operator control plane after this remote-update slice; the remaining
  plugin marketplace queue is non-path entry-source execution and archive/URL
  download handling.
- Verified the remote marketplace update slice with `python -m pytest
  tests\test_cli.py::test_plugins_update_json_refreshes_remote_marketplace_install
  -q` (`1 failed` before implementation because updates still used the
  local-only marketplace resolver), then the same command (`1 passed`),
  adjacent marketplace proof `python -m pytest tests\test_cli.py -q -k
  "plugins_update_json_refreshes_remote_marketplace_install or
  plugins_install_marketplace_json_persists_cloned_github_entry or
  plugins_marketplace_list_json_reads_cloned_github_shorthand or
  plugins_update_json_refreshes_local_marketplace_install or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_install_json_resolves_known_marketplace_shortcut or
  plugins_uninstall_json_removes_native_install_metadata"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Marketplace entries whose plugin source is a separate Git/GitHub repo now
  install through the native fakeable clone adapter too. The CLI resolves
  `github`, `git`, and `git-subdir` entry source shapes, clones the plugin repo,
  resolves the requested subpath inside the clone, copies the result into the
  durable data-dir marketplace install root, and cleans up the plugin clone.
- Progress estimates remain roughly 48% repo-wide and ~97% for the
  CLI/operator control plane after this entry-source clone slice; the remaining
  plugin marketplace queue is archive/URL download handling.
- Verified the GitHub marketplace entry-source slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_marketplace_json_persists_github_entry_source
  -q` (`1 failed` before implementation because non-path entry sources were
  rejected), then the same command (`1 passed`), adjacent marketplace proof
  `python -m pytest tests\test_cli.py -q -k
  "plugins_install_marketplace_json_persists_github_entry_source or
  plugins_install_marketplace_json_persists_cloned_github_entry or
  plugins_update_json_refreshes_remote_marketplace_install or
  plugins_marketplace_list_json_reads_cloned_github_shorthand or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_update_json_refreshes_local_marketplace_install"` (`6 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Marketplace entries whose plugin source is a URL/archive now install through
  a fakeable native downloader. Downloaded files are bounded, staged into a
  temporary file with cleanup, copied into the durable data-dir marketplace
  install root, and persisted as ordinary marketplace install records.
- Progress estimates were adjusted after closing the marketplace source-shape
  queue: repo-wide parity moves from roughly 48% to 49%, and CLI/operator
  control-plane parity moves from roughly 97% to 98%. Remaining plugin CLI
  breadth is now non-marketplace package/npm/clawhub install/update behavior
  plus runtime activation/import depth.
- Verified the URL marketplace entry-source slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_marketplace_json_persists_url_entry_source
  -q` (`1 failed` before implementation because URL entry sources were
  rejected), then the same command (`1 passed`), adjacent marketplace proof
  `python -m pytest tests\test_cli.py -q -k
  "plugins_install_marketplace_json_persists_url_entry_source or
  plugins_install_marketplace_json_persists_github_entry_source or
  plugins_install_marketplace_json_persists_cloned_github_entry or
  plugins_update_json_refreshes_remote_marketplace_install or
  plugins_marketplace_list_json_reads_cloned_github_shorthand or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_update_json_refreshes_local_marketplace_install"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins install <local-path> --link --json` now follows OpenClaw's linked
  local plugin branch. The native config owner persists `source="path"`,
  `sourcePath`, `installPath`, version metadata from `openclaw.plugin.json`,
  allow/entry/load-path state, and restart posture without copying the linked
  directory.
- Progress estimates remain roughly 49% repo-wide and ~98% for the
  CLI/operator control plane after this local-link slice. Remaining
  non-marketplace plugin install parity is copied local installs plus
  package/npm/clawhub install/update behavior.
- Verified the local path-link install slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_link_json_persists_local_plugin_path
  -q` (`1 failed` before implementation because non-marketplace installs
  exited before local path handling), then the same command (`1 passed`),
  adjacent plugin CLI proof `python -m pytest tests\test_cli.py -q -k
  "plugins_install_link_json_persists_local_plugin_path or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_install_json_resolves_known_marketplace_shortcut or
  plugins_uninstall_json_removes_native_install_metadata or
  plugins_list_json_discovers_openclaw_manifest_load_paths"` (`5 passed`),
  `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- `plugins install <local-path> --json` without `--link` now copies local
  plugin directories/files into a durable `plugins/local/<id>` data-dir install
  root before persisting the same OpenClaw-shaped path install record. The
  source path remains tracked separately from the install/load path.
- Progress estimates remain roughly 49% repo-wide and ~98% for the
  CLI/operator control plane after this copied-local install slice. Remaining
  non-marketplace plugin install parity is package/npm/clawhub install/update
  behavior plus deeper runtime activation/import depth.
- Verified the copied local install slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_json_copies_local_plugin_path -q`
  (`1 failed` before implementation because non-link local paths exited at the
  temporary native boundary), then the same command (`1 passed`), adjacent
  plugin CLI proof `python -m pytest tests\test_cli.py -q -k
  "plugins_install_json_copies_local_plugin_path or
  plugins_install_link_json_persists_local_plugin_path or
  plugins_uninstall_json_removes_native_install_metadata or
  plugins_install_marketplace_json_persists_local_manifest_entry"` (`4
  passed`), `ruff check src\openzues\cli.py
  src\openzues\services\gateway_config.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py src\openzues\services\gateway_config.py`.
- Missing local-looking plugin install specs now match OpenClaw's
  `looksLikeLocalInstallSpec` guard for dot-relative, home-relative, absolute,
  archive, and script-shaped paths: the native CLI reports
  `Path not found: <resolved path>` before falling through to the broader
  package/npm/clawhub install queue.
- Progress estimates remain roughly 49% repo-wide and ~98% for the
  CLI/operator control plane after this guard slice. Remaining non-marketplace
  plugin install parity is package/npm/clawhub install/update behavior plus
  deeper runtime activation/import depth.
- Verified the missing local-looking install-spec slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_reports_missing_local_like_spec -q`
  (`1 failed` before implementation because missing `.tgz` specs returned the
  native marketplace boundary), then the same command (`1 passed`), adjacent
  plugin CLI proof `python -m pytest tests\test_cli.py -q -k
  "plugins_install_reports_missing_local_like_spec or
  plugins_install_json_copies_local_plugin_path or
  plugins_install_link_json_persists_local_plugin_path or
  plugins_install_marketplace_json_persists_local_manifest_entry"` (`4
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Verified the full local-looking predicate follow-up with `python -m pytest
  tests\test_cli.py::test_plugins_install_reports_missing_absolute_local_like_spec
  -q` (`1 failed` before implementation because missing absolute path specs
  returned the native marketplace boundary), then adjacent plugin CLI proof
  `python -m pytest tests\test_cli.py -q -k
  "plugins_install_reports_missing_absolute_local_like_spec or
  plugins_install_reports_missing_local_like_spec or
  plugins_install_json_copies_local_plugin_path or
  plugins_install_link_json_persists_local_plugin_path or
  plugins_install_marketplace_json_persists_local_manifest_entry"` (`5
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins install <bare-plugin-id>` now follows OpenClaw's bundled pre-npm
  branch before ClawHub/npm fallback. Native bundled sources resolve from
  `OPENCLAW_BUNDLED_PLUGINS_DIR` / `OPENZUES_BUNDLED_PLUGINS_DIR`, persist
  path install records with `spec=<raw id>`, keep source/install paths pointed
  at the bundled plugin directory, and emit the upstream-shaped warning that a
  scoped npm package name is required to bypass the bundled plugin.
- Progress estimates remain roughly 49% repo-wide and ~98% for the
  CLI/operator control plane after this bundled pre-npm slice. Remaining
  non-marketplace plugin install parity is explicit/preferred ClawHub
  install, npm install/update behavior, and deeper runtime activation/import
  depth.
- Verified the bundled pre-npm install slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_json_uses_bundled_plugin_for_bare_id
  -q` and `python -m pytest
  tests\test_cli.py::test_plugins_install_human_warns_for_bundled_bare_id -q`
  (`1 failed` each before implementation because bare bundled ids returned the
  native marketplace boundary), then both commands (`1 passed` each), adjacent
  plugin CLI proof `python -m pytest tests\test_cli.py -q -k
  "plugins_install_json_uses_bundled_plugin_for_bare_id or
  plugins_install_human_warns_for_bundled_bare_id or
  plugins_install_reports_missing_absolute_local_like_spec or
  plugins_install_reports_missing_local_like_spec or
  plugins_install_json_copies_local_plugin_path or
  plugins_install_link_json_persists_local_plugin_path or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_install_json_resolves_known_marketplace_shortcut"` (`8 passed`),
  `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- `plugins install clawhub:<name>[@version]` now follows OpenClaw's explicit
  ClawHub branch through a fakeable native plugin installer. Successful
  installs persist `source="clawhub"` records with canonical
  `clawhub:<package>@<version>` specs, package family/channel/url, integrity,
  resolved-at metadata, load-path/allow/entry state, and the existing precise
  unavailable boundary when no native installer is wired.
- Progress estimates remain roughly 49% repo-wide and ~98% for the
  CLI/operator control plane after this explicit ClawHub slice. Remaining
  non-marketplace plugin install parity is preferred ClawHub fallback before
  npm, npm install/update behavior, and deeper runtime activation/import depth.
- Verified the explicit ClawHub install slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_json_uses_clawhub_installer_for_explicit_spec
  -q` and `python -m pytest
  tests\test_cli.py::test_plugins_install_clawhub_reports_unavailable_runtime
  -q` (`1 failed` each before implementation because `clawhub:` specs returned
  the native marketplace boundary), then both commands (`1 passed` each),
  adjacent plugin CLI proof `python -m pytest tests\test_cli.py -q -k
  "plugins_install_json_uses_clawhub_installer_for_explicit_spec or
  plugins_install_clawhub_reports_unavailable_runtime or
  plugins_install_json_uses_bundled_plugin_for_bare_id or
  plugins_install_human_warns_for_bundled_bare_id or
  plugins_install_reports_missing_absolute_local_like_spec or
  plugins_install_reports_missing_local_like_spec or
  plugins_install_json_copies_local_plugin_path or
  plugins_install_link_json_persists_local_plugin_path or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_install_json_resolves_known_marketplace_shortcut"` (`10 passed`),
  `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- Registry npm-looking specs now mirror OpenClaw's preferred ClawHub attempt
  before npm install. The native CLI maps valid registry specs to
  `clawhub:<name>[@selector]`, routes them through the same fakeable ClawHub
  plugin installer, persists successful ClawHub records, and only falls through
  to the current npm boundary when ClawHub reports package/version not found.
- Progress estimates remain roughly 49% repo-wide and ~98% for the
  CLI/operator control plane after this preferred ClawHub slice. Remaining
  non-marketplace plugin install parity is npm install/update behavior and
  deeper runtime activation/import depth.
- Verified the preferred ClawHub fallback slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_json_prefers_clawhub_for_registry_npm_spec
  -q` and `python -m pytest
  tests\test_cli.py::test_plugins_install_preferred_clawhub_not_found_falls_through_to_npm_boundary
  -q` (`1 failed` each before implementation because registry specs skipped
  ClawHub), then both commands (`1 passed` each), adjacent plugin CLI proof
  `python -m pytest tests\test_cli.py -q -k
  "plugins_install_json_prefers_clawhub_for_registry_npm_spec or
  plugins_install_preferred_clawhub_not_found_falls_through_to_npm_boundary or
  plugins_install_json_uses_clawhub_installer_for_explicit_spec or
  plugins_install_clawhub_reports_unavailable_runtime or
  plugins_install_json_uses_bundled_plugin_for_bare_id or
  plugins_install_human_warns_for_bundled_bare_id or
  plugins_install_reports_missing_absolute_local_like_spec or
  plugins_install_reports_missing_local_like_spec or
  plugins_install_json_copies_local_plugin_path or
  plugins_install_link_json_persists_local_plugin_path or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_install_json_resolves_known_marketplace_shortcut"` (`12 passed`),
  `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- Registry npm installs now have a fakeable native branch after preferred
  ClawHub fallback. The CLI calls `plugin_npm_installer.install`, persists
  `source="npm"` records with install path, version, resolved name/version/spec,
  integrity, shasum, and resolved-at metadata, and mirrors OpenClaw's `--pin`
  behavior by storing the exact resolved spec when available.
- Progress estimates remain roughly 49% repo-wide and ~98% for the
  CLI/operator control plane after this npm install slice. Remaining
  non-marketplace plugin parity is npm update/failure fallback behavior,
  hook-pack fallback breadth, production npm installer wiring, and deeper
  runtime activation/import depth.
- Verified the npm install slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_json_uses_npm_installer_after_clawhub_miss_with_pin
  -q` and `python -m pytest
  tests\test_cli.py::test_plugins_install_npm_reports_unavailable_runtime_after_clawhub_miss
  -q` (`1 failed` each before implementation because npm specs still reached
  the old native boundary after ClawHub miss), then both commands (`1 passed`
  each), adjacent plugin CLI proof `python -m pytest tests\test_cli.py -q -k
  "plugins_install_json_uses_npm_installer_after_clawhub_miss_with_pin or
  plugins_install_npm_reports_unavailable_runtime_after_clawhub_miss or
  plugins_install_json_prefers_clawhub_for_registry_npm_spec or
  plugins_install_preferred_clawhub_not_found_falls_through_to_npm_boundary or
  plugins_install_json_uses_clawhub_installer_for_explicit_spec or
  plugins_install_clawhub_reports_unavailable_runtime or
  plugins_install_json_uses_bundled_plugin_for_bare_id or
  plugins_install_human_warns_for_bundled_bare_id or
  plugins_install_reports_missing_absolute_local_like_spec or
  plugins_install_reports_missing_local_like_spec or
  plugins_install_json_copies_local_plugin_path or
  plugins_install_link_json_persists_local_plugin_path or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_install_json_resolves_known_marketplace_shortcut"` (`14 passed`),
  `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- npm `npm_package_not_found` failures now mirror OpenClaw's bundled fallback
  by npm spec. Bundled sources expose package `openclaw.install.npmSpec` /
  package-name metadata, and the native CLI persists the matching bundled
  plugin as a path install with the original npm spec plus the upstream-shaped
  `npm package unavailable... using bundled plugin...` warning.
- Progress estimates remain roughly 49% repo-wide and ~98% for the
  CLI/operator control plane after this npm-failure fallback slice. Remaining
  non-marketplace plugin parity is npm update behavior, hook-pack fallback
  breadth, production npm installer wiring, and deeper runtime
  activation/import depth.
- Verified the npm-not-found bundled fallback slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_npm_not_found_uses_bundled_plugin_by_npm_spec
  -q` (`1 failed` before implementation because the npm error surfaced
  directly), then the same command (`1 passed`), adjacent plugin CLI proof
  `python -m pytest tests\test_cli.py -q -k
  "plugins_install_npm_not_found_uses_bundled_plugin_by_npm_spec or
  plugins_install_json_uses_npm_installer_after_clawhub_miss_with_pin or
  plugins_install_npm_reports_unavailable_runtime_after_clawhub_miss or
  plugins_install_json_prefers_clawhub_for_registry_npm_spec or
  plugins_install_preferred_clawhub_not_found_falls_through_to_npm_boundary or
  plugins_install_json_uses_clawhub_installer_for_explicit_spec or
  plugins_install_clawhub_reports_unavailable_runtime or
  plugins_install_json_uses_bundled_plugin_for_bare_id or
  plugins_install_human_warns_for_bundled_bare_id or
  plugins_install_reports_missing_absolute_local_like_spec or
  plugins_install_reports_missing_local_like_spec or
  plugins_install_json_copies_local_plugin_path or
  plugins_install_link_json_persists_local_plugin_path or
  plugins_install_marketplace_json_persists_local_manifest_entry or
  plugins_install_json_resolves_known_marketplace_shortcut"` (`15 passed`),
  `ruff check src\openzues\cli.py src\openzues\services\gateway_config.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py`.
- npm install records now update through the fakeable native npm adapter,
  matching OpenClaw's `plugins update` source dispatch for `source="npm"`.
  The CLI calls the installer with `mode="update"`, reports dry-run/update
  outcomes with current/next versions, and persists refreshed npm resolution
  fields back into `plugins.installs`.
- Progress estimates moved to roughly 49.5% repo-wide and ~98.5% for the
  CLI/operator control plane after this npm-update slice. Remaining
  non-marketplace plugin parity is hook-pack fallback breadth, production npm
  installer wiring, and deeper runtime activation/import depth.
- Verified the npm update slice with `python -m pytest
  tests\test_cli.py::test_plugins_update_json_refreshes_npm_install_record -q`
  (`1 failed` before implementation because npm install records were skipped),
  then the same command (`1 passed`), adjacent plugin CLI proof `python -m
  pytest tests\test_cli.py -q -k
  "plugins_update_json_refreshes_npm_install_record or
  plugins_update_json_refreshes_local_marketplace_install or
  plugins_update_json_refreshes_remote_marketplace_install or
  plugins_install_json_uses_npm_installer_after_clawhub_miss_with_pin or
  plugins_install_npm_reports_unavailable_runtime_after_clawhub_miss or
  plugins_install_npm_not_found_uses_bundled_plugin_by_npm_spec or
  plugins_install_json_prefers_clawhub_for_registry_npm_spec or
  plugins_uninstall_json_removes_native_install_metadata"` (`8 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins update <npm-package>@<tag-or-version>` now mirrors OpenClaw's update
  selection helper by mapping the explicit npm spec back to the single tracked
  npm install whose resolved/package name matches, then using the raw spec as
  the update override. Ambiguous or unmatched specs continue through the normal
  missing-record path.
- Progress estimates are now roughly 49.5% repo-wide and ~98.6% for the
  CLI/operator control plane after this npm spec-override update slice.
  Remaining non-marketplace plugin parity is hook-pack fallback breadth,
  production npm installer wiring, and deeper runtime activation/import depth.
- Verified the npm update spec-override slice with `python -m pytest
  tests\test_cli.py::test_plugins_update_json_maps_npm_spec_override_to_tracked_install
  -q` (`1 failed` before implementation because no npm update call was made),
  then the same command (`1 passed`), adjacent plugin CLI proof `python -m
  pytest tests\test_cli.py -q -k
  "plugins_update_json_maps_npm_spec_override_to_tracked_install or
  plugins_update_json_refreshes_npm_install_record or
  plugins_update_json_refreshes_local_marketplace_install or
  plugins_update_json_refreshes_remote_marketplace_install or
  plugins_install_json_uses_npm_installer_after_clawhub_miss_with_pin or
  plugins_install_npm_not_found_uses_bundled_plugin_by_npm_spec or
  plugins_install_json_prefers_clawhub_for_registry_npm_spec or
  plugins_uninstall_json_removes_native_install_metadata"` (`8 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- `plugins update` now includes tracked npm hook packs from
  `hooks.internal.installs`, matching OpenClaw's merged plugin/hook update
  command behavior. Native config snapshots preserve top-level `hooks`,
  fakeable `hook_npm_installer` updates run with `mode="update"`, refreshed
  hook-pack install metadata persists under `hooks.internal.installs`, and the
  human restart text names both plugins and hooks.
- Progress estimates are now roughly 49.5% repo-wide and ~98.7% for the
  CLI/operator control plane after this hook-pack update slice. Remaining
  non-marketplace plugin/hook parity is hook-pack install fallback breadth,
  production npm/hook installer wiring, and deeper runtime activation/import
  depth.
- Verified the hook-pack update slice with `python -m pytest
  tests\test_cli.py::test_plugins_update_json_refreshes_hook_pack_install_record
  -q` (`1 failed` before implementation because no hook update call was made),
  then the same command (`1 passed`), adjacent plugin/hook update proof
  `python -m pytest tests\test_cli.py -q -k
  "plugins_update_json_refreshes_hook_pack_install_record or
  plugins_update_json_maps_npm_spec_override_to_tracked_install or
  plugins_update_json_refreshes_npm_install_record or
  plugins_update_json_refreshes_local_marketplace_install or
  plugins_update_json_refreshes_remote_marketplace_install"` (`5 passed`),
  broader adjacent CLI proof including install and hooks doctor checks
  (`9 passed, 405 deselected`), `ruff check src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- `plugins install <npm-spec>` now falls back to npm hook-pack installation
  after plugin npm install fails for a non-bundled, non-security reason,
  matching OpenClaw's hook-pack fallback branch. The native CLI persists
  hook-pack npm install records under `hooks.internal.installs`, returns a
  hook-pack JSON payload with installed hooks and npm resolution metadata, and
  keeps bundled npm fallback ahead of hook fallback.
- Progress estimates are now roughly 49.5% repo-wide and ~98.8% for the
  CLI/operator control plane after this hook-pack install fallback slice.
  Remaining non-marketplace plugin/hook parity is production npm/hook installer
  wiring and deeper runtime activation/import depth.
- Verified the hook-pack install fallback slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_json_falls_back_to_npm_hook_pack -q`
  (`1 failed` before implementation because the plugin npm error exited
  directly), then the same command (`1 passed`), adjacent plugin/hook proof
  `python -m pytest tests\test_cli.py -q -k
  "plugins_install_json_falls_back_to_npm_hook_pack or
  plugins_install_npm_not_found_uses_bundled_plugin_by_npm_spec or
  plugins_install_json_uses_npm_installer_after_clawhub_miss_with_pin or
  plugins_install_npm_reports_unavailable_runtime_after_clawhub_miss or
  plugins_update_json_refreshes_hook_pack_install_record or
  plugins_update_json_maps_npm_spec_override_to_tracked_install or
  plugins_update_json_refreshes_npm_install_record or
  plugins_install_json_prefers_clawhub_for_registry_npm_spec or
  plugins_install_preferred_clawhub_not_found_falls_through_to_npm_boundary"`
  (`9 passed`), `ruff check src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py
  tests\test_cli.py`, and `mypy src\openzues\cli.py
  src\openzues\services\gateway_config.py src\openzues\schemas.py`.
- The CLI service graph now production-wires native npm plugin and hook-pack
  installer adapters instead of relying only on fakeable test attributes. The
  adapters use `npm pack --json`, safe tar extraction, durable data-dir install
  targets, plugin manifest validation, hook-pack package metadata projection,
  and npm resolution fields while avoiding package install scripts.
- At the npm/hook installer checkpoint, progress estimates were roughly 49.6%
  repo-wide and ~98.9% for the CLI/operator control plane. The follow-on
  plugin/runtime queue was deeper activation/import behavior, ClawHub
  production breadth, packaging/distribution, and broader runtime command
  ergonomics.
- Verified the production npm installer adapter slice with `python -m pytest
  tests\test_plugin_npm_installers.py
  tests\test_cli.py::test_plugins_install_json_falls_back_to_npm_hook_pack -q`
  (`3 passed`), adjacent plugin/hook CLI proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_install_json_falls_back_to_npm_hook_pack or
  plugins_install_npm_not_found_uses_bundled_plugin_by_npm_spec or
  plugins_install_json_uses_npm_installer_after_clawhub_miss_with_pin or
  plugins_install_npm_reports_unavailable_runtime_after_clawhub_miss or
  plugins_update_json_refreshes_hook_pack_install_record or
  plugins_update_json_maps_npm_spec_override_to_tracked_install or
  plugins_update_json_refreshes_npm_install_record or
  plugins_install_json_prefers_clawhub_for_registry_npm_spec or
  plugins_install_preferred_clawhub_not_found_falls_through_to_npm_boundary"`
  (`9 passed`), `ruff check src\openzues\services\plugin_npm_installers.py
  src\openzues\cli.py tests\test_plugin_npm_installers.py tests\test_cli.py`,
  and `mypy src\openzues\services\plugin_npm_installers.py
  src\openzues\cli.py`.
- The CLI service graph now production-wires a native ClawHub plugin installer
  instead of relying only on the fakeable ClawHub test seam. The adapter uses
  the ClawHub package/version/download API, validates raw-hex and SRI
  `sha256hash` metadata against the observed archive digest, preserves strict
  `files[]` fallback verification, installs the downloaded archive into a
  durable `plugins/clawhub/<id>` data-dir root, and returns OpenClaw-shaped
  ClawHub package/channel/integrity/resolved-at metadata for the existing CLI
  persistence path.
- Progress estimates are now roughly 49.7% repo-wide, ~99.0% for the
  runtime/CLI/doctor native bridge, and ~99.0% for the CLI/operator control
  plane after this ClawHub production adapter slice. Remaining plugin/runtime
  parity is deeper activation/import behavior, packaging/distribution, and
  broader runtime command ergonomics.
- Verified the production ClawHub installer slice with `python -m pytest
  tests\test_plugin_clawhub_installers.py
  tests\test_cli.py::test_cli_services_declares_clawhub_plugin_installer -q`
  (`3 passed`), adjacent ClawHub/plugin CLI proof `python -m pytest
  tests\test_plugin_clawhub_installers.py tests\test_cli.py -q -k
  "clawhub or plugins_install_json_prefers_clawhub_for_registry_npm_spec or
  plugins_install_preferred_clawhub_not_found_falls_through_to_npm_boundary or
  plugins_install_json_uses_npm_installer_after_clawhub_miss_with_pin or
  plugins_install_npm_reports_unavailable_runtime_after_clawhub_miss or
  plugins_install_json_falls_back_to_npm_hook_pack"` (`10 passed`), adjacent
  installer proof `python -m pytest tests\test_plugin_clawhub_installers.py
  tests\test_plugin_npm_installers.py -q` (`4 passed`), `ruff check
  src\openzues\services\plugin_clawhub_installers.py
  src\openzues\services\plugin_npm_installers.py src\openzues\cli.py
  tests\test_plugin_clawhub_installers.py tests\test_plugin_npm_installers.py
  tests\test_cli.py`, and `mypy
  src\openzues\services\plugin_clawhub_installers.py src\openzues\cli.py`.
- OpenZues now has a native manifest activation planner matching OpenClaw's
  `plugins/activation-planner.ts` trigger rules. The helper resolves plugin
  ids from command aliases and `activation.onCommands`, provider metadata plus
  setup providers, agent harnesses, channels, routes, capability hints,
  contracts-owned tools, hooks, origin filters, and explicit empty plugin
  scopes. This closes the data-level planner seam; remaining plugin activation
  parity is runtime import/executor activation wiring that feeds real installed
  manifests into this planner.
- Progress estimates are now roughly 49.8% repo-wide, ~99.1% for the
  runtime/CLI/doctor native bridge, and ~99.1% for the CLI/operator control
  plane after this activation-planner slice.
- Verified the activation-planner slice with `python -m pytest
  tests\test_gateway_plugin_activation.py -q` (`3 passed`), adjacent manifest
  metadata proof `python -m pytest tests\test_cli.py -q -k
  "plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_preserves_command_aliases or
  plugins_list_json_preserves_manifest_tool_contracts"` (`1 passed`), `ruff
  check src\openzues\services\gateway_plugin_activation.py
  tests\test_gateway_plugin_activation.py`, and `mypy
  src\openzues\services\gateway_plugin_activation.py`.
- Native plugin runtime projection now includes an OpenClaw-shaped active
  registry adapter for tool entries: registry tool names become ordered
  `GatewayPluginRuntimeExecutorSpec`s, optional tools require an allowlist hit
  on the tool, plugin id, or `group:plugins`, core tool-name conflicts are
  skipped, and plugin ids that conflict with core tool names block that plugin's
  projected tools. This closes the executor-spec projection edge; remaining
  activation/import parity is loading real installed plugin modules into a
  native active registry without importing the TypeScript runtime.
- Progress estimates are now roughly 49.9% repo-wide, ~99.2% for the
  runtime/CLI/doctor native bridge, and ~99.2% for the CLI/operator control
  plane after this active-registry projection slice.
- Verified the active-registry projection slice with `python -m pytest
  tests\test_gateway_plugin_runtime.py -q` (`3 passed`), adjacent gateway
  plugin-runtime proof `python -m pytest tests\test_gateway_plugin_runtime.py
  tests\test_gateway_node_methods.py -q -k
  "plugin_runtime or tools_invoke_uses_plugin_runtime_service or
  tools_invoke_projects_plugin_runtime_errors or
  tools_catalog_includes_plugin_runtime_specs or
  tools_effective_includes_plugin_runtime_specs"` (`4 passed`), `ruff check
  src\openzues\services\gateway_plugin_runtime.py
  tests\test_gateway_plugin_runtime.py`, and `mypy
  src\openzues\services\gateway_plugin_runtime.py`.
- `plugins doctor --json` now reports runtime activation posture for manifest
  tool contracts that do not yet have a native active executor. This separates
  "metadata discovered" from "runtime executor active" without making
  metadata-only manifests hard failures, giving operators an honest view of the
  remaining native import/activation adapter work.
- Progress estimates are now roughly 50.0% repo-wide, ~99.3% for the
  runtime/CLI/doctor native bridge, and ~99.3% for the CLI/operator control
  plane after this runtime-activation doctor posture slice.
- Verified the doctor posture slice with `python -m pytest
  tests\test_cli.py::test_plugins_doctor_json_reports_metadata_only_tool_activation
  -q` (`1 passed`), adjacent plugin doctor proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_doctor_json_reports_metadata_only_tool_activation or
  plugins_doctor_json_reports_missing_bundled_runtime_dependencies or
  plugins_doctor_json_limits_runtime_deps_to_enabled_channel_plugins or
  plugins_doctor_human_reports_no_plugin_issues or
  plugins_doctor_human_reports_error_plugins or
  plugins_doctor_human_reports_compatibility_notices"` (`6 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- ClawHub-installed plugins now participate in `plugins update`: recorded
  `source="clawhub"` install metadata dispatches to the native ClawHub adapter
  with the stored base URL and expected plugin id, refreshes package
  family/channel/version/integrity/resolved-at metadata, supports dry-run
  checks without archive installation, and preserves the existing npm and
  marketplace update paths.
- Progress estimates are now roughly 50.1% repo-wide, ~99.4% for the
  runtime/CLI/doctor native bridge, and ~99.4% for the CLI/operator control
  plane after this ClawHub update slice.
- Verified the ClawHub update slice with `python -m pytest
  tests\test_cli.py::test_plugins_update_json_refreshes_clawhub_install_record
  -q` (`1 passed`), adjacent CLI/plugin installer proof `python -m pytest
  tests\test_cli.py -q -k
  "clawhub or plugins_update_json_refreshes_npm_install_record or
  plugins_update_json_maps_npm_spec_override_to_tracked_install or
  plugins_update_json_refreshes_local_marketplace_install"` (`11 passed`),
  `python -m pytest tests\test_plugin_clawhub_installers.py -q` (`2 passed`),
  `ruff check src\openzues\cli.py
  src\openzues\services\plugin_clawhub_installers.py tests\test_cli.py
  tests\test_plugin_clawhub_installers.py`, and `mypy src\openzues\cli.py
  src\openzues\services\plugin_clawhub_installers.py`.
- `doctor:security` now mirrors OpenClaw's exec safe-bin doctor helper:
  top-level `doctor --json` reports missing `safeBinProfiles`, marks
  interpreter/runtime safe bins, reports risky `jq`/`awk`/`sed`-family
  semantics, rolls those warnings into the shared doctor warning list, and
  `doctor --fix` scaffolds empty custom profiles while leaving interpreters as
  warnings.
- Progress estimates are now roughly 50.2% repo-wide, ~99.5% for the
  runtime/CLI/doctor native bridge, and ~99.5% for the CLI/operator control
  plane after this exec safe-bin doctor slice.
- Verified the exec safe-bin doctor slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_exec_safe_bin_profile_coverage
  tests\test_cli.py::test_doctor_fix_scaffolds_custom_exec_safe_bin_profiles
  -q` (`2 passed`), adjacent security proof `python -m pytest
  tests\test_cli.py -q -k
  "exec_safe_bin or exec_policy_config_exceeds_host_policy or
  gateway_config_preserves_exec_policy_config_for_security_doctor or
  approvals_exec_forwarding or heartbeat_direct_policy or
  gateway_bind_is_exposed_without_auth"` (`7 passed`), runtime/doctor proof
  `python -m pytest tests\test_cli.py -q -k
  "doctor_json_includes_runtime_bridge_posture or
  doctor_json_warns_when_exec_policy_config_exceeds_host_policy or
  doctor_json_reports_exec_safe_bin_profile_coverage or
  doctor_fix_scaffolds_custom_exec_safe_bin_profiles"` (`4 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Bundled plugin discovery now mirrors OpenClaw's packaged runtime preference:
  when a package root exposes both usable `dist/extensions` and
  `dist-runtime/extensions` plugin trees, native bundled installs resolve from
  `dist-runtime/extensions` so staged runtime wrappers are preferred over the
  built source graph. Existing direct bundled-root overrides still work.
- Progress estimates are now roughly 50.3% repo-wide, ~99.6% for the
  runtime/CLI/doctor native bridge, and ~99.6% for the CLI/operator control
  plane after this packaged bundled-runtime root slice.
- Verified the packaged bundled-runtime root slice with `python -m pytest
  tests\test_cli.py::test_plugins_install_prefers_dist_runtime_bundled_tree_for_package_root
  -q` (`1 passed`), adjacent bundled install proof `python -m pytest
  tests\test_cli.py -q -k
  "bundled_plugin_for_bare_id or bundled_bare_id or
  npm_not_found_uses_bundled_plugin_by_npm_spec or missing_local_like_spec"`
  (`4 passed`), explicit adjacent proof `python -m pytest
  tests\test_cli.py::test_plugins_install_prefers_dist_runtime_bundled_tree_for_package_root
  tests\test_cli.py::test_plugins_install_json_uses_bundled_plugin_for_bare_id
  tests\test_cli.py::test_plugins_install_human_warns_for_bundled_bare_id
  tests\test_cli.py::test_plugins_install_npm_not_found_uses_bundled_plugin_by_npm_spec
  -q` (`4 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- `doctor:security` now also mirrors OpenClaw's exec safe-bin trusted-directory
  hints: profiled safe bins are resolved through the platform command lookup,
  paths outside the default or configured `safeBinTrustedDirs` are reported in
  `execSafeBins.trustedDirHints`, and the warnings point operators at the
  global/agent trusted-dir config.
- Progress estimates are now roughly 50.4% repo-wide, ~99.7% for the
  runtime/CLI/doctor native bridge, and ~99.7% for the CLI/operator control
  plane after this exec safe-bin trusted-dir hint slice.
- Verified the trusted-dir hint slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_exec_safe_bin_trusted_dir_hints
  -q` (`1 passed`), focused safe-bin proof `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_exec_safe_bin_profile_coverage
  tests\test_cli.py::test_doctor_fix_scaffolds_custom_exec_safe_bin_profiles
  tests\test_cli.py::test_doctor_json_reports_exec_safe_bin_trusted_dir_hints
  -q` (`3 passed`), adjacent security proof `python -m pytest
  tests\test_cli.py -q -k
  "exec_safe_bin or exec_policy_config_exceeds_host_policy or
  gateway_config_preserves_exec_policy_config_for_security_doctor or
  approvals_exec_forwarding or heartbeat_direct_policy or
  gateway_bind_is_exposed_without_auth"` (`8 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now mirrors OpenClaw's configured channel doctor
  preview hook from `doctor/shared/channel-doctor.ts`: native OpenZues scans
  configured channel ids, calls registered fakeable channel doctor adapters,
  records a structured `channelDoctor` contribution, and promotes plugin
  preview warnings into the shared doctor warning list.
- Progress estimates are now roughly 50.5% repo-wide, ~99.8% for the
  runtime/CLI/doctor native bridge, and ~99.8% for the CLI/operator control
  plane after this channel-plugin doctor preview slice.
- Verified the channel-plugin doctor preview slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_channel_plugin_preview_warnings
  -q` (`1 passed`), adjacent doctor/security proof `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_channel_plugin_preview_warnings
  tests\test_cli.py::test_doctor_json_warns_when_exec_policy_config_exceeds_host_policy
  tests\test_cli.py::test_doctor_json_reports_exec_safe_bin_profile_coverage
  tests\test_cli.py::test_doctor_json_reports_exec_safe_bin_trusted_dir_hints
  -q` (`4 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Top-level `doctor --fix --json` now also mirrors OpenClaw's channel doctor
  repair sequencing from `doctor/shared/channel-doctor.ts` and
  `doctor/repair-sequencing.ts`: registered native adapters can expose
  `repair_config` / `repairConfig`, receive `{ cfg, doctorFixCommand }`,
  return sequential config mutations plus change/warning notes, and OpenZues
  persists the final config with full replacement semantics so removals survive.
- Progress estimates are now roughly 50.6% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this channel-plugin doctor repair slice.
- Verified the channel-plugin doctor repair slice with `python -m pytest
  tests\test_cli.py::test_doctor_fix_runs_channel_plugin_repair_config
  tests\test_cli.py::test_doctor_json_reports_channel_plugin_preview_warnings
  -q` (`2 passed`), adjacent repair/security proof `python -m pytest
  tests\test_cli.py::test_doctor_fix_runs_channel_plugin_repair_config
  tests\test_cli.py::test_doctor_json_reports_channel_plugin_preview_warnings
  tests\test_cli.py::test_doctor_fix_removes_stale_plugin_config
  tests\test_cli.py::test_doctor_fix_repairs_open_policy_allow_from
  tests\test_cli.py::test_doctor_fix_recovers_allowlist_policy_allow_from_from_store
  -q` (`5 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now also runs OpenClaw's
  `collectChannelDoctorMutableAllowlistWarnings` contract from
  `doctor-config-flow.ts`: registered channel doctor adapters can expose
  `collect_mutable_allowlist_warnings` /
  `collectMutableAllowlistWarnings`, receive `{ cfg }`, and return provider
  warnings that are surfaced under `channelDoctor` and promoted to the shared
  doctor warnings list.
- Progress estimates are now roughly 50.7% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this channel-plugin mutable-allowlist warning slice.
- Verified the mutable-allowlist warning slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings
  tests\test_cli.py::test_doctor_json_reports_channel_plugin_preview_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_plugin_repair_config -q`
  (`3 passed`), adjacent doctor/security proof `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings
  tests\test_cli.py::test_doctor_json_reports_channel_plugin_preview_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_plugin_repair_config
  tests\test_cli.py::test_doctor_json_warns_when_exec_policy_config_exceeds_host_policy
  tests\test_cli.py::test_doctor_json_reports_exec_safe_bin_profile_coverage -q`
  (`5 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now also runs OpenClaw's
  `runChannelDoctorConfigSequences` hook from `doctor-config-flow.ts`:
  registered channel doctor adapters can expose `run_config_sequence` /
  `runConfigSequence`, receive `{ cfg, env, shouldRepair }`, and return
  `changeNotes` / `warningNotes` that are represented as
  `channelDoctor.sequenceChanges`, `channelDoctor.sequenceWarnings`, and the
  shared channel-doctor changes/warnings.
- Progress estimates are now roughly 50.8% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this channel-plugin config-sequence slice.
- Verified the config-sequence slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_channel_config_sequence_notes
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings
  tests\test_cli.py::test_doctor_json_reports_channel_plugin_preview_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_plugin_repair_config -q`
  (`4 passed`), adjacent doctor repair/security proof `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_channel_config_sequence_notes
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings
  tests\test_cli.py::test_doctor_json_reports_channel_plugin_preview_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_plugin_repair_config
  tests\test_cli.py::test_doctor_fix_removes_stale_plugin_config
  tests\test_cli.py::test_doctor_json_warns_when_exec_policy_config_exceeds_host_policy
  -q` (`6 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Top-level `doctor --fix --json` now also runs OpenClaw's
  `collectChannelDoctorStaleConfigMutations` hook from
  `doctor/shared/channel-doctor.ts`: registered channel doctor adapters can
  expose `clean_stale_config` / `cleanStaleConfig`, receive `{ cfg }`, return
  sequential config mutations, and have stale-cleanup changes reported under
  `channelDoctor.staleChanges` while repair mode persists the final candidate.
- Progress estimates are now roughly 50.9% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this channel-plugin stale-cleanup slice.
- Verified the stale-cleanup slice with `python -m pytest
  tests\test_cli.py::test_doctor_fix_runs_channel_clean_stale_config
  tests\test_cli.py::test_doctor_json_reports_channel_config_sequence_notes
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_plugin_repair_config -q`
  (`4 passed`), adjacent doctor repair proof `python -m pytest
  tests\test_cli.py::test_doctor_fix_runs_channel_clean_stale_config
  tests\test_cli.py::test_doctor_json_reports_channel_config_sequence_notes
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_plugin_repair_config
  tests\test_cli.py::test_doctor_fix_removes_stale_plugin_config
  tests\test_cli.py::test_doctor_fix_repairs_open_policy_allow_from -q`
  (`6 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Top-level `doctor --fix --json` now also runs OpenClaw's
  `normalizeCompatibilityConfig` channel doctor contract from
  `channel-doctor.ts`: registered adapters can expose
  `normalize_compatibility_config` / `normalizeCompatibilityConfig`, receive
  `{ cfg }`, return sequential compatibility mutations, and have
  `channelDoctor.compatibilityChanges` persisted in repair mode before later
  sequence/stale/repair hooks run.
- Progress estimates are now roughly 51.0% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this channel-plugin compatibility-normalizer slice.
- Verified the compatibility-normalizer slice with `python -m pytest
  tests\test_cli.py::test_doctor_fix_runs_channel_compatibility_normalizer
  tests\test_cli.py::test_doctor_fix_runs_channel_clean_stale_config
  tests\test_cli.py::test_doctor_json_reports_channel_config_sequence_notes
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_plugin_repair_config -q`
  (`5 passed`), adjacent doctor repair proof `python -m pytest
  tests\test_cli.py::test_doctor_fix_runs_channel_compatibility_normalizer
  tests\test_cli.py::test_doctor_fix_runs_channel_clean_stale_config
  tests\test_cli.py::test_doctor_json_reports_channel_config_sequence_notes
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_plugin_repair_config
  tests\test_cli.py::test_doctor_fix_removes_stale_plugin_config
  tests\test_cli.py::test_doctor_fix_repairs_open_policy_allow_from -q`
  (`7 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now also runs OpenClaw's
  `collectEmptyAllowlistExtraWarnings` channel doctor hook from
  `empty-allowlist-scan.ts`: registered adapters can expose
  `collect_empty_allowlist_extra_warnings` /
  `collectEmptyAllowlistExtraWarnings`, receive top-level and account-scoped
  channel context, and return provider-specific warnings that land under
  `channelDoctor.emptyAllowlistWarnings` and the shared doctor warning list.
- Progress estimates are now roughly 51.1% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this channel-plugin empty-allowlist extra-warning slice.
- Verified the empty-allowlist extra-warning slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_channel_empty_allowlist_extra_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_compatibility_normalizer
  tests\test_cli.py::test_doctor_fix_runs_channel_clean_stale_config
  tests\test_cli.py::test_doctor_json_reports_channel_config_sequence_notes
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings -q`
  (`5 passed`), adjacent security/repair proof `python -m pytest
  tests\test_cli.py::test_doctor_json_reports_channel_empty_allowlist_extra_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_compatibility_normalizer
  tests\test_cli.py::test_doctor_fix_runs_channel_clean_stale_config
  tests\test_cli.py::test_doctor_json_reports_channel_config_sequence_notes
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings
  tests\test_cli.py::test_doctor_json_warns_about_channel_dm_policy_security
  tests\test_cli.py::test_doctor_fix_recovers_allowlist_policy_allow_from_from_store
  -q` (`7 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Top-level `doctor --json` now also implements OpenClaw's default empty group
  allowlist warning and the
  `shouldSkipDefaultEmptyGroupAllowlistWarning` provider hook from
  `empty-allowlist-policy.ts`: group allowlist configurations with no
  sender source emit a native warning, and registered adapters can suppress
  that default warning with the same account context used by upstream.
- Progress estimates are now roughly 51.2% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this empty-group allowlist skip slice.
- Verified the empty-group skip slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_honors_channel_empty_group_allowlist_skip
  tests\test_cli.py::test_doctor_json_reports_channel_empty_allowlist_extra_warnings
  tests\test_cli.py::test_doctor_json_reports_channel_mutable_allowlist_warnings -q`
  (`3 passed`), adjacent channel/security proof `python -m pytest
  tests\test_cli.py::test_doctor_json_honors_channel_empty_group_allowlist_skip
  tests\test_cli.py::test_doctor_json_reports_channel_empty_allowlist_extra_warnings
  tests\test_cli.py::test_doctor_fix_runs_channel_compatibility_normalizer
  tests\test_cli.py::test_doctor_fix_runs_channel_clean_stale_config
  tests\test_cli.py::test_doctor_json_reports_channel_config_sequence_notes
  tests\test_cli.py::test_doctor_json_warns_about_channel_dm_policy_security -q`
  (`6 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Native plugin inventory now mirrors OpenClaw's doctor contract artifact
  preference from `plugins/doctor-contract-registry.ts` without importing the
  TypeScript runtime: plugin records scan their root for
  `doctor-contract-api.*` before `contract-api.*` and expose the preferred
  artifact under `doctorContractApi` for `plugins list --json` /
  `plugins inspect --json`.
- Progress estimates are now roughly 51.3% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this doctor-contract artifact projection slice.
- Verified the doctor-contract artifact projection slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_prefers_doctor_contract_api_artifact
  tests\test_cli.py::test_plugins_list_json_preserves_manifest_config_contracts
  tests\test_cli.py::test_plugins_list_json_preserves_manifest_identity_and_classification
  -q` (`3 passed`), adjacent plugin inventory/inspect proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_prefers_doctor_contract_api_artifact or
  plugins_list_json_preserves_manifest_config_contracts or
  plugins_list_json_preserves_manifest_identity_and_classification or
  plugins_list_json_preserves_manifest_channel_configs or
  plugins_inspect_json_returns_plugin_detail or
  plugins_inspect_json_projects_record_runtime_surfaces"` (`6 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Native doctor-contract registry helpers now also mirror OpenClaw's scoped
  dry-run narrowing from `collectRelevantDoctorPluginIdsForTouchedPaths`:
  touched `channels.<id>` and `plugins.entries.<id>` paths resolve only the
  relevant plugin ids, legacy `talk.*` fields add `elevenlabs`, and broad
  channel/plugin paths fall back to the full relevant doctor plugin set.
- Progress estimates are now roughly 51.4% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this doctor-contract touched-path narrowing slice.
- Verified the touched-path narrowing slice with `python -m pytest
  tests\test_cli.py::test_doctor_contract_relevant_plugin_ids_narrow_touched_paths
  -q` (`1 passed`), adjacent doctor/plugin proof `python -m pytest
  tests\test_cli.py::test_doctor_contract_relevant_plugin_ids_narrow_touched_paths
  tests\test_cli.py::test_plugins_list_json_prefers_doctor_contract_api_artifact
  tests\test_cli.py::test_doctor_fix_runs_channel_compatibility_normalizer
  tests\test_cli.py::test_doctor_json_reports_channel_plugin_preview_warnings
  -q` (`4 passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and
  `mypy src\openzues\cli.py`.
- Native CLI now mirrors OpenClaw's `secrets reload` surface from
  `src/cli/secrets-cli.ts`: the root Typer `secrets` command exposes
  `reload --json`, dispatches through the native `secrets.reload` gateway
  method, writes raw JSON in JSON mode, and prints the upstream warning-count
  human message otherwise.
- Progress estimates are now roughly 51.5% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this secrets reload CLI slice.
- Verified the secrets reload CLI slice with `python -m pytest
  tests\test_cli.py -q -k "secrets_reload"` (`2 passed`), adjacent
  gateway/CLI proof `python -m pytest tests\test_cli.py
  tests\test_gateway_node_methods.py -q -k "secrets_reload"` (`3 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Native `plugins list --json` now mirrors OpenClaw's imported plugin-state
  projection from `src/plugins/status.ts`: plugin rows carry an `imported`
  boolean derived from the native runtime executor registry state, while
  bundle-format plugin rows remain `imported=false` even when a runtime spec
  names them.
- Progress estimates are now roughly 51.6% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this plugin imported-state projection slice.
- Verified the plugin imported-state slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_marks_runtime_executor_plugins_imported
  -q` (`1 passed`), broad plugin-list proof `python -m pytest
  tests\test_cli.py -q -k "plugins_list_json"` (`20 passed`), adjacent
  inspect proof `python -m pytest tests\test_cli.py -q -k
  "plugins_list_json_marks_runtime_executor_plugins_imported or
  plugins_list_json_projects_runtime_executor_inventory or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_json_returns_plugin_detail"` (`4 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Native `doctor --json` workspaceStatus now consumes the same runtime-aware
  imported plugin records as `plugins list --json`, matching OpenClaw's
  `doctor-workspace-status.ts` imported-count note. Runtime-loaded native
  plugins now increment `workspaceStatus.plugins.imported` and appear in the
  workspaceStatus records with `imported=true`.
- Progress estimates are now roughly 51.7% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this doctor workspaceStatus imported-count slice.
- Verified the doctor workspaceStatus imported-count slice with `python -m
  pytest tests\test_cli.py::test_doctor_json_workspace_status_counts_runtime_imported_plugins
  -q` (`1 passed`), adjacent workspace/plugin proof `python -m pytest
  tests\test_cli.py -q -k "workspace_status_plugin_counts or
  runtime_imported_plugins or plugins_list_json"` (`22 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Native plugin inventory now also preserves facade/imported state from
  upstream-shaped Hermes plugin deck rows, matching OpenClaw's
  `listImportedBundledPluginFacadeIds()` contribution to plugin reports.
  Non-bundle facade-loaded plugins remain `imported=true` even without a native
  runtime executor, while bundle rows are still forced to `imported=false`.
- Progress estimates are now roughly 51.8% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this facade-loaded plugin imported-state slice.
- Verified the facade-loaded plugin imported-state slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_preserves_facade_imported_plugin_state
  -q` (`1 passed`), adjacent imported-state proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_list_json_marks_runtime_executor_plugins_imported or
  plugins_list_json_preserves_facade_imported_plugin_state or
  doctor_json_includes_workspace_status_plugin_counts"` (`3 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Native `doctor --json` workspaceStatus now also mirrors OpenClaw's full
  diagnostics-report behavior from `src/plugins/status.ts`: loaded non-bundle
  plugin modules are treated as imported during doctor diagnostics, while
  ordinary metadata-only `plugins list --json` remains runtime/facade driven.
- Progress estimates are now roughly 51.9% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this diagnostics-loaded imported-state slice.
- Verified the diagnostics-loaded imported-state slice with `python -m pytest
  tests\test_cli.py::test_doctor_json_workspace_status_marks_diagnostics_loaded_plugins_imported
  -q` (`1 passed`), adjacent workspace/imported proof `python -m pytest
  tests\test_cli.py -q -k
  "workspace_status_marks_diagnostics_loaded_plugins_imported or
  workspace_status_counts_runtime_imported_plugins or
  workspace_status_plugin_counts or
  plugins_list_json_preserves_facade_imported_plugin_state"` (`4 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Native `plugins list --json` now mirrors OpenClaw's bundled plugin reported
  version normalization from `src/plugins/status.ts`: deck/runtime plugin rows
  preserve explicit `origin` and `version`, and `origin="bundled"` reports the
  host base version such as `2026.3.23` from `2026.3.23-1`.
- Progress estimates are now roughly 52.0% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this bundled plugin reported-version slice.
- Verified the bundled plugin reported-version slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_json_normalizes_bundled_plugin_reported_version
  -q` (`1 passed`), upstream-shaped adjacent expression `python -m pytest
  tests\test_cli.py -q -k "plugins_list_json and (facade_imported or
  bundled_plugin_version)"` (`1 passed`), explicit adjacent proof `python -m
  pytest tests\test_cli.py -q -k
  "plugins_list_json_preserves_facade_imported_plugin_state or
  plugins_list_json_normalizes_bundled_plugin_reported_version or
  plugins_list_json_projects_hermes_plugin_inventory"` (`3 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Native `plugins inspect --json` now mirrors OpenClaw's plugin-scoped
  diagnostics filtering from `src/plugins/status.ts`: inspect reports receive
  inventory diagnostics and include only entries whose `pluginId` matches the
  inspected plugin, while global or other-plugin diagnostics stay out of the
  per-plugin payload.
- Progress estimates are now roughly 52.1% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~99.9% for the CLI/operator control
  plane after this plugin inspect diagnostics slice.
- Verified the plugin inspect diagnostics slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_json_includes_plugin_scoped_diagnostics
  -q` (`1 passed`), adjacent inspect proof `python -m pytest
  tests\test_cli.py -q -k
  "plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_json_returns_plugin_detail or
  plugins_inspect_json_projects_record_runtime_surfaces"` (`3 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Native `chat.inject` now mirrors OpenClaw's live `chat` event dispatch:
  accepted injected assistant messages publish `event="chat"` with
  `runId="inject-<messageId>"`, canonical `sessionKey`, `seq=0`,
  `state="final"`, and the sanitized assistant message payload, then route the
  same event through subscribed gateway nodes for that canonical session.
- Progress estimates are now roughly 52.2% repo-wide, ~98.1% for the
  chat/session contract subfamily, and ~99.9% for runtime/CLI/doctor after this
  `chat.inject` live-event slice.
- Verified the `chat.inject` live-event slice with `python -m pytest
  tests\test_gateway_node_methods.py::test_chat_inject_appends_assistant_message_and_publishes_session_message_event
  -q` (`1 passed`), adjacent `python -m pytest
  tests\test_gateway_node_methods.py -q -k "chat_inject"` (`5 passed`), `ruff
  check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Native `acp client` now mirrors OpenClaw's interactive prompt replay loop:
  without an injected bridge runner, the Typer command starts the native ACP
  client runtime, initializes a subprocess-backed NDJSON client session, trims
  entered prompts, ignores blank input, sends `prompt` requests with ACP text
  blocks, reports the stop reason, and kills the spawned agent on `exit` or
  `quit`.
- Progress estimates are now roughly 52.3% repo-wide, ~99.9% for the
  runtime/CLI/doctor native bridge, and ~98.7% for the CLI/operator table row
  after this ACP interactive replay slice.
- Verified the ACP interactive replay slice with `python -m pytest
  tests\test_acp_client_runtime.py::test_acp_client_interactive_replay_trims_prompts_and_quits
  tests\test_cli.py::test_acp_client_command_runs_native_interactive_runtime
  -q` (`2 passed`), adjacent `python -m pytest
  tests\test_acp_client_runtime.py tests\test_cli.py -q -k "acp_client or
  acp_bridge_command or acp_status_json_and_human or acp_permission"` (`21
  passed`), `ruff check src\openzues\services\acp_client_runtime.py
  src\openzues\cli.py tests\test_acp_client_runtime.py tests\test_cli.py`, and
  `mypy src\openzues\services\acp_client_runtime.py src\openzues\cli.py`.
- Native `sessions.spawn` attachment handling now mirrors OpenClaw's
  `sanitizeMountPathHint` prompt-safety guard: unsafe `attachAs.mountPath`
  values containing control characters, newlines, or disallowed characters are
  dropped before the spawned child system prompt is built, while safe hints
  still appear in the attachment receipt prompt suffix.
- Progress estimates are now roughly 52.4% repo-wide and ~97.1% for the
  gateway session/tool-contract table row after this attachment mount-path
  sanitizer slice.
- Verified the attachment mount-path sanitizer slice with `python -m pytest
  tests\test_gateway_node_methods.py::test_sessions_spawn_sanitizes_invalid_attachment_mount_path_hint
  -q` (`1 passed`), adjacent `python -m pytest
  tests\test_gateway_node_methods.py -q -k "sessions_spawn and attachment"`
  (`8 passed`), `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- Native sandboxed chat/session attachment handling now mirrors OpenClaw's
  remote inbound media staging path from
  `src/auto-reply/reply/stage-sandbox-media.ts`: provider-backed attachments
  with safe `MediaRemoteHost`/`MediaPath` metadata and configured
  `remoteAttachmentRoots` are fetched through the fakeable SCP-backed adapter,
  copied into the child workspace under `media/inbound`, and rewritten to
  sandbox-relative media refs before the runtime sees them. Unsafe or
  unconfigured remote sources remain unstaged.
- Progress estimates are now roughly 52.5% repo-wide, ~98.2% for the
  chat/session contract subfamily, and ~97.2% for the gateway
  session/tool-contract table row after this remote inbound provider media
  staging slice.
- Verified the remote inbound provider media staging slice with `python -m
  pytest
  tests\test_gateway_node_methods.py::test_chat_send_sandboxed_remote_provider_attachment_stages_allowed_media
  -q` (`1 passed`), adjacent `python -m pytest
  tests\test_gateway_node_methods.py -q -k
  "sandboxed_remote_provider_attachment_stages_allowed_media or
  sandboxed_attachment_stages_media_in_session_workspace or
  saved_path_attachment_stages_media_in_session_workspace"` (`6 passed`),
  `ruff check src\openzues\services\gateway_node_methods.py
  tests\test_gateway_node_methods.py`, and `mypy
  src\openzues\services\gateway_node_methods.py`.
- TTS persona gateway/CLI parity is now landed for OpenClaw's
  `tts.personas` and `tts.setPersona` methods: native persona descriptors are
  projected from config or fakeable service state, selected persona persists in
  TTS prefs, `tts.status` includes active persona metadata, and
  `capability`/`infer tts personas` plus `set-persona` expose JSON-capable CLI
  coverage. Checkpointed in `3819d03a`.
- Progress estimates are now roughly 52.8% repo-wide and ~98.3% for the active
  gateway/session/tool-contract family after this TTS persona slice.
- Verified the TTS persona slice with focused gateway persona tests (`2
  passed`), focused policy test (`1 passed`), focused CLI tests (`2 passed`),
  adjacent gateway TTS tests (`9 passed`), adjacent CLI TTS tests (`11
  passed`), adjacent API TTS tests (`6 passed`), `ruff check`, and `mypy`.
- Realtime voice gateway parity is now landed for OpenClaw's
  `talk.realtime.session`, `relayAudio`, `relayMark`, `relayStop`, and
  `relayToolResult` methods through a fakeable native realtime adapter with
  upstream-shaped unavailable responses when no runtime is wired.
  Checkpointed in `75d03a6c`.
- Progress estimates are now roughly 52.9% repo-wide and ~98.4% for the active
  gateway/session/tool-contract family after this realtime voice gateway slice.
- Verified the realtime voice gateway slice with focused gateway/policy proofs,
  adjacent gateway talk tests (`6 passed`), `ruff check`, and `mypy`; a broader
  policy sweep exposed unrelated existing `channels.stop` and
  `node.pair.remove` gaps for the next queue.
- Channel stop gateway parity is now landed for OpenClaw's `channels.stop`
  method: admin scope, channel/account validation, normalized channel id,
  invalid-channel errors, and idempotent stopped projection.
  Checkpointed in `64f6937a`.
- Progress estimates are now roughly 53.0% repo-wide and ~98.5% for the active
  gateway/session/tool-contract family after this `channels.stop` slice.
- Verified the `channels.stop` slice with focused gateway/policy proofs,
  adjacent channel start/logout/stop tests (`7 passed`), `ruff check`, and
  `mypy`.
- Node pairing removal parity is now landed for OpenClaw's
  `node.pair.remove` method: pairing scope, strict `nodeId` validation,
  paired-node deletion, `{nodeId}` response projection, unknown-node errors,
  and `node.pair.resolved` removal broadcasts.
  Checkpointed in `8a0e6ac6`.
- Progress estimates are now roughly 53.1% repo-wide and ~98.6% for the active
  gateway/session/tool-contract family after this `node.pair.remove` slice.
- Verified the `node.pair.remove` slice with focused gateway/policy proofs,
  adjacent node-pair lifecycle tests (`13 passed`), `ruff check`, and `mypy`.
- Slack provider-native thread timestamp parity is now landed for direct
  route-backed sends: invalid internal `replyToId` values are ignored for
  Slack `thread_ts`, valid Slack timestamp `replyToId` values still win, and
  valid `threadId` values are used as fallback.
  Checkpointed in `a461e5eb`.
- Progress estimates are now roughly 53.2% repo-wide and ~98.7% for the active
  gateway/session/tool-contract family after this Slack provider slice.
- Verified the Slack thread timestamp slice with focused Slack native route
  tests (`2 passed`), adjacent Slack native route tests (`5 passed`), `ruff
  check`, and `mypy`.
- Slack provider-native multi-media parity is now landed for direct
  route-backed sends: multiple media URLs are uploaded as an ordered sequence,
  caption text is attached only to the first upload, raw payload text is used as
  the Slack caption, and the final media id is returned as the canonical
  `messageId` with all ids preserved in `mediaIds`.
  Checkpointed in `e3b5bbc0`.
- Progress estimates are now roughly 53.3% repo-wide and ~98.8% for the active
  gateway/session/tool-contract family after this Slack media result slice.
- Verified the Slack multi-media slice with focused Slack media route tests (`2
  passed`), adjacent Slack native/media route tests (`7 passed`), `ruff check`,
  and `mypy`.
- Discord provider-native webhook thread query parity is now landed for direct
  route-backed sends: `threadId` is encoded as the webhook execution
  `thread_id` query parameter alongside `wait=true`, while `replyToId` and
  `silent` remain body-level Discord message options. Checkpointed in
  `0d40be27`.
- Progress estimates are now roughly 53.4% repo-wide and ~98.9% for the active
  gateway/session/tool-contract family after this Discord provider slice.
- Verified the Discord thread query slice with focused Discord thread/reply
  tests (`2 passed`), adjacent Discord native send/poll route tests (`4
  passed`), `ruff check`, and `mypy`.
- WhatsApp provider-native document filename parity is now landed for direct
  route-backed sends: document media includes a decoded filename derived from
  the media URL path, with `file` as fallback, and reply context remains in the
  Cloud API payload. Checkpointed in `05c4f0fc`.
- Progress estimates are now roughly 53.5% repo-wide and ~99.0% for the active
  gateway/session/tool-contract family after this WhatsApp provider slice.
- Verified the WhatsApp document filename slice with a focused WhatsApp
  document route test (`1 passed`), adjacent WhatsApp media/reply/gif/poll
  route tests (`5 passed`), `ruff check`, and `mypy`.
- Discord provider-native media iteration parity is now landed for direct
  route-backed sends: media URLs are sent as an ordered webhook sequence, the
  first send carries text, later sends use blank content, and provider metadata
  preserves ordered `messageIds` while returning the final id as `messageId`.
  Checkpointed in `b5371fd9`.
- Progress estimates are now roughly 53.6% repo-wide and ~99.1% for the active
  gateway/session/tool-contract family after this Discord media slice.
- Verified the Discord media iteration slice with focused Discord media route
  tests (`2 passed`), adjacent Discord native route tests (`5 passed`), `ruff
  check`, and `mypy`.
- Plugin manifest activation-plan reason projection is now landed for
  `plugins doctor --json`: the existing native activation planner service
  projects OpenClaw-shaped trigger plans and reason entries for command aliases,
  providers, setup providers, agent harnesses, channels, routes, and
  capabilities, and the CLI includes those plans under `runtimeActivation`
  alongside manifest/runtime executor posture. Checkpointed in `721ec0f2`.
- Progress estimates are now roughly 53.7% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is deeper real installed module import and
  runtime activation wiring.
- Verified the plugin activation-plan reason projection slice with focused CLI
  and activation-service tests (`2 passed` total), adjacent plugin CLI tests
  (`5 passed`), adjacent activation service tests (`4 passed`), `ruff check`,
  and `mypy`.
- Plugin registry inspect/refresh CLI parity is now landed for OpenClaw's
  `plugins registry` surface: native plugin inventory is canonicalized into a
  persisted registry index, inspect reports `missing`/`fresh`/`stale` state
  with refresh reasons, and refresh writes the current index under the
  OpenZues settings data directory. Checkpointed in `cdb3035e`.
- Progress estimates are now roughly 53.8% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin registry inspect/refresh slice with focused registry CLI
  tests (`2 passed`), adjacent plugin CLI tests (`4 passed`), `ruff check`,
  and `mypy`.
- Plugin list persisted-registry source projection is now landed for
  OpenClaw's `plugins list --json` registry block: native list output reports
  `registry.source`, returns `persisted` with empty diagnostics after a fresh
  refresh, and keeps derived-source diagnostics available for missing or stale
  persisted indexes. Checkpointed in `6468e305`.
- Progress estimates are now roughly 53.9% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin list registry-source projection slice with the focused
  plugin list registry-source CLI test (`1 passed`), adjacent plugin CLI tests
  (`6 passed`), `ruff check`, and `mypy`.
- Plugin inspect runtime-inspection flag parity is now landed for OpenClaw's
  `plugins inspect --runtime` surface: native `inspect` and `info` accept the
  flag, keep default inspect on the static metadata path, and explicitly mark
  loaded non-bundle rows as imported only for runtime inspection. Checkpoint
  in `5fce4371`.
- Progress estimates are now roughly 54.0% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect runtime flag slice with the focused runtime
  inspect CLI test (`1 passed`), adjacent plugin inspect/runtime inventory
  tests (`6 passed`), `ruff check`, and `mypy`.
- Plugin inspect runtime missing-target preflight is now landed for OpenClaw's
  `plugins inspect --runtime` guard: native inspect checks the static metadata
  inventory first, returns `Plugin not found` for absent targets, and only then
  enters the runtime-inspection path for existing plugins. Checkpointed in
  `9a9e89f2`.
- Progress estimates are now roughly 54.1% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect missing-target preflight slice with the focused
  missing-target CLI test (`1 passed`), focused runtime inspect pair (`2
  passed`), adjacent plugin inspect/runtime inventory tests (`7 passed`),
  `ruff check`, and `mypy`.
- Plugin inspect runtime target-scoped inventory is now landed for OpenClaw's
  `onlyPluginIds` diagnostics-report behavior: after the static preflight, the
  runtime-inspection inventory is filtered to the requested plugin id.
  Checkpointed in `c412b98b`.
- Progress estimates are now roughly 54.2% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect target-scoped runtime slice with the focused
  scoped runtime inspect test (`1 passed`), focused runtime inspect trio (`3
  passed`), adjacent plugin inspect/runtime inventory tests (`8 passed`),
  `ruff check`, and `mypy`.
- Installed plugin activation-state projection is now landed for OpenClaw's
  plugin record activation decision fields: installed/config-backed plugin rows
  now carry `activated`, `explicitlyEnabled`, `activationSource`, and
  `activationReason`, and global plugin disablement overrides an explicitly
  enabled installed plugin with a disabled activation state. Checkpointed in
  `78658f29`.
- Progress estimates are now roughly 54.3% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the installed plugin activation-state slice with the focused CLI
  activation-state test (`1 passed`), adjacent plugin config/install list and
  doctor proof (`6 passed`), `ruff check`, and `mypy`.
- Installed plugin allowlist activation guard is now landed for OpenClaw's
  activation decision precedence: `plugins.allow` remains authoritative over
  explicit installed plugin enablement, preserving `explicitlyEnabled=true`
  while projecting disabled status and `activationReason="not in allowlist"`.
  Checkpointed in `73089117`.
- Progress estimates are now roughly 54.4% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the installed plugin allowlist activation slice with the focused CLI
  allowlist test (`1 passed`), adjacent plugin config/install list and doctor
  proof (`7 passed`), `ruff check`, and `mypy`.
- Installed plugin slot activation reason projection is now landed for
  OpenClaw's explicit slot-selection path: memory/context-engine slot choices
  activate matching installed records before the allowlist guard and project
  upstream reason text such as `selected memory slot`. Checkpointed in
  `209dced0`.
- Progress estimates are now roughly 54.5% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the installed plugin slot activation slice with the focused CLI slot
  activation test (`1 passed`), adjacent plugin config/install list and doctor
  proof (`8 passed`), `ruff check`, and `mypy`.
- Plugin doctor failure-phase projection is now landed for OpenClaw's loader
  error records: native plugin inventory preserves `failurePhase` values from
  deck/plugin rows, `plugins doctor --json` includes the phase on error
  entries, and human doctor output renders the phase marker beside the plugin
  id. Checkpointed in `0dc9fc27`.
- Progress estimates are now roughly 54.6% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin doctor failure-phase slice with `python -m pytest
  tests\test_cli.py::test_plugins_doctor_reports_error_failure_phase -q` (`1
  passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_doctor_reports_error_failure_phase or
  plugins_doctor_human_reports_error_plugins or
  plugins_doctor_human_reports_compatibility_notices or
  plugins_doctor_json_reports_metadata_only_tool_activation or
  plugins_doctor_json_projects_manifest_activation_plan_reasons"` (`5
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect failure-phase projection is now landed for OpenClaw's
  `plugins inspect` error details: JSON inspect payloads preserve
  `plugin.failurePhase` and human inspect output renders the upstream
  `Failure phase: <phase>` line for errored plugin records. Checkpointed in
  `6f4d1ad8`.
- Progress estimates are now roughly 54.7% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect failure-phase slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_reports_error_failure_phase -q` (`1
  passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_reports_error_failure_phase or
  plugins_doctor_reports_error_failure_phase or
  plugins_inspect_json_returns_plugin_detail or
  plugins_info_alias_json_uses_inspect_payload or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_runtime_json_uses_runtime_loaded_import_state"` (`6
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect failed-at timestamp projection is now landed for OpenClaw's
  plugin loader error records: native inventory preserves `failedAt`, JSON
  inspect payloads include `plugin.failedAt`, and human inspect output renders
  `Failed at: <timestamp>` for errored plugin records. Checkpointed in
  `b3bf64a5`.
- Progress estimates are now roughly 54.8% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect failed-at slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_reports_error_failed_at -q` (`1
  passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_reports_error_failed_at or
  plugins_inspect_reports_error_failure_phase or
  plugins_doctor_reports_error_failure_phase or
  plugins_inspect_json_returns_plugin_detail or
  plugins_info_alias_json_uses_inspect_payload or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_runtime_json_uses_runtime_loaded_import_state"` (`7
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect loader error text projection is now landed for OpenClaw's
  plugin loader error records: native inventory preserves `error`, JSON
  inspect payloads include `plugin.error`, and human inspect output renders
  `Error: <text>` for errored plugin records. Checkpointed in `88ff1768`.
- Progress estimates are now roughly 54.9% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect loader-error slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_reports_loader_error_text -q` (`1
  passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_reports_loader_error_text or
  plugins_inspect_reports_error_failed_at or
  plugins_inspect_reports_error_failure_phase or
  plugins_doctor_reports_error_failure_phase or
  plugins_inspect_json_returns_plugin_detail or
  plugins_info_alias_json_uses_inspect_payload or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_runtime_json_uses_runtime_loaded_import_state"` (`8
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect human base metadata is now landed for OpenClaw's inspect
  detail surface: human `plugins inspect <id>` renders description, origin,
  version, capability mode, and legacy `before_agent_start` posture when
  present in the native inspect payload. Checkpointed in `c11085d1`.
- Progress estimates are now roughly 55.0% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect human metadata slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_human_reports_base_metadata -q` (`1
  passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_human_reports_base_metadata or
  plugins_inspect_reports_loader_error_text or
  plugins_inspect_reports_error_failed_at or
  plugins_inspect_reports_error_failure_phase or
  plugins_doctor_reports_error_failure_phase or
  plugins_inspect_json_returns_plugin_detail or
  plugins_info_alias_json_uses_inspect_payload or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_runtime_json_uses_runtime_loaded_import_state"` (`9
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect human capability sections are now landed for OpenClaw's
  inspect detail surface: human `plugins inspect <id>` renders bundle
  capabilities and capability rows from the native inspect payload, including
  registered/inventory capability ids. Checkpointed in `2b161d5a`.
- Progress estimates are now roughly 55.1% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect human capability slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_human_reports_capability_sections
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_human_reports_capability_sections or
  plugins_inspect_human_reports_base_metadata or
  plugins_inspect_reports_loader_error_text or
  plugins_inspect_reports_error_failed_at or
  plugins_inspect_reports_error_failure_phase or
  plugins_doctor_reports_error_failure_phase or
  plugins_inspect_json_returns_plugin_detail or
  plugins_info_alias_json_uses_inspect_payload or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_runtime_json_uses_runtime_loaded_import_state"` (`10
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect human runtime surface sections are now landed for OpenClaw's
  inspect detail surface: human `plugins inspect <id>` renders `Commands`,
  `CLI commands`, `Services`, and `Gateway methods` sections from the native
  inspect payload. Checkpointed in `f2221877`.
- Progress estimates are now roughly 55.2% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect human runtime-surface slice with `python -m
  pytest
  tests\test_cli.py::test_plugins_inspect_human_reports_runtime_surface_sections
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_human_reports_runtime_surface_sections or
  plugins_inspect_human_reports_capability_sections or
  plugins_inspect_human_reports_base_metadata or
  plugins_inspect_reports_loader_error_text or
  plugins_inspect_reports_error_failed_at or
  plugins_inspect_reports_error_failure_phase or
  plugins_doctor_reports_error_failure_phase or
  plugins_inspect_json_returns_plugin_detail or
  plugins_info_alias_json_uses_inspect_payload or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_runtime_json_uses_runtime_loaded_import_state"` (`11
  passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect human tools section is now landed for OpenClaw's inspect
  detail surface: human `plugins inspect <id>` renders `Tools` rows from
  native runtime executor specs, including optional tool markers. Checkpoint
  in `5ac316c1`.
- Progress estimates are now roughly 55.3% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect human tools slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_human_reports_runtime_tools -q` (`1
  passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_human_reports_runtime_tools or
  plugins_inspect_human_reports_runtime_surface_sections or
  plugins_inspect_human_reports_capability_sections or
  plugins_inspect_human_reports_base_metadata or
  plugins_inspect_reports_loader_error_text or
  plugins_inspect_reports_error_failed_at or
  plugins_inspect_reports_error_failure_phase or
  plugins_doctor_reports_error_failure_phase or
  plugins_inspect_json_returns_plugin_detail or
  plugins_info_alias_json_uses_inspect_payload or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_runtime_json_uses_runtime_loaded_import_state or
  plugins_inspect_json_projects_runtime_executor_tools"` (`13 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect human MCP/LSP server sections are now landed for OpenClaw's
  inspect detail surface: human `plugins inspect <id>` renders `MCP servers`
  and `LSP servers` sections from the native inspect payload. Checkpointed in
  `6fc67848`.
- Progress estimates are now roughly 55.4% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect human MCP/LSP slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_json_projects_bundle_mcp_and_lsp_servers
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_json_projects_bundle_mcp_and_lsp_servers or
  plugins_inspect_json_projects_claude_bundle_commands or
  plugins_inspect_human_reports_runtime_tools or
  plugins_inspect_human_reports_runtime_surface_sections or
  plugins_inspect_human_reports_capability_sections or
  plugins_inspect_human_reports_base_metadata or
  plugins_inspect_json_projects_runtime_executor_tools"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect human HTTP routes section is now landed for OpenClaw's inspect
  detail surface: human `plugins inspect <id>` renders `HTTP routes` with the
  positive route count from the native inspect payload. Checkpointed in
  `efef8270`.
- Progress estimates are now roughly 55.5% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect human HTTP routes slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_json_projects_record_runtime_surfaces
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_json_projects_bundle_mcp_and_lsp_servers or
  plugins_inspect_human_reports_runtime_tools or
  plugins_inspect_human_reports_runtime_surface_sections or
  plugins_inspect_human_reports_capability_sections or
  plugins_inspect_human_reports_base_metadata or
  plugins_inspect_json_projects_runtime_executor_tools"` (`7 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect human policy section is now landed for OpenClaw's inspect
  detail surface: human `plugins inspect <id>` renders `Policy` rows for
  prompt-injection, conversation access, model override, and configured
  allowed-model policy fields from the native inspect payload. Checkpointed in
  `e0af8199`.
- Progress estimates are now roughly 55.6% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect human policy slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_json_projects_config_policy -q` (`1
  passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_json_projects_config_policy or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_json_projects_bundle_mcp_and_lsp_servers or
  plugins_inspect_human_reports_runtime_tools or
  plugins_inspect_human_reports_runtime_surface_sections or
  plugins_inspect_human_reports_capability_sections or
  plugins_inspect_human_reports_base_metadata"` (`7 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Plugin inspect human diagnostics section is now landed for OpenClaw's
  inspect detail surface: human `plugins inspect <id>` renders `Diagnostics`
  rows for plugin-scoped diagnostics and excludes other/global diagnostics.
  Checkpointed in `667182c7`.
- Progress estimates are now roughly 55.7% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect human diagnostics slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_json_includes_plugin_scoped_diagnostics
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_json_projects_config_policy or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_json_projects_bundle_mcp_and_lsp_servers or
  plugins_inspect_human_reports_runtime_tools or
  plugins_inspect_human_reports_runtime_surface_sections or
  plugins_inspect_human_reports_capability_sections or
  plugins_inspect_human_reports_base_metadata"` (`8 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Plugin inspect human install section is now landed for OpenClaw's inspect
  detail surface: human `plugins inspect <id>` renders `Install` rows for
  saved install records in OpenClaw field order. Checkpointed in `5ca0a5f2`.
- Progress estimates are now roughly 55.8% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect human install slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_all_json_includes_saved_install_records
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_all_json_includes_saved_install_records or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_json_projects_config_policy or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_json_projects_bundle_mcp_and_lsp_servers or
  plugins_inspect_human_reports_runtime_tools or
  plugins_inspect_human_reports_runtime_surface_sections or
  plugins_inspect_human_reports_capability_sections or
  plugins_inspect_human_reports_base_metadata"` (`9 passed`), `ruff check
  src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.
- Plugin inspect human compatibility warnings section is now landed for
  OpenClaw's inspect detail surface: human `plugins inspect <id>` renders
  `Compatibility warnings` rows from native compatibility notices without the
  doctor-only severity suffix. Checkpointed in `38b85a1a`.
- Progress estimates are now roughly 55.9% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect human compatibility slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_human_reports_base_metadata -q` (`1
  passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_human_reports_base_metadata or
  plugins_doctor_human_reports_compatibility_notices or
  plugins_inspect_all_json_includes_saved_install_records or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_json_projects_config_policy or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_json_projects_bundle_mcp_and_lsp_servers or
  plugins_inspect_human_reports_runtime_tools or
  plugins_inspect_human_reports_runtime_surface_sections or
  plugins_inspect_human_reports_capability_sections"` (`10 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect typed/custom hook sections are now landed for OpenClaw's
  inspect detail surface: native plugin records preserve `typedHooks` and
  `customHooks`, inspect JSON projects them, and human `plugins inspect <id>`
  renders `Typed hooks` and `Custom hooks` sections with priority/event
  formatting. Checkpointed in `0a6e8bcd`.
- Progress estimates are now roughly 56.0% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect hook-section slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_projects_and_reports_hook_sections
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_projects_and_reports_hook_sections or
  plugins_inspect_human_reports_base_metadata or
  plugins_doctor_human_reports_compatibility_notices or
  plugins_inspect_all_json_includes_saved_install_records or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_json_projects_config_policy or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_json_projects_bundle_mcp_and_lsp_servers or
  plugins_inspect_human_reports_runtime_tools or
  plugins_inspect_human_reports_runtime_surface_sections or
  plugins_inspect_human_reports_capability_sections"` (`11 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin inspect human header/bundle-format labels are now landed for
  OpenClaw's inspect detail surface: human `plugins inspect <id>` renders
  capitalized `Status`, `Format`, `Source`, and `Shape` labels and includes
  `Bundle format` for bundle plugins. Checkpointed in `df4d586c`.
- Progress estimates are now roughly 56.1% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin inspect header/bundle-format slice with `python -m pytest
  tests\test_cli.py::test_plugins_inspect_json_projects_claude_bundle_commands
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_inspect_json_projects_claude_bundle_commands or
  plugins_inspect_projects_and_reports_hook_sections or
  plugins_inspect_human_reports_base_metadata or
  plugins_doctor_human_reports_compatibility_notices or
  plugins_inspect_all_json_includes_saved_install_records or
  plugins_inspect_json_includes_plugin_scoped_diagnostics or
  plugins_inspect_json_projects_config_policy or
  plugins_inspect_json_projects_record_runtime_surfaces or
  plugins_inspect_json_projects_bundle_mcp_and_lsp_servers or
  plugins_inspect_human_reports_runtime_tools or
  plugins_inspect_human_reports_runtime_surface_sections or
  plugins_inspect_human_reports_capability_sections"` (`12 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.
- Plugin list verbose activation/import state is now landed for OpenClaw's
  list formatting surface: `plugins list --verbose` renders `activated`,
  `imported`, `explicitly enabled`, `activation source`, and sanitized
  `activation reason` rows from native plugin records. Checkpointed in
  `83146bc1`.
- Progress estimates are now roughly 56.2% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin list verbose activation/import slice with `python -m
  pytest
  tests\test_cli.py::test_plugins_list_json_projects_installed_plugin_activation_state
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_list_json_projects_installed_plugin_activation_state or
  plugins_list_json_marks_runtime_executor_plugins_imported or
  plugins_list_verbose_reports_runtime_executor_inventory or
  plugins_list_json_keeps_installed_plugin_allowlist_authoritative or
  plugins_list_json_projects_installed_plugin_slot_activation_reason or
  plugins_list_json_includes_saved_config_install_records"` (`6 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.

- Plugin list human enabled labels are now landed for OpenClaw's list
  formatting surface: active registry/plugin rows render as `enabled` instead
  of exposing the internal OpenZues `loaded` status label, while JSON status
  fields and loaded counts remain unchanged. Checkpointed in `bc362484`.
- Progress estimates are now roughly 56.3% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin list enabled-label slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_verbose_reports_runtime_executor_inventory
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_list_verbose_reports_runtime_executor_inventory or
  plugins_list_json_projects_installed_plugin_activation_state or
  plugins_list_json_marks_runtime_executor_plugins_imported or
  plugins_list_json_keeps_installed_plugin_allowlist_authoritative or
  plugins_list_json_projects_installed_plugin_slot_activation_reason or
  plugins_list_json_includes_saved_config_install_records"` (`6 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.

- Plugin list human enabled counts are now landed for OpenClaw's list command
  surface: human `plugins list --verbose` renders `Plugins (enabled/total
  enabled)` instead of `loaded`, using explicit `enabled` fields when present
  and status fallback for native OpenZues records. Checkpointed in `cc9983c3`.
- Progress estimates are now roughly 56.4% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the plugin list enabled-count slice with `python -m pytest
  tests\test_cli.py::test_plugins_list_verbose_reports_runtime_executor_inventory
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_list_verbose_reports_runtime_executor_inventory or
  plugins_list_json_projects_installed_plugin_activation_state or
  plugins_list_json_marks_runtime_executor_plugins_imported or
  plugins_list_json_keeps_installed_plugin_allowlist_authoritative or
  plugins_list_json_projects_installed_plugin_slot_activation_reason or
  plugins_list_json_includes_saved_config_install_records"` (`6 passed`),
  `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.

- Manifest load-path activation-state projection is now landed for OpenClaw's
  cold metadata inventory path: manifest and bundle plugin records discovered
  through `plugins.load.paths` project `activated`, `explicitlyEnabled`,
  `activationSource`, and optional `activationReason` without forcing runtime
  module import. Checkpoint pending.
- Progress estimates are now roughly 56.5% repo-wide while the
  runtime/CLI/doctor and CLI/operator-control bounded paths remain ~99.9%;
  the remaining plugin queue head is still deeper real installed module import
  and runtime activation wiring.
- Verified the manifest load-path activation-state slice with `python -m
  pytest
  tests\test_cli.py::test_plugins_list_json_discovers_openclaw_manifest_load_paths
  -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
  "plugins_list_json_discovers_openclaw_manifest_load_paths or
  plugins_list_json_projects_installed_plugin_activation_state or
  plugins_list_json_keeps_installed_plugin_allowlist_authoritative or
  plugins_list_json_projects_installed_plugin_slot_activation_reason or
  plugins_list_json_preserves_manifest_activation_and_setup or
  plugins_list_json_discovers_openclaw_bundle_manifest_load_paths or
  plugins_list_json_discovers_manifestless_claude_bundle_load_paths or
  plugins_list_json_accepts_json5_bundle_manifests"` (`8 passed`), `ruff
  check src\openzues\cli.py tests\test_cli.py`, and `mypy
  src\openzues\cli.py`.

## References

- Primary ledger: [openclaw-parity-checkpoint-2026-04-10.md](openclaw-parity-checkpoint-2026-04-10.md)
- Repo-level seam queue: [openclaw-parity-unresolved-seams.md](openclaw-parity-unresolved-seams.md)
- Recovery example: [openclaw-parity-relay-2026-04-14-recovery-thread-019d8e51.md](openclaw-parity-relay-2026-04-14-recovery-thread-019d8e51.md)
