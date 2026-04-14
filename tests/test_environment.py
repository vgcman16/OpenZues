from __future__ import annotations

from pathlib import Path

from openzues.services.codex_desktop import (
    DesktopDiscovery,
    DesktopSessionInfo,
)
from openzues.services.environment import CommandProbe, EnvironmentService


class FakeDesktopService:
    def __init__(self, discovery: DesktopDiscovery) -> None:
        self._discovery = discovery
        self.sandbox_mode = "danger-full-access"
        self.approval_policy = "never"

    def discover(self) -> DesktopDiscovery:
        return self._discovery

    def launch_policy_summary(self) -> str:
        return "launching with sandbox danger-full-access, approval never"

    def probe_executable(self, executable: Path) -> str:
        return f"{executable} --version"


def test_collect_demotes_windows_access_denied_when_desktop_bridge_exists(
    monkeypatch,
) -> None:
    discovery = DesktopDiscovery(
        source_path=Path(r"C:\Program Files\WindowsApps\OpenAI.Codex\codex.exe"),
        staged_path=Path(r"C:\Users\skull\AppData\Local\OpenZues\runtime\codex.exe"),
        staged_ready=True,
        session=DesktopSessionInfo(
            log_path=Path(r"C:\Users\skull\AppData\Local\Codex\codex-desktop.log"),
            last_seen_at="2026-04-13T23:00:00Z",
            transport="stdio",
            app_server_version="0.119.0-alpha.28",
            initialized=True,
            spawned_executable=r"C:\Users\skull\AppData\Local\OpenZues\runtime\codex.exe",
        ),
    )
    service = EnvironmentService(desktop_service=FakeDesktopService(discovery))

    def fake_which(command: str) -> str | None:
        mapping = {
            "python": r"C:\Python312\python.exe",
            "git": r"C:\Program Files\Git\bin\git.exe",
            "codex": r"C:\Users\skull\AppData\Local\Microsoft\WindowsApps\codex.exe",
        }
        return mapping.get(command)

    def fake_run(args: list[str], timeout: int = 10) -> CommandProbe:
        del timeout
        if args[:2] == ["python", "--version"]:
            return CommandProbe(returncode=0, stdout="Python 3.12.0", stderr="")
        if args[:2] == ["git", "--version"]:
            return CommandProbe(returncode=0, stdout="git version 2.49.0", stderr="")
        if args[:2] == ["codex", "--version"]:
            return CommandProbe(returncode=1, stdout="", stderr="Access is denied")
        if args[:3] == ["gh", "auth", "status"]:
            return CommandProbe(returncode=1, stdout="", stderr="not logged in")
        raise AssertionError(f"Unexpected probe: {args}")

    monkeypatch.setattr("openzues.services.environment.shutil.which", fake_which)
    monkeypatch.setattr(service, "_run", fake_run)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)

    diagnostics = service.collect()
    checks = {check.key: check for check in diagnostics.checks}

    assert checks["codex_cli"].status == "info"
    assert "Desktop transport can stage a runnable local Codex bridge" in checks["codex_cli"].detail
    assert checks["openai_api_key"].status == "info"
    assert "Desktop-authenticated Codex lanes can still operate without it" in checks[
        "openai_api_key"
    ].detail
    assert checks["codex_home"].status == "info"
    assert "default Codex home directory" in checks["codex_home"].detail


def test_collect_warns_when_codex_cli_is_missing_and_no_desktop_install(monkeypatch) -> None:
    discovery = DesktopDiscovery(
        source_path=None,
        staged_path=None,
        staged_ready=False,
        session=DesktopSessionInfo(),
    )
    service = EnvironmentService(desktop_service=FakeDesktopService(discovery))

    def fake_which(command: str) -> str | None:
        mapping = {
            "python": r"C:\Python312\python.exe",
            "git": r"C:\Program Files\Git\bin\git.exe",
        }
        return mapping.get(command)

    def fake_run(args: list[str], timeout: int = 10) -> CommandProbe:
        del timeout
        if args[:2] == ["python", "--version"]:
            return CommandProbe(returncode=0, stdout="Python 3.12.0", stderr="")
        if args[:2] == ["git", "--version"]:
            return CommandProbe(returncode=0, stdout="git version 2.49.0", stderr="")
        if args[:3] == ["gh", "auth", "status"]:
            return CommandProbe(returncode=1, stdout="", stderr="not logged in")
        raise AssertionError(f"Unexpected probe: {args}")

    monkeypatch.setattr("openzues.services.environment.shutil.which", fake_which)
    monkeypatch.setattr(service, "_run", fake_run)

    diagnostics = service.collect()
    checks = {check.key: check for check in diagnostics.checks}

    assert checks["codex_cli"].status == "warn"
    assert checks["codex_cli"].detail == "Codex executable not found on PATH."

