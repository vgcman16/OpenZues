# ECC Integration Checkpoint

Date: 2026-04-11
Source of truth: `C:\Users\skull\OneDrive\Documents\everything-claude-code-main`
Target: `C:\Users\skull\OneDrive\Documents\OpenZues`

## Completed slice

OpenZues now understands the local Everything Claude Code repository as a first-class harness surface instead of just another folder on disk.

Landed in this slice:

- Added a new ECC catalog service that auto-discovers a sibling `everything-claude-code-main` repo, parses ECC `skills/*/SKILL.md`, and scores relevant ECC skills against task and mission context.
- Threaded ECC auto-skill attachment into the existing skillbook path so launch drafts and autonomous mission prompts can pick up matching ECC workflows with real source-file references.
- Added ECC workspace inspection for tracked projects so the dashboard can recognize:
  - the ECC source repo itself
  - ECC-managed Codex workspaces with local AGENTS/config/MCP surface
- Surfaced ECC harness posture inside project cards and task/misson objective context so operators can see the available harness assets before a run starts.
- Preserved the broader launch-routing contract while touching the launch-draft path by tightening workspace-affinity route persistence behavior.

## Product effect

When a tracked project points at the ECC repo or an ECC-style Codex workspace, OpenZues now:

- shows that harness surface on the dashboard
- counts visible skills, commands, agents, rule families, Codex roles, and MCP servers
- auto-attaches relevant ECC skills into the skillbook
- tells the mission to open the linked ECC `SKILL.md` before following that workflow
- carries ECC workspace context into task drafts and autonomous mission prompts

## Primary files

- `src/openzues/services/ecc_catalog.py`
- `src/openzues/services/projects.py`
- `src/openzues/services/skillbook.py`
- `src/openzues/services/ops_mesh.py`
- `src/openzues/services/missions.py`
- `src/openzues/services/launch_routing.py`
- `src/openzues/settings.py`
- `src/openzues/app.py`
- `src/openzues/web/static/app.js`
- `tests/test_skillbook.py`
- `tests/test_app.py`
- `tests/test_ops_mesh.py`

## Verification

Passed:

- `.\.venv\Scripts\python.exe -m pytest tests/test_skillbook.py tests/test_app.py tests/test_ops_mesh.py -q`
- `.\.venv\Scripts\ruff.exe check src/openzues/services/ecc_catalog.py src/openzues/services/projects.py src/openzues/services/skillbook.py src/openzues/services/ops_mesh.py src/openzues/services/missions.py src/openzues/services/launch_routing.py src/openzues/settings.py src/openzues/app.py tests/test_skillbook.py tests/test_app.py tests/test_ops_mesh.py`
- `node --check src/openzues/web/static/app.js`
- `.\.venv\Scripts\python.exe -m compileall src`

## Next best slice

The highest-leverage next ECC seam is command and agent surface synthesis:

1. map ECC `commands/` and `agents/` into operator suggestions the same way skills now map into skillbooks
2. expose ECC install/drift health for tracked workspaces, not just raw surface detection
3. let onboarding/bootstrap recommend ECC-flavored setup posture when a workspace already carries ECC config
