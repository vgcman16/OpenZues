from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict, TypeGuard

from openzues.services.session_keys import (
    classify_session_key_shape,
    is_valid_agent_id,
    normalize_agent_id,
)

_DEFAULT_VOICE_WAKE_TRIGGERS = ("openclaw", "claude")
_MAX_VOICE_WAKE_TRIGGERS = 32
_MAX_VOICE_WAKE_TRIGGER_LENGTH = 64
_MAX_VOICE_WAKE_ROUTES = 32


class VoiceWakeRouteTarget(TypedDict, total=False):
    mode: str
    agentId: str
    sessionKey: str


class VoiceWakeRouteRule(TypedDict):
    trigger: str
    target: VoiceWakeRouteTarget


@dataclass(frozen=True, slots=True)
class GatewayVoiceWakeConfig:
    triggers: tuple[str, ...]
    updated_at_ms: int = 0


@dataclass(frozen=True, slots=True)
class GatewayVoiceWakeRoutingConfig:
    version: int
    default_target: VoiceWakeRouteTarget
    routes: tuple[VoiceWakeRouteRule, ...]
    updated_at_ms: int = 0

    def to_payload(self) -> dict[str, object]:
        return {
            "version": 1,
            "defaultTarget": dict(self.default_target),
            "routes": [
                {
                    "trigger": str(route["trigger"]),
                    "target": dict(route["target"]),
                }
                for route in self.routes
            ],
            "updatedAtMs": self.updated_at_ms,
        }


def default_voicewake_triggers() -> tuple[str, ...]:
    return _DEFAULT_VOICE_WAKE_TRIGGERS


def _default_voicewake_routing_config() -> GatewayVoiceWakeRoutingConfig:
    return GatewayVoiceWakeRoutingConfig(
        version=1,
        default_target={"mode": "current"},
        routes=(),
        updated_at_ms=0,
    )


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


def normalize_voicewake_trigger_word(value: str) -> str:
    normalized_tokens: list[str] = []
    for token in value.lower().split():
        stripped = token
        while stripped and unicodedata.category(stripped[0])[0] in {"P", "S"}:
            stripped = stripped[1:]
        while stripped and unicodedata.category(stripped[-1])[0] in {"P", "S"}:
            stripped = stripped[:-1]
        if stripped:
            normalized_tokens.append(stripped)
    return " ".join(normalized_tokens)


def _normalize_optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _is_plain_object(value: object) -> TypeGuard[dict[str, object]]:
    return isinstance(value, dict)


def _is_canonical_agent_session_key(value: str) -> bool:
    trimmed = value.strip()
    return classify_session_key_shape(trimmed) == "agent" and not any(
        len(part) == 0 for part in trimmed.split(":")
    )


def _normalize_voicewake_route_target(value: object) -> VoiceWakeRouteTarget | None:
    if not _is_plain_object(value):
        return None
    mode = _normalize_optional_string(value.get("mode"))
    if mode == "current":
        return {"mode": "current"}
    agent_id = _normalize_optional_string(value.get("agentId"))
    session_key = _normalize_optional_string(value.get("sessionKey"))
    if agent_id and not session_key:
        return {"agentId": normalize_agent_id(agent_id)}
    if session_key and not agent_id:
        return {"sessionKey": session_key}
    return None


def _normalize_voicewake_route_rule(value: object) -> VoiceWakeRouteRule | None:
    if not _is_plain_object(value):
        return None
    trigger_raw = _normalize_optional_string(value.get("trigger"))
    if trigger_raw is None:
        return None
    trigger = normalize_voicewake_trigger_word(trigger_raw)
    if not trigger:
        return None
    target = _normalize_voicewake_route_target(value.get("target"))
    if target is None:
        return None
    return {"trigger": trigger, "target": target}


def _validate_voicewake_route_target(value: object, label: str) -> None:
    if not _is_plain_object(value):
        raise ValueError(f"{label} must be an object")
    mode = _normalize_optional_string(value.get("mode"))
    agent_id = _normalize_optional_string(value.get("agentId"))
    session_key = _normalize_optional_string(value.get("sessionKey"))
    if mode is not None:
        if mode != "current":
            raise ValueError(f'{label}.mode must be "current" when provided')
        if agent_id is not None or session_key is not None:
            raise ValueError(f"{label} cannot mix mode with agentId or sessionKey")
        return
    if agent_id is not None and session_key is not None:
        raise ValueError(f"{label} cannot include both agentId and sessionKey")
    if agent_id is not None:
        if not is_valid_agent_id(agent_id):
            raise ValueError(f"{label}.agentId must be a valid agent id")
        return
    if session_key is not None:
        if not _is_canonical_agent_session_key(session_key):
            raise ValueError(f"{label}.sessionKey must be a canonical agent session key")
        return
    raise ValueError(f"{label} must include mode, agentId, or sessionKey")


def validate_voicewake_routing_config_input(config: object) -> None:
    if not _is_plain_object(config):
        raise ValueError("config must be an object")
    if "defaultTarget" in config:
        _validate_voicewake_route_target(
            config.get("defaultTarget"),
            "config.defaultTarget",
        )
    routes = config.get("routes")
    if routes is not None and not isinstance(routes, list):
        raise ValueError("config.routes must be an array")
    if isinstance(routes, list):
        if len(routes) > _MAX_VOICE_WAKE_ROUTES:
            raise ValueError(
                f"config.routes must contain at most {_MAX_VOICE_WAKE_ROUTES} entries"
            )
        normalized_triggers: dict[str, int] = {}
        for index, route in enumerate(routes):
            if not _is_plain_object(route):
                raise ValueError(f"config.routes[{index}] must be an object")
            trigger = _normalize_optional_string(route.get("trigger"))
            normalized_trigger = (
                normalize_voicewake_trigger_word(trigger) if trigger is not None else ""
            )
            if trigger is None or not normalized_trigger:
                raise ValueError(f"config.routes[{index}].trigger must be a non-empty string")
            if len(trigger) > _MAX_VOICE_WAKE_TRIGGER_LENGTH:
                raise ValueError(
                    f"config.routes[{index}].trigger must be at most "
                    f"{_MAX_VOICE_WAKE_TRIGGER_LENGTH} characters"
                )
            duplicate_index = normalized_triggers.get(normalized_trigger)
            if duplicate_index is not None:
                raise ValueError(
                    f"config.routes[{index}].trigger duplicates "
                    f"config.routes[{duplicate_index}].trigger after normalization"
                )
            normalized_triggers[normalized_trigger] = index
            _validate_voicewake_route_target(
                route.get("target"),
                f"config.routes[{index}].target",
            )


def normalize_voicewake_routing_config(input_value: object) -> GatewayVoiceWakeRoutingConfig:
    if not _is_plain_object(input_value):
        return _default_voicewake_routing_config()
    default_target: VoiceWakeRouteTarget = (
        _normalize_voicewake_route_target(input_value.get("defaultTarget"))
        or {"mode": "current"}
    )
    routes_raw = input_value.get("routes")
    routes = (
        tuple(
            route
            for route in (
                _normalize_voicewake_route_rule(entry)
                for entry in routes_raw
            )
            if route is not None
        )
        if isinstance(routes_raw, list)
        else ()
    )
    updated_at_ms = input_value.get("updatedAtMs")
    return GatewayVoiceWakeRoutingConfig(
        version=1,
        default_target=default_target,
        routes=routes,
        updated_at_ms=(
            int(updated_at_ms)
            if isinstance(updated_at_ms, int) and not isinstance(updated_at_ms, bool)
            and updated_at_ms > 0
            else 0
        ),
    )


class GatewayVoiceWakeService:
    def __init__(self, data_dir: Path) -> None:
        self._config_path = data_dir / "settings" / "voicewake.json"
        self._routing_config_path = data_dir / "settings" / "voicewake-routing.json"

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

    def load_routing(self) -> GatewayVoiceWakeRoutingConfig:
        if not self._routing_config_path.exists():
            return _default_voicewake_routing_config()
        try:
            payload = json.loads(self._routing_config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _default_voicewake_routing_config()
        return normalize_voicewake_routing_config(payload)

    def set_routing(
        self,
        config: dict[str, object],
        *,
        now_ms: int,
    ) -> GatewayVoiceWakeRoutingConfig:
        validate_voicewake_routing_config_input(config)
        normalized = normalize_voicewake_routing_config(config)
        next_config = GatewayVoiceWakeRoutingConfig(
            version=1,
            default_target=normalized.default_target,
            routes=normalized.routes,
            updated_at_ms=max(0, int(now_ms)),
        )
        self._write_routing_config(next_config)
        return next_config

    def _write_routing_config(self, config: GatewayVoiceWakeRoutingConfig) -> None:
        self._routing_config_path.parent.mkdir(parents=True, exist_ok=True)
        self._routing_config_path.write_text(
            json.dumps(config.to_payload(), indent=2),
            encoding="utf-8",
        )
