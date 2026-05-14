from __future__ import annotations

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
