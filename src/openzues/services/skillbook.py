from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from openzues.schemas import SkillPinView
from openzues.services.ecc_catalog import resolve_ecc_skill_matches
from openzues.services.hermes_skills import (
    is_local_skill_source_available,
    resolve_hermes_skill_matches,
)
from openzues.services.hermes_toolsets import expand_hermes_toolsets

_BUILTIN_SOURCE_ROOT = "builtin:openzues-claw-parity"
_REASONING_RANK = {"low": 1, "medium": 2, "high": 3, "xhigh": 4}


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _skill_identity(name: str | None, source: str | None = None) -> tuple[str, str]:
    return (_normalize_text(name), _normalize_text(source))


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


@dataclass(frozen=True, slots=True)
class SkillInstruction:
    name: str
    prompt_hint: str
    source: str | None = None
    auto_attached: bool = False


@dataclass(frozen=True, slots=True)
class SkillProfile:
    skills: tuple[SkillInstruction, ...] = ()
    reasoning_effort: str | None = None
    max_turns_floor: int | None = None


@dataclass(frozen=True, slots=True)
class _BuiltinSkillSpec:
    slug: str
    name: str
    prompt_hint: str
    source: str
    triggers: tuple[str, ...]
    reasoning_effort: str | None = None
    max_turns_floor: int | None = None


_SUPERHUMAN_SKILL = _BuiltinSkillSpec(
    slug="superhuman",
    name="Superhuman Skill",
    prompt_hint=(
        "Start by mapping the current truth, break the objective into concrete milestones, "
        "pick the highest-leverage path, and keep the plan updated as evidence changes."
    ),
    source=f"{_BUILTIN_SOURCE_ROOT}/superhuman-skill",
    triggers=(
        "plan",
        "planning",
        "project",
        "roadmap",
        "milestone",
        "scope",
        "architecture",
        "inventory",
        "parity",
        "system",
        "platform",
        "workflow",
        "build",
        "ship",
        "implement",
    ),
    reasoning_effort="high",
)
_LOOP_SKILL = _BuiltinSkillSpec(
    slug="loop",
    name="Loop Skill",
    prompt_hint=(
        "Work in tight improvement loops: inspect, change, verify, checkpoint, and repeat. "
        "Keep only the highest-leverage step in flight and stop cleanly when the next step "
        "turns speculative."
    ),
    source=f"{_BUILTIN_SOURCE_ROOT}/loop-skill",
    triggers=(
        "continue",
        "keep ",
        "keep",
        "improve",
        "iterat",
        "loop",
        "autonomous",
        "until",
        "ongoing",
        "harden",
        "cook",
        "parity",
        "for days",
    ),
    max_turns_floor=8,
)
_FRONTEND_UI_PRO_SKILL = _BuiltinSkillSpec(
    slug="frontend-ui-pro",
    name="Front-end / UX UI Pro Skill",
    prompt_hint=(
        "When the work touches product UI, raise hierarchy, spacing, copy, interaction flow, "
        "accessibility, responsiveness, and visual polish. Verify in-browser instead of "
        "trusting code alone."
    ),
    source=f"{_BUILTIN_SOURCE_ROOT}/front-end-ux-ui-pro-skill",
    triggers=(
        "ui",
        "ux",
        "frontend",
        "front-end",
        "design",
        "visual",
        "layout",
        "chat interface",
        "dashboard",
        "css",
        "responsive",
        "look cleaner",
        "look better",
        "polish",
        "web app",
        "website",
        "landing page",
        "template",
    ),
    reasoning_effort="high",
)
_CONTROL_PLANE_CONTRACT_GUARD_SKILL = _BuiltinSkillSpec(
    slug="control-plane-contract-guard",
    name="Control Plane Contract Guard",
    prompt_hint=(
        "Treat setup/onboarding/gateway/schema/dashboard work as a contract seam: keep "
        "database, schemas, services, API routes, CLI flows, payload builders, constructors, "
        "serializers, and shared test fixtures aligned in the same turn. Before trusting a "
        "checkpoint, rerun the focused contract pack: `.\\\\.venv\\\\Scripts\\\\python.exe -m "
        "pytest tests/test_app.py tests/test_database.py tests/test_manager.py "
        "tests/test_ops_mesh.py -q`, `node --check src/openzues/web/static/app.js`, and "
        "`.\\\\.venv\\\\Scripts\\\\python.exe -m compileall src/openzues`. If the seam changed "
        "dashboard or schema contracts, include a broader app/dashboard pass before calling it "
        "done."
    ),
    source=f"{_BUILTIN_SOURCE_ROOT}/control-plane-contract-guard",
    triggers=(
        "setup",
        "bootstrap",
        "onboarding",
        "quickstart",
        "gateway",
        "remote access",
        "launch profile",
        "default lane",
        "schema",
        "pydantic",
        "dashboard",
        "payload",
        "contract",
        "doctor",
        "endpoint",
        "api",
        "cli",
        "fixture",
        "constructor",
    ),
    reasoning_effort="high",
)
_BUILTIN_SKILL_SPECS = (
    _SUPERHUMAN_SKILL,
    _LOOP_SKILL,
    _FRONTEND_UI_PRO_SKILL,
    _CONTROL_PLANE_CONTRACT_GUARD_SKILL,
)


def _select_builtin_specs(
    objective: str | None,
    *,
    project_label: str | None = None,
    project_path: str | None = None,
    additional_context: str | None = None,
) -> list[_BuiltinSkillSpec]:
    objective_text = _normalize_text(objective)
    context = " ".join(
        part
        for part in (
            objective_text,
            _normalize_text(project_label),
            _normalize_text(project_path),
            _normalize_text(additional_context),
        )
        if part
    )
    if not context:
        return []

    loop_selected = _contains_any(context, _LOOP_SKILL.triggers)
    frontend_selected = _contains_any(context, _FRONTEND_UI_PRO_SKILL.triggers)
    control_plane_selected = _contains_any(
        context,
        _CONTROL_PLANE_CONTRACT_GUARD_SKILL.triggers,
    )
    superhuman_selected = (
        _contains_any(context, _SUPERHUMAN_SKILL.triggers)
        or loop_selected
        or frontend_selected
        or control_plane_selected
        or len(objective_text.split()) >= 6
    )

    selected: list[_BuiltinSkillSpec] = []
    if superhuman_selected:
        selected.append(_SUPERHUMAN_SKILL)
    if loop_selected:
        selected.append(_LOOP_SKILL)
    if frontend_selected:
        selected.append(_FRONTEND_UI_PRO_SKILL)
    if control_plane_selected:
        selected.append(_CONTROL_PLANE_CONTRACT_GUARD_SKILL)
    return selected


def _builtin_spec_for_skill(
    *,
    name: str | None,
    source: str | None,
) -> _BuiltinSkillSpec | None:
    name_key, source_key = _skill_identity(name, source)
    for spec in _BUILTIN_SKILL_SPECS:
        spec_name_key, spec_source_key = _skill_identity(spec.name, spec.source)
        if name_key and name_key == spec_name_key:
            return spec
        if source_key and source_key == spec_source_key:
            return spec
    return None


def _higher_reasoning_effort(
    current: str | None,
    candidate: str | None,
) -> str | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    if _REASONING_RANK.get(candidate, 0) > _REASONING_RANK.get(current, 0):
        return candidate
    return current


def resolve_skill_profile(
    objective: str | None,
    *,
    explicit_pins: Iterable[SkillPinView] = (),
    project_label: str | None = None,
    project_path: str | None = None,
    additional_context: str | None = None,
    toolsets: Iterable[str] = (),
) -> SkillProfile:
    all_pins = list(explicit_pins)
    enabled_pins = [pin for pin in all_pins if pin.enabled]
    blocked_identities = {
        _skill_identity(pin.name, pin.source)
        for pin in all_pins
        if pin.name or pin.source
    }
    instructions = [
        SkillInstruction(
            name=pin.name,
            prompt_hint=pin.prompt_hint,
            source=pin.source,
            auto_attached=False,
        )
        for pin in enabled_pins
    ]
    reasoning_effort: str | None = None
    max_turns_floor: int | None = None

    for pin in enabled_pins:
        builtin = _builtin_spec_for_skill(name=pin.name, source=pin.source)
        if builtin is None:
            continue
        reasoning_effort = _higher_reasoning_effort(reasoning_effort, builtin.reasoning_effort)
        if builtin.max_turns_floor is not None:
            max_turns_floor = max(max_turns_floor or 0, builtin.max_turns_floor)

    for spec in _select_builtin_specs(
        objective,
        project_label=project_label,
        project_path=project_path,
        additional_context=additional_context,
    ):
        if _skill_identity(spec.name, spec.source) in blocked_identities:
            continue
        instructions.append(
            SkillInstruction(
                name=spec.name,
                prompt_hint=spec.prompt_hint,
                source=spec.source,
                auto_attached=True,
            )
        )
        reasoning_effort = _higher_reasoning_effort(reasoning_effort, spec.reasoning_effort)
        if spec.max_turns_floor is not None:
            max_turns_floor = max(max_turns_floor or 0, spec.max_turns_floor)

    for hermes_skill in resolve_hermes_skill_matches(
        objective,
        project_label=project_label,
        project_path=project_path,
        additional_context=additional_context,
        active_toolsets=expand_hermes_toolsets(toolsets),
    ):
        if _skill_identity(hermes_skill.name, hermes_skill.source) in blocked_identities:
            continue
        instructions.append(
            SkillInstruction(
                name=hermes_skill.name,
                prompt_hint=hermes_skill.prompt_hint,
                source=hermes_skill.source,
                auto_attached=True,
            )
        )

    for ecc_skill in resolve_ecc_skill_matches(
        objective,
        project_label=project_label,
        project_path=project_path,
        additional_context=additional_context,
    ):
        if _skill_identity(ecc_skill.name, ecc_skill.source) in blocked_identities:
            continue
        instructions.append(
            SkillInstruction(
                name=ecc_skill.name,
                prompt_hint=ecc_skill.prompt_hint,
                source=ecc_skill.source,
                auto_attached=True,
            )
        )

    return SkillProfile(
        skills=tuple(instructions),
        reasoning_effort=reasoning_effort,
        max_turns_floor=max_turns_floor,
    )


def materialize_skillbook_pins(
    project_id: int,
    objective: str | None,
    *,
    explicit_pins: Iterable[SkillPinView] = (),
    project_label: str | None = None,
    project_path: str | None = None,
    additional_context: str | None = None,
    toolsets: Iterable[str] = (),
) -> list[SkillPinView]:
    pins = list(explicit_pins)
    enabled_identities = {
        _skill_identity(pin.name, pin.source)
        for pin in pins
        if pin.enabled and (pin.name or pin.source)
    }
    profile = resolve_skill_profile(
        objective,
        explicit_pins=pins,
        project_label=project_label,
        project_path=project_path,
        additional_context=additional_context,
        toolsets=toolsets,
    )
    auto_pins: list[SkillPinView] = []
    now = datetime.now(UTC)
    auto_offset = 1
    for skill in profile.skills:
        identity = _skill_identity(skill.name, skill.source)
        if identity in enabled_identities:
            continue
        auto_pins.append(
            SkillPinView(
                id=-((project_id or 0) * 100 + auto_offset),
                project_id=project_id,
                name=skill.name,
                prompt_hint=skill.prompt_hint,
                source=skill.source,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )
        auto_offset += 1
    return sorted(
        [*pins, *auto_pins],
        key=lambda pin: (pin.name.lower(), _normalize_text(pin.source)),
    )


def build_prompt_skill_lines(skills: Iterable[SkillInstruction]) -> list[str]:
    skill_list = list(skills)
    if not skill_list:
        return []
    lines = ["Mission skillbook:"]
    for skill in skill_list:
        line = f"- {skill.name}: {skill.prompt_hint}"
        if skill.source and not skill.source.startswith("builtin:"):
            line += f" Source: {skill.source}."
        lines.append(line)
    if any(is_local_skill_source_available(skill.source) for skill in skill_list):
        lines.append(
            "- When a skill includes a Source path, open that SKILL.md before you execute the "
            "related workflow so you inherit its procedure instead of guessing."
        )
    lines.append(
        "- Apply the skillbook directly when choosing the next step instead of waiting for a "
        "new operator instruction."
    )
    return lines
