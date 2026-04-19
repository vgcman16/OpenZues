from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PROVIDER_LABELS: tuple[tuple[str, str], ...] = (
    ("elevenlabs", "ElevenLabs"),
    ("microsoft", "Microsoft"),
    ("minimax", "MiniMax"),
    ("openai", "OpenAI"),
)
_PROVIDER_AVAILABILITY: dict[str, bool] = {
    "elevenlabs": False,
    "microsoft": True,
    "minimax": False,
    "openai": False,
}
_PROVIDER_ALIASES: dict[str, str] = {
    "edge": "microsoft",
}


@dataclass(frozen=True, slots=True)
class GatewayTtsPreferences:
    enabled: bool = False
    provider: str | None = None
    updated_at_ms: int = 0


class GatewayTtsService:
    def __init__(
        self,
        data_dir: Path | None = None,
        *,
        prefs_path_loader: Callable[[], str | None] | None = None,
    ) -> None:
        self._prefs_path = data_dir / "settings" / "tts-prefs.json" if data_dir else None
        self._prefs_path_loader = prefs_path_loader
        self._memory_prefs = GatewayTtsPreferences()

    def build_status(self) -> dict[str, Any]:
        prefs = self._load_prefs()
        return {
            "enabled": prefs.enabled,
            "auto": "on" if prefs.enabled else "off",
            "provider": prefs.provider,
            "fallbackProvider": None,
            "fallbackProviders": [],
            "prefsPath": self._resolved_prefs_path(),
            "providerStates": [
                {
                    "id": provider_id,
                    "label": label,
                    "available": _PROVIDER_AVAILABILITY.get(provider_id, False),
                    "selected": prefs.provider == provider_id,
                }
                for provider_id, label in _PROVIDER_LABELS
            ],
        }

    def build_provider_catalog(self) -> dict[str, Any]:
        prefs = self._load_prefs()
        return {
            "providers": [provider_id for provider_id, _ in _PROVIDER_LABELS],
            "active": prefs.provider,
        }

    def set_enabled(self, enabled: bool, *, now_ms: int) -> dict[str, Any]:
        current = self._load_prefs()
        self._save_prefs(
            GatewayTtsPreferences(
                enabled=enabled,
                provider=current.provider,
                updated_at_ms=max(0, int(now_ms)),
            )
        )
        return self.build_status()

    def set_provider(self, provider: str, *, now_ms: int) -> dict[str, Any]:
        current = self._load_prefs()
        self._save_prefs(
            GatewayTtsPreferences(
                enabled=current.enabled,
                provider=normalize_tts_provider(provider),
                updated_at_ms=max(0, int(now_ms)),
            )
        )
        return self.build_status()

    def current_provider(self) -> str | None:
        return self._load_prefs().provider

    def _load_prefs(self) -> GatewayTtsPreferences:
        if self._prefs_path is None:
            return self._memory_prefs
        if not self._prefs_path.exists():
            return GatewayTtsPreferences()
        try:
            payload = json.loads(self._prefs_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return GatewayTtsPreferences()
        if not isinstance(payload, dict):
            return GatewayTtsPreferences()
        updated_at_ms = payload.get("updatedAtMs")
        return GatewayTtsPreferences(
            enabled=bool(payload.get("enabled")),
            provider=normalize_tts_provider(payload.get("provider")),
            updated_at_ms=(
                updated_at_ms
                if isinstance(updated_at_ms, int) and updated_at_ms > 0
                else 0
            ),
        )

    def _save_prefs(self, prefs: GatewayTtsPreferences) -> None:
        if self._prefs_path is None:
            self._memory_prefs = prefs
            return
        self._prefs_path.parent.mkdir(parents=True, exist_ok=True)
        self._prefs_path.write_text(
            json.dumps(
                {
                    "enabled": prefs.enabled,
                    "provider": prefs.provider,
                    "updatedAtMs": prefs.updated_at_ms,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _resolved_prefs_path(self) -> str | None:
        if self._prefs_path_loader is not None:
            return self._prefs_path_loader()
        return str(self._prefs_path) if self._prefs_path is not None else None


def normalize_tts_provider(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip().lower()
    if not trimmed:
        return None
    canonical = _PROVIDER_ALIASES.get(trimmed, trimmed)
    return canonical
