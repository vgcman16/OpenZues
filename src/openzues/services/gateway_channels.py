from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from openzues.schemas import NotificationRouteView


class GatewayChannelsService:
    def __init__(
        self,
        *,
        list_notification_route_views: Callable[[], Awaitable[list[NotificationRouteView]]],
    ) -> None:
        self._list_notification_route_views = list_notification_route_views

    async def build_snapshot(self) -> dict[str, Any]:
        routes = await self._list_notification_route_views()
        route_payloads = [route.model_dump(mode="json") for route in routes]
        return {
            "routes": route_payloads,
            "routeCount": len(route_payloads),
            "enabledCount": sum(
                1 for route in route_payloads if bool(route.get("enabled"))
            ),
            "conversationTargetCount": sum(
                1 for route in route_payloads if route.get("conversation_target") is not None
            ),
        }
