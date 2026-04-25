from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class _ConfiguredModelMetadata:
    configured_by_key: dict[tuple[str | None, str], dict[str, Any]]
    alias_by_key: dict[tuple[str | None, str], str]
    alias_ref_by_alias_key: dict[str, str]
    known_models: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class _ConfiguredModelAllowlist:
    allow_any: bool
    allowed_keys: frozenset[tuple[str | None, str]]
    synthetic_entries: tuple[dict[str, Any], ...]


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
        allow_any_catalog = self._list_instance_views is None
        saw_instance = False

        if self._list_instance_views is not None:
            for instance in await self._list_instance_views():
                saw_instance = True
                configured_metadata = _build_configured_model_metadata(instance.config)
                instance_entries: list[dict[str, Any]] = []
                for raw_entry in instance.models:
                    normalized = _normalize_model_entry(
                        raw_entry,
                        configured_metadata=configured_metadata,
                    )
                    if normalized is None:
                        continue
                    instance_entries.append(normalized)
                configured_models = _normalize_configured_model_entries(
                    instance.config,
                    known_models=[
                        *instance.models,
                        *configured_metadata.known_models,
                        *entries,
                        *_DEFAULT_MODELS,
                    ],
                    configured_metadata=configured_metadata,
                )
                instance_entries.extend(configured_models)
                allowlist = _build_configured_model_allowlist(
                    instance.config,
                    known_models=[
                        *instance.models,
                        *configured_metadata.known_models,
                        *instance_entries,
                        *entries,
                        *_DEFAULT_MODELS,
                    ],
                    catalog_entries=[*instance_entries, *entries],
                    configured_metadata=configured_metadata,
                )
                if allowlist.allow_any:
                    allow_any_catalog = True
                else:
                    instance_entries = _filter_allowed_model_entries(
                        instance_entries,
                        allowlist=allowlist,
                    )
                for instance_entry in instance_entries:
                    _upsert_model(entries, indexes, instance_entry)
                    if instance_entry.get("isDefault") is True:
                        has_explicit_default = True

        if allow_any_catalog or not saw_instance:
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


def _normalize_model_entry(
    value: object,
    *,
    configured_metadata: _ConfiguredModelMetadata | None = None,
) -> dict[str, Any] | None:
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

    return _apply_configured_model_metadata(
        normalized,
        configured_metadata=configured_metadata,
    )


def _normalize_configured_model_entries(
    value: object,
    *,
    known_models: list[object],
    configured_metadata: _ConfiguredModelMetadata | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(value, Mapping):
        return []

    configured_entries: list[dict[str, Any]] = []
    model_config = value.get("model")

    configured_model = _resolve_configured_primary_model(
        model_config,
        configured_metadata=configured_metadata,
    )
    if configured_model is not None:
        configured_entries.append(
            _build_configured_model_entry(
                configured_model,
                config=value,
                known_models=known_models,
                is_default=True,
                configured_metadata=configured_metadata,
            )
        )

    for fallback_model in _resolve_configured_fallback_models(
        model_config,
        configured_metadata=configured_metadata,
    ):
        configured_entries.append(
            _build_configured_model_entry(
                fallback_model,
                config=value,
                known_models=known_models,
                is_default=False,
                configured_metadata=configured_metadata,
            )
        )

    return configured_entries


def _build_configured_model_entry(
    configured_model: str,
    *,
    config: Mapping[str, object],
    known_models: list[object],
    is_default: bool,
    configured_metadata: _ConfiguredModelMetadata | None = None,
) -> dict[str, Any]:
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
    }
    if provider is not None:
        normalized["provider"] = provider
    if is_default:
        normalized["isDefault"] = True

        default_reasoning_effort = _first_non_empty_string(
            config.get("model_reasoning_effort"),
            config.get("modelReasoningEffort"),
        )
        if default_reasoning_effort is not None:
            normalized["defaultReasoningEffort"] = default_reasoning_effort

    return _apply_configured_model_metadata(
        normalized,
        configured_metadata=configured_metadata,
    )


def _resolve_configured_primary_model(
    value: object,
    *,
    configured_metadata: _ConfiguredModelMetadata | None = None,
) -> str | None:
    configured_model = _optional_non_empty_string(value)
    if configured_model is not None:
        return _resolve_configured_model_alias(
            configured_model,
            configured_metadata=configured_metadata,
        )
    if not isinstance(value, Mapping):
        return None
    primary = _optional_non_empty_string(value.get("primary"))
    if primary is None:
        return None
    return _resolve_configured_model_alias(
        primary,
        configured_metadata=configured_metadata,
    )


def _resolve_configured_fallback_models(
    value: object,
    *,
    configured_metadata: _ConfiguredModelMetadata | None = None,
) -> list[str]:
    if not isinstance(value, Mapping):
        return []
    raw_fallbacks = value.get("fallbacks")
    if not isinstance(raw_fallbacks, list):
        return []

    fallbacks: list[str] = []
    seen: set[str] = set()
    for raw_fallback in raw_fallbacks:
        fallback = _optional_non_empty_string(raw_fallback)
        if fallback is None:
            continue
        fallback = _resolve_configured_model_alias(
            fallback,
            configured_metadata=configured_metadata,
        )
        fallback_key = fallback.casefold()
        if fallback_key in seen:
            continue
        seen.add(fallback_key)
        fallbacks.append(fallback)
    return fallbacks


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
    candidates: Sequence[object],
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
    known_models: Sequence[object],
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


def _build_configured_model_metadata(value: object) -> _ConfiguredModelMetadata:
    empty = _ConfiguredModelMetadata(
        configured_by_key={},
        alias_by_key={},
        alias_ref_by_alias_key={},
        known_models=[],
    )
    if not isinstance(value, Mapping):
        return empty

    configured_by_key: dict[tuple[str | None, str], dict[str, Any]] = {}
    alias_by_key: dict[tuple[str | None, str], str] = {}
    alias_ref_by_alias_key: dict[str, str] = {}
    known_models: list[dict[str, Any]] = []

    raw_models = value.get("models")
    if isinstance(raw_models, Mapping):
        raw_providers = raw_models.get("providers")
        if isinstance(raw_providers, Mapping):
            for raw_provider, raw_provider_config in raw_providers.items():
                provider = _normalize_provider_id(_optional_non_empty_string(raw_provider))
                if provider is None or not isinstance(raw_provider_config, Mapping):
                    continue
                raw_provider_models = raw_provider_config.get("models")
                if not isinstance(raw_provider_models, list):
                    continue
                for raw_model in raw_provider_models:
                    if not isinstance(raw_model, Mapping):
                        continue
                    model_id = _optional_non_empty_string(raw_model.get("id"))
                    if model_id is None:
                        continue
                    configured_model: dict[str, Any] = {
                        "id": model_id,
                        "name": _first_non_empty_string(
                            raw_model.get("name"),
                            raw_model.get("displayName"),
                            model_id,
                        )
                        or model_id,
                        "provider": provider,
                    }
                    context_window = _optional_positive_int(raw_model.get("contextWindow"))
                    if context_window is not None:
                        configured_model["contextWindow"] = context_window
                    reasoning = raw_model.get("reasoning")
                    if isinstance(reasoning, bool):
                        configured_model["reasoning"] = reasoning
                    input_types = _normalize_string_list(raw_model.get("input"))
                    if input_types is None:
                        input_types = _normalize_string_list(raw_model.get("inputs"))
                    if input_types is not None:
                        configured_model["input"] = input_types
                    key = _model_key(configured_model)
                    if key is None:
                        continue
                    configured_by_key[key] = configured_model
                    known_models.append(configured_model)

    raw_agents = value.get("agents")
    if isinstance(raw_agents, Mapping):
        raw_defaults = raw_agents.get("defaults")
        if isinstance(raw_defaults, Mapping):
            raw_default_models = raw_defaults.get("models")
            if isinstance(raw_default_models, Mapping):
                known_model_candidates = [*known_models, *_DEFAULT_MODELS]
                for raw_identifier, raw_entry in raw_default_models.items():
                    identifier = _optional_non_empty_string(raw_identifier)
                    if identifier is None:
                        continue
                    parsed_provider, parsed_model_id = _split_provider_prefixed_model(identifier)
                    provider = _normalize_provider_id(parsed_provider)
                    if provider is None:
                        provider = _infer_unique_provider_for_model(
                            parsed_model_id,
                            known_model_candidates,
                        )
                    alias_target = (
                        f"{provider}/{parsed_model_id}"
                        if provider is not None
                        else parsed_model_id
                    )
                    key = (provider, parsed_model_id.casefold())
                    if not isinstance(raw_entry, Mapping):
                        continue
                    alias = _optional_non_empty_string(raw_entry.get("alias"))
                    if alias is None:
                        continue
                    alias_by_key[key] = alias
                    alias_ref_by_alias_key.setdefault(alias.casefold(), alias_target)

    return _ConfiguredModelMetadata(
        configured_by_key=configured_by_key,
        alias_by_key=alias_by_key,
        alias_ref_by_alias_key=alias_ref_by_alias_key,
        known_models=known_models,
    )


def _configured_model_config_sources(value: object) -> list[object]:
    if not isinstance(value, Mapping):
        return []
    sources: list[object] = []
    direct_model = value.get("model")
    if direct_model is not None:
        sources.append(direct_model)
    raw_agents = value.get("agents")
    if not isinstance(raw_agents, Mapping):
        return sources
    raw_defaults = raw_agents.get("defaults")
    if not isinstance(raw_defaults, Mapping):
        return sources
    default_model = raw_defaults.get("model")
    if default_model is not None:
        sources.append(default_model)
    return sources


def _build_configured_model_allowlist(
    value: object,
    *,
    known_models: list[object],
    catalog_entries: list[dict[str, Any]],
    configured_metadata: _ConfiguredModelMetadata | None = None,
) -> _ConfiguredModelAllowlist:
    if not isinstance(value, Mapping):
        return _ConfiguredModelAllowlist(
            allow_any=True,
            allowed_keys=frozenset(),
            synthetic_entries=(),
        )

    raw_agents = value.get("agents")
    if not isinstance(raw_agents, Mapping):
        return _ConfiguredModelAllowlist(
            allow_any=True,
            allowed_keys=frozenset(),
            synthetic_entries=(),
        )
    raw_defaults = raw_agents.get("defaults")
    if not isinstance(raw_defaults, Mapping):
        return _ConfiguredModelAllowlist(
            allow_any=True,
            allowed_keys=frozenset(),
            synthetic_entries=(),
        )
    raw_allowlist = raw_defaults.get("models")
    if not isinstance(raw_allowlist, Mapping):
        return _ConfiguredModelAllowlist(
            allow_any=True,
            allowed_keys=frozenset(),
            synthetic_entries=(),
        )

    allowlist_refs = _extract_configured_allowlist_refs(
        value,
        configured_metadata=configured_metadata,
    )
    if not allowlist_refs:
        return _ConfiguredModelAllowlist(
            allow_any=True,
            allowed_keys=frozenset(),
            synthetic_entries=(),
        )

    allowed_keys: set[tuple[str | None, str]] = set()
    synthetic_entries: list[dict[str, Any]] = []

    for raw_ref in allowlist_refs:
        synthetic_entry = _build_configured_model_entry(
            raw_ref,
            config=value,
            known_models=known_models,
            is_default=False,
            configured_metadata=configured_metadata,
        )
        key = _model_key(synthetic_entry)
        if key is None:
            continue
        allowed_keys.add(key)
        if any(
            _model_keys_match(_model_key(entry), key) for entry in catalog_entries
        ) or any(
            _model_keys_match(_model_key(entry), key) for entry in synthetic_entries
        ):
            continue
        synthetic_entries.append(synthetic_entry)

    if not allowed_keys:
        return _ConfiguredModelAllowlist(
            allow_any=True,
            allowed_keys=frozenset(),
            synthetic_entries=(),
        )

    return _ConfiguredModelAllowlist(
        allow_any=False,
        allowed_keys=frozenset(allowed_keys),
        synthetic_entries=tuple(synthetic_entries),
    )


def _extract_configured_allowlist_refs(
    value: Mapping[str, object],
    *,
    configured_metadata: _ConfiguredModelMetadata | None = None,
) -> list[str]:
    raw_agents = value.get("agents")
    if not isinstance(raw_agents, Mapping):
        return []
    raw_defaults = raw_agents.get("defaults")
    if not isinstance(raw_defaults, Mapping):
        return []
    raw_allowlist = raw_defaults.get("models")
    if not isinstance(raw_allowlist, Mapping):
        return []

    refs: list[str] = []
    seen: set[str] = set()
    for raw_identifier in raw_allowlist:
        identifier = _optional_non_empty_string(raw_identifier)
        if identifier is None:
            continue
        normalized_key = identifier.casefold()
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        refs.append(identifier)

    for fallback in _resolve_configured_allowlist_fallback_models(
        value,
        configured_metadata=configured_metadata,
    ):
        fallback_key = fallback.casefold()
        if fallback_key in seen:
            continue
        seen.add(fallback_key)
        refs.append(fallback)
    return refs


def _resolve_configured_allowlist_fallback_models(
    value: object,
    *,
    configured_metadata: _ConfiguredModelMetadata | None = None,
) -> list[str]:
    fallbacks: list[str] = []
    seen: set[str] = set()
    for model_config in _configured_model_config_sources(value):
        for fallback in _resolve_configured_fallback_models(
            model_config,
            configured_metadata=configured_metadata,
        ):
            fallback_key = fallback.casefold()
            if fallback_key in seen:
                continue
            seen.add(fallback_key)
            fallbacks.append(fallback)
    return fallbacks


def _filter_allowed_model_entries(
    entries: list[dict[str, Any]],
    *,
    allowlist: _ConfiguredModelAllowlist,
) -> list[dict[str, Any]]:
    filtered = [
        entry
        for entry in entries
        if _is_allowed_model_entry(entry, allowlist=allowlist)
    ]
    for synthetic_entry in allowlist.synthetic_entries:
        synthetic_key = _model_key(synthetic_entry)
        if synthetic_key is None:
            continue
        if any(
            _model_keys_match(_model_key(existing_entry), synthetic_key)
            for existing_entry in filtered
        ):
            continue
        filtered.append(synthetic_entry)
    return filtered


def _is_allowed_model_entry(
    entry: dict[str, Any],
    *,
    allowlist: _ConfiguredModelAllowlist,
) -> bool:
    key = _model_key(entry)
    if key is None:
        return False
    return any(_model_keys_match(key, allowed_key) for allowed_key in allowlist.allowed_keys)


def _model_keys_match(
    first: tuple[str | None, str] | None,
    second: tuple[str | None, str] | None,
) -> bool:
    if first is None or second is None:
        return False
    if first == second:
        return True
    return first[1] == second[1] and (first[0] is None or second[0] is None)


def _resolve_configured_model_alias(
    value: str,
    *,
    configured_metadata: _ConfiguredModelMetadata | None = None,
) -> str:
    configured_model = value.strip()
    if not configured_model or configured_metadata is None:
        return configured_model
    return configured_metadata.alias_ref_by_alias_key.get(
        configured_model.casefold(),
        configured_model,
    )


def _apply_configured_model_metadata(
    entry: dict[str, Any],
    *,
    configured_metadata: _ConfiguredModelMetadata | None = None,
) -> dict[str, Any]:
    if configured_metadata is None:
        return entry
    key = _model_key(entry)
    if key is None:
        return entry

    configured_entry = configured_metadata.configured_by_key.get(key)
    alias = configured_metadata.alias_by_key.get(key)
    if configured_entry is None and alias is None:
        return entry

    merged = dict(entry)
    if configured_entry is not None:
        provider = _optional_non_empty_string(configured_entry.get("provider"))
        if provider is not None and "provider" not in merged:
            merged["provider"] = provider
        name = _optional_non_empty_string(configured_entry.get("name"))
        if name is not None:
            merged["name"] = name
        for field in ("contextWindow", "reasoning", "input"):
            if field in configured_entry:
                merged[field] = configured_entry[field]
    if alias is not None:
        merged["alias"] = alias
    return merged


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
