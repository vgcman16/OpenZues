from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

PACKAGE_GLOB = "OpenAI.Codex_*__2p2nqsd0c76g0/app/resources/codex.exe"
LOG_GLOB = "**/codex-desktop-*.log"


@dataclass(slots=True)
class DesktopSessionInfo:
    log_path: Path | None = None
    last_seen_at: str | None = None
    transport: str | None = None
    app_server_version: str | None = None
    initialized: bool = False
    spawned_executable: str | None = None


@dataclass(slots=True)
class DesktopDiscovery:
    source_path: Path | None
    staged_path: Path | None
    staged_ready: bool
    session: DesktopSessionInfo


@dataclass(slots=True)
class DesktopLaunchConfig:
    command: str
    args: str
    note: str
    version: str | None = None


class CodexDesktopService:
    def __init__(
        self,
        *,
        runtime_root: Path | None = None,
        package_root: Path | None = None,
        logs_root: Path | None = None,
    ) -> None:
        local_appdata = Path(
            os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        )
        self.runtime_root = runtime_root or (local_appdata / "OpenZues" / "runtime")
        self.package_root = package_root or Path(r"C:\Program Files\WindowsApps")
        self.logs_root = logs_root or (
            Path.home()
            / "AppData"
            / "Local"
            / "Packages"
            / "OpenAI.Codex_2p2nqsd0c76g0"
            / "LocalCache"
            / "Local"
            / "Codex"
            / "Logs"
        )

    def discover(self) -> DesktopDiscovery:
        source_path = self.find_source_executable()
        staged_path = self._staged_path_for(source_path) if source_path is not None else None
        staged_ready = staged_path.exists() if staged_path is not None else False
        return DesktopDiscovery(
            source_path=source_path,
            staged_path=staged_path,
            staged_ready=staged_ready,
            session=self._discover_session(),
        )

    def find_source_executable(self) -> Path | None:
        package_candidate = self._package_executable_candidate()
        if package_candidate is not None:
            return package_candidate
        session_candidate = self._session_executable_candidate()
        if session_candidate is not None:
            return session_candidate
        which_candidate = shutil.which("codex")
        if which_candidate:
            which_path = Path(which_candidate)
            if which_path.is_file():
                return which_path
        return None

    def stage_executable(self, source_path: Path) -> Path:
        source_path = source_path.expanduser().resolve()
        staged_path = self._staged_path_for(source_path)
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path = staged_path.parent / "metadata.json"
        source_stat = source_path.stat()
        metadata = {
            "source_path": str(source_path),
            "source_size": source_stat.st_size,
            "source_mtime_ns": source_stat.st_mtime_ns,
        }
        if staged_path.exists() and metadata_path.exists():
            try:
                existing = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = None
            if existing == metadata and staged_path.stat().st_size == source_stat.st_size:
                return staged_path
        temp_path = staged_path.with_suffix(".tmp")
        if temp_path.exists():
            temp_path.unlink()
        shutil.copy2(source_path, temp_path)
        temp_path.replace(staged_path)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return staged_path

    def probe_executable(self, executable: Path) -> str:
        try:
            result = subprocess.run(
                [str(executable), "--version"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except Exception as exc:  # pragma: no cover - environment specific
            raise RuntimeError(f"Failed to launch {executable}: {exc}") from exc
        output = (result.stdout or result.stderr).strip()
        if result.returncode != 0:
            detail = output or f"exit code {result.returncode}"
            raise RuntimeError(f"Launch probe failed for {executable}: {detail}")
        return output

    def resolve_launch(self) -> DesktopLaunchConfig:
        discovery = self.discover()
        source_path = discovery.source_path
        if source_path is None:
            raise RuntimeError(
                "Codex Desktop is not installed. "
                "Install the Codex desktop app or use WebSocket transport."
            )
        staged_path = self.stage_executable(source_path)
        version = self.probe_executable(staged_path)
        return DesktopLaunchConfig(
            command=str(staged_path),
            args="app-server",
            note=f"Staged from {source_path}",
            version=version,
        )

    def _discover_session(self) -> DesktopSessionInfo:
        if not self.logs_root.exists():
            return DesktopSessionInfo()
        log_candidates = [path for path in self.logs_root.glob(LOG_GLOB) if path.is_file()]
        if not log_candidates:
            return DesktopSessionInfo()
        log_candidates.sort(key=lambda path: path.stat().st_mtime_ns, reverse=True)
        log_path = log_candidates[0]
        session = DesktopSessionInfo(
            log_path=log_path,
            last_seen_at=self._isoformat_mtime(log_path),
        )
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "Starting app-server connection" in line:
                transport = self._match(r"transport=(\w+)", line)
                if transport:
                    session.transport = transport
                timestamp = self._match(r"^(\S+)", line)
                if timestamp:
                    session.last_seen_at = timestamp
            if "Current reported app-server version" in line:
                version = self._match(r"currentVersion=([^\s]+)", line)
                if version:
                    session.app_server_version = version
            if "Codex CLI initialized" in line:
                session.initialized = True
                timestamp = self._match(r"^(\S+)", line)
                if timestamp:
                    session.last_seen_at = timestamp
            if "stdio_transport_spawned" in line:
                executable = self._match(r'executablePath="([^"]+)"', line)
                if executable:
                    session.spawned_executable = executable
        return session

    def _package_executable_candidate(self) -> Path | None:
        if not self.package_root.exists():
            return None
        candidates = [path for path in self.package_root.glob(PACKAGE_GLOB) if path.is_file()]
        if not candidates:
            return None
        candidates.sort(
            key=lambda path: (
                self._package_version_key(path.parents[2].name),
                path.stat().st_mtime_ns,
            ),
            reverse=True,
        )
        return candidates[0]

    def _session_executable_candidate(self) -> Path | None:
        session = self._discover_session()
        if not session.spawned_executable:
            return None
        candidate = Path(session.spawned_executable)
        return candidate if candidate.is_file() else None

    def _staged_path_for(self, source_path: Path) -> Path:
        package_name = source_path.parents[2].name
        return self.runtime_root / package_name / source_path.name

    def _package_version_key(self, package_name: str) -> tuple[int, ...]:
        match = re.search(r"OpenAI\.Codex_([0-9.]+)_", package_name)
        if not match:
            return ()
        return tuple(int(part) for part in match.group(1).split("."))

    def _isoformat_mtime(self, path: Path) -> str:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()

    def _match(self, pattern: str, value: str) -> str | None:
        match = re.search(pattern, value)
        if not match:
            return None
        return match.group(1)
