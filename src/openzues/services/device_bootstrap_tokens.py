from __future__ import annotations

import hmac
import json
import secrets
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openzues.services.device_bootstrap_profile import (
    default_device_bootstrap_profile,
    normalize_device_bootstrap_handoff_profile,
    normalize_device_bootstrap_profile,
)

DEVICE_BOOTSTRAP_TOKEN_TTL_SECONDS = 10 * 60


@dataclass(frozen=True, slots=True)
class DeviceBootstrapTokenIssue:
    token: str
    expires_at_ms: int


def issue_device_bootstrap_token(
    *,
    base_dir: Path,
    profile: Mapping[str, Iterable[str]] | None = None,
    roles: Iterable[str] | None = None,
    scopes: Iterable[str] | None = None,
) -> DeviceBootstrapTokenIssue:
    now_ms = int(time.time() * 1000)
    expires_at_ms = now_ms + DEVICE_BOOTSTRAP_TOKEN_TTL_SECONDS * 1000
    token = secrets.token_urlsafe(32)
    bootstrap_path = _bootstrap_token_path(base_dir)
    state = _read_bootstrap_state(bootstrap_path, now_ms=now_ms)
    bootstrap_roles, bootstrap_scopes = _issued_bootstrap_profile(
        profile=profile,
        roles=roles,
        scopes=scopes,
    )
    state[token] = {
        "token": token,
        "ts": now_ms,
        "issuedAtMs": now_ms,
        "expiresAtMs": expires_at_ms,
        "profile": {
            "roles": bootstrap_roles,
            "scopes": bootstrap_scopes,
        },
        "redeemedProfile": {
            "roles": [],
            "scopes": [],
        },
    }
    _write_bootstrap_state(bootstrap_path, state)
    return DeviceBootstrapTokenIssue(token=token, expires_at_ms=expires_at_ms)


def get_device_bootstrap_token_profile(
    *,
    base_dir: Path,
    token: str,
) -> dict[str, list[str]] | None:
    found = _find_bootstrap_record_entry(base_dir=base_dir, token=token)
    if found is None:
        return None
    _, _, record = found
    raw_profile = record.get("profile")
    profile = raw_profile if isinstance(raw_profile, dict) else record
    roles, scopes = normalize_device_bootstrap_profile(
        profile.get("roles"),
        profile.get("scopes"),
    )
    return {"roles": roles, "scopes": scopes}


def revoke_device_bootstrap_token(
    *,
    base_dir: Path,
    token: str,
) -> dict[str, object]:
    found = _find_bootstrap_record_entry(base_dir=base_dir, token=token)
    if found is None:
        return {"removed": False}
    state, token_key, record = found
    del state[token_key]
    _write_bootstrap_state(_bootstrap_token_path(base_dir), state)
    return {"removed": True, "record": record}


def clear_device_bootstrap_tokens(*, base_dir: Path) -> dict[str, int]:
    bootstrap_path = _bootstrap_token_path(base_dir)
    state = _read_bootstrap_state(bootstrap_path, now_ms=int(time.time() * 1000))
    removed = len(state)
    _write_bootstrap_state(bootstrap_path, {})
    return {"removed": removed}


def _issued_bootstrap_profile(
    *,
    profile: Mapping[str, Iterable[str]] | None,
    roles: Iterable[str] | None,
    scopes: Iterable[str] | None,
) -> tuple[list[str], list[str]]:
    if profile is not None:
        return normalize_device_bootstrap_handoff_profile(
            profile.get("roles"),
            profile.get("scopes"),
        )
    if roles is not None or scopes is not None:
        return normalize_device_bootstrap_handoff_profile(roles, scopes)
    return default_device_bootstrap_profile()


def _find_bootstrap_record_entry(
    *,
    base_dir: Path,
    token: str,
) -> tuple[dict[str, dict[str, Any]], str, dict[str, Any]] | None:
    provided_token = token.strip()
    if not provided_token:
        return None
    state = _read_bootstrap_state(
        _bootstrap_token_path(base_dir),
        now_ms=int(time.time() * 1000),
    )
    for token_key, record in state.items():
        persisted_token = str(record.get("token") or token_key)
        if hmac.compare_digest(provided_token, persisted_token):
            return state, token_key, record
    return None


def _bootstrap_token_path(base_dir: Path) -> Path:
    return base_dir / "devices" / "bootstrap.json"


def _read_bootstrap_state(path: Path, *, now_ms: int) -> dict[str, dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        raw = {}
    if not isinstance(raw, dict):
        return {}

    state: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        token = str(value.get("token") or key).strip()
        if not token:
            continue
        expires_at = value.get("expiresAtMs")
        if isinstance(expires_at, int | float) and expires_at <= now_ms:
            continue
        state[key] = dict(value)
    return state


def _write_bootstrap_state(path: Path, state: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        json.dumps(state, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(path)
