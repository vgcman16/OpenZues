from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from openzues.services.session_keys import session_key_lookup_aliases


@dataclass(slots=True)
class _BroadcastSubscriber:
    queue: asyncio.Queue[dict[str, Any]]
    client_id: str | None = None


@dataclass(slots=True)
class _ClientSubscriptionState:
    sessions_subscribed: bool = False
    session_message_aliases: set[str] = field(default_factory=set)


class BroadcastHub:
    def __init__(self) -> None:
        self._subscribers: dict[asyncio.Queue[dict[str, Any]], _BroadcastSubscriber] = {}
        self._client_subscription_state: dict[str, _ClientSubscriptionState] = {}
        self._client_subscriber_counts: dict[str, int] = {}

    @asynccontextmanager
    async def subscribe(
        self,
        *,
        client_id: str | None = None,
    ) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        normalized_client_id = _normalized_client_id(client_id)
        self._subscribers[queue] = _BroadcastSubscriber(queue=queue, client_id=normalized_client_id)
        if normalized_client_id is not None:
            self._client_subscriber_counts[normalized_client_id] = (
                self._client_subscriber_counts.get(normalized_client_id, 0) + 1
            )
        try:
            yield queue
        finally:
            subscriber = self._subscribers.pop(queue, None)
            if subscriber is not None and subscriber.client_id is not None:
                remaining = self._client_subscriber_counts.get(subscriber.client_id, 0) - 1
                if remaining > 0:
                    self._client_subscriber_counts[subscriber.client_id] = remaining
                else:
                    self._client_subscriber_counts.pop(subscriber.client_id, None)
                    self._client_subscription_state.pop(subscriber.client_id, None)

    def set_sessions_subscription(self, *, client_id: str, subscribed: bool) -> bool:
        normalized_client_id = _require_client_id(client_id)
        state = self._client_subscription_state.setdefault(
            normalized_client_id,
            _ClientSubscriptionState(),
        )
        state.sessions_subscribed = subscribed
        self._prune_client_subscription_state(normalized_client_id)
        return subscribed

    def set_session_messages_subscription(
        self,
        *,
        client_id: str,
        session_key: str,
        subscribed: bool,
    ) -> bool:
        normalized_client_id = _require_client_id(client_id)
        aliases = _session_aliases(session_key)
        state = self._client_subscription_state.setdefault(
            normalized_client_id,
            _ClientSubscriptionState(),
        )
        if subscribed:
            state.session_message_aliases.update(aliases)
        else:
            state.session_message_aliases.difference_update(aliases)
        self._prune_client_subscription_state(normalized_client_id)
        return subscribed

    async def publish(self, event: dict[str, Any]) -> None:
        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for queue, subscriber in self._subscribers.items():
            try:
                if not self._event_visible_to_subscriber(subscriber.client_id, event):
                    continue
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(queue)
        for queue in dead:
            self._subscribers.pop(queue, None)

    def _event_visible_to_subscriber(
        self,
        client_id: str | None,
        event: dict[str, Any],
    ) -> bool:
        if client_id is None:
            return True
        if str(event.get("type") or "") != "gateway_event":
            return True
        event_name = str(event.get("event") or "")
        if event_name == "sessions.changed":
            state = self._client_subscription_state.get(client_id)
            return bool(state and state.sessions_subscribed)
        if event_name == "session.message":
            state = self._client_subscription_state.get(client_id)
            if state is None or not state.session_message_aliases:
                return False
            payload = event.get("payload")
            if not isinstance(payload, dict):
                return False
            session_key = str(payload.get("sessionKey") or "").strip()
            if not session_key:
                return False
            return bool(state.session_message_aliases.intersection(_session_aliases(session_key)))
        return True

    def _prune_client_subscription_state(self, client_id: str) -> None:
        state = self._client_subscription_state.get(client_id)
        if state is None:
            return
        if state.sessions_subscribed or state.session_message_aliases:
            return
        self._client_subscription_state.pop(client_id, None)


def _normalized_client_id(value: str | None) -> str | None:
    trimmed = str(value or "").strip()
    return trimmed or None


def _require_client_id(value: str | None) -> str:
    normalized = _normalized_client_id(value)
    if normalized is None:
        raise ValueError("client_id must be a non-empty string")
    return normalized


def _session_aliases(session_key: str) -> set[str]:
    aliases = session_key_lookup_aliases(session_key)
    if aliases:
        return set(aliases)
    trimmed = session_key.strip().lower()
    return {trimmed} if trimmed else set()
