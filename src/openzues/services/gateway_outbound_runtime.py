from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

type _NativeAdapterKey = tuple[str, str | None]


def _normalize_optional_string(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _normalize_scope_tuple(scopes: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if scopes is None:
        return ()
    return tuple(str(scope).strip() for scope in scopes if str(scope).strip())


def _native_adapter_key(
    channel: str | None,
    account_id: str | None,
) -> _NativeAdapterKey | None:
    normalized_channel = _normalize_optional_string(channel)
    if normalized_channel is None:
        return None
    return normalized_channel.lower(), _normalize_optional_string(account_id)


def _session_delivery_message_id(result: object) -> str | None:
    if isinstance(result, dict):
        candidate = result.get("messageId") or result.get("id")
    else:
        candidate = getattr(result, "messageId", None) or getattr(result, "id", None)
    if candidate is None:
        return None
    return str(candidate).strip() or None


def _native_result_field(result: object, key: str) -> object | None:
    if isinstance(result, dict):
        return result.get(key)
    return getattr(result, key, None)


def _native_result_payload(result: object) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key in (
        "runtime",
        "messageId",
        "channel",
        "chatId",
        "channelId",
        "roomId",
        "toJid",
        "conversationId",
        "timestamp",
        "pollId",
        "mediaId",
        "mediaIds",
        "mediaUrl",
        "mediaUrls",
        "meta",
    ):
        value = _native_result_field(result, key)
        if value in (None, "", [], {}):
            continue
        if isinstance(value, (str, int, float, bool, list, dict)):
            payload[key] = value
        else:
            payload[key] = str(value)
    return payload


def _provider_runtime(result: object, default: str) -> str:
    candidate = _native_result_field(result, "runtime")
    normalized = str(candidate or "").strip()
    return normalized or default


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
    native_result: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GatewayOutboundRuntimeMessageRequest:
    channel: str
    target: str
    message: str
    media_urls: tuple[str, ...] = ()
    gif_playback: bool | None = None
    reply_to_id: str | None = None
    silent: bool | None = None
    force_document: bool | None = None
    account_id: str | None = None
    thread_id: str | None = None
    session_key: str | None = None
    agent_id: str | None = None
    requester_session_key: str | None = None
    requester_account_id: str | None = None
    requester_sender_id: str | None = None
    requester_sender_name: str | None = None
    requester_sender_username: str | None = None
    requester_sender_e164: str | None = None
    gateway_client_scopes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GatewayOutboundRuntimePollRequest:
    channel: str
    target: str
    question: str
    options: tuple[str, ...]
    max_selections: int | None = None
    duration_seconds: int | None = None
    duration_hours: int | None = None
    silent: bool | None = None
    is_anonymous: bool | None = None
    account_id: str | None = None
    thread_id: str | None = None
    session_key: str | None = None
    gateway_client_scopes: tuple[str, ...] = ()


class GatewayOutboundRuntimeUnavailableError(RuntimeError):
    pass


type GatewayOutboundSessionDeliverer = Callable[[str, str], Awaitable[object]]
type GatewayOutboundProviderMessageDeliverer = Callable[
    [GatewayOutboundRuntimeMessageRequest], Awaitable[object]
]
type GatewayOutboundProviderPollDeliverer = Callable[
    [GatewayOutboundRuntimePollRequest], Awaitable[object]
]


class GatewayOutboundRuntimeService:
    def __init__(
        self,
        *,
        session_deliverer: GatewayOutboundSessionDeliverer | None = None,
        provider_message_deliverer: GatewayOutboundProviderMessageDeliverer | None = None,
        provider_poll_deliverer: GatewayOutboundProviderPollDeliverer | None = None,
    ) -> None:
        self._session_deliverer = session_deliverer
        self._provider_message_deliverer = provider_message_deliverer
        self._provider_poll_deliverer = provider_poll_deliverer
        self._native_message_deliverers: dict[
            _NativeAdapterKey,
            GatewayOutboundProviderMessageDeliverer,
        ] = {}
        self._native_poll_deliverers: dict[
            _NativeAdapterKey,
            GatewayOutboundProviderPollDeliverer,
        ] = {}

    def bind_session_deliverer(
        self,
        session_deliverer: GatewayOutboundSessionDeliverer | None,
    ) -> None:
        self._session_deliverer = session_deliverer

    def bind_provider_message_deliverer(
        self,
        provider_message_deliverer: GatewayOutboundProviderMessageDeliverer | None,
    ) -> None:
        self._provider_message_deliverer = provider_message_deliverer

    def bind_provider_poll_deliverer(
        self,
        provider_poll_deliverer: GatewayOutboundProviderPollDeliverer | None,
    ) -> None:
        self._provider_poll_deliverer = provider_poll_deliverer

    def bind_native_message_deliverer(
        self,
        *,
        channel: str,
        deliverer: GatewayOutboundProviderMessageDeliverer | None,
        account_id: str | None = None,
    ) -> None:
        key = _native_adapter_key(channel, account_id)
        if key is None:
            raise ValueError("native message adapter requires a channel")
        if deliverer is None:
            self._native_message_deliverers.pop(key, None)
            return
        self._native_message_deliverers[key] = deliverer

    def bind_native_poll_deliverer(
        self,
        *,
        channel: str,
        deliverer: GatewayOutboundProviderPollDeliverer | None,
        account_id: str | None = None,
    ) -> None:
        key = _native_adapter_key(channel, account_id)
        if key is None:
            raise ValueError("native poll adapter requires a channel")
        if deliverer is None:
            self._native_poll_deliverers.pop(key, None)
            return
        self._native_poll_deliverers[key] = deliverer

    def _native_message_deliverer(
        self,
        *,
        channel: str | None,
        account_id: str | None,
    ) -> GatewayOutboundProviderMessageDeliverer | None:
        key = _native_adapter_key(channel, account_id)
        if key is None:
            return None
        return self._native_message_deliverers.get(key) or self._native_message_deliverers.get(
            (key[0], None)
        )

    def _native_poll_deliverer(
        self,
        *,
        channel: str | None,
        account_id: str | None,
    ) -> GatewayOutboundProviderPollDeliverer | None:
        key = _native_adapter_key(channel, account_id)
        if key is None:
            return None
        return self._native_poll_deliverers.get(key) or self._native_poll_deliverers.get(
            (key[0], None)
        )

    def is_available(self) -> bool:
        return (
            self._session_deliverer is not None
            or self._provider_message_deliverer is not None
            or self._provider_poll_deliverer is not None
            or bool(self._native_message_deliverers)
            or bool(self._native_poll_deliverers)
        )

    def is_message_available(self) -> bool:
        return (
            self._session_deliverer is not None
            or self._provider_message_deliverer is not None
            or bool(self._native_message_deliverers)
        )

    def has_session_deliverer(self) -> bool:
        return self._session_deliverer is not None

    def is_poll_available(self) -> bool:
        return (
            self._session_deliverer is not None
            or self._provider_poll_deliverer is not None
            or bool(self._native_poll_deliverers)
            or bool(self._native_message_deliverers)
        )

    def has_provider_message_deliverer(self) -> bool:
        return self._provider_message_deliverer is not None or bool(
            self._native_message_deliverers
        )

    def has_provider_poll_deliverer(self) -> bool:
        return self._provider_poll_deliverer is not None or bool(self._native_poll_deliverers)

    async def deliver_message(
        self,
        *,
        session_key: str,
        message: str,
        channel: str | None = None,
        target: str | None = None,
        media_urls: tuple[str, ...] = (),
        gif_playback: bool | None = None,
        reply_to_id: str | None = None,
        silent: bool | None = None,
        force_document: bool | None = None,
        account_id: str | None = None,
        thread_id: str | None = None,
        agent_id: str | None = None,
        requester_session_key: str | None = None,
        requester_account_id: str | None = None,
        requester_sender_id: str | None = None,
        requester_sender_name: str | None = None,
        requester_sender_username: str | None = None,
        requester_sender_e164: str | None = None,
        gateway_client_scopes: list[str] | tuple[str, ...] | None = None,
    ) -> GatewayOutboundRuntimeDeliveryResult:
        normalized_channel = _normalize_optional_string(channel)
        normalized_target = _normalize_optional_string(target)
        normalized_gateway_client_scopes = _normalize_scope_tuple(gateway_client_scopes)
        native_message_deliverer = self._native_message_deliverer(
            channel=normalized_channel,
            account_id=account_id,
        )
        if native_message_deliverer is not None and normalized_target is not None:
            try:
                message_result = await native_message_deliverer(
                    GatewayOutboundRuntimeMessageRequest(
                        channel=str(normalized_channel).lower(),
                        target=normalized_target,
                        message=message,
                        media_urls=media_urls,
                        gif_playback=gif_playback,
                        reply_to_id=_normalize_optional_string(reply_to_id),
                        silent=silent,
                        force_document=force_document,
                        account_id=_normalize_optional_string(account_id),
                        thread_id=_normalize_optional_string(thread_id),
                        session_key=_normalize_optional_string(session_key),
                        agent_id=_normalize_optional_string(agent_id),
                        requester_session_key=_normalize_optional_string(
                            requester_session_key
                        ),
                        requester_account_id=_normalize_optional_string(
                            requester_account_id
                        ),
                        requester_sender_id=_normalize_optional_string(
                            requester_sender_id
                        ),
                        requester_sender_name=_normalize_optional_string(
                            requester_sender_name
                        ),
                        requester_sender_username=_normalize_optional_string(
                            requester_sender_username
                        ),
                        requester_sender_e164=_normalize_optional_string(
                            requester_sender_e164
                        ),
                        gateway_client_scopes=normalized_gateway_client_scopes,
                    )
                )
            except GatewayOutboundRuntimeUnavailableError:
                if (
                    self._provider_message_deliverer is None
                    and self._session_deliverer is None
                ):
                    raise
            else:
                return GatewayOutboundRuntimeDeliveryResult(
                    message_id=_session_delivery_message_id(message_result),
                    native_result=_native_result_payload(message_result),
                    transport=GatewayOutboundRuntimeTransport(
                        runtime=_provider_runtime(
                            message_result,
                            "native-provider-backed",
                        ),
                        channel=normalized_channel,
                        target=normalized_target,
                        account_id=account_id,
                        thread_id=thread_id,
                        session_key=session_key,
                    ),
                )
        if (
            self._provider_message_deliverer is not None
            and normalized_channel is not None
            and normalized_target is not None
        ):
            try:
                message_result = await self._provider_message_deliverer(
                    GatewayOutboundRuntimeMessageRequest(
                        channel=normalized_channel.lower(),
                        target=normalized_target,
                        message=message,
                        media_urls=media_urls,
                        gif_playback=gif_playback,
                        reply_to_id=_normalize_optional_string(reply_to_id),
                        silent=silent,
                        force_document=force_document,
                        account_id=_normalize_optional_string(account_id),
                        thread_id=_normalize_optional_string(thread_id),
                        session_key=_normalize_optional_string(session_key),
                        agent_id=_normalize_optional_string(agent_id),
                        requester_session_key=_normalize_optional_string(
                            requester_session_key
                        ),
                        requester_account_id=_normalize_optional_string(
                            requester_account_id
                        ),
                        requester_sender_id=_normalize_optional_string(
                            requester_sender_id
                        ),
                        requester_sender_name=_normalize_optional_string(
                            requester_sender_name
                        ),
                        requester_sender_username=_normalize_optional_string(
                            requester_sender_username
                        ),
                        requester_sender_e164=_normalize_optional_string(
                            requester_sender_e164
                        ),
                        gateway_client_scopes=normalized_gateway_client_scopes,
                    )
                )
            except GatewayOutboundRuntimeUnavailableError:
                if self._session_deliverer is None:
                    raise
            else:
                return GatewayOutboundRuntimeDeliveryResult(
                    message_id=_session_delivery_message_id(message_result),
                    native_result=_native_result_payload(message_result),
                    transport=GatewayOutboundRuntimeTransport(
                        runtime=_provider_runtime(message_result, "provider-backed"),
                        channel=normalized_channel,
                        target=normalized_target,
                        account_id=account_id,
                        thread_id=thread_id,
                        session_key=session_key,
                    ),
                )
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

    async def deliver_poll(
        self,
        *,
        session_key: str,
        message: str,
        channel: str | None = None,
        target: str | None = None,
        question: str,
        options: tuple[str, ...],
        max_selections: int | None = None,
        duration_seconds: int | None = None,
        duration_hours: int | None = None,
        silent: bool | None = None,
        is_anonymous: bool | None = None,
        account_id: str | None = None,
        thread_id: str | None = None,
        gateway_client_scopes: list[str] | tuple[str, ...] | None = None,
    ) -> GatewayOutboundRuntimeDeliveryResult:
        normalized_channel = _normalize_optional_string(channel)
        normalized_target = _normalize_optional_string(target)
        normalized_gateway_client_scopes = _normalize_scope_tuple(gateway_client_scopes)
        native_poll_deliverer = self._native_poll_deliverer(
            channel=normalized_channel,
            account_id=account_id,
        )
        resolved_max_selections = max_selections if max_selections is not None else 1
        if native_poll_deliverer is not None and normalized_target is not None:
            try:
                poll_result = await native_poll_deliverer(
                    GatewayOutboundRuntimePollRequest(
                        channel=str(normalized_channel).lower(),
                        target=normalized_target,
                        question=question,
                        options=options,
                        max_selections=resolved_max_selections,
                        duration_seconds=duration_seconds,
                        duration_hours=duration_hours,
                        silent=silent,
                        is_anonymous=is_anonymous,
                        account_id=_normalize_optional_string(account_id),
                        thread_id=_normalize_optional_string(thread_id),
                        session_key=_normalize_optional_string(session_key),
                        gateway_client_scopes=normalized_gateway_client_scopes,
                    )
                )
            except GatewayOutboundRuntimeUnavailableError:
                if (
                    self._provider_poll_deliverer is None
                    and self._session_deliverer is None
                ):
                    raise
            else:
                return GatewayOutboundRuntimeDeliveryResult(
                    message_id=_session_delivery_message_id(poll_result),
                    native_result=_native_result_payload(poll_result),
                    transport=GatewayOutboundRuntimeTransport(
                        runtime=_provider_runtime(poll_result, "native-provider-backed"),
                        channel=normalized_channel,
                        target=normalized_target,
                        account_id=account_id,
                        thread_id=thread_id,
                        session_key=session_key,
                    ),
                )
        if (
            self._provider_poll_deliverer is not None
            and normalized_channel is not None
            and normalized_target is not None
        ):
            try:
                poll_result = await self._provider_poll_deliverer(
                    GatewayOutboundRuntimePollRequest(
                        channel=normalized_channel.lower(),
                        target=normalized_target,
                        question=question,
                        options=options,
                        max_selections=resolved_max_selections,
                        duration_seconds=duration_seconds,
                        duration_hours=duration_hours,
                        silent=silent,
                        is_anonymous=is_anonymous,
                        account_id=_normalize_optional_string(account_id),
                        thread_id=_normalize_optional_string(thread_id),
                        session_key=_normalize_optional_string(session_key),
                        gateway_client_scopes=normalized_gateway_client_scopes,
                    )
                )
            except GatewayOutboundRuntimeUnavailableError:
                if self._session_deliverer is None:
                    raise
            else:
                return GatewayOutboundRuntimeDeliveryResult(
                    message_id=_session_delivery_message_id(poll_result),
                    native_result=_native_result_payload(poll_result),
                    transport=GatewayOutboundRuntimeTransport(
                        runtime=_provider_runtime(poll_result, "provider-backed"),
                        channel=normalized_channel,
                        target=normalized_target,
                        account_id=account_id,
                        thread_id=thread_id,
                        session_key=session_key,
                    ),
                )
        return await self.deliver_message(
            session_key=session_key,
            message=message,
            channel=channel,
            target=target,
            account_id=account_id,
            thread_id=thread_id,
            gateway_client_scopes=normalized_gateway_client_scopes,
        )
