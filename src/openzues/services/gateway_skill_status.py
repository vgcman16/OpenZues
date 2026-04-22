from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

from openzues.services.gateway_skill_config import GatewaySkillConfigService

_FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(?P<frontmatter>.*?)\r?\n---\s*\r?\n?", re.DOTALL)
_PLATFORM_ALIASES = {
    "windows": {"windows", "win32"},
    "macos": {"macos", "darwin"},
    "linux": {"linux"},
}


def _default_codex_home() -> Path:
    configured = os.getenv("CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex"


def _current_platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _string_list(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        normalized = value.strip()
        return (normalized,) if normalized else ()
    if not isinstance(value, list):
        return ()
    items: list[str] = []
    for entry in value:
        normalized = str(entry or "").strip()
        if normalized:
            items.append(normalized)
    return tuple(items)


def _required_environment_variables(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        names: list[str] = []
        for entry in value:
            if isinstance(entry, dict):
                normalized = str(entry.get("name") or "").strip()
            else:
                normalized = str(entry or "").strip()
            if normalized:
                names.append(normalized)
        return tuple(names)
    return ()


def _frontmatter_payload(skill_path: Path) -> dict[str, Any]:
    try:
        text = skill_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return {}
    payload = yaml.safe_load(match.group("frontmatter")) or {}
    return payload if isinstance(payload, dict) else {}


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _platform_matches_current(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in _PLATFORM_ALIASES[_current_platform()]


def _build_config_checks(
    required: list[str],
    *,
    skill_config_service: GatewaySkillConfigService,
    config_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "path": path,
            "satisfied": skill_config_service.is_config_path_truthy(
                path,
                payload=config_payload,
            ),
        }
        for path in required
    ]


def _is_configured_secret(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value)
    return False


def _configured_environment_names(
    config_entry: dict[str, Any] | None,
    *,
    primary_env: str | None,
) -> set[str]:
    if not isinstance(config_entry, dict):
        return set()
    configured: set[str] = set()
    entry_env = config_entry.get("env")
    if isinstance(entry_env, dict):
        for raw_name, raw_value in entry_env.items():
            normalized_name = str(raw_name or "").strip()
            if not normalized_name:
                continue
            if isinstance(raw_value, str):
                if raw_value.strip():
                    configured.add(normalized_name)
                continue
            if raw_value:
                configured.add(normalized_name)
    if primary_env and _is_configured_secret(config_entry.get("apiKey")):
        configured.add(primary_env)
    return configured


def _missing_environment_variables(
    required: list[str],
    *,
    config_entry: dict[str, Any] | None,
    primary_env: str | None,
) -> list[str]:
    configured_names = _configured_environment_names(
        config_entry,
        primary_env=primary_env,
    )
    return [
        env_name
        for env_name in required
        if not os.getenv(env_name) and env_name not in configured_names
    ]


class GatewaySkillStatusService:
    def __init__(
        self,
        *,
        codex_home: Path | None = None,
        workspace_root: Path | None = None,
        skill_config_service: GatewaySkillConfigService | None = None,
    ) -> None:
        self.codex_home = (codex_home or _default_codex_home()).expanduser()
        self.workspace_root = (workspace_root or Path.cwd()).expanduser()
        self._skill_config_service = skill_config_service or GatewaySkillConfigService(
            codex_home=self.codex_home,
            workspace_root=self.workspace_root,
        )

    def build_report(self, *, agent_id: str | None = None) -> dict[str, Any]:
        del agent_id
        skill_entries = self._skill_config_service.load_entries()
        config_payload = self._skill_config_service.load_payload()
        skills = [
            self._build_skill_payload(
                skill_path,
                source=source,
                bundled=bundled,
                skill_entries=skill_entries,
                config_payload=config_payload,
            )
            for skill_path, source, bundled in self._iter_skill_paths()
        ]
        skills.sort(key=lambda entry: str(entry["name"]).lower())
        return {
            "workspaceDir": str(self.workspace_root),
            "managedSkillsDir": str(self.codex_home / "skills"),
            "skills": skills,
        }

    def _build_skill_payload(
        self,
        skill_path: Path,
        *,
        source: str,
        bundled: bool,
        skill_entries: dict[str, dict[str, Any]],
        config_payload: dict[str, Any],
    ) -> dict[str, Any]:
        frontmatter = _frontmatter_payload(skill_path)
        metadata = frontmatter.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        requires = metadata.get("requires")
        requires = requires if isinstance(requires, dict) else {}

        name = (
            str(frontmatter.get("name") or skill_path.parent.name).strip()
            or skill_path.parent.name
        )
        description = str(frontmatter.get("description") or "").strip()
        skill_key = (
            str(metadata.get("skillKey") or skill_path.parent.name).strip()
            or skill_path.parent.name
        )
        config_entry = skill_entries.get(skill_key)
        required_bins = list(_string_list(requires.get("bins")))
        any_bins = list(_string_list(requires.get("anyBins")))
        required_env = list(_string_list(requires.get("env")))
        if not required_env:
            required_env = list(
                _required_environment_variables(frontmatter.get("required_environment_variables"))
            )
        required_config = list(_string_list(requires.get("config")))
        required_os = _ordered_unique(
            [
                *_string_list(frontmatter.get("platforms")),
                *_string_list(metadata.get("os")),
            ]
        )
        always = bool(metadata.get("always") is True)
        primary_env = str(metadata.get("primaryEnv") or "").strip() or (
            required_env[0] if required_env else None
        )

        missing_bins = [bin_name for bin_name in required_bins if shutil.which(bin_name) is None]
        if any_bins and not any(shutil.which(bin_name) is not None for bin_name in any_bins):
            missing_bins.extend(bin_name for bin_name in any_bins if bin_name not in missing_bins)
        missing_env = _missing_environment_variables(
            required_env,
            config_entry=config_entry,
            primary_env=primary_env,
        )
        config_checks = _build_config_checks(
            required_config,
            skill_config_service=self._skill_config_service,
            config_payload=config_payload,
        )
        missing_config = [check["path"] for check in config_checks if not check["satisfied"]]
        missing_os = (
            list(required_os)
            if required_os and not any(_platform_matches_current(value) for value in required_os)
            else []
        )
        disabled = bool(metadata.get("disabled") is True or metadata.get("enabled") is False)
        if isinstance(config_entry, dict) and isinstance(config_entry.get("enabled"), bool):
            disabled = not bool(config_entry["enabled"])
        if always:
            missing_bins = []
            missing_env = []
            missing_config = []
            missing_os = []
        eligible = not disabled and (
            always or not (missing_bins or missing_env or missing_config or missing_os)
        )

        return {
            "name": name,
            "description": description,
            "source": source,
            "bundled": bundled,
            "filePath": str(skill_path),
            "baseDir": str(skill_path.parent),
            "skillKey": skill_key,
            "primaryEnv": primary_env,
            "emoji": str(metadata.get("emoji") or "").strip() or None,
            "homepage": str(metadata.get("homepage") or "").strip() or None,
            "always": always,
            "disabled": disabled,
            "blockedByAllowlist": False,
            "eligible": eligible,
            "requirements": {
                "bins": _ordered_unique([*required_bins, *any_bins]),
                "env": _ordered_unique(required_env),
                "config": _ordered_unique(required_config),
                "os": required_os,
            },
            "missing": {
                "bins": _ordered_unique(missing_bins),
                "env": _ordered_unique(missing_env),
                "config": _ordered_unique(missing_config),
                "os": _ordered_unique(missing_os),
            },
            "configChecks": config_checks,
            "install": self._install_options(metadata.get("install"), default_label=name),
        }

    def _install_options(self, value: object, *, default_label: str) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        options: list[dict[str, Any]] = []
        for index, entry in enumerate(value):
            if not isinstance(entry, dict):
                continue
            install_os = _string_list(entry.get("os"))
            if install_os and not any(_platform_matches_current(item) for item in install_os):
                continue
            kind = str(entry.get("kind") or "").strip() or "custom"
            install_id = str(entry.get("id") or f"{kind}-{index}").strip() or f"{kind}-{index}"
            label = str(entry.get("label") or "").strip() or f"Install {default_label}"
            options.append(
                {
                    "id": install_id,
                    "kind": kind,
                    "label": label,
                    "bins": list(_string_list(entry.get("bins"))),
                }
            )
        return options

    def _iter_skill_paths(self) -> list[tuple[Path, str, bool]]:
        candidates: tuple[tuple[Path, str, bool], ...] = (
            (self.codex_home / "skills", "codex-home", True),
            (self.codex_home / "plugins" / "cache", "plugin-cache", True),
            (self.workspace_root / ".codex" / "skills", "workspace-codex", False),
            (self.workspace_root / "skills", "workspace", False),
        )
        discovered: list[tuple[Path, str, bool]] = []
        seen: set[str] = set()
        for root, source, bundled in candidates:
            if not root.exists():
                continue
            for skill_path in root.rglob("SKILL.md"):
                identity = str(skill_path.resolve(strict=False))
                if identity in seen:
                    continue
                seen.add(identity)
                discovered.append((skill_path, source, bundled))
        return discovered
