# Cross-Repo Implementation Tracker

Last updated: 2026-05-05

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
| Repo-wide OpenClaw parity in OpenZues | ~77.7% | Active, broad parity still open | `docs/openclaw-parity-progress.md`, `docs/openclaw-parity-unresolved-seams.md` |
| Active gateway/session/tool-contract path | ~99.9% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Chat/session contract subfamily | ~98.3% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Runtime/CLI/doctor native bridge | ~99.9% | Mostly landed; packaging and installed plugin depth remain | `docs/openclaw-parity-progress.md` |
| Hermes reference surface | 80-85% | Reference-only rough status from repo inspection | `docs/tracking/03-hermes-reference-status.md` |
| Warp reference surface | Mixed | Reference-only; client-local plus backend-gated areas | `docs/tracking/04-warp-reference-status.md` |

## Current Worktree Boundary

The imported plugin provider-auth facade helper shim slice is checkpointed in `35ca435d`.
Any follow-up changes should target the next queue head only:

- `src/openzues/schemas.py`
- `src/openzues/database.py`
- `src/openzues/app.py`
- `src/openzues/services/msteams_webhook_auth.py`
- `src/openzues/services/gateway_outbound_runtime.py`
- `src/openzues/services/ops_mesh.py`
- `src/openzues/services/gateway_channels.py`
- `src/openzues/cli.py`
- `src/openzues/web/templates/index.html`
- `src/openzues/web/static/app.js`
- `tests/test_ops_mesh.py`
- `tests/test_gateway_node_methods.py`
- `tests/test_cli.py`
- `tests/test_app.py`
- `docs/openclaw-parity-progress.md`
- `docs/openclaw-parity-unresolved-seams.md`
- `docs/tracking/00-cross-repo-implementation-tracker.md`
- `docs/tracking/01-openzues-openclaw-parity-status.md`
- `docs/tracking/02-openclaw-source-domain-map.md`

Known untracked temp/log artifacts are unrelated and must remain unstaged.

## Current Queue

| ID | Area | Status | Percent Impact | Next Action |
| --- | --- | --- | ---: | --- |
| OZ-RM-001 | Sandboxed remote inbound provider media staging | Checkpointed and pushed in `2e6a3ed8` | Repo-wide +0.1%, chat/session +0.1%, gateway session/tool +0.1% | Done; continue `OZ-RT-001` |
| OZ-RT-001 | Runtime-control hard gaps | Checkpointed in `8a0e6ac6` | Repo-wide +0.1%, active gateway/method +0.1% | Small base-method sweep done; rotate to provider/runtime breadth |
| OZ-PKG-001 | Packaging/distribution breadth | Update status package-manager dependency posture checkpointed in `f1ac67da` | Repo-wide +0.1%, runtime/CLI/doctor +0.1% | Continue release/update/package breadth |
| OZ-PLUGIN-001 | Real installed plugin module import/activation | Provider-auth facade helper shim checkpointed in `35ca435d` | Repo-wide +0.1%, plugin metadata/runtime +0.1% | Continue broader plugin SDK helper/runtime breadth |
| OZ-CANVAS-001 | Media/voice/web/canvas breadth | Canvas shortcode normalization checkpointed in `c34e4a77` | Repo-wide +0.1%, browser/canvas/nodes/voice +0.1% | Continue media/canvas/provider breadth |
| OZ-COMP-001 | Companion apps/nodes parity | QR JSON setup-code contract checkpointed in `b79b87c3` | Repo-wide +0.1%, companion/setup breadth +0.1% | Continue companion QR/setup-code human/remote breadth |
| OZ-PROV-001 | Provider-native outbound/inbound breadth | Feishu/Lark post/rich-text embedded media hydration checkpointed in `ed3aedb5` | Repo-wide +0.1%, provider-native breadth +0.1% | Rotate to `OZ-PLUGIN-001` |

## Active Slice Detail

- [x] `OZ-PLUGIN-001UN` Imported provider-auth facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-auth.ts`,
    `openclaw-main/src/agents/github-copilot-token.ts`,
    `openclaw-main/src/agents/copilot-dynamic-headers.ts`,
    `openclaw-main/src/agents/model-auth-env.ts`
  - References: `openclaw-main/src/agents/github-copilot-token.test.ts`,
    `openclaw-main/src/image-generation/openai-compatible-image-provider.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/provider-discovery-contract.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/provider-auth`, resolve Copilot IDE headers, derive
    Copilot API base URLs, exchange/cache Copilot tokens through fakeable
    runtime adapters, detect provider API keys from env candidates, and reach
    facade helpers through the generic SDK during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `35ca435d`
  - Weight: 1
  - Last verified: 2026-05-05, focused provider-auth facade proof
    (`1 passed`), adjacent provider-auth proof (`5 passed, 880 deselected`),
    adjacent imported-plugin/runtime proof (`82 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UM` Imported provider-auth-login helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-auth-login.ts`,
    `openclaw-main/src/plugin-sdk/provider-auth-login.runtime.ts`,
    `openclaw-main/src/commands/chutes-oauth.ts`,
    `openclaw-main/src/plugins/provider-openai-codex-oauth.ts`,
    `openclaw-main/src/plugin-sdk/github-copilot-login.ts`
  - References: `openclaw-main/src/commands/chutes-oauth.test.ts`,
    `openclaw-main/src/plugins/provider-openai-codex-oauth.test.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/provider-auth-contract.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/provider-auth-login`, resolve
    `loginOpenAICodexOAuth`, `loginChutes`, and
    `githubCopilotLoginCommand`, receive a precise unavailable boundary for
    the interactive OpenClaw login runtime, and reach the same helpers through
    the generic SDK during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9186faf7`
  - Weight: 1
  - Last verified: 2026-05-05, focused provider-auth-login proof
    (`1 passed`), adjacent provider-auth proof (`4 passed, 880 deselected`),
    adjacent imported-plugin/runtime proof (`81 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UL` Imported provider-auth API-key helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-auth-api-key.ts`,
    `openclaw-main/src/plugins/provider-auth-input.ts`,
    `openclaw-main/src/plugins/provider-auth-mode.ts`,
    `openclaw-main/src/plugins/provider-auth-ref.ts`,
    `openclaw-main/src/plugins/provider-auth-helpers.ts`,
    `openclaw-main/src/plugins/provider-api-key-auth.ts`
  - References: `openclaw-main/src/plugins/provider-auth-input.test.ts`,
    `openclaw-main/src/plugins/provider-auth-env-trust.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/provider-auth-api-key`, normalize API-key input,
    validate and preview keys, resolve secret-input modes, build plaintext/ref
    API-key credentials, apply auth-profile config patches with mixed-mode
    order handling, expose API-key auth methods, and reach the same helpers
    through the generic SDK during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `af3d97ea`
  - Weight: 1
  - Last verified: 2026-05-05, focused provider-auth API-key proof
    (`1 passed`), adjacent provider-auth proof (`3 passed, 880 deselected`),
    adjacent imported-plugin/runtime proof (`80 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UK` Imported provider-auth-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-auth-runtime.ts`
  - References: `openclaw-main/src/plugin-sdk/provider-auth-runtime.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/provider-auth-runtime`, generate OAuth state tokens,
    parse OAuth callback URLs with upstream missing/invalid input diagnostics,
    expose the local callback wait helper, resolve runtime auth/API-key helper
    function exports, and reach the same helpers through the generic SDK during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `cfaae804`
  - Weight: 1
  - Last verified: 2026-05-05, focused provider-auth-runtime proof
    (`1 passed`), adjacent provider-auth/runtime proof
    (`2 passed, 880 deselected`), adjacent imported-plugin/runtime proof
    (`79 passed, 803 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UJ` Imported provider entry/enable/auth-result helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-entry.ts`,
    `openclaw-main/src/plugin-sdk/provider-enable-config.ts`,
    `openclaw-main/src/plugin-sdk/provider-web-fetch-contract.ts`,
    `openclaw-main/src/plugin-sdk/provider-web-search-contract.ts`,
    `openclaw-main/src/plugin-sdk/provider-auth-result.ts`,
    `openclaw-main/src/plugins/provider-api-key-auth.ts`,
    `openclaw-main/src/plugins/provider-catalog.ts`,
    `openclaw-main/src/agents/auth-profiles/identity.ts`
  - References: `openclaw-main/src/plugin-sdk/provider-entry.test.ts`,
    `openclaw-main/src/plugin-sdk/provider-enable-config.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require provider entry,
    enable-config, web-fetch/web-search contract, and auth-result subpaths,
    define single-provider plugin entries, register provider auth methods with
    upstream wizard/env-var defaults, build API-key provider catalogs with
    explicit base-URL overrides, expose static catalogs, enable provider
    plugins without channel normalization, preserve web-fetch/web-search
    enable-contract aliases, return OAuth provider auth profiles/config
    patches, and reach the same helpers through the generic SDK during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0887e67a`
  - Weight: 1
  - Last verified: 2026-05-05, focused provider entry/enable/auth-result
    proof (`1 passed`), adjacent imported-plugin/runtime proof
    (`78 passed, 803 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UI` Imported provider model/catalog helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-model-shared.ts`,
    `openclaw-main/src/plugin-sdk/provider-model-id-normalize.ts`,
    `openclaw-main/src/plugin-sdk/provider-catalog-shared.ts`
  - References: `openclaw-main/src/plugin-sdk/provider-model-shared.test.ts`,
    `openclaw-main/src/plugin-sdk/provider-catalog-shared.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require provider
    model/catalog helper subpaths and use preview model ID normalization,
    provider-hint detection, Claude thinking profiles, replay-family hook
    policies, Google Gemini replay sanitation/reasoning mode, canonical replay
    hook exports, configured model catalog entries, manifest catalog-to-provider
    config conversion, native streaming usage compatibility, scoped/unscoped SDK
    aliases, and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `903343d0`
  - Weight: 1
  - Last verified: 2026-05-05, focused provider model/catalog proof
    (`1 passed`), adjacent imported-plugin/runtime proof
    (`77 passed, 803 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UH` Imported fetch/SSRF helper shim
  - Source: `openclaw-main/src/plugin-sdk/fetch-auth.ts`,
    `openclaw-main/src/plugin-sdk/request-url.ts`,
    `openclaw-main/src/plugin-sdk/ssrf-policy.ts`,
    `openclaw-main/src/plugin-sdk/ssrf-runtime.ts`,
    `openclaw-main/src/infra/net/ssrf.ts`
  - References: `openclaw-main/src/plugin-sdk/fetch-auth.test.ts`,
    `openclaw-main/src/plugin-sdk/ssrf-policy.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require fetch/SSRF helper
    subpaths and use bearer-scope fetch retry fallback, request URL
    extraction, private-network opt-in policies, legacy private-network alias
    migration, SSRF policy merging, HTTP private-network target checks,
    hostname suffix allowlists, hostname allowlist policy expansion,
    private/internal host detection, pinned-host policy checks, guarded-fetch
    stubs, scoped/unscoped SDK aliases, and generic SDK availability during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `f4a23a25`
  - Weight: 1
  - Last verified: 2026-05-05, focused fetch/SSRF helper proof (`1 passed`),
    adjacent imported-plugin/runtime proof (`76 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UG` Imported webhook helper shim
  - Source: `openclaw-main/src/plugin-sdk/webhook-path.ts`,
    `openclaw-main/src/plugin-sdk/webhook-memory-guards.ts`,
    `openclaw-main/src/plugin-sdk/webhook-request-guards.ts`,
    `openclaw-main/src/plugin-sdk/webhook-targets.ts`
  - References: `openclaw-main/src/plugin-sdk/webhook-memory-guards.test.ts`,
    `openclaw-main/src/plugin-sdk/webhook-request-guards.test.ts`,
    `openclaw-main/src/plugin-sdk/webhook-targets.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require webhook helper
    subpaths and use path normalization/resolution, fixed-window rate limits,
    bounded counters, anomaly tracking, JSON content-type checks, request
    guard rejection responses, in-flight request limits, target
    registration/lifecycle cleanup, request-path target resolution, request
    pipeline dispatch/release behavior, sync/async single-target matching,
    auth rejection responses, non-POST rejection, scoped/unscoped SDK aliases,
    and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `98a00cc5`
  - Weight: 1
  - Last verified: 2026-05-05, focused webhook helper proof (`1 passed`),
    adjacent imported-plugin/runtime proof (`75 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UF` Imported command-auth native shim
  - Source: `openclaw-main/src/plugin-sdk/command-auth.ts`,
    `openclaw-main/src/plugin-sdk/command-auth-native.ts`,
    `openclaw-main/src/plugin-sdk/command-gating.ts`,
    `openclaw-main/src/plugin-sdk/command-surface.ts`,
    `openclaw-main/src/plugin-sdk/native-command-registry.ts`,
    `openclaw-main/src/channels/native-command-session-targets.ts`
  - References: `openclaw-main/src/auto-reply/commands-registry.test.ts`,
    `openclaw-main/src/channels/command-gating.test.ts`,
    `openclaw-main/src/channels/native-command-session-targets.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require command-auth native
    helper subpaths and use mode-aware command authorization,
    control-command gates, dual text-command gates, native session target
    resolution, command body alias normalization, text-command routing, native
    command specs, command text serialization, Telegram command pagination
    keyboards, stored model override lookup, scoped/unscoped SDK aliases, and
    generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `1bbd7ed9`
  - Weight: 1
  - Last verified: 2026-05-05, focused command-auth native proof (`1 passed`),
    adjacent plugin invoke proof (`74 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001UE` Imported command-status shim
  - Source: `openclaw-main/src/plugin-sdk/command-status.ts`,
    `openclaw-main/src/auto-reply/command-status-builders.ts`
  - References: `openclaw-main/src/auto-reply/status.test.ts`,
    `openclaw-main/src/plugin-sdk/command-auth.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/command-status` and use help text builders,
    slash-command list builders, config/debug flag filtering, skill-command
    projection, category grouping, paginated command lists, scoped/unscoped SDK
    aliases, deprecated `command-auth` compatibility exports, generic SDK
    availability, and UTF-8-safe native Node bridge output during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent command-auth
    compatibility test, adjacent plugin invoke tests, ruff, mypy
  - Status: checkpointed in `6c22af79`
  - Weight: 1
  - Last verified: 2026-05-05, focused command-status proof (`1 passed`),
    focused adjacent command-auth compatibility proof (`2 passed`), adjacent
    plugin invoke proof (`73 passed, 803 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001UD` Imported windows-spawn shim
  - Source: `openclaw-main/src/plugin-sdk/windows-spawn.ts`
  - References: `openclaw-main/src/plugin-sdk/windows-spawn.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/windows-spawn` and use PATH/PATHEXT executable
    resolution, direct/non-Windows spawning, JS/CJS/MJS Node entrypoint
    wrapping, CMD/BAT shim entrypoint inspection, package.json `bin` fallback
    resolution, fail-closed unresolved wrapper policy, opt-in shell fallback,
    materialized argv construction, and generic SDK availability during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `1c172bde`
  - Weight: 1
  - Last verified: 2026-05-05, focused windows-spawn proof (`1 passed`),
    adjacent plugin invoke proof (`72 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001UC` Imported provider-selection-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/provider-selection-runtime.ts`
  - References: `openclaw-main/src/plugin-sdk/provider-selection-runtime.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/provider-selection-runtime` and use explicit provider
    selection, missing explicit provider reporting, auto-select ordering,
    canonical plus selected raw config merging, configured-capability provider
    resolution, no-provider/provider-not-configured failure codes, and generic
    SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `395d23fc`
  - Weight: 1
  - Last verified: 2026-05-05, focused provider-selection-runtime proof
    (`1 passed`), adjacent plugin invoke proof (`71 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UB` Imported group-access shim
  - Source: `openclaw-main/src/plugin-sdk/group-access.ts`,
    `openclaw-main/src/config/runtime-group-policy.ts`
  - References: `openclaw-main/src/plugin-sdk/group-access.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/group-access` and use sender-scoped group policy
    downgrade, route-level allowlist decisions, matched group access decisions,
    sender allowlist decisions, missing-provider fail-closed fallback policy,
    and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `88510816`
  - Weight: 1
  - Last verified: 2026-05-05, focused group-access proof (`1 passed`),
    adjacent plugin invoke proof (`70 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001UA` Imported allowlist-config-edit shim
  - Source: `openclaw-main/src/plugin-sdk/allowlist-config-edit.ts`
  - References: `openclaw-main/src/plugin-sdk/allowlist-config-edit.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/allowlist-config-edit` and use DM/group and legacy-DM
    config path resolution, configured entry coercion, flat/nested override
    collectors/resolvers, token-gated account-scoped name resolution,
    account-scoped config edit target selection, add/remove/duplicate edit
    semantics, top-level/default-account writes, legacy `dm.allowFrom` cleanup,
    and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `37677120`
  - Weight: 1
  - Last verified: 2026-05-05, focused allowlist-config-edit proof
    (`1 passed`), adjacent plugin invoke proof (`69 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001TZ` Imported channel-setup shim
  - Source: `openclaw-main/src/plugin-sdk/channel-setup.ts`,
    `openclaw-main/src/plugin-sdk/optional-channel-setup.ts`,
    `openclaw-main/src/plugin-sdk/setup.ts`,
    `openclaw-main/src/channels/plugins/setup-wizard-helpers.ts`,
    `openclaw-main/src/terminal/links.ts`
  - References: `openclaw-main/src/plugin-sdk/channel-setup.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-setup` and use optional channel setup
    adapters, optional setup wizards, combined optional setup surfaces, setup
    validation/finalize unavailable messages, docs-link formatting, setup entry
    splitting, setup channel enabled patching, top-level channel DM policy
    descriptors/setters, `DEFAULT_ACCOUNT_ID`, and generic SDK availability
    during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0b86d5ea`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-setup proof (`1 passed`),
    adjacent plugin invoke proof (`68 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TY` Imported command-auth shim
  - Source: `openclaw-main/src/plugin-sdk/command-auth.ts`,
    `openclaw-main/src/plugin-sdk/access-groups.ts`,
    `openclaw-main/src/plugin-sdk/direct-dm.ts`,
    `openclaw-main/src/auto-reply/command-detection.ts`,
    `openclaw-main/src/auto-reply/commands-registry.ts`,
    `openclaw-main/src/channels/command-gating.ts`
  - References: `openclaw-main/src/plugin-sdk/command-auth.test.ts`,
    `openclaw-main/src/plugin-sdk/direct-dm.test.ts`,
    `openclaw-main/src/plugin-sdk/access-groups.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/command-auth` and use sender command authorization
    across DM, group, pairing-store, and access-group allowlists,
    runtime-backed authorization wrappers, direct-DM authorization outcome
    projection, command-gating and detection re-exports, direct-DM/access-group
    compatibility re-exports, deprecated command-status builders, and generic
    SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d06e2c42`
  - Weight: 1
  - Last verified: 2026-05-05, focused command-auth proof (`1 passed`),
    adjacent plugin invoke proof (`67 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TX` Imported channel-pairing shim
  - Source: `openclaw-main/src/plugin-sdk/channel-pairing.ts`,
    `openclaw-main/src/plugin-sdk/pairing-access.ts`,
    `openclaw-main/src/channels/plugins/pairing-adapters.ts`,
    `openclaw-main/src/pairing/pairing-challenge.ts`,
    `openclaw-main/src/pairing/pairing-store.ts`
  - References: `openclaw-main/src/plugin-sdk/channel-pairing.test.ts`,
    `openclaw-main/src/channels/plugins/pairing-adapters.test.ts`,
    `openclaw-main/src/pairing/pairing-challenge.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-pairing` and use scoped pairing controller
    store access, channel-bound challenge issuers, pairing reply delivery,
    prefix-stripping allowFrom adapters, text pairing adapters, logged
    approval notifiers, allowFrom store path/read helpers, and generic SDK
    availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `f0a21c8c`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-pairing proof (`1 passed`),
    adjacent plugin invoke proof (`66 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TW` Imported channel-send-result shim
  - Source: `openclaw-main/src/plugin-sdk/channel-send-result.ts`
  - References: `openclaw-main/src/plugin-sdk/channel-send-result.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-send-result` and use channel result stamping,
    batch stamping, empty outbound result construction, raw send result
    normalization with `Error` projection, attached text/media/poll adapter
    wrapping, raw text/media adapter wrapping, and generic SDK availability
    during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `c73fb961`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-send-result proof
    (`1 passed`), adjacent plugin invoke proof (`65 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001TV` Imported direct-DM shim
  - Source: `openclaw-main/src/plugin-sdk/direct-dm.ts`,
    `openclaw-main/src/plugin-sdk/inbound-envelope.ts`,
    `openclaw-main/src/plugin-sdk/inbound-reply-dispatch.ts`
  - References: `openclaw-main/src/plugin-sdk/direct-dm.test.ts`,
    `openclaw-main/src/plugin-sdk/nostr.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/direct-dm` and use direct-DM access/guard-policy
    re-exports plus direct peer route resolution, session-store path lookup,
    previous timestamp reads, envelope formatting, finalized direct-DM context
    payload projection, inbound session recording, buffered reply dispatch,
    generic SDK availability, and the `channel-inbound` re-export during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `6534f0db`
  - Weight: 1
  - Last verified: 2026-05-05, focused direct-DM proof (`1 passed`),
    adjacent plugin invoke proof (`64 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TU` Imported direct-DM guard-policy shim
  - Source: `openclaw-main/src/plugin-sdk/direct-dm-guard-policy.ts`
  - References: `openclaw-main/src/plugin-sdk/direct-dm.test.ts`,
    `openclaw-main/src/plugin-sdk/channel-inbound.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/direct-dm-guard-policy` and use default and
    overrideable pre-crypto guard policy construction, allowed kind overrides,
    future-skew/ciphertext/plaintext byte limits, nested rate-limit default
    merging, generic SDK availability, and the `channel-inbound` re-export
    during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `02803c84`
  - Weight: 1
  - Last verified: 2026-05-05, focused direct-DM guard-policy proof (`1 passed`),
    adjacent plugin invoke proof (`63 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TT` Imported direct-DM access shim
  - Source: `openclaw-main/src/plugin-sdk/direct-dm-access.ts`
  - References: `openclaw-main/src/plugin-sdk/direct-dm.test.ts`,
    `openclaw-main/src/plugin-sdk/nostr.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/direct-dm-access` and use pairing-store direct-DM
    allowlist reads, access-group expansion for configured/store allowlists,
    open-DM allowlist blocking, resolved direct-DM access projection, command
    authorization runtime delegation, sender command-allow checks, pairing
    challenge callbacks, blocked-sender callbacks, and generic SDK
    availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `5258f537`
  - Weight: 1
  - Last verified: 2026-05-05, focused direct-DM access proof (`1 passed`),
    adjacent plugin invoke proof (`62 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TS` Imported access-groups shim
  - Source: `openclaw-main/src/plugin-sdk/access-groups.ts`
  - References: `openclaw-main/src/plugin-sdk/command-auth.ts`,
    `openclaw-main/src/plugin-sdk/direct-dm-access.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/access-groups` and use access-group allowFrom prefix
    parsing, `message.senders` wildcard/channel membership resolution, async
    membership resolver fallback with error swallowing, duplicate group-name
    dedupe, matched access-group projection, allowFrom expansion with sender
    entries, and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `93a4347c`
  - Weight: 1
  - Last verified: 2026-05-05, focused access-groups proof (`1 passed`),
    adjacent plugin invoke proof (`61 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TR` Imported allow-from shim
  - Source: `openclaw-main/src/plugin-sdk/allow-from.ts`,
    `openclaw-main/src/channels/allowlist-match.ts`,
    `openclaw-main/src/channels/allow-from.ts`,
    `openclaw-main/src/channels/allowlists/resolve-utils.ts`, and
    `openclaw-main/src/channels/plugins/chat-target-prefixes.ts`
  - References: `openclaw-main/src/plugins/contracts/plugin-sdk-subpaths.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/allow-from` and use normalized allowFrom formatting,
    chat-aware sender matching, wildcard/simple and compiled allowlist
    matching, DM/group allowFrom source merging, sender-id gates, allowlist
    resolution summaries, canonicalize/merge/patch helpers, config-entry user
    extraction, sequential input mapping, runtime mapping summaries, and
    generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `bc6e1344`
  - Weight: 1
  - Last verified: 2026-05-05, focused allow-from proof (`1 passed`),
    adjacent plugin invoke proof (`60 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TQ` Imported channel-policy shim
  - Source: `openclaw-main/src/plugin-sdk/channel-policy.ts`,
    `openclaw-main/src/security/dm-policy-shared.ts`,
    `openclaw-main/src/plugin-sdk/group-access.ts`,
    `openclaw-main/src/config/group-policy.ts`, and
    `openclaw-main/src/plugin-sdk/channel-config-helpers.ts`
  - References: `openclaw-main/src/plugins/contracts/plugin-sdk-runtime-api-guardrails.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-policy` and use DM/group access decisions,
    store-backed allowlist reads, command gating, sender/group-route policy
    evaluation, sender-scoped group policy downgrades, tools-by-sender
    matching, channel group policy/mention/tool resolution, scoped DM security
    descriptors, dangerous-name mutable allowlist warnings, native setting
    coercion, policy constants, and generic SDK availability during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9f7b7abd`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-policy proof (`1 passed`),
    adjacent plugin invoke proof (`59 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TP` Imported channel-route shim
  - Source: `openclaw-main/src/plugin-sdk/channel-route.ts` and
    `openclaw-main/src/plugin-sdk/channel-route.test.ts`
  - References: `openclaw-main/src/channels/plugins/target-parsing.ts`,
    `openclaw-main/src/utils/delivery-context.shared.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-route` and use route normalization,
    target/thread accessors, dedupe/compact/deprecated key aliases, exact
    route matching, conversation-sharing comparisons, injected explicit-target
    parsing, numeric thread id stringification, account normalization, and
    generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0f67c4a0`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-route proof (`1 passed`),
    adjacent plugin invoke proof (`58 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TO` Imported channel-inbound shim
  - Source: `openclaw-main/src/plugin-sdk/channel-inbound.ts`,
    `openclaw-main/src/auto-reply/envelope.ts`,
    `openclaw-main/src/auto-reply/reply/mentions.ts`,
    `openclaw-main/src/channels/mention-gating.ts`,
    `openclaw-main/src/channels/inbound-debounce-policy.ts`,
    `openclaw-main/src/channels/location.ts`, and
    `openclaw-main/src/media/inbound-path-policy.ts`
  - References: `openclaw-main/extensions/zalouser/src/monitor.ts`,
    `openclaw-main/extensions/irc/src/runtime-api.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-inbound` and use mention regex/matching,
    nested and legacy mention gate decisions, inbound envelope/from-label
    formatting, envelope option projection, location text/context projection,
    inbound path root normalization/merge, text debounce policy, channel
    inbound debouncer wrapping, log re-exports, and generic SDK availability
    during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `aa9825e0`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-inbound proof (`1 passed`),
    adjacent plugin invoke proof (`57 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TN` Imported channel-feedback shim
  - Source: `openclaw-main/src/plugin-sdk/channel-feedback.ts`,
    `openclaw-main/src/channels/ack-reactions.ts`,
    `openclaw-main/src/channels/status-reactions.ts`,
    `openclaw-main/src/agents/identity.ts`,
    `openclaw-main/src/channels/logging.ts`, and
    `openclaw-main/src/infra/outbound/target-errors.ts`
  - References: `openclaw-main/extensions/telegram/src/exec-approvals.ts`,
    `openclaw-main/extensions/slack/src/exec-approvals.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-feedback` and use ack reaction resolution,
    ack gates, WhatsApp ack mode checks, ack send/remove handles,
    post-reply cleanup, missing-target errors, tool emoji resolution, status
    reaction controller transitions/cleanup, feedback logging exports, exported
    constants, and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7c188623`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-feedback proof (`1 passed`),
    adjacent plugin invoke proof (`56 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TM` Imported channel-reply-pipeline shim
  - Source: `openclaw-main/src/plugin-sdk/channel-reply-pipeline.ts`,
    `openclaw-main/src/auto-reply/reply/source-reply-delivery-mode.ts`,
    `openclaw-main/src/channels/reply-prefix.ts`, and
    `openclaw-main/src/channels/typing.ts`
  - References: `openclaw-main/src/auto-reply/reply/source-reply-delivery-mode.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-reply-pipeline` and use
    `createChannelReplyPipeline`, `createReplyPrefixContext`,
    `createReplyPrefixOptions`, `createTypingCallbacks`, and
    `resolveChannelSourceReplyDeliveryMode`, preserving account response-prefix
    context, transform-payload passthrough, provided-vs-constructed typing
    callbacks, requested/native/group/channel/direct/default visible-reply
    delivery modes, message-tool availability fallback, and generic SDK
    availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `f9f1bf6a`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-reply-pipeline proof
    (`1 passed`), adjacent plugin invoke proof (`55 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001TL` Imported channel-reply-options-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/channel-reply-options-runtime.ts`,
    `openclaw-main/src/channels/reply-prefix.ts`, and
    `openclaw-main/src/channels/typing.ts`
  - References: `openclaw-main/extensions/matrix/src/matrix/monitor/runtime-api.ts`,
    `openclaw-main/extensions/matrix/src/matrix/monitor/handler.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-reply-options-runtime` and use
    `createReplyPrefixOptions` plus `createTypingCallbacks`, preserving
    account/channel/global response-prefix precedence, `auto` identity-name
    prefixes, mutable model-selection prefix context, short model-name
    extraction, typing start/stop cleanup, stop dedupe, start/stop error hooks,
    closed-callback behavior, and generic SDK availability during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `61357e44`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-reply-options proof
    (`1 passed`), adjacent plugin invoke proof (`54 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001TK` Imported reply-dedupe shim
  - Source: `openclaw-main/src/plugin-sdk/reply-dedupe.ts` and
    `openclaw-main/src/auto-reply/reply/inbound-dedupe.ts`
  - References: `openclaw-main/extensions/slack/src/monitor.tool-result.test.ts`,
    `openclaw-main/extensions/whatsapp/src/auto-reply.test-harness.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/reply-dedupe` and use `resetInboundDedupe`,
    preserving shared `Symbol.for("openclaw.inboundDedupeCache")` cache
    clearing, shared `Symbol.for("openclaw.inboundDedupeInflight")` in-flight
    set clearing, and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `e3ec8d6c`
  - Weight: 1
  - Last verified: 2026-05-05, focused reply-dedupe proof (`1 passed`),
    adjacent plugin invoke proof (`53 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TJ` Imported reply-reference shim
  - Source: `openclaw-main/src/plugin-sdk/reply-reference.ts`,
    `openclaw-main/src/auto-reply/reply/reply-reference.ts`, and
    `openclaw-main/src/auto-reply/reply/reply-threading.ts`
  - References: `openclaw-main/extensions/slack/src/action-threading.ts`,
    `openclaw-main/extensions/slack/src/action-runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/reply-reference` and use reply/thread reference
    helpers, preserving off/first/all/batched mode behavior, existing-id
    precedence, non-consuming `peek`, consuming `use`, `markSent`, seeded
    `hasReplied`, `allowReference=false`, batched implicit-current-message
    policy, and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `3bdeeac0`
  - Weight: 1
  - Last verified: 2026-05-05, focused reply-reference proof (`1 passed`),
    adjacent plugin invoke proof (`52 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TI` Imported reply-history shim
  - Source: `openclaw-main/src/plugin-sdk/reply-history.ts` and
    `openclaw-main/src/auto-reply/reply/history.ts`
  - References: `openclaw-main/extensions/bluebubbles/src/monitor-processing-api.ts`,
    `openclaw-main/extensions/zalouser/src/monitor.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/reply-history` and use bounded per-thread history
    helpers, preserving mutable returned history arrays, LRU key eviction,
    disabled limit/null-entry no-ops, pending/current message markers,
    exclude-last defaults, clear behavior, and generic SDK availability during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `738186ae`
  - Weight: 1
  - Last verified: 2026-05-05, focused reply-history proof (`1 passed`),
    adjacent plugin invoke proof (`51 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TH` Imported markdown-table-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/markdown-table-runtime.ts`,
    `openclaw-main/src/config/markdown-tables.ts`, and
    `openclaw-main/src/markdown/tables.ts`
  - References: provider/channel outbound markdown rendering paths
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/markdown-table-runtime` and use
    `resolveMarkdownTableMode` plus `convertMarkdownTables`, preserving
    channel/account markdown-table config precedence, `block` fallback to code
    mode, default code mode, table pass-through for `off`/non-table text,
    code-fenced table rendering, bullet table rendering with empty-cell skips,
    and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `6e51b8a9`
  - Weight: 1
  - Last verified: 2026-05-05, focused markdown-table-runtime proof
    (`1 passed`), adjacent plugin invoke proof (`50 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001TG` Imported channel-inbound-debounce shim
  - Source: `openclaw-main/src/plugin-sdk/channel-inbound-debounce.ts` and
    `openclaw-main/src/auto-reply/inbound-debounce.ts`
  - References: `openclaw-main/extensions/telegram/src/bot-handlers.runtime.ts`,
    `openclaw-main/extensions/whatsapp/src/inbound/monitor.ts`,
    `openclaw-main/extensions/feishu/src/monitor.message-handler.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-inbound-debounce` and use
    `resolveInboundDebounceMs` plus `createInboundDebouncer`, preserving
    override/by-channel/base debounce resolution, finite/truncated/clamped
    milliseconds, keyed timer-backed buffering, forced `flushKey`, same-key
    immediate ordering, saturated-key fallback, non-throwing `onError`
    reporting, and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9ac09500`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-inbound-debounce proof
    (`1 passed`), adjacent plugin invoke proof (`49 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001TF` Imported concurrency-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/concurrency-runtime.ts` and
    `openclaw-main/src/utils/run-with-concurrency.ts`
  - References: `openclaw-main/extensions/slack/src/monitor/message-handler/prepare-content.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/concurrency-runtime` and use
    `runTasksWithConcurrency`, preserving empty-task completion, bounded worker
    count, result ordering, stop/continue error modes, first-error tracking,
    task-error callbacks, and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `e6bd981e`
  - Weight: 1
  - Last verified: 2026-05-05, focused concurrency-runtime proof (`1 passed`),
    adjacent plugin invoke proof (`48 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TE` Imported global-singleton shim
  - Source: `openclaw-main/src/plugin-sdk/global-singleton.ts`,
    `openclaw-main/src/shared/global-singleton.ts`, and
    `openclaw-main/src/shared/scoped-expiring-id-cache.ts`
  - References: `openclaw-main/extensions/discord/src/components-registry.ts`,
    `openclaw-main/extensions/memory-core/src/dreaming-narrative.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/global-singleton` and use `resolveGlobalSingleton`,
    `resolveGlobalMap`, and `createScopedExpiringIdCache`, preserving
    symbol-keyed process-global singleton reuse, global map resolution,
    scoped/id string coercion, ttl cleanup, cleanup-threshold pruning, clear
    behavior, and generic SDK availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d773e608`
  - Weight: 1
  - Last verified: 2026-05-05, focused global-singleton proof (`1 passed`),
    adjacent plugin invoke proof (`46 passed, 804 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TD` Imported command-detection shim
  - Source: `openclaw-main/src/plugin-sdk/command-detection.ts`,
    `openclaw-main/src/auto-reply/command-detection.ts`,
    `openclaw-main/src/auto-reply/commands-registry-list.ts`, and
    `openclaw-main/src/auto-reply/commands-registry-normalize.ts`
  - References: `openclaw-main/extensions/feishu/src/monitor.reaction.test.ts`,
    `openclaw-main/extensions/discord/src/monitor/message-handler.preflight.ts`,
    `openclaw-main/extensions/whatsapp/src/auto-reply/monitor/runtime-api.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/command-detection` and use `hasControlCommand`,
    `isControlCommandMessage`, `hasInlineCommandTokens`, and
    `shouldComputeCommandAuthorized`, preserving bot-addressed slash
    normalization, full-message control-command matching, argument-aware
    aliases, command feature gates, inbound metadata stripping, abort-trigger
    fallback, inline token detection, and generic SDK availability during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `c0c5e8fa`
  - Weight: 1
  - Last verified: 2026-05-05, focused command-detection proof (`1 passed`),
    adjacent plugin invoke proof (`46 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TC` Imported media-mime shim
  - Source: `openclaw-main/src/plugin-sdk/media-mime.ts`,
    `openclaw-main/src/media/mime.ts`, and
    `openclaw-main/src/media/constants.ts`
  - References: `openclaw-main/extensions/browser/src/sdk-setup-tools.ts`,
    `openclaw-main/extensions/discord/src/send.voice.ts`,
    `openclaw-main/extensions/msteams/src/media-helpers.ts`,
    `openclaw-main/extensions/signal/src/monitor.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/media-mime` and use `detectMime`,
    `extensionForMime`, `getFileExtension`, `normalizeMimeType`, and
    `mediaKindFromMime`, preserving header normalization, URL/path extension
    parsing, extension/MIME maps, CAF/PDF/image/ZIP sniffing, generic
    ZIP/octet-stream precedence, media-kind classification, and generic SDK
    plus `media-runtime` MIME helper availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ad1d6cee`
  - Weight: 1
  - Last verified: 2026-05-05, focused media-mime proof (`1 passed`),
    adjacent plugin invoke proof (`45 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001TB` Imported command-primitives-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/command-primitives-runtime.ts`,
    `openclaw-main/src/auto-reply/reply/abort-primitives.ts`, and
    `openclaw-main/src/auto-reply/reply/btw-command.ts`
  - References: `openclaw-main/extensions/telegram/src/sequential-key.ts`,
    `openclaw-main/extensions/feishu/src/sequential-key.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/command-primitives-runtime` and use
    `isAbortRequestText` plus `isBtwRequestText`, preserving slash/colon
    command normalization, bot-mention stripping, abort trigger/trailing
    punctuation handling, BTW command detection, and generic SDK proxy
    availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a39876b1`
  - Weight: 1
  - Last verified: 2026-05-05, focused command-primitives-runtime proof
    (`1 passed`), adjacent plugin invoke proof (`44 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001TA` Imported lazy-value shim
  - Source: `openclaw-main/src/plugin-sdk/lazy-value.ts`
  - References: `openclaw-main/src/plugin-sdk/plugin-entry.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/lazy-value` and use `createCachedLazyValueGetter`,
    preserving one-shot lazy factory memoization, literal value wrapping,
    nullish fallback resolution, and generic SDK proxy availability during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ef545716`
  - Weight: 1
  - Last verified: 2026-05-05, focused lazy-value proof (`1 passed`),
    adjacent plugin invoke proof (`43 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SZ` Imported keyed-async-queue shim
  - Source: `openclaw-main/src/plugin-sdk/keyed-async-queue.ts`
  - References: `openclaw-main/extensions/matrix/src/matrix/sdk.ts`,
    `openclaw-main/extensions/discord/src/monitor/inbound-worker.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/keyed-async-queue` and use `enqueueKeyedTask` plus
    `KeyedAsyncQueue`, preserving per-key serialization, unrelated-key
    concurrency, task-failure recovery, enqueue/settle hooks, tail cleanup,
    testing observability, and generic SDK proxy availability during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4307d460`
  - Weight: 1
  - Last verified: 2026-05-05, focused keyed-async-queue proof (`1 passed`),
    adjacent plugin invoke proof (`42 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SY` Imported retry-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/retry-runtime.ts`,
    `openclaw-main/src/infra/retry.ts`, and
    `openclaw-main/src/infra/retry-policy.ts`
  - References: `openclaw-main/extensions/discord/src/api.ts`,
    `openclaw-main/extensions/telegram/src/bot/delivery.send.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/retry-runtime` and use `resolveRetryConfig`,
    `retryAsync`, `createRateLimitRetryRunner`, `createTelegramRetryRunner`,
    and `TELEGRAM_RETRY_DEFAULTS`, preserving retry config clamping,
    numeric/options retry execution, retry-after handling, should-retry
    short-circuiting, channel API retry heuristics, Telegram defaults, and
    generic SDK proxy availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4608fbc7`
  - Weight: 1
  - Last verified: 2026-05-05, focused retry-runtime proof (`1 passed`),
    adjacent plugin invoke proof (`41 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SX` Imported dedupe-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/dedupe-runtime.ts` and
    `openclaw-main/src/infra/dedupe.ts`
  - References: `openclaw-main/extensions/telegram/src/bot-updates.ts`,
    `openclaw-main/extensions/slack/src/sent-thread-cache.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/dedupe-runtime` and use `createDedupeCache` plus
    `resolveGlobalDedupeCache`, preserving blank-key ignores, ttl/indefinite
    retention, touch-on-read max-size pruning, floor-to-zero clearing,
    delete/clear/size operations, process-global singleton resolution, and
    generic SDK proxy availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `865c9df0`
  - Weight: 1
  - Last verified: 2026-05-05, focused dedupe-runtime proof (`1 passed`),
    adjacent plugin invoke proof (`40 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SW` Imported text-autolink-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/text-autolink-runtime.ts` and
    `openclaw-main/src/shared/text/auto-linked-file-ref.ts`
  - References: `openclaw-main/extensions/matrix/src/matrix/format.ts`,
    `openclaw-main/extensions/telegram/src/format.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/text-autolink-runtime` and use
    `isAutoLinkedFileRef`, preserving protocol stripping, allowed extension
    matching, dotted parent-segment rejection, `text-runtime` reexport, and
    generic SDK proxy availability during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `bcce41be`
  - Weight: 1
  - Last verified: 2026-05-05, focused text-autolink-runtime proof (`1
    passed`), adjacent plugin invoke proof (`39 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001SV` Imported response-limit-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/response-limit-runtime.ts` and
    `openclaw-main/src/media/read-response-with-limit.ts`
  - References: `openclaw-main/extensions/matrix/src/matrix/sdk/read-response-with-limit.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/response-limit-runtime` and use
    `readResponseWithLimit`, preserving bounded Response buffer reads, stream
    prefix limiting, default/custom overflow errors, and idle-timeout hooks
    during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7c0035bf`
  - Weight: 1
  - Last verified: 2026-05-05, focused response-limit-runtime proof (`1
    passed`), adjacent plugin invoke proof (`38 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001SU` Imported target-resolver-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/target-resolver-runtime.ts` and
    `openclaw-main/src/channels/plugins/target-resolvers.ts`
  - References: `openclaw-main/extensions/slack/src/channel.ts`,
    `openclaw-main/extensions/discord/src/channel.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/target-resolver-runtime` and use
    `buildUnresolvedTargetResults` plus `resolveTargetsWithOptionalToken`,
    preserving missing-token unresolved row projection, token trimming,
    resolver invocation, and mapped results during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4ea6901b`
  - Weight: 1
  - Last verified: 2026-05-05, focused target-resolver-runtime proof (`1
    passed`), adjacent plugin invoke proof (`37 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001ST` Imported transport-ready-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/transport-ready-runtime.ts` and
    `openclaw-main/src/infra/transport-ready.ts`
  - References: `openclaw-main/extensions/imessage/src/monitor/monitor-provider.ts`,
    `openclaw-main/extensions/signal/src/monitor.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/transport-ready-runtime` and use
    `waitForTransportReady`, preserving immediate success, timeout
    logging/error, abort return, and polling interval floor behavior during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `dc7e76c6`
  - Weight: 1
  - Last verified: 2026-05-05, focused transport-ready-runtime proof (`1
    passed`), adjacent plugin invoke proof (`36 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001SS` Imported async-lock-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/async-lock-runtime.ts` and
    `openclaw-main/src/infra/json-files.ts`
  - References: `openclaw-main/extensions/memory-core/src/dreaming-narrative.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/async-lock-runtime` and use `createAsyncLock`,
    preserving serial queued execution and lock release after rejected critical
    sections during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9cc677fe`
  - Weight: 1
  - Last verified: 2026-05-05, focused async-lock-runtime proof (`1 passed`),
    adjacent plugin invoke proof (`35 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SR` Imported collection-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/collection-runtime.ts` and
    `openclaw-main/src/infra/map-size.ts`
  - References: `openclaw-main/extensions/slack/src/monitor/thread.ts`,
    `openclaw-main/extensions/slack/src/monitor/thread-resolution.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/collection-runtime` and use `pruneMapToMaxSize`,
    preserving floored limits, non-positive clears, oldest-entry deletion, and
    undersized-map no-op behavior during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `624e55e4`
  - Weight: 1
  - Last verified: 2026-05-05, focused collection-runtime proof (`1 passed`),
    adjacent plugin invoke proof (`34 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SQ` Imported secure-random-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/secure-random-runtime.ts` and
    `openclaw-main/src/infra/secure-random.ts`
  - References: `openclaw-main/extensions/slack/src/monitor/external-arg-menu-store.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/secure-random-runtime` and use
    `generateSecureToken` / `generateSecureUuid`, preserving default, custom,
    and zero-byte base64url token behavior plus UUID generation during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `78d458e7`
  - Weight: 1
  - Last verified: 2026-05-05, focused secure-random-runtime proof (`1
    passed`), adjacent plugin invoke proof (`33 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001SP` Imported number-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/number-runtime.ts` and
    `openclaw-main/src/infra/parse-finite-number.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/number-runtime` and use `parseFiniteNumber` for
    finite numbers plus `parseFloat`-style numeric strings, while preserving
    upstream blank, invalid, `NaN`, infinity, and non-string rejection behavior
    during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7e272081`
  - Weight: 1
  - Last verified: 2026-05-05, focused number-runtime proof (`1 passed`),
    adjacent plugin invoke proof (`32 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SO` Imported time-runtime shim
  - Source: `openclaw-main/src/plugin-sdk/time-runtime.ts` and
    `openclaw-main/src/infra/format-time/format-datetime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/time-runtime` and use `resolveTimezone`,
    `formatUtcTimestamp`, and `formatZonedTimestamp` with upstream
    invalid-timezone, UTC, seconds-display, and zoned formatting behavior
    during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `eb944ee1`
  - Weight: 1
  - Last verified: 2026-05-05, focused time-runtime proof (`1 passed`),
    adjacent plugin invoke proof (`31 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SN` Imported channel-logging shim
  - Source: `openclaw-main/src/plugin-sdk/channel-logging.ts` and
    `openclaw-main/src/channels/logging.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-logging` and use `logInboundDrop`,
    `logTypingFailure`, and `logAckFailure` with upstream log message
    formatting; generic SDK fallbacks also expose the same helpers to
    `channel-feedback` and `channel-inbound` imports during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `c42b0d77`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-logging proof (`1 passed`),
    adjacent plugin invoke proof (`30 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SM` Imported dangerous-name shim
  - Source: `openclaw-main/src/plugin-sdk/dangerous-name-runtime.ts` and
    `openclaw-main/src/config/dangerous-name-matching.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/dangerous-name-runtime` and use
    `isDangerousNameMatchingEnabled` plus
    `resolveDangerousNameMatchingEnabled` for provider defaults and
    account-level boolean overrides during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `01473fb4`
  - Weight: 1
  - Last verified: 2026-05-05, focused dangerous-name proof (`1 passed`),
    adjacent plugin invoke proof (`29 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SL` Imported string-normalization shim
  - Source: `openclaw-main/src/plugin-sdk/string-normalization-runtime.ts` and
    `openclaw-main/src/shared/string-normalization.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/string-normalization-runtime` and use string entry
    normalization, lowercase entry normalization, hyphen slug normalization,
    at/hash slug normalization, and the same `text-runtime` reexports during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `06cd452d`
  - Weight: 1
  - Last verified: 2026-05-05, focused string-normalization proof (`1
    passed`), adjacent plugin invoke proof (`28 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001SK` Imported text-chunking shim
  - Source: `openclaw-main/src/plugin-sdk/text-chunking.ts` and
    `openclaw-main/src/shared/text-chunking.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/text-chunking` and use `chunkTextForOutbound` with
    upstream empty-input behavior, newline/space boundary preference,
    hard-limit fallback, and non-positive limit behavior during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `20267310`
  - Weight: 1
  - Last verified: 2026-05-05, focused text-chunking proof (`1 passed`),
    adjacent plugin invoke proof (`27 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SJ` Imported channel-status shim
  - Source: `openclaw-main/src/plugin-sdk/channel-status.ts`,
    `openclaw-main/src/channels/account-snapshot-fields.ts`, and
    `openclaw-main/src/channels/plugins/pairing-message.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-status` and use credential snapshot field
    projection, configured-status resolution, required credential status
    resolution, the pairing-approved message, and channel status helper
    reexports during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `14ff20a1`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-status proof (`1 passed`),
    adjacent plugin invoke proof (`26 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SI` Imported status-helper shim
  - Source: `openclaw-main/src/plugin-sdk/status-helpers.ts`,
    `openclaw-main/src/channels/plugins/status-issues/shared.ts`, and
    `openclaw-main/src/plugin-sdk/status-helpers.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/status-helpers` and use channel/account runtime
    default snapshots, base/probe/webhook/token channel summaries,
    runtime/base/computed account snapshots, configured credential issue
    collectors, runtime last-error issue projection, enabled-account issue
    collection, and match metadata helpers during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `41323ea2`
  - Weight: 1
  - Last verified: 2026-05-05, focused status-helper proof (`1 passed`),
    adjacent plugin invoke proof (`25 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SH` Imported channel-actions shim
  - Source: `openclaw-main/src/plugin-sdk/channel-actions.ts`,
    `openclaw-main/src/agents/tools/common.ts`,
    `openclaw-main/src/channels/plugins/actions/shared.ts`,
    `openclaw-main/src/channels/plugins/actions/reaction-message-id.ts`,
    `openclaw-main/src/agents/date-time.ts`,
    `openclaw-main/src/agents/sandbox-paths.ts`, `openclaw-main/src/polls.ts`,
    `openclaw-main/src/agents/schema/typebox.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/channel-actions` and use common action gates,
    parameter readers, reaction id fallback, result/schema helpers, timestamp
    normalization, media URL guards, poll selection limits, and available-tag
    parsing during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `447d15ff`
  - Weight: 1
  - Last verified: 2026-05-05, focused channel-actions proof (`1 passed`),
    adjacent plugin invoke proof (`24 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SG` Imported boolean-param shim
  - Source: `openclaw-main/src/plugin-sdk/boolean-param.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/boolean-param` and use loose boolean and
    `"true"`/`"false"` string tool parameter reading during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `65bd842f`
  - Weight: 1
  - Last verified: 2026-05-05, focused boolean-param proof (`1 passed`),
    adjacent plugin invoke proof (`23 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SF` Imported tool-payload shim
  - Source: `openclaw-main/src/plugin-sdk/tool-payload.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/tool-payload` and use structured tool result payload
    extraction plus standalone plain-text tool-call block parsing, allowed-tool
    filtering, payload-size guarding, and block stripping during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `387717ed`
  - Weight: 1
  - Last verified: 2026-05-05, focused tool-payload proof (`1 passed`),
    adjacent plugin invoke proof (`22 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SE` Imported account-core/account-resolution shim
  - Source: `openclaw-main/src/plugin-sdk/account-core.ts`,
    `openclaw-main/src/plugin-sdk/account-resolution.ts`,
    `openclaw-main/src/plugin-sdk/account-resolution-runtime.ts`,
    `openclaw-main/src/plugin-sdk/account-configured-ids.ts`,
    `openclaw-main/src/channels/chat-type.ts`, `openclaw-main/src/utils.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/account-core`, `account-resolution`, and
    `account-resolution-runtime` and use account-core reexports, configured id
    listing, default-account credential fallback, chat-type normalization,
    E.164 normalization, home-relative path resolution, and path existence
    checks during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `47fa2f39`
  - Weight: 1
  - Last verified: 2026-05-05, focused account-core proof (`1 passed`),
    adjacent plugin invoke proof (`21 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SD` Imported account-helper shim
  - Source: `openclaw-main/src/plugin-sdk/account-helpers.ts`,
    `openclaw-main/src/channels/plugins/account-helpers.ts`,
    `openclaw-main/src/channels/plugins/account-action-gate.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/account-helpers` and use account list/default
    resolution, normalized account lookup, merged account config projection,
    account/webhook snapshots, and account action gates during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `6d2cf33b`
  - Weight: 1
  - Last verified: 2026-05-05, focused account-helper proof (`1 passed`),
    adjacent plugin invoke proof (`20 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001SC` Imported reply-payload helper shim
  - Source: `openclaw-main/src/plugin-sdk/reply-payload.ts`,
    `openclaw-main/src/channels/plugins/media-payload.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/reply-payload` and use outbound payload
    normalization, media URL extraction/counting, sendable content
    projection, reasoning payload detection, attachment-link formatting, and
    source-shaped media/text send helper exports during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `5d628f16`
  - Weight: 1
  - Last verified: 2026-05-05, focused reply-payload helper proof (`1
    passed`), adjacent plugin invoke proof (`19 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001SB` Imported reply-chunking helper shim
  - Source: `openclaw-main/src/plugin-sdk/reply-chunking.ts`,
    `openclaw-main/src/auto-reply/chunk.ts`,
    `openclaw-main/src/auto-reply/tokens.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/reply-chunking` and use length/newline text
    chunking, provider/account chunk limit and mode resolution, and silent
    reply token helpers during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `b000f51c`
  - Weight: 1
  - Last verified: 2026-05-05, focused reply-chunking helper proof (`1
    passed`), adjacent plugin invoke proof (`18 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001SA` Imported routing helper shim
  - Source: `openclaw-main/src/plugin-sdk/routing.ts`,
    `openclaw-main/src/routing/session-key.ts`,
    `openclaw-main/src/sessions/session-key-utils.ts`,
    `openclaw-main/src/routing/account-id.ts`,
    `openclaw-main/src/routing/account-lookup.ts`,
    `openclaw-main/src/infra/outbound/thread-id.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/routing` and use common routing/session helper
    exports for account and agent id normalization, session key
    parsing/building, thread suffix handling, account lookup,
    message-channel normalization, and outbound thread id normalization during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2cf7fb27`
  - Weight: 1
  - Last verified: 2026-05-05, focused routing helper proof (`1 passed`),
    adjacent plugin invoke proof (`17 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001RZ` Imported secret-input helper shim
  - Source: `openclaw-main/src/plugin-sdk/secret-input.ts`,
    `openclaw-main/src/config/types.secrets.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/secret-input` and use literal secret normalization,
    SecretRef coercion, inspect-mode resolution, and configured-secret
    detection during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `76e3c638`
  - Weight: 1
  - Last verified: 2026-05-05, focused secret-input helper proof (`1
    passed`), adjacent plugin invoke proof (`16 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001RY` Imported temp-path helper shim
  - Source: `openclaw-main/src/plugin-sdk/temp-path.ts`,
    `openclaw-main/src/infra/temp-download.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/temp-path` and use temp filename sanitization,
    deterministic random temp path construction, preferred temp roots, and
    temp download cleanup helpers during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d6a73b21`
  - Weight: 1
  - Last verified: 2026-05-05, focused temp-path helper proof (`1 passed`),
    adjacent plugin invoke proof (`15 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001RX` Imported error-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/error-runtime.ts`,
    `openclaw-main/src/infra/errors.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/error-runtime` and use error formatting,
    code/name extraction, uncaught formatting, and error-graph helpers during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7888c8de`
  - Weight: 1
  - Last verified: 2026-05-05, focused error-runtime helper proof (`1
    passed`), adjacent plugin invoke proof (`14 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001RW` Imported text-runtime string helper shim
  - Source: `openclaw-main/src/plugin-sdk/text-runtime.ts`,
    `openclaw-main/src/shared/string-coerce.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/text-runtime` and use common string-coerce helpers
    (`normalizeOptionalString`, `normalizeNullableString`,
    `normalizeStringifiedOptionalString`, `hasNonEmptyString`) during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `91918c38`
  - Weight: 1
  - Last verified: 2026-05-05, focused text-runtime helper proof (`1
    passed`), adjacent plugin invoke proof (`13 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001RV` Imported runtime tool factory context
  - Source: `openclaw-main/src/plugins/tool-types.ts`,
    `openclaw-main/src/plugins/registry.ts`,
    `openclaw-main/src/plugins/tools.ts`,
    `openclaw-main/src/gateway/tools-invoke-shared.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`,
    `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_plugin_runtime.py`,
    `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools registered as
    `api.registerTool(factory, { name })` are advertised, resolved at
    `tools.invoke` time, passed config/runtimeConfig, workspace, agent/session,
    sender ownership, and delivery route metadata, and then execute with
    `execute(toolCallId, args)`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ef254cbf`
  - Weight: 1
  - Last verified: 2026-05-05, focused runtime tool factory-context proof (`1
    passed`), adjacent plugin invoke proof (`12 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001RU` Imported ESM runtime tool execution
  - Source: `openclaw-main/src/plugins/loader.ts`,
    `openclaw-main/src/plugins/sdk-alias.ts`,
    `openclaw-main/src/plugins/tools.ts`,
    `openclaw-main/src/gateway/tools-invoke-shared.ts`
  - References: Hermes/Warp `none`
  - Target: `tests/test_gateway_node_methods.py` plus the native runtime
    executor bridge in `src/openzues/cli.py` from `d80b0252`
  - Contract: imported ESM-style OpenClaw runtime entries transformed into
    temporary CommonJS modules preserve SDK alias shims and executable tools
    through `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `311f37e1`
  - Weight: 1
  - Last verified: 2026-05-05, focused ESM runtime invoke proof (`1
    passed`), adjacent plugin invoke proof (`11 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001RT` Imported CommonJS runtime tool execution
  - Source: `openclaw-main/src/plugins/registry.ts`,
    `openclaw-main/src/plugins/tools.ts`,
    `openclaw-main/src/gateway/tools-invoke-shared.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw plugin runtime entries that register tools
    with `execute` are not metadata-only; `tools.invoke` resolves the imported
    runtime spec, preserves before-call and allowlist behavior, reloads the
    runtime entry in a bounded Node bridge, and calls
    `execute(toolCallId, args)`.
  - Evidence required: focused gateway method test, adjacent plugin invoke and
    runtime import tests, ruff, mypy
  - Status: checkpointed in `d80b0252`
  - Weight: 1
  - Last verified: 2026-05-05, focused imported runtime invoke proof (`1
    passed`), adjacent plugin invoke proof (`10 passed, 803 deselected`),
    adjacent runtime import proof (`2 passed, 512 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PROV-001CR` Feishu/Lark post/rich-text embedded media hydration
  - Source: `openclaw-main/extensions/feishu/src/post.ts`,
    `openclaw-main/extensions/feishu/src/bot-content.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native Feishu/Lark read actions resolve localized post payloads,
    collect embedded `img.image_key` and `media.file_key` elements in order,
    download image resources as `type=image` and media resources as
    `type=file`, store bytes under the inbound attachment workspace, and
    project ordered media metadata.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `ed3aedb5`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu post-media proof (`1 passed`),
    adjacent Feishu provider proof (`29 passed, 347 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PROV-001CQ` Feishu/Lark message-resource read hydration
  - Source: `openclaw-main/extensions/feishu/src/media.ts`,
    `openclaw-main/extensions/feishu/src/bot-content.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native Feishu/Lark read actions parse media bodies, prefer
    video `file_key` over thumbnail `image_key`, request message resources
    with `type=file`, retry as `type=media` on Feishu HTTP 502, save bytes
    under the inbound attachment workspace, and project placeholder, path,
    filename, content-type, byte-length, and SHA-256 metadata.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `65da0455`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu read-media fallback proof (`1
    passed`), adjacent Feishu provider proof (`28 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CP` Feishu/Lark direct provider-route media sends
  - Source: `openclaw-main/extensions/feishu/src/media.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: direct `gateway.send`/`send_direct_channel_message` calls on
    native Feishu/Lark routes accept media URLs, upload through the verified
    Feishu media runtime, send the native media payload, and preserve final
    `messageId`, ordered `mediaIds`, `mediaUrls`, chat/channel, and delivery
    provider result metadata.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `77149f94`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu direct media proof (`1 passed`),
    adjacent Feishu provider proof (`27 passed, 347 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PROV-001CO` Feishu/Lark channel capability discovery
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: CLI channel capabilities for Feishu/Lark advertise direct and
    channel chats, replies, threads, media, reactions, edit support,
    `polls=false`, and voice TTS transcode metadata.
  - Evidence required: focused CLI test, adjacent channel-capabilities tests,
    ruff, mypy
  - Status: checkpointed in `326f471f`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu channel capability proof (`1
    passed`), adjacent CLI channel-capabilities proof (`5 passed, 509
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CN` Feishu/Lark mediaMaxMb media-size limits
  - Source: `openclaw-main/extensions/feishu/src/media.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native Feishu media sends resolve account-level
    `mediaMaxMb` before channel-level `mediaMaxMb`, pass the configured byte
    cap into the media loader, and reject oversized media before upload.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `45d6a6bc`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu mediaMaxMb proof (`1 passed`),
    adjacent Feishu provider proof (`26 passed, 347 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PROV-001CM` Feishu/Lark audioAsVoice transcode posture
  - Source: `openclaw-main/extensions/feishu/src/media.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native Feishu media sends carry `audioAsVoice`/`asVoice`,
    transcode compatible audio to `voice.ogg` through a fakeable ffmpeg
    adapter, send native Feishu audio payloads, and fall back to the original
    file attachment if transcode is unavailable.
  - Evidence required: focused runtime tests, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `81c93c0e`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu audioAsVoice proof (`2
    passed`), adjacent Feishu provider proof (`25 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CL` Feishu/Lark mediaLocalRoots local-path guard
  - Source: `openclaw-main/extensions/feishu/src/media.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for Feishu media rejects local
    paths and `file://` media by default, reads channel/account
    `mediaLocalRoots`, allows only files under configured roots, and preserves
    provider upload/send metadata for allowed local files.
  - Evidence required: focused runtime tests, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `78cfda1f`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu local media-root proof (`2
    passed`), adjacent Feishu provider proof (`23 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CK` Feishu/Lark audio/video media sends
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/media.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"` routes Ogg/Opus media through Feishu file upload with
    `file_type="opus"` and `msg_type="audio"`, and routes MP4 video replies
    through `file_type="mp4"`, `msg_type="media"`, and `reply_in_thread=true`.
  - Evidence required: focused runtime tests, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `6e99a40b`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu audio/video media proof (`2
    passed`), adjacent Feishu provider proof (`21 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CJ` Feishu/Lark file media sends
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/media.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"` accepts non-image file `media`, uploads through Feishu
    `im/v1/files`, maps provider file types, sends `msg_type="file"` with
    the returned `file_key`, and preserves route-backed send metadata.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `152dcb38`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu file media send proof (`1
    passed`), adjacent Feishu provider proof (`19 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CI` Feishu/Lark image media sends
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/media.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"` accepts image `media`, loads bytes, uploads through
    Feishu `im/v1/images`, sends `msg_type="image"` with the returned
    `image_key`, and preserves route-backed send metadata.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `64375b92`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu image media send proof (`1
    passed`), adjacent Feishu provider proof (`18 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CH` Feishu/Lark presentation-card sends
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/send.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"` accepts `presentation` blocks on `send`/`thread-reply`,
    renders a Feishu interactive card, sends `msg_type="interactive"` through
    the route-backed message API, and preserves reply-in-thread/fallback
    behavior.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `75edc136`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu presentation-card send proof (`1
    passed`), adjacent Feishu provider proof (`17 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CG` Feishu/Lark reaction message actions
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/reactions.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"` supports `react` add, remove-own, and `clearAll=true`
    bot cleanup plus `reactions` listing through Feishu message-reaction
    endpoints, returning OpenClaw-shaped `{ok, added}`, `{ok, removed}`, and
    `{ok, reactions}` payloads.
  - Evidence required: focused runtime tests, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `1c6b44af`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu reaction action proofs (`2
    passed`), adjacent Feishu provider proof (`16 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CF` Feishu/Lark channel-list message action
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/directory.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"`, `action="channel-list"` supports all/group/user scopes,
    GETs Feishu chat/user directory endpoints with route-backed bearer auth,
    filters query matches client-side, applies provider page-size caps, and
    returns OpenClaw-shaped `{ok, channel, action, groups, peers}` directory
    metadata.
  - Evidence required: focused runtime tests, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `dd915f30`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu channel-list action proofs (`2
    passed`), adjacent Feishu provider proof (`14 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CE` Feishu/Lark member-info message action
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/chat.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"`, `action="member-info"` infers Feishu
    `open_id`/`user_id`/`union_id` mode from upstream member aliases, GETs
    `contact/v3/users/{userId}` for direct profiles or
    `im/v1/chats/{chatId}/members` for chat-member listings with route-backed
    bearer auth, applies the upstream page-size clamp, and returns
    OpenClaw-shaped member/profile or member-list metadata.
  - Evidence required: focused runtime tests, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `ff50511d`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu member-info action proofs (`2
    passed`), adjacent Feishu provider proof (`12 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CD` Feishu/Lark channel-info message action
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/chat.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"`, `action="channel-info"` accepts upstream chat/channel
    aliases, GETs Feishu `im/v1/chats/{chatId}` with route-backed bearer auth,
    and returns OpenClaw-shaped `{ok, provider, action, channel}` chat
    metadata.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `f0bd7837`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu channel-info action proof (`1
    passed`), adjacent Feishu provider proof (`10 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CC` Feishu/Lark list-pins message action
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/pins.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"`, `action="list-pins"` accepts upstream chat/channel
    aliases, forwards time/page options with the upstream page-size clamp,
    GETs Feishu `im/v1/pins` with route-backed bearer auth, normalizes pin
    entries, and returns OpenClaw-shaped `{ok, channel, action, chatId, pins,
    hasMore, pageToken}`.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `b1bfb9e2`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu list-pins action proof (`1
    passed`), adjacent Feishu provider proof (`9 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CB` Feishu/Lark unpin message action
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/pins.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"`, `action="unpin"` accepts upstream message-id aliases,
    DELETEs Feishu `im/v1/pins/{messageId}` with route-backed bearer auth,
    and returns OpenClaw-shaped `{ok, channel, action, messageId}`.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `4f42eae0`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu unpin action proof (`1
    passed`), adjacent Feishu provider proof (`8 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001CA` Feishu/Lark pin message action
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/pins.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"`, `action="pin"` accepts upstream message-id aliases,
    POSTs Feishu `im/v1/pins` with route-backed bearer auth, normalizes Feishu
    pin metadata, and returns OpenClaw-shaped `{ok, channel, action, pin}`.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `1615bdf6`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu pin action proof (`1 passed`),
    adjacent Feishu provider proof (`7 passed, 347 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PROV-001BZ` Feishu/Lark edit message action
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/send.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"`, `action="edit"` accepts upstream message-id aliases,
    enforces exactly one of text/message or card content, PATCHes Feishu
    `im/v1/messages/{messageId}` with route-backed bearer auth, and returns
    OpenClaw-shaped `{ok, channel, action, messageId, contentType}`.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `2203efa7`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu edit action proof (`1 passed`),
    adjacent Feishu provider proof (`6 passed, 347 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PROV-001BY` Feishu/Lark read message action
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/send.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"`, `action="read"` accepts upstream message-id aliases,
    GETs Feishu `im/v1/messages/{messageId}` with route-backed bearer auth,
    parses list and single-message response shapes into the OpenClaw message
    projection, and preserves the upstream-shaped not-found error envelope.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `38f27358`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu read action proof (`1 passed`),
    adjacent Feishu provider proof (`5 passed, 347 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PROV-001BX` Feishu/Lark thread-reply message action
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"`, `action="thread-reply"` requires upstream `messageId` /
    `message_id` / `replyTo` / `reply_to`, accepts the same target and text
    inputs as send, posts to the Feishu reply endpoint with
    `reply_in_thread=true`, and returns OpenClaw-shaped `{ok, channel,
    action, messageId, chatId, channelId, replyToId}`.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `641c8fc7`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu thread-reply action proof (`1
    passed`), adjacent Feishu provider proof (`4 passed, 347 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BW` Feishu/Lark send message action
  - Source: `openclaw-main/extensions/feishu/src/channel.ts`,
    `openclaw-main/extensions/feishu/src/message-action-contract.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="feishu"` or
    `channel="lark"`, `action="send"` accepts upstream `to` / `target` plus
    `text` / `message`, falls back to `toolContext.currentChannelId`, reuses
    the route-backed Feishu post sender, preserves bearer auth and target
    normalization, and returns OpenClaw-shaped `{ok, channel, action,
    messageId, chatId, channelId}`.
  - Evidence required: focused runtime test, adjacent Feishu provider tests,
    ruff, mypy
  - Status: checkpointed in `249f3dbf`
  - Weight: 1
  - Last verified: 2026-05-05, focused Feishu send action proof (`1 passed`),
    adjacent Feishu provider proof (`3 passed, 347 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PROV-001BV` Twitch send message action
  - Source: `openclaw-main/extensions/twitch/src/actions.ts`,
    `openclaw-main/extensions/twitch/src/outbound.ts`,
    `openclaw-main/extensions/twitch/src/actions.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="twitch"`,
    `action="send"` accepts required `message` plus optional `to` scalar
    params, falls back to the native route default channel, shares the
    route-backed Twitch chat sender and markdown stripping path, and returns
    OpenClaw-shaped `{ok, channel, messageId, timestamp}`.
  - Evidence required: focused runtime test, adjacent Twitch provider tests,
    ruff, mypy
  - Status: checkpointed in `9baee646`
  - Weight: 1
  - Last verified: 2026-05-05, focused Twitch send action proof (`1
    passed`), adjacent Twitch provider proof (`3 passed, 346 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BU` Microsoft Teams adaptive-card send action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/send.ts`,
    `openclaw-main/extensions/msteams/src/channel.actions.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="send"` with a `card` payload resolves Teams conversation targets,
    posts an Adaptive Card Bot Framework activity through the native route,
    and returns OpenClaw-shaped `{ok, channel, messageId, conversationId}`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `30fbcc69`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams adaptive-card send
    proof (`1 passed`), adjacent Teams action/provider proof (`16 passed, 332
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BT` Microsoft Teams upload-file message action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/send.ts`,
    `openclaw-main/extensions/msteams/src/send.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="upload-file"` resolves Teams conversation targets, accepts
    OpenClaw `filePath` / `path` / `media` aliases, preserves
    `text`/`content`/`message` plus `filename`/`title` metadata, routes
    through the native Bot Framework send path with FileConsent/Graph upload
    metadata, and returns OpenClaw-shaped `{ok, channel, action, messageId,
    conversationId}` plus `pendingUploadId` when present.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `86be3a2c`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams upload-file proof (`1
    passed`), adjacent Teams action/provider proof (`15 passed, 332
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BS` Microsoft Teams delete message action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/send.ts`,
    `openclaw-main/extensions/msteams/src/send.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="delete"` resolves Teams conversation targets plus `messageId`,
    obtains Bot Framework bearer credentials through route config, DELETEs
    `/activities/{messageId}`, and returns OpenClaw-shaped `{ok, channel,
    conversationId}`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `fd98306a`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams delete proof (`1
    passed`), adjacent Teams action/provider proof (`19 passed, 327
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BR` Microsoft Teams edit message action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/send.ts`,
    `openclaw-main/extensions/msteams/src/send.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="edit"` resolves Teams conversation targets, accepts
    `text`/`content`/`message` content fallback plus `messageId`, obtains
    Bot Framework bearer credentials through route config, PUTs a message
    activity update to `/activities/{messageId}`, and returns OpenClaw-shaped
    `{ok, channel, conversationId}`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `df3f4f0d`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams edit proof (`1
    passed`), adjacent Teams action/provider proof (`18 passed, 327
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BQ` Microsoft Teams channel-info action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/graph-teams.ts`,
    `openclaw-main/extensions/msteams/src/graph-teams.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="channel-info"` trims `teamId`/`channelId`, fetches the Graph team
    channel with the upstream `$select` field set through route-backed Graph
    auth, and returns OpenClaw-shaped `{ok, channel, action, channelInfo}`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `4e6fc71a`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams channel-info proof (`1
    passed`), adjacent Teams action/provider proof (`17 passed, 327
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BP` Microsoft Teams channel-list action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/graph-teams.ts`,
    `openclaw-main/extensions/msteams/src/graph-teams.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="channel-list"` trims `teamId`, fetches Graph team channels with
    the upstream `$select` field set through route-backed Graph auth, follows
    bounded `@odata.nextLink` pagination, and returns OpenClaw-shaped `{ok,
    channel, action, channels, truncated}`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `cf1b7f18`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams channel-list proof (`1
    passed`), adjacent Teams action/provider proof (`16 passed, 327
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BO` Microsoft Teams member-info action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/graph-members.ts`,
    `openclaw-main/extensions/msteams/src/graph-members.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="member-info"` trims `userId`, fetches the Graph user profile with
    the upstream `$select` field set through route-backed Graph auth, and
    returns OpenClaw-shaped `{ok, channel, action, user}`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `8aa5f0a6`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams member-info proof (`1
    passed`), adjacent Teams action/provider proof (`15 passed, 327
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BN` Microsoft Teams search message action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.search.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="search"` resolves route-backed Graph chat/team-channel targets,
    strips double quotes from `query`, clamps numeric `limit` to 1..50, escapes
    OData `from` filters, sends Graph `$search` with
    `ConsistencyLevel=eventual`, and returns OpenClaw-shaped `{ok, channel,
    action, messages}`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `29547a56`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams search proof (`1
    passed`), adjacent Teams action/provider proof (`14 passed, 327
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BM` Microsoft Teams list-pins message action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.read.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="list-pins"` resolves route-backed Graph chat targets, rejects
    channel list-pins with the upstream Graph v1.0 unavailable error, GETs
    `/chats/{chatId}/pinnedMessages?$expand=message`, follows bounded
    `@odata.nextLink` pagination, and returns OpenClaw-shaped `{ok, channel,
    action, pins}` with `id`, `pinnedMessageId`, `messageId`, and `text`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `9531fbe3`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams list-pins proof (`1
    passed`), adjacent Teams action/provider proof (`13 passed, 327
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BL` Microsoft Teams unpin message action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.actions.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="unpin"` accepts `pinnedMessageId` or the upstream `messageId`
    fallback, resolves route-backed Graph chat targets, rejects channel
    unpinning with the upstream Graph v1.0 unavailable error, DELETEs
    `/chats/{chatId}/pinnedMessages/{pinnedMessageId}`, and returns
    OpenClaw-shaped `{ok, channel, action}`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `dafcd607`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams unpin proof (`1
    passed`), adjacent Teams action/provider proof (`12 passed, 327
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BK` Microsoft Teams pin message action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.actions.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="pin"` accepts `target`/`to` plus `messageId`, resolves
    route-backed Graph chat targets, rejects channel pinning with the upstream
    Graph v1.0 unavailable error, POSTs `message@odata.bind` to
    `/chats/{chatId}/pinnedMessages`, and returns OpenClaw-shaped
    `{ok, channel, action, pinnedMessageId}`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `1a99d147`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams pin proof (`1
    passed`), adjacent Teams action/provider proof (`11 passed, 327
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BJ` Microsoft Teams read message action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.read.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="read"` resolves `messageId` plus explicit or tool-context Teams
    targets, obtains route-backed Graph credentials with delegated-token
    preference when available, GETs the Graph message resource through chat or
    team/channel endpoints, and returns OpenClaw-shaped `{ok, channel, action,
    message}` with `id`, `text`, `from`, and `createdAt`.
  - Evidence required: focused runtime test, adjacent Teams action tests,
    ruff, mypy
  - Status: checkpointed in `4d3635c3`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams read proof (`1
    passed`), adjacent Teams action/provider proof (`10 passed, 327
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BI` Microsoft Teams delegated OAuth completion
  - Source: `openclaw-main/extensions/msteams/src/oauth.flow.ts`,
    `openclaw-main/extensions/msteams/src/oauth.token.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `src/openzues/cli.py`,
    `tests/test_cli.py`
  - Contract: native CLI completion parses the full redirect URL, enforces
    state matching, posts the upstream Azure v2 authorization-code form
    payload with redirect URI, code verifier, client secret, and scopes,
    requires a refresh token, applies the five-minute expiry buffer, persists
    delegated access/refresh tokens with scopes/user metadata, and omits
    secrets/tokens from output.
  - Evidence required: focused CLI test, adjacent Teams/setup CLI tests, ruff,
    mypy
  - Status: checkpointed in `3695ca29`
  - Weight: 1
  - Last verified: 2026-05-05, focused delegated OAuth completion proof
    (`1 passed`), adjacent Teams/setup CLI proof (`6 passed, 507
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BH` Microsoft Teams delegated OAuth setup bootstrap
  - Source: `openclaw-main/extensions/msteams/src/oauth.flow.ts`,
    `openclaw-main/extensions/msteams/src/oauth.shared.ts`,
    `openclaw-main/extensions/msteams/src/setup-surface.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `src/openzues/cli.py`,
    `tests/test_cli.py`
  - Contract: native CLI setup resolves Teams route credentials, enables
    `channels.msteams.delegatedAuth`, emits upstream redirect/callback
    metadata, builds an Azure v2 delegated OAuth URL with state, default
    scopes, PKCE S256 challenge, and `prompt=consent`, returns the verifier
    for completion, and does not leak the app password.
  - Evidence required: focused CLI test, adjacent Teams/setup CLI tests, ruff,
    mypy
  - Status: checkpointed in `6f368d37`
  - Weight: 1
  - Last verified: 2026-05-05, focused delegated OAuth setup proof
    (`1 passed`), adjacent Teams/setup CLI proof (`5 passed, 507
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BG` Microsoft Teams delegated refresh-token flow
  - Source: `openclaw-main/extensions/msteams/src/token.ts`,
    `openclaw-main/extensions/msteams/src/oauth.token.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/database.py`,
    `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: expired Teams delegated Graph token rows refresh through Azure
    using persisted refresh tokens/scopes before app-token fallback; refreshed
    access tokens are persisted and old refresh tokens are preserved when the
    provider omits a replacement.
  - Evidence required: focused runtime test, adjacent Teams reaction/probe
    tests, ruff, mypy
  - Status: checkpointed in `34a34a44`
  - Weight: 1
  - Last verified: 2026-05-05, focused delegated refresh-token proof
    (`1 passed`), adjacent Teams reaction/probe proof (`10 passed, 326
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BF` Microsoft Teams expired delegated-token fallback
  - Source: `openclaw-main/extensions/msteams/src/token.ts`,
    `openclaw-main/extensions/msteams/src/graph.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: Teams Graph reaction actions prefer usable stored delegated
    tokens, but skip expired stored SSO rows so app Graph auth handles the
    request instead of sending stale bearer tokens to Graph.
  - Evidence required: focused runtime test, adjacent Teams reaction/probe
    tests, ruff, mypy
  - Status: checkpointed in `ddbeb84f`
  - Weight: 1
  - Last verified: 2026-05-05, focused expired delegated-token fallback proof
    (`1 passed`), adjacent Teams reaction/probe proof (`9 passed, 326
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BE` Microsoft Teams inbound media auth fallback
  - Source: `openclaw-main/extensions/msteams/src/attachments/download.ts`,
    `openclaw-main/extensions/msteams/src/attachments/shared.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: production Teams media staging first tries unauthenticated fetch,
    then retries 401/403 media responses with route-backed Graph or Bot
    Framework bearer credentials when the target URL is in the auth allowlist,
    preserving Graph-first scope order for Graph/SharePoint URLs.
  - Evidence required: focused runtime test, adjacent Teams inbound tests,
    ruff, mypy
  - Status: checkpointed in `5460ebf5`
  - Weight: 1
  - Last verified: 2026-05-05, focused inbound media auth-fallback proof
    (`1 passed`), adjacent Teams inbound proof (`9 passed, 325 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001BD` Microsoft Teams feedback reflection learning/follow-up
  - Source: `openclaw-main/extensions/msteams/src/feedback-reflection.ts`,
    `openclaw-main/extensions/msteams/src/feedback-reflection-store.ts`,
    `openclaw-main/extensions/msteams/src/feedback-reflection-prompt.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: negative Teams feedback builds the reflection prompt, runs a
    fakeable reflection service, stores a bounded session learning file with
    Windows-safe naming, respects cooldown, and sends personal follow-up
    messages through the native outbound runtime when requested.
  - Evidence required: focused runtime test, adjacent Teams invoke/inbound
    tests, ruff, mypy
  - Status: checkpointed in `45c4ca7a`
  - Weight: 1
  - Last verified: 2026-05-05, focused feedback reflection proof (`1 passed`),
    adjacent Teams invoke/inbound proof (`16 passed, 317 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PROV-001BC` Microsoft Teams inbound media staging
  - Source: `openclaw-main/extensions/msteams/src/attachments/download.ts`,
    `openclaw-main/extensions/msteams/src/attachments/remote-media.ts`,
    `openclaw-main/extensions/msteams/src/attachments/payload.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler/inbound-media.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: Teams downloadable attachments are resolved through a fakeable
    fetch adapter, host-allowlisted and size-capped, stored under the inbound
    gateway attachment store, and projected as OpenClaw-style `MediaUrl`,
    `MediaUrls`, `MediaPath`, `MediaPaths`, and `MediaTypes` metadata while
    placeholder text continues into session delivery.
  - Evidence required: focused runtime test, adjacent Teams inbound tests,
    ruff, mypy
  - Status: checkpointed in `eda4db73`
  - Weight: 1
  - Last verified: 2026-05-05, focused inbound media staging proof (`1 passed`),
    adjacent Teams inbound proof (`8 passed, 324 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PROV-001BB` Microsoft Teams inbound attachment URL metadata
  - Source: `openclaw-main/extensions/msteams/src/attachments/download.ts`,
    `openclaw-main/extensions/msteams/src/attachments/shared.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler/inbound-media.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: Teams message attachments with `content.downloadUrl` or
    `contentUrl` preserve a deduped `mediaUrls` array on native inbound
    results while placeholder text continues into session delivery.
  - Evidence required: focused runtime test, adjacent Teams inbound tests,
    ruff, mypy
  - Status: checkpointed in `2205ca86`
  - Weight: 1
  - Last verified: 2026-05-05, focused inbound media URL proof (`1 passed`),
    adjacent Teams inbound proof (`8 passed, 323 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PROV-001BA` Microsoft Teams delegated-auth probe posture
  - Source: `openclaw-main/extensions/msteams/src/probe.ts`,
    `openclaw-main/extensions/msteams/src/token.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `src/openzues/database.py`,
    `tests/test_ops_mesh.py`
  - Contract: native Teams readiness probes include safe `delegatedAuth`
    status when SSO is configured, using the newest persisted token for the
    configured connection to project scopes, user principal, user id, and
    expiry without leaking the bearer.
  - Evidence required: focused runtime test, adjacent Teams probe/SSO/action
    tests, ruff, mypy
  - Status: checkpointed in `2f4e2496`
  - Weight: 1
  - Last verified: 2026-05-05, focused delegated-auth probe proof
    (`1 passed`), adjacent Teams probe/SSO/action proof
    (`11 passed, 319 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AZ` Microsoft Teams stored delegated-token reaction writes
  - Source: `openclaw-main/extensions/msteams/src/graph.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.ts`,
    `openclaw-main/extensions/msteams/src/sso-token-store.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: native Teams `react` / `unreact` Graph beta writes prefer a
    persisted delegated Graph bearer keyed by configured SSO
    `(connectionName, requester sender id)` and fall back to app-only Graph
    credentials only when no stored delegated token is available.
  - Evidence required: focused runtime test, adjacent Teams SSO/action tests,
    ruff, mypy
  - Status: checkpointed in `507c90ad`
  - Weight: 1
  - Last verified: 2026-05-05, focused delegated-token reaction proof
    (`1 passed`), adjacent Teams SSO/action proof
    (`17 passed, 312 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AY` Microsoft Teams feedback-disabled invoke handling
  - Source: `openclaw-main/extensions/msteams/src/monitor-handler.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: Teams `message/submitAction` feedback invokes are consumed when
    `channels.msteams.feedbackEnabled` is false, but do not resolve or persist
    a session transcript feedback event; native result metadata marks the
    consume as disabled/unrecorded.
  - Evidence required: focused runtime test, adjacent Teams invoke/inbound
    tests, ruff, mypy
  - Status: checkpointed in `34346a60`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams disabled-feedback proof
    (`1 passed`), adjacent Teams invoke/inbound proof
    (`15 passed, 313 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AX` Microsoft Teams group welcome lifecycle
  - Source: `openclaw-main/extensions/msteams/src/monitor-handler.ts`,
    `openclaw-main/extensions/msteams/src/welcome-card.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: non-personal `conversationUpdate` events where the bot is in
    `membersAdded` and `groupWelcomeCard` is enabled POST the
    `buildGroupWelcomeText`-shaped Bot Framework activity to the conversation
    activities endpoint and return safe delivery metadata.
  - Evidence required: focused runtime test, adjacent Teams inbound tests,
    ruff, mypy
  - Status: checkpointed in `299a8655`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams group welcome proof
    (`1 passed`), adjacent Teams inbound proof (`7 passed, 320 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AW` Microsoft Teams personal welcome-card lifecycle
  - Source: `openclaw-main/extensions/msteams/src/monitor-handler.ts`,
    `openclaw-main/extensions/msteams/src/welcome-card.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: personal `conversationUpdate` events where the bot is in
    `membersAdded` resolve configured Teams app credentials, fetch a Bot
    Framework bearer, and POST the Adaptive Card welcome message with
    configured prompt starters to the conversation activities endpoint.
  - Evidence required: focused runtime test, adjacent Teams inbound tests,
    ruff, mypy
  - Status: checkpointed in `72b1e637`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams welcome-card proof
    (`1 passed`), adjacent Teams inbound proof (`6 passed, 320 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AV` Microsoft Teams attachment-only inbound placeholders
  - Source: `openclaw-main/extensions/msteams/src/attachments/html.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler/message-handler.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: Teams message activities with no text or HTML-text fallback but
    with attachments route OpenClaw-shaped `<media:image>` /
    `<media:document>` placeholders into session delivery, using MIME,
    filename, and Teams file-download metadata to classify images.
  - Evidence required: focused runtime test, adjacent Teams inbound tests,
    ruff, mypy
  - Status: checkpointed in `86f9fa74`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams media placeholder
    proof (`1 passed`), adjacent Teams inbound proof (`5 passed, 320
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AU` Microsoft Teams Bot Framework webhook JWT validation
  - Source: `openclaw-main/extensions/msteams/src/sdk.ts`,
    `openclaw-main/extensions/msteams/src/monitor.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/app.py`,
    `src/openzues/services/msteams_webhook_auth.py`, `tests/test_app.py`,
    `tests/test_msteams_webhook_auth.py`
  - Contract: when native Teams app credentials are configured, OpenZues
    validates `Bearer` webhook tokens before body parsing by resolving
    issuer-specific JWKS, verifying RS256 signatures, enforcing the OpenClaw
    Bot Framework/Entra/STS issuer list, accepting `appId`, `api://appId`,
    and `https://api.botframework.com` audiences, and requiring global
    audience tokens to carry matching `appid` or `azp`.
  - Evidence required: focused app/JWT tests, adjacent app tests, ruff, mypy
  - Status: checkpointed in `b3f911d2`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams JWT app proof
    (`1 passed`), native validator proof (`3 passed`), adjacent app proof
    (`6 passed, 209 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AT` Microsoft Teams Bot Framework configured webhook path
  - Source: `openclaw-main/extensions/msteams/src/monitor.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/app.py`, `tests/test_app.py`
  - Contract: when `channels.msteams.webhook.path` is configured, OpenZues
    registers that POST path at app startup while keeping `/api/messages` as
    the standard Bot Framework fallback; both paths use the same bearer
    pre-gate, 1 MiB body limit, JSON activity decode, and Ops Mesh Microsoft
    Teams inbound dispatch.
  - Evidence required: focused app test, adjacent app tests, ruff, mypy
  - Status: checkpointed in `91e854a0`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams configured webhook
    path proof (`1 passed`), adjacent app proof (`5 passed, 209 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AS` Microsoft Teams Bot Framework `/api/messages` webhook
  - Source: `openclaw-main/extensions/msteams/src/monitor.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/app.py`, `tests/test_app.py`
  - Contract: standard Bot Framework Teams activity POSTs to `/api/messages`
    are bearer-gated before JSON parsing, bounded to the upstream 1 MiB body
    limit, decoded as activity objects, and dispatched through the native Ops
    Mesh Microsoft Teams inbound handler.
  - Evidence required: focused app tests, adjacent app tests, ruff, mypy
  - Status: checkpointed in `b162bc17`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams `/api/messages`
    proofs (`2 passed`), adjacent app proof (`4 passed, 209 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AR` Microsoft Teams SSO group sender allowlist authorization/drop
  - Source: `openclaw-main/extensions/msteams/src/monitor-handler.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler/access.ts`,
    `openclaw-main/src/security/dm-policy-shared.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: after a non-DM Microsoft Teams sign-in invoke passes route
    allowlist checks, OpenZues evaluates `groupPolicy` and
    `groupAllowFrom`/`allowFrom` before SSO dispatch; blocked senders still
    receive Bot Framework `invokeResponse` status 200, return safe blocked
    metadata, skip Bot Framework User Token service calls, avoid delegated
    token persistence, and never return the verify-state magic code.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `a203f34e`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams SSO group sender proof
    (`1 passed`), adjacent Teams send/action/provider proof (`20 passed, 304
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AQ` Microsoft Teams SSO route allowlist authorization/drop
  - Source: `openclaw-main/extensions/msteams/src/monitor-handler.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler/access.ts`,
    `openclaw-main/extensions/msteams/src/policy.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: when configured Microsoft Teams SSO receives
    `signin/tokenExchange` from a channel/group context while
    `channels.msteams.teams` is configured and the incoming team/channel does
    not match, OpenZues still emits a Bot Framework `invokeResponse` status
    200, returns safe blocked metadata with route context, skips Bot Framework
    User Token service calls, avoids delegated-token persistence, and never
    returns the exchange token.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `5c54430c`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams SSO route allowlist
    proof (`1 passed`), adjacent Teams send/action/provider proof (`19 passed,
    304 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AP` Microsoft Teams SSO DM allowlist authorization/drop
  - Source: `openclaw-main/extensions/msteams/src/monitor-handler.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler/access.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler.sso.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: when configured Microsoft Teams SSO receives
    `signin/tokenExchange` from a personal chat while `dmPolicy="allowlist"`
    and the sender is not in `allowFrom`, OpenZues still emits a Bot
    Framework `invokeResponse` status 200, returns safe blocked SSO metadata,
    skips Bot Framework User Token service calls, avoids delegated-token
    persistence, and never returns the exchange token.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `b9f2f404`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams SSO DM allowlist proof
    (`1 passed`), adjacent Teams send/action/provider proof (`18 passed, 304
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AO` Microsoft Teams configured SSO verify-state magic code
  - Source: `openclaw-main/extensions/msteams/src/sso.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler.sso.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `src/openzues/database.py`, `tests/test_ops_mesh.py`
  - Contract: when SSO is configured, `signin/verifyState` resolves native
    Teams app credentials, obtains a Bot Framework bearer, calls
    `/api/usertoken/GetToken` with the magic-code `state`, persists the
    delegated user token keyed by `(connectionName, userId)`, and returns only
    safe stored metadata without leaking the state code or delegated token.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `0ecfab4c`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams configured
    verify-state proof (`1 passed`), adjacent Teams send/action/provider proof
    (`17 passed, 304 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AN` Microsoft Teams configured SSO token exchange/store
  - Source: `openclaw-main/extensions/msteams/src/sso.ts`,
    `openclaw-main/extensions/msteams/src/sso-token-store.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler.sso.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `src/openzues/database.py`, `tests/test_ops_mesh.py`
  - Contract: when `channels.msteams.sso.enabled` and `connectionName` are
    configured, `signin/tokenExchange` resolves native Teams app credentials,
    obtains a Bot Framework service bearer, calls `/api/usertoken/exchange`,
    persists the delegated user token keyed by `(connectionName, userId)`, and
    returns only safe stored/expiry metadata without leaking exchange or
    delegated tokens.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `1bf6ab5b`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams configured
    token-exchange proof (`1 passed`), adjacent Teams send/action/provider
    proof (`16 passed, 304 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AM` Microsoft Teams SSO no-config invoke acknowledgement
  - Source: `openclaw-main/extensions/msteams/src/monitor-handler.ts`,
    `openclaw-main/extensions/msteams/src/sso.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler.sso.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: Teams `signin/tokenExchange` and `signin/verifyState` invoke
    activities are acknowledged with a Bot Framework `invokeResponse` status
    200 before normal message routing; when no SSO adapter is configured,
    OpenZues returns a native unavailable SSO posture with only safe metadata
    and no raw token or magic-code persistence/leakage.
  - Evidence required: focused runtime tests, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `49ebe481`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams SSO no-config proofs
    (`2 passed`), adjacent Teams send/action/provider proof (`15 passed, 304
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AL` Microsoft Teams feedback invoke recording
  - Source: `openclaw-main/extensions/msteams/src/monitor-handler.ts`,
    `openclaw-main/extensions/msteams/src/feedback-reflection.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: Teams `message/submitAction` feedback invokes normalize
    `like`/`dislike` reactions into positive/negative feedback, parse
    optional `feedbackText`, resolve the same thread-aware session target as
    inbound messages, and persist session-scoped feedback metadata.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `7a545faf`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams feedback invoke proof
    (`1 passed`), adjacent Teams send/action/provider proof (`13 passed, 304
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AK` Microsoft Teams inbound message text normalization
  - Source: `openclaw-main/extensions/msteams/src/monitor-handler/message-handler.ts`,
    `openclaw-main/extensions/msteams/src/inbound.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: Teams message activities strip `<at>...</at>` mention tags
    before routing to the target session, and activities with no plain text
    can derive inbound text from `text/html` attachments while preserving link
    URLs and decoding HTML entities.
  - Evidence required: focused runtime tests, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `65daf165`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams message normalization
    proofs (`2 passed`), adjacent Teams send/action/provider proof (`12
    passed, 304 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AJ` Microsoft Teams adaptive-card inbound monitor/session routing
  - Source: `openclaw-main/extensions/msteams/src/monitor-handler.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler/message-handler.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler/thread-session.ts`,
    `openclaw-main/extensions/msteams/src/inbound.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: Teams `adaptiveCard/action` invoke payloads are serialized as
    compact JSON and routed as inbound session text; `conversation.id` strips
    `;messageid=...` for targeting; channel replies prefer the `messageid`
    thread root over nested `replyToId`; the resulting session key is
    thread-isolated and delivery remains session-backed rather than echoing
    through native provider sends.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `5462df49`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams adaptive-card inbound
    proof (`1 passed`), adjacent Teams send/action/provider proof (`10
    passed, 304 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AI` Microsoft Teams Graph media upload
  - Source: `openclaw-main/extensions/msteams/src/graph-upload.ts`,
    `openclaw-main/extensions/msteams/src/graph-chat.ts`,
    `openclaw-main/extensions/msteams/src/send.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: Teams media sends with a SharePoint site id upload media bytes
    to Graph, create an organization share link, fetch DriveItem properties,
    emit a native FileInfoCard, and persist file-card plus Graph upload
    metadata on the saved delivery.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `a220db23`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams Graph upload proof
    (`1 passed`), adjacent Teams send/action/provider proof (`9 passed, 304
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AH` Microsoft Teams FileConsent accept/upload
  - Source: `openclaw-main/extensions/msteams/src/file-consent.ts`,
    `openclaw-main/extensions/msteams/src/file-consent-invoke.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: Teams `fileConsent/invoke` accept payloads locate the saved
    pending upload by `uploadId`, guard conversation mismatches, validate the
    Teams upload URL against the Microsoft/SharePoint allowlist, PUT pending
    media bytes with `Content-Type` and `Content-Range`, replace the consent
    card with a FileInfoCard, and persist uploaded file metadata on the saved
    outbound delivery.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `709fcf4d`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams FileConsent upload
    proof (`1 passed`), adjacent Teams send/action/provider proof (`8 passed,
    304 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AG` Microsoft Teams FileConsent card emission
  - Source: `openclaw-main/extensions/msteams/src/file-consent.ts`,
    `openclaw-main/extensions/msteams/src/file-consent-helpers.ts`,
    `openclaw-main/extensions/msteams/src/send.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_outbound_runtime.py`,
    `tests/test_ops_mesh.py`
  - Contract: Teams direct sends with media and FileConsent metadata emit a
    Bot Framework `application/vnd.microsoft.teams.card.file.consent`
    attachment with `description`, `sizeInBytes`, `acceptContext`, and
    `declineContext`, omit top-level text from the consent activity, and
    preserve `pendingUploadId`, `mediaUrls`, and `filenames` through
    direct-send responses and saved delivery metadata.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `ad3c8a5c`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams FileConsent card proof
    (`1 passed`), adjacent Teams send/action/provider proof (`7 passed, 304
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AF` Microsoft Teams poll vote storage
  - Source: `openclaw-main/extensions/msteams/src/polls.ts`,
    `openclaw-main/extensions/msteams/src/monitor-handler/message-handler.ts`,
    `openclaw-main/extensions/msteams/src/outbound.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: Teams adaptive-card vote payloads carrying `openclawPollId` /
    `pollId` plus `choices` are extracted from message action value shapes,
    sender ids are used as voters, selection indexes are normalized to the
    poll option range and `maxSelections`, unknown poll ids are consumed
    without error, and known poll votes persist on the saved outbound poll
    delivery metadata.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `b3726879`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams poll-vote proof (`1
    passed`), adjacent Teams send/action/provider proof (`6 passed, 304
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AE` Microsoft Teams file info card media
  - Source: `openclaw-main/extensions/msteams/src/send.ts`,
    `openclaw-main/extensions/msteams/src/graph-chat.ts`,
    `openclaw-main/extensions/msteams/src/graph-upload.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: channel/group Teams sends with media can consume
    provider-ready DriveItem metadata, build the native
    `application/vnd.microsoft.teams.card.file.info` Bot Framework
    attachment with eTag-derived `uniqueId` and filename-derived `fileType`,
    keep caller text as the attachment caption without synthesized media
    inventory text, and preserve `mediaUrls`, `filenames`, and `fileIds`
    provider result metadata.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `eb663838`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams file-card media proof
    (`1 passed`), adjacent Teams send/action/provider proof (`9 passed, 300
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AD` Microsoft Teams threaded replies
  - Source: `openclaw-main/extensions/msteams/src/messenger.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: channel-targeted Teams sends preserve `replyToId`, reconstruct
    the outbound Bot Framework conversation id as
    `<conversationId>;messageid=<thread-root>` when posting the activity, and
    keep provider result metadata on the base conversation id with
    `replyToId`.
  - Evidence required: focused runtime test, adjacent Teams send/action/
    provider tests, ruff, mypy
  - Status: checkpointed in `927d5787`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams threaded-reply proof
    (`1 passed`), adjacent Teams send/action/provider proof (`8 passed, 300
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AC` Microsoft Teams reaction write actions
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.actions.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch accepts
    `channel="msteams"`, `action="react"`, `emoji`/`reactionType`,
    `remove=true`, and `unreact`, normalizes well-known reaction types,
    posts Graph beta `setReaction` / `unsetReaction` with delegated Graph
    token posture, supports chat and team/channel Graph targets, and returns
    OpenClaw-shaped action result metadata.
  - Evidence required: focused runtime test, adjacent Teams/action/provider
    tests, ruff, mypy
  - Status: checkpointed in `02ae95da`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams react proof (`1
    passed`), adjacent Teams/action/provider proof (`10 passed, 297
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AB` Microsoft Teams user-reference routing
  - Source: `openclaw-main/extensions/msteams/src/session-route.ts`,
    `openclaw-main/extensions/msteams/src/send-context.ts`,
    `openclaw-main/extensions/msteams/src/conversation-store.ts`,
    `openclaw-main/extensions/msteams/src/conversation-store-helpers.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `msteams:user:<aad-id>` targets are classified as direct
    peers, matched against route-backed stored `user:` references, resolved to
    stored Bot Framework `conversationId` metadata only when the reference is
    personal or legacy-unknown, and guarded from routing private user sends
    into group/channel conversations.
  - Evidence required: focused runtime test, adjacent Teams/provider tests,
    ruff, mypy
  - Status: checkpointed in `b88c540d`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams user-reference proof
    (`1 passed`), adjacent Teams/provider proof (`6 passed, 300 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001AA` Microsoft Teams native readiness probe
  - Source: `openclaw-main/extensions/msteams/src/probe.ts`,
    `openclaw-main/extensions/msteams/src/token.ts`,
    `openclaw-main/extensions/msteams/src/token-response.ts`,
    `openclaw-main/extensions/msteams/src/sdk.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`, `tests/test_cli.py`
  - Contract: native `kind="msteams"` routes participate in
    `channels status --probe`, validate Bot Framework app-token posture from
    route `appId`/`tenantId` plus secret, attempt Graph app-token posture
    discovery, project optional roles/scopes when token payloads expose them,
    and return native-provider readiness metadata through runtime and CLI probe
    envelopes.
  - Evidence required: focused runtime/CLI tests, adjacent runtime/CLI tests,
    ruff, mypy
  - Status: checkpointed in `50d05198`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams probe proof (`1
    passed`), focused CLI probe proof (`1 passed`), adjacent runtime proof (`8
    passed, 297 deselected`), adjacent CLI proof (`3 passed, 508
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001Z` Microsoft Teams reaction-list action
  - Source: `openclaw-main/extensions/msteams/src/actions.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.ts`,
    `openclaw-main/extensions/msteams/src/graph-messages.read.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for `channel="msteams"`,
    `action="reactions"` resolves explicit `to` / `target` / conversation ids
    or Graph-channel tool context, obtains a Graph app token from route
    `appId`/`tenantId` plus secret, reads the Graph message resource, groups
    reactions by `reactionType`, counts entries without user ids, preserves
    known emoji labels, and returns OpenClaw-shaped `{ok, reactions}`.
  - Evidence required: focused runtime test, adjacent provider/action tests,
    ruff, mypy
  - Status: checkpointed in `4996cf5c`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams reaction-list proof
    (`1 passed`), adjacent action/provider proof (`9 passed, 295
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001Y` Microsoft Teams native polls
  - Source: `openclaw-main/extensions/msteams/src/polls.ts`,
    `openclaw-main/extensions/msteams/src/send.ts`,
    `openclaw-main/extensions/msteams/src/outbound.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `src/openzues/cli.py`,
    `tests/test_ops_mesh.py`, `tests/test_cli.py`
  - Contract: route-backed `kind="msteams"` accepts `gateway/poll`, validates
    question/options/max selections, builds Adaptive Card 1.5 choice-set
    payloads with OpenClaw `openclawPollId` / `pollId` submit metadata and
    Teams `messageBack` action data, posts through Bot Framework proactive
    activities, returns `pollId`, `messageId`, and conversation metadata, and
    advertises `poll` through CLI channel capabilities.
  - Evidence required: focused runtime/CLI tests, adjacent provider/CLI tests,
    ruff, mypy
  - Status: checkpointed in `b0ad5491`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams poll proof (`1
    passed`), focused CLI capability proof (`1 passed`), adjacent provider
    route proof (`11 passed, 292 deselected`), adjacent CLI proof (`3 passed,
    507 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001X` Microsoft Teams native outbound route
  - Source: `openclaw-main/extensions/msteams/src/outbound.ts`,
    `openclaw-main/extensions/msteams/src/send.ts`,
    `openclaw-main/extensions/msteams/src/send-context.ts`,
    `openclaw-main/extensions/msteams/src/messenger.ts`,
    `openclaw-main/extensions/msteams/src/token.ts`,
    `openclaw-main/extensions/msteams/src/session-route.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/schemas.py`,
    `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_channels.py`, `src/openzues/cli.py`,
    `src/openzues/web/templates/index.html`,
    `src/openzues/web/static/app.js`, `tests/test_ops_mesh.py`,
    `tests/test_cli.py`, `tests/test_app.py`
  - Contract: route-backed `kind="msteams"` sends Bot Framework proactive
    top-level text activities to explicit conversation ids, accepts service
    URLs carrying `appId`/`tenantId`, uses route secrets as app passwords or
    bearer tokens, normalizes `msteams:`/`teams:`/`conversation:` targets,
    strips `;messageid=...`, stamps OpenClaw-shaped AI generated-content
    entity metadata, and persists provider `messageId`, chat/channel ids, and
    conversation metadata.
  - Evidence required: focused schema/service/CLI/app tests, adjacent
    provider route tests, ruff, mypy
  - Status: checkpointed in `79258ec2`
  - Weight: 1
  - Last verified: 2026-05-05, focused Microsoft Teams route proof (`2
    passed`), focused CLI proof (`1 passed`), focused app proof (`3 passed`),
    adjacent provider route proof (`10 passed, 292 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PROV-001W` Signal native reaction action
  - Source: `openclaw-main/extensions/signal/src/message-actions.ts`,
    `openclaw-main/extensions/signal/src/send-reactions.ts`,
    `openclaw-main/src/channels/plugins/actions/reaction-message-id.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: native `message.action` dispatch for
    `channel="signal"`, `action="react"` normalizes direct `signal:` /
    `uuid:` recipients and `signal:group:` targets, requires target-author
    metadata for group reactions, falls back to
    `toolContext.currentMessageId` when `messageId` is omitted, posts
    JSON-RPC `sendReaction` payloads to `/api/v1/rpc`, and returns
    OpenClaw-shaped `{ok, added}` / `{ok, removed}` results.
  - Evidence required: focused Signal action tests, adjacent provider/action
    tests, ruff, mypy
  - Status: checkpointed in `c9b45ffb`
  - Weight: 1
  - Last verified: 2026-05-05, focused Signal reaction proof (`3 passed`),
    adjacent provider/action proof (`8 passed, 292 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PROV-001V` Twitch native outbound route
  - Source: `openclaw-main/extensions/twitch/src/send.ts`,
    `openclaw-main/extensions/twitch/src/outbound.ts`,
    `openclaw-main/extensions/twitch/src/twitch-client.ts`,
    `openclaw-main/extensions/twitch/src/utils/markdown.ts`,
    `openclaw-main/extensions/twitch/src/utils/twitch.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/schemas.py`,
    `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_channels.py`, `src/openzues/cli.py`,
    `src/openzues/web/templates/index.html`,
    `src/openzues/web/static/app.js`, `tests/test_ops_mesh.py`,
    `tests/test_cli.py`, `tests/test_app.py`
  - Contract: route-backed `kind="twitch"` sends native Twitch IRC chat
    messages after channel normalization, markdown stripping, and media URL
    text fallback, while persisting generated message/chat/channel/timestamp
    and media metadata.
  - Evidence required: focused schema/service/CLI/app tests, adjacent
    provider/CLI/app route tests, ruff, mypy
  - Status: checkpointed in `6185301b`
  - Weight: 1
  - Last verified: 2026-05-05, focused Twitch route proof (`5 passed, 207
    deselected`), adjacent provider route proof (`21 passed, 276 deselected`),
    adjacent CLI route proof (`9 passed, 499 deselected`), adjacent app route
    proof (`21 passed, 188 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001U` IRC native outbound route
  - Source: `openclaw-main/extensions/irc/src/send.ts`,
    `openclaw-main/extensions/irc/src/normalize.ts`,
    `openclaw-main/extensions/irc/src/client.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/schemas.py`,
    `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_channels.py`, `src/openzues/cli.py`,
    `src/openzues/web/templates/index.html`,
    `src/openzues/web/static/app.js`, `tests/test_ops_mesh.py`,
    `tests/test_cli.py`, `tests/test_app.py`
  - Contract: route-backed `kind="irc"` sends native IRC `PRIVMSG`
    payloads through `irc://`/`ircs://` server targets, normalizes
    `irc:`/`channel:`/`user:` peers, appends `replyToId` as
    `[reply:<id>]`, and persists generated `messageId`, chat/channel ids,
    reply metadata, and media URL fallback metadata.
  - Evidence required: focused schema/service/CLI/app tests, adjacent
    provider/CLI/app route tests, ruff, mypy
  - Status: checkpointed in `8726ab49`
  - Weight: 1
  - Last verified: 2026-05-05, focused IRC route proof (`5 passed, 205
    deselected`), adjacent provider route proof (`19 passed, 276 deselected`),
    adjacent CLI route proof (`8 passed, 499 deselected`), adjacent app route
    proof (`19 passed, 188 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001T` Signal native outbound route
  - Source: `openclaw-main/extensions/signal/src/send.ts`,
    `openclaw-main/extensions/signal/src/client.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/schemas.py`,
    `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_channels.py`, `src/openzues/cli.py`,
    `src/openzues/web/templates/index.html`,
    `src/openzues/web/static/app.js`, `tests/test_ops_mesh.py`,
    `tests/test_cli.py`, `tests/test_app.py`
  - Contract: route-backed `kind="signal"` sends post JSON-RPC `send`
    payloads to `/api/v1/rpc`, normalize recipient/group/username targets,
    forward media URLs as attachments, and persist timestamp-derived
    `messageId`, chat/channel ids, and media URL metadata.
  - Evidence required: focused schema/service/CLI/app tests, adjacent
    provider/CLI/app route tests, ruff, mypy
  - Status: checkpointed in `81491ab7`
  - Weight: 1
  - Last verified: 2026-05-05, focused Signal route proof (`5 passed, 203
    deselected`), adjacent provider route proof (`17 passed, 276 deselected`),
    adjacent CLI route proof (`7 passed, 499 deselected`), adjacent app route
    proof (`17 passed, 188 deselected`), post-ruff app proof (`2 passed, 203
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001S` Mattermost native outbound route
  - Source: `openclaw-main/extensions/mattermost/src/mattermost/send.ts`,
    `openclaw-main/extensions/mattermost/src/mattermost/client.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/schemas.py`,
    `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_channels.py`, `src/openzues/cli.py`,
    `src/openzues/web/templates/index.html`,
    `src/openzues/web/static/app.js`, `tests/test_ops_mesh.py`,
    `tests/test_cli.py`, `tests/test_app.py`
  - Contract: route-backed `kind="mattermost"` sends post `/api/v4/posts`
    JSON payloads with `channel_id`, `message`, and optional `root_id`, attach
    bearer bot auth, and persist provider `messageId`, chat/channel ids, and
    reply metadata.
  - Evidence required: focused schema/service/CLI/app tests, adjacent
    provider/CLI/app route tests, ruff, mypy
  - Status: checkpointed in `44541ef9`
  - Weight: 1
  - Last verified: 2026-05-05, focused Mattermost route proof (`5 passed, 201
    deselected`), adjacent provider route proof (`15 passed, 276 deselected`),
    adjacent CLI route proof (`6 passed, 499 deselected`), adjacent app route
    proof (`15 passed, 188 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001R` Synology Chat native outbound route
  - Source: `openclaw-main/extensions/synology-chat/src/client.ts`,
    `openclaw-main/extensions/synology-chat/src/channel.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/schemas.py`,
    `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_channels.py`, `src/openzues/cli.py`,
    `src/openzues/web/templates/index.html`,
    `src/openzues/web/static/app.js`, `tests/test_ops_mesh.py`,
    `tests/test_cli.py`, `tests/test_app.py`
  - Contract: route-backed `kind="synology-chat"` sends post form-encoded
    `payload` JSON to incoming webhook URLs, preserve numeric `user_ids`, send
    media URLs through `file_url` payloads, and persist generated `messageId`,
    recipient chat/channel ids, and media URL metadata.
  - Evidence required: focused schema/service/CLI/app tests, adjacent
    provider/CLI/app route tests, ruff, mypy
  - Status: checkpointed in `b69d5489`
  - Weight: 1
  - Last verified: 2026-05-05, focused Synology route proof (`5 passed, 199
    deselected`), adjacent provider route proof (`13 passed, 276 deselected`),
    adjacent CLI route proof (`5 passed, 499 deselected`), adjacent app route
    proof (`13 passed, 188 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001Q` Nextcloud Talk native outbound route
  - Source: `openclaw-main/extensions/nextcloud-talk/src/send.ts`,
    `openclaw-main/extensions/nextcloud-talk/src/normalize.ts`,
    `openclaw-main/extensions/nextcloud-talk/src/channel.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/schemas.py`,
    `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_channels.py`, `src/openzues/cli.py`,
    `src/openzues/web/templates/index.html`,
    `src/openzues/web/static/app.js`, `tests/test_ops_mesh.py`,
    `tests/test_cli.py`, `tests/test_app.py`
  - Contract: route-backed `kind="nextcloud-talk"` sends normalize upstream
    room token aliases, post HMAC-signed bot messages to the Spreed bot
    message endpoint, forward `replyTo`, append media URLs as
    `Attachment: <url>` fallback text, and persist provider `messageId`,
    room chat/channel ids, timestamp, reply, and media URL metadata.
  - Evidence required: focused schema/service/CLI/app tests, adjacent
    provider/CLI/app route tests, ruff, mypy
  - Status: checkpointed in `a6732846`
  - Weight: 1
  - Last verified: 2026-05-05, focused schema proof (`1 passed`), focused
    service proof (`1 passed`), focused CLI proof (`1 passed`), focused app
    proof (`2 passed, 197 deselected`), adjacent provider route proof (`11
    passed, 276 deselected`), adjacent CLI route proof (`4 passed, 499
    deselected`), adjacent app route proof (`11 passed, 188 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001P` Google Chat media and DM-resolution delivery
  - Source: `openclaw-main/extensions/googlechat/src/api.ts`,
    `openclaw-main/extensions/googlechat/src/channel.adapters.ts`,
    `openclaw-main/extensions/googlechat/src/targets.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`,
    `tests/test_ops_mesh.py`
  - Contract: route-backed Google Chat sends resolve `users/...` targets
    through `spaces:findDirectMessage`, upload media bytes to the Google Chat
    attachment upload endpoint, send attachment refs in the final message
    create payload, preserve caller captions, and persist provider
    `messageId`, chat, media token, media URL, and filename metadata.
  - Evidence required: focused media/DM tests, adjacent provider route tests,
    ruff, mypy
  - Status: checkpointed in `7086dcb3`
  - Weight: 1
  - Last verified: 2026-05-05, focused media and DM proofs (`1 passed` each),
    adjacent provider route proof (`9 passed, 276 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PROV-001O` Google Chat native outbound route
  - Source: `openclaw-main/extensions/googlechat/src/api.ts`,
    `openclaw-main/extensions/googlechat/src/channel.adapters.ts`,
    `openclaw-main/extensions/googlechat/src/targets.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/schemas.py`,
    `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_channels.py`, `src/openzues/cli.py`,
    `src/openzues/web/templates/index.html`,
    `src/openzues/web/static/app.js`, `tests/test_ops_mesh.py`,
    `tests/test_cli.py`, `tests/test_app.py`
  - Contract: route-backed `kind="googlechat"` sends dispatch through native
    Google Chat message-create semantics, normalize upstream
    `googlechat:`/`google-chat:`/`gchat:` space targets, send
    `{text, thread}` payloads with reply fallback query semantics, attach
    bearer auth, and persist provider `messageId`, chat, thread, and reply
    metadata through the shared direct-send result envelope and route UI/CLI
    surfaces.
  - Evidence required: focused schema/service/CLI tests, adjacent
    provider/CLI/app route tests, ruff, mypy
  - Status: checkpointed in `edb67dfc`
  - Weight: 1
  - Last verified: 2026-05-05, focused schema/service/CLI proofs (`1 passed`
    each), adjacent provider route proof (`7 passed, 276 deselected`),
    adjacent route-create proof (`3 passed, 499 deselected`), adjacent app
    route proof (`9 passed, 188 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001BN` persisted plugin registry provider metadata
  - Source: `openclaw-main/src/plugins/manifest-registry.ts`,
    `openclaw-main/src/plugins/manifest-registry.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `plugins registry --refresh --json` and later registry inspect
    payloads preserve provider endpoints, `modelIdNormalization`, and
    `providerRequest` metadata when those fields are present on current plugin
    rows, while minimal plugin rows remain unchanged.
  - Evidence required: focused registry provider metadata CLI test, adjacent
    registry tests, ruff, mypy
  - Status: checkpointed in `54c2fd49`
  - Weight: 1
  - Last verified: 2026-05-04, focused registry provider metadata proof (`1
    passed`), adjacent registry proof (`4 passed, 497 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001BM` plugin provider metadata projection
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/manifest-registry.ts`,
    `openclaw-main/src/plugins/manifest-registry.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: OpenClaw manifest provider metadata survives native
    `plugins list --json`, including endpoint `hostSuffixes`,
    `googleVertexRegion`, `googleVertexRegionHostSuffix`,
    provider-scoped `modelIdNormalization`, and provider-scoped
    `providerRequest`, with provider-specific maps filtered to manifest-owned
    provider ids.
  - Evidence required: focused manifest provider metadata CLI test, adjacent
    manifest metadata tests, ruff, mypy
  - Status: checkpointed in `9b2bf4fc`
  - Weight: 1
  - Last verified: 2026-05-04, focused plugin provider metadata proof (`1
    passed`), adjacent manifest metadata proof (`6 passed, 494 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-COMP-001F` QR JSON setup-code contract
  - Source: `openclaw-main/src/cli/qr-cli.ts`,
    `openclaw-main/src/cli/qr-cli.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `openzues qr --json --url ... --token ...` returns only
    `setupCode`, `gatewayUrl`, `auth`, and `urlSource`; raw token/password
    overrides do not appear in stdout, and the encoded setup code remains
    limited to `{url, bootstrapToken}`.
  - Evidence required: focused QR JSON CLI test, adjacent QR tests, ruff, mypy
  - Status: checkpointed in `b79b87c3`
  - Weight: 1
  - Last verified: 2026-05-04, focused QR JSON proof (`1 passed`), adjacent
    QR proof (`4 passed, 496 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-COMP-001E` QR remote fail-closed preflight
  - Source: `openclaw-main/src/cli/qr-cli.ts`,
    `openclaw-main/src/cli/qr-cli.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `openzues qr --setup-code-only --remote` refuses to issue a
    bootstrap token unless a concrete remote URL source is supplied, returning
    the upstream `qr --remote requires gateway.remote.url (or
    gateway.tailscale.mode=serve/funnel).` diagnostic.
  - Evidence required: focused remote-preflight CLI test, adjacent QR tests,
    ruff, mypy
  - Status: checkpointed in `12dee789`
  - Weight: 1
  - Last verified: 2026-05-04, focused remote-preflight QR proof (`1 passed`),
    adjacent QR proof (`3 passed, 496 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-COMP-001D` QR invalid URL preflight
  - Source: `openclaw-main/src/cli/qr-cli.test.ts`,
    `openclaw-main/src/pairing/setup-code.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: malformed QR setup-code override URLs fail with
    `Configured publicUrl is invalid.` and return before any
    `devices/bootstrap.json` token state is created.
  - Evidence required: focused invalid-URL CLI test, adjacent QR setup-code
    tests, ruff, mypy
  - Status: checkpointed in `f21c799c`
  - Weight: 1
  - Last verified: 2026-05-04, focused invalid-URL QR proof (`1 passed`),
    adjacent QR setup-code proof (`2 passed, 496 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-COMP-001C` QR setup-code bootstrap handoff
  - Source: `openclaw-main/src/cli/qr-cli.ts`,
    `openclaw-main/src/pairing/setup-code.ts`,
    `openclaw-main/src/infra/device-bootstrap.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`,
    `src/openzues/services/device_bootstrap_tokens.py`, `tests/test_cli.py`
  - Contract: `openzues qr --setup-code-only --url ...` emits exactly one
    OpenClaw base64url JSON setup code containing `{url, bootstrapToken}`,
    persists the issued bootstrap token under `devices/bootstrap.json` with the
    default node/operator handoff profile plus expiry metadata, and never
    embeds raw gateway token/password overrides in the setup payload.
  - Evidence required: focused QR setup-code-only CLI test, adjacent
    setup/bootstrap CLI tests, ruff, mypy
  - Status: checkpointed in `5262359f`
  - Weight: 1
  - Last verified: 2026-05-04, focused QR setup-code proof (`1 passed`),
    adjacent setup/bootstrap CLI proof (`3 passed, 494 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001BL` ESM plugin runtime entry import
  - Source: `openclaw-main/src/plugins/loader.ts`,
    `openclaw-main/src/plugins/sdk-alias.ts`,
    `openclaw-main/src/plugins/loader.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: native plugin runtime import also supports common package ESM
    syntax (`import ... from "openclaw/plugin-sdk/*"` plus `export default`)
    by transforming it into a temporary CommonJS module beside the runtime
    entry, preserving SDK alias shims, relative import posture, registered
    tool collection, imported-state projection, and manifest contract
    satisfaction.
  - Evidence required: focused ESM no-fake-adapter plugin doctor test,
    adjacent plugin import/activation tests, gateway plugin runtime tests,
    ruff, mypy
  - Status: checkpointed in `eb11e22f`
  - Weight: 1
  - Last verified: 2026-05-04, focused ESM plugin runtime import proof (`1
    passed`), adjacent plugin activation proof (`8 passed, 488 deselected`),
    gateway plugin runtime proof (`3 passed`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001BK` bundled plugin runtime entry import
  - Source: `openclaw-main/src/plugins/loader.ts`,
    `openclaw-main/src/plugins/registry.ts`,
    `openclaw-main/src/plugins/loader.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: enabled bundled/package OpenClaw plugin rows with
    `runtimeEntrySource` can be evaluated by the native CLI runtime without a
    fake activation adapter; the loader shims OpenClaw plugin-SDK aliases,
    unwraps default exports, calls `register`/`activate`, records registered
    tools as runtime executor specs, marks the plugin imported, and resolves
    manifest tool contracts to `runtimeActivation.status="ok"`.
  - Evidence required: focused no-fake-adapter plugin doctor test, adjacent
    SDK alias/activation adapter tests, gateway plugin runtime tests, ruff,
    mypy
  - Status: checkpointed in `8cb314f4`
  - Weight: 1
  - Last verified: 2026-05-04, focused plugin runtime import proof (`1
    passed`), adjacent plugin activation proof (`7 passed, 488 deselected`),
    gateway plugin runtime proof (`3 passed`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001N` Feishu/Lark native outbound route
  - Source: `openclaw-main/extensions/feishu/src/send-target.ts`,
    `openclaw-main/extensions/feishu/src/send.ts`,
    `openclaw-main/extensions/feishu/src/send-result.ts`,
    `openclaw-main/extensions/feishu/src/outbound.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/schemas.py`,
    `src/openzues/services/ops_mesh.py`,
    `src/openzues/services/gateway_channels.py`, `src/openzues/cli.py`,
    `tests/test_ops_mesh.py`, `tests/test_cli.py`
  - Contract: route-backed `kind="feishu"` sends dispatch through native
    Feishu/Lark message-create semantics, normalize chat/user/open-id targets,
    send `msg_type="post"` with markdown content under `zh_cn.content`, attach
    bearer auth, and persist provider `messageId`/chat metadata through the
    shared direct-send result envelope.
  - Evidence required: focused Feishu native route test, CLI route-create test,
    adjacent provider route tests, ruff, mypy
  - Status: checkpointed in `d1515da1`
  - Weight: 1
  - Last verified: 2026-05-04, focused Feishu service proof (`2 passed`),
    focused CLI proof (`1 passed`), adjacent provider send proof (`6 passed,
    275 deselected`), adjacent route-create proof (`5 passed, 489
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PKG-001E` update status package-manager dependency posture
  - Source: `openclaw-main/src/infra/detect-package-manager.ts`,
    `openclaw-main/src/infra/update-check.ts`,
    `openclaw-main/src/cli/update-cli/status.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `openzues update status --json` detects `packageManager` from
    `package.json` or lockfiles and projects OpenClaw-shaped `deps` metadata
    with manager, status, lockfile path, marker path, and stale/missing/unknown
    reasons while preserving existing update/channel/availability payloads.
  - Evidence required: focused update-status package-manager test, adjacent
    update/package doctor tests, ruff, mypy
  - Status: checkpointed in `f1ac67da`
  - Weight: 1
  - Last verified: 2026-05-04, focused
    `python -m pytest tests\test_cli.py::test_update_status_json_detects_package_manager_deps -q`
    (`1 passed`), adjacent update/package doctor proof (`5 passed, 488
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001M` Slack agent-request thread metadata
  - Source: `openclaw-main/src/agents/subagent-announce-delivery.ts`,
    `openclaw-main/extensions/slack/src/outbound-adapter.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/app.py`, `tests/test_gateway_node_methods.py`
  - Contract: `node.event` `agent.request` route payloads that target Slack
    preserve `accountId` and Slack timestamp-shaped `threadId` as
    `account_id` / `thread_id` on the fakeable chat runtime path, while
    preserving the existing no-route delivery disable behavior.
  - Evidence required: focused Slack agent-request route test, adjacent
    agent-request route/no-route/receipt/attachment tests, adjacent Slack
    provider direct-send tests, ruff, mypy
  - Status: checkpointed in `e3671d6f`
  - Weight: 1
  - Last verified: 2026-05-04, focused
    `python -m pytest tests\test_gateway_node_methods.py::test_node_event_agent_request_forwards_slack_account_and_thread_to_chat_runtime -q`
    (`1 passed`), adjacent gateway proof (`5 passed, 807 deselected`),
    adjacent Slack provider proof (`3 passed, 276 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PROV-001L` Discord thread result fallback
  - Source: `openclaw-main/extensions/discord/src/send.webhook.ts`,
    `openclaw-main/extensions/discord/src/outbound-adapter.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: Discord native route-backed webhook sends preserve
    `wait=true`, route `threadId` as webhook query, keep reply/silent payload
    fields, and fall back `chatId`/`channelId` to the requested thread id when
    Discord returns a message id without `channel_id`.
  - Evidence required: focused Discord thread-query test, adjacent Discord
    native send/reply/poll tests, ruff, mypy
  - Status: checkpointed in `e47324f4`
  - Weight: 1
  - Last verified: 2026-05-04, focused Discord thread-query test (`1
    passed`), adjacent Discord native route proof (`4 passed, 275
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PROV-001K` WhatsApp split-media result metadata
  - Source: `openclaw-main/src/infra/outbound/message-plan.ts`,
    `openclaw-main/src/infra/outbound/deliver.ts`,
    `openclaw-main/src/gateway/server-methods/send.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: WhatsApp native multi-media sends retain last-message
    `messageId`, expose first-message `primaryMessageId`, include all split
    provider ids in `messageIds`, and persist those fields alongside
    compatibility `mediaIds` and `mediaUrls`.
  - Evidence required: focused WhatsApp split-media test, adjacent WhatsApp
    media/reply/audio tests, ruff, mypy
  - Status: checkpointed in `7e549c1e`
  - Weight: 1
  - Last verified: 2026-05-04, focused WhatsApp split-media test (`1 passed`),
    adjacent WhatsApp media/reply/audio proof (`4 passed, 275 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PROV-001J` Telegram raw media-caption metadata
  - Source: `openclaw-main/extensions/telegram/src/outbound-adapter.ts`,
    `openclaw-main/src/plugin-sdk/reply-payload.ts`,
    `openclaw-main/extensions/telegram/src/send.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: Telegram route-backed media sends pass the caller text as the
    first media caption without appending OpenZues' delivery-summary `Media:`
    URL inventory, keep later media sends captionless, preserve forced-document
    `disable_content_type_detection`, and retain terminal/message/media
    provider metadata.
  - Evidence required: focused Telegram media-group test, adjacent Telegram
    native-options test, ruff, mypy
  - Status: checkpointed in `b2bc7fb7`
  - Weight: 1
  - Last verified: 2026-05-04, focused Telegram media-group test (`1 passed`),
    adjacent Telegram native-options/media proof (`2 passed, 277 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001BJ` manifest runtime-extension contract metadata
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/registry.ts`,
    `openclaw-main/src/plugins/agent-tool-result-middleware-loader.ts`,
    `openclaw-main/src/agents/codex-app-server.extensions.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: OpenClaw manifest `contracts.embeddedExtensionFactories` and
    `contracts.agentToolResultMiddleware` values are normalized, preserved in
    native plugin records, and projected as
    `embedded-extension-factory:<id>` and
    `agent-tool-result-middleware:<id>` capability strings.
  - Evidence required: focused plugin list JSON test, adjacent plugin manifest
    contract projection tests, ruff, mypy
  - Status: checkpointed in `cbd59d1d`
  - Weight: 1
  - Last verified: 2026-05-04, focused runtime-extension contract test (`1
    passed`), adjacent plugin manifest contract proof (`6 passed, 486
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-COMP-001B` companion remote macOS bin discovery
  - Source: `openclaw-main/src/infra/skills-remote.ts`,
    `openclaw-main/src/infra/node-pairing.ts`,
    `openclaw-main/src/gateway/server/ws-connection/message-handler.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_remote_node_bins.py`,
    `src/openzues/services/gateway_skill_bins.py`,
    `src/openzues/services/gateway_node_pairing.py`,
    `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_node_service.py`, `src/openzues/database.py`,
    `src/openzues/app.py`, `tests/test_gateway_node_methods.py`,
    `tests/test_gateway_node_pairing_refresh.py`, `tests/test_gateway_nodes_api.py`
  - Contract: connected paired Darwin/macOS nodes collect required skill binary
    names, invoke `system.which` when available or `system.run` with a
    `command -v` fallback, parse array/object/stdout results, persist
    discovered `bins`, and expose non-empty bins through paired-node metadata.
  - Evidence required: focused remote-bin node method test, adjacent node
    method/API/pairing refresh tests, ruff, mypy
  - Status: checkpointed in `7dcce35d`
  - Weight: 1
  - Last verified: 2026-05-04, focused remote-bin pytest (`1 passed`),
    adjacent node method proof (`5 passed`), adjacent node API proof
    (`4 passed`), pairing refresh proof (`5 passed`), `ruff check`, and
    `mypy`.

- [x] `OZ-PKG-001D` update status git branch channel label
  - Source: `openclaw-main/src/infra/update-channels.ts`,
    `openclaw-main/src/cli/update-cli/status.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `openzues update status --json` reads git branch metadata and
    reports `channel.source="git-branch"` plus `dev (<branch>)` labels when
    `.git/HEAD` points at a branch.
  - Evidence required: focused update-status JSON tests, adjacent update/doctor
    CLI tests, ruff, mypy
  - Status: checkpointed in `8673e35d`
  - Weight: 1
  - Last verified: 2026-05-04, focused update-status pair (`2 passed`),
    adjacent update/package doctor proof (`4 passed`), `ruff check`, and
    `mypy`.

- [x] `OZ-PKG-001C` update status channel projection
  - Source: `openclaw-main/src/cli/update-cli/status.ts`,
    `openclaw-main/src/infra/update-channels.ts`,
    `openclaw-main/src/commands/status.update.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `openzues update status --json` preserves existing update fields
    and adds OpenClaw-shaped `update`, `channel`, and conservative
    `availability` payloads; git roots default to `dev (default)`.
  - Evidence required: focused update-status JSON test, adjacent update/doctor
    CLI tests, ruff, mypy
  - Status: checkpointed in `e32d4d47`
  - Weight: 1
  - Last verified: 2026-05-04, focused update-status test (`1 passed`),
    adjacent update/package doctor proof (`3 passed`), `ruff check`, and
    `mypy`.

- [x] `OZ-PROV-001I` Telegram audio/voice media send routing
  - Source: `openclaw-main/extensions/telegram/src/outbound-adapter.ts`,
    `openclaw-main/extensions/telegram/src/send.ts`,
    `openclaw-main/extensions/telegram/src/voice.ts`,
    `openclaw-main/src/media/audio.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`, `tests/test_ops_mesh.py`
  - Contract: route-backed Telegram `gateway/send` sends audio media through
    `sendAudio` by default and through `sendVoice` with `voice` payload when
    `audioAsVoice=true` and the media URL is voice-compatible, preserving
    caption/thread/reply/silent/media result metadata.
  - Evidence required: focused Telegram audio/voice test, adjacent Telegram
    native-route tests, ruff, mypy
  - Status: checkpointed in `9e1743fb`
  - Weight: 1
  - Last verified: 2026-05-04, focused Telegram audio/voice test (`1 passed`),
    adjacent Telegram native-route proof (`6 passed`), `ruff check`, and
    `mypy`.

- [x] `OZ-PKG-001B` package dist inventory validation
  - Source: `openclaw-main/src/infra/package-dist-inventory.ts`,
    `openclaw-main/src/infra/update-global.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: packaged roots must parse `dist/postinstall-inventory.json` as a
    JSON array of strings; invalid inventory downgrades package-distribution
    doctor status/checks to warning with the invalid-inventory detail.
  - Evidence required: focused package doctor test, adjacent package/runtime
    doctor tests, ruff, mypy
  - Status: checkpointed in `3bf0ff86`
  - Weight: 1
  - Last verified: 2026-05-04, focused package inventory test (`1 passed`),
    adjacent package/runtime doctor proof (`3 passed`), `ruff check`, and
    `mypy`.

- [x] `OZ-CANVAS-001A` canvas shortcode text normalization
  - Source: `openclaw-main/src/chat/canvas-render.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_canvas_render.py`,
    `tests/test_gateway_canvas_render.py`, `tests/test_app.py`
  - Contract: valid assistant-message `[embed ...]` shortcodes are removed and
    converted to canvas previews, then visible text collapses three-or-more
    newlines to one blank line and trims leading/trailing whitespace; fenced
    shortcodes and invalid targets remain visible.
  - Evidence required: focused canvas-render test, adjacent control-chat canvas
    preview test, ruff, mypy
  - Status: checkpointed in `c34e4a77`
  - Weight: 1
  - Last verified: 2026-05-04, focused canvas normalization test (`1 passed`),
    full canvas-render tests (`4 passed`), adjacent control-chat canvas preview
    proof (`1 passed, 194 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001BI` manifest external auth provider contract metadata
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/manifest-registry.ts`,
    `openclaw-main/src/plugins/providers.ts`,
    `openclaw-main/src/plugins/provider-runtime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: OpenClaw manifest `contracts.externalAuthProviders` values are
    normalized, preserved in native plugin records, and projected as
    `external-auth-provider:<id>` capability strings.
  - Evidence required: focused plugin list JSON test, adjacent plugin manifest
    contract projection tests, ruff, mypy
  - Status: checkpointed in `5fdfb23c`
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_plugins_list_json_preserves_manifest_external_auth_provider_contracts
    -q` (`1 passed`), adjacent plugin manifest inventory proof (`12 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001BH` manifest migration provider contract metadata
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/contracts/inventory/bundled-capability-metadata.ts`,
    `openclaw-main/src/plugins/contracts/registry.ts`,
    `openclaw-main/src/plugins/migration-provider-runtime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: OpenClaw manifest `contracts.migrationProviders` values are
    normalized, preserved in native plugin records, and projected as
    `migration-provider:<id>` capability strings.
  - Evidence required: focused plugin list JSON test, adjacent plugin manifest
    contract projection tests, ruff, mypy
  - Status: checkpointed in `17e62174`
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_plugins_list_json_preserves_manifest_migration_provider_contracts
    -q` (`1 passed`), adjacent plugin manifest inventory proof (`11 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001BG` manifest web-content extractor contract metadata
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/contracts/inventory/bundled-capability-metadata.ts`,
    `openclaw-main/src/plugins/web-content-extractors.runtime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: OpenClaw manifest `contracts.webContentExtractors` values are
    normalized, preserved in native plugin records, and projected as
    `web-content-extractor:<id>` capability strings.
  - Evidence required: focused plugin list JSON test, adjacent plugin manifest
    contract projection tests, ruff, mypy
  - Status: checkpointed in `3b392789`
  - Weight: 1
  - Last verified: 2026-05-04, focused `python -m pytest
    tests\test_cli.py::test_plugins_list_json_preserves_manifest_web_content_extractor_contracts
    -q` (`1 passed`), adjacent plugin manifest inventory proof (`10 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-COMP-001A` companion `node.presence.alive` lifecycle
  - Source: `openclaw-main/src/gateway/server-node-events.ts`,
    `openclaw-main/src/shared/node-presence.ts`,
    `openclaw-main/apps/ios/Sources/Push/BackgroundAliveBeacon.swift`, and
    Android gateway session invoke tests.
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_node_methods.py`,
    `src/openzues/services/gateway_node_pairing.py`, `src/openzues/database.py`,
    `tests/test_gateway_node_methods.py`, `tests/test_gateway_nodes_api.py`
  - Contract: authenticated `node.presence.alive` events can arrive without a
    live node socket, persist paired-node `lastSeenAtMs`/`lastSeenReason`,
    normalize allowed triggers, throttle repeated persisted writes per device,
    avoid ordinary node-event persistence, and return OpenClaw-shaped
    handled/reason payloads.
  - Evidence required: focused service/API node presence tests, adjacent
    pairing/event API tests, ruff, mypy
  - Status: checkpointed in `caded84a`
  - Weight: 1
  - Last verified: 2026-05-04, focused service/API tests (`1 passed` each),
    adjacent service/API selections (`3 passed` each), `ruff check` on touched
    node/database files, and `mypy` on touched source modules.

- [x] `OZ-PKG-001A` package distribution doctor diagnostics
  - Source: `openclaw-main/src/flows/doctor-health.ts`,
    `openclaw-main/src/commands/doctor-install.ts`,
    `openclaw-main/src/infra/update-global.ts`, and
    `openclaw-main/src/infra/package-dist-inventory.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `openzues doctor --json` emits `packageDistribution` with
    package root, source-checkout classification, `dist` presence,
    `dist/postinstall-inventory.json` inventory status, platform,
    Windows-first posture, checks, warnings, and
    `doctor:package-distribution` contribution metadata.
  - Evidence required: focused package distribution doctor test, adjacent
    doctor/runtime bridge tests, ruff, mypy
  - Status: checkpointed in `47d73351`
  - Weight: 1
  - Last verified: 2026-05-04, `python -m pytest
    tests\test_cli.py::test_doctor_json_includes_windows_package_distribution_diagnostics
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "package_distribution_diagnostics or runtime_bridge_posture or
    gateway_doctor_json_includes_gateway_capability_summary"` (`3 passed`),
    `ruff check src\openzues\cli.py tests\test_cli.py`, and
    `mypy src\openzues\cli.py`.

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

- [x] `OZ-PLUGIN-001AJ` configured-channel config/global owner trust gate
  - Source: `openclaw-main/src/plugins/channel-presence-policy.ts` and
    `openclaw-main/src/plugins/manifest-owner-policy.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_plugin_activation.py`,
    `tests/test_gateway_plugin_activation.py`, `tests/test_cli.py`
  - Contract: non-bundled `config`/`global` manifest channel owners require
    explicit trust through `plugins.allow` or `plugins.entries.<id>.enabled =
    true` before scoped configured-channel activation; otherwise the owner is
    projected as blocked with `blockedReasons=["untrusted-plugin"]`.
  - Evidence required: focused config-owner trust helper test, full activation
    helper suite, adjacent plugin doctor tests, ruff, mypy
  - Status: checkpointed in `0e6ce093`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_gateway_plugin_activation.py::test_resolve_configured_channel_plugin_plan_requires_trust_for_config_owner
    -q` (`1 passed`), `python -m pytest
    tests\test_gateway_plugin_activation.py -q` (`8 passed`), adjacent
    `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_projects_configured_channel_plugin_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons or
    plugins_doctor_json_reports_metadata_only_tool_activation"` (`3 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001AK` configured-channel workspace owner activation gate
  - Source: `openclaw-main/src/plugins/channel-presence-policy.ts` and
    `openclaw-main/src/plugins/config-activation-shared.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_plugin_activation.py`,
    `tests/test_gateway_plugin_activation.py`
  - Contract: workspace-origin manifest channel owners are disabled by
    default for configured-channel scoped activation unless explicitly
    activated through `plugins.allow` or `plugins.entries.<id>.enabled=true`.
  - Evidence required: focused workspace-owner activation helper test, full
    activation helper suite, adjacent plugin doctor tests, ruff, mypy
  - Status: checkpointed in `bb9ef28a`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_gateway_plugin_activation.py::test_resolve_configured_channel_plugin_plan_requires_activation_for_workspace_owner
    -q` (`1 passed`), `python -m pytest
    tests\test_gateway_plugin_activation.py -q` (`9 passed`), adjacent
    `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_projects_configured_channel_plugin_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons or
    plugins_doctor_json_reports_metadata_only_tool_activation"` (`3 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001AL` manifest toolMetadata availability gate
  - Source: `openclaw-main/src/plugins/tools.optional.test.ts`,
    `openclaw-main/src/plugins/tools.ts`, and
    `openclaw-main/src/plugins/manifest-tool-availability.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: manifest-owned tool contracts with `toolMetadata` auth/config
    signals are reported as unavailable in runtime activation posture until
    matching env/config evidence exists; unavailable tools do not count as
    missing runtime executors, while available metadata-only tools still do.
  - Evidence required: focused plugin doctor toolMetadata availability test,
    adjacent plugin doctor/list manifest tests, ruff, mypy
  - Status: checkpointed in `78d905c6`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_gates_manifest_tool_activation_on_auth_env
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_gates_manifest_tool_activation_on_auth_env or
    plugins_doctor_json_reports_metadata_only_tool_activation or
    plugins_doctor_json_projects_manifest_activation_plan_reasons or
    plugins_list_json_discovers_openclaw_manifest_load_paths or
    plugins_list_json_preserves_manifest_auth_and_env_metadata"` (`5 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001AM` installed plugin runtime activation adapter
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/plugins/registry.ts`, and
    `openclaw-main/src/plugins/runtime.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: a fakeable installed-plugin runtime activation adapter can turn
    enabled manifest/load-path records into native active-registry executor
    specs; those specs mark matching plugins imported, move tool ownership into
    `runtimeExecutorPlugins`, and remove matching entries from
    `missingExecutorPlugins`.
  - Evidence required: focused plugin doctor installed activation adapter test,
    adjacent plugin runtime CLI tests, ruff, mypy
  - Status: checkpointed in `26e55209`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    plugins_doctor_json_gates_manifest_tool_activation_on_auth_env or
    plugins_doctor_json_reports_metadata_only_tool_activation or
    plugins_list_json_marks_runtime_executor_plugins_imported or
    plugins_list_json_projects_runtime_executor_inventory or
    plugins_inspect_json_projects_runtime_executor_tools"` (`6 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001AN` installed plugin disabled activation gate
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/plugins/config-state.ts`, and
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: disabled manifest/load-path plugin records are excluded from
    native installed-plugin activation adapter input, do not count as runtime
    executor gaps, and remain `imported=false`.
  - Evidence required: focused plugin doctor disabled activation adapter test,
    adjacent plugin runtime CLI tests, ruff, mypy
  - Status: checkpointed in `457021d6`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_activation_adapter_skips_disabled_manifest_plugins
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_activation_adapter_skips_disabled_manifest_plugins or
    plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    plugins_doctor_json_gates_manifest_tool_activation_on_auth_env or
    plugins_doctor_json_reports_metadata_only_tool_activation or
    plugins_list_json_marks_runtime_executor_plugins_imported or
    plugins_list_json_projects_runtime_executor_inventory or
    plugins_inspect_json_projects_runtime_executor_tools"` (`7 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001AO` installed plugin inspect runtime adapter tool projection
  - Source: `openclaw-main/src/cli/plugins-inspect-command.ts`,
    `openclaw-main/src/plugins/status.ts`, and
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `plugins inspect <id> --runtime --json` resolves installed
    manifest/load-path runtime executors from the native activation adapter
    after target-scoped runtime inventory, then reports runtime capability mode
    and tool rows for the inspected plugin.
  - Evidence required: focused plugin inspect installed activation adapter
    test, adjacent plugin runtime CLI tests, ruff, mypy
  - Status: checkpointed in `fb4fca1b`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_inspect_runtime_json_uses_installed_activation_adapter_tools
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_inspect_runtime_json_uses_installed_activation_adapter_tools or
    plugins_inspect_runtime_json_uses_runtime_loaded_import_state or
    plugins_inspect_json_projects_runtime_executor_tools or
    plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    plugins_doctor_json_activation_adapter_skips_disabled_manifest_plugins or
    plugins_list_json_marks_runtime_executor_plugins_imported or
    plugins_inspect_json_projects_runtime_executor_tools"` (`6 passed`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001AP` installed plugin scoped runtime activation load context
  - Source: `openclaw-main/src/plugins/runtime/load-context.ts`,
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.ts`,
    `openclaw-main/src/plugins/status.ts`, and
    `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: installed plugin runtime activation adapters receive
    OpenClaw-shaped load context fields for scoped runtime loads, including
    `onlyPluginIds`, `workspaceDir`, and `activationSourceConfig`, while
    preserving the target-scoped inspect runtime tool projection.
  - Evidence required: focused plugin inspect scoped activation context test,
    adjacent plugin runtime CLI tests, ruff, mypy
  - Status: checkpointed in `0ebf7884`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_inspect_runtime_activation_adapter_receives_scoped_load_context
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_inspect_runtime_activation_adapter_receives_scoped_load_context or
    plugins_inspect_runtime_json_uses_installed_activation_adapter_tools or
    plugins_inspect_runtime_json_uses_runtime_loaded_import_state or
    plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    plugins_doctor_json_activation_adapter_skips_disabled_manifest_plugins or
    plugins_list_json_marks_runtime_executor_plugins_imported or
    plugins_doctor_json_gates_manifest_tool_activation_on_auth_env"` (`7
    passed`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001AQ` installed plugin activation adapter failure diagnostics
  - Source: `openclaw-main/src/plugins/loader.ts`,
    `openclaw-main/src/plugins/status.ts`, and
    `openclaw-main/src/cli/plugins-inspect-command.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: native installed-plugin activation adapter failures do not crash
    `plugins doctor --json`; they mark scoped plugin rows as `status=error`
    with `failurePhase=load` and project matching error diagnostics.
  - Evidence required: focused plugin doctor activation adapter error test,
    adjacent plugin runtime CLI tests, ruff, mypy
  - Status: checkpointed in `baa32232`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_projects_installed_activation_adapter_errors
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_projects_installed_activation_adapter_errors or
    plugins_inspect_runtime_activation_adapter_receives_scoped_load_context or
    plugins_inspect_runtime_json_uses_installed_activation_adapter_tools or
    plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    plugins_doctor_json_activation_adapter_skips_disabled_manifest_plugins or
    plugins_doctor_json_reports_metadata_only_tool_activation or
    plugins_doctor_json_gates_manifest_tool_activation_on_auth_env"` (`7
    passed`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001AR` installed activation-adapter manifest tool contract enforcement
  - Source: `openclaw-main/src/plugins/registry.ts` and
    `openclaw-main/src/plugins/loader.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: native installed-plugin activation adapter runtime tools must be
    declared in the plugin manifest's `contracts.tools`; undeclared adapter
    tools are dropped from runtime executor projection, manifest-declared tools
    remain missing until a declared executor exists, and doctor diagnostics use
    OpenClaw's `plugin must declare contracts.tools for: <tool>` message.
  - Evidence required: focused plugin doctor contract test, adjacent plugin
    runtime CLI tests, ruff, mypy
  - Status: checkpointed in `aac25d80`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_rejects_installed_activation_adapter_tool_outside_manifest_contract
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_rejects_installed_activation_adapter_tool_outside_manifest_contract
    or plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    plugins_doctor_json_activation_adapter_skips_disabled_manifest_plugins or
    plugins_doctor_json_projects_installed_activation_adapter_errors or
    plugins_inspect_runtime_json_uses_installed_activation_adapter_tools or
    plugins_inspect_runtime_activation_adapter_receives_scoped_load_context or
    plugins_doctor_json_reports_metadata_only_tool_activation"` (`7 passed`),
    `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001AS` installed activation-adapter OpenClaw runtime load options
  - Source: `openclaw-main/src/plugins/runtime/load-context.ts`,
    `openclaw-main/src/plugins/runtime/load-context.test.ts`,
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.ts`, and
    `openclaw-main/src/plugins/runtime/runtime-registry-loader.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: native installed-plugin activation adapters receive the
    OpenClaw runtime load-option envelope, including `rawConfig`,
    `config`, `activationSourceConfig`, `autoEnabledReasons`, `env`,
    `workspaceDir` when resolved, scoped `onlyPluginIds`, and
    `throwOnLoadError=true`.
  - Evidence required: focused plugin doctor load-options test, adjacent
    plugin runtime CLI tests, ruff, mypy
  - Status: checkpointed in `ee12d2d4`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_activation_adapter_receives_openclaw_runtime_load_options
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_activation_adapter_receives_openclaw_runtime_load_options
    or plugins_inspect_runtime_activation_adapter_receives_scoped_load_context
    or plugins_doctor_json_rejects_installed_activation_adapter_tool_outside_manifest_contract
    or plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    plugins_doctor_json_activation_adapter_skips_disabled_manifest_plugins or
    plugins_doctor_json_projects_installed_activation_adapter_errors or
    plugins_inspect_runtime_json_uses_installed_activation_adapter_tools"` (`7
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001AT` installed-record manifest runtime activation
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/plugins/loader.ts`, and
    `openclaw-main/src/plugins/discovery.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: persisted `plugins.installs.<id>.installPath` records are
    discovered as manifest-backed plugin records even when the path is absent
    from `plugins.load.paths`, preserving manifest `contracts.tools`, install
    metadata, enabled status, and native activation-adapter runtime executor
    projection.
  - Evidence required: focused plugin doctor install-record activation test,
    adjacent installed-plugin activation/list tests, ruff, mypy
  - Status: checkpointed in `b8f39fe3`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_activates_installed_record_manifest_without_load_path
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugins_doctor_json_activates_installed_record_manifest_without_load_path
    or plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    plugins_doctor_json_rejects_installed_activation_adapter_tool_outside_manifest_contract
    or plugins_doctor_json_activation_adapter_receives_openclaw_runtime_load_options
    or plugins_doctor_json_activation_adapter_skips_disabled_manifest_plugins or
    plugins_list_json_projects_installed_plugin_activation_state or
    plugins_list_json_keeps_installed_plugin_allowlist_authoritative"` (`7
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001AU` bundled plugin env discovery/default-disable gate
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/plugins/discovery.ts`, and
    `openclaw-main/src/plugins/config-activation-shared.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: `OPENCLAW_BUNDLED_PLUGINS_DIR` contributes bundled manifest
    records to native plugin list/doctor inventory, marks them
    `origin=bundled`, and preserves OpenClaw's rule that bundled plugins
    without `enabledByDefault=true` remain disabled even when listed in
    `plugins.allow`.
  - Evidence required: focused bundled plugin discovery/default-disable test,
    adjacent bundled/install/plugin-list tests, ruff, mypy
  - Status: checkpointed in `3de3621e`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_discovers_bundled_plugins_disabled_by_default
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "bundled_plugins_disabled_by_default or
    plugins_list_json_discovers_openclaw_manifest_load_paths or
    plugins_doctor_json_activates_installed_record_manifest_without_load_path
    or plugins_doctor_json_activation_adapter_skips_disabled_manifest_plugins
    or plugins_install_json_uses_bundled_plugin_for_bare_id or
    plugins_install_prefers_dist_runtime_bundled_tree_for_package_root"` (`6
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001AV` installed plugin runtime entry-source metadata
  - Source: `openclaw-main/src/plugins/discovery.ts`,
    `openclaw-main/src/plugins/package-entry-resolution.ts`, and
    `openclaw-main/src/plugins/loader.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: manifest-backed plugin records discovered from install records
    or load paths expose resolved runtime entry files from package
    `openclaw.extensions` or default `index.*` candidates as
    `runtimeEntrySource` and `runtimeEntrySources`, so native activation
    adapters can import the same module entry OpenClaw would load.
  - Evidence required: focused installed-record runtime entry-source adapter
    context test, adjacent plugin metadata/runtime tests, ruff, mypy
  - Status: checkpointed in `4f732754`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_installed_record_activation_context_includes_runtime_entry_source
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "runtime_entry_source or
    plugins_list_json_discovers_openclaw_manifest_load_paths or
    plugins_doctor_json_activates_installed_record_manifest_without_load_path
    or plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    bundled_plugins_disabled_by_default"` (`5 passed`), `ruff check
    src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001AW` bundled channel explicit activation
  - Source: `openclaw-main/src/plugins/loader.test.ts` and
    `openclaw-main/src/plugins/config-activation-shared.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: bundled channel plugin records discovered from
    `OPENCLAW_BUNDLED_PLUGINS_DIR` are treated as explicitly activated when
    `channels.<id>.enabled=true`, bypass restrictive `plugins.allow` lists,
    and report `activationReason="channel enabled in config"`.
  - Evidence required: focused bundled configured-channel activation test,
    adjacent bundled/default/configured-channel tests, ruff, mypy
  - Status: checkpointed in `e92cfcae`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_marks_configured_bundled_channel_as_explicit
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "configured_bundled_channel_as_explicit or
    bundled_plugins_disabled_by_default or
    plugins_doctor_json_projects_configured_channel_plugin_activation or
    configured_channel_plugin_activation or
    plugins_list_json_discovers_openclaw_manifest_load_paths"` (`4 passed`),
    `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001AX` bundled channel auto-enable activation
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/config/plugin-auto-enable.shared.ts`, and
    `openclaw-main/src/config/channel-configured-shared.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: bundled channel plugin records with meaningful
    `channels.<id>` configuration are treated as auto-enabled even without
    `enabled=true`, remain non-explicit, bypass allowlist misses like
    OpenClaw's materialized auto-enable config, and report
    `<channel> configured` as the activation reason.
  - Evidence required: focused bundled configured-channel auto-enable test,
    adjacent bundled channel activation/default tests, ruff, mypy
  - Status: checkpointed in `f1de1e28`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_marks_configured_bundled_channel_as_auto_enabled
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "configured_bundled_channel_as_auto_enabled or
    configured_bundled_channel_as_explicit or bundled_plugins_disabled_by_default
    or plugins_doctor_json_projects_configured_channel_plugin_activation or
    plugins_list_json_discovers_openclaw_manifest_load_paths"` (`5 passed`),
    `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001AY` bundled channel manifest env-var activation
  - Source: `openclaw-main/src/plugins/channel-plugin-ids.test.ts`,
    `openclaw-main/src/config/channel-configured-shared.ts`, and
    `openclaw-main/src/plugins/manifest-registry.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: bundled channel plugin records with manifest `channelEnvVars`
    are treated as auto-enabled when one declared env var is present, including
    case-insensitive env names and external channel ids, while preserving
    explicit channel-disable blocking.
  - Evidence required: focused bundled manifest env-var activation test,
    adjacent bundled env/config activation tests, ruff, mypy
  - Status: checkpointed in `f39ca17c`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_auto_enables_bundled_channel_from_manifest_env_var
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "manifest_env_var or configured_bundled_channel_as_auto_enabled or
    configured_bundled_channel_as_explicit or bundled_plugins_disabled_by_default
    or plugins_list_json_preserves_manifest_auth_and_env_metadata"` (`5
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001AZ` auto-enabled runtime load-context reasons
  - Source: `openclaw-main/src/plugins/activation-context.ts`,
    `openclaw-main/src/plugins/runtime/load-context.ts`, and
    `openclaw-main/src/plugins/loader.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: runtime activation adapters receive OpenClaw-shaped
    `autoEnabledReasons` keyed by plugin id when a bundled channel plugin is
    auto-enabled from channel config/env discovery, while preserving raw
    config, activation source config, environment, scoped plugin ids, and
    throw-on-load-error options.
  - Evidence required: focused runtime load-context reason test, adjacent
    activation adapter context and bundled auto-enable tests, ruff, mypy
  - Status: checkpointed in `b44685b1`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_activation_adapter_receives_auto_enabled_channel_reasons
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "auto_enabled_channel_reasons or
    activation_adapter_receives_openclaw_runtime_load_options or
    configured_bundled_channel_as_auto_enabled or manifest_env_var or
    activation_adapter_skips_disabled_manifest_plugins"` (`5 passed`), `ruff
    check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001BA` runtime text-transform plugin projection
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/plugins/registry.ts`, and
    `openclaw-main/src/plugins/text-transforms.runtime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: installed plugin runtime activation adapters that return an
    active registry with standalone `textTransforms` project those plugin
    registrations into `plugins doctor --json` runtime activation metadata,
    preserving plugin id/name/source/root and safe input/output replacement
    counts without requiring tool executor registrations.
  - Evidence required: focused runtime text-transform doctor projection test,
    adjacent runtime adapter and metadata-only activation tests, ruff, mypy
  - Status: checkpointed in `5216fb70`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_projects_runtime_text_transform_plugins
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "runtime_text_transform_plugins or installed_plugin_runtime_activation_adapter
    or activation_adapter_receives_openclaw_runtime_load_options or
    auto_enabled_channel_reasons or metadata_only_tool_activation"` (`5
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001BB` auto-enabled runtime resolved config
  - Source: `openclaw-main/src/plugins/runtime/runtime-registry-loader.test.ts`,
    `openclaw-main/src/plugins/runtime/load-context.ts`, and
    `openclaw-main/src/config/plugin-auto-enable.shared.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: runtime activation adapters receive raw config as
    `activationSourceConfig` and a resolved `config` snapshot that materializes
    auto-enabled bundled channel plugins by setting `channels.<id>.enabled`
    and adding the plugin id to restrictive `plugins.allow` lists, matching
    OpenClaw's post-`applyPluginAutoEnable` load context.
  - Evidence required: focused resolved auto-enabled config load-context test,
    adjacent activation context/runtime transform/bundled auto-enable tests,
    ruff, mypy
  - Status: checkpointed in `5cfbf4fe`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_activation_adapter_receives_resolved_auto_enabled_config
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "resolved_auto_enabled_config or auto_enabled_channel_reasons or
    activation_adapter_receives_openclaw_runtime_load_options or
    runtime_text_transform_plugins or configured_bundled_channel_as_auto_enabled
    or manifest_env_var"` (`6 passed`), `ruff check src\openzues\cli.py
    tests\test_cli.py`, and `mypy src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001BC` bundled runtime plugin-SDK import metadata
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/plugins/loader-sdk-import-guardrails.test.ts`, and
    `openclaw-main/src/plugins/sdk-alias.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: bundled package runtime entries that import
    `openclaw/plugin-sdk` or `@openclaw/plugin-sdk` subpaths expose
    `pluginSdkImports` in plugin list/runtime metadata, preserving the exact
    import specifiers a native activation adapter needs for SDK alias
    resolution without executing the TypeScript/JavaScript runtime.
  - Evidence required: focused bundled plugin-SDK import metadata test,
    adjacent runtime-entry/bundled install/text-transform tests, ruff, mypy
  - Status: checkpointed in `54fb7bf8`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_projects_bundled_runtime_plugin_sdk_imports
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "bundled_runtime_plugin_sdk_imports or runtime_entry_source or
    discovers_openclaw_manifest_load_paths or bundled_plugins_disabled_by_default
    or plugins_install_prefers_dist_runtime_bundled_tree_for_package_root or
    runtime_text_transform_plugins"` (`6 passed`), `ruff check
    src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001BD` bundled plugin-SDK alias context
  - Source: `openclaw-main/src/plugins/loader.test.ts`,
    `openclaw-main/src/plugins/plugin-sdk-dist-alias.ts`, and
    `openclaw-main/src/plugins/sdk-alias.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: bundled package runtime entries loaded from `dist/extensions`
    or staged `dist-runtime/extensions` project `pluginSdkResolution="dist"`,
    `pluginSdkPackageRoot`, `pluginSdkDistRoot`, and `pluginSdkAliasRoot`
    metadata to activation adapters when SDK imports are present, allowing a
    native adapter to resolve OpenClaw-style plugin-SDK aliases before
    reporting runtime tools.
  - Evidence required: focused SDK alias activation-adapter test, adjacent SDK
    import/runtime-entry/runtime-transform tests, ruff, mypy
  - Status: checkpointed in `e6b506db`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_passes_bundled_package_plugin_sdk_alias_to_activation_adapter
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "plugin_sdk_alias_to_activation_adapter or bundled_runtime_plugin_sdk_imports
    or runtime_entry_source or
    plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    runtime_text_transform_plugins or
    plugins_install_prefers_dist_runtime_bundled_tree_for_package_root"` (`6
    passed`), `ruff check src\openzues\cli.py tests\test_cli.py`, and `mypy
    src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001BE` source plugin-SDK subpath alias context
  - Source: `openclaw-main/src/plugins/sdk-alias.ts` and
    `openclaw-main/src/plugins/sdk-alias.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: source/git-style bundled plugin runtime entries that import
    OpenClaw plugin-SDK subpaths project `pluginSdkResolution="src"`,
    `pluginSdkSourceRoot`, and a `pluginSdkAliasMap` containing both scoped
    and unscoped SDK aliases for each discovered local shim file, allowing
    native activation adapters to resolve source runtime shims.
  - Evidence required: focused source SDK alias activation-adapter test,
    adjacent SDK alias/runtime-entry tests, ruff, mypy
  - Status: checkpointed in `55e1fb28`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_cli.py::test_plugins_doctor_json_passes_source_plugin_sdk_subpath_aliases_to_activation_adapter
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "source_plugin_sdk_subpath_aliases or plugin_sdk_alias_to_activation_adapter
    or bundled_runtime_plugin_sdk_imports or runtime_entry_source or
    plugins_doctor_json_uses_installed_plugin_runtime_activation_adapter or
    runtime_text_transform_plugins"` (`6 passed`), `ruff check
    src\openzues\cli.py tests\test_cli.py`, and `mypy src\openzues\cli.py`.

- [x] `OZ-PLUGIN-001BF` manifest document extractor contract metadata
  - Source: `openclaw-main/src/plugins/manifest.ts`,
    `openclaw-main/src/plugins/contracts/inventory/bundled-capability-metadata.ts`,
    and `openclaw-main/src/plugins/document-extractors.runtime.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/cli.py`, `tests/test_cli.py`
  - Contract: OpenClaw manifest `contracts.documentExtractors` values are
    normalized into plugin inventory records, survive `plugins list --json`,
    and project capability strings as `document-extractor:<id>` so document
    extractor plugins are visible to native inventory/doctor surfaces.
  - Evidence required: focused document extractor contract test, adjacent
    plugin manifest inventory tests, ruff, mypy
  - Status: checkpointed in `2196c65e`
  - Weight: 1
  - Last verified: 2026-05-04, `python -m pytest
    tests\test_cli.py::test_plugins_list_json_preserves_manifest_document_extractor_contracts
    -q` (`1 passed`), adjacent `python -m pytest tests\test_cli.py -q -k
    "document_extractor_contracts or
    plugins_list_json_preserves_manifest_config_contracts or
    plugins_list_json_preserves_manifest_model_support or
    plugins_list_json_preserves_manifest_channel_configs or
    plugins_list_json_preserves_manifest_qa_runners or
    plugins_list_json_preserves_manifest_auth_and_env_metadata or
    plugins_list_json_preserves_manifest_activation_and_setup or
    plugins_list_json_preserves_manifest_command_aliases or
    plugins_list_json_discovers_openclaw_manifest_load_paths"` (`9 passed`),
    `ruff check src\openzues\cli.py tests\test_cli.py`, and
    `mypy src\openzues\cli.py`.

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

- [x] `OZ-PROV-001F` Native provider result metadata passthrough
  - Source: `openclaw-main/src/infra/outbound/deliver.ts`,
    `openclaw-main/src/infra/outbound/message-action-param-keys.ts`,
    `openclaw-main/src/channels/plugins/types.core.ts`, and
    `openclaw-main/src/cli/send-runtime/channel-outbound-send.test.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/gateway_outbound_runtime.py`,
    `src/openzues/services/ops_mesh.py`
  - Contract: shared native provider delivery results preserve
    OpenClaw-shaped reply/thread, tracking, file, filename, and document
    metadata in the direct send response and persisted outbound delivery
    `provider_result` while keeping the existing structured media request
    contract for caption-capable native providers.
  - Evidence required: focused provider metadata test, adjacent native adapter
    binding and provider metadata tests, ruff, mypy
  - Status: checkpointed in `fb9c9763`
  - Weight: 1
  - Last verified: 2026-05-02, focused `python -m pytest
    tests\test_ops_mesh.py::test_provider_result_persistence_keeps_native_extended_metadata
    -q` (`1 passed`), adjacent `python -m pytest tests\test_ops_mesh.py -q -k
    "provider_result_persistence_keeps_native_extended_metadata or
    provider_result_persistence_keeps_message_id_runtime_and_meta or
    send_direct_channel_message_uses_native_adapter_binding"` (`3 passed`),
    `ruff check src\openzues\services\gateway_outbound_runtime.py
    src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`, and `mypy
    src\openzues\services\gateway_outbound_runtime.py
    src\openzues\services\ops_mesh.py`.

- [x] `OZ-PROV-001G` Telegram GIF media send animation routing
  - Source: `openclaw-main/extensions/telegram/src/send.ts`,
    `openclaw-main/extensions/telegram/src/send.test.ts`, and
    `openclaw-main/extensions/telegram/src/outbound-adapter.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`
  - Contract: Telegram route-backed direct sends detect GIF media from URL or
    OpenClaw-style media kind/gif playback hints and call Bot API
    `sendAnimation` instead of `sendPhoto` unless `forceDocument=true`, while
    preserving caption, reply, silent, thread, and animation `mediaIds`
    provider metadata.
  - Evidence required: focused Telegram GIF send test, adjacent Telegram
    native send/poll/media tests, ruff, mypy
  - Status: checkpointed in `51ee9573`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_telegram_animation_for_gif_media
    -q` (`1 passed`), adjacent `python -m pytest tests\test_ops_mesh.py -q -k
    "telegram_animation_for_gif_media or telegram_native_options or
    telegram_media_group or send_direct_channel_message_uses_telegram_native_route
    or send_direct_channel_poll_uses_telegram_native_route"` (`5 passed`),
    `ruff check src\openzues\services\ops_mesh.py tests\test_ops_mesh.py`,
    and `mypy src\openzues\services\ops_mesh.py`.

- [x] `OZ-PROV-001H` WhatsApp audio/voice media send payload
  - Source: `openclaw-main/extensions/whatsapp/src/send.ts`,
    `openclaw-main/extensions/whatsapp/src/send.test.ts`, and
    `openclaw-main/extensions/whatsapp/src/outbound-media-contract.ts`
  - References: Hermes/Warp `none`
  - Target: `src/openzues/services/ops_mesh.py`
  - Contract: WhatsApp route-backed direct sends detect audio media from media
    kind, URL mime, or `audioAsVoice=true`, send Cloud API `type="audio"`
    payloads instead of default image payloads, split visible text into a
    follow-up text message because audio payloads do not support captions, and
    preserve reply context plus audio delivery result metadata.
  - Evidence required: focused WhatsApp audio send test, adjacent WhatsApp
    native media/reply/gif/poll tests, ruff, mypy
  - Status: checkpointed in `c27d3439`
  - Weight: 1
  - Last verified: 2026-05-02, `python -m pytest
    tests\test_ops_mesh.py::test_ops_mesh_service_send_direct_channel_message_uses_whatsapp_audio_voice_payload
    -q` (`1 passed`), adjacent `python -m pytest tests\test_ops_mesh.py -q -k
    "whatsapp_audio_voice_payload or whatsapp_gif_video or whatsapp_reply_document
    or whatsapp_media or send_direct_channel_poll_uses_whatsapp"` (`5
    passed`), `ruff check src\openzues\services\ops_mesh.py
    tests\test_ops_mesh.py`, and `mypy src\openzues\services\ops_mesh.py`.

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
