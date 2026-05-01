from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

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


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


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
