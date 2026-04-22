# OpenClaw Parity Progress

## Snapshot

- Estimated repo-wide parity: ~30% overall, with a reasonable band of ~25-35%
- Estimated active-family parity: ~70% for the current gateway/cron/session-delivery lane, with a reasonable band of ~65-75%
- Read this as a planning rollup, not a generated metric or a claim of feature-complete parity

## Methodology Note

- This is a hand-scored estimate based on the parity ledger in [openclaw-parity-checkpoint-2026-04-10.md](openclaw-parity-checkpoint-2026-04-10.md), especially the 2026-04-15, 2026-04-18, and 2026-04-20/2026-04-21 updates at the tail.
- Repo-wide parity is breadth-weighted. Big unfinished families like channels, browser/canvas/nodes/voice, packaging, and companion apps pull the total down harder than the stronger control-plane work pulls it up.
- Active-family parity means the family at the current ledger tail, not the whole product. Right now that is the gateway/cron/session-delivery seam inside the gateway surface.

## Feature Families

| Family | Status | Estimate | Notes |
| --- | --- | --- | --- |
| Gateway + gateway methods | Strong partial | ~70% | Method registry parity is reverified, `usage.cost` and `usage.status` are landed, and the gateway contract is much deeper than the original inventory checkpoint. |
| Cron wake/delivery | Strong partial | ~70% | Many bounded seams are closed, including wake routing, webhook delivery status, last-channel/session fallback, and cron `sessionKey` wake propagation, but direct peer-target announce delivery is still open. |
| Onboarding + setup | Partial | ~65% | QuickStart, gateway bootstrap, re-entrant setup, mode-aware wizard state, and launch handoff are all real. |
| CLI + operator control plane | Partial | ~60% | `status`, `continue`, `queue`, recover/harden flows, and gateway-doctor style surfaces exist, but broad OpenClaw operator/runtime CLI breadth is still missing. |
| Routing + session identity | Partial | ~55% | Launch routing, session-key helpers, routed conversation targeting, and outbox/recovery seams exist, but broader channel/account routing is still open. |
| Skills + Ops Mesh | Partial | ~70% | Skill pins, builtin skillbooks, inbox/snapshots/inventory, and lane-aware operator supervision are real and useful. |
| Channels + direct announce delivery | Early | ~20% | OpenZues now has routed identity and some cron/session fallback delivery, but not a broad native channel runtime and not full explicit-target announce delivery. |
| Browser/canvas/nodes/voice | Minimal | ~5% | Still called out as major parity gaps in the checkpoint and README. |
| Packaging + companion apps | Minimal | ~5% | Still largely outside the current shipped OpenZues surface. |

## Latest Queue Head

- Queue head from the latest checkpoint tail: explicit peer-target announce delivery in the active gateway/cron/session-delivery family.
- Honest boundary: OpenZues now carries cron `sessionKey` through queued wakes and supports session-backed/route-backed fallbacks, but explicit peer-target announce delivery still stops at notification-route or webhook ownership.
- This is a checkpoint-derived queue head, not a live runtime queue snapshot.

## References

- Primary ledger: [openclaw-parity-checkpoint-2026-04-10.md](openclaw-parity-checkpoint-2026-04-10.md)
- Useful narrow seam example: [openclaw-parity-relay-2026-04-14-recovery-thread-019d8e51.md](openclaw-parity-relay-2026-04-14-recovery-thread-019d8e51.md)
