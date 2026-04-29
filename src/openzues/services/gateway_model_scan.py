from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
_DEFAULT_TIMEOUT_MS = 12_000
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


class GatewayModelScanService:
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
        entries = _fetch_openrouter_models(timeout_ms=timeout_ms)
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
            results.append(_build_scan_result(normalized, probe=probe))
        return results


def _fetch_openrouter_models(*, timeout_ms: int | None) -> list[dict[str, Any]]:
    timeout_seconds = max(1.0, (timeout_ms or _DEFAULT_TIMEOUT_MS) / 1000)
    request = Request(_OPENROUTER_MODELS_URL, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ValueError(f"OpenRouter /models failed: HTTP {exc.code}") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise ValueError(f"OpenRouter /models failed: {exc}") from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    return [entry for entry in data if isinstance(entry, dict)] if isinstance(data, list) else []


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


def _build_scan_result(entry: dict[str, Any], *, probe: bool) -> dict[str, Any]:
    supports_tools = bool(entry.get("supportsToolsMeta"))
    supports_image = "image" in str(entry.get("modality") or "").lower()
    skipped_probe = {"ok": False, "latencyMs": None, "skipped": True}
    return {
        **entry,
        "provider": "openrouter",
        "modelRef": f"openrouter/{entry['id']}",
        "isFree": True,
        "tool": {"ok": supports_tools, "latencyMs": None} if probe else skipped_probe,
        "image": {"ok": supports_image, "latencyMs": None} if probe else skipped_probe,
    }


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
