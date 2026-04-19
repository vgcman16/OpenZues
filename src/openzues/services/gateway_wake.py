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
    ) -> dict[str, bool]:
        normalized_text = text.strip()
        if not normalized_text:
            return {"ok": False}
        if mode == "now":
            if self._dispatch_now is None:
                raise RuntimeError("wake dispatch unavailable")
            await self._dispatch_now(normalized_text)
            return {"ok": True}
        await self._database.create_gateway_wake_request(
            mode=mode,
            text=normalized_text,
        )
        return {"ok": True}

    async def claim_next_queued(self) -> dict[str, Any] | None:
        return await self._database.claim_next_gateway_wake_request()

    async def release(self, request_id: int) -> None:
        await self._database.release_gateway_wake_request(request_id)

    async def complete(self, request_id: int) -> None:
        await self._database.mark_gateway_wake_request_dispatched(request_id)
