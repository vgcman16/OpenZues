from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(?P<frontmatter>.*?)\r?\n---\s*\r?\n?", re.DOTALL)


def _default_codex_home() -> Path:
    configured = os.getenv("CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex"


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    items: list[str] = []
    for entry in value:
        normalized = str(entry or "").strip()
        if normalized:
            items.append(normalized)
    return tuple(items)


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


def _skill_bins(skill_path: Path) -> tuple[str, ...]:
    frontmatter = _frontmatter_payload(skill_path)
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict):
        return ()
    bins: list[str] = []
    requires = metadata.get("requires")
    if isinstance(requires, dict):
        bins.extend(_string_list(requires.get("bins")))
        bins.extend(_string_list(requires.get("anyBins")))
    install = metadata.get("install")
    if isinstance(install, list):
        for entry in install:
            if isinstance(entry, dict):
                bins.extend(_string_list(entry.get("bins")))
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in bins:
        if entry in seen:
            continue
        seen.add(entry)
        ordered.append(entry)
    return tuple(ordered)


class GatewaySkillBinsService:
    def __init__(
        self,
        *,
        codex_home: Path | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self.codex_home = (codex_home or _default_codex_home()).expanduser()
        self.workspace_root = (workspace_root or Path.cwd()).expanduser()

    def list_bins(self) -> list[str]:
        bins: set[str] = set()
        for skill_path in self._iter_skill_paths():
            bins.update(_skill_bins(skill_path))
        return sorted(bins)

    def _iter_skill_paths(self) -> list[Path]:
        candidates = (
            self.codex_home / "skills",
            self.codex_home / "plugins" / "cache",
            self.workspace_root / ".codex" / "skills",
            self.workspace_root / "skills",
        )
        discovered: list[Path] = []
        seen: set[str] = set()
        for root in candidates:
            if not root.exists():
                continue
            for skill_path in root.rglob("SKILL.md"):
                identity = str(skill_path.resolve(strict=False))
                if identity in seen:
                    continue
                seen.add(identity)
                discovered.append(skill_path)
        return discovered
