from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openzues.services.gateway_canvas_documents import (
    ensure_canvas_host_default_index,
    resolve_canvas_root_dir,
)

CanvasReloadPublisher = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class CanvasFileSignature:
    mtime_ns: int
    size: int


class CanvasLiveReloadWatcher:
    def __init__(
        self,
        *,
        publish_reload: CanvasReloadPublisher,
        root_dir: str | Path | None = None,
        state_dir: str | Path | None = None,
        poll_interval_seconds: float = 0.25,
        debounce_seconds: float = 0.075,
    ) -> None:
        self._publish_reload = publish_reload
        self._root_dir = resolve_canvas_root_dir(root_dir=root_dir, state_dir=state_dir)
        self._poll_interval_seconds = max(0.01, float(poll_interval_seconds))
        self._debounce_seconds = max(0.0, float(debounce_seconds))
        self._snapshot: dict[str, CanvasFileSignature] | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._debounce_task: asyncio.Task[None] | None = None
        self._closed = False

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    async def start(self) -> None:
        if self._poll_task is not None and not self._poll_task.done():
            return
        self._closed = False
        await self.scan_once()
        self._poll_task = asyncio.create_task(self._poll_forever())

    async def close(self) -> None:
        self._closed = True
        await self._cancel_task(self._poll_task)
        await self._cancel_task(self._debounce_task)
        self._poll_task = None
        self._debounce_task = None

    async def scan_once(self) -> bool:
        snapshot = self._build_snapshot()
        if self._snapshot is None:
            self._snapshot = snapshot
            return False
        if snapshot == self._snapshot:
            return False
        self._snapshot = snapshot
        self._schedule_reload()
        return True

    async def flush_pending_reload(self) -> None:
        task = self._debounce_task
        if task is None:
            return
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _poll_forever(self) -> None:
        while not self._closed:
            await asyncio.sleep(self._poll_interval_seconds)
            await self.scan_once()

    def _schedule_reload(self) -> None:
        task = self._debounce_task
        if task is not None and not task.done():
            task.cancel()
        self._debounce_task = asyncio.create_task(self._publish_after_debounce())

    async def _publish_after_debounce(self) -> None:
        if self._debounce_seconds:
            await asyncio.sleep(self._debounce_seconds)
        if not self._closed:
            await self._publish_reload({"type": "canvas/reload"})

    def _build_snapshot(self) -> dict[str, CanvasFileSignature]:
        ensure_canvas_host_default_index(root_dir=self._root_dir)
        snapshot: dict[str, CanvasFileSignature] = {}
        for path in self._root_dir.rglob("*"):
            if self._should_ignore(path) or not path.is_file():
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            snapshot[str(path.relative_to(self._root_dir).as_posix())] = CanvasFileSignature(
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
            )
        return snapshot

    def _should_ignore(self, path: Path) -> bool:
        try:
            relative_parts = path.relative_to(self._root_dir).parts
        except ValueError:
            return True
        return any(part.startswith(".") or part == "node_modules" for part in relative_parts)

    async def _cancel_task(self, task: asyncio.Task[None] | None) -> None:
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
