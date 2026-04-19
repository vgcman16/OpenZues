from __future__ import annotations

import asyncio
import os
import re
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(?P<frontmatter>.*?)\r?\n---\s*\r?\n?", re.DOTALL)
_PLATFORM_ALIASES = {
    "windows": {"windows", "win32"},
    "macos": {"macos", "darwin"},
    "linux": {"linux"},
}
_DEFAULT_TIMEOUT_MS = 10 * 60_000


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


def _platform_matches_current(value: object) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in _PLATFORM_ALIASES[_current_platform()]


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


class GatewaySkillInstallService:
    def __init__(
        self,
        *,
        codex_home: Path | None = None,
        workspace_root: Path | None = None,
        command_runner: Callable[..., Awaitable[tuple[int, str, str]]] | None = None,
    ) -> None:
        self.codex_home = (codex_home or _default_codex_home()).expanduser()
        self.workspace_root = (workspace_root or Path.cwd()).expanduser()
        self._command_runner = command_runner or _run_command

    async def install(
        self,
        *,
        name: str,
        install_id: str,
        dangerously_force_unsafe_install: bool = False,
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        del dangerously_force_unsafe_install
        match = self._resolve_install_spec(name=name, install_id=install_id)
        command = _install_command(match["install_spec"])
        resolved_timeout_ms = (
            _DEFAULT_TIMEOUT_MS
            if timeout_ms is None
            else max(1, int(timeout_ms))
        )
        return_code, stdout, stderr = await self._command_runner(
            tuple(command),
            cwd=match["base_dir"],
            timeout_ms=resolved_timeout_ms,
        )
        if return_code != 0:
            detail = (stderr or stdout or f"exit code {return_code}").strip()
            raise RuntimeError(
                f"skills.install failed for {match['name']} ({install_id}): {detail}"
            )
        return {
            "ok": True,
            "name": match["name"],
            "skillKey": match["skill_key"],
            "installId": install_id,
            "kind": match["kind"],
            "label": match["label"],
            "bins": list(match["bins"]),
            "command": command,
            "cwd": str(match["base_dir"]),
        }

    def _resolve_install_spec(self, *, name: str, install_id: str) -> dict[str, Any]:
        wanted_name = name.strip().lower()
        if not wanted_name:
            raise ValueError("name is required")
        wanted_install_id = install_id.strip()
        if not wanted_install_id:
            raise ValueError("installId is required")
        for skill_path in self._iter_skill_paths():
            frontmatter = _frontmatter_payload(skill_path)
            skill_name = (
                str(frontmatter.get("name") or skill_path.parent.name).strip()
                or skill_path.parent.name
            )
            if skill_name.lower() != wanted_name:
                continue
            metadata = frontmatter.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            install_options = metadata.get("install")
            install_options = install_options if isinstance(install_options, list) else []
            for install_spec in install_options:
                if not isinstance(install_spec, dict):
                    continue
                install_os = _string_list(install_spec.get("os"))
                if install_os and not any(
                    _platform_matches_current(candidate) for candidate in install_os
                ):
                    continue
                resolved_install_id = (
                    str(install_spec.get("id") or "").strip()
                    or str(install_spec.get("kind") or "").strip()
                )
                if resolved_install_id != wanted_install_id:
                    continue
                skill_key = (
                    str(metadata.get("skillKey") or skill_path.parent.name).strip()
                    or skill_path.parent.name
                )
                label = (
                    str(install_spec.get("label") or "").strip()
                    or f"Install {skill_name}"
                )
                kind = str(install_spec.get("kind") or "").strip()
                return {
                    "name": skill_name,
                    "skill_key": skill_key,
                    "label": label,
                    "kind": kind,
                    "bins": _string_list(install_spec.get("bins")),
                    "base_dir": skill_path.parent,
                    "install_spec": install_spec,
                }
            raise ValueError(
                f"install option '{wanted_install_id}' not found for skill '{skill_name}'"
            )
        raise ValueError(f"skill '{name.strip()}' not found")

    def _iter_skill_paths(self) -> list[Path]:
        candidates: tuple[Path, ...] = (
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


def _install_command(install_spec: dict[str, Any]) -> list[str]:
    kind = str(install_spec.get("kind") or "").strip().lower()
    if kind == "brew":
        formula = _required_spec_string(install_spec, "formula")
        return ["brew", "install", formula]
    if kind == "uv":
        package = _required_spec_string(install_spec, "package", fallback_key="tool")
        return ["uv", "tool", "install", package]
    if kind == "go":
        package = _required_spec_string(install_spec, "package")
        return ["go", "install", package]
    if kind == "node":
        package = _required_spec_string(install_spec, "package")
        manager = str(
            install_spec.get("manager")
            or install_spec.get("nodeManager")
            or "npm"
        ).strip().lower()
        if manager == "npm":
            return ["npm", "install", "-g", package]
        if manager == "pnpm":
            return ["pnpm", "add", "-g", package]
        if manager == "yarn":
            return ["yarn", "global", "add", package]
        if manager == "bun":
            return ["bun", "add", "-g", package]
        raise ValueError(f"unsupported node manager '{manager}'")
    raise ValueError(f"install kind '{kind}' is not wired in OpenZues yet")


def _required_spec_string(
    install_spec: dict[str, Any],
    key: str,
    *,
    fallback_key: str | None = None,
) -> str:
    value = str(install_spec.get(key) or "").strip()
    if not value and fallback_key is not None:
        value = str(install_spec.get(fallback_key) or "").strip()
    if not value:
        raise ValueError(f"install option is missing '{key}'")
    return value


async def _run_command(
    argv: tuple[str, ...],
    *,
    cwd: Path,
    timeout_ms: int | None,
) -> tuple[int, str, str]:
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"installer command not found: {argv[0]}") from exc

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=None if timeout_ms is None else timeout_ms / 1000,
        )
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise RuntimeError(f"installer command timed out after {timeout_ms} ms") from exc
    return (
        int(process.returncode or 0),
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )
