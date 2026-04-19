from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class GatewayTalkModeConfig:
    enabled: bool = False
    phase: str | None = None
    updated_at_ms: int = 0

    def to_payload(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "phase": self.phase,
        }


class GatewayTalkModeService:
    def __init__(self, data_dir: Path | None = None) -> None:
        self._config_path = data_dir / "settings" / "talk-mode.json" if data_dir else None
        self._memory_config = GatewayTalkModeConfig()

    def load(self) -> GatewayTalkModeConfig:
        if self._config_path is None:
            return self._memory_config
        if not self._config_path.exists():
            return GatewayTalkModeConfig()
        try:
            payload = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return GatewayTalkModeConfig()
        if not isinstance(payload, dict):
            return GatewayTalkModeConfig()
        updated_at_ms = payload.get("updatedAtMs")
        return GatewayTalkModeConfig(
            enabled=bool(payload.get("enabled")),
            phase=_normalize_phase(payload.get("phase")),
            updated_at_ms=(
                updated_at_ms
                if isinstance(updated_at_ms, int) and updated_at_ms > 0
                else 0
            ),
        )

    def set_mode(
        self,
        enabled: bool,
        *,
        phase: str | None,
        now_ms: int,
    ) -> GatewayTalkModeConfig:
        config = GatewayTalkModeConfig(
            enabled=bool(enabled),
            phase=_normalize_phase(phase),
            updated_at_ms=max(0, int(now_ms)),
        )
        if self._config_path is None:
            self._memory_config = config
            return config
        self._write_config(config)
        return config

    def _write_config(self, config: GatewayTalkModeConfig) -> None:
        if self._config_path is None:
            self._memory_config = config
            return
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps(
                {
                    "enabled": config.enabled,
                    "phase": config.phase,
                    "updatedAtMs": config.updated_at_ms,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def _normalize_phase(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None
