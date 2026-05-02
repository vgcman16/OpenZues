# Progress Methodology

Agent report source: Dirac

Last updated: 2026-05-02

This file defines how to update the tracking workspace after each implementation
slice.

## Source Of Truth

- `openclaw-main` is the OpenClaw parity source of truth.
- OpenZues implementation evidence must come from source changes and local
  verification.
- Hermes and Warp are reference/bridge repos unless a row explicitly targets
  a Hermes or Warp integration.

## Percent Rules

Use weighted completion, not checkbox count:

```text
percent = sum(weight of verified seams) / sum(weight of all known seams in scope) * 100
```

Weights:

- 1: small validation or payload-shape seam
- 2-3: normal API/runtime seam
- 5+: broad lifecycle, packaging, provider, or companion-app seam

Only verified seams count. Mapped, implemented-but-unverified, partial, blocked,
or reference-only rows count as zero unless split into smaller verified rows.

Keep these percentages separate:

- Repo-wide OpenClaw parity
- Active OpenClaw feature family
- OpenZues bounded local path
- Hermes reference/bridge status
- Warp reference/bridge status

## Checkbox Rules

- `[ ]` open: not yet mapped or not started.
- `[~]` mapped: source, target, contract, and proof are known.
- `[x]` verified: implementation landed, proof passed, evidence recorded.
- `[!]` blocked: concrete external blocker with evidence.

Do not mark `[x]` from source comparison alone. Do not mark `[x]` when tests
were skipped.

## Required Evidence

Before implementation:

```powershell
git status --short
rg -n "specificMethod|specificContract" C:\Users\skull\OneDrive\Documents\openclaw-main\src
```

For OpenZues parity slices:

```powershell
python -m pytest tests\test_relevant.py::test_specific_case -q
python -m pytest tests\test_relevant.py -q -k "seam_keyword or adjacent_keyword"
ruff check src\openzues\... tests\...
mypy src\openzues\...
```

Before staging:

```powershell
git status --short
git diff --stat
git diff -- src\... tests\... docs\...
```

Stage only intentional source, tests, and docs. Never stage unrelated logs,
screenshots, temporary folders, generated databases, or user changes.

## Commit And Push Rules

- One commit should usually equal one verified seam.
- Commit only after the tracker and parity ledgers reflect the same evidence.
- Keep unrelated dirty files unstaged.
- Push `codex/openclaw-parity-native-runtimes` after the checkpoint commit when
  the branch is ready to share.

Commit message shape:

```text
Close OpenClaw <family> <seam> parity

Source: openclaw-main/<file>
Proof: pytest ..., ruff ..., mypy ...
Refs: Hermes <file> / Warp <file> if used
```

## Stale Claim Guardrails

Avoid unverified claims such as `complete`, `locked`, `full parity`, `matches
upstream`, or `done` unless backed by evidence in the row.

Use these labels instead:

- verified on YYYY-MM-DD with command/result
- mapped but unverified
- implemented, proof pending
- blocked by a specific external blocker
- reference-only, not counted toward OpenClaw parity

If OpenClaw changes, recompute affected rows. If Hermes or Warp contradict
OpenClaw, OpenClaw wins for OpenClaw parity.

## After Each Slice

Update:

- The seam row checkbox and status.
- Source, target, and reference file list.
- Exact contract summary.
- Exact verification commands and pass/fail counts.
- Percent rollup only if verified weight changed.
- Remaining adjacent gap and next queue head.
- Commit hash after checkpoint commit.
- Push branch/URL after successful push.

Final question before claiming progress: can a required upstream seam still be
named inside this scope? If yes, the checklist records progress, not completion.
