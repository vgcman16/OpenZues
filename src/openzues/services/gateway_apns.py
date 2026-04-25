from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

from openzues.services.gateway_identity import GatewayIdentityService
from openzues.services.gateway_node_methods import GatewayNodeMethodError
from openzues.settings import Settings

_DEFAULT_APNS_RELAY_TIMEOUT_MS = 10_000
_DEFAULT_APNS_TIMEOUT_MS = 10_000
_APNS_ENVIRONMENTS = {"sandbox", "production"}
_GATEWAY_DEVICE_ID_HEADER = "x-openclaw-gateway-device-id"
_GATEWAY_SIGNATURE_HEADER = "x-openclaw-gateway-signature"
_GATEWAY_SIGNED_AT_HEADER = "x-openclaw-gateway-signed-at-ms"


@dataclass(frozen=True, slots=True)
class GatewayApnsRelayConfig:
    base_url: str
    timeout_ms: int


@dataclass(frozen=True, slots=True)
class GatewayApnsDirectAuthConfig:
    team_id: str
    key_id: str
    private_key: str


class GatewayApnsPushService:
    def __init__(
        self,
        settings: Settings,
        *,
        gateway_identity_service: GatewayIdentityService,
    ) -> None:
        self._settings = settings
        self._gateway_identity_service = gateway_identity_service

    async def send_push(
        self,
        *,
        node_id: str,
        registration: dict[str, Any],
        title: str,
        body: str,
        environment: str | None,
    ) -> dict[str, object]:
        transport = _string_or_none(registration.get("transport")) or "direct"
        if transport == "direct":
            return await self._send_direct_push(
                node_id=node_id,
                registration=registration,
                title=title,
                body=body,
                environment=environment,
            )
        if transport != "relay":
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message=f"APNs registration transport is unsupported: {transport}",
                status_code=400,
            )
        relay_config = self._resolve_relay_config()
        relay_handle = _required_registration_string(registration, "relayHandle")
        send_grant = _required_registration_string(registration, "sendGrant")
        topic = _required_registration_string(registration, "topic")
        push_payload = _build_alert_payload(node_id=node_id, title=title, body=body)
        relay_result = await self._send_relay_delivery(
            relay_config=relay_config,
            relay_handle=relay_handle,
            send_grant=send_grant,
            push_type="alert",
            priority="10",
            payload=push_payload,
        )
        token_suffix = (
            _string_or_none(relay_result.get("tokenSuffix"))
            or _string_or_none(registration.get("tokenDebugSuffix"))
            or relay_handle[-8:]
        )
        return {
            "ok": relay_result["ok"],
            "status": relay_result["status"],
            "apnsId": relay_result.get("apnsId"),
            "reason": relay_result.get("reason"),
            "tokenSuffix": token_suffix,
            "topic": topic,
            "environment": "production",
            "transport": "relay",
        }

    async def send_wake(
        self,
        *,
        node_id: str,
        registration: dict[str, Any],
        wake_reason: str = "node.invoke",
    ) -> dict[str, object]:
        started_at = time.monotonic()
        transport = _string_or_none(registration.get("transport")) or "direct"
        try:
            if transport == "direct":
                result = await self._send_direct_wake(
                    node_id=node_id,
                    registration=registration,
                    wake_reason=wake_reason,
                )
            elif transport == "relay":
                relay_config = self._resolve_relay_config()
                relay_handle = _required_registration_string(registration, "relayHandle")
                send_grant = _required_registration_string(registration, "sendGrant")
                result = await self._send_relay_delivery(
                    relay_config=relay_config,
                    relay_handle=relay_handle,
                    send_grant=send_grant,
                    push_type="background",
                    priority="5",
                    payload=_build_background_payload(
                        node_id=node_id,
                        wake_reason=wake_reason,
                    ),
                )
            else:
                raise GatewayNodeMethodError(
                    code="INVALID_REQUEST",
                    message=f"APNs registration transport is unsupported: {transport}",
                    status_code=400,
                )
        except GatewayNodeMethodError as exc:
            no_auth = exc.code == "INVALID_REQUEST"
            return _build_wake_attempt_payload(
                started_at=started_at,
                available=not no_auth,
                path="no-auth" if no_auth else "send-error",
                apns_reason=str(exc),
            )
        return _build_wake_attempt_payload(
            started_at=started_at,
            available=True,
            path="sent" if result.get("ok") is True else "send-error",
            apns_status=_int_or_none(result.get("status")),
            apns_reason=_string_or_none(result.get("reason")),
        )

    async def _send_direct_push(
        self,
        *,
        node_id: str,
        registration: dict[str, Any],
        title: str,
        body: str,
        environment: str | None,
    ) -> dict[str, object]:
        token = _normalize_apns_token(_required_registration_string(registration, "token"))
        if not _is_likely_apns_token(token):
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message="invalid APNs token",
                status_code=400,
            )
        topic = _required_registration_string(registration, "topic")
        registration_environment = (
            _apns_environment_or_none(registration.get("environment")) or "sandbox"
        )
        resolved_environment = _apns_environment_or_none(environment) or registration_environment
        return await self._send_direct_delivery(
            token=token,
            topic=topic,
            environment=resolved_environment,
            payload=_build_alert_payload(node_id=node_id, title=title, body=body),
            push_type="alert",
            priority="10",
        )

    async def _send_direct_wake(
        self,
        *,
        node_id: str,
        registration: dict[str, Any],
        wake_reason: str,
    ) -> dict[str, object]:
        token = _normalize_apns_token(_required_registration_string(registration, "token"))
        if not _is_likely_apns_token(token):
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message="invalid APNs token",
                status_code=400,
            )
        topic = _required_registration_string(registration, "topic")
        environment = _apns_environment_or_none(registration.get("environment")) or "sandbox"
        return await self._send_direct_delivery(
            token=token,
            topic=topic,
            environment=environment,
            payload=_build_background_payload(node_id=node_id, wake_reason=wake_reason),
            push_type="background",
            priority="5",
        )

    async def _send_direct_delivery(
        self,
        *,
        token: str,
        topic: str,
        environment: str,
        payload: dict[str, object],
        push_type: str,
        priority: str,
    ) -> dict[str, object]:
        auth = self._resolve_direct_auth_config()
        body_json = json.dumps(payload, separators=(",", ":"))
        bearer_token = _build_apns_bearer_token(auth)
        authority = (
            "https://api.push.apple.com"
            if environment == "production"
            else "https://api.sandbox.push.apple.com"
        )
        headers = {
            "authorization": f"bearer {bearer_token}",
            "apns-topic": topic,
            "apns-push-type": push_type,
            "apns-priority": priority,
            "apns-expiration": "0",
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._resolve_direct_timeout_ms() / 1000,
                follow_redirects=False,
                http2=True,
            ) as client:
                response = await client.post(
                    f"{authority}/3/device/{token}",
                    content=body_json,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=f"APNs request timed out: {exc}",
                status_code=503,
            ) from exc
        except httpx.HTTPError as exc:
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=f"APNs request failed: {exc}",
                status_code=503,
            ) from exc
        return {
            "ok": response.status_code == 200,
            "status": response.status_code,
            "apnsId": _string_or_none(response.headers.get("apns-id")),
            "reason": _parse_apns_reason(response.text),
            "tokenSuffix": token[-8:],
            "topic": topic,
            "environment": environment,
            "transport": "direct",
        }

    def _resolve_direct_auth_config(self) -> GatewayApnsDirectAuthConfig:
        team_id = _string_or_none(os.environ.get("OPENCLAW_APNS_TEAM_ID")) or _string_or_none(
            self._settings.apns_team_id
        )
        key_id = _string_or_none(os.environ.get("OPENCLAW_APNS_KEY_ID")) or _string_or_none(
            self._settings.apns_key_id
        )
        if team_id is None or key_id is None:
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message="APNs auth missing: set OPENCLAW_APNS_TEAM_ID and OPENCLAW_APNS_KEY_ID",
                status_code=400,
            )
        inline_key = (
            _string_or_none(os.environ.get("OPENCLAW_APNS_PRIVATE_KEY_P8"))
            or _string_or_none(os.environ.get("OPENCLAW_APNS_PRIVATE_KEY"))
            or _string_or_none(self._settings.apns_private_key_p8)
        )
        if inline_key is not None:
            return GatewayApnsDirectAuthConfig(
                team_id=team_id,
                key_id=key_id,
                private_key=_normalize_private_key(inline_key),
            )
        key_path = _string_or_none(
            os.environ.get("OPENCLAW_APNS_PRIVATE_KEY_PATH")
        ) or _string_or_none(str(self._settings.apns_private_key_path or ""))
        if key_path is None:
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message=(
                    "APNs private key missing: set OPENCLAW_APNS_PRIVATE_KEY_P8 "
                    "or OPENCLAW_APNS_PRIVATE_KEY_PATH"
                ),
                status_code=400,
            )
        try:
            private_key = _normalize_private_key(
                self._settings.apns_private_key_path.read_text(encoding="utf-8")
                if self._settings.apns_private_key_path is not None
                and key_path == str(self._settings.apns_private_key_path)
                else Path(key_path).read_text(encoding="utf-8")
            )
        except OSError as exc:
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message=f"failed reading OPENCLAW_APNS_PRIVATE_KEY_PATH ({key_path}): {exc}",
                status_code=400,
            ) from exc
        return GatewayApnsDirectAuthConfig(
            team_id=team_id,
            key_id=key_id,
            private_key=private_key,
        )

    def _resolve_direct_timeout_ms(self) -> int:
        return _normalize_timeout_ms(
            os.environ.get("OPENCLAW_APNS_TIMEOUT_MS") or self._settings.apns_timeout_ms
        )

    def _resolve_relay_config(self) -> GatewayApnsRelayConfig:
        env_base_url = _string_or_none(os.environ.get("OPENCLAW_APNS_RELAY_BASE_URL"))
        settings_base_url = _string_or_none(self._settings.apns_relay_base_url)
        base_url = env_base_url or settings_base_url
        source = (
            "OPENCLAW_APNS_RELAY_BASE_URL"
            if env_base_url is not None
            else "OPENZUES_APNS_RELAY_BASE_URL"
        )
        if base_url is None:
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message=(
                    "APNs relay config missing: set OPENZUES_APNS_RELAY_BASE_URL "
                    "or OPENCLAW_APNS_RELAY_BASE_URL"
                ),
                status_code=400,
            )
        allow_http = self._settings.apns_relay_allow_http or _env_flag(
            os.environ.get("OPENCLAW_APNS_RELAY_ALLOW_HTTP")
        )
        timeout_ms = _normalize_timeout_ms(
            os.environ.get("OPENCLAW_APNS_RELAY_TIMEOUT_MS")
            or self._settings.apns_relay_timeout_ms
        )
        return GatewayApnsRelayConfig(
            base_url=_normalize_relay_base_url(
                base_url,
                source=source,
                allow_http=allow_http,
            ),
            timeout_ms=timeout_ms,
        )

    async def _send_relay_delivery(
        self,
        *,
        relay_config: GatewayApnsRelayConfig,
        relay_handle: str,
        send_grant: str,
        push_type: str,
        priority: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        body_json = json.dumps(
            {
                "relayHandle": relay_handle,
                "pushType": push_type,
                "priority": int(priority),
                "payload": payload,
            },
            separators=(",", ":"),
        )
        signed_at_ms = int(time.time() * 1000)
        signing_identity = self._gateway_identity_service.load_signing_identity()
        signature_payload = _build_relay_signature_payload(
            gateway_device_id=signing_identity.id,
            signed_at_ms=signed_at_ms,
            body_json=body_json,
        )
        device_id, signature = self._gateway_identity_service.sign_payload(
            signature_payload
        )
        headers = {
            "authorization": f"Bearer {send_grant}",
            "content-type": "application/json",
            _GATEWAY_DEVICE_ID_HEADER: device_id,
            _GATEWAY_SIGNATURE_HEADER: signature,
            _GATEWAY_SIGNED_AT_HEADER: str(signed_at_ms),
        }
        try:
            async with httpx.AsyncClient(
                timeout=relay_config.timeout_ms / 1000,
                follow_redirects=False,
            ) as client:
                response = await client.post(
                    f"{relay_config.base_url}/v1/push/send",
                    content=body_json,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=f"APNs relay request timed out: {exc}",
                status_code=503,
            ) from exc
        except httpx.HTTPError as exc:
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=f"APNs relay request failed: {exc}",
                status_code=503,
            ) from exc
        if 300 <= response.status_code < 400:
            return {
                "ok": False,
                "status": response.status_code,
                "reason": "RelayRedirectNotAllowed",
                "environment": "production",
            }
        response_payload = _response_json_object(response)
        status = _int_or_none(response_payload.get("status")) or response.status_code
        return {
            "ok": _bool_or_none(response_payload.get("ok"))
            if _bool_or_none(response_payload.get("ok")) is not None
            else response.is_success and 200 <= status < 300,
            "status": status,
            "apnsId": _string_or_none(response_payload.get("apnsId")),
            "reason": _string_or_none(response_payload.get("reason")),
            "environment": "production",
            "tokenSuffix": _string_or_none(response_payload.get("tokenSuffix")),
        }


def _build_relay_signature_payload(
    *,
    gateway_device_id: str,
    signed_at_ms: int,
    body_json: str,
) -> str:
    return "\n".join(
        [
            "openclaw-relay-send-v1",
            gateway_device_id.strip(),
            str(signed_at_ms),
            body_json,
        ]
    )


def _build_alert_payload(*, node_id: str, title: str, body: str) -> dict[str, object]:
    return {
        "aps": {
            "alert": {
                "title": title,
                "body": body,
            },
            "sound": "default",
        },
        "openclaw": {
            "kind": "push.test",
            "nodeId": node_id,
            "ts": int(time.time() * 1000),
        },
    }


def _build_background_payload(*, node_id: str, wake_reason: str) -> dict[str, object]:
    return {
        "aps": {
            "content-available": 1,
        },
        "openclaw": {
            "kind": "node.wake",
            "nodeId": node_id,
            "ts": int(time.time() * 1000),
            "reason": wake_reason or "node.invoke",
        },
    }


def _build_wake_attempt_payload(
    *,
    started_at: float,
    available: bool,
    path: str,
    apns_status: int | None = None,
    apns_reason: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "attempted": True,
        "available": available,
        "connected": False,
        "path": path,
        "durationMs": max(0, int((time.monotonic() - started_at) * 1000)),
    }
    if apns_status is not None:
        payload["apnsStatus"] = apns_status
    if apns_reason is not None:
        payload["apnsReason"] = apns_reason
    return payload


def _build_apns_bearer_token(auth: GatewayApnsDirectAuthConfig) -> str:
    issued_at = int(time.time())
    header = _base64_url_json({"alg": "ES256", "kid": auth.key_id, "typ": "JWT"})
    payload = _base64_url_json({"iss": auth.team_id, "iat": issued_at})
    signing_input = f"{header}.{payload}"
    private_key = _load_apns_private_key(auth.private_key)
    signature_der = private_key.sign(signing_input.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
    r_value, s_value = utils.decode_dss_signature(signature_der)
    signature = r_value.to_bytes(32, "big") + s_value.to_bytes(32, "big")
    return f"{signing_input}.{_base64_url_bytes(signature)}"


def _load_apns_private_key(private_key_pem: str) -> ec.EllipticCurvePrivateKey:
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None,
        )
    except (TypeError, ValueError) as exc:
        raise GatewayNodeMethodError(
            code="INVALID_REQUEST",
            message=f"APNs private key invalid: {exc}",
            status_code=400,
        ) from exc
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise GatewayNodeMethodError(
            code="INVALID_REQUEST",
            message="APNs private key invalid: expected an EC private key",
            status_code=400,
        )
    if private_key.curve.name != "secp256r1":
        raise GatewayNodeMethodError(
            code="INVALID_REQUEST",
            message="APNs private key invalid: expected P-256 curve",
            status_code=400,
        )
    return private_key


def _base64_url_json(value: dict[str, object]) -> str:
    return _base64_url_bytes(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _base64_url_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _normalize_relay_base_url(
    value: str,
    *,
    source: str,
    allow_http: bool,
) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"}:
        raise _invalid_relay_url(source, value, "unsupported protocol")
    if not parsed.hostname:
        raise _invalid_relay_url(source, value, "host required")
    if parsed.scheme == "http" and not allow_http:
        raise _invalid_relay_url(
            source,
            value,
            "http relay URLs require OPENCLAW_APNS_RELAY_ALLOW_HTTP=true",
        )
    if parsed.scheme == "http" and not _is_loopback_relay_hostname(parsed.hostname):
        raise _invalid_relay_url(source, value, "http relay URLs are limited to loopback hosts")
    if parsed.username or parsed.password:
        raise _invalid_relay_url(source, value, "userinfo is not allowed")
    if parsed.query or parsed.fragment:
        raise _invalid_relay_url(source, value, "query and fragment are not allowed")
    return value.rstrip("/")


def _invalid_relay_url(source: str, value: str, reason: str) -> GatewayNodeMethodError:
    return GatewayNodeMethodError(
        code="INVALID_REQUEST",
        message=f"invalid {source} ({value}): {reason}",
        status_code=400,
    )


def _is_loopback_relay_hostname(hostname: str) -> bool:
    normalized = hostname.strip().strip("[]").lower()
    if normalized == "localhost":
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _normalize_timeout_ms(value: object) -> int:
    if isinstance(value, bool):
        return _DEFAULT_APNS_RELAY_TIMEOUT_MS
    if isinstance(value, int | float):
        return max(1000, int(value))
    if isinstance(value, str):
        try:
            return max(1000, int(float(value.strip())))
        except ValueError:
            return _DEFAULT_APNS_RELAY_TIMEOUT_MS
    return _DEFAULT_APNS_RELAY_TIMEOUT_MS


def _normalize_apns_token(value: str) -> str:
    return "".join(value.replace("<", "").replace(">", "").split()).lower()


def _is_likely_apns_token(value: str) -> bool:
    if len(value) < 32 or len(value) > 512:
        return False
    return all(character in "0123456789abcdef" for character in value)


def _apns_environment_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized if normalized in _APNS_ENVIRONMENTS else None


def _normalize_private_key(value: str) -> str:
    return value.strip().replace("\\n", "\n")


def _parse_apns_reason(value: str) -> str | None:
    trimmed = value.strip()
    if not trimmed:
        return None
    try:
        payload = json.loads(trimmed)
    except json.JSONDecodeError:
        return trimmed[:200]
    if isinstance(payload, dict):
        reason = _string_or_none(payload.get("reason"))
        if reason is not None:
            return reason
    return trimmed[:200]


def _response_json_object(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _required_registration_string(registration: dict[str, Any], key: str) -> str:
    value = _string_or_none(registration.get(key))
    if value is None:
        raise GatewayNodeMethodError(
            code="INVALID_REQUEST",
            message=f"APNs relay registration is missing {key}",
            status_code=400,
        )
    return value


def _string_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _bool_or_none(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _env_flag(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return normalized in {"1", "true", "yes"}
