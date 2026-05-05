from __future__ import annotations

import base64
import json
from collections.abc import Mapping

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from openzues.services.msteams_webhook_auth import (
    BOT_FRAMEWORK_GLOBAL_AUDIENCE,
    GatewayMSTeamsWebhookJwtValidator,
    build_msteams_webhook_jwt_validator_from_config,
)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _jwk_value(value: int) -> str:
    length = max(1, (value.bit_length() + 7) // 8)
    return _b64url(value.to_bytes(length, "big"))


def _signed_token(
    private_key: rsa.RSAPrivateKey,
    *,
    kid: str,
    payload: Mapping[str, object],
) -> str:
    header = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    signing_input = ".".join(
        [
            _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url(json.dumps(dict(payload), separators=(",", ":")).encode("utf-8")),
        ]
    ).encode("ascii")
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input.decode('ascii')}.{_b64url(signature)}"


@pytest.mark.asyncio
async def test_msteams_webhook_jwt_validator_accepts_bot_framework_global_audience() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "kid-1",
                "alg": "RS256",
                "n": _jwk_value(public_numbers.n),
                "e": _jwk_value(public_numbers.e),
            }
        ]
    }

    async def fetch_jwks(_uri: str) -> Mapping[str, object]:
        return jwks

    validator = GatewayMSTeamsWebhookJwtValidator(
        app_id="app-id",
        tenant_id="tenant-id",
        jwks_fetcher=fetch_jwks,
        now=lambda: 1_700_000_000.0,
    )
    token = _signed_token(
        private_key,
        kid="kid-1",
        payload={
            "iss": "https://api.botframework.com",
            "aud": BOT_FRAMEWORK_GLOBAL_AUDIENCE,
            "appid": "APP-ID",
            "exp": 1_700_000_600,
        },
    )

    assert await validator.validate(f"Bearer {token}") is True


@pytest.mark.asyncio
async def test_msteams_webhook_jwt_validator_rejects_wrong_global_audience_binding() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()

    async def fetch_jwks(_uri: str) -> Mapping[str, object]:
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "kid-1",
                    "alg": "RS256",
                    "n": _jwk_value(public_numbers.n),
                    "e": _jwk_value(public_numbers.e),
                }
            ]
        }

    validator = GatewayMSTeamsWebhookJwtValidator(
        app_id="app-id",
        tenant_id="tenant-id",
        jwks_fetcher=fetch_jwks,
        now=lambda: 1_700_000_000.0,
    )
    token = _signed_token(
        private_key,
        kid="kid-1",
        payload={
            "iss": "https://api.botframework.com",
            "aud": BOT_FRAMEWORK_GLOBAL_AUDIENCE,
            "azp": "other-app-id",
            "exp": 1_700_000_600,
        },
    )

    assert await validator.validate(f"Bearer {token}") is False


def test_msteams_webhook_jwt_validator_builds_from_configured_secret_credentials() -> None:
    validator = build_msteams_webhook_jwt_validator_from_config(
        {
            "channels": {
                "msteams": {
                    "appId": "app-id",
                    "tenantId": "tenant-id",
                    "appPassword": {"env": "MSTEAMS_APP_PASSWORD"},
                }
            }
        }
    )

    assert isinstance(validator, GatewayMSTeamsWebhookJwtValidator)
