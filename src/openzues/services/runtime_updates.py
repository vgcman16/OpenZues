from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from openzues.database import Database

logger = logging.getLogger(__name__)
_UPDATE_LOG_TAIL_CHARS = 8000


RuntimeUpdateCommandRunner = Callable[
    [list[str], Path, int | None],
    Awaitable[dict[str, object]],
]


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


def _trim_update_log_tail(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value[-_UPDATE_LOG_TAIL_CHARS:]


def _update_command_exit_code(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _update_step_log(step: dict[str, object]) -> dict[str, object]:
    log = step.get("log")
    return log if isinstance(log, dict) else {}


def _update_step_exit_code(step: dict[str, object]) -> int | None:
    return _update_command_exit_code(_update_step_log(step).get("exitCode"))


def _update_step_stdout_tail(step: dict[str, object]) -> str | None:
    stdout_tail = _update_step_log(step).get("stdoutTail")
    if not isinstance(stdout_tail, str):
        return None
    return stdout_tail.strip() or None


async def _default_update_command_runner(
    argv: list[str],
    cwd: Path,
    timeout_ms: int | None,
) -> dict[str, object]:
    timeout_seconds = timeout_ms / 1000 if timeout_ms is not None else None

    def run() -> dict[str, object]:
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (
                exc.stdout.decode(errors="replace")
                if isinstance(exc.stdout, bytes)
                else exc.stdout
            )
            stderr = (
                exc.stderr.decode(errors="replace")
                if isinstance(exc.stderr, bytes)
                else exc.stderr
            )
            return {
                "stdout": stdout or "",
                "stderr": stderr or "command timed out",
                "exitCode": None,
            }
        except OSError as exc:
            return {"stdout": "", "stderr": str(exc), "exitCode": 1}
        return {
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "exitCode": completed.returncode,
        }

    return await asyncio.to_thread(run)


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
        update_command_runner: RuntimeUpdateCommandRunner | None = None,
    ) -> None:
        self.database = database
        self.poll_interval_seconds = max(5, int(poll_interval_seconds))
        self._restart_callback = restart_callback
        self._revision_resolver = revision_resolver
        self._update_command_runner = update_command_runner or _default_update_command_runner
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

    async def run_update(self, *, timeout_ms: int | None = None) -> dict[str, object]:
        started_at = time.monotonic()
        steps: list[dict[str, object]] = []
        root = self.repo_root
        if root is None:
            return {
                "status": "error",
                "mode": "unknown",
                "reason": "repo-root-unavailable",
                "steps": steps,
                "durationMs": 0,
            }
        before_sha = self._snapshot.current_revision or self.startup_revision
        before = {"sha": before_sha, "version": None}

        status_step = await self._run_update_command_step(
            "git status",
            ["git", "status", "--porcelain"],
            timeout_ms=timeout_ms,
        )
        steps.append(status_step)
        if _update_step_exit_code(status_step) != 0:
            return self._build_update_command_result(
                status="error",
                reason="git-status-failed",
                root=root,
                before=before,
                after=None,
                steps=steps,
                started_at=started_at,
            )
        status_stdout = _update_step_stdout_tail(status_step)
        if status_stdout:
            return self._build_update_command_result(
                status="skipped",
                reason="dirty",
                root=root,
                before=before,
                after=before,
                steps=steps,
                started_at=started_at,
            )

        for name, argv, reason in (
            ("git fetch", ["git", "fetch", "--all", "--prune", "--tags"], "fetch-failed"),
            ("git pull", ["git", "pull", "--ff-only"], "pull-failed"),
            (
                "deps install",
                [sys.executable, "-m", "pip", "install", "-e", "."],
                "deps-install-failed",
            ),
            ("build", [sys.executable, "-m", "compileall", "-q", "src"], "build-failed"),
        ):
            step = await self._run_update_command_step(name, argv, timeout_ms=timeout_ms)
            steps.append(step)
            if _update_step_exit_code(step) != 0:
                return self._build_update_command_result(
                    status="error",
                    reason=reason,
                    root=root,
                    before=before,
                    after=None,
                    steps=steps,
                    started_at=started_at,
                )

        after_sha = await asyncio.to_thread(self._revision_resolver, root)
        after = {"sha": after_sha, "version": None}
        self._snapshot.last_checked_at = _utcnow_iso()
        self._snapshot.current_revision = after_sha
        self._snapshot.safe_to_restart = await self._is_safe_restart_boundary()
        self._snapshot.pending_revision = (
            after_sha
            if after_sha is not None and after_sha != self.startup_revision
            else None
        )
        self._snapshot.pending_restart = self._snapshot.pending_revision is not None
        self._snapshot.last_error = None
        return self._build_update_command_result(
            status="ok",
            reason=None,
            root=root,
            before=before,
            after=after,
            steps=steps,
            started_at=started_at,
        )

    async def _run_update_command_step(
        self,
        name: str,
        argv: list[str],
        *,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        root = self.repo_root
        if root is None:
            return {
                "name": name,
                "command": " ".join(argv),
                "cwd": "",
                "durationMs": 0,
                "log": {
                    "stdoutTail": None,
                    "stderrTail": "repo root unavailable",
                    "exitCode": 1,
                },
            }
        started_at = time.monotonic()
        result = await self._update_command_runner(argv, root, timeout_ms)
        return {
            "name": name,
            "command": " ".join(argv),
            "cwd": str(root),
            "durationMs": int((time.monotonic() - started_at) * 1000),
            "log": {
                "stdoutTail": _trim_update_log_tail(result.get("stdout")),
                "stderrTail": _trim_update_log_tail(result.get("stderr")),
                "exitCode": _update_command_exit_code(result.get("exitCode")),
            },
        }

    def _build_update_command_result(
        self,
        *,
        status: str,
        reason: str | None,
        root: Path,
        before: dict[str, str | None],
        after: dict[str, str | None] | None,
        steps: list[dict[str, object]],
        started_at: float,
    ) -> dict[str, object]:
        result: dict[str, object] = {
            "status": status,
            "mode": "git",
            "root": str(root),
            "before": before,
            "after": after,
            "steps": steps,
            "durationMs": int((time.monotonic() - started_at) * 1000),
        }
        if reason is not None:
            result["reason"] = reason
        return result

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
