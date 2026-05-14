from __future__ import annotations

import base64
import binascii
import hmac
import json
import secrets
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from openzues.services.device_bootstrap_profile import (
    default_device_bootstrap_profile,
    normalize_device_auth_role,
    normalize_device_auth_scopes,
    normalize_device_bootstrap_handoff_profile,
    normalize_device_bootstrap_profile,
    resolve_bootstrap_profile_scopes_for_role,
)

DEVICE_BOOTSTRAP_TOKEN_TTL_SECONDS = 10 * 60
_DEVICE_BOOTSTRAP_TOKEN_TTL_MS = DEVICE_BOOTSTRAP_TOKEN_TTL_SECONDS * 1000


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


def restore_device_bootstrap_token(
    *,
    base_dir: Path,
    record: Mapping[str, Any],
) -> None:
    token = str(record.get("token") or "").strip()
    if not token:
        return
    bootstrap_path = _bootstrap_token_path(base_dir)
    state = _read_bootstrap_state(bootstrap_path, now_ms=int(time.time() * 1000))
    state[token] = dict(record)
    _write_bootstrap_state(bootstrap_path, state)


def verify_device_bootstrap_token(
    *,
    base_dir: Path,
    token: str,
    device_id: str,
    public_key: str,
    role: str,
    scopes: Iterable[str],
) -> dict[str, object]:
    found = _find_bootstrap_record_entry(base_dir=base_dir, token=token)
    if found is None:
        return {"ok": False, "reason": "bootstrap_token_invalid"}
    state, token_key, record = found
    normalized_device_id = device_id.strip()
    normalized_public_key = _normalize_bootstrap_public_key(public_key)
    normalized_role = normalize_device_auth_role(role)
    if not normalized_device_id or not normalized_public_key or not normalized_role:
        return {"ok": False, "reason": "bootstrap_token_invalid"}
    profile = _record_bootstrap_profile(record)
    if not _bootstrap_profile_allows_request(
        profile=profile,
        role=normalized_role,
        scopes=scopes,
    ):
        return {"ok": False, "reason": "bootstrap_token_invalid"}
    bound_device_id = str(record.get("deviceId") or "").strip()
    bound_public_key = _normalize_bootstrap_public_key(str(record.get("publicKey") or ""))
    if (bound_device_id or bound_public_key) and (
        bound_device_id != normalized_device_id
        or bound_public_key != normalized_public_key
    ):
        return {"ok": False, "reason": "bootstrap_token_invalid"}
    state[token_key] = {
        **record,
        "profile": profile,
        "deviceId": normalized_device_id,
        "publicKey": normalized_public_key,
        "lastUsedAtMs": int(time.time() * 1000),
    }
    _write_bootstrap_state(_bootstrap_token_path(base_dir), state)
    return {"ok": True}


def get_bound_device_bootstrap_profile(
    *,
    base_dir: Path,
    token: str,
    device_id: str,
    public_key: str,
) -> dict[str, list[str]] | None:
    found = _find_bootstrap_record_entry(base_dir=base_dir, token=token)
    if found is None:
        return None
    _, _, record = found
    normalized_device_id = device_id.strip()
    normalized_public_key = _normalize_bootstrap_public_key(public_key)
    if not normalized_device_id or not normalized_public_key:
        return None
    if (
        str(record.get("deviceId") or "").strip() != normalized_device_id
        or _normalize_bootstrap_public_key(str(record.get("publicKey") or ""))
        != normalized_public_key
    ):
        return None
    return _record_bootstrap_profile(record)


def redeem_device_bootstrap_token_profile(
    *,
    base_dir: Path,
    token: str,
    role: str,
    scopes: Iterable[str],
) -> dict[str, bool]:
    found = _find_bootstrap_record_entry(base_dir=base_dir, token=token)
    if found is None:
        return {"recorded": False, "fullyRedeemed": False}
    state, token_key, record = found
    issued_profile = _record_bootstrap_profile(record)
    redeemed_profile = _record_redeemed_bootstrap_profile(record)
    redeemed_roles, redeemed_scopes = normalize_device_bootstrap_profile(
        [*redeemed_profile["roles"], role],
        [
            *redeemed_profile["scopes"],
            *resolve_bootstrap_profile_scopes_for_role(role, scopes),
        ],
    )
    next_redeemed_profile = {"roles": redeemed_roles, "scopes": redeemed_scopes}
    state[token_key] = {
        **record,
        "profile": issued_profile,
        "redeemedProfile": next_redeemed_profile,
    }
    _write_bootstrap_state(_bootstrap_token_path(base_dir), state)
    return {
        "recorded": True,
        "fullyRedeemed": _bootstrap_profile_satisfies_profile(
            actual_profile=next_redeemed_profile,
            required_profile=issued_profile,
        ),
    }


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


def _record_bootstrap_profile(record: Mapping[str, Any]) -> dict[str, list[str]]:
    raw_profile = record.get("profile")
    profile = raw_profile if isinstance(raw_profile, dict) else record
    roles, scopes = normalize_device_bootstrap_profile(
        profile.get("roles"),
        profile.get("scopes"),
    )
    return {"roles": roles, "scopes": scopes}


def _record_redeemed_bootstrap_profile(
    record: Mapping[str, Any],
) -> dict[str, list[str]]:
    raw_profile = record.get("redeemedProfile")
    profile = raw_profile if isinstance(raw_profile, dict) else {}
    roles, scopes = normalize_device_bootstrap_profile(
        profile.get("roles"),
        profile.get("scopes"),
    )
    return {"roles": roles, "scopes": scopes}


def _bootstrap_profile_satisfies_profile(
    *,
    actual_profile: Mapping[str, list[str]],
    required_profile: Mapping[str, list[str]],
) -> bool:
    actual_roles = actual_profile.get("roles") or []
    required_roles = required_profile.get("roles") or []
    for role in required_roles:
        if role not in actual_roles:
            return False
        required_scopes = resolve_bootstrap_profile_scopes_for_role(
            role,
            required_profile.get("scopes") or [],
        )
        if required_scopes and not _bootstrap_profile_allows_request(
            profile=actual_profile,
            role=role,
            scopes=required_scopes,
        ):
            return False
    return True


def _bootstrap_profile_allows_request(
    *,
    profile: Mapping[str, list[str]],
    role: str,
    scopes: Iterable[str],
) -> bool:
    roles = profile.get("roles") or []
    if role not in roles:
        return False
    requested_scopes = normalize_device_auth_scopes(scopes)
    if not requested_scopes:
        return True
    allowed_scopes = set(normalize_device_auth_scopes(profile.get("scopes") or []))
    if role != "operator":
        role_prefix = f"{role}."
        return all(
            scope.startswith(role_prefix) and scope in allowed_scopes
            for scope in requested_scopes
        )
    return all(scope in allowed_scopes for scope in requested_scopes)


def _normalize_bootstrap_public_key(public_key: str) -> str:
    trimmed = public_key.strip()
    if not trimmed:
        return ""
    if "BEGIN" in trimmed or any(marker in trimmed for marker in ("+", "/", "=")):
        normalized = _normalize_device_public_key_base64url(trimmed)
        return normalized if normalized is not None else trimmed
    return trimmed


def _normalize_device_public_key_base64url(public_key: str) -> str | None:
    try:
        if "BEGIN" in public_key:
            key = serialization.load_pem_public_key(public_key.encode("utf-8"))
            if isinstance(key, Ed25519PublicKey):
                public_key_bytes = key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )
            else:
                public_key_bytes = key.public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
        else:
            public_key_bytes = _base64_url_decode(public_key)
        if not public_key_bytes:
            return None
        return base64.urlsafe_b64encode(public_key_bytes).decode("ascii").rstrip("=")
    except (TypeError, ValueError, UnicodeEncodeError, binascii.Error):
        return None


def _base64_url_decode(value: str) -> bytes:
    normalized = value.replace("-", "+").replace("_", "/")
    padded = normalized + "=" * ((4 - len(normalized) % 4) % 4)
    return base64.b64decode(padded, validate=False)


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
        issued_at = value.get("issuedAtMs")
        ts = value.get("ts")
        record_ts = (
            ts
            if isinstance(ts, int | float)
            else issued_at
            if isinstance(issued_at, int | float)
            else 0
        )
        if now_ms - int(record_ts) > _DEVICE_BOOTSTRAP_TOKEN_TTL_MS:
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
