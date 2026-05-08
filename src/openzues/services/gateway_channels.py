from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol

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
    {
        "id": "zalo",
        "label": "Zalo",
        "detailLabel": "Zalo",
    },
    {
        "id": "feishu",
        "label": "Feishu/Lark",
        "detailLabel": "Feishu/Lark",
    },
    {
        "id": "googlechat",
        "label": "Google Chat",
        "detailLabel": "Google Chat",
    },
    {
        "id": "nextcloud-talk",
        "label": "Nextcloud Talk",
        "detailLabel": "Nextcloud Talk",
    },
    {
        "id": "synology-chat",
        "label": "Synology Chat",
        "detailLabel": "Synology Chat",
    },
    {
        "id": "mattermost",
        "label": "Mattermost",
        "detailLabel": "Mattermost",
    },
    {
        "id": "msteams",
        "label": "Microsoft Teams",
        "detailLabel": "Microsoft Teams",
    },
    {
        "id": "signal",
        "label": "Signal",
        "detailLabel": "Signal",
    },
    {
        "id": "irc",
        "label": "IRC",
        "detailLabel": "IRC",
    },
    {
        "id": "twitch",
        "label": "Twitch",
        "detailLabel": "Twitch",
    },
    {
        "id": "imessage",
        "label": "iMessage",
        "detailLabel": "iMessage",
    },
    {
        "id": "tlon",
        "label": "Tlon",
        "detailLabel": "Tlon (Urbit)",
    },
    {
        "id": "line",
        "label": "LINE",
        "detailLabel": "LINE",
    },
    {
        "id": "matrix",
        "label": "Matrix",
        "detailLabel": "Matrix",
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


_IMESSAGE_CONFIGURED_FIELDS = (
    "cliPath",
    "dbPath",
    "service",
    "region",
    "dmPolicy",
    "groupPolicy",
)
_IMESSAGE_CONFIGURED_LIST_FIELDS = (
    "allowFrom",
    "groupAllowFrom",
    "attachmentRoots",
    "remoteAttachmentRoots",
)


def _normalized_config_account_id(account_id: str | None) -> str:
    return str(account_id or "").strip() or DEFAULT_ACCOUNT_ID


def _config_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def imessage_account_configured(config: Mapping[str, Any]) -> bool:
    for field_name in _IMESSAGE_CONFIGURED_FIELDS:
        if _config_string(config.get(field_name)) is not None:
            return True
    for field_name in _IMESSAGE_CONFIGURED_LIST_FIELDS:
        value = config.get(field_name)
        if isinstance(value, list) and value:
            return True
    groups = config.get("groups")
    if isinstance(groups, dict) and groups:
        return True
    for field_name in ("includeAttachments",):
        if isinstance(config.get(field_name), bool):
            return True
    for field_name in ("mediaMaxMb", "textChunkLimit"):
        if isinstance(config.get(field_name), int | float) and not isinstance(
            config.get(field_name),
            bool,
        ):
            return True
    return False


def _imessage_channel_config(snapshot: Mapping[str, Any]) -> Mapping[str, Any] | None:
    channels = snapshot.get("channels")
    if not isinstance(channels, Mapping):
        return None
    channel_config = channels.get("imessage")
    return channel_config if isinstance(channel_config, Mapping) else None


def resolve_imessage_account_config(
    snapshot: Mapping[str, Any],
    account_id: str | None,
) -> dict[str, Any] | None:
    channel_config = _imessage_channel_config(snapshot)
    if channel_config is None:
        return None
    normalized_account_id = _normalized_config_account_id(account_id)
    merged = {
        str(key): value
        for key, value in channel_config.items()
        if str(key) != "accounts"
    }
    if normalized_account_id != DEFAULT_ACCOUNT_ID:
        accounts = channel_config.get("accounts")
        if not isinstance(accounts, Mapping):
            return None
        account_config = accounts.get(normalized_account_id)
        if not isinstance(account_config, Mapping):
            return None
        merged.update({str(key): value for key, value in account_config.items()})
    return merged


def configured_imessage_account_summaries(
    snapshot: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    channel_config = _imessage_channel_config(snapshot)
    if channel_config is None:
        return {}
    account_ids: set[str] = set()
    base_config = resolve_imessage_account_config(snapshot, DEFAULT_ACCOUNT_ID)
    if base_config is not None and imessage_account_configured(base_config):
        account_ids.add(DEFAULT_ACCOUNT_ID)
    accounts = channel_config.get("accounts")
    if isinstance(accounts, Mapping):
        account_ids.update(str(account_id) for account_id in accounts if str(account_id).strip())
    summaries: dict[str, dict[str, Any]] = {}
    for account_id in sorted(account_ids):
        account_config = resolve_imessage_account_config(snapshot, account_id)
        if account_config is None:
            continue
        enabled = channel_config.get("enabled") is not False and account_config.get(
            "enabled"
        ) is not False
        if not enabled:
            continue
        summary = _new_channel_account_summary(account_id)
        summary.update(
            {
                "configured": imessage_account_configured(account_config),
                "enabled": enabled,
                "source": "config",
            }
        )
        name = _config_string(account_config.get("name"))
        if name is not None:
            summary["name"] = name
        cli_path = _config_string(account_config.get("cliPath"))
        if cli_path is not None:
            summary["cliPath"] = cli_path
        db_path = _config_string(account_config.get("dbPath"))
        if db_path is not None:
            summary["dbPath"] = db_path
        summaries[account_id] = summary
    return summaries


class GatewayChannelAccountProbe(Protocol):
    async def __call__(
        self,
        *,
        channel: str,
        account_id: str,
        timeout_ms: int,
    ) -> dict[str, Any]:
        ...


class GatewayChannelTargetResolver(Protocol):
    async def __call__(
        self,
        *,
        channel: str | None,
        account_id: str | None,
        kind: str,
        inputs: list[str],
    ) -> list[dict[str, Any]]:
        ...


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
        probe_account: GatewayChannelAccountProbe | None = None,
        resolve_targets: GatewayChannelTargetResolver | None = None,
        config_snapshot: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self._list_notification_route_views = list_notification_route_views
        self._probe_account = probe_account
        self._resolve_targets = resolve_targets
        self._config_snapshot = config_snapshot

    async def build_snapshot(
        self,
        *,
        probe: bool | None = None,
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        routes = await self._list_notification_route_views()
        route_payloads = [route.model_dump(mode="json") for route in routes]
        resolved_timeout_ms = (
            timeout_ms if timeout_ms is not None else 30_000 if probe else 10_000
        )

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

        if self._config_snapshot is not None:
            try:
                config_snapshot = self._config_snapshot()
            except Exception:  # pragma: no cover - defensive adapter boundary
                config_snapshot = {}
            imessage_accounts = configured_imessage_account_summaries(config_snapshot)
            if imessage_accounts:
                channel_id = "imessage"
                summary = channel_summaries[channel_id]
                accounts_for_channel = account_summaries[channel_id]
                for account_id, account_summary in imessage_accounts.items():
                    existing = accounts_for_channel.get(account_id)
                    if existing is None:
                        accounts_for_channel[account_id] = account_summary
                    else:
                        existing.update(
                            {
                                key: value
                                for key, value in account_summary.items()
                                if key not in {"routeCount", "enabledRouteCount"}
                            }
                        )
                summary["configuredAccountCount"] = len(imessage_accounts)

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

        payload: dict[str, Any] = {
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
        if probe is not None:
            payload["probe"] = bool(probe)
            payload["timeoutMs"] = resolved_timeout_ms
        if probe:
            payload["probeStatus"] = await self._probe_channel_accounts(
                channel_accounts_payload,
                timeout_ms=resolved_timeout_ms,
            )
        return payload

    async def _probe_channel_accounts(
        self,
        channel_accounts_payload: dict[str, list[dict[str, Any]]],
        *,
        timeout_ms: int,
    ) -> dict[str, Any]:
        if self._probe_account is None:
            unavailable = _unavailable_probe_payload(timeout_ms)
            for accounts in channel_accounts_payload.values():
                for account in accounts:
                    account["probe"] = dict(unavailable)
            return {
                "status": "unavailable",
                "reason": "native_probe_runtime_unavailable",
                "summary": "Native provider credential probes are not available yet.",
                "timeoutMs": timeout_ms,
            }

        all_ok = True
        probed_account_count = 0
        for channel_id, accounts in channel_accounts_payload.items():
            for account in accounts:
                probed_account_count += 1
                account_id = str(account.get("accountId") or "").strip() or DEFAULT_ACCOUNT_ID
                try:
                    probe_result = await self._probe_account(
                        channel=channel_id,
                        account_id=account_id,
                        timeout_ms=timeout_ms,
                    )
                except Exception as exc:  # pragma: no cover - defensive adapter boundary
                    probe_result = {
                        "ok": False,
                        "error": str(exc),
                        "timeoutMs": timeout_ms,
                    }
                if probe_result.get("ok") is False:
                    all_ok = False
                account["probe"] = dict(probe_result)
        if probed_account_count == 0:
            return {
                "status": "unavailable",
                "reason": "native_provider_route_unavailable",
                "summary": "No configured channel accounts are available to probe.",
                "timeoutMs": timeout_ms,
            }
        return {
            "status": "ok" if all_ok else "degraded",
            "timeoutMs": timeout_ms,
        }

    async def resolve_targets(
        self,
        *,
        channel: str | None,
        account_id: str | None,
        kind: str,
        inputs: list[str],
    ) -> list[dict[str, Any]]:
        if not inputs:
            return []
        if self._resolve_targets is None:
            return [_unresolved_target_payload(input_value) for input_value in inputs]
        try:
            return await self._resolve_targets(
                channel=channel,
                account_id=account_id,
                kind=kind,
                inputs=inputs,
            )
        except Exception as exc:  # pragma: no cover - defensive adapter boundary
            return [
                _unresolved_target_payload(input_value, error=str(exc))
                for input_value in inputs
            ]


def _unavailable_probe_payload(timeout_ms: int) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "unavailable",
        "reason": "native_probe_runtime_unavailable",
        "summary": "Native provider credential probes are not available yet.",
        "timeoutMs": timeout_ms,
    }


def _unresolved_target_payload(input_value: str, *, error: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "input": input_value,
        "resolved": False,
        "note": "native provider resolver unavailable",
    }
    if error:
        payload["error"] = error
    return payload
