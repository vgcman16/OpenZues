from __future__ import annotations

import re
from collections.abc import Callable
from copy import deepcopy
from typing import Any

from openzues.database import utcnow

_SCHEMA_VERSION = "openzues-control-ui-bootstrap-v1"
_PATH_INDEX_RE = re.compile(r"\[(\*|\d*)\]")
_LOOKUP_PATH_PATTERN = re.compile(r"^[A-Za-z0-9_./\[\]\-*@$]+$")
_LOOKUP_PATH_MAX_LENGTH = 1024
_LOOKUP_PATH_MAX_SEGMENTS = 32
_FORBIDDEN_LOOKUP_SEGMENTS = frozenset({"__proto__", "constructor", "prototype"})
_LOOKUP_SCHEMA_STRING_KEYS = frozenset(
    {
        "$id",
        "$schema",
        "title",
        "description",
        "format",
        "pattern",
        "contentEncoding",
        "contentMediaType",
    }
)
_LOOKUP_SCHEMA_NUMBER_KEYS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "minProperties",
        "maxProperties",
    }
)
_LOOKUP_SCHEMA_BOOLEAN_KEYS = frozenset(
    {
        "additionalProperties",
        "uniqueItems",
        "deprecated",
        "readOnly",
        "writeOnly",
    }
)
_ROOT_REQUIRED = ("assistantName", "assistantAvatar", "assistantAgentId")
_ROOT_PROPERTIES: dict[str, dict[str, Any]] = {
    "basePath": {
        "type": "string",
        "title": "Base Path",
    },
    "assistantName": {
        "type": "string",
        "title": "Assistant Name",
    },
    "assistantAvatar": {
        "type": "string",
        "title": "Assistant Avatar",
    },
    "assistantAgentId": {
        "type": "string",
        "title": "Assistant Agent ID",
    },
    "serverVersion": {
        "type": ["string", "null"],
        "title": "Server Version",
    },
    "localMediaPreviewRoots": {
        "type": "array",
        "title": "Local Media Preview Roots",
        "items": {
            "type": "string",
            "title": "Local Media Preview Root",
        },
    },
    "embedSandbox": {
        "type": "string",
        "title": "Embed Sandbox",
        "enum": ["strict", "scripts", "trusted"],
        "default": "scripts",
    },
    "allowExternalEmbedUrls": {
        "type": "boolean",
        "title": "Allow External Embed URLs",
        "default": False,
    },
}
_UI_HINTS: dict[str, dict[str, Any]] = {
    "basePath": {"label": "Base Path"},
    "assistantName": {"label": "Assistant Name"},
    "assistantAvatar": {
        "label": "Assistant Avatar",
        "placeholder": "/static/zues.svg",
    },
    "assistantAgentId": {"label": "Assistant Agent ID"},
    "serverVersion": {"label": "Server Version"},
    "localMediaPreviewRoots": {"label": "Local Media Preview Roots"},
    "localMediaPreviewRoots[]": {"label": "Local Media Preview Root"},
    "embedSandbox": {"label": "Embed Sandbox"},
    "allowExternalEmbedUrls": {"label": "Allow External Embed URLs"},
}


class GatewayConfigSchemaService:
    def __init__(
        self,
        *,
        generated_at_loader: Callable[[], str] | None = None,
    ) -> None:
        self._generated_at_loader = generated_at_loader or utcnow

    def build_schema(self) -> dict[str, Any]:
        return {
            "schema": _root_schema(),
            "uiHints": deepcopy(_UI_HINTS),
            "version": _SCHEMA_VERSION,
            "generatedAt": _normalize_generated_at(self._generated_at_loader()),
        }

    def lookup(self, path: str) -> dict[str, Any] | None:
        normalized_path = _normalize_lookup_path(path)
        if normalized_path is None:
            return None
        if normalized_path and len(_split_lookup_path(normalized_path)) > _LOOKUP_PATH_MAX_SEGMENTS:
            return None
        node = _lookup_schema_node(normalized_path)
        if node is None:
            return None
        result: dict[str, Any] = {
            "path": normalized_path,
            "schema": _lookup_schema_view(node["schema"]),
            "children": _build_lookup_children(
                normalized_path,
                node["schema"],
            ),
        }
        hint_match = _resolve_hint_match(normalized_path)
        if hint_match is not None:
            result["hint"] = hint_match["hint"]
            result["hintPath"] = hint_match["path"]
        return result


def _root_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "title": "Control UI Bootstrap Config",
        "properties": deepcopy(_ROOT_PROPERTIES),
        "required": list(_ROOT_REQUIRED),
    }


def _normalize_generated_at(value: str) -> str:
    normalized = value.strip()
    return normalized.replace("+00:00", "Z")


def _normalize_lookup_path(path: str) -> str | None:
    normalized = path.strip()
    if not normalized:
        return None
    if len(normalized) > _LOOKUP_PATH_MAX_LENGTH:
        return None
    if not _LOOKUP_PATH_PATTERN.fullmatch(normalized):
        return None

    normalized = _PATH_INDEX_RE.sub(lambda match: f".{match.group(1) or '*'}", normalized)
    normalized = re.sub(r"\.+", ".", normalized.strip("."))
    if not normalized:
        return None
    return normalized


def _split_lookup_path(path: str) -> list[str]:
    if not path:
        return []
    return [segment for segment in path.split(".") if segment]


def _resolve_items_schema(
    schema: dict[str, Any],
    *,
    index: int | None = None,
) -> dict[str, Any] | None:
    items = schema.get("items")
    if isinstance(items, list):
        if index is None:
            for entry in items:
                if isinstance(entry, dict):
                    return entry
            return None
        if 0 <= index < len(items) and isinstance(items[index], dict):
            return items[index]
        return None
    return items if isinstance(items, dict) else None


def _resolve_lookup_child_schema(
    schema: dict[str, Any],
    segment: str,
) -> dict[str, Any] | None:
    if segment in _FORBIDDEN_LOOKUP_SEGMENTS:
        return None

    properties = schema.get("properties")
    if isinstance(properties, dict):
        property_schema = properties.get(segment)
        if isinstance(property_schema, dict):
            return property_schema

    item_index = int(segment) if segment.isdigit() else None
    items = _resolve_items_schema(schema, index=item_index)
    if (segment == "*" or item_index is not None) and items is not None:
        return items

    additional_properties = schema.get("additionalProperties")
    if isinstance(additional_properties, dict):
        return additional_properties
    return None


def _lookup_schema_node(path: str) -> dict[str, Any] | None:
    schema = _root_schema()
    if not path:
        return {"schema": schema}

    current_schema: dict[str, Any] = schema
    for segment in _split_lookup_path(path):
        next_schema = _resolve_lookup_child_schema(current_schema, segment)
        if next_schema is None:
            return None
        current_schema = next_schema

    return {"schema": current_schema}


def _lookup_schema_view(schema: dict[str, Any]) -> dict[str, Any]:
    view: dict[str, Any] = {}
    for key, value in schema.items():
        if key in _LOOKUP_SCHEMA_STRING_KEYS and isinstance(value, str):
            view[key] = value
            continue
        if key in _LOOKUP_SCHEMA_NUMBER_KEYS and _is_lookup_number(value):
            view[key] = value
            continue
        if key in _LOOKUP_SCHEMA_BOOLEAN_KEYS and isinstance(value, bool):
            view[key] = value
            continue
        if key == "type":
            if isinstance(value, str):
                view[key] = value
            elif isinstance(value, list) and all(isinstance(entry, str) for entry in value):
                view[key] = list(value)
            continue
        if key == "enum" and isinstance(value, list):
            if all(_is_lookup_scalar(entry) for entry in value):
                view[key] = deepcopy(value)
            continue
        if key == "const" and _is_lookup_scalar(value):
            view[key] = deepcopy(value)
    return view


def _is_lookup_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_lookup_scalar(value: Any) -> bool:
    return value is None or isinstance(value, str | bool) or _is_lookup_number(value)


def _build_lookup_children(path: str, schema: dict[str, Any]) -> list[dict[str, Any]]:
    required = set(schema.get("required") or [])
    children: list[dict[str, Any]] = []

    def _append_child(
        key: str,
        child_schema: dict[str, Any],
        *,
        required_child: bool,
    ) -> None:
        child_path = key if not path else f"{path}.{key}"
        child: dict[str, Any] = {
            "key": key,
            "path": child_path,
            "type": deepcopy(child_schema.get("type")),
            "required": required_child,
            "hasChildren": _schema_has_children(child_schema),
        }
        hint_match = _resolve_hint_match(child_path)
        if hint_match is not None:
            child["hint"] = hint_match["hint"]
            child["hintPath"] = hint_match["path"]
        children.append(child)

    properties = schema.get("properties")
    if isinstance(properties, dict):
        for key, child_schema in properties.items():
            if not isinstance(child_schema, dict):
                continue
            _append_child(key, child_schema, required_child=key in required)

    wildcard_schema = None
    additional_properties = schema.get("additionalProperties")
    if isinstance(additional_properties, dict):
        wildcard_schema = additional_properties
    else:
        wildcard_schema = _resolve_items_schema(schema)
    if wildcard_schema is not None:
        _append_child("*", wildcard_schema, required_child=False)
    return children


def _schema_has_children(schema: dict[str, Any]) -> bool:
    properties = schema.get("properties")
    if isinstance(properties, dict) and properties:
        return True
    additional_properties = schema.get("additionalProperties")
    if isinstance(additional_properties, dict):
        return True
    items = schema.get("items")
    if isinstance(items, dict):
        return True
    if isinstance(items, list) and any(isinstance(item, dict) for item in items):
        return True
    for branch_key in ("oneOf", "anyOf", "allOf"):
        branch = schema.get(branch_key)
        if not isinstance(branch, list):
            continue
        for entry in branch:
            if isinstance(entry, dict) and _schema_has_children(entry):
                return True
    return False


def _resolve_hint_match(path: str) -> dict[str, Any] | None:
    target_parts = _split_lookup_path(path)
    best_match: tuple[str, dict[str, Any], int] | None = None

    for hint_path, hint in _UI_HINTS.items():
        hint_parts = _split_lookup_path(_normalize_lookup_path(hint_path) or "")
        if len(hint_parts) != len(target_parts):
            continue

        wildcard_count = 0
        for hint_part, target_part in zip(hint_parts, target_parts, strict=False):
            if hint_part == target_part:
                continue
            if hint_part == "*":
                wildcard_count += 1
                continue
            break
        else:
            if best_match is None or wildcard_count < best_match[2]:
                best_match = (hint_path, hint, wildcard_count)

    if best_match is None:
        return None
    return {
        "path": best_match[0],
        "hint": deepcopy(best_match[1]),
    }
