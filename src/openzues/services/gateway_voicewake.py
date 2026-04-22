from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DEFAULT_VOICE_WAKE_TRIGGERS = ("openclaw", "claude")
_MAX_VOICE_WAKE_TRIGGERS = 32
_MAX_VOICE_WAKE_TRIGGER_LENGTH = 64


@dataclass(frozen=True, slots=True)
class GatewayVoiceWakeConfig:
    triggers: tuple[str, ...]
    updated_at_ms: int = 0


def default_voicewake_triggers() -> tuple[str, ...]:
    return _DEFAULT_VOICE_WAKE_TRIGGERS


def normalize_voicewake_triggers(value: object) -> list[str]:
    raw = value if isinstance(value, list) else []
    cleaned: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if not trimmed:
            continue
        cleaned.append(trimmed[:_MAX_VOICE_WAKE_TRIGGER_LENGTH])
        if len(cleaned) >= _MAX_VOICE_WAKE_TRIGGERS:
            break
    return cleaned if cleaned else list(_DEFAULT_VOICE_WAKE_TRIGGERS)


class GatewayVoiceWakeService:
    def __init__(self, data_dir: Path) -> None:
        self._config_path = data_dir / "settings" / "voicewake.json"

    def load(self) -> GatewayVoiceWakeConfig:
        if not self._config_path.exists():
            return GatewayVoiceWakeConfig(triggers=default_voicewake_triggers())
        try:
            payload = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return GatewayVoiceWakeConfig(triggers=default_voicewake_triggers())
        if not isinstance(payload, dict):
            return GatewayVoiceWakeConfig(triggers=default_voicewake_triggers())
        updated_at_ms = payload.get("updatedAtMs")
        return GatewayVoiceWakeConfig(
            triggers=tuple(normalize_voicewake_triggers(payload.get("triggers"))),
            updated_at_ms=(
                updated_at_ms
                if isinstance(updated_at_ms, int) and updated_at_ms > 0
                else 0
            ),
        )

    def set_triggers(self, triggers: list[str], *, now_ms: int) -> GatewayVoiceWakeConfig:
        normalized_triggers = tuple(normalize_voicewake_triggers(triggers))
        config = GatewayVoiceWakeConfig(
            triggers=normalized_triggers,
            updated_at_ms=max(0, int(now_ms)),
        )
        self._write_config(config)
        return config

    def _write_config(self, config: GatewayVoiceWakeConfig) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "triggers": list(config.triggers),
            "updatedAtMs": config.updated_at_ms,
        }
        self._config_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
