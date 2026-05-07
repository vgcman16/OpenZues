# Cross-Repo Implementation Tracker

Last updated: 2026-05-07

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
| Repo-wide OpenClaw parity in OpenZues | ~99.9% | Active, broad parity still open; evidence band ~80-99.9996% | `docs/openclaw-parity-progress.md`, `docs/openclaw-parity-unresolved-seams.md` |
| Active gateway/session/tool-contract path | ~99.9% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Chat/session contract subfamily | ~98.3% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Runtime/CLI/doctor native bridge | ~99.9% | Mostly landed; packaging and installed plugin depth remain | `docs/openclaw-parity-progress.md` |
| Hermes reference surface | 80-85% | Reference-only rough status from repo inspection | `docs/tracking/03-hermes-reference-status.md` |
| Warp reference surface | Mixed | Reference-only; client-local plus backend-gated areas | `docs/tracking/04-warp-reference-status.md` |

## Current Worktree Boundary

The imported plugin SDK test-fixtures facade slice is checkpointed in `aa63f674`.
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
| OZ-PLUGIN-001 | Real installed plugin module import/activation | Test-fixtures SDK shim checkpointed in `aa63f674` | Repo-wide +0.1%, plugin metadata/runtime +0.1% | Continue exact `test-node-mocks` alias |
| OZ-CANVAS-001 | Media/voice/web/canvas breadth | Canvas shortcode normalization checkpointed in `c34e4a77` | Repo-wide +0.1%, browser/canvas/nodes/voice +0.1% | Continue media/canvas/provider breadth |
| OZ-COMP-001 | Companion apps/nodes parity | QR JSON setup-code contract checkpointed in `b79b87c3` | Repo-wide +0.1%, companion/setup breadth +0.1% | Continue companion QR/setup-code human/remote breadth |
| OZ-PROV-001 | Provider-native outbound/inbound breadth | Feishu/Lark post/rich-text embedded media hydration checkpointed in `ed3aedb5` | Repo-wide +0.1%, provider-native breadth +0.1% | Rotate to `OZ-PLUGIN-001` |

## Active Slice Detail

- [x] `OZ-PLUGIN-00206` Imported messaging-targets helper shim
  - Source: `openclaw-main/src/plugin-sdk/messaging-targets.ts` and
    `openclaw-main/src/channels/targets.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `messaging-targets` and get the narrow public target parser
    barrel for target construction, id normalization, mention/prefix parsing,
    at-user parsing, and required target-kind validation.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `cd85f7f5`
  - Weight: 1
  - Last verified: 2026-05-07, focused messaging-targets proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1027 deselected`), adjacent
    imported-plugin proof (`218 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00207` Imported request-url helper shim
  - Source: `openclaw-main/src/plugin-sdk/request-url.ts`
  - References: `openclaw-main/src/plugin-sdk/fetch-auth.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `request-url` and use `resolveRequestUrl` for string, `URL`,
    request-like `{ url }`, and unsupported inputs through the native runtime
    import path.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: verified; source/test behavior checkpointed in `f4a23a25` and
    reverified on 2026-05-07
  - Weight: 1
  - Last verified: 2026-05-07, focused request-url/fetch-SSRF proof (`1
    passed`), adjacent SDK helper proof (`2 passed, 1028 deselected`),
    adjacent imported-plugin proof (`218 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-00208` Imported persistent-dedupe helper shim
  - Source: `openclaw-main/src/plugin-sdk/persistent-dedupe.ts`
  - References: `openclaw-main/src/plugin-sdk/persistent-dedupe.test.ts`,
    `openclaw-main/src/plugin-sdk/memory-host-events.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `persistent-dedupe` and use persistent namespace-scoped duplicate
    records, warmup, memory fallback on disk errors, in-process race guards,
    and claimable claim/commit/release flows through the native runtime import
    path.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `cfe26bca`
  - Weight: 1
  - Last verified: 2026-05-07, focused persistent-dedupe proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1027 deselected`), adjacent
    imported-plugin proof (`219 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00209` Imported qa-runner-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/qa-runner-runtime.ts`,
    `openclaw-main/src/plugin-sdk/private-qa-bundled-env.ts`
  - References: `openclaw-main/src/plugin-sdk/qa-runner-runtime.test.ts`,
    `openclaw-main/src/plugin-sdk/qa-runtime.test-helpers.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `qa-runner-runtime`, lazily load QA lab and bundled plugin test
    API surfaces, report missing QA runtime availability, discover sorted
    QA runner manifests, match bundled/activated registrations, project
    blocked runners, and reject duplicate, invalid, or undeclared runner
    registrations.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `f9d46a8f`
  - Weight: 1
  - Last verified: 2026-05-07, focused qa-runner-runtime proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1029 deselected`), adjacent
    imported-plugin proof (`220 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00210` Imported models-provider-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/models-provider-runtime.ts`,
    `openclaw-main/src/auto-reply/reply/commands-models.ts`
  - References: `openclaw-main/src/auto-reply/reply/commands-models.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `models-provider-runtime`, build provider/model Map+Set data,
    preserve model names, hide legacy runtime providers from picker output,
    expose OpenClaw Pi runtime-choice labels, format provider auth headers,
    and resolve `/models` provider menus, paginated/all provider lists,
    unknown-provider responses, out-of-range page responses, deprecated
    `/models add` text, and non-model command null returns.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `695de78b`
  - Weight: 1
  - Last verified: 2026-05-07, focused models-provider-runtime proof (`1
    passed`), adjacent SDK helper proof (`6 passed, 1027 deselected`),
    adjacent imported-plugin proof (`221 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00211` Imported skill-commands-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/skill-commands-runtime.ts`,
    `openclaw-main/src/auto-reply/skill-commands.ts`,
    `openclaw-main/src/agents/skills/command-specs.ts`
  - References: `openclaw-main/src/auto-reply/skill-commands.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `skill-commands-runtime`, list agent/workspace skill commands,
    honor agent/default allowlists including explicit empty lists, merge
    filters for shared workspaces, skip missing workspaces, de-dupe skillNames,
    sanitize command names, preserve descriptions, and project tool dispatch
    metadata.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `14864460`
  - Weight: 1
  - Last verified: 2026-05-07, focused skill-commands-runtime proof (`1
    passed`), adjacent SDK helper proof (`5 passed, 1029 deselected`),
    adjacent imported-plugin proof (`222 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00212` Imported skills-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/skills-runtime.ts`,
    `openclaw-main/src/agents/skills/refresh-state.ts`
  - References: `openclaw-main/src/agents/skills/refresh.test.ts`,
    `openclaw-main/src/gateway/config-reload.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `skills-runtime`, bump/get global and workspace snapshot versions,
    decide refresh from cached/next versions, register/unsubscribe listeners,
    emit refresh events with reason/path metadata, and swallow listener errors
    while continuing delivery.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `106ddcb8`
  - Weight: 1
  - Last verified: 2026-05-07, focused skills-runtime proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1032 deselected`), adjacent
    imported-plugin proof (`223 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00213` Imported agent-runtime core helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/agent-scope.ts`,
    `openclaw-main/src/agents/agent-paths.ts`,
    `openclaw-main/src/agents/current-time.ts`,
    `openclaw-main/src/agents/date-time.ts`,
    `openclaw-main/src/agents/defaults.ts`,
    `openclaw-main/src/agents/identity.ts`,
    `openclaw-main/src/agents/provider-id.ts`
  - References: `openclaw-main/src/agents/agent-scope.test.ts`,
    `openclaw-main/src/agents/agent-paths.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for default model constants, provider ID
    normalization/lookup, agent list/default/config/workspace/dir/session
    resolution, identity/ack/message/response prefix resolution, timestamp
    normalization, Cron-style current-time lines, and OpenClaw agent-dir env
    overrides.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a8e871a3`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime core proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1033 deselected`), adjacent
    imported-plugin proof (`224 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00214` Imported agent-runtime model-selection helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/model-selection.ts`,
    `openclaw-main/src/agents/model-selection-normalize.ts`,
    `openclaw-main/src/agents/model-selection-shared.ts`,
    `openclaw-main/src/agents/model-selection-resolve.ts`,
    `openclaw-main/src/agents/model-ref-shared.ts`
  - References: `openclaw-main/src/agents/model-selection.test.ts`,
    `openclaw-main/src/agents/model-selection-resolve.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for model key normalization, model ref parsing,
    persisted runtime/override model resolution, alias indexes, configured
    catalog/allowlist helpers, default and subagent model selection, allowed
    model status/projection, and reasoning default projection.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0d009e7d`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime model-selection proof
    (`1 passed`), adjacent SDK helper proof (`3 passed, 1034 deselected`),
    adjacent imported-plugin proof (`225 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00215` Imported agent-runtime tool bridge helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/tools/common.ts`,
    `openclaw-main/src/tools/index.ts`,
    `openclaw-main/src/tools/availability.ts`,
    `openclaw-main/src/tools/descriptors.ts`,
    `openclaw-main/src/tools/diagnostics.ts`,
    `openclaw-main/src/tools/execution.ts`,
    `openclaw-main/src/tools/planner.ts`,
    `openclaw-main/src/tools/protocol.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for tool input/authorization errors, owner-only
    execution wrapping, parameter readers, action gates, result helpers,
    available-tag parsing, descriptor helpers, availability evaluation,
    executor ref formatting, tool-plan sorting/diagnostics, and protocol
    descriptor projection.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `01653787`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime tool bridge proof (`1
    passed`), adjacent SDK helper proof (`3 passed, 1035 deselected`),
    adjacent imported-plugin proof (`226 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00216` Imported agent-runtime facade utility helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/model-auth-markers.ts`,
    `openclaw-main/src/agents/sandbox-paths.ts`,
    `openclaw-main/src/agents/identity-avatar.ts`,
    `openclaw-main/src/agents/simple-completion-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for persisted auth marker constants/checks,
    OAuth/SecretRef marker helpers, sandbox path resolution and data URL
    rejection, public avatar source redaction, and alias/profile-aware
    simple-completion model selection.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a6d70a6f`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime facade utility proof (`1
    passed`), adjacent SDK helper proof (`4 passed, 1035 deselected`),
    adjacent imported-plugin proof (`227 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00217` Imported agent-runtime model-catalog lookup helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/model-catalog.ts`,
    `openclaw-main/src/agents/model-catalog-lookup.ts`,
    `openclaw-main/src/agents/model-catalog.types.ts`
  - References: `openclaw-main/src/agents/model-catalog.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for provider-alias-aware catalog lookup,
    providerless unique-match lookup, and text/image/audio/document input
    capability probes.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a5794303`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime model-catalog proof (`1
    passed`), adjacent SDK helper proof (`5 passed, 1035 deselected`),
    adjacent imported-plugin proof (`228 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00218` Imported agent-runtime PI embedded utility helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/pi-embedded-utils.ts`,
    `openclaw-main/src/shared/text/assistant-visible-text.ts`,
    `openclaw-main/src/shared/text/reasoning-tags.ts`,
    `openclaw-main/src/shared/chat-message-content.ts`
  - References: `openclaw-main/src/agents/pi-embedded-utils.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for assistant-message detection, assistant text
    extraction, visible final-answer extraction, native reasoning extraction,
    thinking-tag splitting/promotion/extraction, reasoning message formatting,
    downgraded tool-call text stripping, and Minimax XML stripping.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `db2affa5`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime PI utility proof (`1
    passed`), adjacent SDK helper proof (`7 passed, 1034 deselected`),
    adjacent imported-plugin proof (`229 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00219` Imported agent-runtime embedded block chunker shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/pi-embedded-block-chunker.ts`,
    `openclaw-main/src/markdown/fences.ts`
  - References: `openclaw-main/src/agents/pi-embedded-block-chunker.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for `EmbeddedBlockChunker`, preserving paragraph
    flushing, forced drain, max-length clamping, fence-safe chunk emission,
    buffered-text visibility, and reset/`hasBuffered` lifecycle behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `da591809`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime block chunker proof (`1
    passed`), adjacent SDK helper proof (`8 passed, 1034 deselected`),
    adjacent imported-plugin proof (`230 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00220` Imported agent-runtime model-auth helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/model-auth.ts`,
    `openclaw-main/src/agents/model-auth-env.ts`,
    `openclaw-main/src/agents/model-auth-runtime-shared.ts`,
    `openclaw-main/src/agents/auth-profiles.ts`
  - References: `openclaw-main/src/agents/model-auth.profiles.test.ts`,
    `openclaw-main/src/agents/auth-profile-runtime-contract.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for custom provider API-key lookup, env-SecretRef
    resolution, synthetic local-provider auth posture, runtime-available auth
    probes, model auth-mode projection, async provider/model auth resolution,
    and local/auth-header override helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `b93c187b`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime model-auth proof (`1
    passed`), adjacent SDK helper proof (`9 passed, 1034 deselected`),
    adjacent imported-plugin proof (`231 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00221` Imported agent-runtime schema/typebox helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/schema/typebox.ts`,
    `openclaw-main/src/agents/schema/string-enum.ts`,
    `openclaw-main/src/infra/outbound/channel-target.ts`
  - References: `openclaw-main/src/plugins/contracts/plugin-sdk-subpaths.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for channel target schemas, channel target-array
    schemas, string enum schemas, and optional string enum schemas with
    OpenClaw target descriptions and enum-object support.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0884d4f3`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime schema/typebox proof (`1
    passed`), adjacent SDK helper proof (`10 passed, 1034 deselected`),
    adjacent imported-plugin proof (`232 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00222` Imported agent-runtime web-tool helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/tools/web-shared.ts`,
    `openclaw-main/src/agents/tools/web-fetch-utils.ts`,
    `openclaw-main/src/agents/tools/web-guarded-fetch.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for web-tool cache key/read/write helpers,
    timeout/cache TTL resolution, bounded response text reads, whitespace/
    Markdown/text helpers, HTML content extraction, trusted/self-hosted/strict
    endpoint wrappers, and fakeable guarded fetch lifecycle behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9bc67f5e`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime web-tool proof (`1
    passed`), adjacent SDK helper proof (`11 passed, 1034 deselected`),
    adjacent imported-plugin proof (`233 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00223` Imported agent-runtime provider-auth alias helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/provider-auth-aliases.ts`,
    `openclaw-main/src/plugins/plugin-config-trust.ts`,
    `openclaw-main/src/plugins/plugin-control-plane-context.ts`
  - References: `openclaw-main/src/agents/provider-auth-aliases.test.ts`,
    `openclaw-main/src/plugins/provider-auth-choices.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for provider auth alias-map resolution, cache
    reset, deprecated auth-choice alias mapping, origin-priority conflict
    handling, trusted workspace plugin gating, and alias-aware provider auth
    id resolution.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `61731b33`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime provider-auth alias proof
    (`1 passed`), adjacent SDK helper proof (`12 passed, 1034 deselected`),
    adjacent imported-plugin proof (`234 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00224` Imported agent-runtime TTS helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/tts/tts.ts`,
    `openclaw-main/src/plugin-sdk/tts-runtime.ts`,
    `openclaw-main/extensions/speech-core/src/tts.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` plus direct/scoped `tts-runtime` for TTS config
    merging, provider/persona normalization, prefs-backed auto/provider/
    persona/max-length/summarization state, directive parser access, explicit
    overrides, provider-order probes, prompt hints, payload pass-through, and
    no-provider synthesis failure projection.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9b328bbd`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime TTS proof (`1 passed`),
    adjacent SDK helper proof (`13 passed, 1034 deselected`), adjacent
    imported-plugin proof (`235 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00225` Imported agent-runtime command entrypoint shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime.ts`,
    `openclaw-main/src/agents/agent-command.ts`,
    `openclaw-main/src/agents/agent-runtime-config.ts`,
    `openclaw-main/src/agents/command/types.ts`,
    `openclaw-main/src/commands/agent.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime` for `agentCommand`, `agentCommandFromIngress`,
    and `__testing` command-preparation helpers; local calls default to owner
    and model-override trust, ingress calls require explicit booleans,
    preparation preserves source validation messages, and execution either
    dispatches through a fakeable runner hook or returns a precise native
    bridge unavailable error.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9e6496fb`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime command entrypoint proof
    (`1 passed`), adjacent SDK helper proof (`14 passed, 1034 deselected`),
    adjacent imported-plugin proof (`236 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00226` Imported file-lock helper shim
  - Source: `openclaw-main/src/plugin-sdk/file-lock.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `file-lock` and use process-local re-entrant lock acquisition,
    `.lock` sidecar files, stale-lock removal, timeout error code/lockPath
    projection, test cleanup helpers, and `withFileLock` callback release.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ed03c127`
  - Weight: 1
  - Last verified: 2026-05-07, focused file-lock proof (`1 passed`),
    adjacent SDK helper proof (`15 passed, 1034 deselected`), adjacent
    imported-plugin proof (`237 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00227` Imported google-model-id alias shim
  - Source: `openclaw-main/src/plugin-sdk/google-model-id.ts`,
    `openclaw-main/src/plugin-sdk/provider-model-shared.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `google-model-id` and get the upstream alias names
    `normalizeGoogleModelId` and `normalizeAntigravityModelId` mapped to the
    provider model ID normalizers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `67db67b5`
  - Weight: 1
  - Last verified: 2026-05-07, focused google-model-id proof (`1 passed`),
    adjacent SDK helper proof (`16 passed, 1034 deselected`), adjacent
    imported-plugin proof (`238 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00228` Imported googlechat-runtime-shared schema shim
  - Source: `openclaw-main/src/plugin-sdk/googlechat-runtime-shared.ts`,
    `openclaw-main/src/config/zod-schema.providers-core.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `googlechat-runtime-shared` and get only the upstream
    `GoogleChatConfigSchema` provider object schema instead of the broad
    generic SDK surface.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `f721b7e3`
  - Weight: 1
  - Last verified: 2026-05-07, focused googlechat-runtime-shared proof (`1
    passed`), adjacent SDK helper proof (`17 passed, 1034 deselected`),
    adjacent imported-plugin proof (`239 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00229` Imported open-prose exact plugin-entry shim
  - Source: `openclaw-main/src/plugin-sdk/open-prose.ts`,
    `openclaw-main/src/plugin-sdk/plugin-entry.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `open-prose` and receive only `definePluginEntry`, while the
    helper preserves `reload`, `nodeHostCommands`, and
    `securityAuditCollectors` with cached lazy `configSchema` resolution.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ef8830b1`
  - Weight: 1
  - Last verified: 2026-05-07, focused open-prose proof (`1 passed`),
    adjacent SDK helper proof (`18 passed, 1034 deselected`), adjacent
    imported-plugin proof (`240 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00230` Imported runtime-group-policy helper shim
  - Source: `openclaw-main/src/plugin-sdk/runtime-group-policy.ts`,
    `openclaw-main/src/config/runtime-group-policy.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `runtime-group-policy` and receive the upstream blocked-label
    map, default policy lookup, open/allowlist provider runtime policy
    resolvers, and one-shot missing-provider fallback warning helper.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `b11adc13`
  - Weight: 1
  - Last verified: 2026-05-07, focused runtime-group-policy proof (`1
    passed`), adjacent SDK helper proof (`20 passed, 1033 deselected`),
    adjacent imported-plugin proof (`241 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00231` Imported browser-cdp helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-cdp.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-cdp` and receive exact `parseBrowserHttpUrl` and
    `redactCdpUrl` helpers with OpenClaw protocol, port, normalized URL, and
    credential-redaction behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4e15c3c2`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-cdp proof (`1 passed`),
    adjacent SDK helper proof (`22 passed, 1032 deselected`), adjacent
    imported-plugin proof (`242 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00232` Imported browser-config-support helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-config-support.ts`,
    `openclaw-main/src/config/paths.ts`,
    `openclaw-main/extensions/browser/src/sdk-config.ts`,
    `openclaw-main/src/gateway/net.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-config-support` and receive exact gateway port
    resolution, browser control/CDP port derivation, loopback host detection,
    CONFIG_DIR, path, and regex helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `33463b7c`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-config-support proof (`1
    passed`), adjacent SDK helper proof (`23 passed, 1032 deselected`),
    adjacent imported-plugin proof (`243 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00233` Imported browser-config facade shim
  - Source: `openclaw-main/src/plugin-sdk/browser-config.ts`,
    `openclaw-main/src/plugin-sdk/browser-profiles.ts`,
    `openclaw-main/src/plugin-sdk/browser-cdp.ts`,
    `openclaw-main/src/plugin-sdk/browser-control-auth.ts`,
    `openclaw-main/src/plugin-sdk/browser-trash.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-config` and receive OpenClaw browser defaults,
    config/profile resolution helpers, browser control auth helpers, CDP URL
    helpers, and safe trash facade exports without falling back to the broad
    SDK proxy.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `300224b7`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-config facade proof (`1
    passed`), adjacent SDK helper proof (`24 passed, 1032 deselected`),
    adjacent imported-plugin proof (`244 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00234` Imported browser-control-auth helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-control-auth.ts`,
    `openclaw-main/extensions/browser/src/browser/control-auth.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-control-auth` and receive the exact OpenClaw
    `resolveBrowserControlAuth`, `shouldAutoGenerateBrowserAuth`, and
    `ensureBrowserControlAuth` runtime helpers with gateway auth mode,
    config-first credential, env fallback, and test/Vitest suppression
    behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d1d7b371`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-control-auth proof (`1
    passed`), focused entrypoints proof (`1 passed`), adjacent SDK helper
    proof (`26 passed, 1031 deselected`), adjacent imported-plugin proof (`245
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00235` Imported browser-profiles helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-profiles.ts`,
    `openclaw-main/extensions/browser/browser-profiles.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-profiles` and receive the exact OpenClaw browser default
    constants, `resolveBrowserConfig`, and `resolveProfile` helpers with
    configured profile defaulting, CDP range derivation, loopback detection,
    tab-cleanup defaults, and existing-session profile projection.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `73d20703`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-profiles proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`27
    passed, 1031 deselected`), adjacent imported-plugin proof (`246 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00236` Imported browser-config-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-config-runtime.ts`,
    `openclaw-main/src/config/config.ts`,
    `openclaw-main/src/config/paths.ts`,
    `openclaw-main/src/plugins/config-state.ts`,
    `openclaw-main/src/utils/boolean.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-config-runtime` and receive config IO, runtime config
    snapshot, config path/gateway/browser port, plugin config normalization,
    effective enable-state, boolean parsing, and CONFIG_DIR/path text helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7a4ef6f0`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-config-runtime proof (`1
    passed`), focused entrypoints proof (`1 passed`), adjacent SDK helper
    proof (`28 passed, 1031 deselected`), adjacent imported-plugin proof (`247
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00237` Imported browser-trash helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-trash.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-trash` and receive the exact OpenClaw `movePathToTrash`
    helper with allowed-root validation, home `.Trash` containerized
    destinations, and cross-device copy/remove fallback.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9a90555e`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-trash proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`29
    passed, 1031 deselected`), adjacent imported-plugin proof (`248 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00238` Imported browser-maintenance helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-maintenance.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-maintenance` and receive `movePathToTrash` plus
    `closeTrackedBrowserTabsForSessions`, preserving OpenClaw's no-session
    no-op and graceful unavailable cleanup warning behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ce39d8c6`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-maintenance proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`30
    passed, 1031 deselected`), adjacent imported-plugin proof (`249 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00239` Imported browser-host-inspection helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-host-inspection.ts`,
    `openclaw-main/extensions/browser/src/browser/chrome.executables.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-host-inspection` and receive
    `parseBrowserMajorVersion`, `readBrowserVersion`, and
    `resolveGoogleChromeExecutableForPlatform`, preserving OpenClaw null
    results for invalid versions, missing executables, and unsupported
    platforms.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `bf5ce3f0`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-host-inspection proof (`1
    passed`), focused entrypoints proof (`1 passed`), adjacent SDK helper proof
    (`31 passed, 1031 deselected`), adjacent imported-plugin proof (`250
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00240` Imported browser-node-host helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-node-host.ts`,
    `openclaw-main/extensions/browser/src/node-host/invoke-browser.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-node-host` and receive `runBrowserProxyCommand`,
    preserving OpenClaw validation for missing `paramsJSON` and missing `path`
    plus an honest unavailable boundary when the node-host browser proxy is not
    wired.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2ef00b04`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-node-host proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`32
    passed, 1031 deselected`), adjacent imported-plugin proof (`251 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00241` Imported browser-node-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-node-runtime.ts`,
    `openclaw-main/extensions/browser/src/sdk-node-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-node-runtime` and receive the browser node-host gateway
    utility aggregate, including JSON parsing, error shaping, gateway auth
    resolution, node command policy checks, node-invoke unavailable projection,
    raw WebSocket data conversion, `runExec`, `defaultRuntime`, and
    callback-style abort-signal `withTimeout`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `bc7ef301`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-node-runtime proof (`1
    passed`), focused entrypoints proof (`1 passed`), adjacent SDK helper proof
    (`33 passed, 1031 deselected`), adjacent imported-plugin proof (`252
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00242` Imported browser-setup-tools helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-setup-tools.ts`,
    `openclaw-main/extensions/browser/src/sdk-setup-tools.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-setup-tools` and receive the browser setup helper
    aggregate for tool results, node selection, CLI/help/docs formatting,
    string enum schemas, MIME/media store helpers, image resize planning,
    env scoping helpers, and fetch preconnect tagging.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `50876922`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-setup-tools proof (`1
    passed`), focused entrypoints proof (`1 passed`), adjacent SDK helper proof
    (`34 passed, 1031 deselected`), adjacent imported-plugin proof (`253
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00243` Imported browser-support helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-support.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-support` and receive the aggregate of
    `browser-config-runtime`, `browser-node-runtime`,
    `browser-security-runtime`, and `browser-setup-tools` without broad SDK
    proxy fallback.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `37eec77e`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-support proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`35
    passed, 1031 deselected`), adjacent imported-plugin proof (`254 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00244` Imported browser-bridge helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-bridge.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `browser-bridge` and receive `startBrowserBridgeServer` and
    `stopBrowserBridgeServer`, with precise unavailable errors while the
    activated browser bridge runtime is not wired.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `f0635cce`
  - Weight: 1
  - Last verified: 2026-05-07, focused browser-bridge proof (`1 passed`),
    focused entrypoints proof (`1 passed`), adjacent SDK helper proof (`36
    passed, 1031 deselected`), adjacent imported-plugin proof (`255 passed,
    812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00245` Imported agent-harness-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-harness-runtime.ts`,
    `openclaw-main/src/plugin-sdk/agent-harness.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-harness-runtime` / `agent-harness` and receive terminal
    fallback classification, tool metadata inference, progress output
    normalization/truncation, the upstream max-output constant, and a precise
    unavailable boundary for heavyweight coding tool construction.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ee7f5c49`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-harness-runtime proof (`1
    passed`), adjacent SDK helper proof (`6 passed, 1062 deselected`),
    adjacent imported-plugin proof (`256 passed, 812 deselected`), `ruff
    check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00246` Imported sandbox helper shim
  - Source: `openclaw-main/src/plugin-sdk/sandbox.ts`,
    `openclaw-main/src/agents/sandbox.ts`,
    `openclaw-main/src/agents/sandbox/ssh.ts`,
    `openclaw-main/src/agents/sandbox/sanitize-env-vars.ts`,
    `openclaw-main/src/agents/sandbox/backend.ts`, and
    `openclaw-main/src/agents/sandbox/fs-bridge-rename-targets.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `sandbox` and receive backend registry helpers, SSH command
    builders/session config helpers, sanitized env projection, writable rename
    target resolution, temp-dir resolution, and run-command timeout bridging,
    with precise unavailable boundaries for remote fs bridge/upload helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2aba5dbc`
  - Weight: 1
  - Last verified: 2026-05-07, focused sandbox proof (`1 passed`), adjacent
    SDK helper proof (`7 passed, 1062 deselected`), adjacent imported-plugin
    proof (`257 passed, 812 deselected`), `ruff check`, `mypy`, and `git diff
    --check`.

- [x] `OZ-PLUGIN-00247` Imported proxy-capture helper shim
  - Source: `openclaw-main/src/plugin-sdk/proxy-capture.ts`,
    `openclaw-main/src/proxy-capture/env.ts`,
    `openclaw-main/src/proxy-capture/store.sqlite.ts`,
    `openclaw-main/src/proxy-capture/runtime.ts`,
    `openclaw-main/src/proxy-capture/blob-store.ts`, and
    `openclaw-main/src/proxy-capture/paths.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `proxy-capture` and receive debug proxy env/settings resolution,
    WebSocket agent fallback, capture-store leasing, blob persistence,
    session/event query helpers, HTTP exchange capture with sensitive-header
    redaction, fetch patch lifecycle, and WS event capture.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `84300681`
  - Weight: 1
  - Last verified: 2026-05-07, focused proxy-capture proof (`1 passed`),
    adjacent SDK helper proof (`6 passed, 1064 deselected`), adjacent
    imported-plugin proof (`258 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00248` Imported setup-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/setup-runtime.ts`,
    `openclaw-main/src/channels/plugins/setup-helpers.ts`,
    `openclaw-main/src/channels/plugins/setup-wizard-helpers.ts`,
    `openclaw-main/src/channels/plugins/setup-wizard-binary.ts`, and
    `openclaw-main/src/channels/plugins/setup-wizard-proxy.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `setup-runtime` and receive account setup adapters, setup input
    validators, allow-from and group-access sections, setup status builders,
    account-scoped config patching, setup entry parsing, delegated setup
    wizard proxies, and CLI-path text input helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `252f28fe`
  - Weight: 1
  - Last verified: 2026-05-07, focused setup-runtime proof (`1 passed`),
    adjacent SDK helper proof (`6 passed, 1065 deselected`), adjacent
    imported-plugin proof (`259 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00249` Imported setup-tools helper shim
  - Source: `openclaw-main/src/plugin-sdk/setup-tools.ts`,
    `openclaw-main/src/cli/command-format.ts`,
    `openclaw-main/src/infra/archive.ts`,
    `openclaw-main/src/infra/brew.ts`,
    `openclaw-main/src/infra/detect-binary.ts`,
    `openclaw-main/src/terminal/links.ts`, and
    `openclaw-main/src/utils.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `setup-tools` and receive CLI command formatting, docs-link
    formatting, `CONFIG_DIR`, Homebrew executable lookup, binary detection,
    and promise-returning archive extraction with upstream-shaped unsupported
    archive errors.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `e0f1e72c`
  - Weight: 1
  - Last verified: 2026-05-07, focused setup-tools proof (`1 passed`),
    adjacent SDK helper proof (`8 passed, 1064 deselected`), adjacent
    imported-plugin proof (`260 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00250` Imported config-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/config-runtime.ts`,
    `openclaw-main/src/plugin-sdk/plugin-config-runtime.ts`,
    `openclaw-main/src/config/io.ts`,
    `openclaw-main/src/config/mutate.ts`,
    `openclaw-main/src/config/logging.ts`,
    `openclaw-main/src/config/sessions/store.ts`,
    `openclaw-main/src/config/sessions/reset.ts`, and adjacent config policy
    helpers re-exported by the upstream barrel
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `config-runtime` and receive plugin config lookup, runtime config
    snapshots, config file IO/mutation helpers, config-update logging,
    context/group/native-command/Telegram policy helpers, cron/session-store
    helpers, model-session helpers, and configured secret resolution through
    the native bridge.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `74fd1711`
  - Weight: 1
  - Last verified: 2026-05-07, focused config-runtime proof (`1 passed`),
    adjacent SDK helper proof (`7 passed, 1066 deselected`), adjacent
    imported-plugin proof (`261 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00251` Imported plugin-config-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/plugin-config-runtime.ts`,
    `openclaw-main/src/plugins/config-state.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `plugin-config-runtime` and receive plugin config lookup, live
    config fallback behavior, runtime-config requirement errors, normalized
    plugin config projection, and effective enable-state resolution without
    falling through to the broad SDK proxy.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `458d6c7f`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-config-runtime proof (`1
    passed`), adjacent SDK helper proof (`8 passed, 1066 deselected`),
    adjacent imported-plugin proof (`262 passed, 812 deselected`), `ruff
    check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00252` Imported config-mutation helper shim
  - Source: `openclaw-main/src/plugin-sdk/config-mutation.ts`,
    `openclaw-main/src/config/mutate.ts`,
    `openclaw-main/src/config/io.ts`,
    `openclaw-main/src/config/logging.ts`, and
    `openclaw-main/src/commands/models/shared.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `config-mutation` and receive config snapshot reads,
    `mutateConfigFile`, `replaceConfigFile`, `updateConfig`, and
    config-update logging through the native bridge.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a9813667`
  - Weight: 1
  - Last verified: 2026-05-07, focused config-mutation proof (`1 passed`),
    adjacent SDK helper proof (`9 passed, 1066 deselected`), adjacent
    imported-plugin proof (`263 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00253` Imported provider-tools helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-tools.ts`,
    `openclaw-main/src/agents/schema/clean-for-gemini.ts`, and
    `openclaw-main/src/plugins/provider-model-compat.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `provider-tools` and receive Gemini schema cleanup/inspection,
    XAI unsupported-keyword stripping and model compat metadata, OpenAI
    strict-schema normalization/violation helpers, and provider compatibility
    hook selection without falling through to the broad SDK proxy.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2762ee46`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-tools proof (`1 passed`),
    adjacent SDK helper proof (`7 passed, 1069 deselected`), adjacent
    imported-plugin proof (`264 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00254` Imported provider-stream-shared helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-stream-shared.ts`,
    `openclaw-main/src/agents/pi-embedded-runner/stream-payload-utils.ts`,
    `openclaw-main/src/agents/pi-embedded-runner/zai-stream-wrappers.ts`,
    `openclaw-main/src/agents/pi-embedded-runner/moonshot-thinking-stream-wrappers.ts`,
    and `openclaw-main/src/shared/message-content-blocks.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `provider-stream-shared` and receive stream wrapper composition,
    tool-stream defaults, HTML entity decoding for tool-call arguments,
    payload patch wrappers, Anthropic prefill stripping, DeepSeek V4
    reasoning-content patching, and Google thinking payload sanitization
    without falling through to the broad SDK proxy.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `711865e0`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-stream-shared proof (`1
    passed`), adjacent SDK helper proof (`8 passed, 1069 deselected`),
    adjacent imported-plugin proof (`265 passed, 812 deselected`), `ruff
    check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00255` Imported provider-stream helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-stream.ts` and
    `openclaw-main/src/plugin-sdk/provider-stream-family.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `provider-stream` / `provider-stream-family` and receive the
    provider stream family hook matrix, canonical hook constants, Google
    thinking wrapping, Moonshot thinking/keep handling, Minimax fast-mode model
    rewriting, OpenAI response defaults, OpenRouter and Kilocode reasoning
    wrappers, and tool-stream default-on behavior through the native bridge.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `da9a3e66`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-stream proof (`1 passed`),
    adjacent SDK helper proof (`5 passed, 1073 deselected`), adjacent
    imported-plugin proof (`266 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00256` Imported provider-transport-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-transport-runtime.ts`,
    `openclaw-main/src/agents/transport-stream-shared.ts`,
    `openclaw-main/src/agents/transport-message-transform.ts`,
    `openclaw-main/src/agents/system-prompt-cache-boundary.ts`, and
    `openclaw-main/src/agents/openai-transport-stream.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `provider-transport-runtime` and receive guarded fetch shape,
    OpenAI completions parameter shaping, prompt-boundary stripping, transport
    message replay repair, header merging, payload sanitization, usage
    initialization, writable stream shape, and stream finalization/failure
    helpers through the native bridge.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `dd8bcfd8`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-transport-runtime proof (`1
    passed`), adjacent SDK helper proof (`4 passed, 1075 deselected`),
    adjacent imported-plugin proof (`267 passed, 812 deselected`), `ruff
    check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00257` Imported provider-http helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-http.ts`,
    `openclaw-main/src/agents/provider-http-errors.ts`,
    `openclaw-main/src/media-understanding/shared.ts`,
    `openclaw-main/src/agents/provider-attribution.ts`, and
    `openclaw-main/src/agents/provider-request-config.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `provider-http` and receive provider HTTP error projection,
    response-text limiting, transcription FormData/file-name helpers,
    operation deadline/polling helpers, guarded JSON/multipart/transcription
    posts, provider attribution/policy/capability resolution, request-header
    merging, transport override sanitization, and dispatcher/TLS policy
    shaping through the native bridge.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `750bbf71`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-http proof (`1 passed`),
    adjacent SDK helper proof (`5 passed, 1075 deselected`), adjacent
    imported-plugin proof (`268 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00258` Imported provider-catalog-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-catalog-runtime.ts`,
    `openclaw-main/src/plugins/provider-runtime.ts`,
    `openclaw-main/src/plugins/providers.ts`, and
    `openclaw-main/src/plugins/providers.runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `provider-catalog-runtime`, register provider plugin surfaces
    through the native plugin API, list/scoped-filter provider plugins, match
    provider refs against aliases/hook aliases, honor config deny/disabled
    filtering, resolve owning plugin ids, report provider load-in-flight
    posture, and aggregate `augmentModelCatalog` hooks through the native
    bridge.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2ede5f0d`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-catalog-runtime proof (`1
    passed`), adjacent SDK helper proof (`5 passed, 1076 deselected`),
    adjacent imported-plugin proof (`269 passed, 812 deselected`), `ruff
    check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00259` Imported provider-onboard helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-onboard.ts`,
    `openclaw-main/src/agents/model-allowlist-entry.ts`,
    `openclaw-main/src/agents/model-ref-shared.ts`, and
    `openclaw-main/src/config/model-input.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `provider-onboard`, mutate onboarding agent/provider config,
    preserve existing agent model aliases and fallback models, apply
    default-model/default-models/model-catalog presets, normalize legacy
    OpenCode Zen default posture, keep preset applier ordering, and add raw
    plus canonical allowlist model refs through the native bridge.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2c994a4c`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-onboard proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1078 deselected`), adjacent
    imported-plugin proof (`270 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00260` Imported provider-usage helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-usage.ts`,
    `openclaw-main/src/infra/provider-usage.fetch.ts`,
    `openclaw-main/src/infra/provider-usage.fetch.shared.ts`,
    `openclaw-main/src/infra/provider-usage.shared.ts`, and provider-specific
    usage fetch helpers under `openclaw-main/src/infra/`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `provider-usage`, build provider usage/error snapshots, clamp
    usage percentages, resolve legacy PI auth tokens, apply fetch timeouts,
    and fetch/normalize Claude, Codex, Gemini, MiniMax, and z.ai usage
    payloads through fakeable provider fetchers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `cbc85bd2`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-usage proof (`1 passed`),
    adjacent SDK helper proof (`5 passed, 1078 deselected`), adjacent
    imported-plugin proof (`271 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00205` Imported media-understanding provider-helper shim
  - Source: `openclaw-main/src/plugin-sdk/media-understanding.ts`,
    `openclaw-main/src/media-understanding/openai-compatible-video.ts`,
    `openclaw-main/src/media-understanding/openai-compatible-audio.ts`, and
    `openclaw-main/src/media-understanding/shared.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `media-understanding`, build/coerce OpenAI-compatible video
    helper payloads, normalize fallback strings, run OpenAI-compatible audio
    transcription helper requests with FormData/header/base URL shaping, and
    expose image helper call surfaces through an injectable image runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4a383013`
  - Weight: 1
  - Last verified: 2026-05-07, focused media-understanding helper proof (`1
    passed`), adjacent SDK helper proof (`3 passed, 1026 deselected`),
    adjacent imported-plugin proof (`217 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00204` Imported media-understanding-runtime helper shim
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
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `media-understanding-runtime`, run provider-backed image/audio/
    video file understanding, preserve request prompt/timeout overrides,
    resolve provider registry entries, select local attachments, return
    disabled/no-attachment decisions, run direct `describeImageFileWithModel`,
    trim outputs, and pass provider call metadata.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `65d2ce12`
  - Weight: 1
  - Last verified: 2026-05-07, focused media-understanding-runtime proof (`1
    passed`), adjacent SDK helper proof (`4 passed, 1024 deselected`),
    adjacent imported-plugin proof (`216 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00203` Imported realtime-voice helper shim
  - Source: `openclaw-main/src/plugin-sdk/realtime-voice.ts`,
    `openclaw-main/src/realtime-voice/provider-types.ts`,
    `openclaw-main/src/realtime-voice/provider-registry.ts`,
    `openclaw-main/src/realtime-voice/provider-resolver.ts`,
    `openclaw-main/src/realtime-voice/agent-consult-tool.ts`,
    `openclaw-main/src/realtime-voice/agent-consult-runtime.ts`,
    `openclaw-main/src/realtime-voice/session-runtime.ts`, and
    `openclaw-main/src/realtime-voice/audio-codec.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `realtime-voice`, expose audio-format constants, resolve/list/get
    realtime voice providers, resolve configured providers with auto-select and
    default model handling, build agent-consult tool prompts/visibility, route
    bridge-session callbacks through the active child session, and expose
    PCM/mu-law/resampling helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0f6e62d7`
  - Weight: 1
  - Last verified: 2026-05-07, focused realtime-voice proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1024 deselected`), adjacent
    imported-plugin proof (`215 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00202` Imported realtime-transcription helper shim
  - Source: `openclaw-main/src/plugin-sdk/realtime-transcription.ts`,
    `openclaw-main/src/realtime-transcription/provider-registry.ts`,
    `openclaw-main/src/plugins/provider-registry-shared.ts`, and
    `openclaw-main/src/realtime-transcription/websocket-session.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `realtime-transcription`, normalize/list/get/canonicalize
    providers, and create realtime transcription sessions that preserve
    queued audio, ready marking, close state, sendJson/sendBinary transport
    hooks, and pre-ready connect failure/error callback behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `18a7e15b`
  - Weight: 1
  - Last verified: 2026-05-06, focused realtime-transcription proof (`1
    passed`), adjacent SDK helper proof (`2 passed, 1024 deselected`),
    adjacent imported-plugin proof (`214 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00201` Imported video-generation-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/video-generation-runtime.ts`,
    `openclaw-main/src/video-generation/runtime.ts`,
    `openclaw-main/src/video-generation/normalization.ts`,
    `openclaw-main/src/video-generation/capabilities.ts`, and
    `openclaw-main/src/video-generation/duration-support.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `video-generation-runtime`, list fakeable runtime providers, and
    run provider-backed `generateVideo` with model candidate fallback,
    configured timeout inheritance, video mode capability resolution,
    reference audio/providerOptions/duration skip guards, supported-duration
    normalization, mixed reference forwarding, generated-video result shaping,
    normalization metadata projection, ignored override reporting,
    missing-provider attempts, undeliverable asset errors, and no-model config
    errors with provider env-var hints.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2cf18309`
  - Weight: 1
  - Last verified: 2026-05-06, focused video-generation-runtime proof (`1
    passed`), adjacent SDK helper proof (`4 passed, 1021 deselected`),
    adjacent imported-plugin proof (`213 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00200` Imported image-generation-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/image-generation-runtime.ts` and
    `openclaw-main/src/image-generation/runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `image-generation-runtime`, list fakeable runtime providers, and
    run provider-backed `generateImage` with model candidate fallback,
    configured timeout inheritance, image override normalization, generated
    image result shaping, normalization metadata projection, ignored override
    reporting, warning hooks, missing-provider attempts, and no-model config
    errors with provider env-var hints.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `719fcee8`
  - Weight: 1
  - Last verified: 2026-05-06, focused image-generation-runtime proof (`1
    passed`), adjacent SDK helper proof (`6 passed, 1018 deselected`),
    adjacent imported-plugin proof (`212 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZZ` Imported media-generation-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/media-generation-runtime.ts`,
    `openclaw-main/src/plugin-sdk/media-generation-runtime-shared.ts`, and
    `openclaw-main/src/media-generation/runtime-shared.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `media-generation-runtime` plus
    `media-generation-runtime-shared` and receive OpenClaw-shaped model
    candidate auto-fallback ordering, no-model and generation-failure
    messaging, failover-attempt recording, normalization-entry detection,
    aspect-ratio/size derivation and closest-match resolution, resolution
    matching, duration clamping, and normalization metadata projection.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `f475d85a`
  - Weight: 1
  - Last verified: 2026-05-06, focused media-generation-runtime proof (`1
    passed`), adjacent SDK helper proof (`6 passed, 1017 deselected`),
    adjacent imported-plugin proof (`211 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZY` Imported music-generation-core helper shim
  - Source: `openclaw-main/src/plugin-sdk/music-generation-core.ts`,
    `openclaw-main/src/music-generation/model-ref.ts`,
    `openclaw-main/src/music-generation/provider-registry.ts`,
    `openclaw-main/src/config/model-input.ts`,
    `openclaw-main/src/agents/failover-error.ts`,
    `openclaw-main/src/logging/subsystem.ts`, and
    `openclaw-main/src/secrets/provider-env-vars.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `music-generation-core` SDK helpers and receive OpenClaw-shaped
    model reference parsing, model config primary/fallback readers, failover
    detection/description, provider env-var hints, empty native provider
    lookup, and subsystem logger availability.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a17da4e3`
  - Weight: 1
  - Last verified: 2026-05-06, focused music-generation-core proof (`1
    passed`), adjacent SDK helper proof (`5 passed, 1017 deselected`),
    adjacent imported-plugin proof (`210 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZX` Imported image-generation-core helper shim
  - Source: `openclaw-main/src/plugin-sdk/image-generation-core.ts`,
    `openclaw-main/src/image-generation/model-ref.ts`,
    `openclaw-main/src/image-generation/provider-registry.ts`,
    `openclaw-main/src/media-generation/runtime-shared.ts`,
    `openclaw-main/src/config/model-input.ts`,
    `openclaw-main/src/agents/failover-error.ts`,
    `openclaw-main/src/infra/gemini-auth.ts`,
    `openclaw-main/src/plugin-sdk/provider-model-shared.ts`,
    `openclaw-main/src/logging/subsystem.ts`, and
    `openclaw-main/src/secrets/provider-env-vars.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `image-generation-core` SDK helpers and receive OpenClaw-shaped
    model reference parsing, model candidate/fallback selection, no-model and
    failover error formatting, Gemini API-key/OAuth parsing, Google model id
    normalization, `OPENAI_DEFAULT_IMAGE_MODEL`, API-key resolver delegation,
    provider env-var hints, empty native provider lookup, and subsystem logger
    availability.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `1a128fa5`
  - Weight: 1
  - Last verified: 2026-05-06, focused image-generation-core proof (`1
    passed`), adjacent SDK helper proof (`4 passed, 1017 deselected`),
    adjacent imported-plugin proof (`209 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZW` Imported video-generation-core helper shim
  - Source: `openclaw-main/src/plugin-sdk/video-generation-core.ts`,
    `openclaw-main/src/video-generation/model-ref.ts`,
    `openclaw-main/src/video-generation/provider-registry.ts`,
    `openclaw-main/src/media-generation/runtime-shared.ts`,
    `openclaw-main/src/config/model-input.ts`,
    `openclaw-main/src/agents/failover-error.ts`,
    `openclaw-main/src/logging/subsystem.ts`, and
    `openclaw-main/src/secrets/provider-env-vars.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `video-generation-core` SDK helpers and receive OpenClaw-shaped
    model reference parsing, model candidate/fallback selection, no-model and
    failover error formatting, provider env-var hints, empty native provider
    lookup, and subsystem logger availability.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `f85c7465`
  - Weight: 1
  - Last verified: 2026-05-06, focused video-generation-core proof (`1
    passed`), adjacent SDK helper proof (`3 passed, 1017 deselected`),
    adjacent imported-plugin proof (`208 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZV` Imported speech-core helper shim
  - Source: `openclaw-main/src/plugin-sdk/speech-core.ts`,
    `openclaw-main/src/tts/tts-core.ts`,
    `openclaw-main/src/tts/tts-provider-helpers.ts`,
    `openclaw-main/src/tts/directives.ts`,
    `openclaw-main/src/tts/provider-registry.ts`,
    `openclaw-main/src/tts/provider-registry-core.ts`,
    `openclaw-main/src/tts/tts-auto-mode.ts`,
    `openclaw-main/src/tts/tts-config.ts`, and
    `openclaw-main/src/agents/provider-http-errors.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `speech-core` SDK helpers and receive OpenClaw-shaped TTS
    normalization, directive parsing, effective config merge, provider id
    handling, provider HTTP errors, response text limits, cleanup scheduling,
    and bounded summarization unavailable/error behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ff03eba7`
  - Weight: 1
  - Last verified: 2026-05-06, focused speech-core proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1016 deselected`), adjacent
    imported-plugin proof (`207 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZU` Imported memory-host-sdk package facade shims
  - Source: `openclaw-main/packages/memory-host-sdk/src/query.ts`,
    `openclaw-main/packages/memory-host-sdk/src/multimodal.ts`,
    `openclaw-main/packages/memory-host-sdk/src/secret.ts`,
    `openclaw-main/packages/memory-host-sdk/src/status.ts`, and
    `openclaw-main/packages/memory-host-sdk/package.json`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require
    `@openclaw/memory-host-sdk/query`, `multimodal`, `secret`, and `status`
    package facades and receive the same query, multimodal, secret-input, and
    status helper contracts as the plugin SDK compatibility shims.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `c95e0129`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-host-sdk package facade proof
    (`1 passed`), adjacent SDK helper proof (`5 passed, 1013 deselected`),
    adjacent imported-plugin proof (`206 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZT` Imported memory-host-sdk runtime aggregate shim
  - Source: `openclaw-main/packages/memory-host-sdk/src/runtime.ts`,
    `openclaw-main/src/memory-host-sdk/runtime.ts`, and
    `openclaw-main/packages/memory-host-sdk/package.json`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require
    `@openclaw/memory-host-sdk/runtime` as the aggregate of runtime-core,
    runtime-cli, and runtime-files helpers, and can resolve implemented runtime
    package subpaths through the same native shim loader.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ebd215d5`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-host-sdk runtime proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1013 deselected`),
    adjacent imported-plugin proof (`205 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZS` Imported memory-host-sdk engine aggregate shim
  - Source: `openclaw-main/packages/memory-host-sdk/src/engine.ts`,
    `openclaw-main/src/memory-host-sdk/engine.ts`, and
    `openclaw-main/packages/memory-host-sdk/package.json`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require
    `@openclaw/memory-host-sdk/engine` as the aggregate of foundation, storage,
    embeddings, and QMD helpers, and can resolve implemented engine package
    subpaths through the same native shim loader.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `fa5ad046`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-host-sdk engine proof
    (`1 passed`), adjacent SDK helper proof (`5 passed, 1011 deselected`),
    adjacent imported-plugin proof (`204 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZR` Imported memory-core-host-engine-storage helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-engine-storage.ts`,
    `openclaw-main/packages/memory-host-sdk/src/engine-storage.ts`, adjacent
    OpenClaw internal, read-file, schema, sqlite, sqlite-vec, fs-utils,
    backend-config, and multimodal helper behavior
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-engine-storage`, exposing file listing, file entry
    metadata, multimodal chunk construction, Markdown chunking/remapping, read
    windows, vector helpers, schema/sqlite helper shims, missing-file handling,
    concurrency, and backend config reuse.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `884c9afb`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-engine-storage proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1011 deselected`),
    adjacent imported-plugin proof (`203 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZQ` Imported memory-core-host-engine-qmd helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-engine-qmd.ts`,
    `openclaw-main/packages/memory-host-sdk/src/engine-qmd.ts`, adjacent
    OpenClaw QMD query parser, scope, process, session-file, session-id, and
    query-expansion helper behavior
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-engine-qmd`, exposing noisy JSON QMD query parsing,
    no-result handling, scope allow/deny matching, transcript
    listing/classification/export helpers, usage-counted session-id parsing,
    CLI spawn invocation materialization, binary availability checks, and
    capped command execution.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `147b0978`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-engine-qmd proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1010 deselected`),
    adjacent imported-plugin proof (`202 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZP` Imported memory-core-host-engine-foundation helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-engine-foundation.ts`,
    `openclaw-main/packages/memory-host-sdk/src/engine-foundation.ts`, adjacent
    OpenClaw agent scope/config, memory search, SecretInput, safe IO,
    transcript-event, global singleton, concurrency, shell-arg, user-path, and
    UTF-16 truncation helper behavior
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-engine-foundation`, exposing agent scope/config/path
    helpers, memory search and sync config projection, duration parsing,
    SecretInput helpers, safe IO/logging/mime wrappers, transcript listener
    registration, global singleton state, concurrency, shell-arg splitting,
    home path shortening, and UTF-16-safe truncation.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4d0b1103`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-engine-foundation
    proof (`1 passed`), adjacent SDK helper proof (`4 passed, 1009
    deselected`), adjacent imported-plugin proof (`201 passed, 812
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZO` Imported memory-core-host-engine-embeddings helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-engine-embeddings.ts`,
    `openclaw-main/packages/memory-host-sdk/src/engine-embeddings.ts`, adjacent
    OpenClaw provider-registry, batch, vector, remote, and multimodal helpers
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-engine-embeddings`, exposing provider
    registration/listing/lookup, remote embedding provider/fetch helpers,
    batch output/status/grouping helpers, UTF-8 and structured input sizing,
    vector normalization, cache-header sanitization, model-prefix
    normalization, multimodal extension/path helpers, and explicit unavailable
    errors for local model and batch upload backends.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4a1d82a8`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-engine-embeddings
    proof (`1 passed`), adjacent SDK helper proof (`4 passed, 1008
    deselected`), adjacent imported-plugin proof (`200 passed, 812
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZN` Imported memory-core-engine-runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-engine-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-engine-runtime`, exposing the engine-facing memory search
    manager, `MemoryIndexManager`, embedding-provider doctor metadata, audit,
    and repair facade with explicit OpenZues-native unavailable
    metadata/errors when the bundled memory-core engine backend is absent.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ad4b05e5`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-engine-runtime proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1007 deselected`),
    adjacent imported-plugin proof (`199 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZM` Imported memory-core-host-runtime-cli helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-runtime-cli.ts`,
    `openclaw-main/packages/memory-host-sdk/src/runtime-cli.ts`, adjacent
    OpenClaw CLI/runtime/theme/progress/home-path helper behavior
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-runtime-cli`, exposing manager lifecycle wrappers,
    progress wrappers, help formatting, docs links, verbosity state, default
    runtime, theme/color helpers, home-path shortening, and no-target
    command-secret resolution without regressing runtime-secret-resolution.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `762da43c`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-runtime-cli proof
    (`1 passed`), runtime-secret-resolution regression proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1006 deselected`), adjacent
    imported-plugin proof (`198 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZL` Imported memory-host-status alias shim
  - Source: `openclaw-main/src/plugin-sdk/memory-host-status.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-host-status`, re-exporting the verified memory-core-host-status
    helper surface for vector, FTS, and cache status projections.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2317c1e7`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-host-status proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1005 deselected`),
    adjacent imported-plugin proof (`197 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZK` Imported memory-host-search helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-host-search.ts`,
    `openclaw-main/src/plugin-sdk/memory-host-search.runtime.ts`,
    `openclaw-main/src/plugins/memory-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-host-search`, delegating active memory search manager lookup and
    manager cleanup through the registered memory capability runtime while
    preserving the unavailable-manager fallback.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a76a8d50`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-host-search proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1004 deselected`),
    adjacent imported-plugin proof (`196 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZJ` Imported memory-host-markdown helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-host-markdown.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-host-markdown`, exposing trailing-newline and managed Markdown
    block replacement helpers with heading-aware replacement, append behavior,
    whitespace handling, and regex-safe marker matching.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4d8513b6`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-host-markdown proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1003 deselected`),
    adjacent imported-plugin proof (`195 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZI` Imported memory-host-events alias shim
  - Source: `openclaw-main/src/plugin-sdk/memory-host-events.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-host-events`, re-exporting the verified memory-core-host-events
    helper surface for event log paths, append/read JSONL behavior, invalid
    line skipping, limits, and missing-log empty results.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `97885bb6`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-host-events proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1002 deselected`),
    adjacent imported-plugin proof (`194 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZH` Imported memory-host-core alias shim
  - Source: `openclaw-main/src/plugin-sdk/memory-host-core.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-host-core`, re-exporting the verified
    memory-core-host-runtime-core helper surface for runtime config, parameter
    readers, byte-size parsing, cron-style time projection, memory state,
    corpus supplements, public artifacts, and transcript paths.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `362efd71`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-host-core proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1001 deselected`),
    adjacent imported-plugin proof (`193 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZG` Imported memory-core-host-runtime-core helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-runtime-core.ts`,
    `openclaw-main/packages/memory-host-sdk/src/runtime-core.ts`, adjacent
    OpenClaw memory state, current-time, byte-size, routing, and transcript
    helper behavior
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-runtime-core`, exposing OpenClaw-shaped runtime config,
    parameter readers, JSON results, byte-size parsing, cron-style time
    projection, default/session agent lookup, memory search config, transcript
    directory resolution, memory capability state, corpus supplements, public
    artifact sorting, and state cleanup.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7b0703b7`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-runtime-core proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 1000 deselected`),
    adjacent imported-plugin proof (`192 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZF` Imported memory-host-files alias shim
  - Source: `openclaw-main/src/plugin-sdk/memory-host-files.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-host-files`, re-exporting the verified runtime-files helper
    surface for memory file listing, extra path normalization, safe agent
    memory reads, and QMD backend config resolution.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `857111d8`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-host-files proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 999 deselected`),
    adjacent imported-plugin proof (`191 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZE` Imported memory-core-host-runtime-files helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-runtime-files.ts`,
    `openclaw-main/packages/memory-host-sdk/src/runtime-files.ts`,
    `openclaw-main/packages/memory-host-sdk/src/host/internal.ts`,
    `openclaw-main/packages/memory-host-sdk/src/host/read-file.ts`,
    `openclaw-main/packages/memory-host-sdk/src/host/backend-config.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-runtime-files`, exposing memory file listing, extra path
    normalization, safe agent memory reads, and QMD backend config resolution
    with OpenClaw path, pagination, collection, update, limit, and session
    projections.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a8d7b586`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-runtime-files proof
    (`1 passed`), adjacent SDK helper proof (`6 passed, 996 deselected`),
    adjacent imported-plugin proof (`190 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZD` Imported memory-core-host-status helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-status.ts`,
    `openclaw-main/packages/memory-host-sdk/src/status.ts`,
    `openclaw-main/packages/memory-host-sdk/src/host/status-format.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-status`, exposing vector, FTS, and cache formatter
    helpers with OpenClaw `tone` / `state` / `text` projections.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `bfcb12a2`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-status proof
    (`1 passed`), adjacent SDK helper proof (`5 passed, 996 deselected`),
    adjacent imported-plugin proof (`189 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZC` Imported memory-core-host-events helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-events.ts`,
    `openclaw-main/src/memory-host-sdk/events.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-events`, exposing the memory event-log relative path,
    path resolver, async append, JSONL read, invalid-line skipping, limit
    handling, and missing-log empty results.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d5695975`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-events proof
    (`1 passed`), adjacent SDK helper proof (`4 passed, 996 deselected`),
    adjacent imported-plugin proof (`188 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZB` Imported memory-core-host-secret helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-secret.ts`,
    `openclaw-main/packages/memory-host-sdk/src/secret.ts`,
    `openclaw-main/packages/memory-host-sdk/src/host/secret-input.ts`,
    `openclaw-main/packages/memory-host-sdk/src/host/secret-input-utils.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-secret`, exposing configured-secret detection and
    `resolveMemorySecretInputString` with inline trimming, env-backed SecretRef
    resolution through the runtime environment, and OpenClaw unresolved-ref
    errors.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `78f2a009`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-secret proof
    (`1 passed`), adjacent SDK helper proof (`3 passed, 996 deselected`),
    adjacent imported-plugin proof (`187 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001ZA` Imported memory-core-host-multimodal helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-multimodal.ts`,
    `openclaw-main/packages/memory-host-sdk/src/multimodal.ts`,
    `openclaw-main/packages/memory-host-sdk/src/host/multimodal.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-multimodal`, exposing
    `normalizeMemoryMultimodalSettings` and `isMemoryMultimodalEnabled` with
    OpenClaw default modalities, max-file-byte normalization, invalid
    modality filtering, and disabled-state projection.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `5be944f7`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-multimodal proof
    (`1 passed`), adjacent SDK helper proof (`3 passed, 995 deselected`),
    adjacent imported-plugin proof (`186 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001YZ` Imported memory-core-host-query helper shim
  - Source: `openclaw-main/src/plugin-sdk/memory-core-host-query.ts`,
    `openclaw-main/packages/memory-host-sdk/src/query.ts`,
    `openclaw-main/packages/memory-host-sdk/src/host/query-expansion.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `memory-core-host-query`, exposing `extractKeywords` and
    `isQueryStopWordToken` with stop-word filtering, duplicate/numeric
    rejection, and CJK trigram-tokenizer behavior without leaking generic SDK
    exports.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0eaf8bf8`
  - Weight: 1
  - Last verified: 2026-05-06, focused memory-core-host-query proof
    (`1 passed`), adjacent SDK helper proof (`3 passed, 994 deselected`),
    adjacent imported-plugin proof (`185 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001YY` Imported runtime-secret-resolution helper shim
  - Source: `openclaw-main/src/plugin-sdk/runtime-secret-resolution.ts`,
    `openclaw-main/src/cli/command-secret-targets.ts`,
    `openclaw-main/src/secrets/resolve.ts`,
    `openclaw-main/src/secrets/runtime-shared.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `runtime-secret-resolution`, exposing resolver context shape, assignment
    application, env-backed SecretRef resolution maps, channel command secret
    target ids, and an honest unavailable error for gateway command-secret
    resolution.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d9574b0f`
  - Weight: 1
  - Last verified: 2026-05-06, focused runtime-secret-resolution proof
    (`1 passed`), adjacent SDK helper proof (`3 passed, 993 deselected`),
    adjacent imported-plugin proof (`184 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001YX` Imported LM Studio runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/lmstudio.ts`,
    `openclaw-main/src/plugin-sdk/lmstudio-runtime.ts`,
    `openclaw-main/extensions/lmstudio/src/models.ts`,
    `openclaw-main/extensions/lmstudio/src/runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `lmstudio` / `lmstudio-runtime`, exposing LM Studio default constants,
    server/inference base URL normalization, provider config normalization,
    auth-header construction, loaded context-window resolution, reasoning
    capability/compat projection, and model wire entry mapping without generic
    SDK leakage.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `6f11c3fa`
  - Weight: 1
  - Last verified: 2026-05-06, focused LM Studio runtime proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 992 deselected`), adjacent
    imported-plugin proof (`183 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001YW` Imported provider setup helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-setup.ts`,
    `openclaw-main/src/plugin-sdk/self-hosted-provider-setup.ts`,
    `openclaw-main/src/plugins/provider-self-hosted-setup.ts`,
    `openclaw-main/src/agents/self-hosted-provider-defaults.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `provider-setup` / `self-hosted-provider-setup`, exposing self-hosted
    defaults, default model patching, OpenAI-compatible local discovery guard,
    provider discovery projection, interactive auth-result helpers, and
    non-interactive model/auth-profile/default-model config updates.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `25ad92b6`
  - Weight: 1
  - Last verified: 2026-05-06, focused provider setup proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 991 deselected`), provider-auth
    regression proof (`2 passed`), adjacent imported-plugin proof (`182
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001YV` Imported runtime-doctor helper shim
  - Source: `openclaw-main/src/plugin-sdk/runtime-doctor.ts`,
    `openclaw-main/src/config/dangerous-name-matching.ts`,
    `openclaw-main/src/config/channel-compat-normalization.ts`,
    `openclaw-main/src/infra/plugin-install-path-warnings.ts`,
    `openclaw-main/src/plugins/uninstall.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `runtime-doctor`, exposing dangerous-name matching scope collection,
    legacy streaming/channel alias normalization, custom-path install issue
    detection/formatting, and pure plugin config uninstall mutation without
    leaking generic SDK exports.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `1a917206`
  - Weight: 1
  - Last verified: 2026-05-06, focused runtime-doctor proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 990 deselected`), adjacent
    imported-plugin proof (`181 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001YU` Imported CLI runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/cli-runtime.ts`,
    `openclaw-main/src/cli/command-format.ts`,
    `openclaw-main/src/cli/parse-duration.ts`,
    `openclaw-main/src/cli/command-options.ts`,
    `openclaw-main/src/cli/argv-invocation.ts`,
    `openclaw-main/src/cli/help-format.ts`,
    `openclaw-main/src/cli/cli-utils.ts`,
    `openclaw-main/src/cli/command-registration-policy.ts`,
    `openclaw-main/src/cli/program/register-command-groups.ts`,
    `openclaw-main/src/cli/wait.ts`,
    `openclaw-main/src/terminal/note.ts`,
    `openclaw-main/src/terminal/prompt-style.ts`,
    `openclaw-main/src/terminal/theme.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `cli-runtime`, exposing command formatting, duration parsing,
    parent-option inheritance, help examples, command-group registration,
    runtime error handling, argv invocation projection, lazy-subcommand
    policy, note/theme helpers, and version metadata without leaking generic
    SDK exports.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `c052ce13`
  - Weight: 1
  - Last verified: 2026-05-06, focused CLI runtime proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 989 deselected`), adjacent
    imported-plugin proof (`180 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-001YT` Imported ACP binding runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/acp-binding-runtime.ts`,
    `openclaw-main/src/acp/persistent-bindings.lifecycle.ts`,
    `openclaw-main/src/acp/persistent-bindings.resolve.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `acp-binding-runtime`, exposing configured ACP binding resolution plus
    readiness ensure behavior through an injected ACP session manager for
    no-binding, already-ready, and initialize paths.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `37b428c1`
  - Weight: 1
  - Last verified: 2026-05-06, focused ACP binding proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 988 deselected`), adjacent
    imported-plugin proof (`179 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YS` Imported ACP runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/acp-runtime.ts`,
    `openclaw-main/src/acp/control-plane/manager.ts`,
    `openclaw-main/src/acp/runtime/session-meta.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `acp-runtime`, exposing the ACP session-manager singleton, test-helper
    proxy surface, session-store entry reads, and shared ACP backend/error/
    reply-hook exports.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `44166f55`
  - Weight: 1
  - Last verified: 2026-05-06, focused ACP runtime proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 987 deselected`), adjacent
    imported-plugin proof (`178 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YR` Imported ACP runtime backend helper shim
  - Source: `openclaw-main/src/plugin-sdk/acp-runtime-backend.ts`,
    `openclaw-main/src/acp/runtime/errors.ts`,
    `openclaw-main/src/acp/runtime/registry.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `acp-runtime-backend`, exposing ACP runtime error checks, backend
    lookup/require/registration/removal, and the reply-hook early-return path
    with an unavailable result when full ACP dispatch is not available.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4833176b`
  - Weight: 1
  - Last verified: 2026-05-06, focused ACP backend proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 986 deselected`), adjacent
    imported-plugin proof (`177 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YQ` Imported ACPX helper shim
  - Source: `openclaw-main/src/plugin-sdk/acpx.ts`,
    `openclaw-main/src/acp/runtime/errors.ts`,
    `openclaw-main/src/acp/runtime/registry.ts`,
    `openclaw-main/src/plugin-sdk/windows-spawn.ts`,
    `openclaw-main/src/secrets/provider-env-vars.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped `acpx`,
    exposing `AcpRuntimeError`, ACP runtime backend registration/removal,
    Windows spawn candidate/policy/materialization helpers, and provider-auth
    env listing/omission helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `c7541c95`
  - Weight: 1
  - Last verified: 2026-05-06, focused ACPX proof (`1 passed`), adjacent SDK
    helper proof (`3 passed, 985 deselected`), adjacent imported-plugin proof
    (`176 passed, 812 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001YP` Imported diffs helper shim
  - Source: `openclaw-main/src/plugin-sdk/diffs.ts`,
    `openclaw-main/src/plugin-sdk/plugin-entry.ts`,
    `openclaw-main/src/plugin-sdk/temp-path.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped `diffs`,
    exposing the narrow bundled-diffs helper surface for `definePluginEntry`
    and `resolvePreferredOpenClawTmpDir`; `definePluginEntry` resolves
    config schemas lazily once and defaults to the empty plugin config schema.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `008c6120`
  - Weight: 1
  - Last verified: 2026-05-06, focused diffs proof (`1 passed`),
    adjacent SDK helper proof (`13 passed, 974 deselected`), adjacent
    imported-plugin proof (`175 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YO` Imported entrypoints helper shim
  - Source: `openclaw-main/src/plugin-sdk/entrypoints.ts`,
    `openclaw-main/scripts/lib/plugin-sdk-entrypoints.json`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `entrypoints`, exposing canonical SDK entrypoint/subpath arrays,
    facade/public-owned entrypoint lists, source/specifier/package-export
    builders, and expected dist artifact listing.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `bd810f14`
  - Weight: 1
  - Last verified: 2026-05-06, focused entrypoints proof (`1 passed`),
    adjacent SDK helper proof (`13 passed, 973 deselected`), adjacent
    imported-plugin proof (`174 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YN` Imported config-schema helper shim
  - Source: `openclaw-main/src/plugin-sdk/config-schema.ts`,
    `openclaw-main/src/config/zod-schema.ts`,
    `openclaw-main/src/plugins/schema-validator.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `config-schema`, parse root config objects through `OpenClawSchema`, and
    validate JSON Schema values with required-property, additional-property,
    enum allowed-values, and default-application behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ae5489b2`
  - Weight: 1
  - Last verified: 2026-05-06, focused config-schema proof (`1 passed`),
    adjacent SDK helper proof (`13 passed, 972 deselected`), adjacent
    imported-plugin proof (`173 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YM` Imported type-only SDK barrel shims
  - Source: `openclaw-main/src/plugin-sdk/config-types.ts`,
    `openclaw-main/src/plugin-sdk/document-extractor.ts`,
    `openclaw-main/src/plugin-sdk/music-generation.ts`,
    `openclaw-main/src/plugin-sdk/provider-model-types.ts`,
    `openclaw-main/src/plugin-sdk/qa-channel-protocol.ts`,
    `openclaw-main/src/plugin-sdk/tts-runtime.types.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped type-only
    SDK barrels and receive empty runtime modules, with no inherited generic SDK
    exports and no synthetic default object.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `fceeecc8`
  - Weight: 1
  - Last verified: 2026-05-06, focused type-only SDK barrel proof (`1
    passed`), adjacent SDK helper proof (`3 passed, 981 deselected`),
    adjacent imported-plugin proof (`172 passed, 812 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001YL` Imported cli-backend helper shim
  - Source: `openclaw-main/src/plugin-sdk/cli-backend.ts`,
    `openclaw-main/src/agents/cli-watchdog-defaults.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `cli-backend`, exposing `CLI_FRESH_WATCHDOG_DEFAULTS` and
    `CLI_RESUME_WATCHDOG_DEFAULTS` with upstream no-output timeout ratios and
    min/max timeout windows.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `be724e3f`
  - Weight: 1
  - Last verified: 2026-05-06, focused cli-backend proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 980 deselected`), adjacent
    imported-plugin proof (`171 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YK` Imported fetch-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/fetch-runtime.ts`,
    `openclaw-main/src/infra/fetch.ts`,
    `openclaw-main/src/infra/net/proxy-env.ts`,
    `openclaw-main/src/infra/net/proxy-fetch.ts`, and
    `openclaw-main/src/infra/net/ssrf.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `fetch-runtime`, resolve abort-safe fetch wrappers, preserve HTTP proxy
    env precedence and `NO_PROXY` bypass rules, expose trusted-env proxy mode
    projection, preserve proxy-fetch metadata, and create pinned DNS lookup
    callbacks.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `3aa66305`
  - Weight: 1
  - Last verified: 2026-05-06, focused fetch-runtime proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 978 deselected`), adjacent
    imported-plugin proof (`170 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YJ` Imported browser-security-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/browser-security-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `browser-security-runtime`, expose proxy-env, safe file/path, SSRF, port,
    secure-token, temp-path, logging/redaction, external-content, and
    secret-equality helper exports, and preserve safe file/path behavior under
    a root directory.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `66ee1a57`
  - Weight: 1
  - Last verified: 2026-05-06, focused browser-security-runtime proof (`1
    passed`), adjacent SDK helper proof (`4 passed, 977 deselected`),
    adjacent imported-plugin proof (`169 passed, 812 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001YI` Imported media-store helper shim
  - Source: `openclaw-main/src/plugin-sdk/media-store.ts`,
    `openclaw-main/src/media/store.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `media-store`, save buffers beneath `OPENCLAW_STATE_DIR/media`, build
    MIME/extension-aware safe IDs, resolve saved IDs back to regular files,
    reject unsafe IDs, and preserve max-byte failure semantics.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `b45381ad`
  - Weight: 1
  - Last verified: 2026-05-06, focused media-store proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 976 deselected`), adjacent
    imported-plugin proof (`168 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YH` Imported group-activation helper shim
  - Source: `openclaw-main/src/plugin-sdk/group-activation.ts`,
    `openclaw-main/src/auto-reply/group-activation.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `group-activation`, normalize `mention`/`always` group activation modes,
    and parse slash or colon `/activation` commands while preserving invalid
    mode and no-command shapes.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `48d912d7`
  - Weight: 1
  - Last verified: 2026-05-06, focused group-activation proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 975 deselected`), adjacent
    imported-plugin proof (`167 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YG` Imported runtime-fetch helper shim
  - Source: `openclaw-main/src/plugin-sdk/runtime-fetch.ts`,
    `openclaw-main/src/infra/net/runtime-fetch.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `runtime-fetch`, detect mocked fetch implementations, dispatch through
    native runtime fetch, and honor mocked global fetch fallback behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `14cdafc6`
  - Weight: 1
  - Last verified: 2026-05-06, focused runtime-fetch proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 975 deselected`), adjacent
    imported-plugin proof (`166 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YF` Imported runtime-config-snapshot helper shim
  - Source: `openclaw-main/src/plugin-sdk/runtime-config-snapshot.ts`,
    `openclaw-main/src/config/runtime-snapshot.ts`,
    `openclaw-main/src/config/io.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `runtime-config-snapshot`, preserve activation config/rawConfig through
    runtime execution, expose runtime config get/snapshot set/get/clear, keep
    `clearConfigCache` as upstream no-op, and select applicable runtime config
    based on source snapshot equivalence.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `39afd0ea`
  - Weight: 1
  - Last verified: 2026-05-06, focused runtime-config-snapshot proof (`1
    passed`), adjacent SDK helper proof (`3 passed, 974 deselected`),
    adjacent imported-plugin proof (`165 passed, 812 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001YE` Imported oauth-utils helper shim
  - Source: `openclaw-main/src/plugin-sdk/oauth-utils.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `oauth-utils`, encode flat form data with `encodeURIComponent`, generate
    base64url PKCE verifier/challenge pairs, and generate hex-verifier PKCE
    pairs with SHA-256 base64url challenges.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `210beb78`
  - Weight: 1
  - Last verified: 2026-05-06, focused oauth-utils proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 973 deselected`), adjacent
    imported-plugin proof (`164 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YD` Imported system-event-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/system-event-runtime.ts`,
    `openclaw-main/src/infra/system-events.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `system-event-runtime`, enqueue session-keyed ephemeral events, reject
    missing session keys, suppress consecutive duplicates, cap queues at 20
    entries, return cloned peek results, normalize delivery contexts, preserve
    trust defaults, and reset test state.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `5c49a1be`
  - Weight: 1
  - Last verified: 2026-05-06, focused system-event-runtime proof (`1
    passed`), adjacent SDK helper proof (`3 passed, 972 deselected`),
    adjacent imported-plugin proof (`163 passed, 812 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001YC` Imported diagnostic-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/diagnostic-runtime.ts`,
    `openclaw-main/src/infra/diagnostic-flags.ts`,
    `openclaw-main/src/infra/diagnostic-events.ts`,
    `openclaw-main/src/infra/diagnostic-trace-context.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `diagnostic-runtime`, match diagnostic flags from config/environment,
    dispatch public/internal diagnostic events with trust metadata and frozen
    listener payloads, reset test state, and create/parse/format W3C
    traceparent contexts.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `095e35fc`
  - Weight: 1
  - Last verified: 2026-05-06, focused diagnostic-runtime proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 971 deselected`), adjacent
    imported-plugin proof (`162 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YB` Imported json-store helper shim
  - Source: `openclaw-main/src/plugin-sdk/json-store.ts`,
    `openclaw-main/src/infra/json-file.ts`,
    `openclaw-main/src/infra/json-files.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `json-store`, synchronously load/save JSON files, return
    fallback/existence metadata for missing or invalid JSON, and atomically
    write secure JSON files with a trailing newline.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9ba7a00e`
  - Weight: 1
  - Last verified: 2026-05-06, focused json-store proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 970 deselected`), adjacent
    imported-plugin proof (`161 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001YA` Imported heartbeat-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/heartbeat-runtime.ts`,
    `openclaw-main/src/infra/heartbeat-events.ts`,
    `openclaw-main/src/infra/heartbeat-visibility.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `heartbeat-runtime`, map heartbeat indicator types, share emitted event
    state/listeners, isolate listener failures, reset state, and resolve
    heartbeat visibility through account/channel/default precedence.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a5863a1d`
  - Weight: 1
  - Last verified: 2026-05-06, focused heartbeat-runtime proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 969 deselected`), adjacent
    imported-plugin proof (`160 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XZ` Imported context-visibility-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/context-visibility-runtime.ts`,
    `openclaw-main/src/config/context-visibility.ts`,
    `openclaw-main/src/security/context-visibility.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `context-visibility-runtime`, resolve default/channel/account visibility
    precedence, and evaluate/filter supplemental context with upstream-shaped
    decision reasons.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `1e503fde`
  - Weight: 1
  - Last verified: 2026-05-06, focused context-visibility-runtime proof (`1
    passed`), adjacent SDK helper proof (`3 passed, 968 deselected`),
    adjacent imported-plugin proof (`159 passed, 812 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001XY` Imported config-paths helper shim
  - Source: `openclaw-main/src/plugin-sdk/config-paths.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `config-paths`, use `resolveChannelAccountConfigBasePath`, route
    mutations to `channels.<channel>.accounts.<accountId>.` when an account
    entry exists, and fall back to `channels.<channel>.` otherwise.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `c1a26ebe`
  - Weight: 1
  - Last verified: 2026-05-06, focused config-paths proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 967 deselected`), adjacent
    imported-plugin proof (`158 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XX` Imported lazy-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/lazy-runtime.ts`,
    `openclaw-main/src/shared/lazy-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `lazy-runtime`, cache module/surface/named-export imports, and bind async
    methods through upstream-shaped method and method-binder helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `6f66d9b8`
  - Weight: 1
  - Last verified: 2026-05-06, focused lazy-runtime proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 966 deselected`), adjacent
    imported-plugin proof (`157 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XW` Imported poll-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/poll-runtime.ts`,
    `openclaw-main/src/polls.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `poll-runtime`, normalize poll question/options/max selections/duration
    fields, enforce upstream poll validation errors, normalize duration hours,
    and resolve multiselect limits.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `83f15bfa`
  - Weight: 1
  - Last verified: 2026-05-06, focused poll-runtime proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 964 deselected`), adjacent
    imported-plugin proof (`156 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XV` Imported approval-auth-helpers shim
  - Source: `openclaw-main/src/plugin-sdk/approval-auth-helpers.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `approval-auth-helpers`, use `createResolvedApproverActionAuthAdapter`,
    inspect implicit same-chat fallback authorization with
    `isImplicitSameChatApprovalAuthorization`, and observe the
    non-enumerable marker dropping across object clones.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `8511485f`
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-auth-helpers proof (`1
    passed`), adjacent approval proof (`5 passed, 962 deselected`), adjacent
    imported-plugin proof (`155 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XU` Imported approval-approvers alias shim
  - Source: `openclaw-main/src/plugin-sdk/approval-approvers.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `approval-approvers`, receive only `resolveApprovalApprovers`, and
    preserve explicit approver precedence, allowFrom/extraAllowFrom/default
    fallback inference, normalization, and deduplication.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0740c2ab`
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-approvers proof (`1
    passed`), adjacent approval proof (`5 passed, 962 deselected`), adjacent
    imported-plugin proof (`155 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XT` Imported approval-client-runtime alias shim
  - Source: `openclaw-main/src/plugin-sdk/approval-client-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `approval-client-runtime` and receive the same channel approval client
    helper contract as `approval-client-helpers`, including enablement checks,
    target-recipient checks, request filters, profiles, and approval reply
    metadata.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `f24a7746`
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-client-runtime proof (`1
    passed`), adjacent approval proof (`4 passed, 963 deselected`), adjacent
    imported-plugin proof (`155 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XS` Imported approval-renderers helper shim
  - Source: `openclaw-main/src/plugin-sdk/approval-renderers.ts`,
    `openclaw-main/src/plugin-sdk/approval-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native runtime entries can require scoped and unscoped
    `approval-renderers`, build exec/plugin pending payloads, build
    exec/plugin resolved payloads, preserve `execApproval` channel data, and
    access the resolved renderer helpers through the aggregate
    `approval-runtime` barrel.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d6bb4129`
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-renderers proof (`1
    passed`), adjacent approval renderer/aggregate proof (`2 passed`),
    adjacent approval proof (`3 passed, 964 deselected`), adjacent
    imported-plugin proof (`155 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XR` Imported approval-native-runtime expiration scheduling
  - Source: `openclaw-main/src/infra/approval-native-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: requested native approvals with `expiresAtMs` install a timer,
    resolved/expired/stop paths clear timers, and timer expiry finalizes the
    stored active entries through the same expired lifecycle path.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `fa7cacbd`
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-native-runtime expiration
    proof (`1 passed`), adjacent approval proof (`13 passed, 953 deselected`),
    adjacent imported-plugin proof (`154 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XQ` Imported approval-handler capability bridge shim
  - Source: `openclaw-main/src/infra/approval-handler-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can turn a channel approval
    capability's native adapter/runtime into a handler, build pending/
    resolved/expired approval views, deliver and bind pending entries, call
    loaded observe hooks with unwrapped entries, unbind on resolution, apply
    final update/delete/clear-actions results, and return `null` when a
    capability has no native runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `6ea77847`; native expiration scheduling remains
    open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-handler capability proof
    (`1 passed`), adjacent approval proof (`12 passed, 953 deselected`),
    adjacent imported-plugin proof (`153 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XP` Imported approval-handler-runtime wrapper shim
  - Source: `openclaw-main/src/infra/approval-handler-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can map the upstream
    `{ runtime, content, transport, lifecycle }` handler adapter shape onto the
    native approval runtime factory, preserving approval kind, pending content,
    delivery callbacks, active entries, and resolved finalization.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `e23b4e9e`; higher-level capability handler
    wrapper remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-handler-runtime wrapper proof
    (`1 passed`), adjacent approval proof (`12 passed, 952 deselected`),
    adjacent imported-plugin proof (`152 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XO` Imported approval-native-runtime factory shim
  - Source: `openclaw-main/src/infra/approval-native-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can create a native approval
    runtime that resolves exec/plugin approval kind, builds pending content,
    resolves and delivers planned native targets, forwards delivery lifecycle
    callbacks with pending content, tracks active entries, finalizes resolved
    requests, and exposes the factory through `approval-native-runtime` and
    the aggregate `approval-runtime` barrel.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `67a72452`; expiration scheduling and the
    higher-level capability handler wrapper remain open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-native-runtime factory proof
    (`1 passed`), adjacent approval proof (`11 passed, 952 deselected`),
    adjacent imported-plugin proof (`151 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XN` Imported approval-gateway-runtime resolver shim
  - Source: `openclaw-main/src/plugin-sdk/approval-gateway-runtime.ts`,
    `openclaw-main/src/infra/approval-gateway-resolver.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `approval-gateway-runtime` through scoped and unscoped aliases, route
    plugin approvals through `plugin.approval.resolve`, route exec approvals
    through `exec.approval.resolve`, preserve gateway URL/config/display-name
    options, and fall back to plugin approval resolution only for not-found
    exec approval errors when explicitly enabled.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `29c62d3f`; broader native approval runtime/
    handler lifecycle remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-gateway-runtime proof
    (`1 passed`), adjacent approval proof (`10 passed, 952 deselected`),
    adjacent imported-plugin proof (`150 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XM` Imported approval-runtime aggregate shim
  - Source: `openclaw-main/src/plugin-sdk/approval-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `approval-runtime` through scoped and unscoped aliases, resolve exec
    approval decisions, build exec/plugin pending payloads, extract approval
    metadata, compose approver authorization, channel approval profiles,
    delivery capabilities, native origin targets, and request filters through
    the aggregate barrel.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `63554e0a`; broader approval gateway/native
    handler lifecycle remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-runtime proof (`1 passed`),
    adjacent approval proof (`9 passed, 952 deselected`), adjacent
    imported-plugin proof (`149 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XL` Imported approval-handler-runtime adapter factory
  - Source: `openclaw-main/src/plugin-sdk/approval-handler-runtime.ts`,
    `openclaw-main/src/infra/approval-handler-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `approval-handler-runtime` through scoped and unscoped aliases, preserve
    the `approval.native` context capability, wrap native runtime specs into
    canonical availability, presentation, transport, interaction, and observe
    adapters, preserve `eventKinds` and custom approval-kind resolution, and
    keep fallback-safe access for broader handler functions that remain open.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `3434972a`; broader handler lifecycle/gateway
    integration remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-handler-runtime proof
    (`1 passed`), adjacent approval proof (`8 passed, 952 deselected`),
    adjacent imported-plugin proof (`148 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XK` Imported approval-handler-adapter-runtime shim
  - Source:
    `openclaw-main/src/plugin-sdk/approval-handler-adapter-runtime.ts`,
    `openclaw-main/src/infra/approval-handler-adapter-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `approval-handler-adapter-runtime` through scoped and unscoped aliases,
    preserve the `approval.native` context capability, expose eager
    availability checks, lazy-load the backing native runtime once, delegate
    presentation, transport, and interaction hooks, and fire observe hooks
    only after a runtime has been loaded.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `21aa746b`; broader approval handler runtime/
    gateway lifecycle remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-handler-adapter-runtime proof
    (`1 passed`), adjacent approval proof (`7 passed, 952 deselected`),
    adjacent imported-plugin proof (`147 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XJ` Imported approval-native-runtime delivery helpers
  - Source: `openclaw-main/src/plugin-sdk/approval-native-runtime.ts`,
    `openclaw-main/src/infra/approval-native-runtime.ts`,
    `openclaw-main/src/infra/approval-native-delivery.ts`,
    `openclaw-main/src/infra/approval-native-target-key.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `approval-native-runtime` through scoped and unscoped aliases, build
    stable native target keys, resolve origin/approver-DM delivery plans,
    dedupe converged native targets, request DM-only origin notices, deliver
    planned native targets with prepared-target dedupe, and continue after
    per-target delivery failures.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `424e376a`; broader
    `createChannelNativeApprovalRuntime` gateway/event lifecycle remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-native-runtime proof
    (`1 passed`), adjacent approval proof (`6 passed, 952 deselected`),
    adjacent imported-plugin proof (`146 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XI` Imported approval-native-helpers shim
  - Source: `openclaw-main/src/plugin-sdk/approval-native-helpers.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `approval-native-helpers` through scoped and unscoped aliases, compare
    native approval targets with shared route semantics, resolve channel origin
    targets with `shouldHandleRequest` gating and target normalization,
    preserve provider-native delivery targets while normalizing only match
    inputs, and map approvers into DM delivery targets while filtering rejected
    requests and null targets.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `51d8ecdc`; broader approval native runtime/
    gateway/handler flows remain open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-native-helpers proof
    (`1 passed`), adjacent approval proof (`5 passed, 952 deselected`),
    adjacent imported-plugin proof (`145 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XH` Imported approval-delivery-helpers shim
  - Source: `openclaw-main/src/plugin-sdk/approval-delivery-helpers.ts`,
    `openclaw-main/src/plugin-sdk/approval-delivery-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `approval-delivery-helpers` and `approval-delivery-runtime` through
    scoped and unscoped aliases, create and split channel approval
    capabilities, preserve the deprecated `approvals` surface alias,
    authorize exec/plugin approvals by sender, report native DM/channel
    delivery availability, and suppress forwarding fallback only for matching
    native delivery surfaces.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d77756fa`; broader approval gateway/native/
    handler runtimes remain open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-delivery-helpers proof
    (`1 passed`), adjacent approval proof (`4 passed, 952 deselected`),
    adjacent imported-plugin proof (`144 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XG` Imported approval-client-helpers shim
  - Source: `openclaw-main/src/plugin-sdk/approval-client-helpers.ts`,
    `openclaw-main/src/infra/approval-request-filters.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `approval-client-helpers` through scoped and unscoped aliases, resolve
    channel approval enablement, match configured approval targets by
    channel/account/sender, apply agent/session filters with session-key agent
    fallback, compose channel approval profiles, and suppress local prompts
    from approval metadata.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `8a40507d`; broader approval gateway/delivery/
    native/handler runtimes remain open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-client-helpers proof
    (`1 passed`), adjacent approval proof (`3 passed, 952 deselected`),
    adjacent imported-plugin proof (`143 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XF` Imported approval-reply-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/approval-reply-runtime.ts`,
    `openclaw-main/src/infra/exec-approval-reply.ts`,
    `openclaw-main/src/infra/exec-approval-command-display.ts`,
    `openclaw-main/src/infra/exec-approvals.ts`,
    `openclaw-main/src/plugin-sdk/approval-renderers.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `approval-reply-runtime` through scoped and unscoped aliases, build
    approval action descriptors and interactive button payloads, parse
    `/approve` commands, resolve allowed decisions, project command display
    text, build exec/plugin pending reply payloads, and extract approval
    metadata.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2215e898`; broader approval gateway/client/
    delivery/native/handler runtimes remain open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-reply-runtime proof
    (`1 passed`), adjacent approval/runtime proof (`3 passed, 951
    deselected`), adjacent imported-plugin proof (`142 passed, 812
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XE` Imported simple-completion-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/simple-completion-runtime.ts`,
    `openclaw-main/src/agents/pi-embedded-utils.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `simple-completion-runtime` through scoped and unscoped aliases and receive
    deterministic `extractAssistantText` behavior for string content, text
    blocks, non-text filtering, leaked tool XML stripping, MiniMax invocation
    stripping, and HTTP-style assistant error copy.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `13a0fa6d`; broader completion model/auth
    transport helpers remain open
  - Weight: 1
  - Last verified: 2026-05-06, focused simple-completion-runtime proof
    (`1 passed`), adjacent runtime/provider proof (`3 passed, 950
    deselected`), adjacent imported-plugin proof (`141 passed, 812
    deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XD` Imported session-visibility helper shim
  - Source: `openclaw-main/src/plugin-sdk/session-visibility.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `session-visibility` through scoped and unscoped aliases, resolve
    visibility defaults and sandbox clamps, enforce same-session/tree/
    cross-agent policy messages, apply `tools.agentToAgent.allow` wildcard
    checks, and keep spawned-session listing behind a fakeable gateway hook.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4e95bfcb`; broader gateway-backed session
    visibility listing remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused session-visibility proof (`1 passed`),
    adjacent session proof (`5 passed, 947 deselected`), adjacent
    imported-plugin proof (`140 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XC` Imported provider-env-vars helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-env-vars.ts`,
    `openclaw-main/src/secrets/provider-env-vars.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `provider-env-vars` through scoped and unscoped aliases, resolve core plus
    bundled provider auth candidates, expose OpenClaw-style setup env
    overrides, protect prototype-chain lookups, and scrub env maps
    case-insensitively while preserving unrelated bridge keys.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `10d34034`; broader provider/runtime breadth
    remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused provider-env-vars proof (`1 passed`),
    adjacent provider proof (`6 passed, 945 deselected`), adjacent
    imported-plugin proof (`139 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001XB` Imported provider-zai-endpoint helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-zai-endpoint.ts`,
    `openclaw-main/src/plugins/provider-zai-endpoint.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `provider-zai-endpoint` through scoped and unscoped aliases, probe ordered
    global/cn/coding candidates through fakeable fetch functions, return
    verified endpoint metadata, and fall back from coding GLM-5.1 to GLM-4.7
    when the first coding probe fails.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `b3d88717`; broader provider runtime breadth
    remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused provider-zai-endpoint proof
    (`1 passed`), adjacent provider proof (`5 passed, 945 deselected`),
    adjacent imported-plugin proof (`138 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001XA` Imported param-readers helper shim
  - Source: `openclaw-main/src/plugin-sdk/param-readers.ts`,
    `openclaw-main/src/agents/tools/common.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `param-readers`
    through scoped and unscoped aliases and receive the four OpenClaw helper
    exports with snake_case lookup, string/string-or-number, number parsing,
    string-array filtering, and `ToolInputError` required-field behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `e7166e23`; broader SDK/runtime breadth remains
    open
  - Weight: 1
  - Last verified: 2026-05-06, focused param-readers proof (`1 passed`),
    adjacent param/tool proof (`3 passed, 946 deselected`), adjacent
    imported-plugin proof (`137 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001WZ` Imported Telegram command config helper shim
  - Source: `openclaw-main/src/plugin-sdk/telegram-command-config.ts`,
    `openclaw-main/src/shared/custom-command-config.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `telegram-command-config` through scoped and unscoped aliases, share the
    Telegram command name regex object, normalize slash command names/
    descriptions, and resolve custom command validation issues for duplicate,
    missing, reserved, and duplicate-disabled cases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `bd248520`; broader provider command/runtime
    breadth remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused Telegram command config proof
    (`1 passed`), adjacent command-config proof (`2 passed, 946 deselected`),
    adjacent imported-plugin proof (`136 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WY` Imported approval-auth-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/approval-auth-runtime.ts`,
    `openclaw-main/src/plugin-sdk/approval-approvers.ts`,
    `openclaw-main/src/plugin-sdk/approval-auth-helpers.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `approval-auth-runtime` through scoped and unscoped aliases, resolve
    explicit/inferred approvers with OpenClaw dedupe ordering, authorize
    matching approvers, deny non-matching approvers with upstream-shaped copy,
    and allow empty approver sets as the same-chat fallback.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `6cda257f`; broader approval gateway runtime
    breadth remains open
  - Weight: 1
  - Last verified: 2026-05-06, focused approval-auth-runtime proof
    (`1 passed`), adjacent approval/provider-auth proof
    (`2 passed, 945 deselected`), adjacent imported-plugin proof
    (`135 passed, 812 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WX` Imported provider-auth-login runtime alias
  - Source: `openclaw-main/src/plugin-sdk/provider-auth-login.runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `provider-auth-login.runtime` through scoped and unscoped aliases, receive
    the same three login facade exports as `provider-auth-login`, and preserve
    the precise native unavailable error for interactive login flows.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9c1a6b73`; broader SDK/runtime breadth remains
    open
  - Weight: 1
  - Last verified: 2026-05-06, focused provider-auth-login proof
    (`1 passed`), adjacent provider-auth proof (`4 passed, 942 deselected`),
    adjacent imported-plugin proof (`134 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WW` Imported string-coerce-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/string-coerce-runtime.ts`,
    `openclaw-main/src/shared/string-coerce.ts`,
    `openclaw-main/src/utils.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `string-coerce-runtime` through scoped and unscoped aliases and receive
    exact primitive normalization, stringified-id, lowercase, read-string,
    non-empty, and record detection helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `70df7410`; broader SDK/runtime breadth remains
    open
  - Weight: 1
  - Last verified: 2026-05-06, focused string-coerce-runtime proof
    (`1 passed`), adjacent helper proof (`3 passed, 943 deselected`),
    adjacent imported-plugin proof (`134 passed, 812 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WV` Imported run-command normalized helper shim
  - Source: `openclaw-main/src/plugin-sdk/run-command.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `run-command`
    through scoped and unscoped aliases and receive normalized
    `{code, stdout, stderr}` results for success, nonzero exit, empty argv, and
    timeout cases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `96c11a19`; broader process/runtime depth remains
    open
  - Weight: 1
  - Last verified: 2026-05-06, focused run-command proof (`1 passed`),
    adjacent helper proof (`3 passed, 942 deselected`), adjacent
    imported-plugin proof (`133 passed, 812 deselected`), `ruff check`, and
    `mypy`.

- [x] `OZ-PLUGIN-001WU` Imported process-runtime command helper shim
  - Source: `openclaw-main/src/plugin-sdk/process-runtime.ts`,
    `openclaw-main/src/process/exec.ts`,
    `openclaw-main/src/process/linux-oom-score.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `process-runtime`
    and receive real `runCommandWithTimeout`, `runExec`, command env/exit
    helpers, and child OOM wrapper helpers through scoped and unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `b5f485b3`; broader process-runtime depth remains
    open
  - Weight: 1
  - Last verified: 2026-05-06, focused process-runtime proof (`1 passed`),
    adjacent helper proof (`2 passed, 942 deselected`), adjacent
    imported-plugin/runtime proof (`141 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WT` Imported model-session-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/model-session-runtime.ts`,
    `openclaw-main/src/config/agent-limits.ts`,
    `openclaw-main/src/channels/model-overrides.ts`,
    `openclaw-main/src/sessions/model-overrides.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `model-session-runtime` and receive agent concurrency default/clamping,
    channel model override resolution, and session-entry model override
    mutation through scoped and unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `6f5096bc`
  - Weight: 1
  - Last verified: 2026-05-06, focused model-session-runtime proof
    (`1 passed`), adjacent helper proof (`3 passed, 940 deselected`),
    adjacent imported-plugin/runtime proof (`140 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WS` Imported image-generation-core auth-runtime helper shim
  - Source:
    `openclaw-main/src/plugin-sdk/image-generation-core.auth.runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `image-generation-core.auth.runtime` and receive the image-generation
    provider auth resolver through scoped and unscoped aliases without falling
    through to the generic SDK object.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `532fd8de`
  - Weight: 1
  - Last verified: 2026-05-06, focused image-generation-core auth-runtime
    proof (`1 passed`), adjacent helper proof (`3 passed, 939 deselected`),
    adjacent imported-plugin/runtime proof (`139 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WR` Imported host-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/host-runtime.ts`,
    `openclaw-main/src/infra/net/hostname.ts`,
    `openclaw-main/src/infra/scp-host.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `host-runtime` and
    receive hostname normalization and SCP remote host token sanitization
    through scoped and unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `355ebc11`
  - Weight: 1
  - Last verified: 2026-05-06, focused host-runtime proof (`1 passed`),
    adjacent helper proof (`3 passed, 938 deselected`), adjacent
    imported-plugin/runtime proof (`138 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WQ` Imported native-command-config-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/native-command-config-runtime.ts`,
    `openclaw-main/src/config/commands.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `native-command-config-runtime` and receive native command enablement,
    native skills enablement, and explicit-disable helpers through scoped and
    unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d2898256`
  - Weight: 1
  - Last verified: 2026-05-06, focused native-command-config-runtime proof
    (`1 passed`), adjacent helper proof (`3 passed, 937 deselected`),
    adjacent imported-plugin/runtime proof (`137 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WP` Imported logging-core helper shim
  - Source: `openclaw-main/src/plugin-sdk/logging-core.ts`,
    `openclaw-main/src/logging/subsystem.ts`,
    `openclaw-main/src/logging/redact-identifier.ts`,
    `openclaw-main/src/logging/redact.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `logging-core` and
    receive subsystem logger creation, deterministic identifier redaction, and
    sensitive text redaction through scoped and unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `50142470`
  - Weight: 1
  - Last verified: 2026-05-06, focused logging-core proof (`1 passed`),
    adjacent helper proof (`3 passed, 936 deselected`), adjacent
    imported-plugin/runtime proof (`136 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WO` Imported file-access-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/file-access-runtime.ts`,
    `openclaw-main/src/infra/fs-safe.ts`,
    `openclaw-main/src/infra/local-file-access.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `file-access-runtime` and receive safe file URL conversion, basename
    extraction, root-bounded writes, and root-bounded reads through scoped and
    unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `22e4455d`
  - Weight: 1
  - Last verified: 2026-05-06, focused file-access-runtime proof
    (`1 passed`), adjacent helper proof (`3 passed, 935 deselected`),
    adjacent imported-plugin/runtime proof (`135 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WN` Imported cron-store-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/cron-store-runtime.ts`,
    `openclaw-main/src/cron/store.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `cron-store-runtime` and receive cron store path resolution,
    missing-store loading, split config/state persistence, and state
    merge-on-load helpers through scoped/unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ded083a8`
  - Weight: 1
  - Last verified: 2026-05-06, focused cron-store-runtime proof
    (`1 passed`), adjacent helper proof (`3 passed, 934 deselected`),
    adjacent imported-plugin/runtime proof (`134 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WM` Imported secret-input-schema helper shim
  - Source: `openclaw-main/src/plugin-sdk/secret-input-schema.ts`,
    `openclaw-main/src/plugin-sdk/secret-input.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `secret-input-schema` and receive the exact shared SecretInput schema
    builder through scoped/unscoped aliases; the `secret-input` barrel also
    exposes optional and array schema helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7935af8b`
  - Weight: 1
  - Last verified: 2026-05-06, focused secret-input-schema proof
    (`1 passed`), adjacent helper proof (`6 passed, 930 deselected`),
    adjacent imported-plugin/runtime proof (`133 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WL` Imported secret-input-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/secret-input-runtime.ts`,
    `openclaw-main/src/config/types.secrets.ts`,
    `openclaw-main/src/gateway/resolve-configured-secret-input-string.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `secret-input-runtime` and receive the exact SecretInput runtime helper
    barrel with configured env-backed SecretRef resolution, fallback
    projection, required SecretRef resolution, and scoped/unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a3b36775`
  - Weight: 1
  - Last verified: 2026-05-06, focused secret-input-runtime proof
    (`1 passed`), adjacent helper proof (`5 passed, 930 deselected`),
    adjacent imported-plugin/runtime proof (`132 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WK` Imported secret-ref-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/secret-ref-runtime.ts`,
    `openclaw-main/src/config/types.secrets.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `secret-ref-runtime` and receive the narrow `coerceSecretRef` helper
    through scoped and unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `8b9f3671`
  - Weight: 1
  - Last verified: 2026-05-06, focused secret-ref-runtime proof
    (`1 passed`), adjacent helper proof (`4 passed, 930 deselected`),
    adjacent imported-plugin/runtime proof (`131 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WJ` Imported secret-file-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/secret-file-runtime.ts`,
    `openclaw-main/src/infra/secret-file.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `secret-file-runtime` and receive secret-file constants, sync readers,
    try-read behavior, and async private atomic writes through scoped and
    unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `fe13141a`
  - Weight: 1
  - Last verified: 2026-05-06, focused secret-file-runtime proof
    (`1 passed`), adjacent helper proof (`4 passed, 929 deselected`),
    adjacent imported-plugin/runtime proof (`130 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WI` Imported channel-secret-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-secret-runtime.ts`
  - References: `openclaw-main/src/plugin-sdk/channel-secret-basic-runtime.ts`,
    `openclaw-main/src/plugin-sdk/channel-secret-tts-runtime.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `channel-secret-runtime` and receive the combined channel secret helper
    barrel through scoped and unscoped aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d192b523`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-secret-runtime proof
    (`1 passed`), adjacent helper proof (`4 passed, 928 deselected`),
    adjacent imported-plugin/runtime proof (`129 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WH` Imported channel-secret-basic-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-secret-basic-runtime.ts`,
    `openclaw-main/src/secrets/channel-secret-basic-runtime.ts`,
    `openclaw-main/src/secrets/runtime-shared.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `channel-secret-basic-runtime` and receive channel/account surface helpers,
    simple/conditional/nested field assignment collectors, SecretRef
    assignment collection, and warning helpers through scoped and unscoped
    aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `b2735360`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-secret-basic-runtime proof
    (`1 passed`), adjacent helper proof (`4 passed, 927 deselected`),
    adjacent imported-plugin/runtime proof (`128 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WG` Imported inbound-envelope helper shim
  - Source: `openclaw-main/src/plugin-sdk/inbound-envelope.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `inbound-envelope`
    and receive only route/envelope builder helpers through scoped and
    unscoped aliases, preserving direct, route-first, and runtime-backed
    envelope construction.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d5ba314d`
  - Weight: 1
  - Last verified: 2026-05-06, focused inbound-envelope proof (`1 passed`),
    adjacent helper proof (`3 passed, 927 deselected`), adjacent
    imported-plugin/runtime proof (`127 passed, 803 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001WF` Imported channel-activity-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-activity-runtime.ts`,
    `openclaw-main/src/infra/channel-activity.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `channel-activity-runtime` and receive only `recordChannelActivity` through
    scoped and unscoped aliases, preserving no-return activity recording.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `89483357`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-activity-runtime proof
    (`1 passed`), adjacent helper proof (`3 passed, 926 deselected`),
    adjacent imported-plugin/runtime proof (`126 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WE` Imported channel-runtime-context helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-runtime-context.ts`,
    `openclaw-main/src/infra/channel-runtime-context.ts`
  - References: `openclaw-main/src/infra/channel-runtime-context.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `channel-runtime-context` and receive only register/get/watch runtime
    context helpers through scoped and unscoped aliases, preserving inert
    no-runtime behavior and fakeable runtime registry forwarding.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ced07255`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-runtime-context proof
    (`1 passed`), adjacent helper proof (`3 passed, 925 deselected`),
    adjacent imported-plugin/runtime proof (`125 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WD` Imported channel-mention-gating helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-mention-gating.ts`
  - References: `openclaw-main/src/channels/mention-gating.ts`,
    `openclaw-main/src/auto-reply/reply/mentions.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `channel-mention-gating` and receive only mention marker, mention
    regex/text utilities, and mention decision helpers through scoped and
    unscoped aliases, preserving legacy and bypass decisions.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `22e17bc5`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-mention-gating proof
    (`1 passed`), adjacent helper proof (`3 passed, 924 deselected`),
    adjacent imported-plugin/runtime proof (`124 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001WC` Imported channel-envelope helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-envelope.ts`,
    `openclaw-main/src/auto-reply/envelope.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `channel-envelope`
    and receive only inbound envelope formatting and envelope option helpers
    through scoped and unscoped aliases, preserving group/direct/self-DM
    formatting and timestamp option resolution.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `782e2591`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-envelope proof (`1 passed`),
    adjacent helper proof (`3 passed, 923 deselected`), adjacent
    imported-plugin/runtime proof (`123 passed, 803 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001WB` Imported channel-streaming helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-streaming.ts`
  - References: `openclaw-main/src/config/types.base.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `channel-streaming`
    and receive streaming config object extraction, chunk-mode resolution,
    block-streaming enablement/coalescing, preview chunk config, preview
    tool-progress defaults, native transport flags, and preview stream-mode
    normalization through scoped, unscoped, and generic SDK aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `9a9a6858`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-streaming proof (`1 passed`),
    adjacent helper proof (`3 passed, 922 deselected`), adjacent
    imported-plugin/runtime proof (`122 passed, 803 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001WA` Imported channel-targets helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-targets.ts`,
    `openclaw-main/src/channels/targets.ts`,
    `openclaw-main/src/channels/channel-config.ts`,
    `openclaw-main/src/channels/plugins/chat-target-prefixes.ts`,
    `openclaw-main/src/channels/plugins/target-resolvers.ts`
  - References: `openclaw-main/src/channels/targets.test.ts`,
    `openclaw-main/src/channels/plugins/target-resolvers.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `channel-targets`
    and receive channel entry matching, nested allowlist decisions, messaging
    target parsing, service-prefixed chat/allow target parsing, allowed sender
    matching, channel id/slug normalization, unresolved target fallback rows,
    and optional-token target resolution through scoped, unscoped, and generic
    SDK aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `27bb6438`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-targets proof (`1 passed`),
    adjacent helper proof (`3 passed, 921 deselected`), adjacent
    imported-plugin/runtime proof (`121 passed, 803 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001VZ` Imported channel-contract-testing helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-contract-testing.ts`,
    `openclaw-main/src/plugin-sdk/channel-contract.ts`,
    `openclaw-main/src/channels/plugins/contracts/test-helpers.ts`,
    `openclaw-main/src/channels/plugins/contracts/inbound-testkit.ts`,
    `openclaw-main/src/channels/plugins/contracts/outbound-payload-testkit.ts`
  - References: `openclaw-main/src/plugin-sdk/channel-contract-testing.test.ts`,
    `openclaw-main/src/channels/plugins/contracts/outbound-payload.contract.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `channel-contract-testing` and receive inbound context contract assertions,
    turn dispatch visible/final/count assertions, outbound send mock priming,
    inbound capture mock wiring, and the outbound payload contract-suite
    entrypoint through scoped, unscoped, and generic SDK aliases. The pure
    type-only `channel-contract` barrel resolves to an empty runtime object.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2fdb744c`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-contract-testing proof
    (`1 passed`), adjacent helper proof (`3 passed, 920 deselected`),
    adjacent imported-plugin/runtime proof (`120 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VY` Imported channel-core helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-core.ts`,
    `openclaw-main/src/plugin-sdk/core.ts`,
    `openclaw-main/src/infra/secret-file.ts`,
    `openclaw-main/src/routing/session-key.ts`
  - References: `openclaw-main/extensions/discord/index.ts`,
    `openclaw-main/extensions/telegram/index.ts`,
    `openclaw-main/extensions/googlechat/src/gateway.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `channel-core` and
    receive channel plugin base builders, chat-channel composition,
    channel/setup entry registration, outbound session route builders,
    thread-aware route recovery, target-prefix parsing, optional delimited
    entries, channel config schema construction, account config cleanup, and
    best-effort secret-file reads through scoped, unscoped, and generic SDK
    aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `20c12150`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-core proof (`1 passed`),
    adjacent helper proof (`3 passed, 919 deselected`), adjacent
    imported-plugin/runtime proof (`119 passed, 803 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001VX` Imported channel-lifecycle helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-lifecycle.ts`,
    `openclaw-main/src/plugin-sdk/channel-lifecycle.core.ts`,
    `openclaw-main/src/channels/draft-preview-finalizer.ts`,
    `openclaw-main/src/channels/draft-stream-controls.ts`,
    `openclaw-main/src/channels/draft-stream-loop.ts`,
    `openclaw-main/src/channels/run-state-machine.ts`,
    `openclaw-main/src/channels/transport/stall-watchdog.ts`
  - References: `openclaw-main/extensions/discord/src/draft-stream.ts`,
    `openclaw-main/extensions/matrix/src/matrix/monitor/index.ts`,
    `openclaw-main/extensions/googlechat/src/gateway.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `channel-lifecycle` and receive account status sinks, abort/passive/server
    lifecycle waiters, run-state and keyed run queues, finalizable draft stream
    controls, preview finalization helpers, and armable stall watchdogs through
    scoped, unscoped, and generic SDK aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d3bc5720`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-lifecycle proof
    (`1 passed`), adjacent helper proof (`3 passed, 918 deselected`),
    adjacent imported-plugin/runtime proof (`118 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VW` Imported channel-config-writes alias shim
  - Source: `openclaw-main/src/plugin-sdk/channel-config-writes.ts`
  - References: `openclaw-main/src/plugin-sdk/channel-config-helpers.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `channel-config-writes` barrel and receive config-write policy helpers
    through scoped and unscoped SDK aliases without falling back to the broad
    root SDK object.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7b668b3c`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-config-writes proof
    (`1 passed`), adjacent helper proof (`3 passed, 917 deselected`),
    adjacent imported-plugin/runtime proof (`117 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VV` Imported channel-config-helpers helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-config-helpers.ts`,
    `openclaw-main/src/channels/plugins/dm-access.ts`,
    `openclaw-main/src/channels/plugins/config-write-policy-shared.ts`,
    `openclaw-main/src/channels/plugins/config-helpers.ts`,
    `openclaw-main/src/channels/plugins/helpers.ts`
  - References: `openclaw-main/extensions/telegram/index.ts`,
    `openclaw-main/extensions/discord/index.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `channel-config-helpers` and receive DM access normalization/migration
    helpers, config-write authorization helpers, allowFrom/default-target
    accessors, scoped/top-level/hybrid channel config adapters, and
    account-scoped DM security resolver helpers through scoped, unscoped, and
    generic SDK aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `02ec0b78`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel-config-helpers proof
    (`1 passed`), adjacent helper proof (`3 passed, 916 deselected`),
    adjacent imported-plugin/runtime proof (`116 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VU` Imported runtime-env helper shim
  - Source: `openclaw-main/src/plugin-sdk/runtime-env.ts`,
    `openclaw-main/src/runtime.ts`, `openclaw-main/src/globals.ts`,
    `openclaw-main/src/infra/env.ts`, `openclaw-main/src/logging.ts`,
    `openclaw-main/src/infra/retry.ts`,
    `openclaw-main/src/infra/backoff.ts`,
    `openclaw-main/src/utils/with-timeout.ts`,
    `openclaw-main/src/infra/abort-signal.ts`,
    `openclaw-main/src/infra/format-time/format-duration.ts`
  - References: `openclaw-main/src/infra/net/undici-global-dispatcher.ts`,
    `openclaw-main/src/infra/unhandled-rejections.ts`,
    `openclaw-main/src/infra/wsl.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require `runtime-env` and
    receive runtime IO, verbose/yes flags, sleep/timeout/retry, truthy env
    parsing, duration/backoff helpers, abort waiters, handler registration,
    subsystem logging facades, undici proxy bootstrap posture, and WSL
    detection through scoped and unscoped SDK aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4e364149`
  - Weight: 1
  - Last verified: 2026-05-06, focused runtime-env proof (`1 passed`),
    adjacent runtime proof (`4 passed, 914 deselected`), adjacent
    imported-plugin/runtime proof (`115 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001VT` Imported channel config primitives/schema helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-config-primitives.ts`,
    `openclaw-main/src/plugin-sdk/channel-config-schema.ts`,
    `openclaw-main/src/plugin-sdk/bundled-channel-config-schema.ts`,
    `openclaw-main/src/channels/plugins/config-schema.ts`,
    `openclaw-main/src/config/zod-schema.core.ts`,
    `openclaw-main/src/config/zod-schema.agent-runtime.ts`
  - References: `openclaw-main/src/plugin-sdk/channel-config-schema-legacy.ts`,
    `openclaw-main/src/config/zod-schema.providers-core.ts`,
    `openclaw-main/src/config/zod-schema.providers-whatsapp.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow channel
    config SDK barrels and receive DM/group policy schemas, context visibility
    and tool policy schemas, markdown/block-streaming schemas, nested DM config
    and catchall multi-account builders, `requireOpenAllowFrom`, and bundled
    provider schema handles through scoped and unscoped SDK aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7f046836`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel config primitives proof
    (`1 passed`), adjacent helper proof (`3 passed, 914 deselected`),
    adjacent imported-plugin/runtime proof (`114 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VS` Imported channel entry contract helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-entry-contract.ts`
  - References: `openclaw-main/extensions/telegram/index.ts`,
    `openclaw-main/extensions/discord/index.ts`,
    `openclaw-main/src/plugin-sdk/channel-entry-contract.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `channel-entry-contract`, define bundled channel/setup entries, load
    CommonJS sidecar exports relative to the entry import URL, preserve default
    empty channel config schema behavior, run registration-mode branches, and
    set channel runtimes through scoped, unscoped, and generic SDK aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `e0bb22bf`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel entry contract proof
    (`1 passed`), adjacent helper proof (`3 passed, 913 deselected`),
    adjacent imported-plugin/runtime proof (`113 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VR` Imported channel plugin common/core helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-plugin-common.ts`,
    `openclaw-main/src/plugin-sdk/core.ts`,
    `openclaw-main/src/channels/chat-meta.ts`,
    `openclaw-main/src/plugins/config-schema.ts`
  - References: `openclaw-main/src/channels/plugins/setup-helpers.ts`,
    `openclaw-main/src/channels/plugins/config-helpers.ts`,
    `openclaw-main/src/channels/plugins/config-schema.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `channel-plugin-common` barrel and `core`, receiving the channel prelude,
    empty config schema helpers, channel metadata, account config mutation
    helpers, pairing approval text, and `createChannelPluginBase` through
    scoped, unscoped, and generic SDK aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `b669ff0b`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel plugin common/core proof
    (`1 passed`), adjacent helper proof (`3 passed, 912 deselected`),
    adjacent imported-plugin/runtime proof (`112 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VQ` Imported GitHub Copilot token helper shim
  - Source: `openclaw-main/src/plugin-sdk/github-copilot-token.ts`,
    `openclaw-main/src/agents/github-copilot-token.ts`,
    `openclaw-main/src/plugin-sdk/provider-auth.ts`
  - References: `openclaw-main/extensions/github-copilot/index.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `github-copilot-token` barrel and derive Copilot API base URLs from valid
    proxy-token hints, reuse cached tokens, save fetched token metadata, and
    reach the helper through scoped and unscoped SDK aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `8ccd0928`
  - Weight: 1
  - Last verified: 2026-05-06, focused GitHub Copilot token proof
    (`1 passed`), adjacent helper proof (`5 passed, 909 deselected`),
    adjacent imported-plugin/runtime proof (`111 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VP` Imported talk config runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/talk-config-runtime.ts`,
    `openclaw-main/src/config/talk.ts`
  - References: `openclaw-main/extensions/talk-voice/index.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `talk-config-runtime` barrel and resolve the active talk provider from
    normalized provider maps, preserving string/SecretRef API keys, explicit
    provider validation, and single-provider fallback.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ef516298`
  - Weight: 1
  - Last verified: 2026-05-06, focused talk config runtime proof
    (`1 passed`), adjacent helper proof (`5 passed, 908 deselected`),
    adjacent imported-plugin/runtime proof (`110 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VO` Imported channel secret TTS runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-secret-tts-runtime.ts`,
    `openclaw-main/src/secrets/channel-secret-tts-runtime.ts`
  - References: `openclaw-main/extensions/discord/src/secret-config-contract.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `channel-secret-tts-runtime` barrel and collect nested voice TTS provider
    API-key SecretRef assignments for top-level and account-scoped channel
    surfaces, including inactive warnings and assignment apply callbacks.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `59936359`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel secret TTS runtime proof
    (`1 passed`), adjacent helper proof (`3 passed, 909 deselected`),
    adjacent imported-plugin/runtime proof (`109 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VN` Imported setup adapter runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/setup-adapter-runtime.ts`,
    `openclaw-main/src/channels/plugins/setup-helpers.ts`
  - References: `openclaw-main/extensions/discord/src/setup-adapter.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `setup-adapter-runtime` barrel and create env-aware account setup adapters
    that validate env/default-account use, normalize account ids, migrate base
    names, and patch top-level or account-scoped channel config.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `c0f33006`
  - Weight: 1
  - Last verified: 2026-05-06, focused setup adapter runtime proof
    (`1 passed`), adjacent helper proof (`3 passed, 908 deselected`),
    adjacent imported-plugin/runtime proof (`108 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VM` Imported state paths helper shim
  - Source: `openclaw-main/src/plugin-sdk/state-paths.ts`,
    `openclaw-main/src/config/paths.ts`,
    `openclaw-main/src/infra/home-dir.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `state-paths` barrel and resolve OpenClaw home, state, and OAuth paths
    through scoped, unscoped, and broad SDK paths.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `8c3128bf`
  - Weight: 1
  - Last verified: 2026-05-06, focused state paths proof (`1 passed`),
    adjacent helper proof (`4 passed, 906 deselected`), adjacent
    imported-plugin/runtime proof (`107 passed, 803 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001VL` Imported channel location helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-location.ts`,
    `openclaw-main/src/channels/location.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `channel-location` barrel and format normalized location text/context
    through scoped, unscoped, and broad SDK paths.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ad24fdc2`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel location proof (`1 passed`),
    adjacent helper proof (`4 passed, 905 deselected`), adjacent
    imported-plugin/runtime proof (`106 passed, 803 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001VK` Imported channel inbound roots helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-inbound-roots.ts`,
    `openclaw-main/src/media/inbound-path-policy.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `channel-inbound-roots` barrel and merge/dedupe valid wildcard media roots
    through scoped, unscoped, and broad SDK paths.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `1e1d6c23`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel inbound roots proof
    (`1 passed`), adjacent helper proof (`3 passed, 905 deselected`),
    adjacent imported-plugin/runtime proof (`105 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VJ` Imported channel pairing paths helper shim
  - Source: `openclaw-main/src/plugin-sdk/channel-pairing-paths.ts`,
    `openclaw-main/src/pairing/allow-from-store-read.ts`
  - References: `openclaw-main/src/pairing/allow-from-store-file.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `channel-pairing-paths` barrel and resolve sanitized legacy/account
    allow-from file paths through scoped, unscoped, and broad SDK paths.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `fa95764e`
  - Weight: 1
  - Last verified: 2026-05-06, focused channel pairing paths proof
    (`1 passed`), adjacent helper proof (`2 passed, 905 deselected`),
    adjacent imported-plugin/runtime proof (`104 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VI` Imported XAI model-id helper shim
  - Source: `openclaw-main/src/plugin-sdk/xai-model-id.ts`,
    `openclaw-main/src/plugin-sdk/provider-model-shared.ts`
  - References: `openclaw-main/src/plugin-sdk/provider-model-id-normalize.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `xai-model-id` barrel, receive `normalizeXaiModelId`, and normalize stale
    Grok fast/reasoning plus 4.20 beta IDs through scoped, unscoped, and broad
    SDK paths.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `6743ca28`
  - Weight: 1
  - Last verified: 2026-05-06, focused XAI model-id proof (`1 passed`),
    adjacent helper proof (`2 passed, 904 deselected`), adjacent
    imported-plugin/runtime proof (`103 passed, 803 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001VH` Imported Anthropic Vertex facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/anthropic-vertex.ts`,
    `openclaw-main/extensions/anthropic-vertex/api.ts`,
    `openclaw-main/extensions/anthropic-vertex/region.ts`,
    `openclaw-main/extensions/anthropic-vertex/provider-catalog.ts`
  - References: `openclaw-main/extensions/anthropic-vertex/region.test.ts`,
    `openclaw-main/extensions/anthropic-vertex/index.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `anthropic-vertex` facade, resolve regional/global Vertex endpoint regions
    before env fallback, validate env regions, and resolve project IDs from
    Anthropic/GCP env vars plus ADC `project_id`/`quota_project_id`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0ea37843`
  - Weight: 1
  - Last verified: 2026-05-06, focused Anthropic Vertex facade proof
    (`1 passed`), adjacent helper proof (`2 passed, 903 deselected`),
    adjacent imported-plugin/runtime proof (`102 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VG` Imported Anthropic Vertex auth-presence helper shim
  - Source: `openclaw-main/src/plugin-sdk/anthropic-vertex-auth-presence.ts`
  - References: `openclaw-main/src/plugin-sdk/anthropic-vertex-auth-presence.test.ts`,
    `openclaw-main/src/plugin-sdk/anthropic-vertex-auth-presence.preflight.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `anthropic-vertex-auth-presence` barrel, detect explicit metadata server
    opt-in, trim explicit ADC credential paths without stripping Unicode, and
    read the ADC file directly without an existence preflight.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `f7c9e174`
  - Weight: 1
  - Last verified: 2026-05-05, focused Anthropic Vertex auth-presence proof
    (`1 passed`), adjacent helper proof (`4 passed, 900 deselected`),
    adjacent imported-plugin/runtime proof (`101 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VF` Imported Anthropic CLI facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/anthropic-cli.ts`,
    `openclaw-main/extensions/anthropic/cli-shared.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `anthropic-cli` barrel, receive `CLAUDE_CLI_BACKEND_ID`, and use the same
    trimmed/case-insensitive Claude CLI provider predicate through scoped and
    unscoped SDK aliases.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `8289eaff`
  - Weight: 1
  - Last verified: 2026-05-05, focused Anthropic CLI proof (`1 passed`),
    adjacent helper proof (`4 passed, 899 deselected`), adjacent
    imported-plugin/runtime proof (`100 passed, 803 deselected`), `ruff
    check`, and `mypy`.

- [x] `OZ-PLUGIN-001VE` Imported ACP binding resolve helper shim
  - Source: `openclaw-main/src/plugin-sdk/acp-binding-resolve-runtime.ts`,
    `openclaw-main/src/acp/persistent-bindings.resolve.ts`,
    `openclaw-main/src/acp/persistent-bindings.types.ts`,
    `openclaw-main/src/channels/plugins/configured-binding-registry.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `acp-binding-resolve-runtime` barrel, resolve top-level typed ACP bindings
    with exact-account preference and parent conversation fallback, and
    materialize OpenClaw-shaped `spec` plus session binding record metadata
    with deterministic ACP binding session keys.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `4c9ed6d6`
  - Weight: 1
  - Last verified: 2026-05-05, focused ACP binding resolve proof (`1
    passed`), adjacent helper proof (`7 passed, 895 deselected`), adjacent
    imported-plugin/runtime proof (`99 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001VD` Imported agent-config-primitives helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-config-primitives.ts`,
    `openclaw-main/src/config/zod-schema.core.ts`,
    `openclaw-main/src/config/zod-schema.agent-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    `agent-config-primitives` barrel, receive the exact
    `ReplyRuntimeConfigSchemaShape` and `ToolPolicySchema` export surface,
    parse optional reply runtime config primitive fields, and preserve the
    OpenClaw tool-policy conflict guard for `allow` plus `alsoAllow`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `99bb3098`
  - Weight: 1
  - Last verified: 2026-05-05, focused agent-config-primitives proof (`1
    passed`), adjacent helper proof (`6 passed, 895 deselected`), adjacent
    imported-plugin/runtime proof (`98 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001VC` Imported agent-media-payload helper shim
  - Source: `openclaw-main/src/plugin-sdk/agent-media-payload.ts`,
    `openclaw-main/src/media/local-roots.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the
    `agent-media-payload` barrel, build legacy agent media payload fields from
    outbound media descriptors, and resolve agent-scoped local media roots
    across config/state media directories, canvas/workspace/sandbox roots,
    preferred temp root, and configured agent workspace.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `21126502`
  - Weight: 1
  - Last verified: 2026-05-05, focused agent-media-payload proof (`1
    passed`), adjacent helper proof (`8 passed, 892 deselected`), adjacent
    imported-plugin/runtime proof (`97 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001VB` Imported account-id/configured-id subpath shim
  - Source: `openclaw-main/src/plugin-sdk/account-id.ts`,
    `openclaw-main/src/routing/account-id.ts`,
    `openclaw-main/src/plugin-sdk/account-configured-ids.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the slim
    `account-id` and `account-configured-ids` barrels, receive only the narrow
    upstream exports, normalize required/optional account ids, and list
    normalized configured account ids without falling through to the generic
    SDK surface.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `2e012bc2`
  - Weight: 1
  - Last verified: 2026-05-05, focused account-id/configured-id subpath proof
    (`1 passed`), adjacent helper proof (`12 passed, 887 deselected`),
    adjacent imported-plugin/runtime proof (`96 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001VA` Imported session-store-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/session-store-runtime.ts`,
    `openclaw-main/src/config/sessions/store-entry.ts`,
    `openclaw-main/src/config/sessions/paths.ts`,
    `openclaw-main/src/config/sessions/session-key.ts`,
    `openclaw-main/src/config/sessions/group.ts`,
    `openclaw-main/src/config/sessions/main-session.ts`,
    `openclaw-main/src/config/sessions/store.ts`,
    `openclaw-main/src/config/sessions/reset.ts`
  - References: `openclaw-main/src/config/sessions/store-entry.ts`,
    `openclaw-main/src/config/sessions/reset-policy.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    session-store runtime barrel, resolve normalized store entries and legacy
    keys, compute agent-scoped store paths, resolve group/direct/explicit/main
    session keys, load/save/update file-backed stores, record inbound metadata,
    update last-route delivery context, and evaluate reset freshness helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `06e04786`
  - Weight: 1
  - Last verified: 2026-05-05, focused session-store-runtime proof (`1
    passed`), adjacent helper proof (`35 passed, 863 deselected`), adjacent
    imported-plugin/runtime proof (`95 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001UZ` Imported session-binding/session-key runtime alias shim
  - Source: `openclaw-main/src/plugin-sdk/session-binding-runtime.ts`,
    `openclaw-main/src/plugin-sdk/thread-bindings-session-runtime.ts`,
    `openclaw-main/src/plugin-sdk/session-key-runtime.ts`
  - References: `openclaw-main/src/infra/outbound/session-binding-service.test.ts`,
    `openclaw-main/src/channels/plugins/binding-routing.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the narrow
    session-binding, thread-bindings-session, and session-key runtime barrels,
    reset/inspect session binding adapters for tests, bind/list/resolve records
    through the service, reuse thread binding lifecycle/farewell helpers, and
    resolve agent ids from session keys.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0307ca2f`
  - Weight: 1
  - Last verified: 2026-05-05, focused session-binding/session-key proof (`1
    passed`), adjacent helper proof (`34 passed, 863 deselected`), adjacent
    imported-plugin/runtime proof (`94 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001UY` Imported conversation-binding-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/conversation-binding-runtime.ts`,
    `openclaw-main/src/channels/plugins/binding-routing.ts`,
    `openclaw-main/src/infra/outbound/session-binding-service.ts`,
    `openclaw-main/src/plugins/conversation-binding.ts`,
    `openclaw-main/src/pairing/pairing-messages.ts`
  - References: `openclaw-main/src/channels/plugins/binding-routing.test.ts`,
    `openclaw-main/src/infra/outbound/session-binding-service.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/conversation-binding-runtime`, obtain the session
    binding service, bind/list/resolve/touch/unbind through registered
    adapters, route runtime conversation bindings to bound sessions while
    preserving plugin-owned routes, project configured binding routes, check
    binding readiness, detect plugin-owned records, and render pairing replies.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `230ec9d2`
  - Weight: 1
  - Last verified: 2026-05-05, focused conversation-binding-runtime proof (`1
    passed`), adjacent helper proof (`33 passed, 863 deselected`), adjacent
    imported-plugin/runtime proof (`93 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001UX` Imported outbound-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/outbound-runtime.ts`,
    `openclaw-main/src/channels/plugins/runtime-forwarders.ts`,
    `openclaw-main/src/infra/outbound/send-deps.ts`,
    `openclaw-main/src/infra/outbound/identity.ts`,
    `openclaw-main/src/infra/outbound/reply-policy.ts`,
    `openclaw-main/src/infra/outbound/sanitize-text.ts`,
    `openclaw-main/src/infra/outbound/session-context.ts`,
    `openclaw-main/src/infra/outbound/payloads.ts`,
    `openclaw-main/src/infra/outbound/deliver.ts`
  - References: `openclaw-main/src/plugin-sdk/thread-aware-outbound-session-route.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/outbound-runtime`, create fakeable outbound delegates,
    resolve dynamic and legacy channel send dependencies, normalize outbound
    identity and session context, sanitize plain-text output, plan/project
    outbound payloads, and deliver through a native fakeable dependency entry
    point.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a0df1bba`
  - Weight: 1
  - Last verified: 2026-05-05, focused outbound-runtime proof (`1 passed`),
    adjacent helper proof (`32 passed, 863 deselected`), adjacent
    imported-plugin/runtime proof (`92 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001UW` Imported conversation-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/conversation-runtime.ts`,
    `openclaw-main/src/channels/conversation-label.ts`,
    `openclaw-main/src/channels/session.ts`,
    `openclaw-main/src/channels/session-meta.ts`
  - References: `openclaw-main/src/channels/conversation-label.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/conversation-runtime`, resolve OpenClaw conversation
    labels, expose safe inbound recording helpers with meta-task tracking and
    pinned main-DM route skip behavior, and reuse thread-binding helpers
    through the conversation facade.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7c5271ba`
  - Weight: 1
  - Last verified: 2026-05-05, focused conversation-runtime proof
    (`1 passed`), adjacent helper proof (`31 passed, 863 deselected`),
    adjacent imported-plugin/runtime proof (`91 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UV` Imported thread-bindings-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/thread-bindings-runtime.ts`,
    `openclaw-main/src/channels/thread-binding-id.ts`,
    `openclaw-main/src/channels/thread-bindings-messages.ts`,
    `openclaw-main/src/channels/thread-bindings-policy.ts`,
    `openclaw-main/src/shared/thread-binding-lifecycle.ts`,
    `openclaw-main/src/infra/outbound/account-scoped-conversation-bindings.ts`
  - References: `openclaw-main/src/channels/thread-binding-id.test.ts`,
    `openclaw-main/src/channels/thread-bindings-policy.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/thread-bindings-runtime`, resolve account-prefixed
    binding IDs, channel/account timeout settings, lifecycle expirations,
    farewell text, and account-scoped in-memory conversation binding managers
    with bind/touch/list/unbind/stop behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `06f36c6c`
  - Weight: 1
  - Last verified: 2026-05-05, focused thread-bindings-runtime proof
    (`1 passed`), adjacent helper proof (`30 passed, 863 deselected`),
    adjacent imported-plugin/runtime proof (`90 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UU` Imported directory-config-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/directory-config-runtime.ts`
  - References:
    `openclaw-main/src/channels/plugins/directory-config-helpers.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/directory-config-runtime`, use query/limit filtering,
    directory entry projection, inspected/resolved account listers, and
    user/group listing through the slim config-backed facade without exposing
    broader adapter-only `directory-runtime` exports.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `335e215d`
  - Weight: 1
  - Last verified: 2026-05-05, focused directory-config-runtime proof
    (`1 passed`), adjacent helper proof (`29 passed, 863 deselected`),
    adjacent imported-plugin/runtime proof (`89 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UT` Imported directory-runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/directory-runtime.ts`,
    `openclaw-main/src/channels/plugins/directory-adapters.ts`,
    `openclaw-main/src/channels/plugins/directory-config-helpers.ts`,
    `openclaw-main/src/channels/plugins/runtime-forwarders.ts`
  - References:
    `openclaw-main/src/channels/plugins/directory-adapters.test.ts`,
    `openclaw-main/src/channels/plugins/directory-config-helpers.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/directory-runtime`, create default/empty directory
    adapters, list user/group directory entries from allowlists, map keys,
    inspected/resolved accounts, and source iterables, apply query/limit
    filtering, forward live directory methods through runtime adapters, preserve
    unavailable-method errors, and reach helpers through the generic SDK during
    `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a354299e`
  - Weight: 1
  - Last verified: 2026-05-05, focused directory-runtime proof (`1 passed`),
    adjacent helper proof (`28 passed, 863 deselected`), adjacent
    imported-plugin/runtime proof (`88 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001US` Imported runtime helper shim
  - Source: `openclaw-main/src/plugin-sdk/runtime.ts`,
    `openclaw-main/src/plugin-sdk/runtime-logger.ts`,
    `openclaw-main/src/runtime.ts`
  - References: `openclaw-main/src/plugins/contracts/plugin-sdk-subpaths.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/runtime` and `openclaw/plugin-sdk/runtime-logger`,
    create logger-backed runtimes, format logger output, write stdout/JSON
    through logger adapters, reuse supplied runtime objects, synthesize runtime
    envs with custom exit errors, return unavailable-exit errors, and reach the
    logger helper through the generic SDK during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `5bd1435b`
  - Weight: 1
  - Last verified: 2026-05-05, focused runtime proof (`1 passed`), adjacent
    helper proof (`27 passed, 863 deselected`), adjacent imported-plugin/runtime
    proof (`87 passed, 803 deselected`), `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UR` Imported runtime-store helper shim
  - Source: `openclaw-main/src/plugin-sdk/runtime-store.ts`
  - References: `openclaw-main/src/plugin-sdk/runtime-store.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/runtime-store`, create isolated legacy stores, shared
    plugin-id stores, shared custom-key stores, preserve falsy initialized
    runtime values, reject empty plugin IDs, and reach the same helper through
    the generic SDK during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `57cc0f37`
  - Weight: 1
  - Last verified: 2026-05-05, focused runtime-store proof (`1 passed`),
    adjacent helper proof (`9 passed, 880 deselected`), adjacent
    imported-plugin/runtime proof (`86 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001UQ` Imported device-bootstrap helper shim
  - Source: `openclaw-main/src/plugin-sdk/device-bootstrap.ts`,
    `openclaw-main/src/shared/device-bootstrap-profile.ts`,
    `openclaw-main/src/infra/device-bootstrap.ts`,
    `openclaw-main/src/infra/device-pairing.ts`
  - References: `openclaw-main/src/infra/device-bootstrap.test.ts`,
    `openclaw-main/src/infra/device-pairing.test.ts`,
    `openclaw-main/src/plugins/contracts/plugin-sdk-subpaths.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/device-bootstrap`, read the setup bootstrap profile,
    normalize bootstrap profile roles/scopes, issue/revoke/clear fakeable
    bootstrap tokens, observe the native no-pairing list/approve boundary, and
    reach the same helpers through the generic SDK during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `ae2fc79f`
  - Weight: 1
  - Last verified: 2026-05-05, focused device-bootstrap proof (`1 passed`),
    adjacent provider/helper proof (`8 passed, 880 deselected`), adjacent
    imported-plugin/runtime proof (`85 passed, 803 deselected`), `ruff check`,
    and `mypy`.

- [x] `OZ-PLUGIN-001UP` Imported provider web facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-web-search.ts`,
    `openclaw-main/src/plugin-sdk/provider-web-fetch.ts`,
    `openclaw-main/src/agents/tools/web-search-provider-common.ts`,
    `openclaw-main/src/agents/tools/web-shared.ts`,
    `openclaw-main/src/agents/tools/web-fetch-utils.ts`,
    `openclaw-main/src/security/external-content.ts`
  - References: `openclaw-main/src/plugins/contracts/plugin-sdk-subpaths.test.ts`,
    `openclaw-main/src/plugins/contracts/web-search-provider.*.contract.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require
    `openclaw/plugin-sdk/provider-web-search` and
    `openclaw/plugin-sdk/provider-web-fetch`, use common web provider
    parameter/result helpers, markdown/text utilities, cache/timing helpers,
    search filter/date/freshness helpers, web-search cache helpers, endpoint
    wrapper stubs, external-content wrappers, and the deprecated
    plugin-backed web-search provider error boundary through scoped and
    generic SDK aliases during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0ba91657`
  - Weight: 1
  - Last verified: 2026-05-05, focused provider web facade proof
    (`1 passed`), adjacent provider-helper proof (`7 passed, 880 deselected`),
    adjacent imported-plugin/runtime proof (`84 passed, 803 deselected`),
    `ruff check`, and `mypy`.

- [x] `OZ-PLUGIN-001UO` Imported provider web-search contract helper shim
  - Source: `openclaw-main/src/plugin-sdk/provider-web-search-contract-fields.ts`,
    `openclaw-main/src/plugin-sdk/provider-web-search-config-contract.ts`,
    `openclaw-main/src/plugin-sdk/provider-web-search-contract.ts`,
    `openclaw-main/src/agents/tools/web-search-provider-config.ts`
  - References:
    `openclaw-main/src/plugin-sdk/provider-web-search-contract.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: imported OpenClaw runtime tools can require the web-search
    contract fields/config/registration modules, read and write scoped,
    top-level, keyless, and configured web-search credentials, merge scoped
    provider config, apply selection config, and reach the same helpers through
    the generic SDK during `tools.invoke`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `3dadf0fb`
  - Weight: 1
  - Last verified: 2026-05-05, focused web-search provider contract proof
    (`1 passed`), adjacent provider-helper proof (`6 passed, 880 deselected`),
    adjacent imported-plugin/runtime proof (`83 passed, 803 deselected`),
    `ruff check`, and `mypy`.

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

- [x] `OZ-PLUGIN-00261` Imported tool-send helper shim
  - Source: `openclaw-main/src/plugin-sdk/tool-send.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `tool-send` and extract canonical send target fields only when
    the action matches, preserving raw `to`, trimming `accountId`, converting
    numeric `threadId`, and returning `null` for wrong action or missing
    target.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `87450dcc`
  - Weight: 1
  - Last verified: 2026-05-07, focused tool-send proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1080 deselected`), adjacent
    imported-plugin proof (`272 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00262` Imported webhook-ingress helper shim
  - Source: `openclaw-main/src/plugin-sdk/webhook-ingress.ts`,
    `openclaw-main/src/gateway/auth-rate-limit.ts`,
    `openclaw-main/src/infra/ws.ts`,
    `openclaw-main/src/plugins/http-path.ts`, and
    `openclaw-main/src/infra/http-body.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `webhook-ingress` and receive the aggregate webhook path,
    memory-guard, request-guard, target, raw WebSocket data, plugin HTTP path,
    auth rate-limit, and max-body-byte helpers through the native bridge.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `399e784a`
  - Weight: 1
  - Last verified: 2026-05-07, focused webhook-ingress proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1082 deselected`), adjacent
    imported-plugin proof (`273 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00263` Imported web-media helper shim
  - Source: `openclaw-main/src/plugin-sdk/web-media.ts`,
    `openclaw-main/src/media/web-media.ts`,
    `openclaw-main/src/media/local-media-access.ts`,
    `openclaw-main/src/media/local-roots.ts`,
    `openclaw-main/src/media/mime.ts`, and
    `openclaw-main/src/media/constants.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `web-media`, load local/file-URL media under explicit local
    roots, classify image/document MIME and kind metadata, expose default
    local media roots, preserve `LocalMediaAccessError` codes, reject unsafe
    root bypasses, and project image optimization helper failures through the
    native bridge.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `a60b54f2`
  - Weight: 1
  - Last verified: 2026-05-07, focused web-media proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1082 deselected`), adjacent
    imported-plugin proof (`274 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00264` Imported speech facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/speech.ts`,
    `openclaw-main/src/plugin-sdk/speech-core.ts`,
    `openclaw-main/src/tts/openai-compatible-speech-provider.ts`,
    `openclaw-main/src/tts/openai-compatible-speech-provider.test.ts`,
    and `openclaw-main/src/agents/provider-http-errors.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `speech`, receive the provider-facing speech helper surface,
    construct OpenAI-compatible speech providers, normalize provider config,
    parse provider voice/model directives, resolve talk config/overrides,
    list voices, detect env-backed configuration, and synthesize audio through
    the native provider HTTP runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `97ec0d27`
  - Weight: 1
  - Last verified: 2026-05-07, focused speech facade proof (`1 passed`),
    adjacent SDK helper proof (`3 passed, 1084 deselected`), adjacent
    imported-plugin proof (`275 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00265` Imported zalouser compatibility facade shim
  - Source: `openclaw-main/src/plugin-sdk/zalouser.ts`,
    `openclaw-main/src/plugin-sdk/command-auth.ts`, and
    `openclaw-main/src/plugin-sdk/command-auth.test.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `zalouser` and receive only the deprecated compatibility facade
    exports for command authorization, preserving the same function identities
    and `resolveSenderCommandAuthorization*` behavior as `command-auth`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `6f0c70b5`
  - Weight: 1
  - Last verified: 2026-05-07, focused zalouser proof (`1 passed`),
    adjacent command-auth proof (`3 passed, 1085 deselected`), adjacent
    imported-plugin proof (`276 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00266` Imported zod facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/zod.ts`,
    `openclaw-main/extensions/acpx/src/config-schema.ts`, and
    `openclaw-main/extensions/feishu/src/config-schema.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `zod` and receive the bounded schema facade needed by bundled
    extension config schemas: `z`, `ZodError`, `ZodIssueCode`, object/strict
    object, string trim/min/url/startsWith, number int/min/max/positive,
    boolean, enum, literal transforms, union, array, record, unknown, optional,
    default, describe, parse/safeParse, and object `superRefine` issue
    projection.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `c49cbd4a`
  - Weight: 1
  - Last verified: 2026-05-07, focused zod proof (`1 passed`),
    adjacent SDK helper proof (`4 passed, 1085 deselected`), adjacent
    imported-plugin proof (`277 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00267` Imported web-content-extractor facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/web-content-extractor.ts`,
    `openclaw-main/src/agents/tools/web-fetch-utils.ts`, and
    `openclaw-main/src/agents/tools/web-fetch-visibility.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `web-content-extractor` and receive the exact public helper
    facade for `extractBasicHtmlContent`, `htmlToMarkdown`, `markdownToText`,
    `normalizeWhitespace`, `sanitizeHtml`, and `stripInvisibleUnicode`,
    including hidden element removal, invisible Unicode stripping, and
    markdown/text extraction shape.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `563d69d7`
  - Weight: 1
  - Last verified: 2026-05-07, focused web-content-extractor proof (`1
    passed`), adjacent web/provider proof (`3 passed, 1087 deselected`),
    adjacent imported-plugin proof (`278 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00268` Imported plugin-entry facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/plugin-entry.ts`,
    `openclaw-main/src/plugins/config-schema.ts`, and
    `openclaw-main/src/plugin-sdk/lazy-value.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `plugin-entry` and receive `definePluginEntry`,
    `buildPluginConfigSchema`, and `emptyPluginConfigSchema`, preserving lazy
    cached config schema evaluation plus runtime entry metadata fields for
    `kind`, `reload`, node-host commands, security audit collectors, and
    `register`.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `b1fd730f`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-entry proof (`1 passed`),
    adjacent entrypoint/facade proof (`5 passed, 1086 deselected`),
    adjacent imported-plugin proof (`279 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00269` Imported optional-channel-setup facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/optional-channel-setup.ts`,
    `openclaw-main/src/routing/session-key.ts`, and
    `openclaw-main/src/terminal/links.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `optional-channel-setup` and receive exactly
    `createOptionalChannelSetupAdapter` and
    `createOptionalChannelSetupWizard`, preserving default-account resolution,
    unavailable setup messages, docs links, wizard labels/status lines,
    empty credentials, and finalize/apply errors.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `34c792c1`
  - Weight: 1
  - Last verified: 2026-05-07, focused optional-channel-setup proof (`1
    passed`), adjacent setup/channel proof (`5 passed, 1087 deselected`),
    adjacent imported-plugin proof (`280 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00270` Imported outbound-media facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/outbound-media.ts`,
    `openclaw-main/src/media/load-options.ts`, and
    `openclaw-main/src/plugin-sdk/web-media.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `outbound-media` and receive `loadOutboundMediaFromUrl`, with
    shared web-media MIME/kind/fileName projection, explicit local-root
    requirements for host-read media, and the upstream missing-local-roots
    error for bare host read functions.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `49969f8f`
  - Weight: 1
  - Last verified: 2026-05-07, focused outbound-media proof (`1 passed`),
    adjacent media/reply proof (`3 passed, 1090 deselected`), adjacent
    imported-plugin proof (`281 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00271` Imported delivery-queue-runtime facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/delivery-queue-runtime.ts`,
    `openclaw-main/src/infra/outbound/delivery-queue-recovery.ts`, and
    `openclaw-main/src/infra/outbound/deliver-runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `delivery-queue-runtime` and receive `drainPendingDeliveries`,
    with default outbound deliverer injection, explicit deliver preservation,
    queue drain adapter routing, and an honest unavailable error when no
    queue drain runtime is wired.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `183c5a68`
  - Weight: 1
  - Last verified: 2026-05-07, focused delivery-queue-runtime proof (`1
    passed`), adjacent runtime proof (`3 passed, 1091 deselected`), adjacent
    imported-plugin proof (`282 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00272` Imported migration-runtime facade helper shim
  - Source: `openclaw-main/src/plugin-sdk/migration-runtime.ts`,
    `openclaw-main/src/plugin-sdk/migration.ts`, and
    `openclaw-main/src/plugins/types.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `migration-runtime` and receive cached config runtime wrappers,
    copy/archive filesystem helpers, conflict/error shaping, report JSON
    redaction, and Markdown summary output.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7a9c8208`
  - Weight: 1
  - Last verified: 2026-05-07, focused migration-runtime proof (`1 passed`),
    adjacent runtime proof (`3 passed, 1092 deselected`), adjacent
    imported-plugin proof (`283 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00273` Imported migration helper facade shim
  - Source: `openclaw-main/src/plugin-sdk/migration.ts` and
    `openclaw-main/src/plugins/types.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `migration` and receive item constructors, status markers,
    summary counts, config path/merge/conflict helpers, config patch/manual
    item creation, config patch/manual application, and redaction helpers.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `d4a72ad9`
  - Weight: 1
  - Last verified: 2026-05-07, focused migration helper proof (`1 passed`),
    adjacent migration/runtime proof (`3 passed, 1093 deselected`), adjacent
    imported-plugin proof (`284 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00274` Imported outbound-send-deps facade shim
  - Source: `openclaw-main/src/plugin-sdk/outbound-send-deps.ts` and
    `openclaw-main/src/infra/outbound/send-deps.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `outbound-send-deps` and receive only the two upstream dependency
    resolver exports, preserving dynamic channel-key precedence and legacy
    `sendPascal` / `sendMS...` fallback key behavior.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `90665ba5`
  - Weight: 1
  - Last verified: 2026-05-07, focused outbound-send-deps proof (`1 passed`),
    adjacent outbound/runtime proof (`3 passed, 1094 deselected`), adjacent
    imported-plugin proof (`285 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00275` Imported command-status-runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/command-status-runtime.ts` and
    `openclaw-main/src/plugin-sdk/command-status.runtime.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `command-status-runtime` and receive the lazy
    `resolveDirectStatusReplyForSession` facade with blank session-key early
    return, fakeable native session-status delegation, and precise unavailable
    error projection when no host runtime is wired.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `b0242a2c`
  - Weight: 1
  - Last verified: 2026-05-07, focused command-status-runtime proof
    (`1 passed`), adjacent command status proof (`2 passed, 1096 deselected`),
    adjacent imported-plugin proof (`286 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00276` Imported reply-runtime aggregate facade shim
  - Source: `openclaw-main/src/plugin-sdk/reply-runtime.ts` and adjacent
    `openclaw-main/src/auto-reply/*` helper modules
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `reply-runtime` and receive the aggregate reply chunking,
    heartbeat, silent-token, group activation, inbound finalization, dedupe,
    reply-reference, dispatch, reply-generation, and conversation-label
    helpers; heavy dispatch/model calls delegate to a fakeable native host
    runtime and return precise unavailable errors when unwired.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `32213a5c`
  - Weight: 1
  - Last verified: 2026-05-07, focused reply-runtime proof (`1 passed`),
    adjacent reply facade proof (`6 passed, 1093 deselected`), adjacent
    imported-plugin proof (`287 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00277` Imported reply-dispatch-runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/reply-dispatch-runtime.ts`,
    `openclaw-main/src/auto-reply/chunk.ts`,
    `openclaw-main/src/auto-reply/reply/conversation-label-generator.ts`,
    `openclaw-main/src/auto-reply/reply/inbound-context.ts`, and
    `openclaw-main/src/auto-reply/reply/provider-dispatcher.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `reply-dispatch-runtime` and receive the exact five-export
    dispatch facade for chunk-mode resolution, inbound context finalization,
    conversation label generation, buffered block dispatch, and direct
    dispatcher calls; heavy runtime calls delegate to the fakeable native host
    runtime and return precise unavailable errors when unwired.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `c587ef3e`
  - Weight: 1
  - Last verified: 2026-05-07, focused reply-dispatch-runtime proof
    (`1 passed`), adjacent reply dispatch proof (`4 passed, 1096 deselected`),
    adjacent imported-plugin proof (`288 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00278` Imported inbound-reply-dispatch facade shim
  - Source: `openclaw-main/src/plugin-sdk/inbound-reply-dispatch.ts`,
    `openclaw-main/src/channels/turn/kernel.ts`,
    `openclaw-main/src/channels/turn/dispatch-result.ts`,
    `openclaw-main/src/auto-reply/dispatch.ts`, and
    `openclaw-main/src/auto-reply/reply/dispatch-from-config.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `inbound-reply-dispatch` and receive the exact channel-turn
    orchestration facade for prepared/full inbound turns, dispatch-count
    helpers, settled dispatch-from-config callbacks, dispatch-base assembly,
    record then dispatch ordering, native reply dispatch delegation, and
    normalized outbound delivery.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `25231852`
  - Weight: 1
  - Last verified: 2026-05-07, focused inbound-reply-dispatch proof
    (`1 passed`), adjacent inbound/reply dispatch proof (`4 passed, 1097
    deselected`), adjacent imported-plugin proof (`289 passed, 812
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00279` Imported interactive-runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/interactive-runtime.ts`,
    `openclaw-main/src/interactive/payload.ts`, and
    `openclaw-main/src/channels/plugins/outbound/interactive.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `interactive-runtime` and receive the exact interactive payload
    facade for interactive reply normalization, message presentation
    normalization, presentation/interactive conversion, fallback rendering,
    reply content/channel-data predicates, text fallback extraction, and block
    reduction.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `3781cad9`
  - Weight: 1
  - Last verified: 2026-05-07, focused interactive-runtime proof (`1 passed`),
    adjacent interactive/outbound payload proof (`3 passed, 1099 deselected`),
    adjacent imported-plugin proof (`290 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00280` Imported infra-runtime compatibility facade shim
  - Source: `openclaw-main/src/plugin-sdk/infra-runtime.ts`,
    `openclaw-main/src/infra/retry.ts`,
    `openclaw-main/src/infra/backoff.ts`,
    `openclaw-main/src/infra/json-files.ts`,
    `openclaw-main/src/utils/fetch-timeout.ts`, and
    `openclaw-main/src/utils/run-with-concurrency.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `infra-runtime` and receive the deprecated compatibility barrel
    for delivery, diagnostics, retry/backoff, JSON atomic file IO, fetch
    timeout, async lock, singleton/dedupe, concurrency, outbound, SSRF,
    system-event, temp-path, and file-lock helpers without importing the
    TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0ba78971`
  - Weight: 1
  - Last verified: 2026-05-07, focused infra-runtime proof (`1 passed`),
    adjacent infra/runtime proof (`6 passed, 1097 deselected`), adjacent
    imported-plugin proof (`291 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00281` Imported media-runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/media-runtime.ts`,
    `openclaw-main/src/media/mime.ts`,
    `openclaw-main/src/media/store.ts`,
    `openclaw-main/src/media/temp-files.ts`,
    `openclaw-main/src/polls.ts`, and
    `openclaw-main/src/channels/plugins/outbound/direct-text-media.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `media-runtime` and receive the public media/payload barrel for
    byte-limit constants, MIME/path helpers, saved media buffers, outbound
    local media loading, poll normalization, agent media payloads,
    media-understanding exports, and direct text/media outbound adapter
    helpers without importing the TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `85e4b720`
  - Weight: 1
  - Last verified: 2026-05-07, focused media-runtime proof (`1 passed`),
    adjacent media/import proof (`7 passed, 1097 deselected`), adjacent
    imported-plugin proof (`292 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00282` Imported plugin-runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/plugin-runtime.ts`,
    `openclaw-main/src/plugins/commands.ts`,
    `openclaw-main/src/plugins/hook-runner-global.ts`,
    `openclaw-main/src/plugins/http-registry.ts`,
    `openclaw-main/src/plugins/interactive-binding-helpers.ts`,
    `openclaw-main/src/plugins/interactive.ts`,
    `openclaw-main/src/plugins/lazy-service-module.ts`, and
    `openclaw-main/src/plugins/runtime/gateway-request-scope.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `plugin-runtime` and receive the plugin command/hook/HTTP/
    interactive/runtime-scope barrel for command validation, duplicate
    detection, native provider specs, matching, safe execution, route
    conflict handling, lazy service startup, interactive dispatch,
    conversation-binding unavailable results, and request-scoped plugin
    identity without importing the TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `eb39f899`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-runtime proof (`1 passed`),
    adjacent plugin-runtime proof (`9 passed, 1096 deselected`), adjacent
    imported-plugin proof (`293 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00283` Imported security-runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/security-runtime.ts`,
    `openclaw-main/src/secrets/channel-secret-collector-runtime.ts`,
    `openclaw-main/src/secrets/runtime-shared.ts`,
    `openclaw-main/src/secrets/shared.ts`,
    `openclaw-main/src/security/channel-metadata.ts`,
    `openclaw-main/src/security/context-visibility.ts`,
    `openclaw-main/src/security/dm-policy-shared.ts`,
    `openclaw-main/src/security/safe-regex.ts`,
    `openclaw-main/src/security/secret-equal.ts`, and
    `openclaw-main/src/plugin-sdk/access-groups.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `security-runtime` and receive the public security/policy barrel
    for channel-secret collection, secret shared file helpers, channel
    metadata wrapping, supplemental context visibility, DM/access-group policy
    helpers, safe regex guards, safe file/port/SSRF/proxy helpers, redaction,
    secure tokens, and constant-time secret comparison without importing the
    TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `16f5ab50`
  - Weight: 1
  - Last verified: 2026-05-07, focused security-runtime proof (`1 passed`),
    adjacent security/import proof (`5 passed, 1101 deselected`), adjacent
    imported-plugin proof (`294 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00284` Imported gateway-runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/gateway-runtime.ts`,
    `openclaw-main/src/gateway/channel-status-patches.ts`,
    `openclaw-main/src/cli/gateway-rpc.ts`,
    `openclaw-main/src/gateway/net.ts`,
    `openclaw-main/src/gateway/node-command-policy.ts`,
    `openclaw-main/src/gateway/server-methods/nodes.helpers.ts`,
    `openclaw-main/src/gateway/startup-auth.ts`,
    `openclaw-main/src/gateway/auth.ts`,
    `openclaw-main/src/infra/ws.ts`,
    `openclaw-main/src/gateway/client.ts`,
    `openclaw-main/src/gateway/client-start-readiness.ts`,
    `openclaw-main/src/gateway/operator-approvals-client.ts`, and
    `openclaw-main/src/gateway/protocol/index.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `gateway-runtime` and receive the public gateway/client barrel for
    channel status patches, gateway RPC unavailable projection, loopback and
    node command helpers, auth/startup helpers, raw data coercion,
    OpenClaw-shaped gateway request errors, close-code hints,
    connect-challenge timeout clamping, event-loop-ready client startup,
    lightweight lifecycle-safe `GatewayClient` methods, and
    operator-approval client helpers without importing the TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `dc028590`
  - Weight: 1
  - Last verified: 2026-05-07, focused gateway-runtime proof (`1 passed`),
    adjacent gateway/import proof (`3 passed, 1104 deselected`), adjacent
    imported-plugin proof (`295 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00285` Imported hook-runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/hook-runtime.ts`,
    `openclaw-main/src/hooks/fire-and-forget.ts`,
    `openclaw-main/src/hooks/internal-hooks.ts`,
    `openclaw-main/src/hooks/internal-hook-types.ts`,
    `openclaw-main/src/hooks/message-hook-mappers.ts`, and
    `openclaw-main/src/plugins/hook-runner-global.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `hook-runtime` and receive the public hook pipeline barrel for
    fire-and-forget hook dispatch, bounded concurrency/drop behavior, hook
    error formatting, internal hook registration/triggering, event guards,
    canonical inbound/sent message hook mappers, plugin hook event/context
    projection, and global hook-runner initialize/reset helpers without
    importing the TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `89db1c12`
  - Weight: 1
  - Last verified: 2026-05-07, focused hook-runtime proof (`1 passed`),
    adjacent hook/plugin-runtime proof (`3 passed, 1105 deselected`),
    adjacent imported-plugin proof (`296 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00286` Imported agent-runtime-test-contracts facade shim
  - Source: `openclaw-main/src/plugin-sdk/agent-runtime-test-contracts.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/agents/auth-profile-runtime-contract.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/agents/delivery-no-reply-runtime-contract.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/agents/openclaw-owned-tool-runtime-contract.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/agents/outcome-fallback-runtime-contract.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/agents/prompt-overlay-runtime-contract.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/agents/schema-normalization-runtime-contract.ts`,
    and
    `openclaw-main/src/plugin-sdk/test-helpers/agents/transcript-repair-runtime-contract.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `agent-runtime-test-contracts` and receive source-backed
    contract fixtures for auth-profile alias forwarding, delivery/no-reply
    payloads, OpenClaw-owned tool hook installation/reset, Codex tool-result
    middleware, fallback model config, prompt overlay contexts, strict schema
    normalization models, queued-message transcript fixtures, and text/media
    tool results without importing the TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `0db396fe`
  - Weight: 1
  - Last verified: 2026-05-07, focused agent-runtime-test-contracts proof
    (`1 passed`), adjacent agent-runtime proof (`14 passed, 1095 deselected`),
    adjacent imported-plugin proof (`297 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00287` Imported channel-target-testing facade shim
  - Source: `openclaw-main/src/plugin-sdk/channel-target-testing.ts` and
    `openclaw-main/src/test-helpers/resolve-target-error-cases.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `channel-target-testing` and receive the public
    `installCommonResolveTargetErrorCases` helper for the four upstream target
    normalization/no-target/whitespace error cases, with fakeable test
    registration through `globalThis.it` and immediate assertion execution when
    no test hook is present.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `e6307d8a`
  - Weight: 1
  - Last verified: 2026-05-07, focused channel-target-testing proof
    (`1 passed`), adjacent channel target proof (`3 passed, 1107 deselected`),
    adjacent imported-plugin proof (`298 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00288` Imported channel-test-helpers facade shim
  - Source: `openclaw-main/src/plugin-sdk/channel-test-helpers.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/directory.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/directory-ids.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/channel-contract-suites.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/outbound-delivery.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/plugin-runtime-mock.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/send-config.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/start-account-context.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/start-account-lifecycle.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/status-issues.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/subagent-hooks.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/bundled-channel-entry.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/envelope-timestamp.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/pairing-reply.ts`, and
    `openclaw-main/src/test-utils/channel-plugins.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `channel-test-helpers` and receive the public channel testing
    barrel for directory assertions, channel plugin/action/setup/status
    contract suites, test registries, outbound plugin builders, hook handler
    maps, send-config assertions, account lifecycle helpers, bundled entry
    assertions, envelope timestamp formatting, pairing reply checks, and
    lightweight plugin runtime mocks without importing the TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `67872a14`
  - Weight: 1
  - Last verified: 2026-05-07, focused channel-test-helpers proof
    (`1 passed`), adjacent channel helper proof (`4 passed, 1107 deselected`),
    adjacent imported-plugin proof (`299 passed, 812 deselected`),
    `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00289` Imported plugin-test-api facade shim
  - Source: `openclaw-main/src/plugin-sdk/plugin-test-api.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `plugin-test-api` and receive `createTestPluginApi` with upstream
    no-op registration defaults, logger/runtime/config defaults, async
    next-turn injection fallback, run-context and session-scheduler no-ops,
    path resolution identity behavior, and caller override handling without
    importing the TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `db9e84ac`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-test-api proof (`1 passed`),
    adjacent plugin-test-api proof (`2 passed, 1110 deselected`), adjacent
    imported-plugin proof (`300 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00290` Imported plugin-test-contracts facade shim
  - Source: `openclaw-main/src/plugin-sdk/plugin-test-contracts.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/contracts-testkit.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/import-side-effects.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/direct-smoke.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/package-manifest-contract.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/plugin-registration-contract.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/plugin-registration-contract-cases.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/public-artifacts.ts`, and
    `openclaw-main/src/plugin-sdk/test-helpers/public-surface-loader.ts`
  - References: none
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `plugin-test-contracts` and receive registry fixtures,
    virtual/test plugin registration, provider capture/lookup, import
    side-effect assertions, direct import smoke execution, package and
    registration contract registration, public artifact guards, public-surface
    loader helpers, and bundled plugin registration case maps without
    importing the TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `086382f8`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-test-contracts proof
    (`1 passed`), adjacent plugin-test-contracts/plugin-test-api proof
    (`2 passed, 1111 deselected`), adjacent imported-plugin proof
    (`301 passed, 812 deselected`), `ruff check`, `mypy`, and
    `git diff --check`.

- [x] `OZ-PLUGIN-00291` Imported plugin-test-runtime facade shim
  - Source: `openclaw-main/src/plugin-sdk/plugin-test-runtime.ts`
  - References: `openclaw-main/src/plugins/contracts/plugin-sdk-subpaths.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `plugin-test-runtime` and receive the aggregate public runtime
    test helper barrel for plugin registries, captured registration, provider
    registration helpers, runtime env mocks, setup wizard helper runners,
    provider wizard option resolution, hook registry helpers, provider
    contract lookup, and lightweight task-flow binding without importing the
    TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `084da020`
  - Weight: 1
  - Last verified: 2026-05-07, focused plugin-test-runtime proof
    (`1 passed`), adjacent plugin-test-runtime/plugin-test-contracts/
    plugin-test-api proof (`3 passed, 1111 deselected`), adjacent
    imported-plugin proof (`302 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00292` Imported provider-test-contracts facade shim
  - Source: `openclaw-main/src/plugin-sdk/provider-test-contracts.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/provider-contract-suites.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/provider-contract.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/provider-replay-policy.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/stt-live-audio.ts`
  - References: `openclaw-main/src/plugins/contracts/plugin-sdk-subpaths.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `provider-test-contracts` and receive provider plugin/web
    search/web fetch contract suites, provider registry describers,
    wizard/runtime/discovery/auth describers, onboard config assertions,
    replay-policy assertions, captured thinking stream hooks, STT live-audio
    helpers, Dashscope video test helpers, media capability assertions,
    provider catalog constants, and public-surface loaders without importing
    the TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `7494160a`
  - Weight: 1
  - Last verified: 2026-05-07, focused provider-test-contracts proof
    (`1 passed`), adjacent provider-test-contracts/plugin-test-runtime/
    plugin-test-contracts proof (`3 passed, 1112 deselected`), adjacent
    imported-plugin proof (`303 passed, 812 deselected`), `ruff check`,
    `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00293` Imported test-env facade shim
  - Source: `openclaw-main/src/plugin-sdk/test-env.ts`,
    `openclaw-main/src/test-utils/env.ts`,
    `openclaw-main/src/test-utils/provider-usage-fetch.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/http-test-server.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/mock-incoming-request.ts`
  - References: `openclaw-main/src/plugins/contracts/plugin-sdk-subpaths.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `test-env` and receive env scoping, live-test helpers, provider
    key collection, error classifiers, shell-env posture, PNG helpers, media
    live model parsing/defaults, video duration/model helpers, HTTP
    request/response helpers, provider usage fetch mocks, temp/state/home
    fixtures, fetch preconnect mocks, mock incoming request/response helpers,
    and local HTTP server fixtures without importing the TypeScript runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `e2368bf5`
  - Weight: 1
  - Last verified: 2026-05-07, focused test-env proof (`1 passed`),
    adjacent test-env/provider-test-contracts/plugin-test-runtime proof
    (`3 passed, 1113 deselected`), adjacent imported-plugin proof (`304
    passed, 812 deselected`), `ruff check`, `mypy`, and `git diff --check`.

- [x] `OZ-PLUGIN-00294` Imported test-fixtures facade shim
  - Source: `openclaw-main/src/plugin-sdk/test-fixtures.ts`,
    `openclaw-main/src/cli/test-runtime-capture.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/bundled-plugin-paths.ts`,
    `openclaw-main/src/plugin-sdk/test-helpers/import-fresh.ts`,
    `openclaw-main/src/agents/sandbox/test-fixtures.ts`,
    `openclaw-main/src/agents/test-helpers/agent-message-fixtures.ts`
  - References: `openclaw-main/src/plugins/contracts/plugin-sdk-subpaths.test.ts`
  - Target: `src/openzues/cli.py`, `tests/test_gateway_node_methods.py`
  - Contract: native installed plugin runtimes can require scoped and
    unscoped `test-fixtures` and receive CLI runtime capture/spies, sandbox
    context/browser/prune/SSH fixtures, skill writers, agent message fixtures,
    fixture-local system-event peeks/reset, terminal sanitizing, chunk/fence
    helpers, generated-token assertions, typed cases, bundled plugin path
    helpers, and fresh dynamic import helpers without importing the TypeScript
    runtime.
  - Evidence required: focused gateway method test, adjacent plugin invoke
    tests, ruff, mypy
  - Status: checkpointed in `aa63f674`
  - Weight: 1
  - Last verified: 2026-05-07, focused test-fixtures proof (`1 passed`),
    system-event runtime regression proof (`1 passed`), adjacent
    test-fixtures/test-env/provider-test-contracts proof (`3 passed, 1114
    deselected`), adjacent imported-plugin proof (`305 passed, 812
    deselected`), `ruff check`, `mypy`, and `git diff --check`.

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
