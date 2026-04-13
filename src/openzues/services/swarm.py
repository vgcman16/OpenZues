from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final
from uuid import uuid4

from openzues.schemas import (
    MissionDelegationBriefView,
    MissionDelegationRoleView,
    MissionSwarmConflictView,
    MissionSwarmRuntimeView,
    SwarmConflictView,
    SwarmConstitutionView,
    SwarmDirectiveView,
    SwarmEnvelopeView,
    SwarmRole,
    SwarmRoleDefinitionView,
    SwarmStageDefinitionView,
    SwarmWorkingSetView,
)

SWARM_COLLABORATION_MODE: Final[str] = "swarm_constitution"
SWARM_ROLE_ORDER: Final[tuple[SwarmRole, ...]] = (
    "conductor",
    "product_manager",
    "architect",
    "test_engineer",
    "backend_engineer",
    "frontend_engineer",
    "security_auditor",
    "refactorer",
    "integration_tester",
)
SWARM_EXECUTION_ROLE_ORDER: Final[tuple[SwarmRole, ...]] = SWARM_ROLE_ORDER[1:]


@dataclass(slots=True)
class SwarmAdvanceResult:
    status: str
    state: MissionSwarmRuntimeView
    checkpoint_kind: str
    checkpoint_summary: str
    final_summary: str | None = None
    blocking_summary: str | None = None


def _utcnow_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _objective_from_envelope(envelope: SwarmEnvelopeView) -> str:
    if envelope.directive is not None and envelope.directive.objective.strip():
        return envelope.directive.objective.strip()
    product_spec = envelope.working_set.product_spec
    if product_spec is not None and product_spec.problem.strip():
        return product_spec.problem.strip()
    return envelope.summary.strip() or "Advance the active swarm mission."


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def _merge_model_lists(values: list[Any], additions: list[Any]) -> list[Any]:
    seen: set[str] = set()
    output: list[Any] = []
    for item in [*values, *additions]:
        if hasattr(item, "model_dump"):
            payload = item.model_dump(mode="json", exclude_none=True)
        else:
            payload = item
        fingerprint = json.dumps(payload, sort_keys=True)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        output.append(item)
    return output


def merge_working_set(
    existing: SwarmWorkingSetView,
    incoming: SwarmWorkingSetView,
) -> SwarmWorkingSetView:
    return SwarmWorkingSetView(
        product_spec=incoming.product_spec or existing.product_spec,
        architecture_plan=incoming.architecture_plan or existing.architecture_plan,
        test_strategy=incoming.test_strategy or existing.test_strategy,
        backend_plan=incoming.backend_plan or existing.backend_plan,
        frontend_plan=incoming.frontend_plan or existing.frontend_plan,
        security_review=incoming.security_review or existing.security_review,
        refactor_plan=incoming.refactor_plan or existing.refactor_plan,
        integration_report=incoming.integration_report or existing.integration_report,
        decisions=_merge_model_lists(existing.decisions, incoming.decisions),
        risks=_merge_model_lists(existing.risks, incoming.risks),
        artifacts=_merge_model_lists(existing.artifacts, incoming.artifacts),
        conflicts=_merge_model_lists(existing.conflicts, incoming.conflicts),
    )


def detect_swarm_conflicts(working_set: SwarmWorkingSetView) -> list[SwarmConflictView]:
    conflicts = list(working_set.conflicts)

    backend_paths = {
        str(reference.path).strip()
        for reference in (working_set.backend_plan.file_targets if working_set.backend_plan else [])
        if reference.path
    }
    frontend_paths = {
        str(reference.path).strip()
        for reference in (
            working_set.frontend_plan.file_targets if working_set.frontend_plan else []
        )
        if reference.path
    }
    overlapping_paths = sorted(path for path in backend_paths & frontend_paths if path)
    if overlapping_paths:
        conflicts.append(
            SwarmConflictView(
                reason="ownership_overlap",
                summary=(
                    "Backend and frontend ownership overlap on "
                    + ", ".join(f"`{path}`" for path in overlapping_paths[:3])
                    + "."
                ),
                roles=["backend_engineer", "frontend_engineer"],
            )
        )

    return conflicts


def parse_swarm_envelope_text(
    text: str,
    *,
    expected_role: SwarmRole,
    expected_stage_index: int,
    run_id: str,
) -> SwarmEnvelopeView:
    normalized = text.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        normalized = "\n".join(lines).strip()
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        start = normalized.find("{")
        end = normalized.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Swarm role output was not valid JSON.") from None
        payload = json.loads(normalized[start : end + 1])

    envelope = SwarmEnvelopeView.model_validate(payload)
    if envelope.from_role != expected_role:
        raise ValueError(
            f"Swarm role output came from '{envelope.from_role}' instead of '{expected_role}'."
        )
    if envelope.to_role != "conductor":
        raise ValueError("Swarm role outputs must hand back to the conductor.")
    if envelope.stage_index != expected_stage_index:
        raise ValueError(
            f"Swarm role output stage {envelope.stage_index} did not match expected stage "
            f"{expected_stage_index}."
        )
    if envelope.run_id != run_id:
        raise ValueError("Swarm role output used the wrong run id.")
    return envelope


def build_swarm_delegation_brief(runtime: MissionSwarmRuntimeView) -> MissionDelegationBriefView:
    constitution = build_swarm_constitution()
    roles = [
        MissionDelegationRoleView(
            name=role.label,
            objective=role.system_prompt,
            ownership=f"Isolation scope: {role.isolation_scope.replace('_', ' ')}.",
            trigger=(
                "Current stage."
                if runtime.active_role == role.role
                else "Runs when the conductor routes work into this owned stage."
            ),
        )
        for role in constitution.roles
        if role.role != "conductor"
    ]
    summary = (
        "Native swarm constitution is armed across Product, Architecture, Test, Backend, "
        "Frontend, Security, Refactor, and Integration roles."
    )
    if runtime.status == "conflicted" and runtime.conflict is not None:
        summary = f"Swarm is paused on conflict: {runtime.conflict.summary}"
    elif runtime.status == "completed":
        summary = "Native swarm constitution completed the full multi-role pipeline."
    return MissionDelegationBriefView(
        enabled=True,
        mode="conductor_brainstorm_architect_planner_coder_auditor",
        activation="ready_now",
        confidence="high",
        summary=summary,
        rationale="The mission is using the native structured swarm bus instead of free-chat.",
        roles=roles,
    )


def build_swarm_constitution() -> SwarmConstitutionView:
    roles = [
        SwarmRoleDefinitionView(
            role="conductor",
            label="Conductor",
            system_prompt=(
                "Route the swarm. Never free-chat, never solve the task directly, and only "
                "emit structured directives or conflict packets."
            ),
            isolation_scope="global_coordination",
            consumes=[
                "mission_brief",
                "product_spec",
                "architecture_plan",
                "test_strategy",
                "backend_plan",
                "frontend_plan",
                "security_review",
                "refactor_plan",
                "integration_report",
                "conflict_report",
            ],
            produces=["role_directive", "conflict_report", "final_handoff"],
        ),
        SwarmRoleDefinitionView(
            role="product_manager",
            label="Product Manager",
            system_prompt=(
                "Turn the mission into a shippable product spec with scope, acceptance, and "
                "operator value. Do not design internals or implementation."
            ),
            isolation_scope="product_scope_only",
            consumes=["mission_brief", "role_directive"],
            produces=["product_spec"],
        ),
        SwarmRoleDefinitionView(
            role="architect",
            label="Architect",
            system_prompt=(
                "Turn the product spec into system design, contracts, sequencing, and file "
                "targets. Do not perform implementation work."
            ),
            isolation_scope="system_design_only",
            consumes=["product_spec", "role_directive"],
            produces=["architecture_plan"],
        ),
        SwarmRoleDefinitionView(
            role="test_engineer",
            label="Test Engineer",
            system_prompt=(
                "Define the proving strategy from the product spec and architecture. Create or "
                "update tests when the seam is already concrete."
            ),
            isolation_scope="quality_strategy_only",
            consumes=["product_spec", "architecture_plan", "role_directive"],
            produces=["test_strategy"],
        ),
        SwarmRoleDefinitionView(
            role="backend_engineer",
            label="Backend Engineer",
            system_prompt=(
                "Own backend, database, API, and mission-runtime changes. Implement only inside "
                "the backend surface and report the exact files and checks you touched."
            ),
            isolation_scope="backend_surface_only",
            consumes=["architecture_plan", "test_strategy", "role_directive"],
            produces=["backend_plan"],
        ),
        SwarmRoleDefinitionView(
            role="frontend_engineer",
            label="Frontend Engineer",
            system_prompt=(
                "Own UI, dashboard, and operator-facing changes. Implement only inside the "
                "frontend surface and honor the shared contracts."
            ),
            isolation_scope="frontend_surface_only",
            consumes=[
                "product_spec",
                "architecture_plan",
                "test_strategy",
                "backend_plan",
                "role_directive",
            ],
            produces=["frontend_plan"],
        ),
        SwarmRoleDefinitionView(
            role="security_auditor",
            label="Security Auditor",
            system_prompt=(
                "Audit the changed plan for auth, secrets, permissions, input handling, and "
                "misuse paths. Report findings and patch only when the repair is tight and local."
            ),
            isolation_scope="security_posture_only",
            consumes=["backend_plan", "frontend_plan", "role_directive"],
            produces=["security_review", "conflict_report"],
        ),
        SwarmRoleDefinitionView(
            role="refactorer",
            label="Refactorer",
            system_prompt=(
                "Tighten structure after the implementation and security review are known. "
                "Simplify without changing required behavior."
            ),
            isolation_scope="refactor_surface_only",
            consumes=["backend_plan", "frontend_plan", "security_review", "role_directive"],
            produces=["refactor_plan"],
        ),
        SwarmRoleDefinitionView(
            role="integration_tester",
            label="Integration Tester",
            system_prompt=(
                "Verify the whole plan end to end across contracts, verification surfaces, and "
                "handoffs. Run the highest-value checks and report exact pass/fail evidence."
            ),
            isolation_scope="integration_surface_only",
            consumes=[
                "test_strategy",
                "backend_plan",
                "frontend_plan",
                "security_review",
                "refactor_plan",
                "role_directive",
            ],
            produces=["integration_report"],
        ),
    ]
    stages = [
        SwarmStageDefinitionView(
            order=0,
            role="conductor",
            consumes=["mission_brief"],
            produces=["role_directive"],
            next_role="product_manager",
        ),
        SwarmStageDefinitionView(
            order=1,
            role="product_manager",
            consumes=["mission_brief", "role_directive"],
            produces=["product_spec"],
            next_role="architect",
        ),
        SwarmStageDefinitionView(
            order=2,
            role="architect",
            consumes=["product_spec", "role_directive"],
            produces=["architecture_plan"],
            next_role="test_engineer",
        ),
        SwarmStageDefinitionView(
            order=3,
            role="test_engineer",
            consumes=["product_spec", "architecture_plan", "role_directive"],
            produces=["test_strategy"],
            next_role="backend_engineer",
        ),
        SwarmStageDefinitionView(
            order=4,
            role="backend_engineer",
            consumes=["architecture_plan", "test_strategy", "role_directive"],
            produces=["backend_plan"],
            next_role="frontend_engineer",
        ),
        SwarmStageDefinitionView(
            order=5,
            role="frontend_engineer",
            consumes=[
                "product_spec",
                "architecture_plan",
                "test_strategy",
                "backend_plan",
                "role_directive",
            ],
            produces=["frontend_plan"],
            next_role="security_auditor",
        ),
        SwarmStageDefinitionView(
            order=6,
            role="security_auditor",
            consumes=["backend_plan", "frontend_plan", "role_directive"],
            produces=["security_review", "conflict_report"],
            next_role="refactorer",
        ),
        SwarmStageDefinitionView(
            order=7,
            role="refactorer",
            consumes=["backend_plan", "frontend_plan", "security_review", "role_directive"],
            produces=["refactor_plan"],
            next_role="integration_tester",
        ),
        SwarmStageDefinitionView(
            order=8,
            role="integration_tester",
            consumes=[
                "test_strategy",
                "backend_plan",
                "frontend_plan",
                "security_review",
                "refactor_plan",
                "role_directive",
            ],
            produces=["integration_report"],
            next_role="conductor",
        ),
    ]
    return SwarmConstitutionView(stages=stages, roles=roles)


class SwarmConductor:
    def __init__(self, constitution: SwarmConstitutionView | None = None) -> None:
        self.constitution = constitution or build_swarm_constitution()
        self._stage_by_role = {stage.role: stage for stage in self.constitution.stages}
        self._role_by_name = {role.role: role for role in self.constitution.roles}

    def role_definition(self, role: SwarmRole) -> SwarmRoleDefinitionView:
        return self._role_by_name[role]

    def stage_definition(self, role: SwarmRole) -> SwarmStageDefinitionView:
        return self._stage_by_role[role]

    def open_mission(
        self,
        *,
        objective: str,
        mission_id: int | None = None,
        run_id: str | None = None,
    ) -> SwarmEnvelopeView:
        return SwarmEnvelopeView(
            mission_id=mission_id,
            run_id=run_id or f"swarm-{uuid4().hex}",
            stage_index=1,
            from_role="conductor",
            to_role="product_manager",
            kind="mission_brief",
            summary=objective,
            directive=SwarmDirectiveView(
                objective=objective,
                required_outputs=["product_spec"],
                owned_surfaces=["problem framing", "scope", "acceptance criteria"],
                blocked_surfaces=["architecture", "implementation details"],
                guardrails=[
                    "Respond with structured JSON only.",
                    "Do not free-chat with any other role.",
                    "Do not invent implementation details yet.",
                ],
                exit_criteria=[
                    "Define scope-in and scope-out cleanly.",
                    "Define operator-visible acceptance criteria.",
                ],
            ),
            working_set=SwarmWorkingSetView(),
        )

    def route(
        self,
        envelope: SwarmEnvelopeView,
        *,
        objective: str | None = None,
    ) -> SwarmEnvelopeView:
        stage = self.stage_definition(envelope.from_role)
        next_role = stage.next_role
        if next_role is None or next_role == "conductor":
            return SwarmEnvelopeView(
                mission_id=envelope.mission_id,
                run_id=envelope.run_id,
                stage_index=envelope.stage_index + 1,
                from_role="conductor",
                to_role="conductor",
                kind="final_handoff",
                summary=envelope.summary,
                directive=SwarmDirectiveView(
                    objective=objective or _objective_from_envelope(envelope),
                    required_outputs=["final_handoff"],
                ),
                working_set=envelope.working_set,
                notes=list(envelope.notes),
                blockers=list(envelope.blockers),
                created_at=datetime.now(UTC),
            )

        next_stage = self.stage_definition(next_role)
        return SwarmEnvelopeView(
            mission_id=envelope.mission_id,
            run_id=envelope.run_id,
            stage_index=next_stage.order,
            from_role="conductor",
            to_role=next_role,
            kind=envelope.kind,
            summary=envelope.summary,
            directive=SwarmDirectiveView(
                objective=objective or _objective_from_envelope(envelope),
                required_outputs=list(next_stage.produces),
                guardrails=[
                    "Use the active JSON bus envelope below as the only inter-role context.",
                    "Preserve accepted working-set sections outside your ownership.",
                    "Do not free-chat or impersonate another role.",
                    "Respond with structured JSON only.",
                    "Return one raw JSON object only.",
                ],
                exit_criteria=[
                    "Stay inside your isolation scope.",
                    "If you detect a cross-role conflict, record it in working_set.conflicts.",
                ],
            ),
            working_set=envelope.working_set,
            notes=list(envelope.notes),
            blockers=list(envelope.blockers),
            created_at=datetime.now(UTC),
        )

    def redirect_conflict(
        self,
        envelope: SwarmEnvelopeView,
        *,
        conflict: SwarmConflictView,
        objective: str,
    ) -> SwarmEnvelopeView:
        stage = self.stage_definition(envelope.from_role)
        return SwarmEnvelopeView(
            mission_id=envelope.mission_id,
            run_id=envelope.run_id,
            stage_index=stage.order,
            from_role="conductor",
            to_role=envelope.from_role,
            kind=envelope.kind,
            summary=conflict.summary,
            directive=SwarmDirectiveView(
                objective=objective,
                required_outputs=list(stage.produces),
                guardrails=[
                    "Resolve the named conflict before broadening scope.",
                    "Preserve accepted work outside your ownership.",
                    "Return one raw JSON object only.",
                ],
                exit_criteria=[
                    "Explain the conflict resolution in notes.",
                    "Remove stale conflict entries if they are resolved.",
                ],
            ),
            working_set=envelope.working_set,
            notes=list(_unique_preserve_order([*envelope.notes, conflict.summary])),
            blockers=list(envelope.blockers),
            created_at=datetime.now(UTC),
        )


def build_initial_swarm_runtime(
    *,
    objective: str,
    mission_id: int | None = None,
    run_id: str | None = None,
    constitution: SwarmConstitutionView | None = None,
) -> MissionSwarmRuntimeView:
    conductor = SwarmConductor(constitution)
    first_envelope = conductor.open_mission(
        objective=objective,
        mission_id=mission_id,
        run_id=run_id,
    )
    return MissionSwarmRuntimeView(
        enabled=True,
        constitution_version=conductor.constitution.version,
        run_id=first_envelope.run_id,
        status="ready",
        stage_index=first_envelope.stage_index,
        active_role=first_envelope.to_role,
        completed_roles=[],
        pending_roles=list(SWARM_EXECUTION_ROLE_ORDER),
        active_envelope=first_envelope,
        working_set=first_envelope.working_set,
    )


def is_swarm_collaboration_mode(mode: str | None) -> bool:
    return str(mode or "").strip().lower() == SWARM_COLLABORATION_MODE


def build_swarm_turn_prompt(
    *,
    mission_name: str,
    runtime: MissionSwarmRuntimeView,
    constitution: SwarmConstitutionView | None = None,
) -> str:
    if runtime.active_role is None or runtime.active_envelope is None:
        raise ValueError("Swarm runtime is missing an active role envelope.")

    conductor = SwarmConductor(constitution)
    role = runtime.active_role
    role_definition = conductor.role_definition(role)
    stage_definition = conductor.stage_definition(role)
    envelope_json = json.dumps(
        runtime.active_envelope.model_dump(mode="json", exclude_none=True),
        indent=2,
        sort_keys=True,
    )
    role_specific_lines: list[str] = []
    if role == "product_manager":
        role_specific_lines.extend(
            [
                "- Clarify operator value, scope-in, scope-out, and acceptance criteria.",
                "- Do not propose implementation details unless they are unavoidable constraints.",
            ]
        )
    elif role == "architect":
        role_specific_lines.extend(
            [
                "- Name exact file seams, data contracts, and system boundaries.",
                "- Do not start editing code in this stage.",
            ]
        )
    elif role == "test_engineer":
        role_specific_lines.extend(
            [
                "- Define or add the highest-value tests for the agreed seam.",
                "- Report the exact checks the implementation stages must satisfy.",
            ]
        )
    elif role in {"backend_engineer", "frontend_engineer"}:
        role_specific_lines.extend(
            [
                "- Implement the owned slice now when the envelope is concrete enough.",
                "- Report every touched file and every verification step you ran.",
            ]
        )
    elif role == "security_auditor":
        role_specific_lines.extend(
            [
                "- Review the changed surfaces for auth, secrets, permissions, and misuse paths.",
                "- If you disagree with a prior stage, add a structured conflict entry.",
            ]
        )
    elif role == "refactorer":
        role_specific_lines.extend(
            [
                "- Refactor only after preserving behavior and accepted contracts.",
                "- Keep cleanup local and report any invariants you relied on.",
            ]
        )
    elif role == "integration_tester":
        role_specific_lines.extend(
            [
                "- Run the tightest meaningful end-to-end checks for the seam.",
                "- The mission only completes if failing_checks and blockers are both empty.",
            ]
        )

    lines = [
        (
            f"You are the {role_definition.label} inside the OpenZues Swarm Constitution "
            f"for mission '{mission_name}'."
        ),
        role_definition.system_prompt,
        "",
        "Swarm Constitution rules:",
        "- Never free-chat with another role.",
        "- The active JSON bus envelope below is the only inter-role context you may consume.",
        "- Stay inside your isolation scope and preserve accepted work outside your ownership.",
        "- Return one raw JSON object only. No markdown fences. No prose before or after it.",
        (
            f"- Your output must set `from_role` to `{role}`, `to_role` to `conductor`, "
            f"`run_id` to `{runtime.run_id}`, and `stage_index` to {runtime.stage_index}."
        ),
        (
            "- Your `kind` must be one of: "
            + ", ".join(f"`{kind}`" for kind in stage_definition.produces)
            + "."
        ),
        (
            "- If you detect a true cross-role disagreement, record it in "
            "`working_set.conflicts` and explain it in `notes` or `blockers`."
        ),
        "- Keep previously accepted working-set sections unless your owned stage updates them.",
        "",
        f"Isolation scope: {role_definition.isolation_scope.replace('_', ' ')}.",
        "Stage-specific duties:",
        *role_specific_lines,
        "",
        "Active envelope JSON:",
        envelope_json,
    ]
    return "\n".join(lines).strip()


def _first_conflict(
    working_set: SwarmWorkingSetView,
    *,
    mission_name: str,
    role: SwarmRole,
    envelope: SwarmEnvelopeView,
) -> MissionSwarmConflictView | None:
    detected = detect_swarm_conflicts(working_set)
    if not detected:
        return None
    conflict = detected[0]
    conductor = SwarmConductor()
    corrective_envelope = conductor.redirect_conflict(
        envelope,
        conflict=conflict,
        objective=_objective_from_envelope(envelope),
    )
    prompt = build_swarm_turn_prompt(
        mission_name=mission_name,
        runtime=MissionSwarmRuntimeView(
            enabled=True,
            constitution_version=conductor.constitution.version,
            run_id=envelope.run_id,
            status="conflicted",
            stage_index=corrective_envelope.stage_index,
            active_role=role,
            pending_roles=[],
            active_envelope=corrective_envelope,
            working_set=corrective_envelope.working_set,
        ),
        constitution=conductor.constitution,
    )
    return MissionSwarmConflictView(
        reason=conflict.reason,
        summary=conflict.summary,
        roles=list(conflict.roles),
        prompt=prompt,
        detected_at=_utcnow_text(),
        recommended_reflex=conflict.recommended_reflex,
    )


def _swarm_checkpoint_summary(envelope: SwarmEnvelopeView) -> str:
    return json.dumps(
        envelope.model_dump(mode="json", exclude_none=True),
        indent=2,
        sort_keys=True,
    )


def _swarm_final_summary(runtime: MissionSwarmRuntimeView) -> str:
    working_set = runtime.working_set
    report = working_set.integration_report
    lines = [
        "Swarm pipeline completed.",
    ]
    if working_set.product_spec is not None:
        lines.append(f"Problem: {working_set.product_spec.problem}")
    if working_set.architecture_plan is not None:
        lines.append(f"Architecture: {working_set.architecture_plan.headline}")
    if report is not None and report.verified_checks:
        lines.append("Verified:")
        lines.extend(f"- {check}" for check in report.verified_checks[:6])
    if working_set.security_review is not None and working_set.security_review.required_repairs:
        lines.append("Security repairs:")
        lines.extend(
            f"- {repair}" for repair in working_set.security_review.required_repairs[:4]
        )
    return "\n".join(lines)


def advance_swarm_runtime(
    runtime: MissionSwarmRuntimeView,
    envelope: SwarmEnvelopeView,
    *,
    mission_name: str,
    constitution: SwarmConstitutionView | None = None,
) -> SwarmAdvanceResult:
    conductor = SwarmConductor(constitution)
    merged_working_set = merge_working_set(runtime.working_set, envelope.working_set)
    normalized_envelope = envelope.model_copy(update={"working_set": merged_working_set})
    conflict = _first_conflict(
        merged_working_set,
        mission_name=mission_name,
        role=envelope.from_role,
        envelope=normalized_envelope,
    )
    completed_roles = _unique_preserve_order([*runtime.completed_roles, envelope.from_role])

    if conflict is not None:
        corrective_envelope = conductor.redirect_conflict(
            normalized_envelope,
            conflict=SwarmConflictView(
                reason=conflict.reason,
                summary=conflict.summary,
                roles=list(conflict.roles),
                recommended_reflex=conflict.recommended_reflex,
            ),
            objective=_objective_from_envelope(normalized_envelope),
        )
        updated = runtime.model_copy(
            update={
                "status": "conflicted",
                "stage_index": corrective_envelope.stage_index,
                "active_role": corrective_envelope.to_role,
                "completed_roles": completed_roles,
                "pending_roles": [
                    role for role in SWARM_EXECUTION_ROLE_ORDER if role not in completed_roles
                ],
                "last_payload_kind": normalized_envelope.kind,
                "last_output_summary": normalized_envelope.summary,
                "active_envelope": corrective_envelope,
                "working_set": merged_working_set,
                "conflict": conflict,
            }
        )
        return SwarmAdvanceResult(
            status="conflicted",
            state=updated,
            checkpoint_kind="swarm_conflict",
            checkpoint_summary=_swarm_checkpoint_summary(normalized_envelope),
            blocking_summary=conflict.summary,
        )

    if envelope.from_role == "integration_tester":
        report = merged_working_set.integration_report
        has_blockers = bool(report and (report.failing_checks or report.blockers))
        if has_blockers:
            integration_summary = (
                report.recommended_action
                if report is not None and report.recommended_action
                else "Integration verification still has failing checks or blockers."
            )
            corrective_envelope = conductor.redirect_conflict(
                normalized_envelope,
                conflict=SwarmConflictView(
                    reason="integration_break",
                    summary=integration_summary,
                    roles=["integration_tester"],
                ),
                objective=_objective_from_envelope(normalized_envelope),
            )
            updated = runtime.model_copy(
                update={
                    "status": "blocked",
                    "stage_index": corrective_envelope.stage_index,
                    "active_role": corrective_envelope.to_role,
                    "completed_roles": completed_roles,
                    "pending_roles": [
                        role
                        for role in SWARM_EXECUTION_ROLE_ORDER
                        if role not in completed_roles
                    ],
                    "last_payload_kind": normalized_envelope.kind,
                    "last_output_summary": normalized_envelope.summary,
                    "active_envelope": corrective_envelope,
                    "working_set": merged_working_set,
                    "conflict": None,
                }
            )
            return SwarmAdvanceResult(
                status="blocked",
                state=updated,
                checkpoint_kind="swarm_integration",
                checkpoint_summary=_swarm_checkpoint_summary(normalized_envelope),
                blocking_summary=integration_summary,
            )

        updated = runtime.model_copy(
            update={
                "status": "completed",
                "stage_index": envelope.stage_index,
                "active_role": None,
                "completed_roles": completed_roles,
                "pending_roles": [],
                "last_payload_kind": normalized_envelope.kind,
                "last_output_summary": normalized_envelope.summary,
                "active_envelope": None,
                "working_set": merged_working_set,
                "conflict": None,
            }
        )
        return SwarmAdvanceResult(
            status="completed",
            state=updated,
            checkpoint_kind="swarm_final",
            checkpoint_summary=_swarm_checkpoint_summary(normalized_envelope),
            final_summary=_swarm_final_summary(updated),
        )

    next_envelope = conductor.route(
        normalized_envelope,
        objective=_objective_from_envelope(normalized_envelope),
    )
    updated = runtime.model_copy(
        update={
            "status": "ready",
            "stage_index": next_envelope.stage_index,
            "active_role": next_envelope.to_role,
            "completed_roles": completed_roles,
            "pending_roles": [
                role for role in SWARM_EXECUTION_ROLE_ORDER if role not in completed_roles
            ],
            "last_payload_kind": normalized_envelope.kind,
            "last_output_summary": normalized_envelope.summary,
            "active_envelope": next_envelope,
            "working_set": merged_working_set,
            "conflict": None,
        }
    )
    return SwarmAdvanceResult(
        status="advanced",
        state=updated,
        checkpoint_kind="swarm_payload",
        checkpoint_summary=_swarm_checkpoint_summary(normalized_envelope),
    )
