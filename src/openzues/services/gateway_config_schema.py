from __future__ import annotations

import re
from collections.abc import Callable
from copy import deepcopy
from typing import Any

from openzues.database import utcnow

_SCHEMA_VERSION = "openzues-control-ui-bootstrap-v1"
_PATH_INDEX_RE = re.compile(r"\[(\d+)\]")
_LOOKUP_PATH_PATTERN = re.compile(r"^[A-Za-z0-9_./\[\]\-*]+$")
_LOOKUP_PATH_MAX_LENGTH = 1024
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
        hint = _hint_for_path(node["hint_path"])
        if hint is not None:
            result["hint"] = hint
            result["hintPath"] = node["hint_path"]
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
    if path == "":
        return ""

    normalized = path.strip()
    if not normalized:
        return None
    if len(normalized) > _LOOKUP_PATH_MAX_LENGTH:
        return None
    if not _LOOKUP_PATH_PATTERN.fullmatch(normalized):
        return None

    normalized = _PATH_INDEX_RE.sub(r".\1", normalized)
    normalized = normalized.strip(".")
    return normalized


def _lookup_schema_node(path: str) -> dict[str, Any] | None:
    schema = _root_schema()
    hint_path = ""
    if not path:
        return {"schema": schema, "hint_path": hint_path}

    current_schema: dict[str, Any] = schema
    current_hint_path = ""
    for segment in path.split("."):
        properties = current_schema.get("properties")
        if isinstance(properties, dict):
            property_schema = properties.get(segment)
            if not isinstance(property_schema, dict):
                return None
            current_schema = property_schema
            current_hint_path = (
                segment
                if not current_hint_path
                else f"{current_hint_path}.{segment}"
            )
            continue

        if current_schema.get("type") == "array" and segment.isdigit():
            items = current_schema.get("items")
            if not isinstance(items, dict):
                return None
            current_schema = items
            current_hint_path = (
                f"{current_hint_path}[]" if current_hint_path else "[]"
            )
            continue
        return None

    return {"schema": current_schema, "hint_path": current_hint_path}


def _lookup_schema_view(schema: dict[str, Any]) -> dict[str, Any]:
    view: dict[str, Any] = {}
    for key in ("type", "title", "description", "enum", "default"):
        value = schema.get(key)
        if value is None:
            continue
        view[key] = deepcopy(value)
    return view


def _build_lookup_children(path: str, schema: dict[str, Any]) -> list[dict[str, Any]]:
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return []

    required = set(schema.get("required") or [])
    children: list[dict[str, Any]] = []
    for key, child_schema in properties.items():
        if not isinstance(child_schema, dict):
            continue
        child_path = key if not path else f"{path}.{key}"
        child_hint_path = key if not path else f"{path}.{key}"
        child: dict[str, Any] = {
            "key": key,
            "path": child_path,
            "type": deepcopy(child_schema.get("type")),
            "required": key in required,
            "hasChildren": _schema_has_children(child_schema),
        }
        hint = _hint_for_path(child_hint_path)
        if hint is not None:
            child["hint"] = hint
            child["hintPath"] = child_hint_path
        children.append(child)
    return children


def _schema_has_children(schema: dict[str, Any]) -> bool:
    properties = schema.get("properties")
    if isinstance(properties, dict) and properties:
        return True
    items = schema.get("items")
    return isinstance(items, dict) and bool(items.get("properties"))


def _hint_for_path(path: str) -> dict[str, Any] | None:
    hint = _UI_HINTS.get(path)
    return deepcopy(hint) if hint is not None else None
