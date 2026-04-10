from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from openzues.database import utcnow
from openzues.schemas import DiagnosticCheck, DiagnosticStatus, DiagnosticsView


@dataclass(slots=True)
class CommandProbe:
    returncode: int | None
    stdout: str
    stderr: str
    error: str | None = None


class EnvironmentService:
    def _run(self, args: list[str], timeout: int = 10) -> CommandProbe:
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return CommandProbe(
                returncode=result.returncode,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
            )
        except Exception as exc:  # pragma: no cover - environment specific
            return CommandProbe(
                returncode=None,
                stdout="",
                stderr="",
                error=str(exc),
            )

    def collect(self) -> DiagnosticsView:
        checks: list[DiagnosticCheck] = []

        python_exe = shutil.which("python")
        checks.append(
            DiagnosticCheck(
                key="python",
                label="Python runtime",
                status="ok" if python_exe else "fail",
                detail=python_exe or "Python executable not found on PATH.",
                value=self._run(["python", "--version"]).stdout if python_exe else None,
            )
        )

        git_exe = shutil.which("git")
        checks.append(
            DiagnosticCheck(
                key="git",
                label="Git CLI",
                status="ok" if git_exe else "fail",
                detail=git_exe or "Git executable not found on PATH.",
                value=self._run(["git", "--version"]).stdout if git_exe else None,
            )
        )

        gh_exe = shutil.which("gh")
        gh_probe = self._run(["gh", "auth", "status"]) if gh_exe else None
        gh_status: DiagnosticStatus = (
            "ok" if gh_probe and gh_probe.returncode == 0 else ("warn" if gh_exe else "fail")
        )
        gh_detail = (
            gh_probe.stdout or gh_probe.stderr
            if gh_probe is not None
            else "GitHub CLI not found on PATH."
        )
        checks.append(
            DiagnosticCheck(
                key="github_cli",
                label="GitHub CLI auth",
                status=gh_status,
                detail=gh_detail.splitlines()[0] if gh_detail else "GitHub CLI status unavailable.",
                value=gh_exe,
                action="Run `gh auth login` if you want PR and repo automation."
                if gh_status != "ok"
                else None,
            )
        )

        codex_exe = shutil.which("codex")
        codex_probe = self._run(["codex", "--version"]) if codex_exe else None
        if codex_probe is None:
            codex_status: DiagnosticStatus = "fail"
            codex_detail = "Codex executable not found on PATH."
            codex_action = "Install or expose Codex CLI before using stdio transport."
        elif codex_probe.returncode == 0:
            codex_status = "ok"
            codex_detail = codex_probe.stdout or codex_probe.stderr or "Codex CLI is available."
            codex_action = None
        elif codex_probe.error and "Access is denied" in codex_probe.error:
            codex_status = "warn"
            codex_detail = codex_probe.error
            codex_action = "This Windows install may need WebSocket transport instead of stdio."
        else:
            codex_status = "warn"
            codex_detail = codex_probe.stderr or codex_probe.error or "Codex probe did not succeed."
            codex_action = "Verify the local Codex install or switch to WebSocket transport."
        checks.append(
            DiagnosticCheck(
                key="codex_cli",
                label="Codex CLI launchability",
                status=codex_status,
                detail=codex_detail,
                value=codex_exe,
                action=codex_action,
            )
        )

        openai_key = os.getenv("OPENAI_API_KEY")
        checks.append(
            DiagnosticCheck(
                key="openai_api_key",
                label="OPENAI_API_KEY",
                status="info" if openai_key else "warn",
                detail="Environment variable present."
                if openai_key
                else "Not set in the current shell environment.",
                action="Set it only if your Codex workflow needs shell-visible API credentials."
                if not openai_key
                else None,
            )
        )

        code_dir = os.getenv("CODEX_HOME")
        checks.append(
            DiagnosticCheck(
                key="codex_home",
                label="CODEX_HOME",
                status="info" if code_dir else "warn",
                detail=code_dir or "Using the default Codex home directory.",
                action=(
                    "Set CODEX_HOME if you want a custom profile, skills, or automation "
                    "location."
                )
                if not code_dir
                else None,
            )
        )

        workspace = Path.cwd()
        checks.append(
            DiagnosticCheck(
                key="workspace",
                label="OpenZues workspace",
                status="ok",
                detail=str(workspace),
                value="writable" if os.access(workspace, os.W_OK) else "read-only",
            )
        )

        return DiagnosticsView(checks=checks, checked_at=utcnow())
