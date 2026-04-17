from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from openzues.schemas import InstanceView

_DEFAULT_MODELS: tuple[dict[str, Any], ...] = (
    {
        "id": "gpt-5.4",
        "name": "gpt-5.4",
        "provider": "openai",
        "isDefault": True,
    },
    {
        "id": "gpt-5.4-mini",
        "name": "gpt-5.4-mini",
        "provider": "openai",
    },
)


class GatewayModelsService:
    def __init__(
        self,
        *,
        list_instance_views: Callable[[], Awaitable[list[InstanceView]]] | None = None,
    ) -> None:
        self._list_instance_views = list_instance_views

    async def build_catalog(self) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []
        seen: set[tuple[str | None, str]] = set()

        if self._list_instance_views is not None:
            for instance in await self._list_instance_views():
                for raw_entry in instance.models:
                    normalized = _normalize_model_entry(raw_entry)
                    if normalized is None:
                        continue
                    _append_model(entries, seen, normalized)

        for raw_entry in _DEFAULT_MODELS:
            _append_model(entries, seen, dict(raw_entry))

        return {"models": entries}


def _append_model(
    entries: list[dict[str, Any]],
    seen: set[tuple[str | None, str]],
    entry: dict[str, Any],
) -> None:
    provider = _optional_non_empty_string(entry.get("provider"))
    model_id = _optional_non_empty_string(entry.get("id"))
    if model_id is None:
        return
    key = (provider.lower() if provider is not None else None, model_id.lower())
    if key in seen:
        return
    seen.add(key)
    entries.append(entry)


def _normalize_model_entry(value: object) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None

    raw_identifier = _first_non_empty_string(
        value.get("id"),
        value.get("model"),
        value.get("slug"),
    )
    if raw_identifier is None:
        return None
    parsed_provider, parsed_model_id = _split_provider_prefixed_model(raw_identifier)
    provider = _first_non_empty_string(value.get("provider"), parsed_provider)
    model_id = parsed_model_id or raw_identifier
    name = _first_non_empty_string(
        value.get("displayName"),
        value.get("name"),
        model_id,
    )
    if name is None:
        return None

    normalized: dict[str, Any] = {"id": model_id, "name": name}
    if provider is not None:
        normalized["provider"] = provider

    alias = _optional_non_empty_string(value.get("alias"))
    if alias is not None:
        normalized["alias"] = alias

    description = _optional_non_empty_string(value.get("description"))
    if description is not None:
        normalized["description"] = description

    default_reasoning_effort = _optional_non_empty_string(
        value.get("defaultReasoningEffort")
    )
    if default_reasoning_effort is not None:
        normalized["defaultReasoningEffort"] = default_reasoning_effort

    context_window = _optional_positive_int(value.get("contextWindow"))
    if context_window is not None:
        normalized["contextWindow"] = context_window

    is_default = value.get("isDefault")
    if isinstance(is_default, bool):
        normalized["isDefault"] = is_default

    return normalized


def _split_provider_prefixed_model(identifier: str) -> tuple[str | None, str]:
    provider, _, model_id = identifier.partition("/")
    if not provider or not model_id:
        return None, identifier
    return provider, model_id


def _first_non_empty_string(*values: object) -> str | None:
    for value in values:
        resolved = _optional_non_empty_string(value)
        if resolved is not None:
            return resolved
    return None


def _optional_non_empty_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _optional_positive_int(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return None
    return value
