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
| Repo-wide OpenClaw parity in OpenZues | ~62.4% | Active, broad parity still open | `docs/openclaw-parity-progress.md`, `docs/openclaw-parity-unresolved-seams.md` |
| Active gateway/session/tool-contract path | ~99.9% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Chat/session contract subfamily | ~98.3% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Runtime/CLI/doctor native bridge | ~99.9% | Mostly landed; packaging and installed plugin depth remain | `docs/openclaw-parity-progress.md` |
| Hermes reference surface | 80-85% | Reference-only rough status from repo inspection | `docs/tracking/03-hermes-reference-status.md` |
| Warp reference surface | Mixed | Reference-only; client-local plus backend-gated areas | `docs/tracking/04-warp-reference-status.md` |

## Current Worktree Boundary

The Google Chat media/DM provider route slice is checkpointed in `7086dcb3`.
Any follow-up changes should target the next queue head only:

- `src/openzues/services/ops_mesh.py`
- `src/openzues/cli.py`
- `src/openzues/services/gateway_channels.py`
- `src/openzues/web/templates/index.html`
- `src/openzues/web/static/app.js`
- `tests/test_ops_mesh.py`
- `tests/test_cli.py`
- `tests/test_app.py`
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
| OZ-PKG-001 | Packaging/distribution breadth | Update status package-manager dependency posture checkpointed in `f1ac67da` | Repo-wide +0.1%, runtime/CLI/doctor +0.1% | Continue release/update/package breadth |
| OZ-PLUGIN-001 | Real installed plugin module import/activation | Persisted provider metadata checkpointed in `54c2fd49` | Repo-wide +0.1%, plugin metadata/runtime +0.1% | Continue runtime executor invocation breadth |
| OZ-CANVAS-001 | Media/voice/web/canvas breadth | Canvas shortcode normalization checkpointed in `c34e4a77` | Repo-wide +0.1%, browser/canvas/nodes/voice +0.1% | Continue media/canvas/provider breadth |
| OZ-COMP-001 | Companion apps/nodes parity | QR JSON setup-code contract checkpointed in `b79b87c3` | Repo-wide +0.1%, companion/setup breadth +0.1% | Continue companion QR/setup-code human/remote breadth |
| OZ-PROV-001 | Provider-native outbound/inbound breadth | Google Chat media/DM route checkpointed in `7086dcb3` | Repo-wide +0.1%, provider-native breadth +0.1% | Continue provider-specific send/poll/replay metadata gaps |

## Active Slice Detail

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
