from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from openzues.database import Database

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _default_repo_root() -> Path | None:
    return _find_repo_root(Path(__file__).resolve())


def _resolve_git_revision(repo_root: Path) -> str | None:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        completed = subprocess.run(
            [git, "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    revision = completed.stdout.strip()
    return revision or None


@dataclass(slots=True)
class RuntimeUpdateSnapshot:
    enabled: bool
    repo_root: str | None
    startup_revision: str | None
    current_revision: str | None
    pending_revision: str | None
    pending_restart: bool
    restart_in_progress: bool
    safe_to_restart: bool
    last_checked_at: str | None
    last_restart_at: str | None
    last_error: str | None
    auto_restart: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class RuntimeUpdateService:
    def __init__(
        self,
        database: Database,
        *,
        enabled: bool,
        poll_interval_seconds: int = 20,
        restart_callback: Callable[[], Awaitable[None]],
        repo_root: Path | None = None,
        revision_resolver: Callable[[Path], str | None] = _resolve_git_revision,
    ) -> None:
        self.database = database
        self.poll_interval_seconds = max(5, int(poll_interval_seconds))
        self._restart_callback = restart_callback
        self._revision_resolver = revision_resolver
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self.repo_root = repo_root or _default_repo_root()
        self.startup_revision = (
            revision_resolver(self.repo_root) if self.repo_root is not None else None
        )
        active = enabled and self.repo_root is not None and self.startup_revision is not None
        self._snapshot = RuntimeUpdateSnapshot(
            enabled=active,
            repo_root=str(self.repo_root) if self.repo_root is not None else None,
            startup_revision=self.startup_revision,
            current_revision=self.startup_revision,
            pending_revision=None,
            pending_restart=False,
            restart_in_progress=False,
            safe_to_restart=False,
            last_checked_at=None,
            last_restart_at=None,
            last_error=None,
            auto_restart=enabled,
        )

    def snapshot(self) -> dict[str, object]:
        return self._snapshot.to_dict()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._runner_loop(),
            name="openzues-runtime-updates",
        )

    async def close(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def tick(self) -> bool:
        self._snapshot.last_checked_at = _utcnow_iso()
        if not self._snapshot.enabled or self.repo_root is None or self.startup_revision is None:
            return False
        try:
            current_revision = await asyncio.to_thread(
                self._revision_resolver,
                self.repo_root,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            self._snapshot.last_error = str(exc)
            logger.exception("Runtime update poll failed.")
            return False

        self._snapshot.current_revision = current_revision
        self._snapshot.safe_to_restart = await self._is_safe_restart_boundary()
        if current_revision is None or current_revision == self.startup_revision:
            self._snapshot.pending_revision = None
            self._snapshot.pending_restart = False
            self._snapshot.restart_in_progress = False
            self._snapshot.last_error = None
            return False

        self._snapshot.pending_revision = current_revision
        self._snapshot.pending_restart = True
        if not self._snapshot.safe_to_restart or self._snapshot.restart_in_progress:
            return False

        self._snapshot.restart_in_progress = True
        self._snapshot.last_restart_at = _utcnow_iso()
        try:
            await self._restart_callback()
        except Exception as exc:  # pragma: no cover - defensive guard
            self._snapshot.last_error = str(exc)
            self._snapshot.restart_in_progress = False
            logger.exception("Runtime self-update restart failed.")
            return False
        return True

    async def _runner_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:  # pragma: no cover - defensive guard
                logger.exception("Runtime update loop crashed.")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval_seconds,
                )
            except TimeoutError:
                continue

    async def _is_safe_restart_boundary(self) -> bool:
        missions = await self.database.list_missions()
        return not any(bool(mission.get("in_progress")) for mission in missions)
