from __future__ import annotations

import base64
import binascii
import json
import os
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol, cast

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

BOT_FRAMEWORK_GLOBAL_AUDIENCE = "https://api.botframework.com"
BOT_FRAMEWORK_JWKS_URI = "https://login.botframework.com/v1/.well-known/keys"
ENTRA_COMMON_JWKS_URI = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
MSTEAMS_WEBHOOK_JWT_CLOCK_TOLERANCE_SECONDS = 300.0

MSTeamsJwksFetcher = Callable[[str], Awaitable[Mapping[str, object]]]
MSTeamsClock = Callable[[], float]


class MSTeamsWebhookJwtValidator(Protocol):
    async def validate(self, auth_header: str) -> bool:
        """Return whether a Microsoft Teams Bot Framework auth header is valid."""


class GatewayMSTeamsWebhookJwtValidator:
    def __init__(
        self,
        *,
        app_id: str,
        tenant_id: str,
        jwks_fetcher: MSTeamsJwksFetcher | None = None,
        now: MSTeamsClock | None = None,
    ) -> None:
        self.app_id = app_id
        self.tenant_id = tenant_id
        self._jwks_fetcher = jwks_fetcher or _fetch_jwks
        self._now = now or time.time
        self._jwks_cache: dict[str, Mapping[str, object]] = {}

    async def validate(self, auth_header: str) -> bool:
        token = _bearer_token(auth_header)
        if token is None:
            return False
        parsed = _decode_jwt(token)
        if parsed is None:
            return False
        header, payload, signing_input, signature = parsed
        if header.get("alg") != "RS256":
            return False
        kid = _non_empty_string(header.get("kid"))
        issuer = _non_empty_string(payload.get("iss"))
        if kid is None or issuer is None:
            return False
        jwks_uri = self._jwks_uri_for_issuer(issuer)
        if jwks_uri is None:
            return False
        public_key = await self._public_key_for_kid(jwks_uri, kid)
        if public_key is None:
            return False
        try:
            public_key.verify(
                signature,
                signing_input,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except InvalidSignature:
            return False
        if not self._payload_claims_are_valid(payload):
            return False
        return True

    def _jwks_uri_for_issuer(self, issuer: str) -> str | None:
        if issuer == "https://api.botframework.com":
            return BOT_FRAMEWORK_JWKS_URI
        if issuer == f"https://login.microsoftonline.com/{self.tenant_id}/v2.0":
            return ENTRA_COMMON_JWKS_URI
        if issuer == f"https://sts.windows.net/{self.tenant_id}/":
            return ENTRA_COMMON_JWKS_URI
        return None

    async def _public_key_for_kid(self, jwks_uri: str, kid: str) -> rsa.RSAPublicKey | None:
        jwks = await self._load_jwks(jwks_uri)
        raw_keys = jwks.get("keys")
        if not isinstance(raw_keys, list):
            return None
        for raw_key in raw_keys:
            if not isinstance(raw_key, Mapping):
                continue
            if _non_empty_string(raw_key.get("kid")) != kid:
                continue
            public_key = _rsa_public_key_from_jwk(raw_key)
            if public_key is not None:
                return public_key
        return None

    async def _load_jwks(self, jwks_uri: str) -> Mapping[str, object]:
        cached = self._jwks_cache.get(jwks_uri)
        if cached is not None:
            return cached
        jwks = await self._jwks_fetcher(jwks_uri)
        self._jwks_cache[jwks_uri] = jwks
        return jwks

    def _payload_claims_are_valid(self, payload: Mapping[str, object]) -> bool:
        if not _time_claims_are_valid(
            payload,
            now=self._now(),
            tolerance_seconds=MSTEAMS_WEBHOOK_JWT_CLOCK_TOLERANCE_SECONDS,
        ):
            return False
        audiences = _audience_claims(payload)
        allowed_audiences = {
            self.app_id,
            f"api://{self.app_id}",
            BOT_FRAMEWORK_GLOBAL_AUDIENCE,
        }
        if not any(audience in allowed_audiences for audience in audiences):
            return False
        if BOT_FRAMEWORK_GLOBAL_AUDIENCE in audiences and not _has_expected_bot_identity(
            payload,
            self.app_id,
        ):
            return False
        return True


def build_msteams_webhook_jwt_validator_from_config(
    snapshot: Mapping[str, object],
) -> MSTeamsWebhookJwtValidator | None:
    msteams_config = _msteams_channel_config(snapshot)
    if msteams_config is None:
        return None
    app_id = _secret_input_string(msteams_config.get("appId")) or _env_string("MSTEAMS_APP_ID")
    tenant_id = _secret_input_string(msteams_config.get("tenantId")) or _env_string(
        "MSTEAMS_TENANT_ID"
    )
    if app_id is None or tenant_id is None:
        return None
    auth_type = (
        _secret_input_string(msteams_config.get("authType"))
        or _env_string("MSTEAMS_AUTH_TYPE")
        or "secret"
    )
    if auth_type == "federated":
        has_certificate = bool(
            _secret_input_string(msteams_config.get("certificatePath"))
            or _env_string("MSTEAMS_CERTIFICATE_PATH")
        )
        use_managed_identity = _config_bool(msteams_config.get("useManagedIdentity")) or _env_bool(
            "MSTEAMS_USE_MANAGED_IDENTITY"
        )
        if not has_certificate and not use_managed_identity:
            return None
    elif not (
        _secret_input_present(msteams_config.get("appPassword"))
        or _env_string("MSTEAMS_APP_PASSWORD") is not None
    ):
        return None
    return GatewayMSTeamsWebhookJwtValidator(app_id=app_id, tenant_id=tenant_id)


async def _fetch_jwks(uri: str) -> Mapping[str, object]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(uri)
        response.raise_for_status()
        parsed = response.json()
    if not isinstance(parsed, Mapping):
        return {"keys": []}
    return cast(Mapping[str, object], parsed)


def _msteams_channel_config(snapshot: Mapping[str, object]) -> Mapping[str, object] | None:
    channels = snapshot.get("channels")
    if not isinstance(channels, Mapping):
        return None
    msteams = channels.get("msteams")
    if not isinstance(msteams, Mapping):
        msteams = channels.get("teams")
    return cast(Mapping[str, object], msteams) if isinstance(msteams, Mapping) else None


def _bearer_token(auth_header: str) -> str | None:
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def _decode_jwt(
    token: str,
) -> tuple[Mapping[str, object], Mapping[str, object], bytes, bytes] | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header = _decode_jwt_json_object(parts[0])
    payload = _decode_jwt_json_object(parts[1])
    signature = _base64url_decode(parts[2])
    if header is None or payload is None or signature is None:
        return None
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    return header, payload, signing_input, signature


def _decode_jwt_json_object(segment: str) -> Mapping[str, object] | None:
    decoded = _base64url_decode(segment)
    if decoded is None:
        return None
    try:
        parsed = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return cast(Mapping[str, object], parsed) if isinstance(parsed, Mapping) else None


def _base64url_decode(value: str) -> bytes | None:
    try:
        return base64.urlsafe_b64decode((value + "=" * ((4 - len(value) % 4) % 4)).encode("ascii"))
    except (binascii.Error, ValueError):
        return None


def _rsa_public_key_from_jwk(jwk: Mapping[str, object]) -> rsa.RSAPublicKey | None:
    if _non_empty_string(jwk.get("kty")) not in {None, "RSA"}:
        return None
    modulus = _base64url_decode(_non_empty_string(jwk.get("n")) or "")
    exponent = _base64url_decode(_non_empty_string(jwk.get("e")) or "")
    if modulus is None or exponent is None:
        return None
    try:
        numbers = rsa.RSAPublicNumbers(
            int.from_bytes(exponent, "big"),
            int.from_bytes(modulus, "big"),
        )
        return numbers.public_key()
    except ValueError:
        return None


def _audience_claims(payload: Mapping[str, object]) -> list[str]:
    audience = payload.get("aud")
    if isinstance(audience, str):
        normalized = audience.strip()
        return [normalized] if normalized else []
    if isinstance(audience, list):
        return [item.strip() for item in audience if isinstance(item, str) and item.strip()]
    return []


def _has_expected_bot_identity(payload: Mapping[str, object], app_id: str) -> bool:
    expected = app_id.strip().lower()
    if not expected:
        return False
    return (
        _normalized_claim(payload.get("appid")) == expected
        or _normalized_claim(payload.get("azp")) == expected
    )


def _time_claims_are_valid(
    payload: Mapping[str, object],
    *,
    now: float,
    tolerance_seconds: float,
) -> bool:
    exp = _optional_numeric_claim(payload.get("exp"))
    if payload.get("exp") is not None and exp is None:
        return False
    if exp is not None and exp < now - tolerance_seconds:
        return False
    nbf = _optional_numeric_claim(payload.get("nbf"))
    if payload.get("nbf") is not None and nbf is None:
        return False
    if nbf is not None and nbf > now + tolerance_seconds:
        return False
    return True


def _optional_numeric_claim(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _normalized_claim(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _non_empty_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _secret_input_string(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if not isinstance(value, Mapping):
        return None
    for key in ("value", "env", "secretId", "id", "path"):
        normalized = _non_empty_string(value.get(key))
        if normalized is not None:
            return normalized
    return None


def _secret_input_present(value: object) -> bool:
    return _secret_input_string(value) is not None


def _config_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _env_string(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _env_bool(name: str) -> bool:
    value = os.getenv(name)
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}
