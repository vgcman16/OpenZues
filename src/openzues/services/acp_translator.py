from __future__ import annotations

import math
import os
import socket
from collections.abc import Mapping

from openzues.services.acp_event_mapper import (
    extract_attachments_from_prompt,
    extract_text_from_prompt,
)
from openzues.services.acp_session_mapper import parse_session_meta

MAX_PROMPT_BYTES = 2 * 1024 * 1024


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _read_string(meta: Mapping[str, object] | None, keys: tuple[str, ...]) -> str | None:
    if meta is None:
        return None
    for key in keys:
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _read_bool(meta: Mapping[str, object] | None, keys: tuple[str, ...]) -> bool | None:
    if meta is None:
        return None
    for key in keys:
        value = meta.get(key)
        if isinstance(value, bool):
            return value
    return None


def _read_number(meta: Mapping[str, object] | None, keys: tuple[str, ...]) -> int | float | None:
    if meta is None:
        return None
    for key in keys:
        value = meta.get(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        if math.isfinite(value):
            return value
    return None


def shorten_home_path(path: str) -> str:
    candidates = [
        value
        for value in (
            os.environ.get("OPENCLAW_HOME"),
            os.environ.get("USERPROFILE"),
            os.environ.get("HOME"),
            os.path.expanduser("~"),
        )
        if value
    ]
    for home in sorted(set(candidates), key=len, reverse=True):
        normalized_home = home.rstrip("\\/")
        if not normalized_home:
            continue
        if path == normalized_home:
            return "~"
        for separator in ("\\", "/"):
            prefix = f"{normalized_home}{separator}"
            if path.startswith(prefix):
                return f"~{path[len(normalized_home):]}"
    return path


def build_system_input_provenance(origin_session_id: str) -> dict[str, str]:
    return {
        "kind": "external_user",
        "originSessionId": origin_session_id,
        "sourceChannel": "acp",
        "sourceTool": "openclaw_acp",
    }


def build_system_provenance_receipt(
    *,
    cwd: str,
    session_id: str,
    session_key: str,
) -> str:
    return "\n".join(
        [
            "[Source Receipt]",
            "bridge=openclaw-acp",
            f"originHost={socket.gethostname()}",
            f"originCwd={shorten_home_path(cwd)}",
            f"acpSessionId={session_id}",
            f"originSessionId={session_id}",
            f"targetSession={session_key}",
            "[/Source Receipt]",
        ]
    )


def build_prompt_send_request(
    *,
    session: Mapping[str, object],
    prompt_request: Mapping[str, object],
    run_id: str,
    opts: Mapping[str, object],
) -> dict[str, object]:
    session_id = str(session.get("sessionId") or prompt_request.get("sessionId") or "")
    session_key = str(session.get("sessionKey") or "")
    cwd = str(session.get("cwd") or os.getcwd())
    meta = parse_session_meta(prompt_request.get("_meta"))
    raw_meta = _as_mapping(prompt_request.get("_meta"))
    prompt = prompt_request.get("prompt")
    prompt_blocks = prompt if isinstance(prompt, list) else []
    user_text = extract_text_from_prompt(prompt_blocks, max_bytes=MAX_PROMPT_BYTES)
    attachments = extract_attachments_from_prompt(prompt_blocks)
    meta_prefix = _read_bool(meta, ("prefixCwd",))
    opts_prefix = _read_bool(opts, ("prefixCwd",))
    prefix_cwd = meta_prefix if meta_prefix is not None else (
        opts_prefix if opts_prefix is not None else True
    )
    message = (
        f"[Working directory: {shorten_home_path(cwd)}]\n\n{user_text}"
        if prefix_cwd
        else user_text
    )
    if len(message.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise ValueError(f"Prompt exceeds maximum allowed size of {MAX_PROMPT_BYTES} bytes")

    request: dict[str, object] = {
        "sessionKey": session_key,
        "message": message,
        "idempotencyKey": run_id,
    }
    if attachments:
        request["attachments"] = attachments
    thinking = _read_string(raw_meta, ("thinking", "thinkingLevel"))
    deliver = _read_bool(raw_meta, ("deliver",))
    timeout_ms = _read_number(raw_meta, ("timeoutMs",))
    if thinking is not None:
        request["thinking"] = thinking
    if deliver is not None:
        request["deliver"] = deliver
    if timeout_ms is not None:
        request["timeoutMs"] = timeout_ms

    provenance_mode = _read_string(opts, ("provenanceMode",)) or "off"
    if provenance_mode != "off":
        request["systemInputProvenance"] = build_system_input_provenance(session_id)
    if provenance_mode == "meta+receipt":
        request["systemProvenanceReceipt"] = build_system_provenance_receipt(
            cwd=cwd,
            session_id=session_id,
            session_key=session_key,
        )
    return request
