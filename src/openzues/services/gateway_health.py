from __future__ import annotations

from collections.abc import Callable
from typing import Any


class GatewayHealthService:
    def __init__(
        self,
        *,
        control_plane_role: Callable[[], str | None] | None = None,
        owner_pid: Callable[[], int | None] | None = None,
        lock_path: Callable[[], str | None] | None = None,
        runtime_update_snapshot: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self._control_plane_role = control_plane_role
        self._owner_pid = owner_pid
        self._lock_path = lock_path
        self._runtime_update_snapshot = runtime_update_snapshot

    def build_snapshot(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "controlPlane": self._control_plane_role() if self._control_plane_role else None,
            "ownerPid": self._owner_pid() if self._owner_pid else None,
            "lockPath": self._lock_path() if self._lock_path else None,
            "runtimeUpdate": (
                self._runtime_update_snapshot() if self._runtime_update_snapshot else {}
            ),
        }
