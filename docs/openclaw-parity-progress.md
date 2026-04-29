# OpenClaw Parity Progress

## Snapshot

- Updated: 2026-04-29.
- Estimated repo-wide parity: ~45% overall, with a reasonable band of ~40-50%.
- Estimated active gateway/session/tool-contract family parity: ~97% for the bounded local OpenZues path.
- Estimated chat/session contract subfamily parity: ~98% after the latest `chat.send`, `chat.inject`, `chat.abort`, `sessions.create`, `sessions.patch`, `sessions.delete`, `sessions.spawn`, and `tools.invoke` slices.
- Estimated browser/canvas/nodes/voice bounded-command family parity: ~99%; it is no longer the active queue head.
- This is a planning rollup, not a generated metric or a claim of feature-complete parity.

## Methodology Note

- Estimates are hand-scored from the primary parity ledger and the unresolved seam queue.
- Repo-wide parity is breadth-weighted. Packaging, companion apps, broader provider runtimes, ACP harness spawning, and full OpenClaw runtime/CLI breadth still keep the overall number below the local gateway/control-plane score.
- Active-family parity tracks the current source-backed gateway/session/tool-contract family, not the whole product.

## Fully Completed / Locked Bounded Slices

These are complete within the bounded OpenZues-local parity contract verified in this repo. They are not a claim that every OpenClaw product behavior is finished.

- Gateway method registry, method policy wiring, strict parameter guards, config lookup/mutation, node invoke guard rails, device pairing, device-token rotation/revoke, plugin approval lifecycle, exec approval lifecycle, and node/global exec approval policy are landed and verified.
- Cron local scheduling now covers expression schedules, due-run detection, delivery status, fallback announcement, session delivery fallback, system-event session-key wake routing, retry/backoff, one-shot cleanup, and OpenClaw-style CLI add/edit schedule parsing.
- Browser/canvas/nodes/voice bounded command coverage is effectively locked for the local bridge: native browser commands, action grammar, storage/cookies/HAR, auth profile login/delete/save, batch execution, dashboard lifecycle, canvas/A2UI/live reload, APNS wake paths, managed attachments, scoped capability URLs, and iOS provider command bridges all have concrete gateway runtimes or honest unavailable boundaries.
- Chat transcript contracts are locked for the current SQLite-backed store: `chat.history` projection, usage/cost metadata, abort partial metadata, text caps, oversized payload placeholders, untrusted suffix stripping, skip-only hiding, directive cleanup, `chat.send` schema/provenance/timeout/session-key guards, `chat.inject` schema guards, and `chat.abort` run-id plus requester ownership validation.
- Session tool contracts are locked across the bounded local path for `sessions_history`, `session_status`, `sessions_list`, `sessions_send`, `sessions_yield`, `sessions.create`, `sessions.patch`, `sessions.delete`, `sessions.preview`, and direct session-history REST/SSE behavior.
- Custom-agent control-plane ownership is landed for persisted agent create/update/delete, identity lookup, workspace file ownership, session creation/filtering, alias resolution, and deleted-agent send/steer guards.
- `tools.invoke` core bridge is landed for allow/deny policy, owner-only controls, before-call hooks, ordered registry-backed plugin runtime service envelopes, safe core mappings, plugin error projection, plugin-published `tools.catalog` and `tools.effective` groups, and OpenClaw-style projection/visibility for neighboring session tools.
- Native runtime seams are now landed for ACP spawn dispatch/tracking plus delete/reset cleanup, app-wired sandbox-required child-turn dispatch through Codex app-server workspace-write policy, route-backed thread-bound spawn binding, shared provider-native send metadata, and Telegram native document/reply/silent/thread payloads.

## Feature Families

| Family | Status | Estimate | Current Read |
| --- | --- | --- | --- |
| Gateway + gateway methods | Near-complete bounded local path | ~99% | Gateway method registry, config lookups/mutation, model/session inventory, node invoke guards, native browser command productization, plugin/exec approval lifecycles, exec approval policy config, device-pair lifecycle, device token rotate/revoke, agent registry mutation, memory-doctor mutation, OpenClaw bootstrap/memory agent files, and strict chat/session validation are heavily covered. |
| Gateway session/tool contracts | Active | ~97% | `sessions_history`, `session_status`, `sessions_list`, `sessions_send`, `sessions_spawn`, `sessions_yield`, `sessions.create`, `sessions.patch`, `sessions.delete`, `tools.invoke`, plugin-published `tools.catalog` / `tools.effective` groups, visibility policy, ACP spawn dispatch/tracking plus `mode="session"` thread-required guard and delete/reset runtime cleanup, app-wired sandbox-required Codex app-server dispatch, route-backed thread adapters with bound initial child-run and terminal completion delivery, configured and omitted subagent timeout defaults, completion-expectation metadata, lightweight bootstrap context, child task envelopes, lifecycle policy metadata, terminal cleanup consumption, wait-consumed completion announcements, completion-announcement idempotency, tracked-run freshness guards, `agent.wait` zero-timeout polling, exact run-id wait precedence, recovered-run tracking cleanup, exact-run tracker isolation, and chat/session transcript contracts are now the live queue head; config-driven sandbox target selection and broader native executor/provider hooks remain. |
| Chat + transcript contracts | Strong partial | ~97% | `chat.history`, direct session history REST/SSE, `chat.send`, `chat.inject`, `chat.abort` run ownership and partial persistence, live `session.message`, `sessions.changed`, transcript metadata, usage/cost, text caps, and sanitizer parity are verified against OpenClaw-shaped behavior where they map to SQLite-backed storage. |
| Cron wake/delivery | Strong partial | ~98% | Direct send/poll, provider route callbacks, native route setup, replay/test dispatch, provider error/result metadata, OpenClaw-style cron-expression schedules, due-run behavior, session-key wake routing, retry/backoff, one-shot delete-after-run cleanup, the CLI simple command group, and add/edit schedule/payload breadth are verified. |
| Onboarding + setup | Partial | ~70% | QuickStart, gateway bootstrap, saved-lane handling, degraded bootstrap boundaries, remote saved-lane wizard progression, and broken-default repair posture are real, with broader OpenClaw setup breadth still open. |
| CLI + operator control plane | Partial | ~90% | Health, status JSON breadth flags with fakeable usage/security adapters, text `status --all`, ACP unavailable bridge boundaries, continue, queue, recover/harden, gateway doctor, top-level sandbox/Docker doctor warning, delivery replay, route creation, direct route send/poll, sandbox inventory/config-backed explain/recreate plus human summaries, sessions inventory/spawn/wait plus cleanup dry-run/no-op apply, `--fix-missing` metadata pruning, stale `updatedAt` preview/enforce, count-cap preview/enforce, native disk-budget preview/enforce, and all-agent grouped cleanup JSON, read-only `tasks`/`tasks list`/`tasks show` inspection plus `tasks audit`, `tasks maintenance`, metadata-backed `tasks notify`, mission-backed `tasks cancel`, and `tasks flow list/show/cancel` over native mission/task-blueprint state, cron status/list/runs/run/rm/enable/disable plus add/edit schedule, delivery, payload, failure-alert, and one-shot cleanup flags, models list/status plus auth-status probe fallback, root `models set` / `models set-image` mutations, `models scan` metadata/no-probe/non-interactive/live probe posture, aliases list/add/remove, fallbacks list/add/remove/clear, image fallback list/add/remove/clear, auth order get/set/clear, and auth add/login/login-github-copilot/setup-token/paste-token with fakeable auth probes/check exits, `infer`/`capability` metadata list/inspect plus model run/list/inspect/providers/auth status/login/logout, image providers/generate/edit/describe/describe-many, audio providers/transcribe, video providers/generate/describe, web providers/search/fetch, embedding providers/create, and TTS providers/status/voices/enable/disable/set-provider/convert, channel status/probe/capabilities/resolve/logs, plugins list with saved install records, metadata-only `plugins.load.paths` manifest discovery, runtime-backed inspect tool projection, doctor with compatibility notices, inspect/info/marketplace list/local marketplace install/update/uninstall/enable/disable, and operator monitor surfaces exist; broader runtime CLI/TUI breadth remains. |
| Routing + session identity | Strong partial | ~84% | Session keys, routed targeting, custom-agent session creation/filtering/identity/workspace files, snapshot filtering, compaction inventory, spawned-session visibility, parent/child aliases, and direct session-history replay are real; provider-owned routing remains open. |
| Skills + Ops Mesh | Partial | ~72% | Skill pins, skillbooks, inbox/snapshots/inventory, Hermes-inspired toolsets, recall/learning surfaces, and lane-aware supervision are useful but not complete OpenClaw/Hermes parity. |
| Channels + direct announce delivery | Strong partial | ~96% | Shared outbound runtime ownership spans direct send/poll, explicit announce, saved replays, native adapters, Slack/Telegram/Discord/WhatsApp routes, CLI route send/poll commands, gateway-owned channel status/capability probe metadata with route-backed Slack/Telegram/Discord account probes and WhatsApp's upstream no-hook probe posture, saved-target plus route-backed Slack channel/user resolve with OpenClaw-style auto-kind grouping, route-backed Telegram username resolve, route-backed Discord channel-id/guild-qualified/global channel-name and user resolve, fakeable live channel resolve, structured channel log tailing, provider result metadata, OpenClaw-style send reply/thread/silent/document fields, Telegram native document/reply/silent/thread payloads plus topic-qualified send target parsing and parent-route matching, WhatsApp native reply/document/gif-video payloads, admin-scoped chat origin/system provenance, A2A announce/reply loops, and idle `sessions.steer` runtime sends; broader per-provider option coverage remains open. |
| Browser/canvas/nodes/voice | Locked bounded family | ~99% | Canvas documents/A2UI/live-reload/capability routing, node event wakes, APNS wake paths, managed attachments, native browser runtimes, guarded artifacts, action grammar, scoped settings, batch execution, dashboard lifecycle, AI chat command routing, iOS provider command bridges, clipboard controls, storage/cookie mutation, HAR capture, confirmation handling, auth profile login/delete, and password-safe auth save are now landed. |
| Packaging + companion apps | Minimal | ~5% | Still largely outside the current shipped OpenZues surface. |

## Remaining Not-Fully-Complete Areas

- Config-driven sandboxed target runtimes beyond the app-wired Codex workspace-write path plus deeper persistent thread unbind/end-hook behavior.
- Broader provider-native outbound runtime breadth for remaining provider-specific edge cases beyond the verified Telegram topic-qualified send/poll paths.
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

- `python -m pytest tests\test_cli.py -q -k "plugins_inspect_json_projects_runtime_executor_tools"`: 1 passed after projecting native plugin runtime executor tools through `plugins inspect --json`.
- `python -m pytest tests\test_cli.py -q -k "plugins_"`: 16 passed after rechecking plugin list/inspect/doctor/marketplace/install/update/uninstall/toggle surfaces.
- `ruff check src\openzues\cli.py tests\test_cli.py`: clean after the plugin runtime inspect projection slice.
- `mypy src\openzues\cli.py`: clean after the plugin runtime inspect projection slice.
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
- Telegram native `sendPoll` topic-qualified targets are now covered by the
  same OpenClaw-shaped proof as topic-qualified sends: parent supergroup routes
  accept `telegram:group:<chatId>:topic:<threadId>` and the provider payload
  carries Bot API `message_thread_id`.
- Verified the Telegram topic poll proof with `python -m pytest tests\test_ops_mesh.py -q -k "send_direct_channel_poll_parses_telegram_topic_target"`, adjacent `python -m pytest tests\test_ops_mesh.py -q -k "telegram_topic_target or topic_to_parent or send_direct_channel_poll_uses_telegram_native_route or send_direct_channel_poll_parses_telegram_topic_target"`, and `ruff check tests\test_ops_mesh.py`.
- `update.run` now returns the OpenClaw-shaped runtime update envelope with
  `ok`, native update result stats, restart scheduling metadata, and a restart
  sentinel payload/file carrying session delivery context, thread id, note, and
  the upstream 1000ms minimum timeout normalization.
- Verified the update-run envelope/sentinel slice with `python -m pytest tests\test_gateway_node_methods.py -q -k "update_run"`, `python -m pytest tests\test_gateway_nodes_api.py -q -k "update_run"`, adjacent `python -m pytest tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py -q -k "update_run or config_write_methods_persist_control_ui_config_with_base_hash or supports_config_set_patch_apply"`, `ruff check src\openzues\services\gateway_node_methods.py tests\test_gateway_node_methods.py tests\test_gateway_nodes_api.py`, and `mypy src\openzues\services\gateway_node_methods.py`.
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
- Verified the ACP client spawn-plan slice with `python -m pytest
  tests\test_cli.py -q -k "acp_client"` (`4 passed`), adjacent ACP CLI pack
  `python -m pytest tests\test_cli.py -q -k "acp_bridge or acp_client"` (`8
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

## References

- Primary ledger: [openclaw-parity-checkpoint-2026-04-10.md](openclaw-parity-checkpoint-2026-04-10.md)
- Repo-level seam queue: [openclaw-parity-unresolved-seams.md](openclaw-parity-unresolved-seams.md)
- Recovery example: [openclaw-parity-relay-2026-04-14-recovery-thread-019d8e51.md](openclaw-parity-relay-2026-04-14-recovery-thread-019d8e51.md)
