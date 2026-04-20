from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from openzues.schemas import NotificationRouteView
from openzues.services.session_keys import DEFAULT_ACCOUNT_ID

_CHANNEL_META = (
    {
        "id": "discord",
        "label": "Discord",
        "detailLabel": "Discord",
    },
    {
        "id": "slack",
        "label": "Slack",
        "detailLabel": "Slack",
    },
    {
        "id": "telegram",
        "label": "Telegram",
        "detailLabel": "Telegram",
    },
    {
        "id": "whatsapp",
        "label": "WhatsApp",
        "detailLabel": "WhatsApp",
    },
)


def _new_channel_summary() -> dict[str, int]:
    return {
        "routeCount": 0,
        "enabledRouteCount": 0,
        "conversationTargetCount": 0,
        "accountCount": 0,
    }


def _new_channel_account_summary(account_id: str) -> dict[str, Any]:
    return {
        "accountId": account_id,
        "routeCount": 0,
        "enabledRouteCount": 0,
        "conversationTargetCount": 0,
    }


def _resolve_channel_label(channel_id: str) -> str:
    normalized = channel_id.strip().replace("-", " ").replace("_", " ")
    return " ".join(part.capitalize() for part in normalized.split()) or channel_id


def _resolve_default_account_id(account_ids: tuple[str, ...]) -> str:
    if not account_ids:
        return DEFAULT_ACCOUNT_ID
    if DEFAULT_ACCOUNT_ID in account_ids:
        return DEFAULT_ACCOUNT_ID
    return sorted(account_ids)[0]


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

        known_channel_ids = tuple(entry["id"] for entry in _CHANNEL_META)
        meta_by_id = {entry["id"]: dict(entry) for entry in _CHANNEL_META}
        channel_summaries = {
            channel_id: _new_channel_summary() for channel_id in known_channel_ids
        }
        account_summaries: dict[str, dict[str, dict[str, Any]]] = {
            channel_id: {} for channel_id in known_channel_ids
        }
        extra_channel_ids: list[str] = []

        for route in routes:
            target = route.conversation_target
            if target is None:
                continue
            channel_id = str(target.channel or "").strip().lower()
            if not channel_id:
                continue
            if channel_id not in meta_by_id:
                label = _resolve_channel_label(channel_id)
                meta_by_id[channel_id] = {
                    "id": channel_id,
                    "label": label,
                    "detailLabel": label,
                }
                channel_summaries[channel_id] = _new_channel_summary()
                account_summaries[channel_id] = {}
                extra_channel_ids.append(channel_id)

            summary = channel_summaries[channel_id]
            summary["routeCount"] += 1
            summary["conversationTargetCount"] += 1
            if route.enabled:
                summary["enabledRouteCount"] += 1

            account_id = str(target.account_id or "").strip() or DEFAULT_ACCOUNT_ID
            accounts_for_channel = account_summaries[channel_id]
            account_summary = accounts_for_channel.get(account_id)
            if account_summary is None:
                account_summary = _new_channel_account_summary(account_id)
                accounts_for_channel[account_id] = account_summary
            account_summary["routeCount"] += 1
            account_summary["conversationTargetCount"] += 1
            if route.enabled:
                account_summary["enabledRouteCount"] += 1

        channel_order = [*known_channel_ids, *sorted(extra_channel_ids)]
        channel_labels = {
            channel_id: str(meta_by_id[channel_id]["label"]) for channel_id in channel_order
        }
        channel_detail_labels = {
            channel_id: str(meta_by_id[channel_id]["detailLabel"]) for channel_id in channel_order
        }
        channel_meta = [meta_by_id[channel_id] for channel_id in channel_order]
        channel_accounts_payload: dict[str, list[dict[str, Any]]] = {}
        channel_default_account_ids: dict[str, str] = {}

        for channel_id in channel_order:
            accounts_for_channel = account_summaries[channel_id]
            channel_summaries[channel_id]["accountCount"] = len(accounts_for_channel)
            sorted_accounts = [
                accounts_for_channel[account_id] for account_id in sorted(accounts_for_channel)
            ]
            channel_accounts_payload[channel_id] = sorted_accounts
            channel_default_account_ids[channel_id] = _resolve_default_account_id(
                tuple(accounts_for_channel)
            )

        return {
            "ts": int(time.time() * 1000),
            "channelOrder": channel_order,
            "channelLabels": channel_labels,
            "channelDetailLabels": channel_detail_labels,
            "channelMeta": channel_meta,
            "channels": {
                channel_id: dict(channel_summaries[channel_id]) for channel_id in channel_order
            },
            "channelAccounts": channel_accounts_payload,
            "channelDefaultAccountId": channel_default_account_ids,
            "routes": route_payloads,
            "routeCount": len(route_payloads),
            "enabledCount": sum(1 for route in route_payloads if bool(route.get("enabled"))),
            "conversationTargetCount": sum(
                1 for route in route_payloads if route.get("conversation_target") is not None
            ),
        }
