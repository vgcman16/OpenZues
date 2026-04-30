from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class GatewayMessageActionDispatchRequest:
    channel: str
    action: str
    params: dict[str, Any]
    idempotency_key: str
    account_id: str | None = None
    requester_sender_id: str | None = None
    sender_is_owner: bool = False
    session_key: str | None = None
    session_id: str | None = None
    agent_id: str | None = None
    tool_context: dict[str, Any] | None = None


class GatewayMessageActionDispatcher(Protocol):
    def __call__(
        self,
        request: GatewayMessageActionDispatchRequest,
    ) -> Awaitable[dict[str, object] | None]:
        ...
