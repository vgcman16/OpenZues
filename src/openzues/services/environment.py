from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from openzues.database import utcnow
from openzues.schemas import DiagnosticCheck, DiagnosticStatus, DiagnosticsView
from openzues.services.codex_desktop import CodexDesktopService


def _desktop_source_label(source_kind: str | None) -> str:
    if source_kind is None:
        return "desktop runtime"
    return {
        "package": "packaged desktop runtime",
        "session": "desktop session runtime",
        "path": "PATH desktop runtime",
    }.get(source_kind, "desktop runtime")


def _paths_match(left: Path | None, right: Path | None) -> bool:
    if left is None or right is None:
        return False
    try:
        return left.resolve(strict=False) == right.resolve(strict=False)
    except OSError:
        return False


@dataclass(slots=True)
class CommandProbe:
    returncode: int | None
    stdout: str
    stderr: str
    error: str | None = None


class EnvironmentService:
    def __init__(self, desktop_service: CodexDesktopService | None = None) -> None:
        self.desktop_service = desktop_service or CodexDesktopService()

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
        desktop = self.desktop_service.discover()

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
            "ok" if gh_probe and gh_probe.returncode == 0 else "warn"
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
        codex_status: DiagnosticStatus
        codex_detail: str
        codex_action: str | None
        if codex_probe is None:
            if desktop.source_path is not None:
                codex_status = "info"
                codex_detail = (
                    "Codex executable is not on PATH, but Desktop transport can "
                    "stage a runnable local Codex bridge."
                )
                codex_action = (
                    "Use Desktop transport or Quick Connect to stage a runnable "
                    "Codex binary from the local desktop install."
                )
            else:
                codex_status = "warn"
                codex_detail = "Codex executable not found on PATH."
                codex_action = (
                    "Install or expose Codex CLI before using stdio transport, "
                    "or use WebSocket transport."
                )
        elif codex_probe.returncode == 0:
            codex_status = "ok"
            codex_detail = codex_probe.stdout or codex_probe.stderr or "Codex CLI is available."
            codex_action = None
        elif "Access is denied" in (codex_probe.stderr or codex_probe.error or codex_probe.stdout):
            if desktop.source_path is not None:
                codex_status = "info"
                codex_detail = (
                    "Direct PATH launch is blocked on this Windows install, but Desktop "
                    "transport can stage a runnable local Codex bridge."
                )
                codex_action = (
                    "Use Desktop transport or Quick Connect when a direct `codex` PATH "
                    "probe is blocked by Windows app execution policy."
                )
            else:
                codex_status = "warn"
                codex_detail = (
                    codex_probe.stderr
                    or codex_probe.error
                    or "Codex CLI launch is blocked."
                )
                codex_action = (
                    "Use Desktop transport. OpenZues can stage a local runnable "
                    "copy from the installed Codex desktop package."
                )
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

        if desktop.source_path is None:
            desktop_status: DiagnosticStatus = "warn"
            desktop_detail = (
                "Codex Desktop package was not found. Desktop transport is optional until "
                "you want one-click local bridging."
            )
            desktop_action = (
                "Install the Codex desktop app to use one-click desktop transport, "
                "or keep using WebSocket or saved disconnected lanes."
            )
            desktop_value = None
        else:
            desktop_status = "ok"
            source_label = _desktop_source_label(desktop.source_kind)
            desktop_detail = f"Found {source_label} at {desktop.source_path}"
            if desktop.package_version:
                desktop_detail += f" (package {desktop.package_version})"
            desktop_action = "Use Desktop transport or Quick Connect to attach the site to Codex."
            desktop_value = desktop.package_version
        checks.append(
            DiagnosticCheck(
                key="codex_desktop_install",
                label="Codex Desktop install",
                status=desktop_status,
                detail=desktop_detail,
                value=desktop_value,
                action=desktop_action,
            )
        )
        checks.append(
            DiagnosticCheck(
                key="codex_desktop_policy",
                label="Desktop mission policy",
                status="info",
                detail=(
                    "OpenZues will launch desktop Codex lanes "
                    f"{self.desktop_service.launch_policy_summary()}."
                ),
                value=(
                    f"sandbox={self.desktop_service.sandbox_mode or 'default'}, "
                    f"approval={self.desktop_service.approval_policy or 'default'}"
                ),
                action=(
                    "Set OPENZUES_DESKTOP_SANDBOX_MODE or "
                    "OPENZUES_DESKTOP_APPROVAL_POLICY to override this launch policy."
                ),
            )
        )

        if desktop.source_path is None:
            bridge_status: DiagnosticStatus = "warn"
            bridge_detail = (
                "Desktop bridge is unavailable until Codex Desktop is installed, "
                "but the gateway can still use WebSocket or saved lane posture."
            )
            bridge_value = None
            bridge_action = (
                "Install Codex Desktop when you want one-click local bridging, "
                "or keep using WebSocket transport."
            )
        elif desktop.staged_path is None or not desktop.staged_ready:
            bridge_source_label = _desktop_source_label(desktop.source_kind)
            bridge_status = "info"
            bridge_detail = (
                "OpenZues will stage a local runnable Codex binary from the "
                f"{bridge_source_label} on first desktop connection."
            )
            bridge_value = str(desktop.source_path)
            bridge_action = "Press Quick Connect in the site to create the bridge automatically."
        else:
            try:
                bridge_value = self.desktop_service.probe_executable(desktop.staged_path)
                bridge_status = "ok"
                bridge_detail = f"Staged runtime ready at {desktop.staged_path}"
                bridge_action = None
            except RuntimeError as exc:
                bridge_status = "warn"
                bridge_detail = str(exc)
                bridge_value = str(desktop.staged_path)
                bridge_action = "Reconnect the desktop instance to refresh the staged runtime."
        checks.append(
            DiagnosticCheck(
                key="codex_desktop_bridge",
                label="Codex Desktop bridge",
                status=bridge_status,
                detail=bridge_detail,
                value=bridge_value,
                action=bridge_action,
            )
        )

        if desktop.session.log_path is None:
            session_status: DiagnosticStatus = "warn"
            session_detail = "No recent Codex Desktop session logs were found."
            session_value = None
            session_action = (
                "Open Codex Desktop once if you want OpenZues to verify the latest desktop session."
            )
        else:
            session_status = "ok" if desktop.session.initialized else "info"
            transport = desktop.session.transport or "unknown"
            version = desktop.session.app_server_version or "unknown"
            spawned_detail = ""
            if desktop.session.spawned_executable:
                spawned_path = Path(desktop.session.spawned_executable)
                if _paths_match(spawned_path, desktop.staged_path):
                    spawned_detail = (
                        "spawned the staged bridge "
                        f"from the {_desktop_source_label(desktop.source_kind)} "
                        f"at {desktop.session.spawned_executable}, "
                    )
                elif _paths_match(spawned_path, desktop.source_path):
                    spawned_detail = (
                        "spawned the "
                        f"{_desktop_source_label(desktop.source_kind)} "
                        f"directly at {desktop.session.spawned_executable}, "
                    )
                else:
                    spawned_detail = f"spawned {desktop.session.spawned_executable}, "
            initialization_detail = (
                "initialized Codex CLI."
                if desktop.session.initialized
                else "did not finish Codex CLI initialization."
            )
            session_detail = (
                f"Last desktop session {spawned_detail}used {transport} transport and "
                f"reported app-server {version}, and {initialization_detail}"
            )
            session_value = desktop.session.last_seen_at
            session_action = None
        checks.append(
            DiagnosticCheck(
                key="codex_desktop_session",
                label="Latest desktop session",
                status=session_status,
                detail=session_detail,
                value=session_value,
                action=session_action,
            )
        )

        openai_key = os.getenv("OPENAI_API_KEY")
        checks.append(
            DiagnosticCheck(
                key="openai_api_key",
                label="OPENAI_API_KEY",
                status="info",
                detail="Environment variable present."
                if openai_key
                else (
                    "Not set in the current shell environment. Desktop-authenticated Codex "
                    "lanes can still operate without it."
                ),
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
                status="info",
                detail=code_dir
                or (
                    "Using the default Codex home directory, which is fine unless "
                    "you want a custom profile path."
                ),
                action=(
                    "Set CODEX_HOME if you want a custom profile, skills, or automation location."
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
