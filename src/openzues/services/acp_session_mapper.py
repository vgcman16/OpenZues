from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol


class AcpGatewayClient(Protocol):
    async def request(self, method: str, params: dict[str, object]) -> Mapping[str, object]:
        ...


def _read_string(meta: Mapping[str, object] | None, keys: Sequence[str]) -> str | None:
    if meta is None:
        return None
    for key in keys:
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _read_bool(meta: Mapping[str, object] | None, keys: Sequence[str]) -> bool | None:
    if meta is None:
        return None
    for key in keys:
        value = meta.get(key)
        if isinstance(value, bool):
            return value
    return None


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def parse_session_meta(meta: object) -> dict[str, object]:
    record = _as_mapping(meta)
    if record is None:
        return {}
    parsed: dict[str, object] = {}
    session_key = _read_string(record, ("sessionKey", "session", "key"))
    session_label = _read_string(record, ("sessionLabel", "label"))
    reset_session = _read_bool(record, ("resetSession", "reset"))
    require_existing = _read_bool(record, ("requireExistingSession", "requireExisting"))
    prefix_cwd = _read_bool(record, ("prefixCwd",))
    if session_key is not None:
        parsed["sessionKey"] = session_key
    if session_label is not None:
        parsed["sessionLabel"] = session_label
    if reset_session is not None:
        parsed["resetSession"] = reset_session
    if require_existing is not None:
        parsed["requireExisting"] = require_existing
    if prefix_cwd is not None:
        parsed["prefixCwd"] = prefix_cwd
    return parsed


async def _resolve_gateway_session(
    gateway: AcpGatewayClient,
    params: dict[str, object],
    *,
    error_prefix: str,
) -> str:
    resolved = await gateway.request("sessions.resolve", params)
    key = resolved.get("key")
    if not isinstance(key, str) or not key.strip():
        value = next(iter(params.values()), "")
        raise ValueError(f"{error_prefix}: {value}")
    return key


async def resolve_session_key(
    *,
    meta: Mapping[str, object],
    fallback_key: str,
    gateway: AcpGatewayClient,
    opts: Mapping[str, object],
) -> str:
    requested_label = _read_string(meta, ("sessionLabel",)) or _read_string(
        opts, ("defaultSessionLabel",)
    )
    requested_key = _read_string(meta, ("sessionKey",)) or _read_string(
        opts, ("defaultSessionKey",)
    )
    meta_require_existing = _read_bool(meta, ("requireExisting",))
    require_existing = (
        meta_require_existing
        if meta_require_existing is not None
        else (_read_bool(opts, ("requireExistingSession",)) or False)
    )

    meta_label = _read_string(meta, ("sessionLabel",))
    if meta_label is not None:
        return await _resolve_gateway_session(
            gateway,
            {"label": meta_label},
            error_prefix="Unable to resolve session label",
        )

    meta_key = _read_string(meta, ("sessionKey",))
    if meta_key is not None:
        if not require_existing:
            return meta_key
        return await _resolve_gateway_session(
            gateway,
            {"key": meta_key},
            error_prefix="Session key not found",
        )

    if requested_label is not None:
        return await _resolve_gateway_session(
            gateway,
            {"label": requested_label},
            error_prefix="Unable to resolve session label",
        )

    if requested_key is not None:
        if not require_existing:
            return requested_key
        return await _resolve_gateway_session(
            gateway,
            {"key": requested_key},
            error_prefix="Session key not found",
        )

    return fallback_key


async def reset_session_if_needed(
    *,
    meta: Mapping[str, object],
    session_key: str,
    gateway: AcpGatewayClient,
    opts: Mapping[str, object],
) -> None:
    meta_reset_session = _read_bool(meta, ("resetSession",))
    reset_session = (
        meta_reset_session
        if meta_reset_session is not None
        else (_read_bool(opts, ("resetSession",)) or False)
    )
    if not reset_session:
        return
    await gateway.request("sessions.reset", {"key": session_key})
