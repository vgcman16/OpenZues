from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(?P<frontmatter>.*?)\r?\n---\s*\r?\n?", re.DOTALL)
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+/.-]*")
_STOPWORDS = {
    "agent",
    "agents",
    "assistant",
    "automate",
    "automation",
    "build",
    "building",
    "create",
    "creates",
    "creating",
    "flow",
    "flows",
    "guide",
    "help",
    "helps",
    "hermes",
    "integrate",
    "integration",
    "integrations",
    "manage",
    "management",
    "run",
    "running",
    "skill",
    "skills",
    "supports",
    "system",
    "tool",
    "tools",
    "use",
    "using",
    "workflow",
    "workflows",
}
_WINDOWS_PLATFORM = "windows"
_LOCAL_LANE_TRANSPORTS = {"desktop", "stdio"}


def default_hermes_source_path() -> Path | None:
    candidate = Path(__file__).resolve().parents[3].with_name("hermes-agent-main")
    if candidate.exists():
        return candidate
    return None


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _normalize_phrase(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    return normalized or None


def _term_set(*values: str | None) -> frozenset[str]:
    terms: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized:
            continue
        for token in _TOKEN_RE.findall(normalized):
            if len(token) < 4 or token in _STOPWORDS:
                continue
            terms.add(token)
    return frozenset(terms)


def _string_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        normalized = value.strip()
        return (normalized,) if normalized else ()
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            normalized = str(item or "").strip()
            if normalized:
                items.append(normalized)
        return tuple(items)
    return ()


def _required_environment_variables(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    names: list[str] = []
    for item in value:
        if isinstance(item, dict):
            normalized = str(item.get("name") or "").strip()
            if normalized:
                names.append(normalized)
    return tuple(names)


def _current_platform() -> str:
    if sys.platform.startswith("win"):
        return _WINDOWS_PLATFORM
    if sys.platform == "darwin":
        return "macos"
    return "linux"


@dataclass(frozen=True, slots=True)
class HermesSkillSpec:
    kind: str
    slug: str
    name: str
    description: str
    category: str | None
    tags: tuple[str, ...]
    source: str
    platforms: tuple[str, ...]
    requires_toolsets: tuple[str, ...]
    fallback_for_toolsets: tuple[str, ...]
    required_environment_variables: tuple[str, ...]
    prompt_hint: str
    name_terms: frozenset[str]
    tag_terms: frozenset[str]
    match_phrases: tuple[str, ...]

    @property
    def platform_compatible(self) -> bool:
        if not self.platforms:
            return True
        return _current_platform() in {platform.lower() for platform in self.platforms}


@dataclass(frozen=True, slots=True)
class HermesSkillMatch:
    name: str
    prompt_hint: str
    source: str


_configured_root_key: str | None = None


def configure_hermes_skill_catalog(source_path: str | Path | None) -> None:
    global _configured_root_key
    _catalog_for_root.cache_clear()
    if source_path is None:
        _configured_root_key = None
        return
    resolved = Path(source_path).expanduser().resolve()
    _configured_root_key = str(resolved) if resolved.exists() else None


def _frontmatter_parts(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return {}, text
    frontmatter = yaml.safe_load(match.group("frontmatter")) or {}
    if not isinstance(frontmatter, dict):
        return {}, text
    return frontmatter, text[match.end() :]


def _match_phrases(
    *,
    name: str,
    slug: str,
    category: str | None,
    tags: tuple[str, ...],
) -> tuple[str, ...]:
    phrases: list[str] = []
    for candidate in (
        name,
        slug.replace("/", " "),
        slug.split("/")[-1].replace("-", " "),
        category,
        *tags,
    ):
        normalized = _normalize_phrase(candidate)
        if normalized and normalized not in phrases:
            phrases.append(normalized)
    return tuple(phrases)


def _build_prompt_hint(
    *,
    description: str,
    category: str | None,
    required_environment_variables: tuple[str, ...],
    requires_toolsets: tuple[str, ...],
) -> str:
    base = description.strip().rstrip(".")
    if not base:
        base = (
            f"Use this Hermes skill when the mission needs {category}"
            if category
            else "Use this Hermes skill when the mission needs its documented workflow"
        )
    hint = f"{base}."
    if requires_toolsets:
        hint += (
            " Best fit when "
            + ", ".join(sorted({toolset for toolset in requires_toolsets if toolset}))
            + " tooling is available."
        )
    if required_environment_variables:
        hint += (
            " If it needs credentials or environment setup, ask for the exact missing input "
            "instead of guessing."
        )
    hint += (
        " Read the linked Hermes SKILL.md before executing the workflow so you follow its "
        "procedure instead of improvising."
    )
    return hint


def _load_skill_spec(root: Path, kind: str, skill_md_path: Path) -> HermesSkillSpec | None:
    if any(part.startswith(".") for part in skill_md_path.relative_to(root).parts):
        return None
    frontmatter, _ = _frontmatter_parts(skill_md_path.read_text(encoding="utf-8"))
    name = str(frontmatter.get("name") or skill_md_path.parent.name).strip()
    description = str(frontmatter.get("description") or "").strip()
    metadata = frontmatter.get("metadata") or {}
    hermes_metadata = metadata.get("hermes") if isinstance(metadata, dict) else {}
    hermes_metadata = hermes_metadata if isinstance(hermes_metadata, dict) else {}
    category = str(hermes_metadata.get("category") or "").strip() or None
    tags = _string_list(hermes_metadata.get("tags"))
    platforms = tuple(platform.lower() for platform in _string_list(frontmatter.get("platforms")))
    requires_toolsets = _string_list(hermes_metadata.get("requires_toolsets"))
    fallback_for_toolsets = _string_list(hermes_metadata.get("fallback_for_toolsets"))
    required_environment_variables = _required_environment_variables(
        frontmatter.get("required_environment_variables")
    )
    relative_parts = skill_md_path.parent.relative_to(root / kind).parts
    slug = "/".join(relative_parts)
    return HermesSkillSpec(
        kind="optional" if kind == "optional-skills" else "bundled",
        slug=slug,
        name=name,
        description=description,
        category=category or (relative_parts[0] if relative_parts else None),
        tags=tags,
        source=str(skill_md_path),
        platforms=platforms,
        requires_toolsets=requires_toolsets,
        fallback_for_toolsets=fallback_for_toolsets,
        required_environment_variables=required_environment_variables,
        prompt_hint=_build_prompt_hint(
            description=description,
            category=category or (relative_parts[0] if relative_parts else None),
            required_environment_variables=required_environment_variables,
            requires_toolsets=requires_toolsets,
        ),
        name_terms=_term_set(name, slug.replace("/", " "), slug.replace("/", "-")),
        tag_terms=_term_set(*(tag for tag in tags), category),
        match_phrases=_match_phrases(
            name=name,
            slug=slug,
            category=category or (relative_parts[0] if relative_parts else None),
            tags=tags,
        ),
    )


@lru_cache(maxsize=8)
def _catalog_for_root(root_key: str | None) -> tuple[HermesSkillSpec, ...]:
    if root_key is None:
        return ()
    root = Path(root_key)
    if not root.exists():
        return ()
    specs: list[HermesSkillSpec] = []
    for kind in ("skills", "optional-skills"):
        base_dir = root / kind
        if not base_dir.exists():
            continue
        for skill_md_path in sorted(base_dir.rglob("SKILL.md")):
            spec = _load_skill_spec(root, kind, skill_md_path)
            if spec is not None and spec.platform_compatible:
                specs.append(spec)
    return tuple(specs)


def iter_hermes_skill_specs() -> tuple[HermesSkillSpec, ...]:
    return _catalog_for_root(_configured_root_key)


def _match_score(spec: HermesSkillSpec, context: str, context_terms: frozenset[str]) -> int:
    phrase_score = 0
    for phrase in spec.match_phrases:
        if phrase and phrase in context:
            phrase_score += 6
    name_overlap = len(spec.name_terms & context_terms)
    tag_overlap = len(spec.tag_terms & context_terms)
    score = phrase_score + (name_overlap * 3) + (tag_overlap * 2)
    if spec.category and _normalize_text(spec.category) in context_terms:
        score += 1
    if spec.name_terms and spec.name_terms.issubset(context_terms) and len(spec.name_terms) <= 3:
        score += 2
    return score


def resolve_hermes_skill_matches(
    objective: str | None,
    *,
    project_label: str | None = None,
    project_path: str | None = None,
    additional_context: str | None = None,
    active_toolsets: Iterable[str] = (),
    limit: int = 4,
) -> tuple[HermesSkillMatch, ...]:
    context = _normalize_text(
        " ".join(
            part
            for part in (objective, project_label, project_path, additional_context)
            if part
        )
    )
    if not context:
        return ()
    context_terms = _term_set(context)
    active_toolset_set = {str(toolset or "").strip().lower() for toolset in active_toolsets if str(toolset or "").strip()}
    ranked: list[tuple[int, str, HermesSkillSpec]] = []
    for spec in iter_hermes_skill_specs():
        if spec.requires_toolsets and active_toolset_set and not (
            set(spec.requires_toolsets) & active_toolset_set
        ):
            continue
        score = _match_score(spec, context, context_terms)
        if spec.requires_toolsets:
            if active_toolset_set:
                score += 4 * len(set(spec.requires_toolsets) & active_toolset_set)
            else:
                score += 1
        if spec.fallback_for_toolsets and active_toolset_set:
            score += 3 * len(set(spec.fallback_for_toolsets) & active_toolset_set)
        if score < 6:
            continue
        ranked.append((score, spec.name.lower(), spec))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    matches: list[HermesSkillMatch] = []
    seen_sources: set[str] = set()
    for _, _, spec in ranked:
        if spec.source in seen_sources:
            continue
        matches.append(
            HermesSkillMatch(
                name=spec.name,
                prompt_hint=spec.prompt_hint,
                source=spec.source,
            )
        )
        seen_sources.add(spec.source)
        if len(matches) >= limit:
            break
    return tuple(matches)


def is_local_skill_source_available(source: str | None) -> bool:
    if not source:
        return False
    candidate = Path(source).expanduser()
    return candidate.is_absolute() and candidate.exists()


def lane_can_read_local_skill_source(*, source: str | None, transport: str | None) -> bool:
    return is_local_skill_source_available(source) and (transport or "") in _LOCAL_LANE_TRANSPORTS
