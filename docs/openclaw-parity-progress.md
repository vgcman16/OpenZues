# OpenClaw Parity Progress

## Snapshot

- Estimated repo-wide parity: ~31% overall, with a reasonable band of ~26-36%
- Estimated active-family parity: ~82% for the current gateway/cron/session-delivery lane, with a reasonable band of ~79-85%
- Read this as a planning rollup, not a generated metric or a claim of feature-complete parity

## Methodology Note

- This is a hand-scored estimate based on the parity ledger in [openclaw-parity-checkpoint-2026-04-10.md](openclaw-parity-checkpoint-2026-04-10.md), especially the 2026-04-15, 2026-04-18, and 2026-04-20/2026-04-21 updates at the tail.
- Repo-wide parity is breadth-weighted. Big unfinished families like channels, browser/canvas/nodes/voice, packaging, and companion apps pull the total down harder than the stronger control-plane work pulls it up.
- Active-family parity means the family at the current ledger tail, not the whole product. Right now that is the gateway/cron/session-delivery seam inside the gateway surface.

## Feature Families

| Family | Status | Estimate | Notes |
| --- | --- | --- | --- |
| Gateway + gateway methods | Strong partial | ~80% | Method registry parity is reverified, `usage.cost` and `usage.status` are landed, `gateway.send` now has a real session-backed direct-target runtime for text plus media URL sends, `poll` rides the same explicit-target owner instead of a 503 placeholder, saved failed `gateway/poll` replays now rebuild the same poll transcript instead of collapsing to the question-only summary, direct `idempotencyKey` retries now reuse the same bounded local delivery instead of duplicating mirrored session messages, fresh/cached direct send-poll responses surface honest `runId` / `channel` plus session-backed transport metadata, those direct outbound paths now resolve through one explicit shared outbound runtime owner, and the capability inventory now keeps mixed scoped plus bare-string MCP tool catalogs classified instead of dropping live plugin methods from the scope summary. |
| Cron wake/delivery | Strong partial | ~76% | Many bounded seams are closed, including wake routing, webhook delivery status, last-channel/session fallback, cron `sessionKey` wake propagation, a shared session-backed explicit-target owner, and now one shared outbound runtime owner spanning explicit announce plus saved session-like replays, but true provider-runtime parity is still open. |
| Onboarding + setup | Partial | ~65% | QuickStart, gateway bootstrap, re-entrant setup, mode-aware wizard state, and launch handoff are all real; disabled recurring tasks now stay staged instead of falsely launch-ready, and picker-only wizard saves no longer preseed guided drafts. |
| CLI + operator control plane | Partial | ~60% | `status`, `continue`, `queue`, recover/harden flows, and gateway-doctor style surfaces exist, but broad OpenClaw operator/runtime CLI breadth is still missing. |
| Routing + session identity | Partial | ~58% | Launch routing, session-key helpers, routed conversation targeting, outbox/recovery seams, and session snapshot/compaction inventory surfacing are all real now, but broader provider-owned channel/account routing is still open. |
| Skills + Ops Mesh | Partial | ~70% | Skill pins, builtin skillbooks, inbox/snapshots/inventory, and lane-aware operator supervision are real and useful. |
| Channels + direct announce delivery | Partial | ~51% | OpenZues now has routed identity, shared explicit-target owners for direct text send, media URL send, and poll, cron/session fallback delivery, route-inventory default-account reuse for explicit targets, idempotent retry collapse for the shared session-backed direct owner, saved outbound delivery views that preserve request ids, mirrored message ids, and honest session-backed transport metadata, and one shared outbound runtime owner spanning direct send/poll, explicit announce, and saved session-like replays, but not an OpenClaw-style provider runtime or native media upload/result surface. |
| Browser/canvas/nodes/voice | Minimal | ~5% | Still called out as major parity gaps in the checkpoint and README, but the node lane now also pins paired-node commands to the approved roster, stages silent scope-upgrade requests when live commands widen, and keeps failed managed wakes on the truthful `node not connected` boundary. |
| Packaging + companion apps | Minimal | ~5% | Still largely outside the current shipped OpenZues surface. |

## Latest Queue Head

- Live repo-level queue: [openclaw-parity-unresolved-seams.md](openclaw-parity-unresolved-seams.md)
- Queue head from the latest checkpoint tail: provider-native outbound implementation behind the new shared direct/announce runtime owner remains the active gateway/cron/session-delivery queue head.
- This run integrated the hot gateway capability/bootstrap/logs/wizard shard already living in the dirty tree: wrapped live MCP tool catalogs now keep bare string plugin tools such as `browser.request` classified in the capability scope summary instead of dropping them from `classified_method_count`, wizard step field persistence stayed green, and the remote-bootstrap/log-tail proofs stayed locked through direct verification.
- Queue head unchanged: re-reading the upstream outbound/runtime source-of-truth still shows provider-native delivery behind channel outbound adapters, while the local tree still stops at the shared session-backed owner, so the missing move remains a real provider/runtime implementation behind that owner rather than another control-plane detour.
- Honest boundary: OpenZues now carries cron `sessionKey` through queued wakes, replays saved direct deliveries with honest transport identity, rebuilds saved failed `gateway/poll` deliveries into the same bounded local poll transcript, keeps launch/session and Ops Mesh channel-account identity on the same canonical account/peer rules, derives known default accounts from route inventory before shared explicit-target delivery, routes `gateway.send` direct text plus media URL messages through that owner, routes `poll` through the same session-backed explicit-target delivery path, routes explicit announce plus saved session-like outbound delivery replays through the same shared outbound runtime owner, dedupes repeated direct send/poll retries by `idempotencyKey` on that shared local owner, surfaces honest `runId` / `channel` plus session-backed transport metadata on fresh and cached direct gateway responses, preserves the same session-backed transport metadata on saved outbound delivery views, keeps gateway session discovery/compaction inventory honest without inventing an empty fallback global session, and now keeps mixed scoped plus string MCP tool catalogs classified honestly on the capability surface, but the transport still mirrors into canonical target sessions rather than an OpenClaw-style provider runtime or native media upload/result surface.
- The former hot session archive/compaction inventory surfacing seam is now locked, so there is no shorter hot-shard detour ahead of the provider-runtime queue head.
- There is no separate session-backed `gateway.send` breadth placeholder left ahead of the queue head; direct text, poll, media URL send, explicit announce, and saved session-like replays now share the same local runtime owner, so the next honest follow-on is the provider-native implementation behind that owner.

## References

- Primary ledger: [openclaw-parity-checkpoint-2026-04-10.md](openclaw-parity-checkpoint-2026-04-10.md)
- Repo-level seam queue: [openclaw-parity-unresolved-seams.md](openclaw-parity-unresolved-seams.md)
- Useful narrow seam example: [openclaw-parity-relay-2026-04-14-recovery-thread-019d8e51.md](openclaw-parity-relay-2026-04-14-recovery-thread-019d8e51.md)
