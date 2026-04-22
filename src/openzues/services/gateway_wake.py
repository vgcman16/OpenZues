from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal

from openzues.database import Database


class GatewayWakeService:
    def __init__(
        self,
        database: Database,
        *,
        dispatch_now: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self._database = database
        self._dispatch_now = dispatch_now

    async def wake(
        self,
        *,
        mode: Literal["now", "next-heartbeat"],
        text: str,
        reason: str | None = None,
        agent_id: str | None = None,
        session_key: str | None = None,
    ) -> dict[str, bool]:
        normalized_text = text.strip()
        if not normalized_text:
            return {"ok": False}
        normalized_reason = reason.strip() if isinstance(reason, str) else ""
        if not normalized_reason:
            normalized_reason = "wake"
        payload: dict[str, str] = {"text": normalized_text, "reason": normalized_reason}
        if agent_id is not None:
            payload["agentId"] = agent_id
        if session_key is not None:
            payload["sessionKey"] = session_key
        await self._database.append_event(
            instance_id=None,
            thread_id=None,
            method="system-event",
            payload=payload,
        )
        await self._database.create_gateway_wake_request(
            mode=mode,
            text=normalized_text,
            reason=normalized_reason,
            agent_id=agent_id,
            session_key=session_key,
        )
        if mode == "now":
            if self._dispatch_now is None:
                raise RuntimeError("wake dispatch unavailable")
            await self._dispatch_now(normalized_text)
            return {"ok": True}
        return {"ok": True}

    async def claim_next_queued(
        self,
        *,
        modes: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        return await self._database.claim_next_gateway_wake_request(modes=modes)

    async def release(self, request_id: int) -> None:
        await self._database.release_gateway_wake_request(request_id)

    async def complete(self, request_id: int) -> None:
        await self._database.mark_gateway_wake_request_dispatched(request_id)
