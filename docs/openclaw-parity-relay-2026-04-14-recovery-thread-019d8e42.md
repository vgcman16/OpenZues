# OpenClaw Parity Relay

- Date: 2026-04-14
- Mission: Recover OpenClaw Total Parity Program
- Recovery thread: `019d8e42-657c-73d1-b0fc-79209133ccdf`
- Anchor ledger: `docs/openclaw-parity-checkpoint-2026-04-10.md`

## Completed

- Resumed from the saved relay trail instead of reopening Recall or rereading the parity ledger.
- Mapped the nearest OpenZues ownership seam for session-key routing:
  - `src/openzues/services/launch_routing.py` owns routed launch session-key construction via `_build_session_key(...)`.
  - `src/openzues/services/ops_mesh.py` only consumes an inbound camel-case event `sessionKey` and falls back to the mission row's stored `session_key`.
  - `src/openzues/services/gateway_capability.py` has a separate memory-proof-specific session key shape (`gateway:memory-proof:{instance_id}:{scope}`).
- Re-read the OpenClaw source-of-truth seam at `C:\Users\skull\OneDrive\Documents\openclaw-main\src\routing\session-key.ts` to compare the helper surface against the current OpenZues ownership map.

## Verified

- Concrete claim locked: OpenZues already has one authoritative routed-session-key builder, and it is lane-churn-stable for the workspace-affinity seam.
- Focused proof:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_app.py -k "test_setup_launch_handoff_keeps_workspace_affinity_session_key_across_lane_churn"
```

- Result: `1 passed, 145 deselected`
- The passing proof confirms the routed session key remains stable across lane churn while launch resolution moves between lanes, which matches the current `launch_routing` ownership model rather than the richer OpenClaw helper API.

## Current Parity Gap

- OpenClaw exposes reusable helper names and shapes for agent-scoped session keys:
  - `buildAgentMainSessionKey`
  - `toAgentStoreSessionKey`
  - `resolveThreadSessionKeys`
  - `normalizeAgentId`
  - `classifySessionKeyShape`
  - `parseAgentSessionKey`
- OpenZues does not yet expose a shared helper module or equivalent API under that surface.
- The closest current OpenZues owner is `LaunchRoutingService._build_session_key(...)`, but that function only covers launch-route keys and does not absorb agent/main/thread parsing or normalization.

## Next Smallest Step

- Introduce one shared OpenZues session-key helper seam, starting with extraction of the current launch-route builder into a reusable module with tests.
- Keep the first slice bounded:
  - preserve existing `launch:mode:...` output exactly,
  - keep `gateway:memory-proof:...` separate unless the helper can host it without widening scope,
  - do not broaden into browser, node, voice, or packaging seams on the next turn.

## Blockers

- No runtime blocker is active on this seam.
- The blocker is structural parity only: OpenZues lacks a reusable session-key helper surface comparable to OpenClaw's `routing/session-key.ts`.
