from __future__ import annotations

import re
from urllib.parse import quote

CanvasPreview = dict[str, object]

_EMBED_BLOCK_RE = re.compile(r"\[embed\s+([^\]]*?)\]([\s\S]*?)\[/embed\]", re.IGNORECASE)
_EMBED_SELF_CLOSING_RE = re.compile(r"\[embed\s+([^\]]*?)/\]", re.IGNORECASE)
_EMBED_ATTR_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")
_FENCE_RE = re.compile(r"```[\s\S]*?```")


def extract_canvas_shortcodes(text: str | None) -> dict[str, object]:
    source = text or ""
    if "[embed" not in source.lower():
        return {"text": source, "previews": []}

    fence_spans = [(match.start(), match.end()) for match in _FENCE_RE.finditer(source)]
    matches: list[tuple[int, int, dict[str, str]]] = []
    for regex in (_EMBED_BLOCK_RE, _EMBED_SELF_CLOSING_RE):
        for match in regex.finditer(source):
            start = match.start()
            if any(span_start <= start < span_end for span_start, span_end in fence_spans):
                continue
            matches.append((start, match.end(), _parse_canvas_attributes(match.group(1) or "")))

    if not matches:
        return {"text": source, "previews": []}

    matches.sort(key=lambda item: item[0])
    stripped = ""
    previews: list[CanvasPreview] = []
    cursor = 0
    for start, end, attrs in matches:
        if start < cursor:
            continue
        stripped += source[cursor:start]
        preview = _preview_from_shortcode(attrs)
        if preview is None:
            stripped += source[start:end]
        else:
            previews.append(preview)
        cursor = end
    stripped += source[cursor:]
    return {"text": stripped, "previews": previews}


def _parse_canvas_attributes(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in _EMBED_ATTR_RE.finditer(raw):
        key = (match.group(1) or "").strip().lower()
        value = (match.group(2) if match.group(2) is not None else match.group(3) or "").strip()
        if key and value:
            attrs[key] = value
    return attrs


def _preview_from_shortcode(attrs: dict[str, str]) -> CanvasPreview | None:
    target = attrs.get("target")
    if target and target != "assistant_message":
        return None

    ref = attrs.get("ref")
    url = attrs.get("url")
    if not ref and not url:
        return None

    preview: CanvasPreview = {
        "kind": "canvas",
        "surface": "assistant_message",
        "render": "url",
        "url": url or _default_canvas_entry_url(ref or ""),
    }
    if ref:
        preview["viewId"] = ref
    title = attrs.get("title")
    if title:
        preview["title"] = title
    preferred_height = _normalize_preferred_height(attrs.get("height"))
    if preferred_height is not None:
        preview["preferredHeight"] = preferred_height
    class_name = attrs.get("class") or attrs.get("class_name")
    if class_name:
        preview["className"] = class_name
    style = attrs.get("style")
    if style:
        preview["style"] = style
    return preview


def _default_canvas_entry_url(ref: str) -> str:
    return f"/__openclaw__/canvas/documents/{quote(ref.strip(), safe='')}/index.html"


def _normalize_preferred_height(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if not parsed or parsed < 160:
        return None
    return min(int(parsed), 1200)
