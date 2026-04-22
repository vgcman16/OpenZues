# OpenClaw Parity Unresolved Seams

Updated: 2026-04-22

## How To Read This Queue

- This queue is repo-level and cross-cutting. It is for seams likely to fall between shard workers or cut across cron, session, gateway, delivery, and integration ownership.
- `Hot` means the relevant product files are already active in the current dirty tree, so the parity orchestrator should prefer verification and ledger work unless a fix is clearly surgical.
- `Next unowned` means the seam is not yet covered by the current hot write sets and is the best follow-on slice for this thread.

## Unresolved Queue

| Priority | Seam | Status | Why it still matters | Next exact move |
| --- | --- | --- | --- | --- |
| P1 | True outbound provider runtime for direct channel/account send + announce (`channel` / `to` / `accountId`) | Next unowned | OpenZues now has a shared explicit-target text-send owner across cron and gateway, but it still resolves those sends into canonical target sessions rather than an OpenClaw-style outbound provider runtime. | Decide whether parity stops at the local session-backed owner or continues into a real provider/runtime delivery surface. |
| P2 | Channel-target media and poll delivery breadth | Next unowned | `gateway.send` now works for text-only direct messages, but `send` media delivery and `poll` still return 503 placeholders. | Extend the shared direct owner to media/poll payloads or document those surfaces as intentionally unsupported. |
| P3 | Session archive/compaction inventory surfacing | Hot | The current dirty tree includes new session-compaction coverage, but the shard has not yet been ledgered as a closed seam. | Reverify the compaction/inventory proofs once the active session shard settles, then either lock the seam or requeue the missing payload surface precisely. |

## Verified This Run

- Landed one shared direct channel-target send owner in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py), [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_node_methods.py), and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\app.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/app.py): the reusable explicit-target owner that cron announce delivery used privately is now exposed for gateway callers, and `gateway.send` routes text-only direct messages through the same canonical target session/runtime instead of staying a perpetual 503 placeholder.
- Added focused regression coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_node_methods.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_node_methods.py) for injected direct-send runtime calls plus thread-id derivation from a thread-scoped `sessionKey`.
- Added focused API proof coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_gateway_nodes_api.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_gateway_nodes_api.py) for real `gateway.send` delivery history/session writes plus blank optional routing identifiers.
- Closed the saved direct-transport replay read-model seam in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\cli.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/cli.py): replay results for saved `session`, `announce`, and route-less `webhook` deliveries now surface honest transport kind plus target identity instead of a synthetic webhook-only route view, and the human CLI now prints route kind plus target for saved direct-delivery history and replay.
- Closed one verification-found regression in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\gateway_models.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/gateway_models.py): merged model catalog entries now sort by provider plus canonical model id before display name, so richer duplicate names do not destabilize catalog order.
- Landed one reusable channel/account routing kernel slice in [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\session_keys.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/session_keys.py) and [`C:\Users\skull\OneDrive\Documents\OpenZues\src\openzues\services\ops_mesh.py`](C:/Users/skull/OneDrive/Documents/OpenZues/src/openzues/services/ops_mesh.py): launch session keys and Ops Mesh route matching now canonicalize conversation-target `account_id` the same way, while preserving lowercase channel/peer identity for routed channel deliveries.
- Added focused regression coverage in [`C:\Users\skull\OneDrive\Documents\OpenZues\tests\test_channel_account_routing.py`](C:/Users/skull/OneDrive/Documents/OpenZues/tests/test_channel_account_routing.py) for canonical launch session keys plus peer/account route matching across raw `Workspace Bot` versus canonical `workspace-bot` identity.
- Verified direct-send unit coverage with `tests/test_gateway_node_methods.py -k "test_send_returns_validated_unavailable_contract or test_send_uses_channel_message_runtime_and_derives_thread_from_session_key"`: `2 passed`.
- Verified the new temp-path-sensitive direct-send API proofs by directly executing the exact test functions against repo-local temp paths:
  - `test_send_endpoint_delivers_channel_target_message_and_records_outbound_delivery`
  - `test_send_endpoint_allows_blank_optional_routing_identifiers`
- Verified saved direct replay route identity with `tests/test_ops_mesh.py -k "replay_outbound_deliveries_retries_saved_failed_session_delivery or replay_outbound_deliveries_retries_saved_failed_announce_delivery or replay_outbound_deliveries_retry_secret_backed_ad_hoc_webhook_delivery"`: `3 passed`.
- Verified saved direct-delivery CLI surfaces with `tests/test_cli.py -k "routes_deliveries_reports_saved_direct_transport_identity or routes_replay_json_reports_saved_announce_transport_identity or routes_replay_reports_saved_announce_transport_identity"`: `3 passed`.
- Verified the shared direct-send runtime types with `mypy src/openzues/services/ops_mesh.py src/openzues/services/gateway_node_methods.py`: clean.
- Verified the shared direct-send files with `ruff check --extend-ignore E501 src/openzues/services/ops_mesh.py src/openzues/services/gateway_node_methods.py src/openzues/app.py tests/test_gateway_node_methods.py tests/test_gateway_nodes_api.py`: clean.
- Verified touched schema/runtime types with `mypy src/openzues/services/ops_mesh.py src/openzues/cli.py src/openzues/schemas.py`: clean.
- Verified touched routing runtime types with `mypy src/openzues/services/session_keys.py src/openzues/services/ops_mesh.py`: clean.
- Verified touched files with `ruff check src/openzues/schemas.py src/openzues/services/ops_mesh.py src/openzues/cli.py tests/test_ops_mesh.py tests/test_cli.py`: clean.
- Verified this run's touched routing files with `ruff check src/openzues/services/session_keys.py src/openzues/services/ops_mesh.py tests/test_channel_account_routing.py`: clean.
- Verified model catalog coverage with `tests/test_gateway_models.py`: `3 passed`.
- Verified pending-work coverage with `tests/test_gateway_node_pending_work.py`: `7 passed`.
- Verified remote wizard ordering with `tests/test_gateway_wizard.py -k "remote_wizard_collects_operator_name_before_task_name"`: `1 passed`.
- Verified main-session cron wake routing with `tests/test_gateway_nodes_api.py -k "main_system_event_cron_run_routes_session_key_through_wake_queue"`: `1 passed`.
- Verified replay + wake regressions with `tests/test_ops_mesh.py -k "replay_outbound_deliveries_retry_secret_backed_ad_hoc_webhook_delivery or ops_mesh_routes_due_main_system_event_session_key_through_wake_queue"`: `2 passed`.
- Verified the temp-path-sensitive gateway session and local wizard proofs by directly executing the exact test functions against repo-local temp paths:
  - `test_build_snapshot_discovers_mission_and_transcript_sessions_without_metadata`
  - `test_build_snapshot_sorts_discovered_sessions_by_updated_at_desc`
  - `test_resolve_key_prefers_structural_session_id_match_over_fresher_fuzzy_duplicate`
  - `test_resolve_key_rejects_ambiguous_structural_session_id_duplicates`
  - `test_gateway_node_method_call_endpoint_supports_local_wizard_completion_from_saved_draft`
- Verified the new temp-path-sensitive channel/account routing proofs by directly executing the exact test functions against repo-local temp paths:
  - `test_build_launch_session_key_canonicalizes_channel_account_and_peer_identity`
  - `test_ops_mesh_matches_routes_after_account_id_canonicalization`
  - `test_ops_mesh_service_filters_notification_routes_by_conversation_target`

## Verification Notes

- `pytest` temp-path cleanup currently hits `WinError 5` in this Windows/OneDrive environment, so temp-path-heavy proofs may need direct invocation until that harness issue is cleaned up.
- The repo virtualenv launcher currently points at a missing base Python; focused verification succeeded by running the Codex runtime interpreter with `.venv\\Lib\\site-packages` on `PYTHONPATH`.
- `tests/test_gateway_nodes_api.py` still carries unrelated historical `E501` lines, so touched-file Ruff verification for this seam used `--extend-ignore E501` instead of widening into repo-style cleanup.
- The queue head now tracks the post-send shared direct-owner boundary rather than the older checkpoint-only follow-on.
