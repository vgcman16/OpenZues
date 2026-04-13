# Swarm Constitution Checkpoint

Date: 2026-04-12
Repo: `C:\Users\skull\OneDrive\Documents\OpenZues`
Scope: Native 9-agent swarm constitution landed end to end

## Objective

Build a native 9-agent orchestration layer directly into OpenZues without external agent
frameworks:

- structured JSON payload bus only
- 9 native roles with isolated prompts and owned surfaces
- mission-level sequential routing through the swarm
- conflict pause semantics surfaced through the existing reflex deck

## Landed In This Slice

### Schema contract

Added native swarm schema types in `src/openzues/schemas.py` for:

- role identity and stage status
- payload kinds and isolation scopes
- product spec, architecture plan, test strategy, implementation plans
- security review, refactor plan, integration report
- conflict packets and a cumulative working set
- role definitions, stage definitions, constitution view, and bus envelope

This establishes how the pipeline is expected to move:

1. Conductor emits a `mission_brief`
2. Product Manager emits a `product_spec`
3. Architect emits an `architecture_plan`
4. Test Engineer emits a `test_strategy`
5. Backend Engineer emits a `backend_plan`
6. Frontend Engineer emits a `frontend_plan`
7. Security Auditor emits a `security_review`
8. Refactorer emits a `refactor_plan`
9. Integration Tester emits an `integration_report`

Every handoff is modeled as a `SwarmEnvelopeView` with structured fields and a shared
`SwarmWorkingSetView`. The constitution explicitly sets `routing_mode = "json_bus"` and
`no_free_chat = true`.

### Service runtime

`src/openzues/services/swarm.py` now carries the real runtime helpers:

- the canonical 9-role order
- role definitions and prompts
- stage sequencing for the full swarm constitution
- `SwarmConductor.open_mission(...)` for the initial conductor-to-PM brief
- `SwarmConductor.route(...)` for conductor-owned handoffs
- conflict redirection back into the currently blocked role
- mission bootstrap state creation
- stage prompt construction
- structured payload parsing and validation
- working-set merge logic
- integration completion and blocking logic

### Mission integration

`src/openzues/services/missions.py` now treats swarm missions as a first-class mission mode:

- `MissionCreate` accepts `swarm_enabled`
- swarm missions persist their runtime state on the mission row through `swarm_state_json`
- swarm startup removes the legacy `delegation` toolset from the autonomous prompt path
- `_build_turn_prompt(...)` swaps to the role-scoped swarm prompt when a swarm runtime is active
- `item/completed` + `final_answer` is interpreted as a stage payload for swarm missions
- valid role payloads advance the mission to the next role instead of prematurely completing it
- integration payloads complete the mission only when blockers and failing checks are empty
- malformed payloads or detected conflicts pause the mission with structured swarm state intact

### Reflex deck integration

`src/openzues/services/reflexes.py` now synthesizes a dedicated conflict-resolution reflex for
blocked swarm missions:

- blocked swarm conflicts stay paused instead of being auto-unblocked by the normal runner
- the reflex deck now surfaces a `scope_realign` conflict-resolution prompt synthesized from the
  stored swarm conflict packet
- the prompt remains JSON-only so a resumed role can re-emit a valid structured payload

## Verification

Verification run from the repo virtualenv:

- `.\.venv\Scripts\python.exe -m ruff check src/openzues/schemas.py src/openzues/database.py src/openzues/services/swarm.py src/openzues/services/missions.py src/openzues/services/reflexes.py tests/test_swarm.py tests/test_missions.py tests/test_app.py`
  - result: passed
- `.\.venv\Scripts\python.exe -m mypy src/openzues/services/swarm.py src/openzues/services/missions.py src/openzues/services/reflexes.py`
  - result: passed
- `.\.venv\Scripts\python.exe -m pytest tests/test_swarm.py tests/test_missions.py tests/test_app.py -q`
  - result: `201 passed`

## Next Step

The native swarm kernel itself is landed. The next follow-on work is productizing the entrypoints:

- expose swarm launch controls in the operator UI and CLI
- add richer conductor policies for looping integration failures back to the owning role
- broaden swarm-specific dashboard surfaces if operator visibility needs to go deeper than the
  current delegation brief and reflex deck

## Blockers

No access blocker hit in this slice.
No implementation blocker remains in the native swarm runtime seam.
