from __future__ import annotations

from openzues.schemas import (
    SwarmAcceptanceCriterionView,
    SwarmEnvelopeView,
    SwarmProductSpecView,
    SwarmWorkingSetView,
)
from openzues.services.swarm import SWARM_ROLE_ORDER, SwarmConductor, build_swarm_constitution


def test_swarm_constitution_defines_json_bus_and_nine_roles() -> None:
    constitution = build_swarm_constitution()

    assert constitution.routing_mode == "json_bus"
    assert constitution.no_free_chat is True
    assert constitution.pause_on_conflict is True
    assert [stage.role for stage in constitution.stages] == list(SWARM_ROLE_ORDER)


def test_swarm_conductor_routes_product_spec_to_architect_via_internal_bus() -> None:
    conductor = SwarmConductor()
    pm_output = SwarmEnvelopeView(
        mission_id=42,
        run_id="swarm-run-42",
        stage_index=1,
        from_role="product_manager",
        to_role="conductor",
        kind="product_spec",
        summary="Product spec for native nine-role swarm orchestration is ready.",
        working_set=SwarmWorkingSetView(
            product_spec=SwarmProductSpecView(
                problem=(
                    "OpenZues needs a native nine-role swarm pipeline that never relies on "
                    "free-chat between agents."
                ),
                user_outcomes=[
                    "A single mission can advance through the full swarm pipeline.",
                    "Each handoff is checkpointable and recoverable through SQLite state.",
                ],
                scope_in=[
                    "Native role constitution",
                    "Structured JSON bus handoffs",
                    "Mission-level sequential routing",
                ],
                scope_out=[
                    "External agent frameworks",
                    "Unstructured role-to-role chat",
                ],
                acceptance_criteria=[
                    SwarmAcceptanceCriterionView(
                        id="ac-json-bus",
                        summary="The conductor forwards the PM spec to the Architect as JSON.",
                        owner="architect",
                    )
                ],
            )
        ),
    )

    architect_handoff = conductor.route(pm_output)

    assert architect_handoff.from_role == "conductor"
    assert architect_handoff.to_role == "architect"
    assert architect_handoff.kind == "product_spec"
    assert architect_handoff.directive is not None
    assert architect_handoff.working_set.product_spec is not None
    assert any(
        "structured json only" in guardrail.lower()
        for guardrail in architect_handoff.directive.guardrails
    )
