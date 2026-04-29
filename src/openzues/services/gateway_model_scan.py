from __future__ import annotations

import asyncio
import json
import os
import re
import time
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
_OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_TIMEOUT_MS = 12_000
_BASE_IMAGE_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+X3mIAAAAASUVORK5CYII="
)
_PROVIDER_ALIASES = {
    "z.ai": "zai",
    "z-ai": "zai",
    "modelstudio": "qwen",
    "qwencloud": "qwen",
    "bedrock": "amazon-bedrock",
    "aws-bedrock": "amazon-bedrock",
    "bytedance": "volcengine",
    "doubao": "volcengine",
}
_PARAM_B_RE = re.compile(r"(?<![a-z0-9])(\d+(?:\.\d+)?)\s*b(?:\b|[^a-z0-9])", re.IGNORECASE)
_SKIPPED_PROBE = {"ok": False, "latencyMs": None, "skipped": True}
_Urlopen = Callable[..., Any]


class GatewayModelScanService:
    def __init__(self, *, urlopen_impl: _Urlopen = urlopen) -> None:
        self._urlopen = urlopen_impl

    async def scan(
        self,
        *,
        min_params: int | float | None = None,
        max_age_days: int | float | None = None,
        provider: str | None = None,
        timeout_ms: int | None = None,
        concurrency: int | None = None,
        probe: bool = True,
    ) -> list[dict[str, Any]]:
        del concurrency
        return await asyncio.to_thread(
            self._scan_sync,
            min_params=min_params,
            max_age_days=max_age_days,
            provider=provider,
            timeout_ms=timeout_ms,
            probe=probe,
        )

    def _scan_sync(
        self,
        *,
        min_params: int | float | None,
        max_age_days: int | float | None,
        provider: str | None,
        timeout_ms: int | None,
        probe: bool,
    ) -> list[dict[str, Any]]:
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if probe and not api_key:
            raise ValueError(
                "Missing OpenRouter API key. Set OPENROUTER_API_KEY to run models scan."
            )
        timeout_seconds = max(1.0, (timeout_ms or _DEFAULT_TIMEOUT_MS) / 1000)
        entries = _fetch_openrouter_models(
            timeout_seconds=timeout_seconds,
            urlopen_impl=self._urlopen,
        )
        now_ms = time.time() * 1000
        min_param_b = float(min_params or 0)
        max_age = float(max_age_days or 0)
        provider_filter = _normalize_provider(provider)
        results: list[dict[str, Any]] = []
        for entry in entries:
            normalized = _normalize_openrouter_entry(entry)
            if normalized is None:
                continue
            if not _is_free_model(normalized):
                continue
            model_prefix = _normalize_provider(str(normalized["id"]).split("/", 1)[0])
            if provider_filter and model_prefix != provider_filter:
                continue
            inferred = normalized["inferredParamB"]
            if min_param_b > 0 and (
                not isinstance(inferred, (int, float)) or inferred < min_param_b
            ):
                continue
            created_at_ms = normalized["createdAtMs"]
            if max_age > 0 and isinstance(created_at_ms, (int, float)):
                age_days = (now_ms - created_at_ms) / (24 * 60 * 60 * 1000)
                if age_days > max_age:
                    continue
            if not probe:
                results.append(
                    _build_scan_result(
                        normalized,
                        tool=dict(_SKIPPED_PROBE),
                        image=dict(_SKIPPED_PROBE),
                    )
                )
                continue
            tool = _probe_tool(
                normalized,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
                urlopen_impl=self._urlopen,
            )
            image = (
                _probe_image(
                    normalized,
                    api_key=api_key,
                    timeout_seconds=timeout_seconds,
                    urlopen_impl=self._urlopen,
                )
                if _supports_image_input(normalized)
                else dict(_SKIPPED_PROBE)
            )
            results.append(_build_scan_result(normalized, tool=tool, image=image))
        return results


def _fetch_openrouter_models(
    *,
    timeout_seconds: float,
    urlopen_impl: _Urlopen,
) -> list[dict[str, Any]]:
    request = Request(_OPENROUTER_MODELS_URL, headers={"Accept": "application/json"})
    try:
        with urlopen_impl(request, timeout=timeout_seconds) as response:
            payload = _read_json_response(response)
    except HTTPError as exc:
        raise ValueError(f"OpenRouter /models failed: HTTP {exc.code}") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise ValueError(f"OpenRouter /models failed: {exc}") from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    return [entry for entry in data if isinstance(entry, dict)] if isinstance(data, list) else []


def _post_openrouter_chat(
    payload: dict[str, Any],
    *,
    api_key: str,
    timeout_seconds: float,
    urlopen_impl: _Urlopen,
) -> dict[str, Any]:
    request = Request(
        _OPENROUTER_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen_impl(request, timeout=timeout_seconds) as response:
        response_payload = _read_json_response(response)
    return response_payload if isinstance(response_payload, dict) else {}


def _read_json_response(response: object) -> object:
    read = getattr(response, "read", None)
    if not callable(read):
        return {}
    return json.loads(read().decode("utf-8"))


def _normalize_openrouter_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    model_id = str(entry.get("id") or "").strip()
    if not model_id:
        return None
    name = str(entry.get("name") or model_id).strip() or model_id
    context_length = _number_or_none(entry.get("context_length"))
    max_completion_tokens = _number_or_none(
        entry.get("max_completion_tokens", entry.get("max_output_tokens"))
    )
    supported_parameters = [
        str(value).strip()
        for value in entry.get("supported_parameters", [])
        if str(value).strip()
    ] if isinstance(entry.get("supported_parameters"), list) else []
    modality = str(entry.get("modality") or "").strip() or None
    pricing = _pricing_from_entry(entry.get("pricing"))
    return {
        "id": model_id,
        "name": name,
        "contextLength": context_length,
        "maxCompletionTokens": max_completion_tokens,
        "supportedParametersCount": len(supported_parameters),
        "supportsToolsMeta": "tools" in supported_parameters,
        "modality": modality,
        "inferredParamB": _infer_param_b(f"{model_id} {name}"),
        "createdAtMs": _created_at_ms(entry.get("created_at")),
        "pricing": pricing,
    }


def _probe_tool(
    entry: dict[str, Any],
    *,
    api_key: str,
    timeout_seconds: float,
    urlopen_impl: _Urlopen,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        payload = _post_openrouter_chat(
            {
                "model": entry["id"],
                "messages": [
                    {
                        "role": "user",
                        "content": "Call the ping tool with {} and nothing else.",
                    }
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "ping",
                            "description": "Return OK.",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": False,
                            },
                        },
                    }
                ],
                "tool_choice": "required",
                "max_tokens": 256,
                "temperature": 0,
            },
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            urlopen_impl=urlopen_impl,
        )
        if _response_has_tool_call(payload):
            return {"ok": True, "latencyMs": _elapsed_ms(started)}
        return {
            "ok": False,
            "latencyMs": _elapsed_ms(started),
            "error": "No tool call returned",
        }
    except (HTTPError, OSError, URLError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "latencyMs": _elapsed_ms(started), "error": str(exc)}


def _probe_image(
    entry: dict[str, Any],
    *,
    api_key: str,
    timeout_seconds: float,
    urlopen_impl: _Urlopen,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        _post_openrouter_chat(
            {
                "model": entry["id"],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Reply with OK."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{_BASE_IMAGE_PNG}"
                                },
                            },
                        ],
                    }
                ],
                "max_tokens": 16,
                "temperature": 0,
            },
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            urlopen_impl=urlopen_impl,
        )
        return {"ok": True, "latencyMs": _elapsed_ms(started)}
    except (HTTPError, OSError, URLError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "latencyMs": _elapsed_ms(started), "error": str(exc)}


def _build_scan_result(
    entry: dict[str, Any],
    *,
    tool: dict[str, Any],
    image: dict[str, Any],
) -> dict[str, Any]:
    return {
        **entry,
        "provider": "openrouter",
        "modelRef": f"openrouter/{entry['id']}",
        "isFree": True,
        "tool": tool,
        "image": image,
    }


def _supports_image_input(entry: dict[str, Any]) -> bool:
    return "image" in str(entry.get("modality") or "").lower()


def _response_has_tool_call(payload: dict[str, Any]) -> bool:
    choices = payload.get("choices")
    if not isinstance(choices, list):
        return False
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            return True
    return False


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


def _pricing_from_entry(value: object) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    prompt = _number_or_none(value.get("prompt"))
    completion = _number_or_none(value.get("completion"))
    if prompt is None or completion is None:
        return None
    return {
        "prompt": prompt,
        "completion": completion,
        "request": _number_or_none(value.get("request")) or 0,
        "image": _number_or_none(value.get("image")) or 0,
        "webSearch": _number_or_none(value.get("web_search")) or 0,
        "internalReasoning": _number_or_none(value.get("internal_reasoning")) or 0,
    }


def _is_free_model(entry: dict[str, Any]) -> bool:
    model_id = str(entry.get("id") or "")
    if model_id.endswith(":free"):
        return True
    pricing = entry.get("pricing")
    if not isinstance(pricing, dict):
        return False
    return pricing.get("prompt") == 0 and pricing.get("completion") == 0


def _normalize_provider(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    return _PROVIDER_ALIASES.get(normalized, normalized)


def _number_or_none(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value == value:
        return float(value)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _created_at_ms(value: object) -> int | None:
    number = _number_or_none(value)
    if number is None or number <= 0:
        return None
    return round(number if number > 1e12 else number * 1000)


def _infer_param_b(value: str) -> float | None:
    match = _PARAM_B_RE.search(value)
    if match is None:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None
