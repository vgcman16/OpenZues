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
| Repo-wide OpenClaw parity in OpenZues | ~52.8% | Active, broad parity still open | `docs/openclaw-parity-progress.md`, `docs/openclaw-parity-unresolved-seams.md` |
| Active gateway/session/tool-contract path | ~98.3% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Chat/session contract subfamily | ~98.3% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Runtime/CLI/doctor native bridge | ~99.9% | Mostly landed; packaging and installed plugin depth remain | `docs/openclaw-parity-progress.md` |
| Hermes reference surface | 80-85% | Reference-only rough status from repo inspection | `docs/tracking/03-hermes-reference-status.md` |
| Warp reference surface | Mixed | Reference-only; client-local plus backend-gated areas | `docs/tracking/04-warp-reference-status.md` |

## Current Worktree Boundary

The `tts.personas` / `tts.setPersona` gateway and CLI parity slice is verified
and ready for checkpointing with these intended files:

- `src/openzues/services/gateway_tts.py`
- `src/openzues/services/gateway_node_methods.py`
- `src/openzues/services/gateway_method_policy.py`
- `src/openzues/cli.py`
- `tests/test_gateway_node_methods.py`
- `tests/test_gateway_method_policy.py`
- `tests/test_cli.py`
- `docs/openclaw-parity-progress.md`
- `docs/openclaw-parity-unresolved-seams.md`
- `docs/tracking/00-cross-repo-implementation-tracker.md`
- `docs/tracking/01-openzues-openclaw-parity-status.md`

Known untracked temp/log artifacts are unrelated and must remain unstaged.

## Current Queue

| ID | Area | Status | Percent Impact | Next Action |
| --- | --- | --- | ---: | --- |
| OZ-RM-001 | Sandboxed remote inbound provider media staging | Checkpointed and pushed in `2e6a3ed8` | Repo-wide +0.1%, chat/session +0.1%, gateway session/tool +0.1% | Done; continue `OZ-RT-001` |
| OZ-RT-001 | Runtime-control hard gaps | Active | Repo-wide +0.1%, active gateway/method +0.1% | `tts.personas` / `tts.setPersona` verified; next source-backed base-method gap is `talk.realtime.*` |
| OZ-PKG-001 | Packaging/distribution breadth | Open | Broad | Map Windows-first doctor/package surfaces against OpenClaw |
| OZ-PLUGIN-001 | Real installed plugin module import/activation | Checkpointed in `9fb5098b` | Repo-wide +0.1%, gateway session/tool +0.1% | `plugins.uiDescriptors` done; continue next source-backed plugin/runtime base-method gap |
| OZ-COMP-001 | Companion apps/nodes parity | Open | Broad | Inventory OpenClaw macOS/iOS/Android node behavior and choose first local bridge seam |
| OZ-PROV-001 | Provider-native outbound/inbound breadth | Open | Medium | Continue provider-specific send/poll/replay metadata gaps |

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
  - Status: verified; checkpoint commit pending
  - Weight: 1
  - Last verified: 2026-05-02, focused gateway persona tests (`2 passed`),
    focused policy test (`1 passed`), focused CLI tests (`2 passed`),
    adjacent `python -m pytest tests\test_gateway_node_methods.py -q -k
    "tts_"` (`9 passed`), adjacent `python -m pytest tests\test_cli.py -q
    -k "tts_"` (`11 passed`), adjacent `python -m pytest
    tests\test_gateway_nodes_api.py -q -k "tts"` (`6 passed`), `ruff
    check`, and `mypy`.

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
