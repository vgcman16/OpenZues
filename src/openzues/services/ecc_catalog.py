from __future__ import annotations

from copy import deepcopy
import json
import re
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(?P<frontmatter>.*?)\r?\n---\s*\r?\n?", re.DOTALL)
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+/.-]*")
_STOPWORDS = {
    "agent",
    "agents",
    "ai",
    "anthropic",
    "baseline",
    "best",
    "build",
    "claude",
    "code",
    "codex",
    "command",
    "commands",
    "config",
    "configs",
    "development",
    "ecc",
    "everything",
    "for",
    "guide",
    "help",
    "install",
    "instructions",
    "model",
    "models",
    "plugin",
    "plugins",
    "project",
    "projects",
    "repo",
    "repositories",
    "repository",
    "rule",
    "rules",
    "skill",
    "skills",
    "surface",
    "system",
    "target",
    "targets",
    "tool",
    "tools",
    "use",
    "using",
    "workflow",
    "workflows",
    "workspace",
}
_MCP_SERVER_ALIASES = {"context7-mcp": "context7"}
_CORE_WORKSPACE_SURFACES = (
    "AGENTS.md",
    ".codex/AGENTS.md",
    ".codex/config.toml",
    ".mcp.json",
    ".codex/agents/",
)
_INSTALL_STATE_CANDIDATES = (
    ".codex/ecc-install-state.json",
    ".claude/ecc-install-state.json",
    ".cursor/ecc-install-state.json",
    ".agent/ecc-install-state.json",
    ".codebuddy/ecc-install-state.json",
    ".gemini/ecc-install-state.json",
    "ecc-install-state.json",
)
_INSTALL_STATE_SCHEMA_VERSION = "ecc.install.v1"
_PROJECT_CODEX_INSTALL_TARGET_ID = "codex-project"
_PROJECT_CODEX_INSTALL_MODULE_ID = "legacy-codex-install"
_ECC_INSTALL_TARGET = "codex"
_CODEX_INSTALL_SUPPLEMENTAL_PATHS = (".mcp.json",)
_CODEX_CONFIG_MERGE_ROOT_KEYS = (
    "approval_policy",
    "sandbox_mode",
    "web_search",
    "notify",
    "persistent_instructions",
)
_CODEX_CONFIG_MERGE_TABLE_PATHS = (
    "features",
    "profiles.strict",
    "profiles.yolo",
    "agents",
    "agents.explorer",
    "agents.reviewer",
    "agents.docs_researcher",
)
_JSON_REMOVE_SENTINEL = object()
_configured_root_key: str | None = None


@dataclass(frozen=True, slots=True)
class EccSkillSpec:
    slug: str
    name: str
    description: str
    source: str
    prompt_hint: str
    name_terms: frozenset[str]
    detail_terms: frozenset[str]
    match_phrases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EccSkillMatch:
    name: str
    prompt_hint: str
    source: str


@dataclass(frozen=True, slots=True)
class EccDoctorCheck:
    key: str
    label: str
    status: str
    detail: str
    expected: tuple[str, ...] = ()
    observed: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EccDoctorAction:
    title: str
    detail: str
    command: str | None = None


@dataclass(frozen=True, slots=True)
class EccWorkspaceDoctor:
    level: str
    headline: str
    summary: str
    baseline_path: str | None = None
    install_state_paths: tuple[str, ...] = ()
    expected_surface_paths: tuple[str, ...] = ()
    missing_surface_paths: tuple[str, ...] = ()
    expected_mcp_servers: tuple[str, ...] = ()
    missing_mcp_servers: tuple[str, ...] = ()
    expected_codex_roles: tuple[str, ...] = ()
    missing_codex_roles: tuple[str, ...] = ()
    drifted_paths: tuple[str, ...] = ()
    drift_notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    checks: tuple[EccDoctorCheck, ...] = ()
    repair_actions: tuple[EccDoctorAction, ...] = ()


@dataclass(frozen=True, slots=True)
class EccRepairEntry:
    relative_path: str
    reason: str
    action: str
    operation: EccInstallFileOperation | None = None


@dataclass(frozen=True, slots=True)
class EccWorkspaceRepairRun:
    mode: str
    status: str
    headline: str
    summary: str
    project_path: str
    baseline_path: str
    profile: str | None = None
    selected_modules: tuple[str, ...] = ()
    skipped_modules: tuple[str, ...] = ()
    planned_paths: tuple[str, ...] = ()
    changed_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    doctor: EccWorkspaceDoctor | None = None


@dataclass(frozen=True, slots=True)
class EccInstallModule:
    id: str
    kind: str
    description: str
    paths: tuple[str, ...]
    targets: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    default_install: bool = False
    cost: str | None = None
    stability: str | None = None


@dataclass(frozen=True, slots=True)
class EccInstallComponent:
    id: str
    family: str
    description: str
    modules: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EccInstallProfile:
    id: str
    description: str
    modules: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EccInstallManifest:
    version: int
    profiles: tuple[EccInstallProfile, ...]
    components: tuple[EccInstallComponent, ...]
    modules: tuple[EccInstallModule, ...]


@dataclass(frozen=True, slots=True)
class EccInstallProfileSummary:
    id: str
    description: str
    module_count: int
    installable_module_count: int
    skipped_module_count: int


@dataclass(frozen=True, slots=True)
class EccInstallStateSummary:
    profile: str | None = None
    selected_modules: tuple[str, ...] = ()
    skipped_modules: tuple[str, ...] = ()
    legacy_mode: bool = False


@dataclass(frozen=True, slots=True)
class EccInstallFileOperation:
    module_id: str
    source_relative_path: str | None = None
    kind: str = "copy-file"
    destination_relative_path: str | None = None
    strategy: str = "preserve-relative-path"
    ownership: str = "managed"
    rendered_content: str | None = None
    previous_content: str | None = None
    merge_payload: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EccInstallPlan:
    profile: str
    requested_modules: tuple[str, ...]
    selected_modules: tuple[str, ...]
    skipped_modules: tuple[str, ...]
    missing_modules: tuple[str, ...] = ()
    missing_source_paths: tuple[str, ...] = ()
    operations: tuple[EccInstallFileOperation, ...] = ()


@dataclass(frozen=True, slots=True)
class EccWorkspaceSurface:
    kind: str
    headline: str
    summary: str
    skill_count: int = 0
    command_count: int = 0
    agent_count: int = 0
    rule_family_count: int = 0
    codex_role_count: int = 0
    mcp_servers: tuple[str, ...] = ()
    features: tuple[str, ...] = ()
    surface_paths: tuple[str, ...] = ()
    baseline_path: str | None = None
    install_state_paths: tuple[str, ...] = ()
    install_manifest_version: int | None = None
    install_profiles: tuple[EccInstallProfileSummary, ...] = ()
    default_install_profile: str | None = None
    active_install_profile: str | None = None
    active_install_modules: tuple[str, ...] = ()
    active_install_skipped_modules: tuple[str, ...] = ()
    doctor: EccWorkspaceDoctor | None = None


def default_ecc_source_path() -> Path | None:
    candidate = Path(__file__).resolve().parents[3].with_name("everything-claude-code-main")
    return candidate if candidate.exists() else None


def configure_ecc_catalog(source_path: str | Path | None) -> None:
    global _configured_root_key
    _catalog_for_root.cache_clear()
    _install_manifest_for_root.cache_clear()
    if source_path is None:
        _configured_root_key = None
        return
    resolved = Path(source_path).expanduser().resolve(strict=False)
    _configured_root_key = str(resolved) if resolved.exists() else None


def _configured_source_root() -> Path | None:
    if _configured_root_key is None:
        return None
    root = Path(_configured_root_key)
    if root.exists() and root.is_dir() and _is_ecc_source_repo(root):
        return root
    return None


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _normalize_phrase(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    return normalized or None


def _normalized_text_value(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("\r\n", "\n")


def _normalize_mcp_server_name(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None
    return _MCP_SERVER_ALIASES.get(normalized, normalized)


def _read_text(path: Path) -> str | None:
    try:
        return _normalized_text_value(path.read_text(encoding="utf-8"))
    except OSError:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    raw_text = _read_text(path)
    if raw_text is None:
        return {}
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_toml(path: Path) -> dict[str, Any]:
    raw_text = _read_text(path)
    if raw_text is None:
        return {}
    try:
        payload = tomllib.loads(raw_text)
    except tomllib.TOMLDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_json_object_text(text: str | None, *, label: str) -> dict[str, Any]:
    normalized = _normalized_text_value(text)
    if normalized is None or not normalized.strip():
        return {}
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return payload


def _format_json_text(payload: dict[str, Any]) -> str:
    return _ensure_trailing_newline(json.dumps(payload, indent=2))


def _frontmatter_parts(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return {}, text
    frontmatter = yaml.safe_load(match.group("frontmatter")) or {}
    if not isinstance(frontmatter, dict):
        return {}, text
    return frontmatter, text[match.end() :]


def _string_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        item = value.strip()
        return (item,) if item else ()
    if isinstance(value, list):
        items: list[str] = []
        for value_item in value:
            normalized = str(value_item or "").strip()
            if normalized:
                items.append(normalized)
        return tuple(items)
    return ()


def _unique_ordered(items: list[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        ordered.append(normalized)
        seen.add(normalized)
    return tuple(ordered)


def _relative_surface_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _term_set(*values: str | None) -> frozenset[str]:
    terms: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized:
            continue
        for token in _TOKEN_RE.findall(normalized):
            if len(token) < 3 or token in _STOPWORDS:
                continue
            terms.add(token)
    return frozenset(terms)

def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else f"{text}\n"


def _is_ecc_source_repo(root: Path) -> bool:
    if not root.exists() or not root.is_dir():
        return False
    package_name = str(_read_json(root / "package.json").get("name") or "").strip().lower()
    if package_name == "ecc-universal":
        return True
    return any((root / name).exists() for name in ("skills", "commands", "agents", "rules"))


def _candidate_source_root(project_path: str | Path | None = None) -> Path | None:
    if project_path is not None:
        candidate = Path(project_path).expanduser().resolve(strict=False)
        if _is_ecc_source_repo(candidate):
            return candidate
    configured = _configured_source_root()
    if configured is not None:
        return configured
    default = default_ecc_source_path()
    if default is not None and _is_ecc_source_repo(default):
        return default
    return None


def _path_has_marker(path: Path, marker: str) -> bool:
    text = _read_text(path)
    return bool(text and marker in text)


def _codex_role_paths(root: Path) -> tuple[Path, ...]:
    role_root = root / ".codex" / "agents"
    if not role_root.exists():
        return ()
    return tuple(sorted(path for path in role_root.glob("*.toml") if path.is_file()))


def _codex_role_names(root: Path) -> tuple[str, ...]:
    return tuple(path.stem for path in _codex_role_paths(root))


def _rule_family_count(root: Path) -> int:
    rules_root = root / "rules"
    if not rules_root.exists():
        return 0
    families = {
        path.relative_to(rules_root).parts[0]
        for path in rules_root.rglob("*")
        if path.is_file() and path.relative_to(rules_root).parts
    }
    return len(families)


def _file_count(root: Path, relative_path: str) -> int:
    base_path = root / relative_path
    if not base_path.exists():
        return 0
    if base_path.is_file():
        return 1
    return sum(1 for path in base_path.rglob("*") if path.is_file())


def _surface_paths(root: Path) -> tuple[str, ...]:
    candidates = [
        ("skills", "skills/"),
        ("commands", "commands/"),
        ("agents", "agents/"),
        (".agents", ".agents/"),
        ("rules", "rules/"),
        (".codex/agents", ".codex/agents/"),
        ("AGENTS.md", "AGENTS.md"),
        (".codex/AGENTS.md", ".codex/AGENTS.md"),
        (".codex/config.toml", ".codex/config.toml"),
        (".mcp.json", ".mcp.json"),
    ]
    paths: list[str] = []
    for relative_path, label in candidates:
        if (root / relative_path).exists():
            paths.append(label)
    return tuple(paths)


def _extract_mcp_servers_from_payload(payload: dict[str, Any]) -> tuple[str, ...]:
    servers = payload.get("mcpServers")
    if not isinstance(servers, dict):
        return ()
    ordered: list[str] = []
    for raw_name in servers:
        normalized = _normalize_mcp_server_name(str(raw_name))
        if normalized:
            ordered.append(normalized)
    return _unique_ordered(ordered)


def _extract_mcp_servers_from_toml(payload: dict[str, Any]) -> tuple[str, ...]:
    servers = payload.get("mcp_servers")
    if not isinstance(servers, dict):
        return ()
    ordered: list[str] = []
    for raw_name in servers:
        normalized = _normalize_mcp_server_name(str(raw_name))
        if normalized:
            ordered.append(normalized)
    return _unique_ordered(ordered)


def _workspace_mcp_servers(root: Path) -> tuple[str, ...]:
    return _unique_ordered(
        [
            *_extract_mcp_servers_from_payload(_read_json(root / ".mcp.json")),
            *_extract_mcp_servers_from_toml(_read_toml(root / ".codex" / "config.toml")),
        ]
    )


def _workspace_has_ecc_marker(root: Path) -> bool:
    if _find_install_state_path(root) is not None:
        return True
    return _path_has_marker(root / ".codex" / "AGENTS.md", "ECC for Codex CLI") or _path_has_marker(
        root / "AGENTS.md",
        "Everything Claude Code",
    )


@lru_cache(maxsize=8)
def _catalog_for_root(root_key: str) -> tuple[EccSkillSpec, ...]:
    root = Path(root_key)
    skills_root = root / "skills"
    if not skills_root.exists():
        return ()
    specs: list[EccSkillSpec] = []
    for skill_path in sorted(skills_root.rglob("SKILL.md")):
        text = _read_text(skill_path)
        if not text:
            continue
        frontmatter, _body = _frontmatter_parts(text)
        name = str(frontmatter.get("name") or skill_path.parent.name).strip() or skill_path.parent.name
        description = str(frontmatter.get("description") or "").strip()
        match_phrases = tuple(
            phrase
            for phrase in (
                _normalize_phrase(name),
                _normalize_phrase(description),
            )
            if phrase
        )
        specs.append(
            EccSkillSpec(
                slug=skill_path.parent.name,
                name=name,
                description=description,
                source=str(skill_path),
                prompt_hint=(
                    "Read the linked ECC SKILL.md and follow its documented workflow before "
                    "making changes."
                ),
                name_terms=_term_set(name),
                detail_terms=_term_set(description),
                match_phrases=match_phrases,
            )
        )
    return tuple(specs)


def resolve_ecc_skill_matches(
    objective: str | None,
    *,
    project_label: str | None = None,
    project_path: str | None = None,
    additional_context: str | None = None,
    limit: int = 3,
) -> list[EccSkillMatch]:
    source_root = _candidate_source_root(project_path)
    if source_root is None or limit <= 0:
        return []
    context = " ".join(
        part
        for part in (
            _normalize_text(objective),
            _normalize_text(project_label),
            _normalize_text(project_path),
            _normalize_text(additional_context),
        )
        if part
    )
    if not context:
        return []
    context_terms = _term_set(context)
    ranked: list[tuple[int, str, EccSkillSpec]] = []
    for spec in _catalog_for_root(str(source_root)):
        score = 0
        score += len(context_terms & spec.name_terms) * 5
        score += len(context_terms & spec.detail_terms) * 3
        score += sum(7 for phrase in spec.match_phrases if phrase and phrase in context)
        if score <= 0:
            continue
        ranked.append((score, spec.name.lower(), spec))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [
        EccSkillMatch(
            name=spec.name,
            prompt_hint=spec.prompt_hint,
            source=spec.source,
        )
        for _score, _name, spec in ranked[:limit]
    ]


@lru_cache(maxsize=8)
def _install_manifest_for_root(root_key: str) -> EccInstallManifest | None:
    root = Path(root_key)
    manifest_root = root / "manifests"
    profiles_payload = _read_json(manifest_root / "install-profiles.json")
    components_payload = _read_json(manifest_root / "install-components.json")
    modules_payload = _read_json(manifest_root / "install-modules.json")
    profiles_raw = profiles_payload.get("profiles")
    modules_raw = modules_payload.get("modules")
    components_raw = components_payload.get("components")
    if not isinstance(profiles_raw, dict) or not isinstance(modules_raw, list):
        return None
    profiles = tuple(
        EccInstallProfile(
            id=str(profile_id),
            description=str(profile_payload.get("description") or "").strip(),
            modules=_string_list(profile_payload.get("modules")),
        )
        for profile_id, profile_payload in profiles_raw.items()
        if isinstance(profile_payload, dict)
    )
    components = tuple(
        EccInstallComponent(
            id=str(component_payload.get("id") or "").strip(),
            family=str(component_payload.get("family") or "").strip(),
            description=str(component_payload.get("description") or "").strip(),
            modules=_string_list(component_payload.get("modules")),
        )
        for component_payload in components_raw
        if isinstance(components_raw, list) and isinstance(component_payload, dict)
    )
    modules = tuple(
        EccInstallModule(
            id=str(module_payload.get("id") or "").strip(),
            kind=str(module_payload.get("kind") or "").strip(),
            description=str(module_payload.get("description") or "").strip(),
            paths=_string_list(module_payload.get("paths")),
            targets=_string_list(module_payload.get("targets")),
            dependencies=_string_list(module_payload.get("dependencies")),
            default_install=bool(module_payload.get("defaultInstall")),
            cost=str(module_payload.get("cost") or "").strip() or None,
            stability=str(module_payload.get("stability") or "").strip() or None,
        )
        for module_payload in modules_raw
        if isinstance(module_payload, dict)
    )
    version = int(profiles_payload.get("version") or modules_payload.get("version") or 1)
    return EccInstallManifest(
        version=version,
        profiles=profiles,
        components=components,
        modules=modules,
    )


def _module_map(manifest: EccInstallManifest) -> dict[str, EccInstallModule]:
    return {module.id: module for module in manifest.modules if module.id}


def _default_install_profile_id(manifest: EccInstallManifest | None) -> str | None:
    if manifest is None or not manifest.profiles:
        return None
    for profile in manifest.profiles:
        if profile.id == "developer":
            return profile.id
    return manifest.profiles[0].id


def _is_installable_for_codex(source_root: Path, module: EccInstallModule) -> bool:
    if _ECC_INSTALL_TARGET not in module.targets:
        return False
    for relative_path in module.paths:
        if not (source_root / relative_path).exists():
            return False
    return True


def _install_profile_summaries(
    source_root: Path,
    manifest: EccInstallManifest | None,
) -> tuple[EccInstallProfileSummary, ...]:
    if manifest is None:
        return ()
    modules = _module_map(manifest)
    summaries: list[EccInstallProfileSummary] = []
    for profile in manifest.profiles:
        installable = sum(
            1
            for module_id in profile.modules
            if module_id in modules and _is_installable_for_codex(source_root, modules[module_id])
        )
        summaries.append(
            EccInstallProfileSummary(
                id=profile.id,
                description=profile.description,
                module_count=len(profile.modules),
                installable_module_count=installable,
                skipped_module_count=max(len(profile.modules) - installable, 0),
            )
        )
    return tuple(summaries)


@dataclass(frozen=True, slots=True)
class EccInstallState:
    source_root: str | None
    install_state_path: Path
    profile: str | None = None
    selected_modules: tuple[str, ...] = ()
    skipped_modules: tuple[str, ...] = ()
    legacy_mode: bool = False
    operations: tuple[EccInstallFileOperation, ...] = ()


def _default_install_state_path(workspace_root: Path) -> Path:
    return workspace_root / ".codex" / "ecc-install-state.json"


def _find_install_state_path(workspace_root: Path) -> Path | None:
    for relative_path in _INSTALL_STATE_CANDIDATES:
        candidate = workspace_root / relative_path
        if candidate.exists():
            return candidate
    return None


def _serialize_operation(
    workspace_root: Path,
    operation: EccInstallFileOperation,
) -> dict[str, Any]:
    destination_relative_path = operation.destination_relative_path or ""
    destination_path = (
        str((workspace_root / destination_relative_path).resolve(strict=False))
        if destination_relative_path
        else None
    )
    payload: dict[str, Any] = {
        "kind": operation.kind,
        "moduleId": operation.module_id,
        "sourceRelativePath": operation.source_relative_path,
        "destinationPath": destination_path,
        "destinationRelativePath": operation.destination_relative_path,
        "strategy": operation.strategy,
        "ownership": operation.ownership,
        "scaffoldOnly": bool(operation.metadata.get("scaffold_only")),
    }
    if operation.rendered_content is not None:
        payload["renderedContent"] = operation.rendered_content
    if operation.previous_content is not None:
        payload["previousContent"] = operation.previous_content
    if operation.merge_payload:
        payload["mergePayload"] = operation.merge_payload
    return payload


def _deserialize_operation(payload: dict[str, Any]) -> EccInstallFileOperation:
    metadata: dict[str, Any] = {}
    if bool(payload.get("scaffoldOnly")):
        metadata["scaffold_only"] = True
    merge_payload = payload.get("mergePayload")
    return EccInstallFileOperation(
        module_id=str(payload.get("moduleId") or "").strip(),
        source_relative_path=str(payload.get("sourceRelativePath") or "").strip() or None,
        kind=str(payload.get("kind") or "copy-file"),
        destination_relative_path=str(payload.get("destinationRelativePath") or "").strip() or None,
        strategy=str(payload.get("strategy") or "preserve-relative-path"),
        ownership=str(payload.get("ownership") or "managed"),
        rendered_content=payload.get("renderedContent")
        if isinstance(payload.get("renderedContent"), str)
        else None,
        previous_content=payload.get("previousContent")
        if isinstance(payload.get("previousContent"), str)
        else None,
        merge_payload=merge_payload if isinstance(merge_payload, dict) else None,
        metadata=metadata,
    )

def _load_install_state(workspace_root: Path) -> EccInstallState | None:
    state_path = _find_install_state_path(workspace_root)
    if state_path is None:
        return None
    payload = _read_json(state_path)
    if payload.get("schemaVersion") != _INSTALL_STATE_SCHEMA_VERSION:
        return None
    operations_raw = payload.get("operations")
    operations = tuple(
        _deserialize_operation(operation_payload)
        for operation_payload in operations_raw
        if isinstance(operations_raw, list) and isinstance(operation_payload, dict)
    )
    request = payload.get("request") if isinstance(payload.get("request"), dict) else {}
    resolution = payload.get("resolution") if isinstance(payload.get("resolution"), dict) else {}
    source_root = str(payload.get("sourceRoot") or "").strip() or None
    return EccInstallState(
        source_root=source_root,
        install_state_path=state_path,
        profile=str(request.get("profile") or "").strip() or None,
        selected_modules=_string_list(resolution.get("selectedModules")),
        skipped_modules=_string_list(resolution.get("skippedModules")),
        legacy_mode=bool(request.get("legacyMode")),
        operations=operations,
    )


def _write_install_state(
    workspace_root: Path,
    *,
    source_root: Path | None,
    profile: str | None,
    selected_modules: tuple[str, ...],
    skipped_modules: tuple[str, ...],
    legacy_mode: bool,
    operations: tuple[EccInstallFileOperation, ...],
) -> Path:
    state_path = _default_install_state_path(workspace_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": _INSTALL_STATE_SCHEMA_VERSION,
        "sourceRoot": str(source_root.resolve(strict=False)) if source_root is not None else None,
        "createdAt": datetime.now(UTC).isoformat(),
        "target": {
            "id": _PROJECT_CODEX_INSTALL_TARGET_ID,
            "target": _ECC_INSTALL_TARGET,
            "kind": "project",
            "projectPath": str(workspace_root.resolve(strict=False)),
            "installStatePath": str(state_path.resolve(strict=False)),
        },
        "request": {
            "profile": profile,
            "legacyMode": legacy_mode,
        },
        "resolution": {
            "selectedModules": list(selected_modules),
            "skippedModules": list(skipped_modules),
        },
        "operations": [_serialize_operation(workspace_root, operation) for operation in operations],
    }
    state_path.write_text(_format_json_text(payload), encoding="utf-8")
    return state_path


def _install_state_summary(state: EccInstallState | None) -> EccInstallStateSummary:
    if state is None:
        return EccInstallStateSummary()
    return EccInstallStateSummary(
        profile=state.profile,
        selected_modules=state.selected_modules,
        skipped_modules=state.skipped_modules,
        legacy_mode=state.legacy_mode,
    )


def _operation_expected_text(operation: EccInstallFileOperation) -> str | None:
    return operation.rendered_content


def _operation_drifted(
    workspace_root: Path,
    operation: EccInstallFileOperation,
) -> bool:
    if not operation.destination_relative_path:
        return False
    destination_path = workspace_root / operation.destination_relative_path
    expected = _operation_expected_text(operation)
    if expected is None:
        return not destination_path.exists()
    actual = _read_text(destination_path)
    return _normalized_text_value(actual) != _normalized_text_value(expected)


def _parse_toml_object_text(text: str | None) -> dict[str, Any]:
    normalized = _normalized_text_value(text)
    if normalized is None or not normalized.strip():
        return {}
    try:
        payload = tomllib.loads(normalized)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError("Codex config is not valid TOML.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Codex config must decode to a TOML table.")
    return payload


def _expected_mcp_servers_from_operations(
    operations: tuple[EccInstallFileOperation, ...],
) -> tuple[str, ...]:
    ordered: list[str] = []
    for operation in operations:
        if operation.destination_relative_path == ".mcp.json":
            ordered.extend(
                _extract_mcp_servers_from_payload(
                    _parse_json_object_text(
                        operation.rendered_content,
                        label="ECC managed .mcp.json",
                    )
                )
            )
        if operation.destination_relative_path == ".codex/config.toml":
            ordered.extend(_extract_mcp_servers_from_toml(_parse_toml_object_text(operation.rendered_content)))
    return _unique_ordered(ordered)


def _expected_codex_roles_from_operations(
    operations: tuple[EccInstallFileOperation, ...],
) -> tuple[str, ...]:
    ordered: list[str] = []
    for operation in operations:
        destination = operation.destination_relative_path or ""
        if destination.startswith(".codex/agents/") and destination.endswith(".toml"):
            ordered.append(Path(destination).stem)
    return _unique_ordered(ordered)


def _workspace_doctor_actions(workspace_root: Path) -> tuple[EccDoctorAction, ...]:
    command = f'node repair.js --workspace "{workspace_root}"'
    return (
        EccDoctorAction(
            title="Repair ECC workspace",
            detail="Rebuild the missing or drifted ECC-managed surface for this workspace.",
            command=command,
        ),
    )


def _legacy_surface_repairs(
    workspace_root: Path,
    baseline_root: Path,
) -> tuple[EccRepairEntry, ...]:
    entries: list[EccRepairEntry] = []

    def maybe_add(relative_path: str, *, compare_text: bool = True) -> None:
        source_path = baseline_root / relative_path
        if not source_path.exists() or not source_path.is_file():
            return
        destination_path = workspace_root / relative_path
        if not destination_path.exists():
            entries.append(EccRepairEntry(relative_path, "missing", "restore-from-baseline"))
            return
        if compare_text and _normalized_text_value(_read_text(destination_path)) != _normalized_text_value(
            _read_text(source_path)
        ):
            entries.append(EccRepairEntry(relative_path, "drifted", "restore-from-baseline"))

    maybe_add("AGENTS.md")
    maybe_add(".codex/AGENTS.md")
    maybe_add(".mcp.json")
    maybe_add(".codex/config.toml", compare_text=False)
    for role_path in _codex_role_paths(baseline_root):
        maybe_add(_relative_surface_path(baseline_root, role_path))
    return tuple(entries)


def _doctor_for_workspace(
    workspace_root: Path,
    *,
    baseline_root: Path | None,
    install_state: EccInstallState | None,
) -> EccWorkspaceDoctor:
    if baseline_root is None:
        return EccWorkspaceDoctor(
            level="warn",
            headline="ECC baseline unavailable",
            summary="The workspace exposes ECC markers, but no source baseline is configured.",
        )

    install_state_paths = (
        (_relative_surface_path(workspace_root, install_state.install_state_path),)
        if install_state is not None
        else ()
    )

    if install_state is not None:
        expected_surface_paths = _unique_ordered(
            [
                operation.destination_relative_path or ""
                for operation in install_state.operations
                if operation.destination_relative_path
            ]
        )
        drifted_paths = tuple(
            operation.destination_relative_path or ""
            for operation in install_state.operations
            if operation.destination_relative_path and _operation_drifted(workspace_root, operation)
        )
        expected_mcp_servers = _expected_mcp_servers_from_operations(install_state.operations)
        expected_codex_roles = _expected_codex_roles_from_operations(install_state.operations)
        actual_mcp_servers = _workspace_mcp_servers(workspace_root)
        actual_codex_roles = _codex_role_names(workspace_root)
        missing_mcp_servers = tuple(
            server for server in expected_mcp_servers if server not in actual_mcp_servers
        )
        missing_codex_roles = tuple(
            role for role in expected_codex_roles if role not in actual_codex_roles
        )
        is_ready = not drifted_paths and not missing_mcp_servers and not missing_codex_roles
        return EccWorkspaceDoctor(
            level="ready" if is_ready else "warn",
            headline="ECC workspace matches recorded install state"
            if is_ready
            else "ECC workspace drift detected",
            summary="Recorded ECC-managed files are aligned with the workspace."
            if is_ready
            else "One or more recorded ECC-managed files are missing or have drifted.",
            baseline_path=str(baseline_root),
            install_state_paths=install_state_paths,
            expected_surface_paths=expected_surface_paths,
            missing_surface_paths=(),
            expected_mcp_servers=expected_mcp_servers,
            missing_mcp_servers=missing_mcp_servers,
            expected_codex_roles=expected_codex_roles,
            missing_codex_roles=missing_codex_roles,
            drifted_paths=drifted_paths,
            repair_actions=() if is_ready else _workspace_doctor_actions(workspace_root),
        )

    expected_surface_paths = tuple(
        relative_path
        for relative_path in _CORE_WORKSPACE_SURFACES
        if (baseline_root / relative_path.rstrip("/")).exists()
    )
    missing_surface_paths = tuple(
        relative_path
        for relative_path in expected_surface_paths
        if not (workspace_root / relative_path.rstrip("/")).exists()
    )
    expected_mcp_servers = _workspace_mcp_servers(baseline_root)
    actual_mcp_servers = _workspace_mcp_servers(workspace_root)
    expected_codex_roles = _codex_role_names(baseline_root)
    actual_codex_roles = _codex_role_names(workspace_root)
    missing_mcp_servers = tuple(server for server in expected_mcp_servers if server not in actual_mcp_servers)
    missing_codex_roles = tuple(role for role in expected_codex_roles if role not in actual_codex_roles)
    drifted_paths: list[str] = []
    for relative_path in ("AGENTS.md", ".codex/AGENTS.md", ".mcp.json"):
        source_path = baseline_root / relative_path
        destination_path = workspace_root / relative_path
        if source_path.exists() and destination_path.exists():
            if _normalized_text_value(_read_text(source_path)) != _normalized_text_value(_read_text(destination_path)):
                drifted_paths.append(relative_path)
    for role_path in _codex_role_paths(baseline_root):
        relative_path = _relative_surface_path(baseline_root, role_path)
        destination_path = workspace_root / relative_path
        if destination_path.exists() and _normalized_text_value(_read_text(role_path)) != _normalized_text_value(
            _read_text(destination_path)
        ):
            drifted_paths.append(relative_path)
    is_ready = not missing_surface_paths and not missing_mcp_servers and not missing_codex_roles and not drifted_paths
    return EccWorkspaceDoctor(
        level="ready" if is_ready else "warn",
        headline="ECC workspace surface detected" if is_ready else "ECC workspace needs repair",
        summary="The workspace already exposes the expected ECC surface."
        if is_ready
        else "One or more ECC surface files, MCP servers, or Codex roles are missing.",
        baseline_path=str(baseline_root),
        install_state_paths=install_state_paths,
        expected_surface_paths=expected_surface_paths,
        missing_surface_paths=missing_surface_paths,
        expected_mcp_servers=expected_mcp_servers,
        missing_mcp_servers=missing_mcp_servers,
        expected_codex_roles=expected_codex_roles,
        missing_codex_roles=missing_codex_roles,
        drifted_paths=tuple(drifted_paths),
        repair_actions=() if is_ready else _workspace_doctor_actions(workspace_root),
    )


def _toml_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_literal(item) for item in value) + "]"
    raise ValueError(f"Unsupported TOML value: {value!r}")


def _format_toml_table(payload: dict[str, Any], prefix: tuple[str, ...] = ()) -> list[str]:
    lines: list[str] = []
    scalar_items = [(key, value) for key, value in payload.items() if not isinstance(value, dict)]
    table_items = [(key, value) for key, value in payload.items() if isinstance(value, dict)]
    if prefix:
        lines.append(f"[{'.'.join(prefix)}]")
    for key, value in scalar_items:
        lines.append(f"{key} = {_toml_literal(value)}")
    if scalar_items and table_items:
        lines.append("")
    for index, (key, value) in enumerate(table_items):
        lines.extend(_format_toml_table(value, (*prefix, key)))
        if index < len(table_items) - 1:
            lines.append("")
    return lines


def _format_toml_text(payload: dict[str, Any]) -> str:
    return _ensure_trailing_newline("\n".join(_format_toml_table(payload)))


def _merge_existing_over_source(source: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(source)
    for key, value in existing.items():
        if key not in merged:
            merged[key] = deepcopy(value)
            continue
        if isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_existing_over_source(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _json_missing_from_existing(existing: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    additions: dict[str, Any] = {}
    for key, value in source.items():
        if key not in existing:
            additions[key] = deepcopy(value)
            continue
        if isinstance(existing[key], dict) and isinstance(value, dict):
            nested = _json_missing_from_existing(existing[key], value)
            if nested:
                additions[key] = nested
    return additions


def _expand_module_source_files(source_root: Path, module: EccInstallModule) -> tuple[str, ...]:
    ordered: list[str] = []
    requested_paths = list(module.paths)
    if module.id == "platform-configs":
        requested_paths.extend(_CODEX_INSTALL_SUPPLEMENTAL_PATHS)
    for relative_path in requested_paths:
        source_path = source_root / relative_path
        if source_path.is_file():
            ordered.append(relative_path)
            continue
        if source_path.is_dir():
            ordered.extend(
                _relative_surface_path(source_root, child_path)
                for child_path in sorted(source_path.rglob("*"))
                if child_path.is_file()
            )
    return _unique_ordered(ordered)


def _build_install_operations(
    workspace_root: Path,
    source_root: Path,
    selected_modules: tuple[str, ...],
    manifest: EccInstallManifest,
) -> tuple[EccInstallFileOperation, ...]:
    operations: dict[str, EccInstallFileOperation] = {}
    module_index = _module_map(manifest)
    for module_id in selected_modules:
        module = module_index.get(module_id)
        if module is None:
            continue
        for source_relative_path in _expand_module_source_files(source_root, module):
            source_path = source_root / source_relative_path
            source_text = _read_text(source_path)
            if source_text is None:
                continue
            destination_path = workspace_root / source_relative_path
            previous_content = _read_text(destination_path)
            kind = "copy-file"
            rendered_content = _ensure_trailing_newline(source_text)
            merge_payload: dict[str, Any] | None = None
            if source_relative_path == ".codex/config.toml":
                kind = "render-template"
                rendered_content = _format_toml_text(
                    _merge_existing_over_source(
                        _parse_toml_object_text(source_text),
                        _parse_toml_object_text(previous_content),
                    )
                )
            elif source_relative_path == ".mcp.json":
                if previous_content and previous_content.strip():
                    kind = "merge-json"
                    existing_payload = _parse_json_object_text(
                        previous_content,
                        label="Workspace .mcp.json",
                    )
                    source_payload = _parse_json_object_text(
                        source_text,
                        label="ECC baseline .mcp.json",
                    )
                    merge_payload = _json_missing_from_existing(existing_payload, source_payload)
                    rendered_content = _format_json_text(
                        _merge_existing_over_source(source_payload, existing_payload)
                    )
                else:
                    rendered_content = _format_json_text(
                        _parse_json_object_text(source_text, label="ECC baseline .mcp.json")
                    )
            operations[source_relative_path] = EccInstallFileOperation(
                module_id=module_id,
                source_relative_path=source_relative_path,
                kind=kind,
                destination_relative_path=source_relative_path,
                rendered_content=rendered_content,
                previous_content=previous_content,
                merge_payload=merge_payload,
            )
    return tuple(operations[path] for path in sorted(operations))


def _resolve_profile_modules(
    source_root: Path,
    manifest: EccInstallManifest,
    profile_id: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    module_index = _module_map(manifest)
    profile = next((item for item in manifest.profiles if item.id == profile_id), None)
    if profile is None:
        raise ValueError(f"Unknown ECC install profile: {profile_id}")
    selected: list[str] = []
    skipped: list[str] = []
    for module_id in profile.modules:
        module = module_index.get(module_id)
        if module is None or not _is_installable_for_codex(source_root, module):
            skipped.append(module_id)
            continue
        selected.append(module_id)
    return tuple(selected), tuple(skipped)


def _apply_operation(workspace_root: Path, operation: EccInstallFileOperation) -> bool:
    relative_path = operation.destination_relative_path or operation.source_relative_path
    if not relative_path or operation.rendered_content is None:
        return False
    destination_path = workspace_root / relative_path
    current_text = _read_text(destination_path)
    if _normalized_text_value(current_text) == _normalized_text_value(operation.rendered_content):
        return False
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(operation.rendered_content, encoding="utf-8")
    return True


def _remove_workspace_path(workspace_root: Path, relative_path: str) -> bool:
    target_path = workspace_root / relative_path
    if not target_path.exists():
        return False
    if target_path.is_file():
        target_path.unlink()
        current = target_path.parent
        while current != workspace_root and current.exists():
            if any(current.iterdir()):
                break
            current.rmdir()
            current = current.parent
        return True
    return False


def _surface_from_source_repo(root: Path) -> EccWorkspaceSurface:
    manifest = _install_manifest_for_root(str(root))
    install_profiles = _install_profile_summaries(root, manifest)
    skill_count = sum(1 for _ in (root / "skills").rglob("SKILL.md")) if (root / "skills").exists() else 0
    roles = _codex_role_names(root)
    return EccWorkspaceSurface(
        kind="ecc_source",
        headline="Everything Claude Code source detected",
        summary=(
            f"ECC source repo detected with {skill_count} skill(s), "
            f"{_file_count(root, 'commands')} command(s), and "
            f"{_file_count(root, 'agents')} agent file(s)."
        ),
        skill_count=skill_count,
        command_count=_file_count(root, "commands"),
        agent_count=_file_count(root, "agents"),
        rule_family_count=_rule_family_count(root),
        codex_role_count=len(roles),
        mcp_servers=_workspace_mcp_servers(root),
        features=("install-manifests", "codex-surface", "workspace-skills"),
        surface_paths=_surface_paths(root),
        baseline_path=str(root),
        install_manifest_version=manifest.version if manifest is not None else None,
        install_profiles=install_profiles,
        default_install_profile=_default_install_profile_id(manifest),
        doctor=EccWorkspaceDoctor(
            level="ready",
            headline="ECC source baseline is ready",
            summary="The Everything Claude Code source repo is available for workspace installs.",
            baseline_path=str(root),
        ),
    )


def _is_primary_ecc_source_repo(root: Path) -> bool:
    package_name = str(_read_json(root / "package.json").get("name") or "").strip().lower()
    return package_name == "ecc-universal" or (
        (root / "manifests" / "install-profiles.json").exists()
        and (root / "manifests" / "install-modules.json").exists()
    )


def inspect_ecc_harness_surface(project_path: str | Path | None) -> EccWorkspaceSurface | None:
    if project_path is None:
        return None
    workspace_root = Path(project_path).expanduser().resolve(strict=False)
    source_root = _candidate_source_root(workspace_root)
    if _is_primary_ecc_source_repo(workspace_root):
        return _surface_from_source_repo(workspace_root)

    manifest = _install_manifest_for_root(str(source_root)) if source_root is not None else None
    install_state = _load_install_state(workspace_root)
    if _workspace_has_ecc_marker(workspace_root):
        install_state_paths = (
            (_relative_surface_path(workspace_root, install_state.install_state_path),)
            if install_state is not None
            else ()
        )
        state_summary = _install_state_summary(install_state)
        return EccWorkspaceSurface(
            kind="ecc_workspace",
            headline="Everything Claude Code workspace detected",
            summary="Installed ECC workspace detected with Codex-facing files and a tracked baseline.",
            surface_paths=_surface_paths(workspace_root),
            baseline_path=str(source_root) if source_root is not None else None,
            install_state_paths=install_state_paths,
            install_manifest_version=manifest.version if manifest is not None else None,
            install_profiles=_install_profile_summaries(source_root, manifest)
            if source_root is not None
            else (),
            default_install_profile=_default_install_profile_id(manifest),
            active_install_profile=state_summary.profile,
            active_install_modules=state_summary.selected_modules,
            active_install_skipped_modules=state_summary.skipped_modules,
            doctor=_doctor_for_workspace(
                workspace_root,
                baseline_root=source_root,
                install_state=install_state,
            ),
        )
    if source_root is None:
        return None
    return EccWorkspaceSurface(
        kind="ecc_candidate",
        headline="Everything Claude Code install candidate",
        summary="This project can adopt the ECC Codex-facing harness profile.",
        surface_paths=_surface_paths(workspace_root),
        baseline_path=str(source_root),
        install_manifest_version=manifest.version if manifest is not None else None,
        install_profiles=_install_profile_summaries(source_root, manifest),
        default_install_profile=_default_install_profile_id(manifest),
    )


def build_ecc_workspace_lines(project_path: str | Path | None) -> list[str]:
    surface = inspect_ecc_harness_surface(project_path)
    if surface is None:
        return []
    lines = ["ECC workspace surface:", surface.summary]
    if surface.baseline_path:
        lines.append(f"ECC baseline: {surface.baseline_path}")
    if surface.surface_paths:
        lines.append("ECC paths: " + ", ".join(surface.surface_paths))
    if surface.doctor is not None:
        lines.extend(["", "ECC doctor:", surface.doctor.headline, surface.doctor.summary])
    return lines

def _serialize_doctor(doctor: EccWorkspaceDoctor | None) -> dict[str, Any] | None:
    if doctor is None:
        return None
    return {
        "level": doctor.level,
        "headline": doctor.headline,
        "summary": doctor.summary,
        "baseline_path": doctor.baseline_path,
        "install_state_paths": list(doctor.install_state_paths),
        "expected_surface_paths": list(doctor.expected_surface_paths),
        "missing_surface_paths": list(doctor.missing_surface_paths),
        "expected_mcp_servers": list(doctor.expected_mcp_servers),
        "missing_mcp_servers": list(doctor.missing_mcp_servers),
        "expected_codex_roles": list(doctor.expected_codex_roles),
        "missing_codex_roles": list(doctor.missing_codex_roles),
        "drifted_paths": list(doctor.drifted_paths),
        "drift_notes": list(doctor.drift_notes),
        "warnings": list(doctor.warnings),
        "checks": [
            {
                "key": check.key,
                "label": check.label,
                "status": check.status,
                "detail": check.detail,
                "expected": list(check.expected),
                "observed": list(check.observed),
                "missing": list(check.missing),
            }
            for check in doctor.checks
        ],
        "repair_actions": [
            {
                "title": action.title,
                "detail": action.detail,
                "command": action.command,
            }
            for action in doctor.repair_actions
        ],
    }


def serialize_ecc_workspace_surface(surface: EccWorkspaceSurface | None) -> dict[str, Any] | None:
    if surface is None:
        return None
    return {
        "kind": surface.kind,
        "headline": surface.headline,
        "summary": surface.summary,
        "skill_count": surface.skill_count,
        "command_count": surface.command_count,
        "agent_count": surface.agent_count,
        "rule_family_count": surface.rule_family_count,
        "codex_role_count": surface.codex_role_count,
        "mcp_servers": list(surface.mcp_servers),
        "features": list(surface.features),
        "surface_paths": list(surface.surface_paths),
        "baseline_path": surface.baseline_path,
        "install_state_paths": list(surface.install_state_paths),
        "install_manifest_version": surface.install_manifest_version,
        "install_profiles": [
            {
                "id": profile.id,
                "description": profile.description,
                "module_count": profile.module_count,
                "installable_module_count": profile.installable_module_count,
                "skipped_module_count": profile.skipped_module_count,
            }
            for profile in surface.install_profiles
        ],
        "default_install_profile": surface.default_install_profile,
        "active_install_profile": surface.active_install_profile,
        "active_install_modules": list(surface.active_install_modules),
        "active_install_skipped_modules": list(surface.active_install_skipped_modules),
        "doctor": _serialize_doctor(surface.doctor),
    }


def serialize_ecc_repair_run(run: EccWorkspaceRepairRun) -> dict[str, Any]:
    return {
        "mode": run.mode,
        "status": run.status,
        "headline": run.headline,
        "summary": run.summary,
        "project_path": run.project_path,
        "baseline_path": run.baseline_path,
        "profile": run.profile,
        "selected_modules": list(run.selected_modules),
        "skipped_modules": list(run.skipped_modules),
        "planned_paths": list(run.planned_paths),
        "changed_paths": list(run.changed_paths),
        "warnings": list(run.warnings),
        "doctor": _serialize_doctor(run.doctor),
    }


__all__ = [
    "EccSkillMatch",
    "EccWorkspaceDoctor",
    "EccWorkspaceRepairRun",
    "EccWorkspaceSurface",
    "build_ecc_workspace_lines",
    "configure_ecc_catalog",
    "default_ecc_source_path",
    "inspect_ecc_harness_surface",
    "resolve_ecc_skill_matches",
    "run_ecc_workspace_install",
    "run_ecc_workspace_repair",
    "run_ecc_workspace_uninstall",
    "serialize_ecc_repair_run",
    "serialize_ecc_workspace_surface",
]

def _toml_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_literal(item) for item in value) + "]"
    raise ValueError(f"Unsupported TOML value: {value!r}")


def _format_toml_table(payload: dict[str, Any], prefix: tuple[str, ...] = ()) -> list[str]:
    lines: list[str] = []
    scalar_items = [(key, value) for key, value in payload.items() if not isinstance(value, dict)]
    table_items = [(key, value) for key, value in payload.items() if isinstance(value, dict)]
    if prefix:
        lines.append(f"[{'.'.join(prefix)}]")
    for key, value in scalar_items:
        lines.append(f"{key} = {_toml_literal(value)}")
    if scalar_items and table_items:
        lines.append("")
    for index, (key, value) in enumerate(table_items):
        lines.extend(_format_toml_table(value, (*prefix, key)))
        if index < len(table_items) - 1:
            lines.append("")
    return lines


def _format_toml_text(payload: dict[str, Any]) -> str:
    return _ensure_trailing_newline("\n".join(_format_toml_table(payload)))


def _merge_missing_dict_values(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if key not in target:
            target[key] = deepcopy(value)
            continue
        if isinstance(target[key], dict) and isinstance(value, dict):
            _merge_missing_dict_values(target[key], value)


def _nested_dict_value(payload: dict[str, Any], path_parts: tuple[str, ...]) -> dict[str, Any] | None:
    current: Any = payload
    for part in path_parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current if isinstance(current, dict) else None


def _ensure_nested_dict(payload: dict[str, Any], path_parts: tuple[str, ...]) -> dict[str, Any]:
    current = payload
    for part in path_parts:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    return current


def _merge_codex_config_text(existing_text: str | None, source_text: str | None) -> str:
    source_payload = _parse_toml_object_text(source_text)
    if existing_text is None or not existing_text.strip():
        return _format_toml_text(source_payload)
    merged = deepcopy(_parse_toml_object_text(existing_text))
    for root_key in _CODEX_CONFIG_MERGE_ROOT_KEYS:
        if root_key not in merged and root_key in source_payload:
            merged[root_key] = deepcopy(source_payload[root_key])
    for table_path in _CODEX_CONFIG_MERGE_TABLE_PATHS:
        path_parts = tuple(part for part in table_path.split(".") if part)
        source_table = _nested_dict_value(source_payload, path_parts)
        if source_table is None:
            continue
        target_table = _ensure_nested_dict(merged, path_parts)
        _merge_missing_dict_values(target_table, source_table)
    return _format_toml_text(merged)


def _additive_json_merge(
    target: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    additions: dict[str, Any] = {}
    for key, value in source.items():
        if key not in target:
            target[key] = deepcopy(value)
            additions[key] = deepcopy(value)
            continue
        if isinstance(target[key], dict) and isinstance(value, dict):
            child_additions = _additive_json_merge(target[key], value)
            if child_additions:
                additions[key] = child_additions
    return additions


def _deep_remove_subset(target: Any, subset: Any) -> Any:
    if not isinstance(target, dict) or not isinstance(subset, dict):
        return _JSON_REMOVE_SENTINEL if target == subset else target
    updated = dict(target)
    for key, subset_value in subset.items():
        if key not in updated:
            continue
        result = _deep_remove_subset(updated[key], subset_value)
        if result is _JSON_REMOVE_SENTINEL:
            updated.pop(key, None)
        else:
            updated[key] = result
    return _JSON_REMOVE_SENTINEL if not updated else updated


def _iter_module_source_files(
    source_root: Path,
    module: EccInstallModule,
) -> tuple[str, ...]:
    ordered: list[str] = []
    for relative_path in module.paths:
        source_path = source_root / relative_path
        if source_path.is_file():
            ordered.append(relative_path)
            continue
        if not source_path.is_dir():
            continue
        for child_path in sorted(path for path in source_path.rglob("*") if path.is_file()):
            ordered.append(_relative_surface_path(source_root, child_path))
    if module.id == "platform-configs":
        for relative_path in _CODEX_INSTALL_SUPPLEMENTAL_PATHS:
            if (source_root / relative_path).is_file():
                ordered.append(relative_path)
    return _unique_ordered(ordered)


def _resolve_install_plan(
    source_root: Path,
    *,
    profile: str | None,
) -> EccInstallPlan:
    manifest = _install_manifest_for_root(str(source_root))
    if manifest is None:
        raise ValueError("ECC install manifests are unavailable for the configured source repo.")
    profile_id = profile or _default_install_profile_id(manifest)
    if not profile_id:
        raise ValueError("No ECC install profile is available.")
    profile_payload = next((item for item in manifest.profiles if item.id == profile_id), None)
    if profile_payload is None:
        raise ValueError(f"Unknown ECC install profile: {profile_id}")
    modules = _module_map(manifest)
    selected_modules: list[str] = []
    skipped_modules: list[str] = []
    missing_modules: list[str] = []
    missing_source_paths: list[str] = []
    for module_id in profile_payload.modules:
        module = modules.get(module_id)
        if module is None:
            missing_modules.append(module_id)
            continue
        if _ECC_INSTALL_TARGET not in module.targets:
            skipped_modules.append(module_id)
            continue
        absent_paths = [
            relative_path for relative_path in module.paths if not (source_root / relative_path).exists()
        ]
        if absent_paths:
            skipped_modules.append(module_id)
            missing_source_paths.extend(absent_paths)
            continue
        selected_modules.append(module_id)
    return EccInstallPlan(
        profile=profile_payload.id,
        requested_modules=profile_payload.modules,
        selected_modules=tuple(selected_modules),
        skipped_modules=tuple(skipped_modules),
        missing_modules=tuple(missing_modules),
        missing_source_paths=_unique_ordered(missing_source_paths),
    )


def _build_install_operation(
    source_root: Path,
    workspace_root: Path,
    *,
    module_id: str,
    source_relative_path: str,
    previous_operation: EccInstallFileOperation | None,
) -> EccInstallFileOperation:
    source_path = source_root / source_relative_path
    source_text = _read_text(source_path)
    destination_relative_path = source_relative_path
    destination_path = workspace_root / destination_relative_path
    current_text = _read_text(destination_path)
    previous_content = previous_operation.previous_content if previous_operation is not None else current_text

    if source_relative_path == ".codex/config.toml":
        rendered = _merge_codex_config_text(current_text, source_text)
        return EccInstallFileOperation(
            module_id=module_id,
            source_relative_path=source_relative_path,
            kind="render-template",
            destination_relative_path=destination_relative_path,
            strategy="merge-codex-config",
            rendered_content=rendered,
            previous_content=previous_content,
        )

    if source_relative_path == ".mcp.json":
        merged_payload = _parse_json_object_text(current_text, label="Workspace .mcp.json")
        additions = _additive_json_merge(
            merged_payload,
            _parse_json_object_text(source_text, label="ECC baseline .mcp.json"),
        )
        rendered = _format_json_text(merged_payload)
        return EccInstallFileOperation(
            module_id=module_id,
            source_relative_path=source_relative_path,
            kind="merge-json",
            destination_relative_path=destination_relative_path,
            strategy="merge-json-additive",
            rendered_content=rendered,
            previous_content=previous_content,
            merge_payload=additions or None,
        )

    return EccInstallFileOperation(
        module_id=module_id,
        source_relative_path=source_relative_path,
        kind="copy-file",
        destination_relative_path=destination_relative_path,
        rendered_content=source_text,
        previous_content=previous_content,
    )


def _operation_map_by_destination(
    operations: tuple[EccInstallFileOperation, ...],
) -> dict[str, EccInstallFileOperation]:
    return {
        operation.destination_relative_path: operation
        for operation in operations
        if operation.destination_relative_path
    }


def _write_operation(
    workspace_root: Path,
    operation: EccInstallFileOperation,
) -> None:
    if not operation.destination_relative_path:
        return
    destination_path = workspace_root / operation.destination_relative_path
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if operation.rendered_content is None:
        return
    destination_path.write_text(operation.rendered_content, encoding="utf-8")


def _cleanup_empty_parents(path: Path, *, stop_at: Path) -> None:
    current = path.parent
    while current != stop_at and current.exists():
        try:
            next(current.iterdir())
            break
        except StopIteration:
            current.rmdir()
            current = current.parent
        except OSError:
            break


def _restore_operation(
    workspace_root: Path,
    operation: EccInstallFileOperation,
) -> None:
    if not operation.destination_relative_path:
        return
    destination_path = workspace_root / operation.destination_relative_path
    if operation.previous_content is not None:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(operation.previous_content, encoding="utf-8")
        return
    if operation.kind == "merge-json" and operation.merge_payload and destination_path.exists():
        current_payload = _parse_json_object_text(_read_text(destination_path), label="Workspace .mcp.json")
        updated_payload = _deep_remove_subset(current_payload, operation.merge_payload)
        if updated_payload is _JSON_REMOVE_SENTINEL:
            destination_path.unlink(missing_ok=True)
        else:
            destination_path.write_text(_format_json_text(updated_payload), encoding="utf-8")
    else:
        destination_path.unlink(missing_ok=True)
    _cleanup_empty_parents(destination_path, stop_at=workspace_root)


def _snapshot_legacy_operations(workspace_root: Path) -> tuple[EccInstallFileOperation, ...]:
    relative_paths: list[str] = []
    for relative_path in ("AGENTS.md", ".mcp.json", ".codex/AGENTS.md", ".codex/config.toml"):
        if (workspace_root / relative_path).is_file():
            relative_paths.append(relative_path)
    role_root = workspace_root / ".codex" / "agents"
    if role_root.exists():
        relative_paths.extend(
            _relative_surface_path(workspace_root, path)
            for path in sorted(role_root.glob("*.toml"))
            if path.is_file()
        )
    operations: list[EccInstallFileOperation] = []
    for relative_path in _unique_ordered(relative_paths):
        current_text = _read_text(workspace_root / relative_path)
        if current_text is None:
            continue
        kind = "copy-file"
        strategy = "preserve-relative-path"
        merge_payload = None
        if relative_path == ".codex/config.toml":
            kind = "render-template"
            strategy = "captured-workspace-state"
        elif relative_path == ".mcp.json":
            kind = "merge-json"
            strategy = "captured-workspace-state"
            merge_payload = _parse_json_object_text(current_text, label="Workspace .mcp.json")
        operations.append(
            EccInstallFileOperation(
                module_id=_PROJECT_CODEX_INSTALL_MODULE_ID,
                source_relative_path=relative_path,
                kind=kind,
                destination_relative_path=relative_path,
                strategy=strategy,
                rendered_content=current_text,
                merge_payload=merge_payload,
            )
        )
    return tuple(operations)

def run_ecc_workspace_install(
    project_path: str | Path,
    *,
    profile: str | None = None,
    apply: bool,
) -> EccWorkspaceRepairRun:
    workspace_root = Path(project_path).expanduser().resolve(strict=False)
    source_root = _candidate_source_root()
    if source_root is None:
        raise ValueError("ECC source baseline is not configured.")

    plan = _resolve_install_plan(source_root, profile=profile)
    manifest = _install_manifest_for_root(str(source_root))
    if manifest is None:
        raise ValueError("ECC install manifests are unavailable for the configured source repo.")

    previous_state = _load_install_state(workspace_root)
    previous_operations = _operation_map_by_destination(previous_state.operations) if previous_state else {}
    module_lookup = _module_map(manifest)
    operations: list[EccInstallFileOperation] = []
    for module_id in plan.selected_modules:
        module = module_lookup[module_id]
        for source_relative_path in _iter_module_source_files(source_root, module):
            operations.append(
                _build_install_operation(
                    source_root,
                    workspace_root,
                    module_id=module_id,
                    source_relative_path=source_relative_path,
                    previous_operation=previous_operations.get(source_relative_path),
                )
            )

    stale_operations: tuple[EccInstallFileOperation, ...] = ()
    if previous_state is not None:
        current_destinations = {
            operation.destination_relative_path
            for operation in operations
            if operation.destination_relative_path
        }
        stale_operations = tuple(
            operation
            for operation in previous_state.operations
            if operation.destination_relative_path
            and operation.destination_relative_path not in current_destinations
        )

    warnings = [
        f"Will prune stale ECC-managed file: {operation.destination_relative_path}"
        for operation in stale_operations
        if operation.destination_relative_path
    ]
    drifted_stale_paths = [
        operation.destination_relative_path or ""
        for operation in stale_operations
        if operation.destination_relative_path and _operation_drifted(workspace_root, operation)
    ]
    warnings.extend(
        f"Cannot safely prune stale ECC-managed file because it drifted: {relative_path}"
        for relative_path in drifted_stale_paths
    )
    planned_paths = _unique_ordered(
        [
            *(operation.destination_relative_path or "" for operation in operations if operation.destination_relative_path),
            *(operation.destination_relative_path or "" for operation in stale_operations if operation.destination_relative_path),
            ".codex/ecc-install-state.json",
        ]
    )

    current_surface = inspect_ecc_harness_surface(workspace_root)
    current_doctor = current_surface.doctor if current_surface is not None else None
    if not apply:
        return EccWorkspaceRepairRun(
            mode="install_preview",
            status="planned",
            headline="ECC install plan ready",
            summary=f"Install profile '{plan.profile}' is ready to apply.",
            project_path=str(workspace_root),
            baseline_path=str(source_root),
            profile=plan.profile,
            selected_modules=plan.selected_modules,
            skipped_modules=plan.skipped_modules,
            planned_paths=planned_paths,
            warnings=tuple(warnings),
            doctor=current_doctor,
        )

    if drifted_stale_paths:
        joined = ", ".join(drifted_stale_paths)
        raise ValueError(f"Cannot continue because managed files have drifted: {joined}")

    changed_paths: list[str] = []
    for operation in stale_operations:
        _restore_operation(workspace_root, operation)
        if operation.destination_relative_path:
            changed_paths.append(operation.destination_relative_path)
    for operation in operations:
        _write_operation(workspace_root, operation)
        if operation.destination_relative_path:
            changed_paths.append(operation.destination_relative_path)
    _write_install_state(
        workspace_root,
        source_root=source_root,
        profile=plan.profile,
        selected_modules=plan.selected_modules,
        skipped_modules=plan.skipped_modules,
        legacy_mode=False,
        operations=tuple(operations),
    )
    changed_paths.append(".codex/ecc-install-state.json")
    resulting_state = _load_install_state(workspace_root)
    doctor = _doctor_for_workspace(
        workspace_root,
        baseline_root=source_root,
        install_state=resulting_state,
    )
    return EccWorkspaceRepairRun(
        mode="install_apply",
        status="installed",
        headline="ECC install applied",
        summary=f"Install profile '{plan.profile}' is now active in this workspace.",
        project_path=str(workspace_root),
        baseline_path=str(source_root),
        profile=plan.profile,
        selected_modules=plan.selected_modules,
        skipped_modules=plan.skipped_modules,
        changed_paths=_unique_ordered(changed_paths),
        warnings=tuple(warnings),
        doctor=doctor,
    )


def run_ecc_workspace_uninstall(
    project_path: str | Path,
    *,
    apply: bool,
) -> EccWorkspaceRepairRun:
    workspace_root = Path(project_path).expanduser().resolve(strict=False)
    install_state = _load_install_state(workspace_root)
    if install_state is None:
        raise ValueError("No ECC install state was found for this workspace.")
    source_root = (
        Path(install_state.source_root).expanduser().resolve(strict=False)
        if install_state.source_root
        else _candidate_source_root()
    )
    if source_root is None:
        raise ValueError("ECC source baseline is not configured.")

    drifted_paths = [
        operation.destination_relative_path or ""
        for operation in install_state.operations
        if operation.destination_relative_path and _operation_drifted(workspace_root, operation)
    ]
    warnings = [
        f"Cannot safely uninstall because managed file drifted: {relative_path}"
        for relative_path in drifted_paths
    ]
    planned_paths = _unique_ordered(
        [
            *(operation.destination_relative_path or "" for operation in install_state.operations if operation.destination_relative_path),
            _relative_surface_path(workspace_root, install_state.install_state_path),
        ]
    )

    if not apply:
        return EccWorkspaceRepairRun(
            mode="uninstall_preview",
            status="planned",
            headline="ECC uninstall plan ready",
            summary="The recorded ECC-managed workspace surface can be removed.",
            project_path=str(workspace_root),
            baseline_path=str(source_root),
            profile=install_state.profile,
            selected_modules=install_state.selected_modules,
            skipped_modules=install_state.skipped_modules,
            planned_paths=planned_paths,
            warnings=tuple(warnings),
            doctor=_doctor_for_workspace(
                workspace_root,
                baseline_root=source_root,
                install_state=install_state,
            ),
        )

    if drifted_paths:
        joined = ", ".join(drifted_paths)
        raise ValueError(f"Cannot uninstall because managed files have drifted: {joined}")

    changed_paths: list[str] = []
    for operation in reversed(install_state.operations):
        _restore_operation(workspace_root, operation)
        if operation.destination_relative_path:
            changed_paths.append(operation.destination_relative_path)
    install_state.install_state_path.unlink(missing_ok=True)
    changed_paths.append(_relative_surface_path(workspace_root, install_state.install_state_path))
    _cleanup_empty_parents(install_state.install_state_path, stop_at=workspace_root)
    return EccWorkspaceRepairRun(
        mode="uninstall_apply",
        status="uninstalled",
        headline="ECC install removed",
        summary="The recorded ECC-managed workspace surface has been removed.",
        project_path=str(workspace_root),
        baseline_path=str(source_root),
        profile=install_state.profile,
        selected_modules=install_state.selected_modules,
        skipped_modules=install_state.skipped_modules,
        changed_paths=_unique_ordered(changed_paths),
        warnings=tuple(warnings),
        doctor=None,
    )


def run_ecc_workspace_repair(
    project_path: str | Path,
    *,
    apply: bool,
) -> EccWorkspaceRepairRun:
    workspace_root = Path(project_path).expanduser().resolve(strict=False)
    source_root = _candidate_source_root()
    if source_root is None:
        raise ValueError("ECC source baseline is not configured.")

    install_state = _load_install_state(workspace_root)
    if install_state is not None:
        drifted_operations = tuple(
            operation
            for operation in install_state.operations
            if operation.destination_relative_path and _operation_drifted(workspace_root, operation)
        )
        planned_paths = _unique_ordered(
            [
                operation.destination_relative_path or ""
                for operation in drifted_operations
                if operation.destination_relative_path
            ]
        )
        if not apply:
            return EccWorkspaceRepairRun(
                mode="repair_preview",
                status="planned" if planned_paths else "noop",
                headline="ECC repair preview ready",
                summary="The recorded ECC-managed files can be restored."
                if planned_paths
                else "The recorded ECC-managed files are already healthy.",
                project_path=str(workspace_root),
                baseline_path=str(source_root),
                profile=install_state.profile,
                selected_modules=install_state.selected_modules,
                skipped_modules=install_state.skipped_modules,
                planned_paths=planned_paths,
                doctor=_doctor_for_workspace(
                    workspace_root,
                    baseline_root=source_root,
                    install_state=install_state,
                ),
            )
        changed_paths: list[str] = []
        for operation in drifted_operations:
            _write_operation(workspace_root, operation)
            if operation.destination_relative_path:
                changed_paths.append(operation.destination_relative_path)
        return EccWorkspaceRepairRun(
            mode="repair_apply",
            status="repaired" if changed_paths else "noop",
            headline="ECC repair applied",
            summary="The recorded ECC-managed files have been restored."
            if changed_paths
            else "No recorded ECC-managed files needed repair.",
            project_path=str(workspace_root),
            baseline_path=str(source_root),
            profile=install_state.profile,
            selected_modules=install_state.selected_modules,
            skipped_modules=install_state.skipped_modules,
            changed_paths=_unique_ordered(changed_paths),
            doctor=_doctor_for_workspace(
                workspace_root,
                baseline_root=source_root,
                install_state=install_state,
            ),
        )

    repair_entries = _legacy_surface_repairs(workspace_root, source_root)
    planned_paths = _unique_ordered(
        [*(entry.relative_path for entry in repair_entries), ".codex/ecc-install-state.json"]
    )

    if not apply:
        return EccWorkspaceRepairRun(
            mode="repair_preview",
            status="planned",
            headline="ECC repair plan ready",
            summary="The missing ECC surface and install state can be restored.",
            project_path=str(workspace_root),
            baseline_path=str(source_root),
            profile=None,
            selected_modules=(_PROJECT_CODEX_INSTALL_MODULE_ID,),
            planned_paths=planned_paths,
            doctor=_doctor_for_workspace(
                workspace_root,
                baseline_root=source_root,
                install_state=None,
            ),
        )

    changed_paths: list[str] = []
    for entry in repair_entries:
        source_text = _read_text(source_root / entry.relative_path)
        if source_text is None:
            continue
        destination_path = workspace_root / entry.relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(source_text, encoding="utf-8")
        changed_paths.append(entry.relative_path)

    operations = _snapshot_legacy_operations(workspace_root)
    _write_install_state(
        workspace_root,
        source_root=source_root,
        profile=None,
        selected_modules=(_PROJECT_CODEX_INSTALL_MODULE_ID,),
        skipped_modules=(),
        legacy_mode=True,
        operations=operations,
    )
    changed_paths.append(".codex/ecc-install-state.json")
    resulting_state = _load_install_state(workspace_root)
    doctor = _doctor_for_workspace(
        workspace_root,
        baseline_root=source_root,
        install_state=resulting_state,
    )
    return EccWorkspaceRepairRun(
        mode="repair_apply",
        status="repaired",
        headline="ECC repair applied",
        summary="The ECC workspace surface and install state have been restored.",
        project_path=str(workspace_root),
        baseline_path=str(source_root),
        profile=None,
        selected_modules=(_PROJECT_CODEX_INSTALL_MODULE_ID,),
        changed_paths=_unique_ordered(changed_paths),
        doctor=doctor,
    )
