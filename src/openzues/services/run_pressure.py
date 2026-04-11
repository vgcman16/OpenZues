from __future__ import annotations

from collections.abc import Iterable

LEGACY_VERIFICATION_SPIKE_THRESHOLD = 40_000
LEGACY_CHECKPOINT_PRESSURE_THRESHOLD = 60_000
LONG_CONTEXT_VERIFICATION_SPIKE_THRESHOLD = 300_000
LONG_CONTEXT_CHECKPOINT_PRESSURE_THRESHOLD = 500_000
LONG_CONTEXT_CONTINUITY_SNAPSHOT_THRESHOLD = 250_000
LONG_CONTEXT_MODEL_MARKERS = (
    "gpt-5",
    "codex",
    "o3",
    "o4",
)


def _normalize_model_name(model: str | None) -> str:
    return str(model or "").strip().lower()


def is_long_context_model(model: str | None) -> bool:
    normalized = _normalize_model_name(model)
    if not normalized:
        return False
    return any(marker in normalized for marker in LONG_CONTEXT_MODEL_MARKERS)


def verification_spike_threshold(model: str | None) -> int:
    if is_long_context_model(model):
        return LONG_CONTEXT_VERIFICATION_SPIKE_THRESHOLD
    return LEGACY_VERIFICATION_SPIKE_THRESHOLD


def checkpoint_pressure_threshold(model: str | None) -> int:
    if is_long_context_model(model):
        return LONG_CONTEXT_CHECKPOINT_PRESSURE_THRESHOLD
    return LEGACY_CHECKPOINT_PRESSURE_THRESHOLD


def continuity_snapshot_threshold(model: str | None) -> int:
    if is_long_context_model(model):
        return LONG_CONTEXT_CONTINUITY_SNAPSHOT_THRESHOLD
    return LEGACY_VERIFICATION_SPIKE_THRESHOLD


def has_verification_spike_pressure(
    *,
    total_tokens: int,
    model: str | None,
    has_checkpoint: bool,
) -> bool:
    if has_checkpoint:
        return False
    return total_tokens >= verification_spike_threshold(model)


def has_checkpoint_pressure(
    *,
    total_tokens: int,
    model: str | None,
    has_checkpoint: bool,
) -> bool:
    if has_checkpoint:
        return False
    return total_tokens >= checkpoint_pressure_threshold(model)


def scope_checkpoint_pressure_threshold(models: Iterable[str | None]) -> int:
    normalized = [_normalize_model_name(model) for model in models if _normalize_model_name(model)]
    if not normalized:
        return LEGACY_CHECKPOINT_PRESSURE_THRESHOLD
    if all(is_long_context_model(model) for model in normalized):
        return LONG_CONTEXT_CHECKPOINT_PRESSURE_THRESHOLD
    return LEGACY_CHECKPOINT_PRESSURE_THRESHOLD
