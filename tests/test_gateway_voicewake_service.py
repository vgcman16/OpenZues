from __future__ import annotations

import json
import uuid
from pathlib import Path

from openzues.services.gateway_voicewake import (
    GatewayVoiceWakeService,
    default_voicewake_triggers,
    normalize_voicewake_triggers,
)


def _voicewake_tmp_dir() -> Path:
    root = Path(__file__).resolve().parent / ".tmp-voicewake"
    root.mkdir(parents=True, exist_ok=True)
    tmp_dir = root / f"voicewake-{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True, exist_ok=False)
    return tmp_dir


def test_voicewake_service_returns_defaults_when_missing() -> None:
    tmp_path = _voicewake_tmp_dir()
    service = GatewayVoiceWakeService(tmp_path)

    config = service.load()

    assert config.triggers == default_voicewake_triggers()
    assert config.updated_at_ms == 0


def test_voicewake_service_trims_and_persists_triggers_with_upstream_limits() -> None:
    tmp_path = _voicewake_tmp_dir()
    service = GatewayVoiceWakeService(tmp_path)
    long_trigger = "wake-" + ("x" * 128)
    oversized = [f"word-{index}" for index in range(40)]

    saved = service.set_triggers(
        ["  hello  ", "", long_trigger, "  world ", *oversized],
        now_ms=1234,
    )

    expected_triggers = (
        "hello",
        long_trigger[:64],
        "world",
        *(f"word-{index}" for index in range(29)),
    )

    assert saved.triggers == expected_triggers
    assert saved.updated_at_ms == 1234

    reloaded = service.load()
    assert reloaded.triggers == expected_triggers
    assert reloaded.updated_at_ms == 1234
    assert json.loads((tmp_path / "settings" / "voicewake.json").read_text(encoding="utf-8")) == {
        "triggers": list(expected_triggers),
        "updatedAtMs": 1234,
    }


def test_voicewake_service_normalizes_malformed_persisted_triggers() -> None:
    tmp_path = _voicewake_tmp_dir()
    settings_dir = tmp_path / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "voicewake.json").write_text(
        json.dumps(
            {
                "triggers": ["  wake  ", "", 42, None],
                "updatedAtMs": -1,
            }
        ),
        encoding="utf-8",
    )

    service = GatewayVoiceWakeService(tmp_path)

    config = service.load()

    assert config.triggers == ("wake",)
    assert config.updated_at_ms == 0
    assert normalize_voicewake_triggers(["", None, 7]) == list(default_voicewake_triggers())


def test_voicewake_service_falls_back_to_two_upstream_default_triggers() -> None:
    tmp_path = _voicewake_tmp_dir()
    service = GatewayVoiceWakeService(tmp_path)

    saved = service.set_triggers(["", "  "], now_ms=99)

    assert saved.triggers == ("openclaw", "claude")
