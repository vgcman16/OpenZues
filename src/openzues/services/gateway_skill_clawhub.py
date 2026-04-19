from __future__ import annotations

import asyncio
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path

_DEFAULT_TIMEOUT_MS = 10 * 60_000


class GatewaySkillClawHubUnavailableError(RuntimeError):
    pass


class GatewaySkillClawHubService:
    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        launcher: tuple[str, ...] | None = None,
        resolve_launcher: bool = True,
        command_runner: Callable[..., Awaitable[tuple[int, str, str]]] | None = None,
    ) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).expanduser()
        self._launcher = launcher if launcher is not None else (
            _resolve_launcher() if resolve_launcher else None
        )
        self._command_runner = command_runner or _run_command

    async def install(
        self,
        *,
        slug: str,
        version: str | None = None,
        force: bool = False,
        timeout_ms: int | None = None,
    ) -> dict[str, object]:
        command = self._command_prefix() + _install_args(
            slug=slug,
            workspace_root=self.workspace_root,
            version=version,
            force=force,
        )
        await self._run(command, timeout_ms=timeout_ms)
        return {
            "ok": True,
            "source": "clawhub",
            "action": "install",
            "slug": slug,
            "version": version,
            "force": force,
            "command": list(command),
            "workspaceDir": str(self.workspace_root),
            "skillsDir": str(self.workspace_root / "skills"),
        }

    async def update(
        self,
        *,
        slug: str | None = None,
        all_installed: bool = False,
        version: str | None = None,
        force: bool = False,
        timeout_ms: int | None = None,
    ) -> dict[str, object]:
        command = self._command_prefix() + _update_args(
            slug=slug,
            all_installed=all_installed,
            workspace_root=self.workspace_root,
            version=version,
            force=force,
        )
        await self._run(command, timeout_ms=timeout_ms)
        return {
            "ok": True,
            "source": "clawhub",
            "action": "update",
            "slug": slug,
            "version": version,
            "force": force,
            "all": all_installed,
            "command": list(command),
            "workspaceDir": str(self.workspace_root),
            "skillsDir": str(self.workspace_root / "skills"),
        }

    async def _run(self, command: tuple[str, ...], *, timeout_ms: int | None) -> None:
        return_code, stdout, stderr = await self._command_runner(
            command,
            cwd=self.workspace_root,
            timeout_ms=(max(1, int(timeout_ms)) if timeout_ms is not None else None),
        )
        if return_code != 0:
            detail = (stderr or stdout or f"exit code {return_code}").strip()
            raise RuntimeError(f"ClawHub command failed: {detail}")

    def _command_prefix(self) -> tuple[str, ...]:
        if not self._launcher:
            raise GatewaySkillClawHubUnavailableError(
                "ClawHub CLI is not available on the gateway host."
            )
        return self._launcher


def _resolve_launcher() -> tuple[str, ...] | None:
    return ("clawhub",) if shutil.which("clawhub") else None


def _install_args(
    *,
    slug: str,
    workspace_root: Path,
    version: str | None,
    force: bool,
) -> tuple[str, ...]:
    command = [
        "install",
        slug,
        "--workdir",
        str(workspace_root),
        "--dir",
        "skills",
        "--no-input",
    ]
    if version:
        command.extend(["--version", version])
    if force:
        command.append("--force")
    return tuple(command)


def _update_args(
    *,
    slug: str | None,
    all_installed: bool,
    workspace_root: Path,
    version: str | None,
    force: bool,
) -> tuple[str, ...]:
    if all_installed:
        if version:
            raise ValueError("version is not supported with all=true")
        command = ["update", "--all"]
    elif slug:
        command = ["update", slug]
    else:
        raise ValueError("either slug or all=true is required")
    command.extend(["--workdir", str(workspace_root), "--dir", "skills", "--no-input"])
    if version:
        command.extend(["--version", version])
    if force:
        command.append("--force")
    return tuple(command)


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
        raise GatewaySkillClawHubUnavailableError(
            "ClawHub CLI is not available on the gateway host."
        ) from exc

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=None if timeout_ms is None else timeout_ms / 1000,
        )
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise RuntimeError(f"ClawHub command timed out after {timeout_ms} ms") from exc
    return (
        int(process.returncode or 0),
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )
