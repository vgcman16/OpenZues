from __future__ import annotations

from typing import Protocol


class GatewaySubagentLifecycleService(Protocol):
    async def emit_subagent_ended(
        self,
        event: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        """Emit an OpenClaw-shaped subagent_ended lifecycle event."""
