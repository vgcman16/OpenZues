from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import TypedDict

DEFAULT_DIAGNOSTIC_STABILITY_CAPACITY = 1000
DEFAULT_DIAGNOSTIC_STABILITY_LIMIT = 50
MAX_DIAGNOSTIC_STABILITY_LIMIT = DEFAULT_DIAGNOSTIC_STABILITY_CAPACITY

_SAFE_REASON_CODE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")

_STRING_FIELDS = (
    "channel",
    "pluginId",
    "source",
    "target",
    "surface",
    "action",
    "outcome",
    "mode",
    "level",
    "detector",
    "deliveryKind",
    "toolName",
    "activeWorkKind",
    "pairedToolName",
    "provider",
    "model",
    "failureKind",
)
_NUMBER_FIELDS = (
    "durationMs",
    "requestBytes",
    "responseBytes",
    "timeToFirstByteMs",
    "resultCount",
    "commandLength",
    "exitCode",
    "costUsd",
    "count",
    "bytes",
    "limitBytes",
    "thresholdBytes",
    "rssGrowthBytes",
    "windowMs",
    "eventLoopDelayP99Ms",
    "eventLoopDelayMaxMs",
    "eventLoopUtilization",
    "cpuCoreRatio",
    "ageMs",
    "queueDepth",
    "queueSize",
    "waitMs",
    "active",
    "waiting",
    "queued",
)
_USAGE_FIELDS = ("input", "output", "cacheRead", "cacheWrite", "promptTokens", "total")
_CONTEXT_FIELDS = ("limit", "used")
_WEBHOOK_FIELDS = ("received", "processed", "errors")
_MEMORY_FIELDS = (
    "rssBytes",
    "heapTotalBytes",
    "heapUsedBytes",
    "externalBytes",
    "arrayBuffersBytes",
)


class _DiagnosticStabilityQuery(TypedDict):
    limit: int
    type: str | None
    sinceSeq: int | None


class GatewayDiagnosticStabilityService:
    def __init__(
        self,
        *,
        capacity: int = DEFAULT_DIAGNOSTIC_STABILITY_CAPACITY,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._now = now or (lambda: datetime.now(UTC))
        self._records: list[dict[str, object]] = []
        self._dropped = 0
        self._next_seq = 1

    @property
    def capacity(self) -> int:
        return self._capacity

    def record_event(self, event: Mapping[str, object]) -> dict[str, object]:
        record = self._sanitize_event(event)
        if len(self._records) >= self._capacity:
            self._records.pop(0)
            self._dropped += 1
        self._records.append(record)
        return dict(record)

    def snapshot(self, params: Mapping[str, object] | None = None) -> dict[str, object]:
        query = _normalize_diagnostic_stability_query(params)
        event_type = query["type"]
        since_seq = query["sinceSeq"]
        filtered = [
            record
            for record in self._records
            if (event_type is None or record.get("type") == event_type)
            and (
                since_seq is None
                or (
                    isinstance(seq_value := record.get("seq"), int)
                    and seq_value > since_seq
                )
            )
        ]
        limit = query["limit"]
        events = [dict(record) for record in filtered[-limit:]]
        return {
            "generatedAt": _format_generated_at(self._now()),
            "capacity": self._capacity,
            "count": len(filtered),
            "dropped": self._dropped,
            "firstSeq": filtered[0].get("seq") if filtered else None,
            "lastSeq": filtered[-1].get("seq") if filtered else None,
            "events": events,
            "summary": _summarize_diagnostic_stability_records(filtered),
        }

    def _sanitize_event(self, event: Mapping[str, object]) -> dict[str, object]:
        raw_type = event.get("type")
        if not isinstance(raw_type, str) or not raw_type.strip():
            raise ValueError("type must be a non-empty string")
        seq = _parse_record_seq(event.get("seq"), self._next_seq)
        self._next_seq = max(self._next_seq, seq + 1)
        record: dict[str, object] = {
            "seq": seq,
            "ts": _parse_record_ts(event.get("ts"), self._now),
            "type": raw_type.strip(),
        }
        for field in _STRING_FIELDS:
            value = event.get(field)
            if isinstance(value, str) and value:
                record[field] = value
        reason = event.get("reason")
        if isinstance(reason, str) and _SAFE_REASON_CODE.fullmatch(reason):
            record["reason"] = reason
        for field in _NUMBER_FIELDS:
            value = event.get(field)
            number_value = _finite_number(value)
            if number_value is not None:
                record[field] = number_value
        timed_out = event.get("timedOut")
        if isinstance(timed_out, bool):
            record["timedOut"] = timed_out
        usage = _copy_number_mapping(event.get("usage"), _USAGE_FIELDS)
        if usage:
            record["usage"] = usage
        context = _copy_number_mapping(event.get("context"), _CONTEXT_FIELDS)
        if context:
            record["context"] = context
        webhooks = _copy_number_mapping(event.get("webhooks"), _WEBHOOK_FIELDS)
        if webhooks:
            record["webhooks"] = webhooks
        memory = _copy_number_mapping(event.get("memory"), _MEMORY_FIELDS)
        if memory:
            record["memory"] = memory
        return record


def _normalize_diagnostic_stability_query(
    params: Mapping[str, object] | None,
) -> _DiagnosticStabilityQuery:
    payload = params or {}
    limit = _normalize_diagnostic_stability_limit(payload.get("limit"))
    return {
        "limit": limit,
        "type": _parse_optional_type(payload.get("type")),
        "sinceSeq": _parse_optional_non_negative_integer(
            payload.get("sinceSeq"),
            "sinceSeq",
        ),
    }


def _normalize_diagnostic_stability_limit(value: object) -> int:
    parsed = _parse_optional_non_negative_integer(value, "limit")
    if parsed is None:
        return DEFAULT_DIAGNOSTIC_STABILITY_LIMIT
    if parsed < 1 or parsed > MAX_DIAGNOSTIC_STABILITY_LIMIT:
        raise ValueError(
            f"limit must be between 1 and {MAX_DIAGNOSTIC_STABILITY_LIMIT}"
        )
    return parsed


def _parse_optional_non_negative_integer(value: object, field: str) -> int | None:
    if value is None or value == "":
        return None
    parsed: int | None = None
    if isinstance(value, bool):
        parsed = None
    elif isinstance(value, int):
        parsed = value
    elif isinstance(value, float) and value.is_integer():
        parsed = int(value)
    elif isinstance(value, str):
        normalized = value.strip()
        if re.fullmatch(r"[+-]?\d+", normalized):
            parsed = int(normalized)
    if parsed is None or parsed < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return parsed


def _parse_optional_type(value: object) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("type must be a non-empty string")
    return value.strip()


def _parse_record_seq(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    return default


def _parse_record_ts(value: object, now: Callable[[], datetime]) -> int:
    if isinstance(value, bool):
        value = None
    if isinstance(value, int | float) and value >= 0:
        return int(value)
    return int(now().timestamp() * 1000)


def _is_finite_number(value: object) -> bool:
    return _finite_number(value) is not None


def _finite_number(value: object) -> int | float | None:
    if (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and value == value
        and value not in {float("inf"), float("-inf")}
    ):
        return value
    return None


def _copy_number_mapping(value: object, fields: tuple[str, ...]) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, object] = {}
    for field in fields:
        field_value = _finite_number(value.get(field))
        if field_value is not None:
            result[field] = field_value
    return result


def _summarize_diagnostic_stability_records(
    records: list[dict[str, object]],
) -> dict[str, object]:
    by_type: dict[str, int] = {}
    latest_memory: dict[str, object] | None = None
    max_rss_bytes: int | float | None = None
    max_heap_used_bytes: int | float | None = None
    pressure_count = 0
    payload_large_count = 0
    payload_large_rejected = 0
    payload_large_truncated = 0
    payload_large_chunked = 0
    payload_large_by_surface: dict[str, int] = {}

    for record in records:
        record_type = str(record.get("type") or "")
        by_type[record_type] = by_type.get(record_type, 0) + 1
        memory = record.get("memory")
        if isinstance(memory, dict):
            latest_memory = dict(memory)
            rss_bytes = _finite_number(memory.get("rssBytes"))
            if rss_bytes is not None:
                max_rss_bytes = (
                    rss_bytes
                    if max_rss_bytes is None
                    else max(max_rss_bytes, rss_bytes)
                )
            heap_used_bytes = _finite_number(memory.get("heapUsedBytes"))
            if heap_used_bytes is not None:
                max_heap_used_bytes = (
                    heap_used_bytes
                    if max_heap_used_bytes is None
                    else max(max_heap_used_bytes, heap_used_bytes)
                )
        if record_type == "diagnostic.memory.pressure":
            pressure_count += 1
        if record_type == "payload.large":
            payload_large_count += 1
            action = record.get("action")
            if action == "rejected":
                payload_large_rejected += 1
            elif action == "truncated":
                payload_large_truncated += 1
            elif action == "chunked":
                payload_large_chunked += 1
            surface = str(record.get("surface") or "unknown")
            payload_large_by_surface[surface] = payload_large_by_surface.get(surface, 0) + 1

    summary: dict[str, object] = {"byType": by_type}
    if latest_memory is not None or pressure_count > 0:
        memory_summary: dict[str, object] = {"pressureCount": pressure_count}
        if latest_memory is not None:
            memory_summary["latest"] = latest_memory
        if max_rss_bytes is not None:
            memory_summary["maxRssBytes"] = max_rss_bytes
        if max_heap_used_bytes is not None:
            memory_summary["maxHeapUsedBytes"] = max_heap_used_bytes
        summary["memory"] = memory_summary
    if payload_large_count > 0:
        summary["payloadLarge"] = {
            "count": payload_large_count,
            "rejected": payload_large_rejected,
            "truncated": payload_large_truncated,
            "chunked": payload_large_chunked,
            "bySurface": payload_large_by_surface,
        }
    return summary


def _format_generated_at(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    normalized = normalized.astimezone(UTC).replace(microsecond=0)
    return normalized.isoformat().replace("+00:00", "Z")
