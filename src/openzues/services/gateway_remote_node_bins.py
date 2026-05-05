from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Sequence

from openzues.services.gateway_node_pairing import GatewayNodePairingService
from openzues.services.gateway_node_registry import GatewayNodeRegistry
from openzues.services.gateway_skill_bins import GatewaySkillBinsService

_REMOTE_BIN_PROBE_TIMEOUT_MS = 15_000
_REMOTE_BIN_STDOUT_SPLIT_RE = re.compile(r"\r?\n")


def _is_macos_platform(platform: str | None, device_family: str | None) -> bool:
    platform_norm = str(platform or "").strip().lower()
    family_norm = str(device_family or "").strip().lower()
    return "darwin" in platform_norm or "mac" in platform_norm or family_norm == "mac"


def _supports_command(commands: Sequence[str] | None, command: str) -> bool:
    if commands is None:
        return False
    return command in {entry.strip() for entry in commands if isinstance(entry, str)}


def _normalize_bins(values: object) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        trimmed = value.strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        normalized.append(trimmed)
    return normalized


def _single_quote_shell(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _build_bin_probe_script(bins: Sequence[str]) -> str:
    escaped = " ".join(_single_quote_shell(bin_name) for bin_name in bins)
    return (
        f"for b in {escaped}; do "
        'if command -v "$b" >/dev/null 2>&1; then echo "$b"; fi; '
        "done"
    )


def _parse_bin_probe_payload(
    *,
    payload_json: str | None,
    payload: object | None,
) -> list[str]:
    parsed: object | None = None
    if payload_json:
        try:
            parsed = json.loads(payload_json)
        except json.JSONDecodeError:
            return []
    elif payload is not None:
        parsed = payload
    if not isinstance(parsed, dict):
        return []

    bins = parsed.get("bins")
    if isinstance(bins, list):
        return _normalize_bins(bins)
    if isinstance(bins, dict):
        found: list[str] = []
        for bin_name, resolved_path in bins.items():
            if not isinstance(bin_name, str):
                continue
            if not str(resolved_path or "").strip():
                continue
            found.append(bin_name)
        return _normalize_bins(found)

    stdout = parsed.get("stdout")
    if isinstance(stdout, str):
        return _normalize_bins(_REMOTE_BIN_STDOUT_SPLIT_RE.split(stdout))
    return []


class GatewayRemoteNodeBinsService:
    def __init__(
        self,
        registry: GatewayNodeRegistry,
        *,
        pairing_service: GatewayNodePairingService,
        skill_bins_service: GatewaySkillBinsService | None = None,
        timeout_ms: int = _REMOTE_BIN_PROBE_TIMEOUT_MS,
    ) -> None:
        self.registry = registry
        self.pairing_service = pairing_service
        self.skill_bins_service = skill_bins_service or GatewaySkillBinsService()
        self.timeout_ms = timeout_ms
        self._inflight: dict[str, asyncio.Task[dict[str, object]]] = {}

    async def refresh_for_node(
        self,
        *,
        node_id: str,
        platform: str | None,
        device_family: str | None = None,
        commands: Sequence[str] | None = None,
    ) -> dict[str, object]:
        normalized_node_id = node_id.strip()
        if not normalized_node_id:
            return {"ok": False, "status": "skipped", "reason": "missing_node_id"}
        if not _is_macos_platform(platform, device_family):
            return {"ok": True, "status": "skipped", "reason": "non_macos"}
        can_which = _supports_command(commands, "system.which")
        can_run = _supports_command(commands, "system.run")
        if not can_which and not can_run:
            return {"ok": True, "status": "skipped", "reason": "unsupported_command"}
        if self.registry.get(normalized_node_id) is None:
            return {"ok": True, "status": "skipped", "reason": "not_connected"}

        existing = self._inflight.get(normalized_node_id)
        if existing is not None:
            return await existing

        task = asyncio.create_task(
            self._refresh_for_node_uncoalesced(
                node_id=normalized_node_id,
                can_which=can_which,
            )
        )
        self._inflight[normalized_node_id] = task
        try:
            return await task
        finally:
            if self._inflight.get(normalized_node_id) is task:
                self._inflight.pop(normalized_node_id, None)

    async def _refresh_for_node_uncoalesced(
        self,
        *,
        node_id: str,
        can_which: bool,
    ) -> dict[str, object]:
        required_bins = self.skill_bins_service.list_bins(platform="darwin")
        if not required_bins:
            return {"ok": True, "status": "skipped", "reason": "no_required_bins"}
        command = "system.which" if can_which else "system.run"
        params: object
        if can_which:
            params = {"bins": required_bins}
        else:
            params = {"command": ["/bin/sh", "-lc", _build_bin_probe_script(required_bins)]}
        result = await self.registry.invoke(
            node_id=node_id,
            command=command,
            params=params,
            timeout_ms=self.timeout_ms,
        )
        if not result.ok:
            await self.pairing_service.update_paired_node_metadata(node_id, bins=[])
            return {
                "ok": False,
                "status": "failed",
                "command": command,
                "error": result.error or {},
            }
        bins = _parse_bin_probe_payload(
            payload_json=result.payload_json,
            payload=result.payload,
        )
        await self.pairing_service.update_paired_node_metadata(node_id, bins=bins)
        return {
            "ok": True,
            "status": "refreshed",
            "command": command,
            "bins": bins,
        }
