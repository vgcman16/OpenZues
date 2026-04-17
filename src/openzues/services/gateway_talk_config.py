from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


class GatewayTalkConfigService:
    def __init__(
        self,
        *,
        talk_loader: Callable[[], Mapping[str, Any] | None] | None = None,
        session_main_key_loader: Callable[[], str | None] | None = None,
        seam_color_loader: Callable[[], str | None] | None = None,
    ) -> None:
        self._talk_loader = talk_loader
        self._session_main_key_loader = session_main_key_loader
        self._seam_color_loader = seam_color_loader

    def build_snapshot(self, *, include_secrets: bool = False) -> dict[str, Any]:
        config: dict[str, Any] = {}
        talk_payload = self._build_talk_payload(include_secrets=include_secrets)
        if talk_payload is not None:
            config["talk"] = talk_payload
        session_main_key = self._load_session_main_key()
        if session_main_key is not None:
            config["session"] = {"mainKey": session_main_key}
        seam_color = self._load_seam_color()
        if seam_color is not None:
            config["ui"] = {"seamColor": seam_color}
        return {"config": config}

    def _build_talk_payload(self, *, include_secrets: bool) -> dict[str, Any] | None:
        if self._talk_loader is None:
            return None
        raw_talk = _as_mapping(self._talk_loader())
        if raw_talk is None:
            return None
        providers = _normalize_provider_map(
            raw_talk.get("providers"),
            include_secrets=include_secrets,
        )
        configured_provider = _optional_non_empty_string(raw_talk.get("provider"))
        resolved_payload = _as_mapping(raw_talk.get("resolved"))
        resolved_provider = _optional_non_empty_string(
            resolved_payload.get("provider") if resolved_payload is not None else None
        )
        resolved_config = _normalize_provider_config(
            resolved_payload.get("config") if resolved_payload is not None else None,
            include_secrets=include_secrets,
        )

        if resolved_provider is None:
            resolved_provider = configured_provider
        if resolved_provider is None and providers is not None and len(providers) == 1:
            resolved_provider = next(iter(providers))
        if resolved_provider is None:
            return None

        if resolved_config is None and providers is not None:
            resolved_config = providers.get(resolved_provider)
        if resolved_config is None:
            resolved_config = {}

        payload: dict[str, Any] = {
            "provider": configured_provider or resolved_provider,
            "resolved": {
                "provider": resolved_provider,
                "config": resolved_config,
            },
        }
        if providers:
            payload["providers"] = providers
        interrupt_on_speech = raw_talk.get("interruptOnSpeech")
        if isinstance(interrupt_on_speech, bool):
            payload["interruptOnSpeech"] = interrupt_on_speech
        silence_timeout_ms = _positive_int(raw_talk.get("silenceTimeoutMs"))
        if silence_timeout_ms is not None:
            payload["silenceTimeoutMs"] = silence_timeout_ms
        return payload

    def _load_session_main_key(self) -> str | None:
        if self._session_main_key_loader is None:
            return None
        return _optional_non_empty_string(self._session_main_key_loader())

    def _load_seam_color(self) -> str | None:
        if self._seam_color_loader is None:
            return None
        return _optional_non_empty_string(self._seam_color_loader())


def _as_mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _optional_non_empty_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _positive_int(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return None
    return value


def _normalize_provider_map(
    value: object,
    *,
    include_secrets: bool,
) -> dict[str, dict[str, Any]] | None:
    raw_mapping = _as_mapping(value)
    if raw_mapping is None:
        return None
    providers: dict[str, dict[str, Any]] = {}
    for raw_provider_id, raw_config in raw_mapping.items():
        provider_id = _optional_non_empty_string(raw_provider_id)
        if provider_id is None:
            continue
        normalized_config = _normalize_provider_config(
            raw_config,
            include_secrets=include_secrets,
        )
        if normalized_config is None:
            continue
        providers[provider_id] = normalized_config
    return providers or None


def _normalize_provider_config(
    value: object,
    *,
    include_secrets: bool,
) -> dict[str, Any] | None:
    raw_config = _as_mapping(value)
    if raw_config is None:
        return None
    normalized: dict[str, Any] = {}
    for key, raw_value in raw_config.items():
        if raw_value is None:
            continue
        if key == "apiKey":
            normalized[key] = raw_value if include_secrets else "__OPENCLAW_REDACTED__"
            continue
        normalized[str(key)] = raw_value
    return normalized
