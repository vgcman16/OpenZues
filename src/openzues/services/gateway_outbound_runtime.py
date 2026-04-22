from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass


def _normalize_optional_string(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _session_delivery_message_id(result: object) -> str | None:
    if isinstance(result, dict):
        candidate = result.get("messageId") or result.get("id")
    else:
        candidate = getattr(result, "messageId", None) or getattr(result, "id", None)
    if candidate is None:
        return None
    return str(candidate).strip() or None


@dataclass(frozen=True, slots=True)
class GatewayOutboundRuntimeTransport:
    runtime: str
    channel: str | None = None
    target: str | None = None
    account_id: str | None = None
    thread_id: str | None = None
    session_key: str | None = None

    def as_payload(self) -> dict[str, str]:
        payload: dict[str, str] = {"runtime": self.runtime}
        channel = _normalize_optional_string(self.channel)
        if channel is not None:
            payload["channel"] = channel.lower()
        target = _normalize_optional_string(self.target)
        if target is not None:
            payload["target"] = target
        account_id = _normalize_optional_string(self.account_id)
        if account_id is not None:
            payload["account_id"] = account_id
        thread_id = _normalize_optional_string(self.thread_id)
        if thread_id is not None:
            payload["thread_id"] = thread_id
        session_key = _normalize_optional_string(self.session_key)
        if session_key is not None:
            payload["session_key"] = session_key
        return payload


@dataclass(frozen=True, slots=True)
class GatewayOutboundRuntimeDeliveryResult:
    message_id: str | None
    transport: GatewayOutboundRuntimeTransport


class GatewayOutboundRuntimeUnavailableError(RuntimeError):
    pass


type GatewayOutboundSessionDeliverer = Callable[[str, str], Awaitable[object]]


class GatewayOutboundRuntimeService:
    def __init__(
        self,
        *,
        session_deliverer: GatewayOutboundSessionDeliverer | None = None,
    ) -> None:
        self._session_deliverer = session_deliverer

    def bind_session_deliverer(
        self,
        session_deliverer: GatewayOutboundSessionDeliverer | None,
    ) -> None:
        self._session_deliverer = session_deliverer

    def is_available(self) -> bool:
        return self._session_deliverer is not None

    async def deliver_message(
        self,
        *,
        session_key: str,
        message: str,
        channel: str | None = None,
        target: str | None = None,
        account_id: str | None = None,
        thread_id: str | None = None,
    ) -> GatewayOutboundRuntimeDeliveryResult:
        if self._session_deliverer is None:
            raise GatewayOutboundRuntimeUnavailableError(
                "gateway outbound runtime is unavailable"
            )
        message_result = await self._session_deliverer(session_key, message)
        return GatewayOutboundRuntimeDeliveryResult(
            message_id=_session_delivery_message_id(message_result),
            transport=GatewayOutboundRuntimeTransport(
                runtime="session-backed",
                channel=channel,
                target=target,
                account_id=account_id,
                thread_id=thread_id,
                session_key=session_key,
            ),
        )
