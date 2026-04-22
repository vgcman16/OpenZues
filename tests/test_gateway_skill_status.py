from __future__ import annotations

import json
from pathlib import Path

from openzues.services.gateway_skill_status import GatewaySkillStatusService


def _write_skill(skill_dir: Path, frontmatter_lines: list[str]) -> Path:
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(
        "\n".join([*frontmatter_lines, "", "# Test Skill", "", "Skill body."]) + "\n",
        encoding="utf-8",
    )
    return skill_path


def _skill_report_by_name(report: dict[str, object], name: str) -> dict[str, object]:
    skills = report.get("skills")
    assert isinstance(skills, list)
    for skill in skills:
        if isinstance(skill, dict) and skill.get("name") == name:
            return skill
    raise AssertionError(f"skill {name!r} not found in report")


def test_build_report_uses_configured_env_and_api_key_for_eligibility(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    _write_skill(
        workspace_root / "skills" / "hosted-search",
        [
            "---",
            "name: Hosted Search",
            "description: Search with a provider-backed API.",
            "metadata:",
            "  skillKey: hosted-search",
            "  primaryEnv: SEARCH_API_KEY",
            "  requires:",
            "    env: [SEARCH_API_KEY, SEARCH_REGION]",
            "    config: [features.search.enabled]",
            "---",
        ],
    )

    config_path = workspace_root / ".codex" / "gateway-skill-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "features": {"search": {"enabled": True}},
                "skills": {
                    "entries": {
                        "hosted-search": {
                            "apiKey": "secret-token",
                            "env": {"SEARCH_REGION": "us"},
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    report = GatewaySkillStatusService(workspace_root=workspace_root).build_report()
    skill = _skill_report_by_name(report, "Hosted Search")

    assert skill["primaryEnv"] == "SEARCH_API_KEY"
    assert skill["eligible"] is True
    assert skill["missing"] == {"bins": [], "env": [], "config": [], "os": []}
    assert skill["configChecks"] == [{"path": "features.search.enabled", "satisfied": True}]


def test_build_report_preserves_primary_env_without_requires_env(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    _write_skill(
        workspace_root / "skills" / "primary-only",
        [
            "---",
            "name: Primary Only",
            "description: Advertise an api-key-backed skill.",
            "metadata:",
            "  primaryEnv: PRIMARY_ONLY_API_KEY",
            "---",
        ],
    )

    report = GatewaySkillStatusService(workspace_root=workspace_root).build_report()
    skill = _skill_report_by_name(report, "Primary Only")

    assert skill["primaryEnv"] == "PRIMARY_ONLY_API_KEY"


def test_build_report_always_skips_missing_requirements(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    _write_skill(
        workspace_root / "skills" / "always-on",
        [
            "---",
            "name: Always On",
            "description: Remains visible regardless of host readiness.",
            "platforms: [darwin]",
            "metadata:",
            "  always: true",
            "  requires:",
            "    bins: [definitely-missing-bin]",
            "    env: [MISSING_ENV_VAR]",
            "    config: [features.always.enabled]",
            "---",
        ],
    )

    report = GatewaySkillStatusService(workspace_root=workspace_root).build_report()
    skill = _skill_report_by_name(report, "Always On")

    assert skill["always"] is True
    assert skill["eligible"] is True
    assert skill["missing"] == {"bins": [], "env": [], "config": [], "os": []}
