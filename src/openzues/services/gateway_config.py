from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from openzues.schemas import ControlUiBootstrapConfigView


def _escape_powershell_single_quoted_string(value: str) -> str:
    return value.replace("'", "''")


def resolve_gateway_config_open_command(
    path: Path,
    *,
    platform: str | None = None,
) -> tuple[str, list[str]]:
    normalized_platform = platform or sys.platform
    if normalized_platform.startswith("win"):
        target = str(path)
        return (
            "powershell.exe",
            [
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                (
                    "Start-Process -LiteralPath "
                    f"'{_escape_powershell_single_quoted_string(target)}'"
                ),
            ],
        )
    target = path.as_posix()
    if normalized_platform == "darwin":
        return ("open", [target])
    return ("xdg-open", [target])


def _open_gateway_config_path(path: Path) -> None:
    command, args = resolve_gateway_config_open_command(path)
    subprocess.run(  # noqa: S603
        [command, *args],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class GatewayConfigService:
    def __init__(
        self,
        *,
        assistant_name: str,
        assistant_avatar: str,
        assistant_agent_id: str,
        server_version: str | None,
        base_path: str = "",
        local_media_preview_roots: list[str] | None = None,
        embed_sandbox: str = "scripts",
        allow_external_embed_urls: bool = False,
        data_dir: Path | None = None,
        open_path: Callable[[Path], None] | None = None,
    ) -> None:
        self._assistant_name = assistant_name
        self._assistant_avatar = assistant_avatar
        self._assistant_agent_id = assistant_agent_id
        self._server_version = server_version
        self._base_path = base_path
        self._local_media_preview_roots = list(local_media_preview_roots or [])
        self._embed_sandbox = embed_sandbox
        self._allow_external_embed_urls = allow_external_embed_urls
        self._config_path = data_dir / "settings" / "control-ui-config.json" if data_dir else None
        self._open_path = open_path or _open_gateway_config_path

    def build_snapshot(self) -> dict[str, Any]:
        if self._config_path is not None and self._config_path.exists():
            try:
                persisted = json.loads(self._config_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                persisted = None
            if isinstance(persisted, dict):
                return self._validated_snapshot(persisted)
        return self._default_snapshot()

    def set_raw(self, raw: str, *, base_hash: str | None = None) -> dict[str, Any]:
        self._require_config_path()
        parsed = self._parse_raw_object(raw, label="config.set")
        next_snapshot = self._validated_snapshot(parsed)
        return self._write_snapshot(next_snapshot, base_hash=base_hash)

    def patch_raw(self, raw: str, *, base_hash: str | None = None) -> dict[str, Any]:
        self._require_config_path()
        patch = self._parse_raw_object(raw, label="config.patch")
        current = self.build_snapshot()
        next_snapshot = self._validated_snapshot(_merge_config_patch(current, patch))
        return self._write_snapshot(next_snapshot, base_hash=base_hash)

    def apply_raw(self, raw: str, *, base_hash: str | None = None) -> dict[str, Any]:
        result = self.set_raw(raw, base_hash=base_hash)
        result["restart"] = None
        result["sentinel"] = None
        return result

    def _default_snapshot(self) -> dict[str, Any]:
        return ControlUiBootstrapConfigView.model_validate(
            {
                "basePath": self._base_path,
                "assistantName": self._assistant_name,
                "assistantAvatar": self._assistant_avatar,
                "assistantAgentId": self._assistant_agent_id,
                "serverVersion": self._server_version,
                "localMediaPreviewRoots": self._local_media_preview_roots,
                "embedSandbox": self._embed_sandbox,
                "allowExternalEmbedUrls": self._allow_external_embed_urls,
            }
        ).model_dump(mode="json", by_alias=True)

    def _validated_snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        return ControlUiBootstrapConfigView.model_validate(payload).model_dump(
            mode="json",
            by_alias=True,
        )

    def _require_config_path(self) -> Path:
        if self._config_path is None:
            raise RuntimeError("config file path unavailable")
        return self._config_path

    def _parse_raw_object(self, raw: str, *, label: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
        except ValueError as exc:
            raise ValueError(f"{label} raw must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{label} raw must be an object")
        return parsed

    def _write_snapshot(self, snapshot: dict[str, Any], *, base_hash: str | None) -> dict[str, Any]:
        config_path = self._require_config_path()
        if config_path.exists():
            current_hash = self._snapshot_hash(self.build_snapshot())
            if not base_hash:
                raise ValueError("config base hash required; re-run config.get and retry")
            if base_hash != current_hash:
                raise ValueError("config changed since last load; re-run config.get and retry")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "ok": True,
            "path": str(config_path),
            "config": snapshot,
            "hash": self._snapshot_hash(snapshot),
        }

    def _snapshot_hash(self, snapshot: dict[str, Any]) -> str:
        encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

    def can_open_file(self) -> bool:
        return self._config_path is not None

    def open_file(self) -> dict[str, Any]:
        if self._config_path is None:
            raise RuntimeError("config file path unavailable")
        snapshot = self.build_snapshot()
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            self._open_path(self._config_path)
        except Exception:
            return {
                "ok": False,
                "path": str(self._config_path),
                "error": "failed to open config file",
            }
        return {"ok": True, "path": str(self._config_path)}


def _merge_config_patch(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_config_patch(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged
