# OpenClaw Parity Relay

- Date: 2026-04-14
- Mission: Recover OpenClaw Total Parity Program
- Recovery thread: `019d8e51-b75b-7472-91bc-81b864cf428d`
- Anchor ledger: `docs/openclaw-parity-checkpoint-2026-04-10.md`

## Completed

- Locked the session-key helper extraction seam without reopening the parity ledger.
- Added a shared OpenZues helper at `src/openzues/services/session_keys.py`.
- Rewired `src/openzues/services/launch_routing.py` so routed launch keys now flow through that shared helper instead of an inline builder.
- Added a launch-safe session-key shape classifier to `src/openzues/services/session_keys.py` aligned to the OpenClaw routing helper surface.
- Expanded the narrow proof file at `tests/test_session_keys.py` so it now preserves:
  - workspace-affinity key shape,
  - saved-lane key shape with conversation-target suffixes,
  - `missing | agent | legacy_or_alias | malformed_agent` classification behavior.

## Verified

- Concrete claim locked: OpenZues now mirrors one additional OpenClaw session-key primitive by classifying agent-shaped keys separately from legacy aliases and malformed agent keys, while preserving the routed launch-key output exactly for the current seam.
- Focused proof:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests\test_session_keys.py
.\.venv\Scripts\python.exe -m pytest .\tests\test_app.py -k "test_setup_launch_handoff_keeps_workspace_affinity_session_key_across_lane_churn"
```

- Result:
  - `tests/test_session_keys.py`: `3 passed`
  - `tests/test_app.py -k "test_setup_launch_handoff_keeps_workspace_affinity_session_key_across_lane_churn"`: `1 passed, 145 deselected`

## Current Parity Position

- OpenZues now has one reusable session-key helper seam for routed launch keys.
- OpenZues now also exposes the first agent-key-aware classification primitive from OpenClaw's `src/routing/session-key.ts`.
- OpenClaw parity gaps still remain for richer agent/main/thread parsing and normalization APIs such as `normalizeAgentId`, `buildAgentMainSessionKey`, and `resolveThreadSessionKeys`.
- `gateway:memory-proof:{instance_id}:{scope}` remains separate, which keeps this recovery slice bounded.

## Next Smallest Step

- Extend `src/openzues/services/session_keys.py` with one more bounded primitive from the OpenClaw surface, preferably `normalizeAgentId` as the next launch-safe normalization helper before any thread-key or peer-key expansion.
- Keep the next proof narrow:
  - exact helper unit tests first,
  - then one existing routed-launch integration proof from `tests/test_app.py`.

## Notes

- The workspace has unrelated in-flight changes outside this seam; they were left untouched on this recovery path.
