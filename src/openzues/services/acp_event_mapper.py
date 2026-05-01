from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from urllib.parse import unquote, urlparse

INLINE_CONTROL_ESCAPE_MAP = {
    "\0": "\\0",
    "\r": "\\r",
    "\n": "\\n",
    "\t": "\\t",
    "\v": "\\v",
    "\f": "\\f",
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
}
TOOL_LOCATION_PATH_KEYS = (
    "path",
    "filePath",
    "file_path",
    "targetPath",
    "target_path",
    "targetFile",
    "target_file",
    "sourcePath",
    "source_path",
    "destinationPath",
    "destination_path",
    "oldPath",
    "old_path",
    "newPath",
    "new_path",
    "outputPath",
    "output_path",
    "inputPath",
    "input_path",
)
TOOL_LOCATION_LINE_KEYS = ("line", "lineNumber", "line_number", "startLine", "start_line")
TOOL_RESULT_PATH_MARKER_RE = re.compile(r"^(?:FILE|MEDIA):(.+)$", flags=re.MULTILINE)
TOOL_LOCATION_MAX_DEPTH = 4
TOOL_LOCATION_MAX_NODES = 100


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _has_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _read_string_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def escape_inline_control_chars(value: str) -> str:
    escaped = ""
    for char in value:
        codepoint = ord(char)
        is_inline_control = (
            codepoint <= 0x1F
            or 0x7F <= codepoint <= 0x9F
            or codepoint in {0x2028, 0x2029}
        )
        if not is_inline_control:
            escaped += char
            continue
        mapped = INLINE_CONTROL_ESCAPE_MAP.get(char)
        if mapped is not None:
            escaped += mapped
        elif codepoint <= 0xFF:
            escaped += f"\\x{codepoint:02x}"
        else:
            escaped += f"\\u{codepoint:04x}"
    return escaped


def escape_resource_title(value: str) -> str:
    escaped = escape_inline_control_chars(value)
    return "".join(f"\\{char}" if char in "()[]" else char for char in escaped)


def extract_text_from_prompt(
    prompt: Sequence[Mapping[str, object]],
    max_bytes: int | None = None,
) -> str:
    parts: list[str] = []
    total_bytes = 0
    for block in prompt:
        block_text: str | None = None
        block_type = block.get("type")
        if block_type == "text":
            text = block.get("text")
            block_text = text if isinstance(text, str) else None
        elif block_type == "resource":
            resource = _as_mapping(block.get("resource"))
            text = resource.get("text") if resource is not None else None
            block_text = text if isinstance(text, str) and text else None
        elif block_type == "resource_link":
            title = block.get("title")
            title_suffix = f" ({escape_resource_title(title)})" if isinstance(title, str) else ""
            uri = block.get("uri")
            safe_uri = escape_inline_control_chars(uri) if isinstance(uri, str) else ""
            block_text = (
                f"[Resource link{title_suffix}] {safe_uri}"
                if safe_uri
                else f"[Resource link{title_suffix}]"
            )
        if block_text is None:
            continue
        if max_bytes is not None:
            separator_bytes = 1 if parts else 0
            total_bytes += separator_bytes + len(block_text.encode("utf-8"))
            if total_bytes > max_bytes:
                raise ValueError(f"Prompt exceeds maximum allowed size of {max_bytes} bytes")
        parts.append(block_text)
    return "\n".join(parts)


def extract_attachments_from_prompt(
    prompt: Sequence[Mapping[str, object]],
) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    for block in prompt:
        if block.get("type") != "image":
            continue
        data = block.get("data")
        mime_type = block.get("mimeType")
        if not isinstance(data, str) or not data:
            continue
        if not isinstance(mime_type, str) or not mime_type:
            continue
        attachments.append({"type": "image", "mimeType": mime_type, "content": data})
    return attachments


def _format_tool_arg_value(value: object) -> str:
    if isinstance(value, str):
        raw = value
    else:
        raw = json.dumps(value, separators=(",", ":"))
    return f"{raw[:100]}..." if len(raw) > 100 else raw


def format_tool_title(name: str | None, args: Mapping[str, object] | None) -> str:
    base = name or "tool"
    if not args:
        return base
    parts = [
        f"{key}: {_format_tool_arg_value(value)}"
        for key, value in args.items()
    ]
    return escape_inline_control_chars(f"{base}: {', '.join(parts)}")


def infer_tool_kind(name: str | None) -> str:
    if not name:
        return "other"
    normalized = name.strip().lower()
    if "read" in normalized:
        return "read"
    if "write" in normalized or "edit" in normalized:
        return "edit"
    if "delete" in normalized or "remove" in normalized:
        return "delete"
    if "move" in normalized or "rename" in normalized:
        return "move"
    if "search" in normalized or "find" in normalized:
        return "search"
    if "exec" in normalized or "run" in normalized or "bash" in normalized:
        return "execute"
    if "fetch" in normalized or "http" in normalized:
        return "fetch"
    return "other"


def extract_tool_call_content(value: object) -> list[dict[str, object]] | None:
    if _has_non_empty_string(value):
        return [
            {
                "type": "content",
                "content": {"type": "text", "text": value},
            }
        ]
    record = _as_mapping(value)
    if record is None:
        return None
    contents: list[dict[str, object]] = []
    blocks = record.get("content")
    if isinstance(blocks, list):
        for block in blocks:
            entry = _as_mapping(block)
            text = entry.get("text") if entry is not None else None
            if entry is not None and entry.get("type") == "text" and _has_non_empty_string(text):
                contents.append(
                    {
                        "type": "content",
                        "content": {"type": "text", "text": text},
                    }
                )
    if contents:
        return contents
    fallback_text = (
        _read_string_value(record.get("text"))
        or _read_string_value(record.get("message"))
        or _read_string_value(record.get("error"))
    )
    if not _has_non_empty_string(fallback_text):
        return None
    return [
        {
            "type": "content",
            "content": {"type": "text", "text": fallback_text},
        }
    ]


def _normalize_tool_location_path(value: str) -> str | None:
    trimmed = value.strip()
    if (
        not trimmed
        or len(trimmed) > 4096
        or "\0" in trimmed
        or "\r" in trimmed
        or "\n" in trimmed
    ):
        return None
    if re.match(r"^https?://", trimmed, flags=re.IGNORECASE):
        return None
    if re.match(r"^file://", trimmed, flags=re.IGNORECASE):
        try:
            parsed = urlparse(trimmed)
            path = unquote(parsed.path or "")
            return path or None
        except ValueError:
            return None
    return trimmed


def _normalize_tool_location_line(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    if not math.isfinite(value):
        return None
    line = math.floor(value)
    return line if line > 0 else None


def _extract_tool_location_line(record: Mapping[str, object]) -> int | None:
    for key in TOOL_LOCATION_LINE_KEYS:
        line = _normalize_tool_location_line(record.get(key))
        if line is not None:
            return line
    return None


def _add_tool_location(
    locations: dict[str, dict[str, object]],
    raw_path: str,
    line: int | None = None,
) -> None:
    path = _normalize_tool_location_path(raw_path)
    if path is None:
        return
    for existing_key, existing in list(locations.items()):
        if existing.get("path") != path:
            continue
        existing_line = existing.get("line")
        if line is None or existing_line == line:
            return
        if existing_line is None:
            del locations[existing_key]
    location_key = f"{path}:{line or ''}"
    if location_key in locations:
        return
    location: dict[str, object] = {"path": path}
    if line is not None:
        location["line"] = line
    locations[location_key] = location


def _collect_locations_from_text_markers(
    text: str,
    locations: dict[str, dict[str, object]],
) -> None:
    for match in TOOL_RESULT_PATH_MARKER_RE.finditer(text):
        candidate = match.group(1).strip()
        if candidate:
            _add_tool_location(locations, candidate)


def _collect_tool_locations(
    value: object,
    locations: dict[str, dict[str, object]],
    state: dict[str, int],
    depth: int,
) -> None:
    if state["visited"] >= TOOL_LOCATION_MAX_NODES or depth > TOOL_LOCATION_MAX_DEPTH:
        return
    state["visited"] += 1
    if isinstance(value, str):
        _collect_locations_from_text_markers(value, locations)
        return
    if value is None or isinstance(value, int | float | bool):
        return
    if isinstance(value, list):
        for item in value:
            _collect_tool_locations(item, locations, state, depth + 1)
            if state["visited"] >= TOOL_LOCATION_MAX_NODES:
                return
        return
    record = _as_mapping(value)
    if record is None:
        return
    line = _extract_tool_location_line(record)
    for key in TOOL_LOCATION_PATH_KEYS:
        raw_path = record.get(key)
        if isinstance(raw_path, str):
            _add_tool_location(locations, raw_path, line)
    content = record.get("content")
    if isinstance(content, list):
        for block in content:
            entry = _as_mapping(block)
            text = entry.get("text") if entry is not None else None
            if entry is not None and entry.get("type") == "text" and isinstance(text, str):
                _collect_locations_from_text_markers(text, locations)
    for key, nested in record.items():
        if key == "content":
            continue
        _collect_tool_locations(nested, locations, state, depth + 1)
        if state["visited"] >= TOOL_LOCATION_MAX_NODES:
            return


def extract_tool_call_locations(*values: object) -> list[dict[str, object]] | None:
    locations: dict[str, dict[str, object]] = {}
    for value in values:
        _collect_tool_locations(value, locations, {"visited": 0}, 0)
    return list(locations.values()) if locations else None
