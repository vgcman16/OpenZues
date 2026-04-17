from __future__ import annotations

from collections.abc import Callable
from typing import Any


class GatewayTtsService:
    def __init__(
        self,
        *,
        prefs_path_loader: Callable[[], str | None] | None = None,
    ) -> None:
        self._prefs_path_loader = prefs_path_loader

    def build_status(self) -> dict[str, Any]:
        return {
            "enabled": False,
            "auto": "off",
            "provider": None,
            "fallbackProvider": None,
            "fallbackProviders": [],
            "prefsPath": self._prefs_path_loader() if self._prefs_path_loader else None,
            "providerStates": [],
        }

    def build_provider_catalog(self) -> dict[str, Any]:
        return {
            "providers": [],
            "active": None,
        }
