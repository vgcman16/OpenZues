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
| Repo-wide OpenClaw parity in OpenZues | ~52.5% | Active, broad parity still open | `docs/openclaw-parity-progress.md`, `docs/openclaw-parity-unresolved-seams.md` |
| Active gateway/session/tool-contract path | ~98% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Chat/session contract subfamily | ~98.2% | Near-complete bounded local path | `docs/openclaw-parity-progress.md` |
| Runtime/CLI/doctor native bridge | ~99.9% | Mostly landed; packaging and installed plugin depth remain | `docs/openclaw-parity-progress.md` |
| Hermes reference surface | 80-85% | Reference-only rough status from repo inspection | `docs/tracking/03-hermes-reference-status.md` |
| Warp reference surface | Mixed | Reference-only; client-local plus backend-gated areas | `docs/tracking/04-warp-reference-status.md` |

## Current Worktree Boundary

The remote-media parity slice is now part of the active checkpoint and may be
staged with its source, test, and ledger updates:

- `src/openzues/services/gateway_node_methods.py`
- `tests/test_gateway_node_methods.py`
- `docs/openclaw-parity-progress.md`
- `docs/openclaw-parity-unresolved-seams.md`
- `docs/tracking/00-cross-repo-implementation-tracker.md`
- `docs/tracking/01-openzues-openclaw-parity-status.md`

Known untracked temp/log artifacts are unrelated and must remain unstaged.

## Current Queue

| ID | Area | Status | Percent Impact | Next Action |
| --- | --- | --- | ---: | --- |
| OZ-RM-001 | Sandboxed remote inbound provider media staging | Checkpointed and pushed in `2e6a3ed8` | Repo-wide +0.1%, chat/session +0.1%, gateway session/tool +0.1% | Done; continue `OZ-RT-001` |
| OZ-RT-001 | Runtime-control hard gaps | Open | TBD | Map next source-backed `chat.*` or `sessions.*` runtime mismatch |
| OZ-PKG-001 | Packaging/distribution breadth | Open | Broad | Map Windows-first doctor/package surfaces against OpenClaw |
| OZ-PLUGIN-001 | Real installed plugin module import/activation | Open | Broad | Compare OpenClaw plugin activation/import lifecycle and implement next seam |
| OZ-COMP-001 | Companion apps/nodes parity | Open | Broad | Inventory OpenClaw macOS/iOS/Android node behavior and choose first local bridge seam |
| OZ-PROV-001 | Provider-native outbound/inbound breadth | Open | Medium | Continue provider-specific send/poll/replay metadata gaps |

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
