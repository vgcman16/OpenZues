from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import secrets
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

WEB_PUSH_STATE_FILENAME = Path("push") / "web-push-subscriptions.json"
VAPID_KEYS_FILENAME = Path("push") / "vapid-keys.json"
DEFAULT_VAPID_SUBJECT = "mailto:openclaw@localhost"
MAX_ENDPOINT_LENGTH = 2048
MAX_KEY_LENGTH = 512

GatewayWebPushSendNotification = Callable[..., Awaitable[dict[str, object]]]


class GatewayWebPushInvalidRequestError(ValueError):
    pass


class GatewayWebPushUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class GatewayWebPushVapidKeys:
    public_key: str
    private_key: str
    subject: str

    def to_gateway_payload(self) -> dict[str, str]:
        return {
            "publicKey": self.public_key,
            "privateKey": self.private_key,
            "subject": self.subject,
        }


@dataclass(frozen=True)
class GatewayWebPushSubscription:
    subscription_id: str
    endpoint: str
    keys: dict[str, str]
    created_at_ms: int
    updated_at_ms: int

    def to_gateway_payload(self) -> dict[str, object]:
        return {
            "subscriptionId": self.subscription_id,
            "endpoint": self.endpoint,
            "keys": dict(self.keys),
            "createdAtMs": self.created_at_ms,
            "updatedAtMs": self.updated_at_ms,
        }


class GatewayWebPushService:
    def __init__(
        self,
        *,
        state_dir: str | Path | None = None,
        send_notification: GatewayWebPushSendNotification | None = None,
        env: Mapping[str, str] | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self._state_dir = _resolve_state_dir(state_dir, env=env)
        self._send_notification = send_notification
        self._env = env
        self._clock_ms = clock_ms or _now_ms
        self._lock = asyncio.Lock()

    async def vapid_public_key(self) -> dict[str, str]:
        keys = await self.resolve_vapid_keys()
        return {"vapidPublicKey": keys.public_key}

    async def subscribe(
        self,
        *,
        endpoint: str,
        keys: Mapping[str, object],
    ) -> dict[str, str]:
        subscription = await self.register_subscription(endpoint=endpoint, keys=keys)
        return {"subscriptionId": subscription.subscription_id}

    async def unsubscribe(self, *, endpoint: str) -> dict[str, bool]:
        removed = await self.clear_subscription_by_endpoint(endpoint)
        return {"removed": removed}

    async def test(
        self,
        *,
        title: str = "OpenClaw",
        body: str = "Web push test notification",
    ) -> dict[str, object]:
        results = await self.broadcast({"title": title, "body": body})
        if not results:
            raise GatewayWebPushInvalidRequestError("no web push subscriptions registered")
        return {"results": results}

    async def resolve_vapid_keys(self) -> GatewayWebPushVapidKeys:
        env = self._env or os.environ
        env_public = _first_env(env, "OPENCLAW_VAPID_PUBLIC_KEY", "OPENZUES_VAPID_PUBLIC_KEY")
        env_private = _first_env(env, "OPENCLAW_VAPID_PRIVATE_KEY", "OPENZUES_VAPID_PRIVATE_KEY")
        if env_public and env_private:
            return GatewayWebPushVapidKeys(
                public_key=env_public,
                private_key=env_private,
                subject=_first_env(
                    env,
                    "OPENCLAW_VAPID_SUBJECT",
                    "OPENZUES_VAPID_SUBJECT",
                )
                or DEFAULT_VAPID_SUBJECT,
            )

        async with self._lock:
            payload = _read_json_object(self._vapid_keys_path())
            public_key = _optional_string(payload.get("publicKey"))
            private_key = _optional_string(payload.get("privateKey"))
            if public_key and private_key:
                return GatewayWebPushVapidKeys(
                    public_key=public_key,
                    private_key=private_key,
                    subject=_first_env(
                        env,
                        "OPENCLAW_VAPID_SUBJECT",
                        "OPENZUES_VAPID_SUBJECT",
                    )
                    or DEFAULT_VAPID_SUBJECT,
                )

            generated = GatewayWebPushVapidKeys(
                public_key=_generate_vapid_token(65),
                private_key=_generate_vapid_token(32),
                subject=_first_env(
                    env,
                    "OPENCLAW_VAPID_SUBJECT",
                    "OPENZUES_VAPID_SUBJECT",
                )
                or DEFAULT_VAPID_SUBJECT,
            )
            _write_json_object(self._vapid_keys_path(), generated.to_gateway_payload())
            return generated

    async def register_subscription(
        self,
        *,
        endpoint: str,
        keys: Mapping[str, object],
    ) -> GatewayWebPushSubscription:
        endpoint = _validate_endpoint(endpoint)
        p256dh = _validate_key(keys.get("p256dh"), label="keys.p256dh")
        auth = _validate_key(keys.get("auth"), label="keys.auth")

        async with self._lock:
            state = _read_state(self._subscriptions_path())
            endpoint_hash = _hash_endpoint(endpoint)
            now = self._clock_ms()
            existing = _subscription_from_payload(
                state["subscriptionsByEndpointHash"].get(endpoint_hash)
            )
            subscription = GatewayWebPushSubscription(
                subscription_id=existing.subscription_id if existing else str(uuid.uuid4()),
                endpoint=endpoint,
                keys={"p256dh": p256dh, "auth": auth},
                created_at_ms=existing.created_at_ms if existing else now,
                updated_at_ms=now,
            )
            state["subscriptionsByEndpointHash"][endpoint_hash] = (
                subscription.to_gateway_payload()
            )
            _write_json_object(self._subscriptions_path(), state)
            return subscription

    async def clear_subscription_by_endpoint(self, endpoint: str) -> bool:
        endpoint = _validate_endpoint(endpoint)
        async with self._lock:
            state = _read_state(self._subscriptions_path())
            endpoint_hash = _hash_endpoint(endpoint)
            if endpoint_hash not in state["subscriptionsByEndpointHash"]:
                return False
            del state["subscriptionsByEndpointHash"][endpoint_hash]
            _write_json_object(self._subscriptions_path(), state)
            return True

    async def list_subscriptions(self) -> list[GatewayWebPushSubscription]:
        state = _read_state(self._subscriptions_path())
        subscriptions = [
            subscription
            for payload in state["subscriptionsByEndpointHash"].values()
            if (subscription := _subscription_from_payload(payload)) is not None
        ]
        return subscriptions

    async def broadcast(self, payload: Mapping[str, object]) -> list[dict[str, object]]:
        subscriptions = await self.list_subscriptions()
        if not subscriptions:
            return []
        if self._send_notification is None:
            raise GatewayWebPushUnavailableError(
                "web push sender runtime is not configured"
            )

        vapid_keys = await self.resolve_vapid_keys()
        results: list[dict[str, object]] = []
        expired_endpoints: list[str] = []
        for subscription in subscriptions:
            try:
                raw_result = await self._send_notification(
                    subscription=subscription.to_gateway_payload(),
                    payload=dict(payload),
                    vapidKeys=vapid_keys.to_gateway_payload(),
                )
                result = _normalize_send_result(
                    raw_result,
                    subscription_id=subscription.subscription_id,
                )
            except Exception as exc:
                result = {
                    "ok": False,
                    "subscriptionId": subscription.subscription_id,
                    "error": str(exc).strip() or "unknown error",
                }
            results.append(result)
            status_code = result.get("statusCode")
            if result.get("ok") is False and status_code in (404, 410):
                expired_endpoints.append(subscription.endpoint)

        for endpoint in expired_endpoints:
            await self.clear_subscription_by_endpoint(endpoint)

        return results

    def _subscriptions_path(self) -> Path:
        return self._state_dir / WEB_PUSH_STATE_FILENAME

    def _vapid_keys_path(self) -> Path:
        return self._state_dir / VAPID_KEYS_FILENAME


def _resolve_state_dir(
    state_dir: str | Path | None,
    *,
    env: Mapping[str, str] | None,
) -> Path:
    if state_dir is not None:
        return Path(state_dir).expanduser().resolve()
    source = env or os.environ
    configured = _first_env(source, "OPENCLAW_STATE_DIR", "OPENZUES_STATE_DIR")
    if configured:
        return Path(os.path.expandvars(os.path.expanduser(configured))).resolve()
    return (Path.cwd() / ".openzues" / "state").resolve()


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json_object(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    temp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def _read_state(path: Path) -> dict[str, dict[str, object]]:
    payload = _read_json_object(path)
    subscriptions = payload.get("subscriptionsByEndpointHash")
    if not isinstance(subscriptions, dict):
        subscriptions = {}
    return {"subscriptionsByEndpointHash": dict(subscriptions)}


def _subscription_from_payload(payload: object) -> GatewayWebPushSubscription | None:
    if not isinstance(payload, dict):
        return None
    subscription_id = _optional_string(payload.get("subscriptionId"))
    endpoint = _optional_string(payload.get("endpoint"))
    raw_keys = payload.get("keys")
    if not subscription_id or not endpoint or not isinstance(raw_keys, dict):
        return None
    p256dh = _optional_string(raw_keys.get("p256dh"))
    auth = _optional_string(raw_keys.get("auth"))
    if not p256dh or not auth:
        return None
    created_at_ms = _optional_int(payload.get("createdAtMs")) or 0
    updated_at_ms = _optional_int(payload.get("updatedAtMs")) or created_at_ms
    return GatewayWebPushSubscription(
        subscription_id=subscription_id,
        endpoint=endpoint,
        keys={"p256dh": p256dh, "auth": auth},
        created_at_ms=created_at_ms,
        updated_at_ms=updated_at_ms,
    )


def _validate_endpoint(endpoint: object) -> str:
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > MAX_ENDPOINT_LENGTH:
        raise GatewayWebPushInvalidRequestError(
            "invalid push subscription endpoint: must be an HTTPS URL under 2048 chars"
        )
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        raise GatewayWebPushInvalidRequestError(
            "invalid push subscription endpoint: must be an HTTPS URL under 2048 chars"
        )
    return endpoint


def _validate_key(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_KEY_LENGTH:
        raise GatewayWebPushInvalidRequestError(
            "invalid push subscription keys: must be non-empty strings under 512 chars"
        )
    return value


def _hash_endpoint(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()[:32]


def _first_env(env: Mapping[str, str], *names: str) -> str | None:
    for name in names:
        value = env.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _now_ms() -> int:
    return int(asyncio.get_running_loop().time() * 1000)


def _generate_vapid_token(byte_count: int) -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(byte_count)).rstrip(b"=").decode("ascii")


def _normalize_send_result(
    result: Mapping[str, object],
    *,
    subscription_id: str,
) -> dict[str, object]:
    normalized: dict[str, object] = {
        "ok": bool(result.get("ok")),
        "subscriptionId": _optional_string(result.get("subscriptionId")) or subscription_id,
    }
    status_code = result.get("statusCode")
    if isinstance(status_code, int) and not isinstance(status_code, bool):
        normalized["statusCode"] = status_code
    error = _optional_string(result.get("error"))
    if error:
        normalized["error"] = error
    return normalized
