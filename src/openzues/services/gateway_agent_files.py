from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openzues.database import Database

_ALLOWED_AGENT_IDS = {"main", "openzues"}
_ALLOWED_FILES = {
    "AGENTS.md": Path("AGENTS.md"),
    "SOUL.md": Path("SOUL.md"),
    "TOOLS.md": Path("TOOLS.md"),
    "IDENTITY.md": Path("IDENTITY.md"),
    "USER.md": Path("USER.md"),
    "HEARTBEAT.md": Path("HEARTBEAT.md"),
    "BOOTSTRAP.md": Path("BOOTSTRAP.md"),
    "MEMORY.md": Path("MEMORY.md"),
    "memory.md": Path("memory.md"),
    ".codex/AGENTS.md": Path(".codex") / "AGENTS.md",
}
_MEMORY_FILE_NAMES = ("MEMORY.md", "memory.md")


class GatewayAgentFilesService:
    def __init__(
        self,
        *,
        database: Database | None = None,
        workspace_dir: Path | str | None = None,
    ) -> None:
        self._database = database
        self._workspace_dir = Path(workspace_dir) if workspace_dir is not None else None

    async def list_files(self, *, agent_id: str) -> dict[str, Any]:
        resolved_agent_id, workspace_dir = await self._resolve_agent_file_context(agent_id)
        files = [
            self._file_summary(workspace_dir, name=name, relative_path=relative_path)
            for name, relative_path in _listed_agent_files(workspace_dir)
        ]
        return {
            "agentId": resolved_agent_id,
            "workspace": str(workspace_dir),
            "files": files,
        }

    async def get_file(self, *, agent_id: str, name: str) -> dict[str, Any]:
        resolved_agent_id, workspace_dir = await self._resolve_agent_file_context(agent_id)
        relative_path = _ALLOWED_FILES.get(name)
        if relative_path is None:
            raise ValueError("unsupported agent file")
        file_path = workspace_dir / relative_path
        if not file_path.exists() or not file_path.is_file():
            return {
                "agentId": resolved_agent_id,
                "workspace": str(workspace_dir),
                "file": {
                    "name": name,
                    "path": str(file_path),
                    "missing": True,
                },
            }
        resolved_file_path = file_path.resolve()
        if not _is_within_workspace(resolved_file_path, workspace_dir.resolve()):
            raise ValueError("agent file escapes workspace")
        stat = resolved_file_path.stat()
        return {
            "agentId": resolved_agent_id,
            "workspace": str(workspace_dir),
            "file": {
                "name": name,
                "path": str(file_path),
                "missing": False,
                "size": stat.st_size,
                "updatedAtMs": int(stat.st_mtime * 1000),
                "content": resolved_file_path.read_text(encoding="utf-8"),
            },
        }

    async def set_file(self, *, agent_id: str, name: str, content: str) -> dict[str, Any]:
        resolved_agent_id, workspace_dir = await self._resolve_agent_file_context(agent_id)
        relative_path = _ALLOWED_FILES.get(name)
        if relative_path is None:
            raise ValueError("unsupported agent file")
        resolved_workspace_dir = workspace_dir.resolve()
        file_path = workspace_dir / relative_path
        resolved_file_path = file_path.resolve(strict=False)
        if not _is_within_workspace(resolved_file_path, resolved_workspace_dir):
            raise ValueError("agent file escapes workspace")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        stat = file_path.stat()
        return {
            "ok": True,
            "agentId": resolved_agent_id,
            "workspace": str(workspace_dir),
            "file": {
                "name": name,
                "path": str(file_path),
                "missing": False,
                "size": stat.st_size,
                "updatedAtMs": int(stat.st_mtime * 1000),
                "content": content,
            },
        }

    async def _resolve_workspace_dir(self) -> Path:
        if self._workspace_dir is not None:
            return self._workspace_dir
        if self._database is not None:
            bootstrap = await self._database.get_gateway_bootstrap()
            default_cwd = str((bootstrap or {}).get("default_cwd") or "").strip()
            if default_cwd:
                return Path(default_cwd)
        return Path.cwd()

    async def _resolve_agent_file_context(self, agent_id: str) -> tuple[str, Path]:
        normalized_agent_id = agent_id.strip().lower()
        if normalized_agent_id in _ALLOWED_AGENT_IDS:
            return "main", await self._resolve_workspace_dir()
        if self._database is None:
            raise ValueError("unknown agent id")
        row = await self._database.get_gateway_agent(normalized_agent_id)
        if row is None:
            raise ValueError("unknown agent id")
        workspace = str(row.get("workspace") or "").strip()
        if not workspace:
            raise ValueError("agent workspace is missing")
        return str(row["agent_id"]), Path(workspace)

    def _file_summary(
        self,
        workspace_dir: Path,
        *,
        name: str,
        relative_path: Path,
    ) -> dict[str, Any]:
        file_path = workspace_dir / relative_path
        if not file_path.exists() or not file_path.is_file():
            return {
                "name": name,
                "path": str(file_path),
                "missing": True,
            }
        stat = file_path.stat()
        return {
            "name": name,
            "path": str(file_path),
            "missing": False,
            "size": stat.st_size,
            "updatedAtMs": int(stat.st_mtime * 1000),
        }


def _is_within_workspace(candidate: Path, workspace_dir: Path) -> bool:
    try:
        candidate.relative_to(workspace_dir)
    except ValueError:
        return False
    return True


def _listed_agent_files(workspace_dir: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for name, relative_path in _ALLOWED_FILES.items():
        if name in _MEMORY_FILE_NAMES:
            continue
        files.append((name, relative_path))
    primary_memory = _ALLOWED_FILES["MEMORY.md"]
    legacy_memory = _ALLOWED_FILES["memory.md"]
    if (workspace_dir / primary_memory).is_file():
        files.append(("MEMORY.md", primary_memory))
    elif (workspace_dir / legacy_memory).is_file():
        files.append(("memory.md", legacy_memory))
    else:
        files.append(("MEMORY.md", primary_memory))
    return files


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized_value = value.strip()
    if not normalized_value:
        return None
    try:
        parsed = datetime.fromisoformat(normalized_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
