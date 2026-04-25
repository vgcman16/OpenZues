from __future__ import annotations

import json
import re
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, unquote
from uuid import uuid4

CANVAS_HOST_PATH = "/__openclaw__/canvas"
CANVAS_DOCUMENTS_DIR_NAME = "documents"

_CANVAS_DOCUMENT_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

_DEFAULT_CANVAS_HOST_INDEX = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OpenClaw Canvas</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; }
    body { margin: 0; min-height: 100vh; background: #000; color: #fff; }
    main { display: grid; place-items: center; min-height: 100vh; padding: 24px; }
    section {
      width: min(720px, 100%);
      padding: 18px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.06);
    }
    button { margin-right: 8px; padding: 9px 12px; border-radius: 10px; }
  </style>
</head>
<body>
  <main>
    <section>
      <h1>OpenClaw Canvas</h1>
      <p>Interactive test page (auto-reload enabled)</p>
      <button id="btn-hello" type="button">Hello</button>
      <button id="btn-time" type="button">Time</button>
    </section>
  </main>
  <script>
    function openclawPostMessage(payload) {
      const raw = typeof payload === "string" ? payload : JSON.stringify(payload);
      globalThis.webkit?.messageHandlers?.openclawCanvasA2UIAction?.postMessage?.(raw);
      globalThis.openclawCanvasA2UIAction?.postMessage?.(raw);
    }
    function openclawSendUserAction(action) {
      const id = action?.id || globalThis.crypto?.randomUUID?.() || String(Date.now());
      openclawPostMessage({ userAction: { ...action, id } });
    }
    globalThis.openclawPostMessage = openclawPostMessage;
    globalThis.openclawSendUserAction = openclawSendUserAction;
    document.getElementById("btn-hello")?.addEventListener("click", () => {
      openclawSendUserAction({ type: "demo.hello" });
    });
    document.getElementById("btn-time")?.addEventListener("click", () => {
      openclawSendUserAction({ type: "demo.time" });
    });
  </script>
</body>
</html>
"""


def resolve_canvas_root_dir(
    *,
    root_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
) -> Path:
    if root_dir is not None and str(root_dir).strip():
        return Path(root_dir).expanduser().resolve()
    base_state_dir = Path.cwd() if state_dir is None else Path(state_dir).expanduser()
    return (base_state_dir / "canvas").resolve()


def resolve_canvas_documents_dir(
    *,
    root_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
) -> Path:
    return resolve_canvas_root_dir(root_dir=root_dir, state_dir=state_dir) / (
        CANVAS_DOCUMENTS_DIR_NAME
    )


def ensure_canvas_host_default_index(
    *,
    root_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
) -> Path:
    canvas_root = resolve_canvas_root_dir(root_dir=root_dir, state_dir=state_dir)
    canvas_root.mkdir(parents=True, exist_ok=True)
    index_path = canvas_root / "index.html"
    if not index_path.exists():
        index_path.write_text(_DEFAULT_CANVAS_HOST_INDEX, encoding="utf-8")
    return index_path


def resolve_canvas_document_dir(
    document_id: str,
    *,
    root_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
) -> Path:
    normalized_id = _normalize_canvas_document_id(document_id)
    return resolve_canvas_documents_dir(root_dir=root_dir, state_dir=state_dir) / normalized_id


def build_canvas_document_entry_url(document_id: str, entrypoint: str) -> str:
    normalized_entrypoint = _normalize_logical_path(entrypoint)
    encoded_entrypoint = "/".join(
        quote(segment, safe="") for segment in normalized_entrypoint.split("/")
    )
    return (
        f"{CANVAS_HOST_PATH}/{CANVAS_DOCUMENTS_DIR_NAME}/"
        f"{quote(document_id, safe='')}/{encoded_entrypoint}"
    )


def build_canvas_document_asset_url(document_id: str, logical_path: str) -> str:
    return build_canvas_document_entry_url(document_id, logical_path)


def create_canvas_document(
    document: Mapping[str, object],
    *,
    state_dir: str | Path | None = None,
    workspace_dir: str | Path | None = None,
    canvas_root_dir: str | Path | None = None,
) -> dict[str, object]:
    document_id = (
        _normalize_canvas_document_id(str(document["id"]))
        if str(document.get("id") or "").strip()
        else _generate_canvas_document_id()
    )
    kind = _required_string(document.get("kind"), label="kind")
    entrypoint = _required_mapping(document.get("entrypoint"), label="entrypoint")
    entrypoint_type = _required_string(entrypoint.get("type"), label="entrypoint.type")
    entrypoint_value = _required_string(entrypoint.get("value"), label="entrypoint.value")
    root_dir = resolve_canvas_document_dir(
        document_id,
        root_dir=canvas_root_dir,
        state_dir=state_dir,
    )
    if root_dir.exists():
        shutil.rmtree(root_dir)
    root_dir.mkdir(parents=True, exist_ok=True)

    assets = _copy_assets(root_dir, document.get("assets"), workspace_dir=workspace_dir)
    entry = _materialize_entrypoint(
        root_dir,
        kind=kind,
        entrypoint_type=entrypoint_type,
        entrypoint_value=entrypoint_value,
        workspace_dir=workspace_dir,
    )
    manifest: dict[str, object] = {
        "id": document_id,
        "kind": kind,
        "createdAt": _utc_now_iso(),
        "entryUrl": entry.get("entryUrl")
        or build_canvas_document_entry_url(document_id, entry["localEntrypoint"]),
        "assets": assets,
    }
    if entry.get("localEntrypoint"):
        manifest["localEntrypoint"] = entry["localEntrypoint"]
    if entry.get("externalUrl"):
        manifest["externalUrl"] = entry["externalUrl"]
    title = str(document.get("title") or "").strip()
    if title:
        manifest["title"] = title
    preferred_height = document.get("preferredHeight")
    if isinstance(preferred_height, int | float):
        manifest["preferredHeight"] = preferred_height
    surface = str(document.get("surface") or "").strip()
    if surface:
        manifest["surface"] = surface

    _write_json_manifest(root_dir / "manifest.json", manifest)
    return manifest


def resolve_canvas_http_path_to_local_path(
    request_path: str,
    *,
    root_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
) -> Path | None:
    trimmed = str(request_path).strip()
    prefix = f"{CANVAS_HOST_PATH}/{CANVAS_DOCUMENTS_DIR_NAME}/"
    if not trimmed.startswith(prefix):
        return None

    path_without_query = re.sub(r"[?#].*$", "", trimmed)
    relative_path = path_without_query[len(prefix) :]
    segments = [_decode_url_segment(segment) for segment in relative_path.split("/") if segment]
    if len(segments) < 2:
        return None

    raw_document_id, *entry_segments = segments
    try:
        document_id = _normalize_canvas_document_id(raw_document_id)
        normalized_entrypoint = _normalize_logical_path("/".join(entry_segments))
    except ValueError:
        return None

    documents_dir = resolve_canvas_documents_dir(
        root_dir=root_dir,
        state_dir=state_dir,
    ).resolve()
    candidate_path = (
        resolve_canvas_document_dir(
            document_id,
            root_dir=root_dir,
            state_dir=state_dir,
        )
        / normalized_entrypoint
    ).resolve()

    try:
        candidate_path.relative_to(documents_dir)
    except ValueError:
        return None
    return candidate_path


def resolve_canvas_host_http_path_to_local_path(
    request_path: str,
    *,
    root_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
) -> Path | None:
    trimmed = str(request_path).strip()
    path_without_query = re.sub(r"[?#].*$", "", trimmed)
    if path_without_query not in {CANVAS_HOST_PATH, f"{CANVAS_HOST_PATH}/"} and not (
        path_without_query.startswith(f"{CANVAS_HOST_PATH}/")
    ):
        return None

    relative_path = path_without_query[len(CANVAS_HOST_PATH) :]
    if relative_path.startswith(f"/{CANVAS_DOCUMENTS_DIR_NAME}/"):
        return None

    decoded_path = unquote(relative_path).replace("\\", "/")
    if decoded_path in {"", "/"}:
        normalized_path = "index.html"
    elif decoded_path.endswith("/"):
        normalized_path = _normalize_logical_path(f"{decoded_path}/index.html")
    else:
        try:
            normalized_path = _normalize_logical_path(decoded_path)
        except ValueError:
            return None

    canvas_root = resolve_canvas_root_dir(root_dir=root_dir, state_dir=state_dir).resolve()
    ensure_canvas_host_default_index(root_dir=canvas_root)
    candidate_path = (canvas_root / normalized_path).resolve()
    try:
        candidate_path.relative_to(canvas_root)
    except ValueError:
        return None
    if candidate_path.is_dir():
        candidate_path = candidate_path / "index.html"
    return candidate_path


def load_canvas_document_manifest(
    document_id: str,
    *,
    root_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
) -> dict[str, object] | None:
    normalized_id = _normalize_canvas_document_id(document_id)
    manifest_path = (
        resolve_canvas_document_dir(
            normalized_id,
            root_dir=root_dir,
            state_dir=state_dir,
        )
        / "manifest.json"
    )
    try:
        parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def resolve_canvas_document_assets(
    manifest: Mapping[str, object],
    *,
    base_url: str | None = None,
    root_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    document_id = _required_string(manifest.get("id"), label="id")
    assets_value = manifest.get("assets")
    if not isinstance(assets_value, list):
        return []
    normalized_base_url = str(base_url or "").strip().rstrip("/")
    document_dir = resolve_canvas_document_dir(
        document_id,
        root_dir=root_dir,
        state_dir=state_dir,
    )
    resolved_assets: list[dict[str, object]] = []
    for asset_value in assets_value:
        if not isinstance(asset_value, Mapping):
            continue
        logical_path = _normalize_logical_path(
            _required_string(asset_value.get("logicalPath"), label="logicalPath")
        )
        asset: dict[str, object] = {
            "logicalPath": logical_path,
            "localPath": document_dir / logical_path,
            "url": (
                f"{normalized_base_url}{build_canvas_document_asset_url(document_id, logical_path)}"
                if normalized_base_url
                else build_canvas_document_asset_url(document_id, logical_path)
            ),
        }
        content_type = str(asset_value.get("contentType") or "").strip()
        if content_type:
            asset["contentType"] = content_type
        resolved_assets.append(asset)
    return resolved_assets


def _generate_canvas_document_id() -> str:
    return f"cv_{uuid4().hex}"


def _copy_assets(
    root_dir: Path,
    assets_value: object,
    *,
    workspace_dir: str | Path | None,
) -> list[dict[str, str]]:
    if assets_value is None:
        return []
    if not isinstance(assets_value, list):
        raise ValueError("canvas document assets must be an array")

    copied_assets: list[dict[str, str]] = []
    for asset_value in assets_value:
        if not isinstance(asset_value, Mapping):
            raise ValueError("canvas document asset must be an object")
        logical_path = _normalize_logical_path(
            _required_string(asset_value.get("logicalPath"), label="asset.logicalPath")
        )
        source_path = _resolve_entrypoint_path(
            _required_string(asset_value.get("sourcePath"), label="asset.sourcePath"),
            workspace_dir=workspace_dir,
        )
        destination_path = root_dir / logical_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, destination_path)
        copied_asset = {"logicalPath": logical_path}
        content_type = str(asset_value.get("contentType") or "").strip()
        if content_type:
            copied_asset["contentType"] = content_type
        copied_assets.append(copied_asset)
    return copied_assets


def _materialize_entrypoint(
    root_dir: Path,
    *,
    kind: str,
    entrypoint_type: str,
    entrypoint_value: str,
    workspace_dir: str | Path | None,
) -> dict[str, str]:
    if entrypoint_type == "html":
        file_name = "index.html"
        (root_dir / file_name).write_text(entrypoint_value, encoding="utf-8")
        return {"localEntrypoint": file_name}

    if entrypoint_type == "url":
        if kind == "document" and _is_pdf_path_like(entrypoint_value):
            file_name = "index.html"
            (root_dir / file_name).write_text(
                _build_pdf_wrapper(entrypoint_value),
                encoding="utf-8",
            )
            return {"localEntrypoint": file_name, "externalUrl": entrypoint_value}
        return {"entryUrl": entrypoint_value, "externalUrl": entrypoint_value}

    if entrypoint_type != "path":
        raise ValueError("canvas document entrypoint type unsupported")

    source_path = _resolve_entrypoint_path(entrypoint_value, workspace_dir=workspace_dir)
    copied_name = source_path.name
    shutil.copyfile(source_path, root_dir / copied_name)
    if kind in {"image", "video_asset"}:
        file_name = "index.html"
        wrapper = (
            _build_image_wrapper(copied_name)
            if kind == "image"
            else _build_video_wrapper(copied_name)
        )
        (root_dir / file_name).write_text(wrapper, encoding="utf-8")
        return {"localEntrypoint": file_name}
    if kind == "document" and _is_pdf_path_like(copied_name):
        file_name = "index.html"
        (root_dir / file_name).write_text(_build_pdf_wrapper(copied_name), encoding="utf-8")
        return {"localEntrypoint": file_name}
    return {"localEntrypoint": copied_name}


def _resolve_entrypoint_path(value: str, *, workspace_dir: str | Path | None) -> Path:
    raw_path = Path(value).expanduser()
    if raw_path.is_absolute():
        return raw_path.resolve()
    workspace = Path.cwd() if workspace_dir is None else Path(workspace_dir).expanduser()
    return (workspace / raw_path).resolve()


def _is_pdf_path_like(value: str) -> bool:
    return re.search(r"\.pdf(?:[?#].*)?$", value.strip(), flags=re.IGNORECASE) is not None


def _build_pdf_wrapper(url: str) -> str:
    escaped = _escape_html(url)
    return (
        '<!doctype html><html><body style="margin:0;background:#e5e7eb;">'
        f'<object data="{escaped}" type="application/pdf" '
        'style="width:100%;height:100vh;border:0;">'
        f'<iframe src="{escaped}" style="width:100%;height:100vh;border:0;"></iframe>'
        '<p style="padding:16px;font:14px system-ui,sans-serif;">'
        "Unable to render PDF preview. "
        f'<a href="{escaped}" target="_blank" rel="noopener noreferrer">Open PDF</a>'
        "</p></object></body></html>"
    )


def _build_image_wrapper(path: str) -> str:
    escaped = _escape_html(path)
    return (
        '<!doctype html><html><body style="margin:0;background:#0f172a;'
        'display:flex;align-items:center;justify-content:center;">'
        f'<img src="{escaped}" '
        'style="max-width:100%;max-height:100vh;object-fit:contain;" />'
        "</body></html>"
    )


def _build_video_wrapper(path: str) -> str:
    escaped = _escape_html(path)
    return (
        '<!doctype html><html><body style="margin:0;background:#0f172a;">'
        f'<video src="{escaped}" controls autoplay '
        'style="width:100%;height:100vh;object-fit:contain;background:#000;"></video>'
        "</body></html>"
    )


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _write_json_manifest(path: Path, manifest: Mapping[str, object]) -> None:
    path.write_text(f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8")


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _required_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"canvas document {label} required")
    return value


def _required_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"canvas document {label} required")
    return value


def _decode_url_segment(value: str) -> str:
    try:
        return unquote(value)
    except ValueError:
        return value


def _normalize_logical_path(value: str) -> str:
    normalized = str(value).replace("\\", "/").lstrip("/")
    parts = [part for part in normalized.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        raise ValueError("canvas document logicalPath invalid")
    return "/".join(parts)


def _normalize_canvas_document_id(value: str) -> str:
    normalized = str(value).strip()
    if (
        not normalized
        or normalized in {".", ".."}
        or _CANVAS_DOCUMENT_ID_RE.fullmatch(normalized) is None
    ):
        raise ValueError("canvas document id invalid")
    return normalized
