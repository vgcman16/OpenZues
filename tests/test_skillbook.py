from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from openzues.services.ecc_catalog import configure_ecc_catalog
from openzues.services.hermes_skills import configure_hermes_skill_catalog
from openzues.services.skillbook import (
    SkillInstruction,
    build_prompt_skill_lines,
    materialize_skillbook_pins,
)


def _write_fake_hermes_skill(
    repo_root: Path,
    *,
    relative_dir: str,
    name: str,
    description: str,
    category: str,
    tags: list[str],
    requires_toolsets: list[str] | None = None,
    fallback_for_toolsets: list[str] | None = None,
) -> Path:
    skill_dir = repo_root / relative_dir
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {description}",
                "metadata:",
                "  hermes:",
                f"    category: {category}",
                f"    tags: [{', '.join(tags)}]",
                *(
                    [f"    requires_toolsets: [{', '.join(requires_toolsets)}]"]
                    if requires_toolsets
                    else []
                ),
                *(
                    [f"    fallback_for_toolsets: [{', '.join(fallback_for_toolsets)}]"]
                    if fallback_for_toolsets
                    else []
                ),
                "---",
                "",
                f"# {name}",
                "",
                "## When to Use",
                "Use when the workflow needs this skill.",
                "",
                "## Procedure",
                "1. Load the skill.",
                "2. Follow the process.",
            ]
        ),
        encoding="utf-8",
    )
    return skill_path


@pytest.fixture(autouse=True)
def _reset_hermes_catalog() -> Generator[None, None, None]:
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)
    yield
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)


def _write_fake_ecc_skill(
    repo_root: Path,
    *,
    relative_dir: str,
    name: str,
    description: str,
) -> Path:
    skill_dir = repo_root / relative_dir
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {description}",
                "origin: ECC",
                "---",
                "",
                f"# {name}",
                "",
                "## When to Use",
                "Use this ECC skill when the workflow needs the documented steps.",
                "",
                "## Procedure",
                "1. Open the skill.",
                "2. Follow the workflow.",
            ]
        ),
        encoding="utf-8",
    )
    return skill_path


def test_materialize_skillbook_pins_auto_attaches_matching_hermes_skill(tmp_path: Path) -> None:
    hermes_root = tmp_path / "hermes-agent-main"
    skill_path = _write_fake_hermes_skill(
        hermes_root,
        relative_dir="skills/research/arxiv-research",
        name="ArXiv Research",
        description="Search arXiv papers, summarize findings, and track citations for the topic",
        category="research",
        tags=["research", "arxiv", "papers", "citations"],
    )
    configure_hermes_skill_catalog(hermes_root)

    pins = materialize_skillbook_pins(
        7,
        "Research arxiv papers, summarize the evidence, and cite the strongest findings.",
        explicit_pins=[],
        project_label="OpenZues Workspace",
        project_path=str(tmp_path),
    )

    assert any(pin.name == "ArXiv Research" for pin in pins)
    hermes_pin = next(pin for pin in pins if pin.name == "ArXiv Research")
    assert hermes_pin.id < 0
    assert hermes_pin.source == str(skill_path)
    assert "Read the linked Hermes SKILL.md" in hermes_pin.prompt_hint


def test_build_prompt_skill_lines_tells_zues_to_open_source_skill_files(
    tmp_path: Path,
) -> None:
    skill_file = tmp_path / "hermes-ui-review" / "SKILL.md"
    skill_file.parent.mkdir(parents=True, exist_ok=True)
    skill_file.write_text("# Hermes UI Review\n", encoding="utf-8")

    lines = build_prompt_skill_lines(
        [
            SkillInstruction(
                name="Hermes UI Review",
                prompt_hint=(
                    "Tighten the UI hierarchy and read the skill file before following the "
                    "workflow."
                ),
                source=str(skill_file),
                auto_attached=True,
            )
        ]
    )

    assert lines
    assert any(
        "open that SKILL.md before you execute the related workflow" in line for line in lines
    )
    assert any("Apply the skillbook directly" in line for line in lines)


def test_materialize_skillbook_pins_respects_active_hermes_toolsets(tmp_path: Path) -> None:
    hermes_root = tmp_path / "hermes-agent-main"
    _write_fake_hermes_skill(
        hermes_root,
        relative_dir="skills/browser/browser-verify",
        name="Browser Verify",
        description="Verify the rendered UI in a browser session.",
        category="frontend",
        tags=["browser", "ui", "verify"],
        requires_toolsets=["browser"],
    )
    configure_hermes_skill_catalog(hermes_root)

    without_browser = materialize_skillbook_pins(
        7,
        "Verify the browser UI after the dashboard change.",
        explicit_pins=[],
        project_label="OpenZues Workspace",
        project_path=str(tmp_path),
        toolsets=["terminal", "debugging"],
    )
    with_browser = materialize_skillbook_pins(
        7,
        "Verify the browser UI after the dashboard change.",
        explicit_pins=[],
        project_label="OpenZues Workspace",
        project_path=str(tmp_path),
        toolsets=["browser", "debugging"],
    )

    assert not any(pin.name == "Browser Verify" for pin in without_browser)
    assert any(pin.name == "Browser Verify" for pin in with_browser)


def test_materialize_skillbook_pins_auto_attaches_matching_ecc_skill(tmp_path: Path) -> None:
    ecc_root = tmp_path / "everything-claude-code-main"
    skill_path = _write_fake_ecc_skill(
        ecc_root,
        relative_dir="skills/workspace-surface-audit",
        name="workspace-surface-audit",
        description="Audit the project harness surface, installed skills, and Codex-facing config.",
    )
    configure_ecc_catalog(ecc_root)

    pins = materialize_skillbook_pins(
        11,
        "Audit the workspace surface, inspect the Codex config, and summarize the harness state.",
        explicit_pins=[],
        project_label="ECC Workspace",
        project_path=str(ecc_root),
    )

    assert any(pin.name == "workspace-surface-audit" for pin in pins)
    ecc_pin = next(pin for pin in pins if pin.name == "workspace-surface-audit")
    assert ecc_pin.id < 0
    assert ecc_pin.source == str(skill_path)
    assert "Read the linked ECC SKILL.md" in ecc_pin.prompt_hint
