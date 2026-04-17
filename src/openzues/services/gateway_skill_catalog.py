from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(?P<frontmatter>.*?)\r?\n---\s*\r?\n?", re.DOTALL)
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._/-]*")
_SLUG_PART_RE = re.compile(r"[^a-z0-9._-]+")


def _default_codex_home() -> Path:
    configured = os.getenv("CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex"


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


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


def _slug_part(value: str) -> str:
    normalized = _SLUG_PART_RE.sub("-", value.strip().lower()).strip("-")
    return normalized or "skill"


@dataclass(frozen=True, slots=True)
class GatewaySkillCatalogEntry:
    slug: str
    display_name: str
    summary: str | None
    version: str | None
    updated_at: int
    created_at: int
    tags: tuple[str, ...]
    os: tuple[str, ...]
    systems: tuple[str, ...]
    search_text: str


class GatewaySkillCatalogService:
    def __init__(
        self,
        *,
        codex_home: Path | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self.codex_home = (codex_home or _default_codex_home()).expanduser()
        self.workspace_root = (workspace_root or Path.cwd()).expanduser()

    def search(
        self,
        *,
        query: str | None = None,
        limit: int | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        del agent_id
        normalized_query = _normalize_text(query)
        results: list[dict[str, Any]] = []
        for entry in self._iter_entries():
            score = self._search_score(entry, normalized_query)
            if normalized_query and score <= 0.0:
                continue
            results.append(
                {
                    "score": score,
                    "slug": entry.slug,
                    "displayName": entry.display_name,
                    "summary": entry.summary,
                    "version": entry.version,
                    "updatedAt": entry.updated_at,
                }
            )
        resolved_limit = 20 if limit is None else limit
        results.sort(
            key=lambda item: (
                -float(item["score"]),
                str(item["displayName"]).lower(),
                str(item["slug"]),
            )
        )
        return {"results": results[:resolved_limit]}

    def detail(
        self,
        *,
        slug: str,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        del agent_id
        wanted_slug = slug.strip()
        for entry in self._iter_entries():
            if entry.slug != wanted_slug:
                continue
            skill_payload: dict[str, Any] = {
                "slug": entry.slug,
                "displayName": entry.display_name,
                "summary": entry.summary,
                "createdAt": entry.created_at,
                "updatedAt": entry.updated_at,
            }
            if entry.tags:
                skill_payload["tags"] = list(entry.tags)
            metadata: dict[str, Any] = {}
            if entry.os:
                metadata["os"] = list(entry.os)
            if entry.systems:
                metadata["systems"] = list(entry.systems)
            return {
                "skill": skill_payload,
                "latestVersion": (
                    {"version": entry.version, "createdAt": entry.created_at}
                    if entry.version is not None
                    else None
                ),
                "metadata": metadata or None,
                "owner": {
                    "handle": "local",
                    "displayName": "Local Skill Catalog",
                    "image": None,
                },
            }
        return {
            "skill": None,
            "latestVersion": None,
            "metadata": None,
            "owner": None,
        }

    def _iter_entries(self) -> list[GatewaySkillCatalogEntry]:
        entries: list[GatewaySkillCatalogEntry] = []
        seen: set[str] = set()
        for root, source in self._skill_roots():
            if not root.exists():
                continue
            for skill_path in root.rglob("SKILL.md"):
                identity = str(skill_path.resolve(strict=False))
                if identity in seen:
                    continue
                seen.add(identity)
                entries.append(self._build_entry(skill_path, root=root, source=source))
        entries.sort(key=lambda entry: (entry.display_name.lower(), entry.slug))
        return entries

    def _build_entry(
        self,
        skill_path: Path,
        *,
        root: Path,
        source: str,
    ) -> GatewaySkillCatalogEntry:
        frontmatter = _frontmatter_payload(skill_path)
        metadata = frontmatter.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        skill_dir = skill_path.parent
        relative_parts = [
            _slug_part(part)
            for part in skill_dir.relative_to(root).parts
            if str(part or "").strip()
        ]
        slug = "/".join(("local", source, *relative_parts))
        display_name = (
            str(frontmatter.get("name") or skill_dir.name).strip()
            or skill_dir.name
        )
        summary = str(frontmatter.get("description") or "").strip() or None
        version = str(frontmatter.get("version") or metadata.get("version") or "").strip() or None
        tags = _string_list(frontmatter.get("tags"))
        os_values = _string_list(frontmatter.get("platforms"))
        systems = _string_list(metadata.get("systems"))
        try:
            stat_result = skill_path.stat()
            timestamp = int(stat_result.st_mtime)
        except OSError:
            timestamp = 0
        search_parts = [
            slug,
            display_name,
            summary or "",
            version or "",
            *tags,
            *os_values,
            *systems,
        ]
        return GatewaySkillCatalogEntry(
            slug=slug,
            display_name=display_name,
            summary=summary,
            version=version,
            updated_at=timestamp,
            created_at=timestamp,
            tags=tags,
            os=os_values,
            systems=systems,
            search_text=" ".join(_normalize_text(part) for part in search_parts if part),
        )

    def _search_score(self, entry: GatewaySkillCatalogEntry, query: str) -> float:
        if not query:
            return 1.0
        if query in entry.search_text:
            return 1.0
        query_terms = [term for term in _TOKEN_RE.findall(query) if term]
        if not query_terms:
            return 0.0
        matched_terms = sum(1 for term in query_terms if term in entry.search_text)
        if matched_terms <= 0:
            return 0.0
        return round(matched_terms / len(query_terms), 3)

    def _skill_roots(self) -> tuple[tuple[Path, str], ...]:
        return (
            (self.codex_home / "skills", "codex-home"),
            (self.codex_home / "plugins" / "cache", "plugin-cache"),
            (self.workspace_root / ".codex" / "skills", "workspace-codex"),
            (self.workspace_root / "skills", "workspace"),
        )
