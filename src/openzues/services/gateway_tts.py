from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
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
    persona: str | None = None
    updated_at_ms: int = 0


@dataclass(frozen=True, slots=True)
class GatewayTtsPersona:
    id: str
    label: str
    description: str | None = None
    provider: str | None = None
    fallback_policy: str | None = None
    providers: tuple[str, ...] = ()


class GatewayTtsService:
    def __init__(
        self,
        data_dir: Path | None = None,
        *,
        prefs_path_loader: Callable[[], str | None] | None = None,
        personas: Mapping[str, Mapping[str, object]]
        | Iterable[Mapping[str, object]]
        | None = None,
        config_loader: Callable[[], Mapping[str, object] | None] | None = None,
    ) -> None:
        self._prefs_path = data_dir / "settings" / "tts-prefs.json" if data_dir else None
        self._prefs_path_loader = prefs_path_loader
        self._configured_personas = personas
        self._config_loader = config_loader
        self._memory_prefs = GatewayTtsPreferences()

    def build_status(self) -> dict[str, Any]:
        prefs = self._load_prefs()
        active_persona = self._active_persona(prefs)
        return {
            "enabled": prefs.enabled,
            "auto": "on" if prefs.enabled else "off",
            "provider": prefs.provider,
            "persona": active_persona.id if active_persona is not None else None,
            "personas": [
                {
                    "id": persona.id,
                    "label": persona.label,
                    "description": persona.description,
                    "provider": persona.provider,
                }
                for persona in self._list_personas()
            ],
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

    def build_personas(self) -> dict[str, Any]:
        prefs = self._load_prefs()
        active_persona = self._active_persona(prefs)
        return {
            "active": active_persona.id if active_persona is not None else None,
            "personas": [
                {
                    "id": persona.id,
                    "label": persona.label,
                    "description": persona.description,
                    "provider": persona.provider,
                    "fallbackPolicy": persona.fallback_policy,
                    "providers": list(persona.providers),
                }
                for persona in self._list_personas()
            ],
        }

    def set_enabled(self, enabled: bool, *, now_ms: int) -> dict[str, Any]:
        current = self._load_prefs()
        self._save_prefs(
            GatewayTtsPreferences(
                enabled=enabled,
                provider=current.provider,
                persona=current.persona,
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
                persona=current.persona,
                updated_at_ms=max(0, int(now_ms)),
            )
        )
        return self.build_status()

    def set_persona(self, persona: object, *, now_ms: int) -> dict[str, Any]:
        requested = _optional_tts_string(persona)
        current = self._load_prefs()
        if requested is None or requested.lower() in {"off", "none", "default"}:
            self._save_prefs(
                GatewayTtsPreferences(
                    enabled=current.enabled,
                    provider=current.provider,
                    persona=None,
                    updated_at_ms=max(0, int(now_ms)),
                )
            )
            return {"persona": None}
        normalized = requested.lower()
        personas = {entry.id: entry for entry in self._list_personas()}
        selected = personas.get(normalized)
        if selected is None:
            raise ValueError("Invalid persona. Use a configured TTS persona id.")
        self._save_prefs(
            GatewayTtsPreferences(
                enabled=current.enabled,
                provider=current.provider,
                persona=selected.id,
                updated_at_ms=max(0, int(now_ms)),
            )
        )
        return {"persona": selected.id}

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
        raw_persona = payload.get("persona")
        if raw_persona is None and isinstance(payload.get("tts"), dict):
            raw_persona = payload["tts"].get("persona")
        return GatewayTtsPreferences(
            enabled=bool(payload.get("enabled")),
            provider=normalize_tts_provider(payload.get("provider")),
            persona=_normalize_tts_persona_id(raw_persona),
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
                    "persona": prefs.persona,
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

    def _active_persona(self, prefs: GatewayTtsPreferences) -> GatewayTtsPersona | None:
        if prefs.persona is None:
            return None
        for persona in self._list_personas():
            if persona.id == prefs.persona:
                return persona
        return None

    def _list_personas(self) -> tuple[GatewayTtsPersona, ...]:
        personas: dict[str, GatewayTtsPersona] = {}
        for persona in _personas_from_config(self._load_config()):
            personas[persona.id] = persona
        for persona in _normalize_tts_personas(self._configured_personas):
            personas[persona.id] = persona
        return tuple(personas.values())

    def _load_config(self) -> Mapping[str, object] | None:
        if self._config_loader is None:
            return None
        try:
            return self._config_loader()
        except Exception:
            return None


def normalize_tts_provider(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip().lower()
    if not trimmed:
        return None
    canonical = _PROVIDER_ALIASES.get(trimmed, trimmed)
    return canonical


def _normalize_tts_persona_id(value: object) -> str | None:
    text = _optional_tts_string(value)
    return text.lower() if text is not None else None


def _optional_tts_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def _personas_from_config(config: Mapping[str, object] | None) -> tuple[GatewayTtsPersona, ...]:
    if not isinstance(config, Mapping):
        return ()
    messages = config.get("messages")
    if not isinstance(messages, Mapping):
        return ()
    tts = messages.get("tts")
    if not isinstance(tts, Mapping):
        return ()
    personas = tts.get("personas")
    return _normalize_tts_personas(personas if isinstance(personas, Mapping) else None)


def _normalize_tts_personas(
    personas: Mapping[str, Mapping[str, object]] | Iterable[Mapping[str, object]] | None,
) -> tuple[GatewayTtsPersona, ...]:
    if personas is None:
        return ()
    entries: Iterable[tuple[object, object]]
    if isinstance(personas, Mapping):
        entries = personas.items()
    else:
        entries = (
            (
                entry.get("id") if isinstance(entry, Mapping) else None,
                entry,
            )
            for entry in personas
        )
    normalized: list[GatewayTtsPersona] = []
    seen: set[str] = set()
    for raw_id, raw_entry in entries:
        persona_id = _normalize_tts_persona_id(raw_id)
        if persona_id is None or persona_id in seen or not isinstance(raw_entry, Mapping):
            continue
        label = _optional_tts_string(raw_entry.get("label")) or persona_id
        provider = normalize_tts_provider(raw_entry.get("provider"))
        fallback_policy = _optional_tts_string(raw_entry.get("fallbackPolicy"))
        if fallback_policy not in {None, "preserve-persona", "provider-defaults", "fail"}:
            fallback_policy = None
        normalized.append(
            GatewayTtsPersona(
                id=persona_id,
                label=label,
                description=_optional_tts_string(raw_entry.get("description")),
                provider=provider,
                fallback_policy=fallback_policy,
                providers=_normalize_tts_persona_providers(raw_entry.get("providers")),
            )
        )
        seen.add(persona_id)
    return tuple(normalized)


def _normalize_tts_persona_providers(value: object) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return ()
    providers: list[str] = []
    seen: set[str] = set()
    for raw_provider in value:
        provider = normalize_tts_provider(raw_provider)
        if provider is None or provider in seen:
            continue
        providers.append(provider)
        seen.add(provider)
    return tuple(providers)
