from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from openzues.schemas import InstanceView

_DEFAULT_PROVIDER = "openai"
_PROVIDER_ALIASES: dict[str, str] = {
    "modelstudio": "qwen",
    "qwencloud": "qwen",
    "z.ai": "zai",
    "z-ai": "zai",
    "opencode-zen": "opencode",
    "opencode-go-auth": "opencode-go",
    "kimi": "kimi",
    "kimi-code": "kimi",
    "kimi-coding": "kimi",
    "bedrock": "amazon-bedrock",
    "aws-bedrock": "amazon-bedrock",
    "bytedance": "volcengine",
    "doubao": "volcengine",
}

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
_FALLBACK_MODELS: tuple[dict[str, Any], ...] = tuple(
    {
        key: value
        for key, value in entry.items()
        if key != "isDefault"
    }
    for entry in _DEFAULT_MODELS
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
        indexes: dict[tuple[str | None, str], int] = {}
        has_explicit_default = False

        if self._list_instance_views is not None:
            for instance in await self._list_instance_views():
                for raw_entry in instance.models:
                    normalized = _normalize_model_entry(raw_entry)
                    if normalized is None:
                        continue
                    _upsert_model(entries, indexes, normalized)
                    if normalized.get("isDefault") is True:
                        has_explicit_default = True
                configured_model = _normalize_configured_model_entry(
                    instance.config,
                    known_models=[*instance.models, *entries, *_DEFAULT_MODELS],
                )
                if configured_model is not None:
                    _upsert_model(entries, indexes, configured_model)
                    has_explicit_default = True

        for raw_entry in (_FALLBACK_MODELS if has_explicit_default else _DEFAULT_MODELS):
            _upsert_model(entries, indexes, dict(raw_entry))

        entries.sort(key=_model_sort_key)
        return {"models": entries}


def _upsert_model(
    entries: list[dict[str, Any]],
    indexes: dict[tuple[str | None, str], int],
    entry: dict[str, Any],
) -> None:
    key = _model_key(entry)
    if key is None:
        return
    index = indexes.get(key)
    if index is None and key[0] is not None:
        providerless_key = (None, key[1])
        if providerless_key in indexes:
            index = indexes.pop(providerless_key)
            indexes[key] = index
    if index is None:
        indexes[key] = len(entries)
        entries.append(entry)
        return
    entries[index] = _merge_model_entries(entries[index], entry)


def _normalize_model_entry(value: object) -> dict[str, Any] | None:
    identity = _extract_model_identity(value)
    if identity is None:
        return None

    normalized_provider, model_id = identity
    assert isinstance(value, Mapping)
    name = _first_non_empty_string(
        value.get("displayName"),
        value.get("name"),
        model_id,
    )
    if name is None:
        return None

    normalized: dict[str, Any] = {"id": model_id, "name": name}
    if normalized_provider is not None:
        normalized["provider"] = normalized_provider

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

    reasoning = value.get("reasoning")
    if isinstance(reasoning, bool):
        normalized["reasoning"] = reasoning

    input_types = _normalize_string_list(value.get("input"))
    if input_types is None:
        input_types = _normalize_string_list(value.get("inputs"))
    if input_types is not None:
        normalized["input"] = input_types

    is_default = value.get("isDefault")
    if isinstance(is_default, bool):
        normalized["isDefault"] = is_default

    return normalized


def _normalize_configured_model_entry(
    value: object,
    *,
    known_models: list[object],
) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None

    configured_model = _optional_non_empty_string(value.get("model"))
    if configured_model is None:
        return None

    parsed_provider, parsed_model_id = _split_provider_prefixed_model(configured_model)
    model_id = parsed_model_id or configured_model
    provider = _normalize_provider_id(parsed_provider)
    if provider is None:
        provider = _infer_unique_provider_for_model(
            model_id,
            known_models,
        )
    name = _resolve_known_model_name(
        provider=provider,
        model_id=model_id,
        known_models=known_models,
    ) or model_id

    normalized: dict[str, Any] = {
        "id": model_id,
        "name": name,
        "isDefault": True,
    }
    if provider is not None:
        normalized["provider"] = provider

    default_reasoning_effort = _first_non_empty_string(
        value.get("model_reasoning_effort"),
        value.get("modelReasoningEffort"),
    )
    if default_reasoning_effort is not None:
        normalized["defaultReasoningEffort"] = default_reasoning_effort

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


def _extract_model_identity(value: object) -> tuple[str | None, str] | None:
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
    provider = _first_non_empty_string(
        value.get("provider"),
        value.get("providerId"),
        parsed_provider,
    )
    normalized_provider = _normalize_provider_id(provider)
    model_id = parsed_model_id or raw_identifier
    return normalized_provider, model_id


def _normalize_provider_id(value: str | None) -> str | None:
    provider = _optional_non_empty_string(value)
    if provider is None:
        return None
    return _PROVIDER_ALIASES.get(provider.casefold(), provider.casefold())


def _normalize_string_list(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    seen: set[str] = set()
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        lowered = cleaned.casefold()
        if not cleaned or lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(cleaned)
    return normalized or None


def _infer_unique_provider_for_model(
    model_id: str,
    candidates: list[object],
) -> str | None:
    normalized_model_id = model_id.casefold()
    providers: set[str] = set()
    for candidate in candidates:
        identity = _extract_model_identity(candidate)
        if identity is None:
            continue
        provider, candidate_model_id = identity
        if provider is None or candidate_model_id.casefold() != normalized_model_id:
            continue
        providers.add(provider)
        if len(providers) > 1:
            return None
    if len(providers) == 1:
        return next(iter(providers))
    if normalized_model_id in {entry["id"].casefold() for entry in _DEFAULT_MODELS}:
        return _DEFAULT_PROVIDER
    return None


def _resolve_known_model_name(
    *,
    provider: str | None,
    model_id: str,
    known_models: list[object],
) -> str | None:
    normalized_model_id = model_id.casefold()
    fallback_name: str | None = None
    for candidate in known_models:
        identity = _extract_model_identity(candidate)
        if identity is None:
            continue
        candidate_provider, candidate_model_id = identity
        if candidate_model_id.casefold() != normalized_model_id:
            continue
        assert isinstance(candidate, Mapping)
        candidate_name = _first_non_empty_string(
            candidate.get("displayName"),
            candidate.get("name"),
            candidate_model_id,
        )
        if candidate_name is None:
            continue
        if provider is not None and candidate_provider == provider:
            return candidate_name
        fallback_name = fallback_name or candidate_name
    return fallback_name


def _model_key(entry: dict[str, Any]) -> tuple[str | None, str] | None:
    model_id = _optional_non_empty_string(entry.get("id"))
    if model_id is None:
        return None
    provider = _normalize_provider_id(_optional_non_empty_string(entry.get("provider")))
    return (provider, model_id.casefold())


def _merge_model_entries(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)

    provider = _normalize_provider_id(_optional_non_empty_string(merged.get("provider")))
    incoming_provider = _normalize_provider_id(
        _optional_non_empty_string(incoming.get("provider"))
    )
    if provider is not None:
        merged["provider"] = provider
    if provider is None and incoming_provider is not None:
        merged["provider"] = incoming_provider

    preferred_name = _preferred_model_name(existing, incoming)
    if preferred_name is not None:
        merged["name"] = preferred_name

    for field in ("alias", "description", "defaultReasoningEffort", "contextWindow", "reasoning"):
        if field not in merged and field in incoming:
            merged[field] = incoming[field]

    merged_input = _merge_string_lists(merged.get("input"), incoming.get("input"))
    if merged_input is not None:
        merged["input"] = merged_input

    if incoming.get("isDefault") is True:
        merged["isDefault"] = True

    return merged


def _preferred_model_name(existing: dict[str, Any], incoming: dict[str, Any]) -> str | None:
    existing_name = _optional_non_empty_string(existing.get("name"))
    incoming_name = _optional_non_empty_string(incoming.get("name"))
    if incoming_name is None:
        return existing_name
    if existing_name is None:
        return incoming_name
    existing_id = _optional_non_empty_string(existing.get("id"))
    if (
        existing_id is not None
        and existing_name.casefold() == existing_id.casefold()
        and incoming_name.casefold() != existing_name.casefold()
    ):
        return incoming_name
    return existing_name


def _merge_string_lists(existing: object, incoming: object) -> list[str] | None:
    values: list[str] = []
    seen: set[str] = set()
    for source in (existing, incoming):
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            lowered = cleaned.casefold()
            if not cleaned or lowered in seen:
                continue
            seen.add(lowered)
            values.append(cleaned)
    return values or None


def _model_sort_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    provider = _normalize_provider_id(_optional_non_empty_string(entry.get("provider"))) or ""
    model_id = _optional_non_empty_string(entry.get("id")) or ""
    name = _optional_non_empty_string(entry.get("name")) or ""
    return (provider, model_id.casefold(), name.casefold())
