# Ops Mesh Sidecar Brief

## Summary

OpenZues already behaves like a local-first Codex mission control: it tracks live lanes, autonomous missions, approvals, checkpoints, playbooks, projects, event streams, and instance capability catalogs. The Ops Mesh Sidecar extends that control plane with a MyClaw-style operator layer that answers a different question: "What needs attention across all lanes right now, what is scheduled next, and what tooling is actually available?"

The sidecar should be additive, not a parallel product. It should reuse current OpenZues primitives instead of inventing a second mission system.

## Current product foundation

OpenZues already has the right seams:

- `missions`, `mission_checkpoints`, and continuity packets provide durable task state and handoff memory.
- `server_requests` and radar/reflex signals already expose approvals, blockers, and operator interrupts.
- `playbooks` and mission drafts already model reusable work units that can become scheduled runs.
- `projects` already anchor workspaces, git state, and GitHub context.
- connected instances already publish `skills`, `apps`, `plugins`, `mcp_servers`, config, and loaded threads.
- the WebSocket event stream already gives a live notification backbone.

## Product goal

Add a compact sidecar that helps an operator supervise multiple autonomous lanes without living inside the raw dashboard. The sidecar should compress attention, timing, and capability visibility into one fast surface.

## Sidecar surfaces

### 1. Task inbox

A unified operator queue for the highest-value next actions across the system.

- approvals waiting in `server_requests`
- blocked or failed missions
- fragile continuity packets
- armed reflexes
- fresh checkpoints ready for review
- queued or suggested launch opportunities

Each inbox item should show source, urgency, lane, project, recommended action, and a direct jump target.

### 2. Schedules

A lightweight timing layer for repeatable operations.

- run a playbook every morning
- launch a scout mission on a repo after a PR merge
- trigger a checkpoint sweep on long-running missions
- remind operators to review paused missions that have fresh handoffs

Start with scheduled playbook and mission-draft launches. Do not build a general workflow engine first.

### 3. Notifications

Push only the events that deserve interruption.

- approval required
- lane offline or failover needed
- mission failed after recovery budget
- new checkpoint ready
- scheduled run due

Notifications should be derived from the existing event hub and mission snapshots, with operator-selectable channels later.

### 4. Skills registry

A workspace-aware registry that turns raw `skills/list` output into an operator tool map.

- which skills exist on each lane
- which skills are relevant to the attached repo
- which skills are frequently used in successful runs
- which mission types have a matching skill gap

This makes "what can this lane do?" visible without drilling into instance details.

### 5. Integrations inventory

A normalized inventory of connected capability, built from existing app, plugin, MCP, and auth metadata.

- installed apps
- enabled plugins
- MCP server status
- auth posture and gaps
- lane-by-lane accessibility

The goal is operational trust: before launching work, the operator can see whether GitHub, Slack, Figma, or other integrations are actually ready.

### 6. Lane snapshots

A compact per-lane status card for fast supervision and handoff.

- connected/disconnected state
- active mission and thread
- current phase and current command
- approvals pending
- token heat and command burn
- last checkpoint summary
- continuity state and safest next handoff

This is the bridge between raw telemetry and operator judgment.

## Product principles

- Derived first: phase one should synthesize from current database rows and live instance refreshes before adding new persistence.
- Operator-native: optimize for triage, delegation, and resume, not for verbose reporting.
- Cross-lane: show work by lane, project, and urgency, not only by mission.
- Low-noise: the sidecar exists to suppress dashboard digging, not recreate it.

## Rollout phases

### Phase 1: Read-only sidecar

Ship task inbox, integrations inventory, skills registry, and lane snapshots from existing mission, request, checkpoint, and instance data.

### Phase 2: Scheduled operations

Add recurring schedules for playbooks and mission drafts, plus notification rules for approvals, failures, and fresh handoffs.

### Phase 3: Mesh coordination

Use sidecar history to rank lane health, recommend the best lane for a job, and surface recurring capability or integration gaps across repos.

## Operator value

OpenZues already runs missions well. The Ops Mesh Sidecar makes it operable at higher concurrency. It gives operators one place to see what needs judgment, what is due next, what each lane can actually do, and which missions are safe to resume, relay, or escalate.
