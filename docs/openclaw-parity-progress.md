# OpenClaw Parity Progress

## Snapshot

- Estimated repo-wide parity: ~30% overall, with a reasonable band of ~25-35%
- Estimated active-family parity: ~75% for the current gateway/cron/session-delivery lane, with a reasonable band of ~70-80%
- Read this as a planning rollup, not a generated metric or a claim of feature-complete parity

## Methodology Note

- This is a hand-scored estimate based on the parity ledger in [openclaw-parity-checkpoint-2026-04-10.md](openclaw-parity-checkpoint-2026-04-10.md), especially the 2026-04-15, 2026-04-18, and 2026-04-20/2026-04-21 updates at the tail.
- Repo-wide parity is breadth-weighted. Big unfinished families like channels, browser/canvas/nodes/voice, packaging, and companion apps pull the total down harder than the stronger control-plane work pulls it up.
- Active-family parity means the family at the current ledger tail, not the whole product. Right now that is the gateway/cron/session-delivery seam inside the gateway surface.

## Feature Families

| Family | Status | Estimate | Notes |
| --- | --- | --- | --- |
| Gateway + gateway methods | Strong partial | ~75% | Method registry parity is reverified, `usage.cost` and `usage.status` are landed, and `gateway.send` now has a real text-only direct-target runtime instead of a 503 placeholder. |
| Cron wake/delivery | Strong partial | ~75% | Many bounded seams are closed, including wake routing, webhook delivery status, last-channel/session fallback, cron `sessionKey` wake propagation, and a shared session-backed explicit-target owner, but true provider-runtime parity is still open. |
| Onboarding + setup | Partial | ~65% | QuickStart, gateway bootstrap, re-entrant setup, mode-aware wizard state, and launch handoff are all real. |
| CLI + operator control plane | Partial | ~60% | `status`, `continue`, `queue`, recover/harden flows, and gateway-doctor style surfaces exist, but broad OpenClaw operator/runtime CLI breadth is still missing. |
| Routing + session identity | Partial | ~55% | Launch routing, session-key helpers, routed conversation targeting, and outbox/recovery seams exist, but broader channel/account routing is still open. |
| Skills + Ops Mesh | Partial | ~70% | Skill pins, builtin skillbooks, inbox/snapshots/inventory, and lane-aware operator supervision are real and useful. |
| Channels + direct announce delivery | Early partial | ~35% | OpenZues now has routed identity, a shared text-only explicit-target send owner, and cron/session fallback delivery, but not an OpenClaw-style provider runtime and not media/poll breadth. |
| Browser/canvas/nodes/voice | Minimal | ~5% | Still called out as major parity gaps in the checkpoint and README. |
| Packaging + companion apps | Minimal | ~5% | Still largely outside the current shipped OpenZues surface. |

## Latest Queue Head

- Live repo-level queue: [openclaw-parity-unresolved-seams.md](openclaw-parity-unresolved-seams.md)
- Queue head from the latest checkpoint tail: true outbound provider runtime for direct channel/account send + announce in the active gateway/cron/session-delivery family.
- Honest boundary: OpenZues now carries cron `sessionKey` through queued wakes, replays saved direct deliveries with honest transport identity, keeps launch/session and Ops Mesh channel-account identity on the same canonical account/peer rules, and routes `gateway.send` text-only direct messages through the shared explicit-target owner, but that owner is still session-backed rather than an OpenClaw-style provider runtime.
- If product scope stays session-backed, the next honest unowned follow-on is the remaining channel-target breadth gap: `send` media delivery plus `poll`.

## References

- Primary ledger: [openclaw-parity-checkpoint-2026-04-10.md](openclaw-parity-checkpoint-2026-04-10.md)
- Repo-level seam queue: [openclaw-parity-unresolved-seams.md](openclaw-parity-unresolved-seams.md)
- Useful narrow seam example: [openclaw-parity-relay-2026-04-14-recovery-thread-019d8e51.md](openclaw-parity-relay-2026-04-14-recovery-thread-019d8e51.md)
