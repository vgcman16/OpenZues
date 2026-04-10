from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO


def _lock_file(handle: TextIO) -> None:
    if sys.platform.startswith("win"):
        import msvcrt

        handle.seek(0)
        if handle.tell() == 0 and handle.read(1) == "":
            handle.seek(0)
            handle.write("0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl  # pragma: no cover - exercised on non-Windows hosts

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file(handle: TextIO) -> None:
    if sys.platform.startswith("win"):
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl  # pragma: no cover - exercised on non-Windows hosts

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@dataclass(slots=True)
class ControlPlaneLease:
    path: Path
    acquired: bool = False
    owner_pid: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    _handle: TextIO | None = None

    def acquire(self, *, metadata: dict[str, Any] | None = None) -> bool:
        if self.acquired:
            return True

        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        try:
            _lock_file(handle)
        except OSError:
            self.acquired = False
            handle.close()
            self._refresh_observer_metadata()
            return False

        payload = {"pid": os.getpid(), **(metadata or {})}
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(payload))
        handle.flush()
        os.fsync(handle.fileno())
        self.metadata_path.write_text(json.dumps(payload), encoding="utf-8")

        self._handle = handle
        self.acquired = True
        self.owner_pid = os.getpid()
        self.metadata = payload
        return True

    def release(self) -> None:
        handle = self._handle
        if handle is None:
            return
        try:
            if self.acquired:
                _unlock_file(handle)
        finally:
            handle.close()
            if self.acquired:
                try:
                    self.metadata_path.unlink()
                except FileNotFoundError:
                    pass
            self._handle = None
            self.acquired = False

    @property
    def role(self) -> str:
        return "leader" if self.acquired else "observer"

    @property
    def metadata_path(self) -> Path:
        return self.path.with_suffix(f"{self.path.suffix}.meta.json")

    def _refresh_observer_metadata(self) -> None:
        try:
            raw = self.metadata_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            self.owner_pid = None
            self.metadata = {}
            return
        except OSError:
            self.owner_pid = None
            self.metadata = {}
            return

        if not raw:
            self.owner_pid = None
            self.metadata = {}
            return

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.owner_pid = None
            self.metadata = {}
            return

        self.metadata = payload if isinstance(payload, dict) else {}
        pid = self.metadata.get("pid")
        self.owner_pid = pid if isinstance(pid, int) else None
