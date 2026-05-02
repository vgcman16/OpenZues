# Cross-Repo Implementation Tracker

Last updated: 2026-05-02

Coordinator repo: `C:\Users\skull\OneDrive\Documents\OpenZues`

Primary source of truth: `C:\Users\skull\OneDrive\Documents\openclaw-main`

Reference/bridge repos:

- `C:\Users\skull\OneDrive\Documents\hermes-agent-main`
- `C:\Users\skull\OneDrive\Documents\warp-master`

This workspace tracks what is implemented, what is verified, what remains, and
which percentages can move after a checked-off implementation slice. Hermes and
Warp rows are reference/bridge evidence unless a row explicitly targets a
Hermes or Warp integration.

## Status Summary

| Scope | Percent | Status | Source |
| --- | ---: | --- | --- |
| Repo-wide OpenClaw parity in OpenZues | ~57.0% | Active, broad parity still open | `docs/openclaw-parity-progress.md`, `docs/openclaw-parity-unresolved-seams.md` |
| Active gateway/session/tool-contract path | ~99.1% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Chat/session contract subfamily | ~98.3% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Runtime/CLI/doctor native bridge | ~99.9% | Mostly landed; packaging and installed plugin depth remain | `docs/openclaw-parity-progress.md` |
| Hermes reference surface | 80-85% | Reference-only rough status from repo inspection | `docs/tracking/03-hermes-reference-status.md` |
| Warp reference surface | Mixed | Reference-only; client-local plus backend-gated areas | `docs/tracking/04-warp-reference-status.md` |

## Current Worktree Boundary

The configured-channel bundled-owner allowlist bypass slice is checkpointed in
`6ad518d4`. Any follow-up changes should target the next queue head only:

- `src/openzues/cli.py`
- `src/openzues/services/gateway_plugin_activation.py`
- `tests/test_cli.py`
- `tests/test_gateway_plugin_activation.py`
- `docs/openclaw-parity-progress.md`
- `docs/openclaw-parity-unresolved-seams.md`
- `docs/tracking/00-cross-repo-implementation-tracker.md`
- `docs/tracking/01-openzues-openclaw-parity-status.md`

Known untracked temp/log artifacts are unrelated and must remain unstaged.

## Current Queue

| ID | Area | Status | Percent Impact | Next Action |
| --- | --- | --- | ---: | --- |
| OZ-RM-001 | Sandboxed remote inbound provider media staging | Checkpointed and pushed in `2e6a3ed8` | Repo-wide +0.1%, chat/session +0.1%, gateway session/tool +0.1% | Done; continue `OZ-RT-001` |
| OZ-RT-001 | Runtime-control hard gaps | Checkpointed in `8a0e6ac6` | Repo-wide +0.1%, active gateway/method +0.1% | Small base-method sweep done; rotate to provider/runtime breadth |
| OZ-PKG-001 | Packaging/distribution breadth | Open | Broad | Map Windows-first doctor/package surfaces against OpenClaw |
| OZ-PLUGIN-001 | Real installed plugin module import/activation | Configured-channel bundled-owner allowlist bypass checkpointed in `6ad518d4` | Repo-wide +0.1%, CLI/runtime +0.1% | Continue real installed module import/activation depth |
| OZ-COMP-001 | Companion apps/nodes parity | Open | Broad | Inventory OpenClaw macOS/iOS/Android node behavior and choose first local bridge seam |
| OZ-PROV-001 | Provider-native outbound/inbound breadth | Discord media iteration checkpointed in `b5371fd9` | Repo-wide +0.1%, active gateway/method +0.1% | Continue provider-specific send/poll/replay metadata gaps |

## Active Slice Detail

- [x] `OZ-RT-001A` `sessions.pluginPatch` registered plugin session extension state
  - Source: `openclaw-main/src/gateway/server-methods/sessions.ts`,
    `openclaw-main/src/plugins/host-hook-state.ts`,
    `openclaw-main/src/plugins/host-hook-json.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_plugin_runtime.py`,
    `src/openzues/services/gateway_sessions.py`,
    `src/openzues/services/gateway_method_policy.py`
  - Contract: `sessions.pluginPatch` is admin-only, rejects unregistered
    plugin/namespace pairs, persists JSON-compatible plugin extension state
    by plugin id and namespace, projects registered extension values on
    session rows, and removes state on explicit `unset=true`.
  - Evidence required: focused test, adjacent session-control test, ruff, mypy
  - Status: checkpointed in `e0c02761`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_gateway_node_methods.py::test_sessions_plugin_patch_persists_registered_extension_state
    -q` (`1 passed`), adjacent `python -m pytest
    tests\test_gateway_node_methods.py -q -k "sessions_plugin_patch or
    sessions_patch or sessions_resolve"` (`27 passed`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001A` `plugins.uiDescriptors` control UI descriptor gateway method
  - Source: `openclaw-main/src/gateway/server-methods/plugin-host-hooks.ts`,
    `openclaw-main/src/gateway/protocol/schema/plugins.ts`, and
    `openclaw-main/src/plugins/registry.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_plugin_runtime.py`,
    `src/openzues/services/gateway_method_policy.py`
  - Contract: `plugins.uiDescriptors` accepts only `{}`, returns
    `{ok: true, descriptors}` from the active plugin runtime registry, stamps
    each descriptor with registry-owned `pluginId` and optional `pluginName`,
    preserves JSON-compatible `schema` and valid `requiredScopes`, and skips
    invalid/disabled descriptor registrations before projection.
  - Evidence required: focused test, adjacent plugin-runtime test, ruff, mypy
  - Status: checkpointed in `9fb5098b`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_gateway_node_methods.py::test_plugins_ui_descriptors_returns_registered_control_ui_descriptors
    -q` (`1 passed`), adjacent `python -m pytest
    tests\test_gateway_node_methods.py -q -k "plugins_ui_descriptors or
    tools_invoke_uses_plugin_runtime or tools_invoke_runs_registry_plugin_executor
    or tools_invoke_keeps_registry_owner_only or sessions_plugin_patch"` (`5
    passed`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001B` plugin manifest activation-plan reason projection
  - Source: `openclaw-main/src/plugins/activation-planner.ts`,
    `openclaw-main/src/plugins/activation-planner.test.ts`,
    `openclaw-main/src/plugins/cli-registry-loader.ts`,
    `openclaw-main/src/plugins/providers.runtime.ts`, and
    `openclaw-main/src/plugins/channel-presence-policy.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`,
    `src/openzues/services/gateway_plugin_activation.py`,
    `tests/test_cli.py`, `tests/test_gateway_plugin_activation.py`
  - Contract: `plugins doctor --json` projects native OpenClaw-shaped
    activation plans for installed manifest records, including command alias,
    provider/setup-provider, agent-harness, channel, route, and capability
    triggers with upstream reason strings such as
    `activation-command-hint`, `manifest-provider-owner`,
    `manifest-setup-provider-owner`, and `manifest-tool-contract`.
  - Evidence required: focused plugin doctor activation test, adjacent plugin
    CLI tests, ruff, mypy
  - Status: checkpointed in `721ec0f2`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_projects_manifest_activation_plan_reasons
    -q` (`1 passed`), `python -m pytest
    tests\test_gateway_plugin_activation.py::test_resolve_manifest_activation_plan_projects_reason_entries
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_reports_metadata_only_tool_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons or
    plugins_list_json_preserves_manifest_activation_and_setup or
    plugins_list_json_projects_runtime_executor_inventory or
    plugins_list_json_marks_runtime_executor_plugins_imported"` (`5 passed`),
    adjacent `python -m pytest tests\test_gateway_plugin_activation.py -q` (`4
    passed`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001C` plugin registry inspect/refresh CLI
  - Source: `openclaw-main/src/cli/plugins-cli.ts`,
    `openclaw-main/src/cli/plugins-cli.list.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `plugins registry --json` compares current native manifest/load
    path plugin inventory with a persisted registry index and reports
    `missing`/`fresh`/`stale` plus refresh reasons; `plugins registry
    --refresh --json` writes the current index under the OpenZues settings
    data directory and returns `{refreshed: true, registry}`.
  - Evidence required: focused registry inspect/refresh tests, adjacent plugin
    CLI tests, ruff, mypy
  - Status: checkpointed in `cdb3035e`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_registry_json_reports_missing_persisted_registry
    -q` (`1 passed`), `python -m pytest
    tests\test_cli.py::test_plugins_registry_refresh_json_persists_current_index
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_registry or
    plugins_list_json_preserves_manifest_activation_and_setup or
    plugins_doctor_json_projects_manifest_activation_plan_reasons"` (`4
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001D` plugin list persisted-registry source projection
  - Source: `openclaw-main/src/cli/plugins-list-command.ts`,
    `openclaw-main/src/plugins/status.ts`,
    `openclaw-main/src/plugins/status.registry-snapshot.test.ts`,
    `openclaw-main/src/cli/plugins-cli.list.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: after `plugins registry --refresh`, `plugins list --json`
    reports a `registry` block with `source="persisted"` and no diagnostics;
    missing or stale persisted indexes report derived-source diagnostics while
    keeping plugin list metadata cold and native.
  - Evidence required: focused plugin list registry-source test, adjacent
    plugin registry/list tests, ruff, mypy
  - Status: checkpointed in `6468e305`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_reports_persisted_registry_source_after_refresh
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_registry or
    plugins_list_json_reports_persisted_registry_source_after_refresh or
    plugins_list_json_preserves_manifest_activation_and_setup or
    plugins_doctor_json_projects_manifest_activation_plan_reasons or
    plugins_list_json_discovers_openclaw_manifest_load_paths"` (`6 passed`),
    `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001E` plugin inspect runtime-inspection flag
  - Source: `openclaw-main/src/cli/plugins-cli.ts`,
    `openclaw-main/src/cli/plugins-cli.list.test.ts`,
    `openclaw-main/src/plugins/status.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `plugins inspect <id> --runtime --json` is accepted, uses the
    native runtime-inspection posture only when explicitly requested, preserves
    missing-target behavior, and marks loaded non-bundle metadata rows as
    imported for runtime inspection without importing the TypeScript runtime.
  - Evidence required: focused plugin inspect runtime test, adjacent plugin
    inspect/runtime inventory tests, ruff, mypy
  - Status: checkpointed in `5fce4371`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001F` plugin inspect runtime missing-target static preflight
  - Source: `openclaw-main/src/cli/plugins-cli.list.test.ts`,
    `openclaw-main/src/cli/plugins-cli.ts`,
    `openclaw-main/src/plugins/status.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `plugins inspect <missing> --runtime` resolves target existence
    from the static metadata inventory first and returns the OpenClaw-shaped
    missing-plugin error without entering the runtime-inspection path.
  - Evidence required: focused missing-target runtime inspect test, adjacent
    plugin inspect/runtime inventory tests, ruff, mypy
  - Status: checkpointed in `9a9e89f2`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001G` plugin inspect runtime target-scoped inventory
  - Source: `openclaw-main/src/cli/plugins-cli.list.test.ts`,
    `openclaw-main/src/plugins/status.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: after static target preflight, `plugins inspect <id> --runtime`
    loads native runtime-inspection inventory scoped to the requested plugin
    id, matching OpenClaw's `onlyPluginIds` diagnostics-report call shape.
  - Evidence required: focused scoped runtime inspect test, adjacent plugin
    inspect/runtime inventory tests, ruff, mypy
  - Status: checkpointed in `c412b98b`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001H` installed plugin activation-state projection
  - Source: `openclaw-main/src/plugins/config-activation-shared.ts`,
    `openclaw-main/src/plugins/loader-records.ts`,
    `openclaw-main/src/plugins/status.ts`, and
    `openclaw-main/src/cli/plugins-cli.list.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: config/install-backed plugin rows preserve OpenClaw-shaped
    activation decision fields: `activated`, `explicitlyEnabled`,
    `activationSource`, `activationReason`, and disabled status when global
    plugin activation blocks an explicitly enabled installed plugin.
  - Evidence required: focused installed activation-state CLI test, adjacent
    plugin config/install list and doctor tests, ruff, mypy
  - Status: checkpointed in `78658f29`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_projects_installed_plugin_activation_state
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_list_json_includes_saved_config_install_records or
    plugins_list_json_projects_installed_plugin_activation_state or
    plugins_list_json_discovers_openclaw_manifest_load_paths or
    plugins_list_json_marks_runtime_executor_plugins_imported or
    plugins_doctor_json_reports_metadata_only_tool_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons"` (`6
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001I` installed plugin allowlist activation guard
  - Source: `openclaw-main/src/plugins/config-activation-shared.ts`,
    `openclaw-main/src/plugins/config-state.test.ts`,
    `openclaw-main/src/plugins/loader-records.ts`, and
    `openclaw-main/src/plugins/status.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `plugins.allow` remains authoritative over explicitly enabled
    config/install-backed plugin records: excluded installed plugins project
    `status="disabled"`, `activated=false`, `explicitlyEnabled=true`,
    `activationSource="disabled"`, and `activationReason="not in allowlist"`.
  - Evidence required: focused allowlist activation-state CLI test, adjacent
    plugin config/install list and doctor tests, ruff, mypy
  - Status: checkpointed in `73089117`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_keeps_installed_plugin_allowlist_authoritative
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_list_json_keeps_installed_plugin_allowlist_authoritative or
    plugins_list_json_projects_installed_plugin_activation_state or
    plugins_list_json_includes_saved_config_install_records or
    plugins_list_json_discovers_openclaw_manifest_load_paths or
    plugins_list_json_marks_runtime_executor_plugins_imported or
    plugins_doctor_json_reports_metadata_only_tool_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons"` (`7
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001J` installed plugin slot activation reason
  - Source: `openclaw-main/src/plugins/config-activation-shared.ts`,
    `openclaw-main/src/plugins/config-state.test.ts`,
    `openclaw-main/src/plugins/loader-records.ts`, and
    `openclaw-main/src/plugins/status.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `plugins.slots.memory` and `plugins.slots.contextEngine`
    explicitly activate matching config/install-backed plugin records before
    the allowlist guard, preserving upstream reasons such as
    `selected memory slot`.
  - Evidence required: focused slot activation-state CLI test, adjacent plugin
    config/install list and doctor tests, ruff, mypy
  - Status: checkpointed in `209dced0`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_projects_installed_plugin_slot_activation_reason
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_list_json_projects_installed_plugin_slot_activation_reason or
    plugins_list_json_keeps_installed_plugin_allowlist_authoritative or
    plugins_list_json_projects_installed_plugin_activation_state or
    plugins_list_json_includes_saved_config_install_records or
    plugins_list_json_discovers_openclaw_manifest_load_paths or
    plugins_list_json_marks_runtime_executor_plugins_imported or
    plugins_doctor_json_reports_metadata_only_tool_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons"` (`8
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001K` plugin doctor failure-phase projection
  - Source: `openclaw-main/src/plugins/loader-records.ts`,
    `openclaw-main/src/plugins/registry-types.ts`, and
    `openclaw-main/src/cli/plugins-cli.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: native plugin inventory rows preserve OpenClaw loader
    `failurePhase` values (`validation`, `load`, `register`), `plugins doctor
    --json` includes the phase on plugin errors, and human doctor output
    renders the phase beside the plugin id.
  - Evidence required: focused plugin doctor failure-phase test, adjacent
    plugin doctor/activation tests, ruff, mypy
  - Status: checkpointed in `0dc9fc27`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_reports_error_failure_phase -q`
    (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_reports_error_failure_phase or
    plugins_doctor_human_reports_error_plugins or
    plugins_doctor_human_reports_compatibility_notices or
    plugins_doctor_json_reports_metadata_only_tool_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons"` (`5
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001L` plugin inspect failure-phase projection
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`,
    `openclaw-main/src/plugins/loader-records.ts`, and
    `openclaw-main/src/plugins/registry-types.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `plugins inspect <id> --json` preserves `plugin.failurePhase`
    for loader error records and human `plugins inspect <id>` renders the
    OpenClaw-style `Failure phase: <phase>` line after status.
  - Evidence required: focused plugin inspect failure-phase test, adjacent
    plugin inspect/doctor tests, ruff, mypy
  - Status: checkpointed in `6f4d1ad8`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_inspect_reports_error_failure_phase -q`
    (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_inspect_reports_error_failure_phase or
    plugins_doctor_reports_error_failure_phase or
    plugins_inspect_json_returns_plugin_detail or
    plugins_info_alias_json_uses_inspect_payload or
    plugins_inspect_json_includes_plugin_scoped_diagnostics or
    plugins_inspect_runtime_json_uses_runtime_loaded_import_state"` (`6
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001M` plugin inspect failed-at timestamp projection
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`,
    `openclaw-main/src/plugins/loader-records.ts`, and
    `openclaw-main/src/plugins/registry-types.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: native plugin inventory rows preserve OpenClaw loader
    `failedAt` timestamps, `plugins inspect <id> --json` includes
    `plugin.failedAt`, and human `plugins inspect <id>` renders the
    OpenClaw-style `Failed at: <timestamp>` line.
  - Evidence required: focused plugin inspect failed-at test, adjacent plugin
    inspect/doctor tests, ruff, mypy
  - Status: checkpointed in `b3bf64a5`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001N` plugin inspect loader error text projection
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`,
    `openclaw-main/src/plugins/loader-records.ts`, and
    `openclaw-main/src/plugins/registry-types.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: native plugin inventory rows preserve OpenClaw loader
    `error` text, `plugins inspect <id> --json` includes `plugin.error`, and
    human `plugins inspect <id>` renders the OpenClaw-style `Error: <text>`
    line for errored plugin records.
  - Evidence required: focused plugin inspect loader-error test, adjacent
    plugin inspect/doctor tests, ruff, mypy
  - Status: checkpointed in `88ff1768`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_inspect_reports_loader_error_text -q`
    (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
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

- [x] `OZ-PLUGIN-001O` plugin inspect human base metadata
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders the OpenClaw-style base
    metadata that was already present in native inspect payloads: description,
    origin, version, capability mode, and legacy `before_agent_start` posture.
  - Evidence required: focused plugin inspect human metadata test, adjacent
    plugin inspect/doctor tests, ruff, mypy
  - Status: checkpointed in `c11085d1`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_inspect_human_reports_base_metadata -q`
    (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
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

- [x] `OZ-PLUGIN-001P` plugin inspect human capability sections
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders OpenClaw-style bundle
    capabilities and capability section rows from the native inspect payload,
    including registered/inventory capability ids.
  - Evidence required: focused plugin inspect human capability test, adjacent
    plugin inspect/doctor tests, ruff, mypy
  - Status: checkpointed in `2b161d5a`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001Q` plugin inspect human runtime surface sections
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders OpenClaw-style `Commands`,
    `CLI commands`, `Services`, and `Gateway methods` sections from the native
    inspect payload.
  - Evidence required: focused plugin inspect human runtime-surface test,
    adjacent plugin inspect/doctor tests, ruff, mypy
  - Status: checkpointed in `f2221877`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001R` plugin inspect human tools section
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders OpenClaw-style `Tools`
    section rows from native runtime executor specs, including optional tool
    markers.
  - Evidence required: focused plugin inspect human tools test, adjacent
    plugin inspect/doctor tests, ruff, mypy
  - Status: checkpointed in `5ac316c1`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_inspect_human_reports_runtime_tools -q`
    (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
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

- [x] `OZ-PLUGIN-001S` plugin inspect human MCP/LSP sections
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders OpenClaw-style `MCP
    servers` and `LSP servers` sections from bundle/native inspect payloads.
  - Evidence required: focused plugin inspect MCP/LSP test, adjacent plugin
    inspect bundle/runtime tests, ruff, mypy
  - Status: checkpointed in `6fc67848`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001T` plugin inspect human HTTP routes section
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders OpenClaw-style `HTTP
    routes` when the inspect payload has a positive route count.
  - Evidence required: focused plugin inspect runtime-surface test, adjacent
    plugin inspect human/runtime tests, ruff, mypy
  - Status: checkpointed in `efef8270`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001U` plugin inspect human policy section
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders OpenClaw-style `Policy`
    rows for prompt-injection, conversation access, model override, and
    configured allowed-model policy fields from the native inspect payload.
  - Evidence required: focused plugin inspect config-policy test, adjacent
    plugin inspect human/runtime tests, ruff, mypy
  - Status: checkpointed in `e0af8199`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_inspect_json_projects_config_policy -q`
    (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_inspect_json_projects_config_policy or
    plugins_inspect_json_projects_record_runtime_surfaces or
    plugins_inspect_json_projects_bundle_mcp_and_lsp_servers or
    plugins_inspect_human_reports_runtime_tools or
    plugins_inspect_human_reports_runtime_surface_sections or
    plugins_inspect_human_reports_capability_sections or
    plugins_inspect_human_reports_base_metadata"` (`7 passed`), `ruff check
    src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001V` plugin inspect human diagnostics section
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders OpenClaw-style
    `Diagnostics` rows for plugin-scoped diagnostics while excluding
    diagnostics for other plugins or global scope.
  - Evidence required: focused plugin inspect scoped-diagnostics test,
    adjacent plugin inspect human/runtime tests, ruff, mypy
  - Status: checkpointed in `667182c7`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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
    src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001W` plugin inspect human install section
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders OpenClaw-style `Install`
    rows for saved install records, including source, spec/source/install
    paths, recorded version, ClawHub/ClawPack metadata, size, and installed-at
    fields when present.
  - Evidence required: focused plugin inspect saved-install test, adjacent
    plugin inspect human/runtime tests, ruff, mypy
  - Status: checkpointed in `5ca0a5f2`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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
    src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001X` plugin inspect human compatibility warnings section
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`,
    `openclaw-main/src/plugins/status.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders OpenClaw-style
    `Compatibility warnings` rows from plugin compatibility notices without
    the doctor-only severity suffix.
  - Evidence required: focused plugin inspect human metadata/compatibility
    test, adjacent plugin inspect/doctor tests, ruff, mypy
  - Status: checkpointed in `38b85a1a`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_inspect_human_reports_base_metadata -q`
    (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
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

- [x] `OZ-PLUGIN-001Y` plugin inspect typed/custom hook sections
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: native plugin records preserve `typedHooks` and `customHooks`,
    inspect JSON projects them, and human `plugins inspect <id>` renders
    OpenClaw-style `Typed hooks` and `Custom hooks` sections with priority and
    event formatting.
  - Evidence required: focused plugin inspect hook-section test, adjacent
    plugin inspect/doctor tests, ruff, mypy
  - Status: checkpointed in `0a6e8bcd`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001Z` plugin inspect human header/bundle-format labels
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins inspect <id>` renders OpenClaw-style capitalized
    `Status`, `Format`, `Source`, and `Shape` labels and includes `Bundle
    format` when present.
  - Evidence required: focused plugin inspect Claude bundle test, adjacent
    plugin inspect/doctor tests, ruff, mypy
  - Status: checkpointed in `df4d586c`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001AA` plugin list verbose activation/import state
  - Source: `openclaw-main/src/cli/plugins-list-format.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins list --verbose` renders OpenClaw-style
    `activated`, `imported`, `explicitly enabled`, `activation source`, and
    sanitized `activation reason` rows for plugin records that carry those
    fields.
  - Evidence required: focused plugin list activation-state test, adjacent
    plugin list/runtime tests, ruff, mypy
  - Status: checkpointed in `83146bc1`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001AB` plugin list human enabled label
  - Source: `openclaw-main/src/cli/plugins-list-format.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins list --verbose` renders active registry entries
    as `enabled` rather than leaking OpenZues' internal `loaded` status while
    preserving JSON status fields and loaded counts.
  - Evidence required: focused plugin list runtime-inventory test, adjacent
    plugin list/runtime tests, ruff, mypy
  - Status: checkpointed in `bc362484`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001AC` plugin list human enabled count
  - Source: `openclaw-main/src/cli/plugins-list-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: human `plugins list --verbose` renders the header count as
    `Plugins (enabled/total enabled)`, using explicit record `enabled` values
    when present and falling back to `status="loaded"` for native records.
  - Evidence required: focused plugin list runtime-inventory test, adjacent
    plugin list/runtime tests, ruff, mypy
  - Status: checkpointed in `cc9983c3`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001AD` manifest load-path activation-state projection
  - Source: `openclaw-main/src/plugins/status.ts`,
    `openclaw-main/src/plugins/config-state.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: manifest and bundle records discovered through
    `plugins.load.paths` project OpenClaw-shaped `activated`,
    `explicitlyEnabled`, `activationSource`, and optional
    `activationReason` fields without forcing runtime module import.
  - Evidence required: focused manifest load-path test, adjacent plugin
    activation/manifest inventory tests, ruff, mypy
  - Status: checkpointed in `54bf33aa`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
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

- [x] `OZ-PLUGIN-001AE` errored runtime-imported plugin projection
  - Source: `openclaw-main/src/plugins/status.test.ts`,
    `openclaw-main/src/plugins/status.ts`,
    `openclaw-main/src/plugins/runtime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: runtime diagnostics/inspect paths mark non-bundle plugins as
    `imported=true` when the plugin module was evaluated even if the final
    plugin status is `error`, preserving the error status and metadata.
  - Evidence required: focused runtime inspect error-import test, adjacent
    loader-error/workspace-status tests, ruff, mypy
  - Status: checkpointed in `cc2da90c`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_inspect_runtime_marks_error_plugin_imported
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_inspect_runtime_marks_error_plugin_imported or
    plugins_inspect_reports_loader_error_text or
    plugins_inspect_reports_error_failure_phase or
    plugins_inspect_reports_error_failed_at or
    plugins_doctor_reports_error_failure_phase or
    doctor_json_workspace_status_marks_diagnostics_loaded_plugins_imported or
    doctor_json_workspace_status_counts_runtime_imported_plugins"` (`7
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001AF` public-surface/runtime-sidecar artifact metadata
  - Source: `openclaw-main/src/plugins/bundled-plugin-metadata.test.ts`,
    `openclaw-main/src/plugins/bundled-plugin-scan.ts`, and
    `openclaw-main/src/plugins/public-surface-runtime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: OpenClaw manifest/load-path plugin records scan top-level public
    surface source files, rewrite them to built `.js` artifact names, exclude
    primary extension/setup/config/test files, and project
    `publicSurfaceArtifacts` plus `runtimeSidecarArtifacts` without importing
    the TypeScript runtime.
  - Evidence required: focused manifest load-path test, adjacent
    manifest/bundle inventory tests, ruff, mypy
  - Status: checkpointed in `2acd2736`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_discovers_openclaw_manifest_load_paths
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_list_json_discovers_openclaw_manifest_load_paths or
    plugins_list_json_projects_installed_plugin_activation_state or
    plugins_list_json_preserves_manifest_activation_and_setup or
    plugins_list_json_discovers_openclaw_bundle_manifest_load_paths or
    plugins_list_json_discovers_manifestless_claude_bundle_load_paths or
    plugins_list_json_accepts_json5_bundle_manifests or
    plugins_inspect_json_projects_record_runtime_surfaces"` (`7 passed`),
    `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001AG` configured-channel plugin owner activation projection
  - Source: `openclaw-main/src/plugins/runtime/runtime-registry-loader.test.ts`,
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.ts`,
    `openclaw-main/src/plugins/channel-presence-policy.ts`, and
    `openclaw-main/src/plugins/activation-context.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_plugin_activation.py`,
    `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `plugins doctor --json` projects the configured-channel runtime
    scope by resolving explicit configured channel ids to manifest-owning
    plugin ids, preserving channel policy entries, and showing the
    OpenClaw-shaped temporary activation config that would allow scoped owner
    loading without importing the TypeScript runtime.
  - Evidence required: focused configured-channel doctor test, adjacent
    plugin doctor/manifest tests, activation helper tests, ruff, mypy
  - Status: checkpointed in `ae5c3986`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_projects_configured_channel_plugin_activation
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_projects_configured_channel_plugin_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons or
    plugins_doctor_json_reports_metadata_only_tool_activation or
    plugins_list_json_discovers_openclaw_manifest_load_paths or
    plugins_list_json_preserves_manifest_activation_and_setup"` (`5 passed`),
    `python -m pytest
    tests\test_gateway_plugin_activation.py::test_resolve_configured_channel_plugin_plan_projects_activation_config
    -q` (`1 passed`), `python -m pytest
    tests\test_gateway_plugin_activation.py -q` (`5 passed`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001AH` configured-channel disabled-owner policy
  - Source: `openclaw-main/src/plugins/channel-presence-policy.ts`,
    `openclaw-main/src/plugins/manifest-owner-policy.ts`, and
    `openclaw-main/src/plugins/activation-context.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_plugin_activation.py`,
    `tests/test_gateway_plugin_activation.py`
  - Contract: configured-channel owner resolution honors explicit plugin
    activation policy; a manifest owner with `plugins.entries.<id>.enabled =
    false` stays blocked with `blockedReasons=["plugin-disabled"]`, produces no
    scoped plugin ids, and does not emit a temporary activation config.
  - Evidence required: focused disabled-owner activation helper test, full
    activation helper suite, adjacent plugin doctor tests, ruff, mypy
  - Status: checkpointed in `d2d0e9c3`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_gateway_plugin_activation.py::test_resolve_configured_channel_plugin_plan_respects_disabled_owner
    -q` (`1 passed`), `python -m pytest
    tests\test_gateway_plugin_activation.py -q` (`6 passed`), adjacent
    `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_projects_configured_channel_plugin_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons or
    plugins_doctor_json_reports_metadata_only_tool_activation"` (`3 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001AI` configured-channel bundled-owner allowlist bypass
  - Source: `openclaw-main/src/plugins/channel-presence-policy.ts` and
    `openclaw-main/src/plugins/manifest-owner-policy.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_plugin_activation.py`,
    `tests/test_gateway_plugin_activation.py`
  - Contract: an explicitly configured channel can activate its bundled
    manifest owner even when `plugins.allow` is restrictive and omits that
    owner, while still preserving explicit disabled and denylist blocks.
  - Evidence required: focused bundled-owner allowlist-bypass helper test,
    full activation helper suite, adjacent plugin doctor tests, ruff, mypy
  - Status: checkpointed in `6ad518d4`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_gateway_plugin_activation.py::test_resolve_configured_channel_plugin_plan_bypasses_allowlist_for_bundled_owner
    -q` (`1 passed`), `python -m pytest
    tests\test_gateway_plugin_activation.py -q` (`7 passed`), adjacent
    `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_projects_configured_channel_plugin_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons or
    plugins_doctor_json_reports_metadata_only_tool_activation"` (`3 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-RT-001B` TTS persona gateway and CLI methods
  - Source: `openclaw-main/src/gateway/server-methods/tts.ts`,
    `openclaw-main/src/config/types.tts.ts`, and
    `openclaw-main/src/cli/capability-cli.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_tts.py`,
    `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_method_policy.py`, and
    `src/openzues/cli.py`
  - Contract: `tts.personas` accepts `{}` and returns the active persona plus
    configured persona descriptors; `tts.setPersona` accepts `persona`, clears
    on `off`/`none`/`default`, rejects unknown ids, persists selected persona
    in TTS prefs, projects `persona`/`personas` on status, and exposes matching
    JSON-capable Typer commands.
  - Evidence required: focused gateway/policy/CLI tests, adjacent TTS gateway,
    API, and CLI tests, ruff, mypy
  - Status: checkpointed in `3819d03a`
  - Weight: 1
  - Last verified: 2026-05-02, focused gateway persona tests (`2 passed`),
    focused policy test (`1 passed`), focused CLI tests (`2 passed`),
    adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k
    "tts_"` (`9 passed`), adjacent `python -m pytest tests\test_cli.py -q
    -k "tts_"` (`11 passed`), adjacent `python -m pytest
    tests\test_gateway_nodes_api.py -q -k "tts"` (`6 passed`), `ruff
    check`, and `mypy`.

- [x] `OZ-RT-001C` realtime voice gateway session and relay methods
  - Source: `openclaw-main/src/gateway/server-methods/talk.ts`,
    `openclaw-main/src/gateway/protocol/schema/channels.ts`, and
    `openclaw-main/src/gateway/method-scopes.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_method_policy.py`
  - Contract: `talk.realtime.session`, `relayAudio`, `relayMark`,
    `relayStop`, and `relayToolResult` are write-scoped, validate
    OpenClaw-shaped params, dispatch through a fakeable realtime runtime
    adapter when registered, return relay `{ok: true}` responses, and preserve
    OpenClaw-shaped unavailable errors when no realtime provider/relay runtime
    is wired.
  - Evidence required: focused gateway/policy tests, adjacent talk gateway
    tests, ruff, mypy
  - Status: checkpointed in `75d03a6c`
  - Weight: 1
  - Last verified: 2026-05-02, focused gateway realtime tests (`2 passed`),
    focused talk/TTS policy proof (`2 passed`), adjacent `python -m pytest
    tests\test_gateway_node_methods.py -q -k "talk_realtime or talk_speak or
    talk_config"` (`6 passed`), `ruff check`, and `mypy`. A broader policy
    selection exposed unrelated existing gaps for `channels.stop` and
    `node.pair.remove`.

- [x] `OZ-RT-001D` `channels.stop` gateway method
  - Source: `openclaw-main/src/gateway/server-methods/channels.ts` and
    `openclaw-main/src/gateway/method-scopes.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_method_policy.py`
  - Contract: `channels.stop` is admin-scoped, validates `channel` and optional
    `accountId`, normalizes known channel ids, returns `{channel, accountId,
    stopped: true}` as an idempotent native stop boundary, and preserves
    OpenClaw-shaped invalid-channel errors.
  - Evidence required: focused gateway/policy tests, adjacent channel mutation
    tests, ruff, mypy
  - Status: checkpointed in `64f6937a`
  - Weight: 1
  - Last verified: 2026-05-02, focused gateway stop tests (`2 passed`),
    focused channel policy proof (`1 passed`), adjacent `python -m pytest
    tests\test_gateway_node_methods.py -q -k "channels_stop or channels_start
    or channels_logout"` (`7 passed`), `ruff check`, and `mypy`. A broader
    channel-status selection exposed an unrelated older catalog expectation for
    Zalo/LINE/Matrix.

- [x] `OZ-RT-001E` `node.pair.remove` gateway method
  - Source: `openclaw-main/src/gateway/server-methods/nodes.ts` and
    `openclaw-main/src/gateway/method-scopes.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_pairing.py`,
    `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_method_policy.py`
  - Contract: `node.pair.remove` is pairing-scoped, validates `nodeId`,
    removes a paired node from the native pairing store, returns `{nodeId}`,
    rejects unknown nodes, and broadcasts `node.pair.resolved` with
    `decision="removed"` and an empty `requestId`.
  - Evidence required: focused gateway/policy tests, adjacent node-pair
    lifecycle tests, ruff, mypy
  - Status: checkpointed in `8a0e6ac6`
  - Weight: 1
  - Last verified: 2026-05-02, focused gateway remove tests (`2 passed`),
    focused node/voice policy proof (`1 passed`), adjacent `python -m pytest
    tests\test_gateway_node_methods.py -q -k "node_pair_remove or
    node_pair_approve or node_pair_reject or node_pair_list or
    node_pair_request or node_pair_verify or node_rename"` (`13 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001A` Slack native route `thread_ts` fallback
  - Source: `openclaw-main/extensions/slack/src/thread-ts.ts`,
    `openclaw-main/extensions/slack/src/thread-ts.test.ts`, and
    `openclaw-main/extensions/slack/src/outbound-adapter.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`
  - Contract: Slack native route-backed sends use `replyToId` as Slack
    `thread_ts` only when it matches Slack timestamp format, fall back to a
    valid Slack timestamp `threadId`, and omit invalid internal ids from Slack
    API payloads.
  - Evidence required: focused Slack native route test, adjacent Slack route
    test, ruff, mypy
  - Status: checkpointed in `a461e5eb`
  - Weight: 1
  - Last verified: 2026-05-02, focused Slack native route tests (`2 passed`),
    adjacent `python -m pytest tests\test_ops_mesh.py -q -k
    "slack_native_route or direct_channel_message_uses_slack or
    slack_reply_to_thread"` (`5 passed`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001B` Slack native multi-media result metadata
  - Source: `openclaw-main/test/helpers/channels/outbound-payload-contract.ts`,
    `openclaw-main/src/channels/plugins/outbound/direct-text-media.ts`, and
    `openclaw-main/extensions/slack/src/outbound-adapter.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`
  - Contract: Slack native route-backed media sends iterate `mediaUrls`, attach
    raw payload text only to the first upload, return the final media id as
    `messageId`, and preserve ordered `mediaIds` and `mediaUrls`.
  - Evidence required: focused Slack media route test, adjacent Slack native
    route test, ruff, mypy
  - Status: checkpointed in `e3b5bbc0`
  - Weight: 1
  - Last verified: 2026-05-02, focused Slack media route tests (`2 passed`),
    adjacent `python -m pytest tests\test_ops_mesh.py -q -k
    "slack_native_route or slack_media or direct_channel_message_uses_slack"`
    (`7 passed`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001C` Discord webhook thread query placement
  - Source: `openclaw-main/extensions/discord/src/send.webhook.ts`,
    `openclaw-main/extensions/discord/src/outbound-adapter.ts`, and
    `openclaw-main/extensions/discord/src/outbound-adapter.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`
  - Contract: Discord route-backed sends preserve `wait=true`, pass
    `threadId` as webhook execution query parameter `thread_id`, keep
    `silent` flags and `replyToId` message references in the JSON body, and
    omit `thread_id` from the body.
  - Evidence required: focused Discord native route test, adjacent Discord
    native send/poll route test, ruff, mypy
  - Status: checkpointed in `0d40be27`
  - Weight: 1
  - Last verified: 2026-05-02, focused Discord thread/reply tests (`2
    passed`), adjacent `python -m pytest tests\test_ops_mesh.py -q -k
    "discord_native_route or discord_thread_query or discord_reply_and_silent
    or send_direct_channel_poll_uses_discord"` (`4 passed`), `ruff check`,
    and `mypy`.

- [x] `OZ-PROV-001D` WhatsApp document filename projection
  - Source: `openclaw-main/extensions/whatsapp/src/send.ts`,
    `openclaw-main/extensions/whatsapp/src/outbound-media-contract.ts`, and
    `openclaw-main/extensions/whatsapp/src/inbound/send-api.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`
  - Contract: WhatsApp route-backed document sends derive a filename from the
    outbound media URL path, decode URL escapes, fall back to `file`, preserve
    reply context, and include the Cloud API document `filename` field on
    single and split document sends.
  - Evidence required: focused WhatsApp native document route test, adjacent
    WhatsApp native media/reply/gif/poll route tests, ruff, mypy
  - Status: checkpointed in `05c4f0fc`
  - Weight: 1
  - Last verified: 2026-05-02, focused WhatsApp document route test (`1
    passed`), adjacent `python -m pytest tests\test_ops_mesh.py -q -k
    "whatsapp_native_route or whatsapp_media or whatsapp_reply_document or
    whatsapp_gif_video or send_direct_channel_poll_uses_whatsapp"` (`5
    passed`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001E` Discord native media iteration
  - Source: `openclaw-main/src/channels/plugins/outbound/direct-text-media.ts`,
    `openclaw-main/src/plugin-sdk/reply-payload.ts`, and
    `openclaw-main/extensions/discord/src/outbound-payload.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`
  - Contract: Discord route-backed media sends use the shared OpenClaw media
    sequence contract: send one webhook message per media URL, keep text only
    on the first media send, return the final message id, preserve ordered
    message ids in provider metadata, and keep reply/silent/thread options on
    each provider call.
  - Evidence required: focused Discord native media route test, adjacent
    Discord native send/reply/thread/poll route tests, ruff, mypy
  - Status: checkpointed in `b5371fd9`
  - Weight: 1
  - Last verified: 2026-05-02, focused Discord media route tests (`2
    passed`), adjacent `python -m pytest tests\test_ops_mesh.py -q -k
    "discord_native_route or discord_media or discord_thread_query or
    discord_reply_and_silent or send_direct_channel_poll_uses_discord"` (`5
    passed`), `ruff check`, and `mypy`.

## Canonical Checklist Format

Use this shape for each bounded seam:

```md
- [ ] Seam name
  - Source: OpenClaw file/test/behavior
  - References: Hermes/Warp paths or `none`
  - Target: OpenZues owner files
  - Contract: input, state change, output, persistence/API/UI behavior
  - Evidence required: focused test, adjacent test, ruff, mypy
  - Status: open | mapped | implemented | verified | checkpointed | blocked
  - Weight: 1 small, 2-3 normal, 5+ broad
  - Last verified: YYYY-MM-DD, command/result
```

Checkbox meanings:

- `[ ]` open
- `[~]` mapped, source/target/proof known
- `[x]` verified with implementation and evidence
- `[!]` blocked by a concrete external blocker

## After-Slice Update Checklist

- [ ] Update the seam checkbox and status.
- [ ] Update percent only if verified weighted numerator changed.
- [ ] Record fully implemented behavior.
- [ ] Record remaining checklist items.
- [ ] Record source, target, and reference paths.
- [ ] Record exact verification command and result.
- [ ] Record the next queue head.
- [ ] Record commit hash after checkpoint.
- [ ] Record push branch/URL only after successful push.
