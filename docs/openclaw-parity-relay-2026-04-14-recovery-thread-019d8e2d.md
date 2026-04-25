# OpenClaw Parity Relay

- Date: 2026-04-14
- Mission: Recover OpenClaw Total Parity Program
- Recovery thread: `019d8e2d-6757-7cf1-9213-04237beb5cd9`
- Anchor ledger: `docs/openclaw-parity-checkpoint-2026-04-10.md`

## Completed

- Reused the saved relay anchor instead of reopening Recall or rereading the parity ledger.
- Read the OpenClaw source-of-truth seam at `C:\Users\skull\OneDrive\Documents\openclaw-main\src\routing\session-key.ts`.
- Ran one bounded OpenZues mapping pass for the exported `routing/session-key` helpers.

## Verified

- OpenClaw source seam exports these parity-shaping helpers:
  - `buildAgentMainSessionKey`
  - `toAgentStoreSessionKey`
  - `resolveThreadSessionKeys`
  - `normalizeAgentId`
  - `classifySessionKeyShape`
  - `parseAgentSessionKey`
- Command:

```powershell
rg -n "buildAgentMainSessionKey|toAgentStoreSessionKey|resolveThreadSessionKeys|normalizeAgentId|classifySessionKeyShape|parseAgentSessionKey" src/openzues
```

- Result: no matches under `src/openzues`
- Concrete claim locked: OpenZues does not yet expose a direct ownership point for the current OpenClaw `routing/session-key` helper surface under the same exported API names.

## Next Smallest Step

- Do one tighter target-file discovery pass inside OpenZues session/routing code using the shared noun `sessionKey`, then map the nearest ownership file before making any parity edit.
- If that pass still finds no real owner, checkpoint the seam as an unmapped parity gap instead of broadening into unrelated routing or browser surfaces.

## Blockers

- The `routing/session-key` seam is not blocked by runtime failure.
- The remaining blocker is structural: the exact OpenZues file that should own session-key normalization/scoping behavior is still unmapped.
