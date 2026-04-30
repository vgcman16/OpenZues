from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openzues.schemas import ControlUiBootstrapConfigView

_OPENCLAW_DEFAULT_GATEWAY_PORT = 18789
_SHELL_METACHARS_PATTERN = re.compile(r"[;&|`$<>]")
_EXEC_CONTROL_CHARS_PATTERN = re.compile(r"[\r\n]")
_EXEC_QUOTE_CHARS_PATTERN = re.compile(r"['\"]")
_EXEC_BARE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._+-]+$")
_EXEC_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")
_AGENT_HEARTBEAT_KEYS = {
    "every",
    "activeHours",
    "model",
    "session",
    "includeReasoning",
    "target",
    "directPolicy",
    "to",
    "accountId",
    "prompt",
    "ackMaxChars",
    "suppressToolErrorWarnings",
    "lightContext",
    "isolatedSession",
}
_CHANNEL_HEARTBEAT_KEYS = {"showOk", "showAlerts", "useIndicator"}
_LEGACY_TTS_PROVIDER_KEYS = ("openai", "elevenlabs", "microsoft", "edge")
_LEGACY_TTS_PROVIDER_TARGETS = {
    "openai": "openai",
    "elevenlabs": "elevenlabs",
    "microsoft": "microsoft",
    "edge": "microsoft",
}
_LEGACY_TTS_PLUGIN_IDS = {"voice-call"}
_LEGACY_WEB_SEARCH_GLOBAL_PROVIDER_ID = "brave"
_LEGACY_WEB_SEARCH_MODERN_SCOPED_KEYS = {"openaiCodex"}
_LEGACY_WEB_SEARCH_PROVIDER_PLUGIN_IDS = {
    "brave": "brave",
    "duckduckgo": "duckduckgo",
    "exa": "exa",
    "firecrawl": "firecrawl",
    "gemini": "google",
    "grok": "xai",
    "kimi": "moonshot",
    "minimax": "minimax",
    "ollama": "ollama",
    "perplexity": "perplexity",
    "searxng": "searxng",
}
_LEGACY_WEB_SEARCH_PROVIDER_IDS = tuple(sorted(_LEGACY_WEB_SEARCH_PROVIDER_PLUGIN_IDS))
_OPENCLAW_CHANNEL_PLUGIN_ALIASES = {
    "discord": "discord",
    "feishu": "feishu",
    "gchat": "googlechat",
    "google-chat": "googlechat",
    "googlechat": "googlechat",
    "imessage": "imessage",
    "imsg": "imessage",
    "internet-relay-chat": "irc",
    "irc": "irc",
    "line": "line",
    "matrix": "matrix",
    "msteams": "msteams",
    "nextcloud-talk": "nextcloud-talk",
    "nostr": "nostr",
    "signal": "signal",
    "slack": "slack",
    "teams": "msteams",
    "telegram": "telegram",
    "tg": "telegram",
    "wa": "whatsapp",
    "whatsapp": "whatsapp",
    "zalo": "zalo",
    "zulip": "zulip",
}
_MODEL_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")
_DEFAULT_MODEL_PROVIDER = "openai"
_DEFAULT_AGENT_ID = "main"
_AGENT_ID_VALID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.IGNORECASE)
_AGENT_ID_INVALID_CHARS_PATTERN = re.compile(r"[^a-z0-9_-]+")
_PROVIDER_ID_ALIASES = {
    "aws-bedrock": "amazon-bedrock",
    "bedrock": "amazon-bedrock",
    "bytedance": "volcengine",
    "doubao": "volcengine",
    "kimi-code": "kimi",
    "kimi-coding": "kimi",
    "modelstudio": "qwen",
    "opencode-go-auth": "opencode-go",
    "opencode-zen": "opencode",
    "qwencloud": "qwen",
    "z.ai": "zai",
    "z-ai": "zai",
}


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
        self._data_dir = data_dir
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
        config_path = self._require_config_path()
        patch = self._parse_raw_object(raw, label="config.patch")
        current = self.build_snapshot()
        next_snapshot = self._validated_snapshot(_merge_config_patch(current, patch))
        if next_snapshot == current:
            current_hash = self._snapshot_hash(current)
            if config_path.exists():
                if not base_hash:
                    raise ValueError("config base hash required; re-run config.get and retry")
                if base_hash != current_hash:
                    raise ValueError("config changed since last load; re-run config.get and retry")
            return {
                "ok": True,
                "noop": True,
                "path": str(config_path),
                "config": current,
                "hash": current_hash,
            }
        return self._write_snapshot(next_snapshot, base_hash=base_hash)

    def apply_raw(self, raw: str, *, base_hash: str | None = None) -> dict[str, Any]:
        result = self.set_raw(raw, base_hash=base_hash)
        result["restart"] = None
        result["sentinel"] = None
        return result

    def detect_legacy_thread_binding_ttl_hours(self) -> dict[str, Any]:
        config_path = self._require_config_path()
        if not config_path.exists():
            return {"ok": True, "path": str(config_path), "issues": []}
        payload = self._read_raw_config_object(label="legacy thread binding config detection")
        return {
            "ok": True,
            "path": str(config_path),
            "issues": [
                _legacy_thread_binding_ttl_hour_issue(path)
                for path in _iter_legacy_thread_binding_ttl_hour_paths(payload)
            ],
        }

    def detect_legacy_config_issues(self) -> dict[str, Any]:
        config_path = self._require_config_path()
        if not config_path.exists():
            return {"ok": True, "path": str(config_path), "issues": []}
        payload = self._read_raw_config_object(label="legacy config detection")
        return {
            "ok": True,
            "path": str(config_path),
            "issues": _collect_legacy_config_issues(payload),
        }

    def repair_legacy_thread_binding_ttl_hours(self) -> dict[str, Any]:
        config_path = self._require_config_path()
        if not config_path.exists():
            return {
                "ok": True,
                "path": str(config_path),
                "changed": False,
                "changes": [],
                "config": self._default_snapshot(),
                "hash": self._snapshot_hash(self._default_snapshot()),
            }
        payload = self._read_raw_config_object(label="legacy thread binding config repair")
        changes = _migrate_legacy_thread_binding_ttl_hours(payload)
        if not changes:
            snapshot = self.build_snapshot()
            return {
                "ok": True,
                "path": str(config_path),
                "changed": False,
                "changes": [],
                "config": snapshot,
                "hash": self._snapshot_hash(snapshot),
            }
        snapshot = self._validated_snapshot(payload)
        config_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "ok": True,
            "path": str(config_path),
            "changed": True,
            "changes": changes,
            "config": snapshot,
            "hash": self._snapshot_hash(snapshot),
        }

    def repair_legacy_config(self) -> dict[str, Any]:
        config_path = self._require_config_path()
        if not config_path.exists():
            snapshot = self._default_snapshot()
            return {
                "ok": True,
                "path": str(config_path),
                "changed": False,
                "changes": [],
                "config": snapshot,
                "hash": self._snapshot_hash(snapshot),
            }
        payload = self._read_raw_config_object(label="legacy config repair")
        changes = [
            *_migrate_legacy_thread_binding_ttl_hours(payload),
            *_migrate_legacy_channel_allow_aliases(payload),
            *_migrate_legacy_x_search_api_key(payload),
            *_migrate_legacy_web_search_provider_config(payload),
            *_migrate_legacy_telegram_streaming_keys(payload),
            *_migrate_legacy_slack_streaming_keys(payload),
            *_migrate_legacy_googlechat_stream_mode(payload),
            *_migrate_legacy_audio_transcription(payload),
            *_migrate_legacy_sandbox_per_session(payload),
            *_migrate_legacy_memory_search(payload),
            *_migrate_legacy_heartbeat(payload),
            *_migrate_legacy_tts_provider_config(payload),
            *_migrate_gateway_control_ui_allowed_origins(payload),
            *_migrate_legacy_gateway_bind_alias(payload),
        ]
        if not changes:
            snapshot = self.build_snapshot()
            return {
                "ok": True,
                "path": str(config_path),
                "changed": False,
                "changes": [],
                "config": snapshot,
                "hash": self._snapshot_hash(snapshot),
            }
        snapshot = self._validated_snapshot(payload)
        config_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "ok": True,
            "path": str(config_path),
            "changed": True,
            "changes": changes,
            "config": snapshot,
            "hash": self._snapshot_hash(snapshot),
        }

    def set_plugin_enabled(self, plugin_id: str, enabled: bool) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        toggle = _set_plugin_enabled_in_snapshot(current, plugin_id, enabled)
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(toggle["config"], base_hash=base_hash)
        write_result.update(
            {
                "pluginId": toggle["pluginId"],
                "resolvedPluginId": toggle["resolvedPluginId"],
                "enabled": toggle["enabled"],
                "requestedEnabled": enabled,
                "reason": toggle["reason"],
                "channelSynced": toggle["channelSynced"],
            }
        )
        return write_result

    def set_default_model(self, model_ref: str) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        target = _resolve_model_alias_target(
            model_ref,
            aliases=_model_aliases_from_config_snapshot(current),
        )
        next_snapshot = _set_model_primary_in_snapshot(current, target=target)
        next_snapshot = _ensure_model_config_entry_in_snapshot(next_snapshot, target=target)
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        write_result.update({"target": target, "field": "model"})
        return write_result

    def set_default_image_model(self, model_ref: str) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        target = _resolve_model_alias_target(
            model_ref,
            aliases=_model_aliases_from_config_snapshot(current),
        )
        next_snapshot = _set_model_primary_in_snapshot(
            current,
            target=target,
            key="imageModel",
        )
        next_snapshot = _ensure_model_config_entry_in_snapshot(next_snapshot, target=target)
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        write_result.update({"target": target, "field": "imageModel"})
        return write_result

    def set_model_alias(self, *, alias: str, model_ref: str) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        alias_value = _normalize_model_alias(alias)
        target = _resolve_model_alias_target(
            model_ref,
            aliases=_model_aliases_from_config_snapshot(current),
        )
        next_snapshot = _set_model_alias_in_snapshot(
            current,
            alias=alias_value,
            target=target,
        )
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        write_result.update({"alias": alias_value, "target": target})
        return write_result

    def remove_model_alias(self, alias: str) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        alias_value = _normalize_model_alias(alias)
        next_snapshot = _remove_model_alias_in_snapshot(current, alias=alias_value)
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        remaining_aliases = _model_aliases_from_config_snapshot(next_snapshot)
        write_result.update(
            {
                "alias": alias_value,
                "aliasesRemaining": len(remaining_aliases),
            }
        )
        return write_result

    def add_model_fallback(self, model_ref: str) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        aliases = _model_aliases_from_config_snapshot(current)
        target = _resolve_model_alias_target(model_ref, aliases=aliases)
        existing = _model_fallbacks_from_config_snapshot(current)
        existing_targets = {
            resolved
            for fallback in existing
            for resolved in (_try_resolve_model_alias_target(fallback, aliases=aliases),)
            if resolved is not None
        }
        fallbacks = existing if target in existing_targets else [*existing, target]
        next_snapshot = _set_model_fallbacks_in_snapshot(current, fallbacks=fallbacks)
        next_snapshot = _ensure_model_config_entry_in_snapshot(next_snapshot, target=target)
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        write_result.update({"target": target, "fallbacks": fallbacks})
        return write_result

    def add_image_model_fallback(self, model_ref: str) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        aliases = _model_aliases_from_config_snapshot(current)
        target = _resolve_model_alias_target(model_ref, aliases=aliases)
        existing = _model_fallbacks_from_config_snapshot(current, key="imageModel")
        existing_targets = {
            resolved
            for fallback in existing
            for resolved in (_try_resolve_model_alias_target(fallback, aliases=aliases),)
            if resolved is not None
        }
        fallbacks = existing if target in existing_targets else [*existing, target]
        next_snapshot = _set_model_fallbacks_in_snapshot(
            current,
            fallbacks=fallbacks,
            key="imageModel",
        )
        next_snapshot = _ensure_model_config_entry_in_snapshot(next_snapshot, target=target)
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        write_result.update({"target": target, "fallbacks": fallbacks})
        return write_result

    def remove_model_fallback(self, model_ref: str) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        aliases = _model_aliases_from_config_snapshot(current)
        target = _resolve_model_alias_target(model_ref, aliases=aliases)
        existing = _model_fallbacks_from_config_snapshot(current)
        fallbacks = [
            fallback
            for fallback in existing
            if _try_resolve_model_alias_target(fallback, aliases=aliases) != target
        ]
        if len(fallbacks) == len(existing):
            raise ValueError(f"Fallback not found: {target}")
        next_snapshot = _set_model_fallbacks_in_snapshot(current, fallbacks=fallbacks)
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        write_result.update({"target": target, "fallbacks": fallbacks})
        return write_result

    def remove_image_model_fallback(self, model_ref: str) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        aliases = _model_aliases_from_config_snapshot(current)
        target = _resolve_model_alias_target(model_ref, aliases=aliases)
        existing = _model_fallbacks_from_config_snapshot(current, key="imageModel")
        fallbacks = [
            fallback
            for fallback in existing
            if _try_resolve_model_alias_target(fallback, aliases=aliases) != target
        ]
        if len(fallbacks) == len(existing):
            raise ValueError(f"Image fallback not found: {target}")
        next_snapshot = _set_model_fallbacks_in_snapshot(
            current,
            fallbacks=fallbacks,
            key="imageModel",
        )
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        write_result.update({"target": target, "fallbacks": fallbacks})
        return write_result

    def clear_model_fallbacks(self) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        next_snapshot = _set_model_fallbacks_in_snapshot(current, fallbacks=[])
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        write_result.update({"fallbacks": []})
        return write_result

    def clear_image_model_fallbacks(self) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        next_snapshot = _set_model_fallbacks_in_snapshot(
            current,
            fallbacks=[],
            key="imageModel",
        )
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        write_result.update({"fallbacks": []})
        return write_result

    def apply_model_scan_selection(
        self,
        *,
        selected: list[str],
        selected_images: list[str],
        set_default: bool = False,
        set_image: bool = False,
    ) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        aliases = _model_aliases_from_config_snapshot(current)
        text_targets = [
            _resolve_model_alias_target(model_ref, aliases=aliases)
            for model_ref in selected
        ]
        image_targets = [
            _resolve_model_alias_target(model_ref, aliases=aliases)
            for model_ref in selected_images
        ]
        next_snapshot = _set_model_fallbacks_in_snapshot(current, fallbacks=text_targets)
        if set_default and text_targets:
            next_snapshot = _set_model_primary_in_snapshot(next_snapshot, target=text_targets[0])
        if image_targets:
            next_snapshot = _set_model_fallbacks_in_snapshot(
                next_snapshot,
                fallbacks=image_targets,
                key="imageModel",
            )
            if set_image:
                next_snapshot = _set_model_primary_in_snapshot(
                    next_snapshot,
                    target=image_targets[0],
                    key="imageModel",
                )
        for target in [*text_targets, *image_targets]:
            next_snapshot = _ensure_model_config_entry_in_snapshot(
                next_snapshot,
                target=target,
            )
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(next_snapshot, base_hash=base_hash)
        write_result.update(
            {
                "selected": text_targets,
                "selectedImages": image_targets,
                "setDefault": set_default,
                "setImage": set_image,
            }
        )
        return write_result

    def get_model_auth_order(
        self,
        *,
        provider: str,
        agent: str | None = None,
    ) -> dict[str, Any]:
        context = _resolve_model_auth_order_context(
            self.build_snapshot(),
            data_dir=self._require_data_dir(),
            provider=provider,
            agent=agent,
        )
        state = _read_json_object(context["auth_state_path"])
        order = _auth_order_from_state(state, provider=context["provider"])
        return {
            "agentId": context["agent_id"],
            "agentDir": str(context["agent_dir"]),
            "provider": context["provider"],
            "authStatePath": str(context["auth_state_path"]),
            "order": order if order else None,
        }

    def set_model_auth_order(
        self,
        *,
        provider: str,
        order: list[str],
        agent: str | None = None,
    ) -> dict[str, Any]:
        context = _resolve_model_auth_order_context(
            self.build_snapshot(),
            data_dir=self._require_data_dir(),
            provider=provider,
            agent=agent,
        )
        requested = _normalize_string_entries(order)
        if not requested:
            raise ValueError("Missing profile ids. Provide one or more profile ids.")
        profiles = _auth_profiles_from_store(_read_json_object(context["auth_store_path"]))
        for profile_id in requested:
            credential = profiles.get(profile_id)
            if not isinstance(credential, dict):
                agent_dir = context["agent_dir"]
                raise ValueError(f'Auth profile "{profile_id}" not found in {agent_dir}.')
            credential_provider = str(credential.get("provider") or "")
            if _normalize_model_auth_provider(credential_provider) != context["provider"]:
                raise ValueError(
                    f'Auth profile "{profile_id}" is for {credential_provider}, '
                    f'not {context["provider"]}.'
                )
        state = _read_json_object(context["auth_state_path"])
        next_state = _set_auth_order_in_state(
            state,
            provider=context["provider"],
            order=requested,
        )
        _write_json_object(context["auth_state_path"], next_state)
        return {
            "agentId": context["agent_id"],
            "agentDir": str(context["agent_dir"]),
            "provider": context["provider"],
            "authStatePath": str(context["auth_state_path"]),
            "order": requested,
        }

    def clear_model_auth_order(
        self,
        *,
        provider: str,
        agent: str | None = None,
    ) -> dict[str, Any]:
        context = _resolve_model_auth_order_context(
            self.build_snapshot(),
            data_dir=self._require_data_dir(),
            provider=provider,
            agent=agent,
        )
        state = _read_json_object(context["auth_state_path"])
        next_state = _clear_auth_order_in_state(state, provider=context["provider"])
        _write_or_remove_auth_state(context["auth_state_path"], next_state)
        return {
            "agentId": context["agent_id"],
            "agentDir": str(context["agent_dir"]),
            "provider": context["provider"],
            "authStatePath": str(context["auth_state_path"]),
            "order": None,
        }

    def record_marketplace_plugin_install(
        self,
        *,
        plugin_id: str,
        install_path: str,
        marketplace_source: str,
        marketplace_plugin: str,
        marketplace_name: str | None = None,
        version: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        record = _record_marketplace_plugin_install_in_snapshot(
            current,
            plugin_id=plugin_id,
            install_path=install_path,
            marketplace_source=marketplace_source,
            marketplace_plugin=marketplace_plugin,
            marketplace_name=marketplace_name,
            version=version,
            force=force,
        )
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(record["config"], base_hash=base_hash)
        write_result.update(
            {
                "pluginId": record["pluginId"],
                "install": record["install"],
                "loadPath": record["loadPath"],
                "enabled": True,
                "restart": "gateway",
            }
        )
        return write_result

    def preview_plugin_uninstall(self, plugin_id: str) -> dict[str, Any]:
        current = self.build_snapshot()
        result = _uninstall_plugin_in_snapshot(current, plugin_id=plugin_id)
        return {
            "ok": True,
            "pluginId": result["pluginId"],
            "actions": result["actions"],
            "warnings": result["warnings"],
            "restart": "gateway",
        }

    def uninstall_plugin(self, plugin_id: str) -> dict[str, Any]:
        config_path = self._require_config_path()
        current = self.build_snapshot()
        result = _uninstall_plugin_in_snapshot(current, plugin_id=plugin_id)
        base_hash = self._snapshot_hash(current) if config_path.exists() else None
        write_result = self._write_snapshot(result["config"], base_hash=base_hash)
        write_result.update(
            {
                "pluginId": result["pluginId"],
                "actions": result["actions"],
                "warnings": result["warnings"],
                "restart": "gateway",
            }
        )
        return write_result

    def _default_snapshot(self) -> dict[str, Any]:
        return _clean_config_snapshot(
            ControlUiBootstrapConfigView.model_validate(
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
        )

    def _validated_snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        _reject_legacy_thread_binding_ttl_hours(payload)
        return _clean_config_snapshot(
            ControlUiBootstrapConfigView.model_validate(payload).model_dump(
                mode="json",
                by_alias=True,
            )
        )

    def _require_config_path(self) -> Path:
        if self._config_path is None:
            raise RuntimeError("config file path unavailable")
        return self._config_path

    def _require_data_dir(self) -> Path:
        if self._data_dir is None:
            raise ValueError("model auth order config runtime is unavailable.")
        return self._data_dir

    def _parse_raw_object(self, raw: str, *, label: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
        except ValueError as exc:
            raise ValueError(f"{label} raw must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{label} raw must be an object")
        return parsed

    def _read_raw_config_object(self, *, label: str) -> dict[str, Any]:
        config_path = self._require_config_path()
        try:
            raw = config_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"{label} could not read config file") from exc
        return self._parse_raw_object(raw, label=label)

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


def _normalize_model_alias(alias: str) -> str:
    normalized = alias.strip()
    if not normalized:
        raise ValueError("Alias cannot be empty.")
    if _MODEL_ALIAS_PATTERN.fullmatch(normalized) is None:
        raise ValueError("Alias must use letters, numbers, dots, underscores, colons, or dashes.")
    return normalized


def _resolve_model_alias_target(raw: str, *, aliases: dict[str, str]) -> str:
    normalized = raw.strip()
    if not normalized:
        raise ValueError(f"Invalid model reference: {raw}")
    alias_target = aliases.get(normalized)
    if alias_target:
        return alias_target
    if "/" in normalized:
        provider, model = normalized.split("/", 1)
    else:
        provider, model = _DEFAULT_MODEL_PROVIDER, normalized
    provider = _normalize_model_provider_id(provider)
    model = _normalize_model_id_for_provider(provider, model)
    if not provider or not model:
        raise ValueError(f"Invalid model reference: {raw}")
    return _model_config_key(provider, model)


def _try_resolve_model_alias_target(raw: str, *, aliases: dict[str, str]) -> str | None:
    try:
        return _resolve_model_alias_target(raw, aliases=aliases)
    except ValueError:
        return None


def _normalize_model_auth_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if not normalized:
        raise ValueError("Missing --provider.")
    return _normalize_model_provider_id(normalized)


def _normalize_model_provider_id(provider: str) -> str:
    normalized = provider.strip().lower()
    return _PROVIDER_ID_ALIASES.get(normalized, normalized)


def _normalize_model_id_for_provider(provider: str, model: str) -> str:
    trimmed = model.strip()
    if provider == "anthropic":
        anthropic_aliases = {
            "opus-4.6": "claude-opus-4-6",
            "opus-4.5": "claude-opus-4-5",
            "sonnet-4.6": "claude-sonnet-4-6",
            "sonnet-4.5": "claude-sonnet-4-5",
        }
        return anthropic_aliases.get(trimmed.lower(), trimmed)
    if provider == "huggingface" and trimmed.lower().startswith("huggingface/"):
        return trimmed[len("huggingface/") :]
    if provider == "openrouter" and "/" not in trimmed:
        return f"openrouter/{trimmed}"
    if provider == "vercel-ai-gateway" and "/" not in trimmed:
        anthropic_aliases = {
            "opus-4.6": "claude-opus-4-6",
            "opus-4.5": "claude-opus-4-5",
            "sonnet-4.6": "claude-sonnet-4-6",
            "sonnet-4.5": "claude-sonnet-4-5",
        }
        normalized = anthropic_aliases.get(trimmed.lower(), trimmed)
        return f"anthropic/{normalized}" if normalized.startswith("claude-") else normalized
    return trimmed


def _model_config_key(provider: str, model: str) -> str:
    provider_id = provider.strip()
    model_id = model.strip()
    if not provider_id:
        return model_id
    if not model_id:
        return provider_id
    if model_id.lower().startswith(f"{provider_id.lower()}/"):
        return model_id
    return f"{provider_id}/{model_id}"


def _legacy_model_config_key(target: str) -> str | None:
    if not target.startswith("openrouter/"):
        return None
    remainder = target[len("openrouter/") :]
    if not remainder or "/" in remainder:
        return None
    return f"openrouter/{target}"


def _normalize_agent_id(value: str | None) -> str:
    trimmed = (value or "").strip()
    if not trimmed:
        return _DEFAULT_AGENT_ID
    lowered = trimmed.lower()
    if _AGENT_ID_VALID_PATTERN.fullmatch(trimmed) is not None:
        return lowered
    normalized = _AGENT_ID_INVALID_CHARS_PATTERN.sub("-", lowered)
    normalized = normalized.strip("-")[:64]
    return normalized or _DEFAULT_AGENT_ID


def _agent_entries_from_config_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    agents = snapshot.get("agents")
    if not isinstance(agents, dict):
        return []
    raw_entries = agents.get("list")
    if not isinstance(raw_entries, list):
        return []
    return [entry for entry in raw_entries if isinstance(entry, dict)]


def _known_agent_ids_from_config_snapshot(snapshot: dict[str, Any]) -> list[str]:
    entries = _agent_entries_from_config_snapshot(snapshot)
    if not entries:
        return [_DEFAULT_AGENT_ID]
    ids: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        agent_id = _normalize_agent_id(str(entry.get("id") or ""))
        if agent_id in seen:
            continue
        seen.add(agent_id)
        ids.append(agent_id)
    return ids or [_DEFAULT_AGENT_ID]


def _default_agent_id_from_config_snapshot(snapshot: dict[str, Any]) -> str:
    entries = _agent_entries_from_config_snapshot(snapshot)
    if not entries:
        return _DEFAULT_AGENT_ID
    for entry in entries:
        if entry.get("default") is True:
            return _normalize_agent_id(str(entry.get("id") or ""))
    return _normalize_agent_id(str(entries[0].get("id") or ""))


def _agent_entry_from_config_snapshot(
    snapshot: dict[str, Any],
    *,
    agent_id: str,
) -> dict[str, Any] | None:
    for entry in _agent_entries_from_config_snapshot(snapshot):
        if _normalize_agent_id(str(entry.get("id") or "")) == agent_id:
            return entry
    return None


def _resolve_model_auth_agent_dir(
    *,
    data_dir: Path,
    agent_id: str,
    raw_agent_dir: object,
) -> Path:
    if isinstance(raw_agent_dir, str) and raw_agent_dir.strip():
        configured = Path(raw_agent_dir.strip()).expanduser()
        if configured.is_absolute():
            return configured
        return data_dir / configured
    return data_dir / "agents" / agent_id / "agent"


def _resolve_model_auth_order_context(
    snapshot: dict[str, Any],
    *,
    data_dir: Path,
    provider: str,
    agent: str | None,
) -> dict[str, Any]:
    provider_id = _normalize_model_auth_provider(provider)
    if agent is not None and agent.strip():
        raw_agent = agent.strip()
        agent_id = _normalize_agent_id(raw_agent)
        known_agents = _known_agent_ids_from_config_snapshot(snapshot)
        if agent_id not in known_agents:
            raise ValueError(
                f'Unknown agent id "{raw_agent}". Use "openclaw agents list" '
                "to see configured agents."
            )
    else:
        agent_id = _default_agent_id_from_config_snapshot(snapshot)
    entry = _agent_entry_from_config_snapshot(snapshot, agent_id=agent_id)
    agent_dir = _resolve_model_auth_agent_dir(
        data_dir=data_dir,
        agent_id=agent_id,
        raw_agent_dir=entry.get("agentDir") if entry is not None else None,
    )
    return {
        "agent_id": agent_id,
        "agent_dir": agent_dir,
        "provider": provider_id,
        "auth_state_path": agent_dir / "auth-state.json",
        "auth_store_path": agent_dir / "auth-profiles.json",
    }


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_or_remove_auth_state(path: Path, payload: dict[str, Any] | None) -> None:
    if payload is None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return
    _write_json_object(path, payload)


def _normalize_string_entries(entries: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        value = entry.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _auth_profiles_from_store(store: dict[str, Any]) -> dict[str, Any]:
    profiles = store.get("profiles")
    return dict(profiles) if isinstance(profiles, dict) else {}


def _auth_order_from_state(state: dict[str, Any], *, provider: str) -> list[str]:
    raw_order = state.get("order")
    if not isinstance(raw_order, dict):
        return []
    provider_key = _normalize_model_auth_provider(provider)
    for raw_provider, raw_entries in raw_order.items():
        if not isinstance(raw_provider, str):
            continue
        if _normalize_model_auth_provider(raw_provider) != provider_key:
            continue
        if not isinstance(raw_entries, list):
            return []
        return [entry.strip() for entry in raw_entries if isinstance(entry, str) and entry.strip()]
    return []


def _set_auth_order_in_state(
    state: dict[str, Any],
    *,
    provider: str,
    order: list[str],
) -> dict[str, Any]:
    provider_key = _normalize_model_auth_provider(provider)
    raw_order = state.get("order")
    next_order: dict[str, list[str]] = {}
    if isinstance(raw_order, dict):
        for raw_provider, raw_entries in raw_order.items():
            if not isinstance(raw_provider, str):
                continue
            if _normalize_model_auth_provider(raw_provider) == provider_key:
                continue
            if not isinstance(raw_entries, list):
                continue
            entries = [
                entry.strip()
                for entry in raw_entries
                if isinstance(entry, str) and entry.strip()
            ]
            if entries:
                next_order[raw_provider] = entries
    next_order[provider_key] = order
    next_state: dict[str, Any] = {
        key: value
        for key, value in state.items()
        if key in {"lastGood", "usageStats"} and isinstance(value, dict)
    }
    next_state["version"] = 1
    next_state["order"] = next_order
    return next_state


def _clear_auth_order_in_state(
    state: dict[str, Any],
    *,
    provider: str,
) -> dict[str, Any] | None:
    provider_key = _normalize_model_auth_provider(provider)
    raw_order = state.get("order")
    next_order: dict[str, list[str]] = {}
    if isinstance(raw_order, dict):
        for raw_provider, raw_entries in raw_order.items():
            if not isinstance(raw_provider, str):
                continue
            if _normalize_model_auth_provider(raw_provider) == provider_key:
                continue
            if not isinstance(raw_entries, list):
                continue
            entries = [
                entry.strip()
                for entry in raw_entries
                if isinstance(entry, str) and entry.strip()
            ]
            if entries:
                next_order[raw_provider] = entries
    next_state: dict[str, Any] = {
        key: value
        for key, value in state.items()
        if key in {"lastGood", "usageStats"} and isinstance(value, dict)
    }
    if next_order:
        next_state["order"] = next_order
    if not next_state:
        return None
    next_state["version"] = 1
    return next_state


def _model_aliases_from_config_snapshot(snapshot: dict[str, Any]) -> dict[str, str]:
    models = _agents_defaults_models_from_snapshot(snapshot)
    aliases: dict[str, str] = {}
    for model_key, raw_entry in models.items():
        if not isinstance(raw_entry, dict):
            continue
        alias = raw_entry.get("alias")
        if isinstance(alias, str) and alias.strip():
            aliases[alias.strip()] = model_key
    return aliases


def _agents_defaults_models_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    agents = snapshot.get("agents")
    if not isinstance(agents, dict):
        return {}
    defaults = agents.get("defaults")
    if not isinstance(defaults, dict):
        return {}
    models = defaults.get("models")
    return dict(models) if isinstance(models, dict) else {}


def _model_fallbacks_from_config_snapshot(
    snapshot: dict[str, Any],
    *,
    key: str = "model",
) -> list[str]:
    agents = snapshot.get("agents")
    if not isinstance(agents, dict):
        return []
    defaults = agents.get("defaults")
    if not isinstance(defaults, dict):
        return []
    model = defaults.get(key)
    if not isinstance(model, dict):
        return []
    fallbacks = model.get("fallbacks")
    if not isinstance(fallbacks, list):
        return []
    return [entry.strip() for entry in fallbacks if isinstance(entry, str) and entry.strip()]


def _set_model_alias_in_snapshot(
    snapshot: dict[str, Any],
    *,
    alias: str,
    target: str,
) -> dict[str, Any]:
    models = _agents_defaults_models_from_snapshot(snapshot)
    for model_key, raw_entry in models.items():
        entry = raw_entry if isinstance(raw_entry, dict) else {}
        existing = entry.get("alias")
        if isinstance(existing, str) and existing.strip() == alias and model_key != target:
            raise ValueError(f"Alias {alias} already points to {model_key}.")
    target_entry = models.get(target)
    next_models = dict(models)
    next_entry = dict(target_entry) if isinstance(target_entry, dict) else {}
    next_entry["alias"] = alias
    next_models[target] = next_entry
    next_snapshot = dict(snapshot)
    raw_agents = next_snapshot.get("agents")
    agents = dict(raw_agents) if isinstance(raw_agents, dict) else {}
    raw_defaults = agents.get("defaults")
    defaults = dict(raw_defaults) if isinstance(raw_defaults, dict) else {}
    defaults["models"] = next_models
    agents["defaults"] = defaults
    next_snapshot["agents"] = agents
    return next_snapshot


def _set_model_fallbacks_in_snapshot(
    snapshot: dict[str, Any],
    *,
    fallbacks: list[str],
    key: str = "model",
) -> dict[str, Any]:
    next_snapshot = dict(snapshot)
    raw_agents = next_snapshot.get("agents")
    agents = dict(raw_agents) if isinstance(raw_agents, dict) else {}
    raw_defaults = agents.get("defaults")
    defaults = dict(raw_defaults) if isinstance(raw_defaults, dict) else {}
    raw_model = defaults.get(key)
    if isinstance(raw_model, dict):
        model = dict(raw_model)
    elif isinstance(raw_model, str) and raw_model.strip():
        model = {"primary": raw_model.strip()}
    else:
        model = {}
    model["fallbacks"] = list(fallbacks)
    defaults[key] = model
    agents["defaults"] = defaults
    next_snapshot["agents"] = agents
    return next_snapshot


def _set_model_primary_in_snapshot(
    snapshot: dict[str, Any],
    *,
    target: str,
    key: str = "model",
) -> dict[str, Any]:
    next_snapshot = dict(snapshot)
    raw_agents = next_snapshot.get("agents")
    agents = dict(raw_agents) if isinstance(raw_agents, dict) else {}
    raw_defaults = agents.get("defaults")
    defaults = dict(raw_defaults) if isinstance(raw_defaults, dict) else {}
    raw_model = defaults.get(key)
    if isinstance(raw_model, dict):
        model = dict(raw_model)
    else:
        model = {}
    model["primary"] = target
    defaults[key] = model
    agents["defaults"] = defaults
    next_snapshot["agents"] = agents
    return next_snapshot


def _ensure_model_config_entry_in_snapshot(
    snapshot: dict[str, Any],
    *,
    target: str,
) -> dict[str, Any]:
    next_snapshot = dict(snapshot)
    raw_agents = next_snapshot.get("agents")
    agents = dict(raw_agents) if isinstance(raw_agents, dict) else {}
    raw_defaults = agents.get("defaults")
    defaults = dict(raw_defaults) if isinstance(raw_defaults, dict) else {}
    raw_models = defaults.get("models")
    models = dict(raw_models) if isinstance(raw_models, dict) else {}
    target_entry = models.get(target)
    legacy_key = _legacy_model_config_key(target)
    if not isinstance(target_entry, dict) and legacy_key is not None:
        target_entry = models.get(legacy_key)
    models[target] = dict(target_entry) if isinstance(target_entry, dict) else {}
    if legacy_key is not None:
        models.pop(legacy_key, None)
    defaults["models"] = models
    agents["defaults"] = defaults
    next_snapshot["agents"] = agents
    return next_snapshot


def _remove_model_alias_in_snapshot(
    snapshot: dict[str, Any],
    *,
    alias: str,
) -> dict[str, Any]:
    models = _agents_defaults_models_from_snapshot(snapshot)
    found_key: str | None = None
    for model_key, raw_entry in models.items():
        if not isinstance(raw_entry, dict):
            continue
        existing = raw_entry.get("alias")
        if isinstance(existing, str) and existing.strip() == alias:
            found_key = model_key
            break
    if found_key is None:
        raise ValueError(f"Alias not found: {alias}")
    next_models = dict(models)
    target_entry = next_models.get(found_key)
    next_entry = dict(target_entry) if isinstance(target_entry, dict) else {}
    next_entry.pop("alias", None)
    next_models[found_key] = next_entry
    next_snapshot = dict(snapshot)
    raw_agents = next_snapshot.get("agents")
    agents = dict(raw_agents) if isinstance(raw_agents, dict) else {}
    raw_defaults = agents.get("defaults")
    defaults = dict(raw_defaults) if isinstance(raw_defaults, dict) else {}
    defaults["models"] = next_models
    agents["defaults"] = defaults
    next_snapshot["agents"] = agents
    return next_snapshot


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


def _set_plugin_enabled_in_snapshot(
    snapshot: dict[str, Any],
    plugin_id: str,
    enabled: bool,
) -> dict[str, Any]:
    requested_id = plugin_id.strip()
    if not requested_id:
        raise ValueError("plugin id is required")
    channel_id = _normalize_openclaw_channel_plugin_id(requested_id)
    resolved_id = channel_id or requested_id
    plugins = snapshot.get("plugins")
    plugins_config = dict(plugins) if isinstance(plugins, dict) else {}

    if enabled:
        if plugins_config.get("enabled") is False:
            return {
                "config": dict(snapshot),
                "pluginId": requested_id,
                "resolvedPluginId": resolved_id,
                "enabled": False,
                "reason": "plugins disabled",
                "channelSynced": False,
            }
        deny = plugins_config.get("deny")
        deny_values = {str(value) for value in deny} if isinstance(deny, list) else set()
        if requested_id in deny_values or resolved_id in deny_values:
            return {
                "config": dict(snapshot),
                "pluginId": requested_id,
                "resolvedPluginId": resolved_id,
                "enabled": False,
                "reason": "blocked by denylist",
                "channelSynced": False,
            }

    entries = plugins_config.get("entries")
    next_entries = dict(entries) if isinstance(entries, dict) else {}
    existing_entry = next_entries.get(resolved_id)
    next_entry = dict(existing_entry) if isinstance(existing_entry, dict) else {}
    next_entry["enabled"] = enabled
    next_entries[resolved_id] = next_entry

    next_plugins = dict(plugins_config)
    next_plugins["entries"] = next_entries
    if enabled:
        allow = next_plugins.get("allow")
        if isinstance(allow, list) and resolved_id not in {str(value) for value in allow}:
            next_plugins["allow"] = [*allow, resolved_id]

    next_snapshot = dict(snapshot)
    next_snapshot["plugins"] = next_plugins
    channel_synced = False
    if channel_id is not None:
        channels = next_snapshot.get("channels")
        next_channels = dict(channels) if isinstance(channels, dict) else {}
        existing_channel = next_channels.get(channel_id)
        next_channel = dict(existing_channel) if isinstance(existing_channel, dict) else {}
        next_channel["enabled"] = enabled
        next_channels[channel_id] = next_channel
        next_snapshot["channels"] = next_channels
        channel_synced = True

    return {
        "config": next_snapshot,
        "pluginId": requested_id,
        "resolvedPluginId": resolved_id,
        "enabled": enabled,
        "reason": None,
        "channelSynced": channel_synced,
    }


def _record_marketplace_plugin_install_in_snapshot(
    snapshot: dict[str, Any],
    *,
    plugin_id: str,
    install_path: str,
    marketplace_source: str,
    marketplace_plugin: str,
    marketplace_name: str | None,
    version: str | None,
    force: bool,
) -> dict[str, Any]:
    requested_id = plugin_id.strip()
    if not requested_id:
        raise ValueError("plugin id is required")
    normalized_install_path = install_path.strip()
    if not normalized_install_path:
        raise ValueError("plugin install path is required")
    normalized_marketplace_source = marketplace_source.strip()
    if not normalized_marketplace_source:
        raise ValueError("marketplace source is required")
    normalized_marketplace_plugin = marketplace_plugin.strip()
    if not normalized_marketplace_plugin:
        raise ValueError("marketplace plugin is required")

    plugins = snapshot.get("plugins")
    plugins_config = dict(plugins) if isinstance(plugins, dict) else {}
    installs = plugins_config.get("installs")
    next_installs = dict(installs) if isinstance(installs, dict) else {}
    if requested_id in next_installs and not force:
        raise ValueError(f'plugin "{requested_id}" is already installed; pass --force to update')

    install_record: dict[str, Any] = {
        "source": "marketplace",
        "installPath": normalized_install_path,
        "marketplaceSource": normalized_marketplace_source,
        "marketplacePlugin": normalized_marketplace_plugin,
        "installedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    normalized_marketplace_name = (
        marketplace_name.strip() if isinstance(marketplace_name, str) else None
    )
    if normalized_marketplace_name:
        install_record["marketplaceName"] = normalized_marketplace_name
    normalized_version = version.strip() if isinstance(version, str) else None
    if normalized_version:
        install_record["version"] = normalized_version
    next_installs[requested_id] = install_record

    entries = plugins_config.get("entries")
    next_entries = dict(entries) if isinstance(entries, dict) else {}
    existing_entry = next_entries.get(requested_id)
    next_entry = dict(existing_entry) if isinstance(existing_entry, dict) else {}
    next_entry["enabled"] = True
    next_entries[requested_id] = next_entry

    allow = plugins_config.get("allow")
    next_allow = list(allow) if isinstance(allow, list) else []
    if requested_id not in {str(value) for value in next_allow}:
        next_allow.append(requested_id)

    load = plugins_config.get("load")
    next_load = dict(load) if isinstance(load, dict) else {}
    paths = next_load.get("paths")
    next_paths = [str(value) for value in paths] if isinstance(paths, list) else []
    if normalized_install_path not in next_paths:
        next_paths.append(normalized_install_path)
    next_load["paths"] = next_paths

    next_plugins = dict(plugins_config)
    next_plugins["allow"] = next_allow
    next_plugins["entries"] = next_entries
    next_plugins["installs"] = next_installs
    next_plugins["load"] = next_load

    next_snapshot = dict(snapshot)
    next_snapshot["plugins"] = next_plugins
    return {
        "config": next_snapshot,
        "pluginId": requested_id,
        "install": install_record,
        "loadPath": normalized_install_path,
    }


def _uninstall_plugin_in_snapshot(
    snapshot: dict[str, Any],
    *,
    plugin_id: str,
) -> dict[str, Any]:
    requested_id = plugin_id.strip()
    if not requested_id:
        raise ValueError("plugin id is required")

    plugins = snapshot.get("plugins")
    plugins_config = dict(plugins) if isinstance(plugins, dict) else {}
    entries = plugins_config.get("entries")
    next_entries = dict(entries) if isinstance(entries, dict) else {}
    installs = plugins_config.get("installs")
    next_installs = dict(installs) if isinstance(installs, dict) else {}
    has_entry = requested_id in next_entries
    has_install = requested_id in next_installs
    if not has_entry and not has_install:
        raise ValueError(f"Plugin not found: {requested_id}")

    install_record = next_installs.get(requested_id)
    install_payload = install_record if isinstance(install_record, dict) else {}
    actions: dict[str, bool] = {
        "entry": False,
        "install": False,
        "allowlist": False,
        "loadPath": False,
        "memorySlot": False,
        "channelConfig": False,
        "directory": False,
    }
    if has_entry:
        next_entries.pop(requested_id, None)
        actions["entry"] = True
    if has_install:
        next_installs.pop(requested_id, None)
        actions["install"] = True

    allow = plugins_config.get("allow")
    next_allow = list(allow) if isinstance(allow, list) else []
    filtered_allow = [value for value in next_allow if str(value) != requested_id]
    if len(filtered_allow) != len(next_allow):
        actions["allowlist"] = True

    load = plugins_config.get("load")
    next_load = dict(load) if isinstance(load, dict) else {}
    paths = next_load.get("paths")
    next_paths = [str(value) for value in paths] if isinstance(paths, list) else []
    removable_paths = {
        str(value)
        for value in (
            install_payload.get("installPath"),
            install_payload.get("sourcePath"),
        )
        if isinstance(value, str) and value.strip()
    }
    if removable_paths:
        filtered_paths = [path for path in next_paths if path not in removable_paths]
        if len(filtered_paths) != len(next_paths):
            actions["loadPath"] = True
        next_paths = filtered_paths
    if next_paths:
        next_load["paths"] = next_paths
    else:
        next_load.pop("paths", None)

    slots = plugins_config.get("slots")
    next_slots = dict(slots) if isinstance(slots, dict) else {}
    if next_slots.get("memory") == requested_id:
        next_slots["memory"] = "memory-core"
        actions["memorySlot"] = True

    next_snapshot = dict(snapshot)
    channels = next_snapshot.get("channels")
    if has_install and isinstance(channels, dict):
        next_channels = dict(channels)
        channel_keys = {requested_id}
        normalized_channel = _normalize_openclaw_channel_plugin_id(requested_id)
        if normalized_channel is not None:
            channel_keys.add(normalized_channel)
        for key in channel_keys:
            if key in next_channels:
                next_channels.pop(key, None)
                actions["channelConfig"] = True
        if next_channels:
            next_snapshot["channels"] = next_channels
        elif "channels" in next_snapshot:
            next_snapshot.pop("channels", None)

    next_plugins = dict(plugins_config)
    if next_entries:
        next_plugins["entries"] = next_entries
    else:
        next_plugins.pop("entries", None)
    if next_installs:
        next_plugins["installs"] = next_installs
    else:
        next_plugins.pop("installs", None)
    if filtered_allow:
        next_plugins["allow"] = filtered_allow
    else:
        next_plugins.pop("allow", None)
    if next_load:
        next_plugins["load"] = next_load
    else:
        next_plugins.pop("load", None)
    if next_slots:
        next_plugins["slots"] = next_slots
    else:
        next_plugins.pop("slots", None)

    if next_plugins:
        next_snapshot["plugins"] = next_plugins
    else:
        next_snapshot.pop("plugins", None)

    return {
        "config": next_snapshot,
        "pluginId": requested_id,
        "actions": actions,
        "warnings": [],
    }


def _normalize_openclaw_channel_plugin_id(plugin_id: str) -> str | None:
    normalized = plugin_id.strip().lower()
    if not normalized:
        return None
    return _OPENCLAW_CHANNEL_PLUGIN_ALIASES.get(normalized)


def _clean_config_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    omitted_null_sections = (
        "agents",
        "gateway",
        "session",
        "tools",
        "acp",
        "plugins",
        "channels",
        "messages",
    )
    if any(snapshot.get(section) is None for section in omitted_null_sections):
        snapshot = dict(snapshot)
        for section in omitted_null_sections:
            if snapshot.get(section) is None:
                snapshot.pop(section, None)
    return snapshot


def _reject_legacy_thread_binding_ttl_hours(payload: dict[str, Any]) -> None:
    legacy_paths = list(_iter_legacy_thread_binding_ttl_hour_paths(payload))
    if not legacy_paths:
        return
    path = legacy_paths[0]
    replacement = path.removesuffix(".ttlHours") + ".idleHours"
    raise ValueError(
        f'{path} is legacy; use {replacement}. Run "openzues doctor --fix".'
    )


def _iter_legacy_thread_binding_ttl_hour_paths(payload: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    session = payload.get("session")
    if isinstance(session, dict):
        thread_bindings = session.get("threadBindings")
        if isinstance(thread_bindings, dict) and "ttlHours" in thread_bindings:
            paths.append("session.threadBindings.ttlHours")

    channels = payload.get("channels")
    if not isinstance(channels, dict):
        return paths
    for raw_channel_id, raw_channel in channels.items():
        channel_id = str(raw_channel_id)
        if channel_id == "defaults" or not isinstance(raw_channel, dict):
            continue
        thread_bindings = raw_channel.get("threadBindings")
        if isinstance(thread_bindings, dict) and "ttlHours" in thread_bindings:
            paths.append(f"channels.{channel_id}.threadBindings.ttlHours")
        accounts = raw_channel.get("accounts")
        if not isinstance(accounts, dict):
            continue
        for raw_account_id, raw_account in accounts.items():
            if not isinstance(raw_account, dict):
                continue
            account_thread_bindings = raw_account.get("threadBindings")
            if isinstance(account_thread_bindings, dict) and "ttlHours" in account_thread_bindings:
                account_id = str(raw_account_id)
                paths.append(
                    f"channels.{channel_id}.accounts.{account_id}.threadBindings.ttlHours"
                )
    return paths


def _legacy_thread_binding_ttl_hour_issue(path: str) -> dict[str, str]:
    replacement = path.removesuffix(".ttlHours") + ".idleHours"
    return {
        "path": path,
        "replacement": replacement,
        "message": f"{path} is legacy; use {replacement}.",
    }


def _legacy_channel_allow_alias_issue(path: str) -> dict[str, str]:
    replacement = path.removesuffix(".allow") + ".enabled"
    return {
        "path": path,
        "replacement": replacement,
        "message": f"{path} is legacy; use {replacement}.",
    }


def _legacy_x_search_api_key_issue(path: str) -> dict[str, str]:
    return {
        "path": path,
        "replacement": "plugins.entries.xai.config.webSearch.apiKey",
        "message": (
            "tools.web.x_search.apiKey is legacy; use "
            "plugins.entries.xai.config.webSearch.apiKey."
        ),
    }


def _legacy_web_search_provider_issue(path: str) -> dict[str, str]:
    return {
        "path": path,
        "replacement": "plugins.entries.<plugin>.config.webSearch",
        "message": (
            "tools.web.search provider-owned config moved to "
            "plugins.entries.<plugin>.config.webSearch."
        ),
    }


def _legacy_telegram_streaming_issue(path: str) -> dict[str, str]:
    return {
        "path": path,
        "replacement": f"{path}.streaming",
        "message": (
            f"{path} uses legacy Telegram streaming scalar aliases; use "
            f"{path}.streaming.*."
        ),
    }


def _legacy_slack_streaming_issue(path: str) -> dict[str, str]:
    return {
        "path": path,
        "replacement": f"{path}.streaming",
        "message": (
            f"{path} uses legacy Slack streaming scalar aliases; use "
            f"{path}.streaming.*."
        ),
    }


def _legacy_googlechat_stream_mode_issue(path: str) -> dict[str, str]:
    return {
        "path": path,
        "replacement": "",
        "message": f"{path}.streamMode is legacy and no longer used.",
    }


def _legacy_gateway_bind_alias_issue(path: str) -> dict[str, str]:
    return {
        "path": path,
        "replacement": "gateway.bind",
        "message": (
            "gateway.bind host aliases are legacy; use bind modes "
            "lan/loopback/custom/tailnet/auto instead."
        ),
    }


def _legacy_sandbox_per_session_issue(path: str) -> dict[str, str]:
    replacement = path.removesuffix(".perSession") + ".scope"
    return {
        "path": path,
        "replacement": replacement,
        "message": f"{path} is legacy; use {replacement}.",
    }


def _legacy_memory_search_issue(path: str) -> dict[str, str]:
    return {
        "path": path,
        "replacement": "agents.defaults.memorySearch",
        "message": "top-level memorySearch is legacy; use agents.defaults.memorySearch.",
    }


def _legacy_heartbeat_issue(path: str) -> dict[str, str]:
    return {
        "path": path,
        "replacement": "agents.defaults.heartbeat",
        "message": "top-level heartbeat is legacy; use defaults heartbeat config.",
    }


def _legacy_tts_provider_issue(path: str) -> dict[str, str]:
    return {
        "path": path,
        "replacement": f"{path}.providers",
        "message": f"{path}.<provider> keys are legacy; use {path}.providers.",
    }


def _collect_legacy_config_issues(payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        *[
            _legacy_thread_binding_ttl_hour_issue(path)
            for path in _iter_legacy_thread_binding_ttl_hour_paths(payload)
        ],
        *[
            _legacy_channel_allow_alias_issue(path)
            for path in _iter_legacy_channel_allow_alias_paths(payload)
        ],
        *[
            _legacy_x_search_api_key_issue(path)
            for path in _iter_legacy_x_search_api_key_paths(payload)
        ],
        *[
            _legacy_web_search_provider_issue(path)
            for path in _iter_legacy_web_search_provider_paths(payload)
        ],
        *[
            _legacy_telegram_streaming_issue(path)
            for path in _iter_legacy_telegram_streaming_paths(payload)
        ],
        *[
            _legacy_slack_streaming_issue(path)
            for path in _iter_legacy_slack_streaming_paths(payload)
        ],
        *[
            _legacy_googlechat_stream_mode_issue(path)
            for path in _iter_legacy_googlechat_stream_mode_paths(payload)
        ],
        *[
            _legacy_sandbox_per_session_issue(path)
            for path in _iter_legacy_sandbox_per_session_paths(payload)
        ],
        *[
            _legacy_memory_search_issue(path)
            for path in _iter_legacy_memory_search_paths(payload)
        ],
        *[
            _legacy_heartbeat_issue(path)
            for path in _iter_legacy_heartbeat_paths(payload)
        ],
        *[
            _legacy_tts_provider_issue(path)
            for path in _iter_legacy_tts_provider_paths(payload)
        ],
        *[
            _legacy_gateway_bind_alias_issue(path)
            for path in _iter_legacy_gateway_bind_alias_paths(payload)
        ],
    ]


def _migrate_legacy_thread_binding_ttl_hours(payload: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    session = payload.get("session")
    if isinstance(session, dict):
        _migrate_thread_binding_ttl_hours_at(
            session,
            path_label="session",
            changes=changes,
        )

    channels = payload.get("channels")
    if not isinstance(channels, dict):
        return changes
    for raw_channel_id, raw_channel in channels.items():
        channel_id = str(raw_channel_id)
        if channel_id == "defaults" or not isinstance(raw_channel, dict):
            continue
        channel_path = f"channels.{channel_id}"
        _migrate_thread_binding_ttl_hours_at(
            raw_channel,
            path_label=channel_path,
            changes=changes,
        )
        accounts = raw_channel.get("accounts")
        if not isinstance(accounts, dict):
            continue
        for raw_account_id, raw_account in accounts.items():
            if not isinstance(raw_account, dict):
                continue
            _migrate_thread_binding_ttl_hours_at(
                raw_account,
                path_label=f"{channel_path}.accounts.{raw_account_id}",
                changes=changes,
            )
    return changes


def _migrate_thread_binding_ttl_hours_at(
    container: dict[str, Any],
    *,
    path_label: str,
    changes: list[str],
) -> None:
    thread_bindings = container.get("threadBindings")
    if not isinstance(thread_bindings, dict) or "ttlHours" not in thread_bindings:
        return
    if "idleHours" not in thread_bindings:
        thread_bindings["idleHours"] = thread_bindings["ttlHours"]
    del thread_bindings["ttlHours"]
    changes.append(f"Moved {path_label}.threadBindings.ttlHours to idleHours.")


def _iter_legacy_channel_allow_alias_paths(payload: dict[str, Any]) -> list[str]:
    channels = payload.get("channels")
    if not isinstance(channels, dict):
        return []
    paths: list[str] = []
    slack = channels.get("slack")
    if isinstance(slack, dict):
        paths.extend(_iter_collection_allow_alias_paths(slack, "channels.slack", "channels"))
        paths.extend(
            _iter_account_collection_allow_alias_paths(
                slack,
                "channels.slack",
                "channels",
            )
        )
    googlechat = channels.get("googlechat")
    if isinstance(googlechat, dict):
        paths.extend(
            _iter_collection_allow_alias_paths(googlechat, "channels.googlechat", "groups")
        )
        paths.extend(
            _iter_account_collection_allow_alias_paths(
                googlechat,
                "channels.googlechat",
                "groups",
            )
        )
    discord = channels.get("discord")
    if isinstance(discord, dict):
        paths.extend(_iter_discord_guild_channel_allow_alias_paths(discord, "channels.discord"))
        paths.extend(_iter_discord_account_guild_channel_allow_alias_paths(discord))
    return paths


def _iter_collection_allow_alias_paths(
    container: dict[str, Any],
    path_prefix: str,
    collection_key: str,
) -> list[str]:
    collection = container.get(collection_key)
    if not isinstance(collection, dict):
        return []
    return [
        f"{path_prefix}.{collection_key}.{item_id}.allow"
        for item_id, item in collection.items()
        if isinstance(item, dict) and "allow" in item
    ]


def _iter_account_collection_allow_alias_paths(
    provider: dict[str, Any],
    path_prefix: str,
    collection_key: str,
) -> list[str]:
    accounts = provider.get("accounts")
    if not isinstance(accounts, dict):
        return []
    paths: list[str] = []
    for account_id, account in accounts.items():
        if not isinstance(account, dict):
            continue
        paths.extend(
            _iter_collection_allow_alias_paths(
                account,
                f"{path_prefix}.accounts.{account_id}",
                collection_key,
            )
        )
    return paths


def _iter_discord_guild_channel_allow_alias_paths(
    container: dict[str, Any],
    path_prefix: str,
) -> list[str]:
    guilds = container.get("guilds")
    if not isinstance(guilds, dict):
        return []
    paths: list[str] = []
    for guild_id, guild in guilds.items():
        if not isinstance(guild, dict):
            continue
        paths.extend(
            _iter_collection_allow_alias_paths(
                guild,
                f"{path_prefix}.guilds.{guild_id}",
                "channels",
            )
        )
    return paths


def _iter_discord_account_guild_channel_allow_alias_paths(
    discord: dict[str, Any],
) -> list[str]:
    accounts = discord.get("accounts")
    if not isinstance(accounts, dict):
        return []
    paths: list[str] = []
    for account_id, account in accounts.items():
        if not isinstance(account, dict):
            continue
        paths.extend(
            _iter_discord_guild_channel_allow_alias_paths(
                account,
                f"channels.discord.accounts.{account_id}",
            )
        )
    return paths


def _migrate_legacy_channel_allow_aliases(payload: dict[str, Any]) -> list[str]:
    channels = payload.get("channels")
    if not isinstance(channels, dict):
        return []
    changes: list[str] = []
    slack = channels.get("slack")
    if isinstance(slack, dict):
        _migrate_collection_allow_aliases(slack, "channels.slack", "channels", changes)
        _migrate_account_collection_allow_aliases(slack, "channels.slack", "channels", changes)
    googlechat = channels.get("googlechat")
    if isinstance(googlechat, dict):
        _migrate_collection_allow_aliases(
            googlechat,
            "channels.googlechat",
            "groups",
            changes,
        )
        _migrate_account_collection_allow_aliases(
            googlechat,
            "channels.googlechat",
            "groups",
            changes,
        )
    discord = channels.get("discord")
    if isinstance(discord, dict):
        _migrate_discord_guild_channel_allow_aliases(discord, "channels.discord", changes)
        _migrate_discord_account_guild_channel_allow_aliases(discord, changes)
    return changes


def _migrate_collection_allow_aliases(
    container: dict[str, Any],
    path_prefix: str,
    collection_key: str,
    changes: list[str],
) -> None:
    collection = container.get(collection_key)
    if not isinstance(collection, dict):
        return
    for item_id, item in collection.items():
        if not isinstance(item, dict):
            continue
        _migrate_allow_alias_at(
            item,
            path_label=f"{path_prefix}.{collection_key}.{item_id}",
            changes=changes,
        )


def _migrate_account_collection_allow_aliases(
    provider: dict[str, Any],
    path_prefix: str,
    collection_key: str,
    changes: list[str],
) -> None:
    accounts = provider.get("accounts")
    if not isinstance(accounts, dict):
        return
    for account_id, account in accounts.items():
        if not isinstance(account, dict):
            continue
        _migrate_collection_allow_aliases(
            account,
            f"{path_prefix}.accounts.{account_id}",
            collection_key,
            changes,
        )


def _migrate_discord_guild_channel_allow_aliases(
    container: dict[str, Any],
    path_prefix: str,
    changes: list[str],
) -> None:
    guilds = container.get("guilds")
    if not isinstance(guilds, dict):
        return
    for guild_id, guild in guilds.items():
        if not isinstance(guild, dict):
            continue
        _migrate_collection_allow_aliases(
            guild,
            f"{path_prefix}.guilds.{guild_id}",
            "channels",
            changes,
        )


def _migrate_discord_account_guild_channel_allow_aliases(
    discord: dict[str, Any],
    changes: list[str],
) -> None:
    accounts = discord.get("accounts")
    if not isinstance(accounts, dict):
        return
    for account_id, account in accounts.items():
        if not isinstance(account, dict):
            continue
        _migrate_discord_guild_channel_allow_aliases(
            account,
            f"channels.discord.accounts.{account_id}",
            changes,
        )


def _migrate_allow_alias_at(
    entry: dict[str, Any],
    *,
    path_label: str,
    changes: list[str],
) -> None:
    if "allow" not in entry:
        return
    if "enabled" not in entry:
        entry["enabled"] = entry["allow"]
        changes.append(f"Moved {path_label}.allow to enabled.")
    else:
        changes.append(f"Removed {path_label}.allow ({path_label}.enabled already set).")
    del entry["allow"]


def _iter_legacy_x_search_api_key_paths(payload: dict[str, Any]) -> list[str]:
    legacy = _legacy_x_search_config(payload)
    if not isinstance(legacy, dict) or "apiKey" not in legacy:
        return []
    return ["tools.web.x_search.apiKey"]


def _legacy_x_search_config(payload: dict[str, Any]) -> dict[str, Any] | None:
    tools = payload.get("tools")
    if not isinstance(tools, dict):
        return None
    web = tools.get("web")
    if not isinstance(web, dict):
        return None
    x_search = web.get("x_search")
    return x_search if isinstance(x_search, dict) else None


def _migrate_legacy_x_search_api_key(payload: dict[str, Any]) -> list[str]:
    legacy = _legacy_x_search_config(payload)
    if legacy is None or "apiKey" not in legacy:
        return []
    auth = legacy.get("apiKey")
    del legacy["apiKey"]

    tools = _ensure_config_record(payload, "tools")
    web = _ensure_config_record(tools, "web")
    if legacy:
        web["x_search"] = legacy
    else:
        web.pop("x_search", None)

    plugins = _ensure_config_record(payload, "plugins")
    entries = _ensure_config_record(plugins, "entries")
    xai = _ensure_config_record(entries, "xai")
    had_enabled = "enabled" in xai
    if not had_enabled:
        xai["enabled"] = True
    config = _ensure_config_record(xai, "config")
    existing_web_search = config.get("webSearch")
    web_search = dict(existing_web_search) if isinstance(existing_web_search, dict) else None

    changes: list[str] = []
    target_path = "plugins.entries.xai.config.webSearch.apiKey"
    if web_search is None:
        config["webSearch"] = {"apiKey": auth}
        changes.append(f"Moved tools.web.x_search.apiKey to {target_path}.")
    elif "apiKey" not in web_search:
        web_search["apiKey"] = auth
        config["webSearch"] = web_search
        changes.append(
            "Merged tools.web.x_search.apiKey to "
            f"{target_path} (filled missing plugin auth)."
        )
    else:
        config["webSearch"] = web_search
        changes.append(f"Removed tools.web.x_search.apiKey ({target_path} already set).")

    if not legacy and not had_enabled:
        changes.append("Removed empty tools.web.x_search.")
    return changes


def _iter_legacy_web_search_provider_paths(payload: dict[str, Any]) -> list[str]:
    return (
        ["tools.web.search"]
        if _has_mapped_legacy_web_search_provider_config(payload)
        else []
    )


def _legacy_web_search_config(payload: dict[str, Any]) -> dict[str, Any] | None:
    tools = payload.get("tools")
    if not isinstance(tools, dict):
        return None
    web = tools.get("web")
    if not isinstance(web, dict):
        return None
    search = web.get("search")
    return search if isinstance(search, dict) else None


def _has_mapped_legacy_web_search_provider_config(payload: dict[str, Any]) -> bool:
    search = _legacy_web_search_config(payload)
    if search is None:
        return False
    if "apiKey" in search:
        return True
    return any(
        isinstance(search.get(provider_id), dict)
        for provider_id in _LEGACY_WEB_SEARCH_PROVIDER_IDS
    )


def _migrate_legacy_web_search_provider_config(payload: dict[str, Any]) -> list[str]:
    search = _legacy_web_search_config(payload)
    if search is None or not _has_mapped_legacy_web_search_provider_config(payload):
        return []

    tools = _ensure_config_record(payload, "tools")
    web = _ensure_config_record(tools, "web")
    next_search: dict[str, Any] = {}
    for key, value in search.items():
        if key == "apiKey":
            continue
        if (
            key in _LEGACY_WEB_SEARCH_PROVIDER_PLUGIN_IDS
            and isinstance(value, dict)
        ):
            continue
        if key in _LEGACY_WEB_SEARCH_MODERN_SCOPED_KEYS or not isinstance(value, dict):
            next_search[key] = copy.deepcopy(value)
    web["search"] = next_search

    changes: list[str] = []
    global_migration = _legacy_global_web_search_migration(search)
    if global_migration is not None:
        _migrate_plugin_web_search_config(
            payload,
            legacy_path=global_migration["legacyPath"],
            target_path=global_migration["targetPath"],
            plugin_id=global_migration["pluginId"],
            provider_config=global_migration["payload"],
            changes=changes,
        )

    for provider_id in _LEGACY_WEB_SEARCH_PROVIDER_IDS:
        if provider_id == _LEGACY_WEB_SEARCH_GLOBAL_PROVIDER_ID:
            continue
        scoped = search.get(provider_id)
        if not isinstance(scoped, dict) or not scoped:
            continue
        plugin_id = _LEGACY_WEB_SEARCH_PROVIDER_PLUGIN_IDS.get(provider_id)
        if not plugin_id:
            continue
        _migrate_plugin_web_search_config(
            payload,
            legacy_path=f"tools.web.search.{provider_id}",
            target_path=f"plugins.entries.{plugin_id}.config.webSearch",
            plugin_id=plugin_id,
            provider_config=copy.deepcopy(scoped),
            changes=changes,
        )
    return changes


def _legacy_global_web_search_migration(
    search: dict[str, Any],
) -> dict[str, Any] | None:
    provider_config = search.get(_LEGACY_WEB_SEARCH_GLOBAL_PROVIDER_ID)
    payload = copy.deepcopy(provider_config) if isinstance(provider_config, dict) else {}
    has_legacy_api_key = "apiKey" in search
    if has_legacy_api_key:
        payload["apiKey"] = copy.deepcopy(search.get("apiKey"))
    if not payload:
        return None
    plugin_id = _LEGACY_WEB_SEARCH_PROVIDER_PLUGIN_IDS[
        _LEGACY_WEB_SEARCH_GLOBAL_PROVIDER_ID
    ]
    return {
        "pluginId": plugin_id,
        "payload": payload,
        "legacyPath": (
            "tools.web.search.apiKey"
            if has_legacy_api_key
            else f"tools.web.search.{_LEGACY_WEB_SEARCH_GLOBAL_PROVIDER_ID}"
        ),
        "targetPath": (
            f"plugins.entries.{plugin_id}.config.webSearch.apiKey"
            if has_legacy_api_key and not isinstance(provider_config, dict)
            else f"plugins.entries.{plugin_id}.config.webSearch"
        ),
    }


def _migrate_plugin_web_search_config(
    payload: dict[str, Any],
    *,
    legacy_path: str,
    target_path: str,
    plugin_id: str,
    provider_config: dict[str, Any],
    changes: list[str],
) -> None:
    plugins = _ensure_config_record(payload, "plugins")
    entries = _ensure_config_record(plugins, "entries")
    entry = _ensure_config_record(entries, plugin_id)
    had_enabled = "enabled" in entry
    if not had_enabled:
        entry["enabled"] = True
    config = _ensure_config_record(entry, "config")
    existing = config.get("webSearch")
    if not isinstance(existing, dict):
        config["webSearch"] = copy.deepcopy(provider_config)
        changes.append(f"Moved {legacy_path} to {target_path}.")
        return

    merged = copy.deepcopy(existing)
    _merge_missing_config_values(merged, provider_config)
    config["webSearch"] = merged
    if merged != existing or not had_enabled:
        changes.append(
            f"Merged {legacy_path} to {target_path} "
            "(filled missing fields from legacy; kept explicit plugin config values)."
        )
        return
    changes.append(f"Removed {legacy_path} ({target_path} already set).")


def _ensure_config_record(container: dict[str, Any], key: str) -> dict[str, Any]:
    value = container.get(key)
    if isinstance(value, dict):
        return value
    created: dict[str, Any] = {}
    container[key] = created
    return created


def _iter_legacy_telegram_streaming_paths(payload: dict[str, Any]) -> list[str]:
    telegram = _legacy_channel_config(payload, "telegram")
    if telegram is None:
        return []
    paths: list[str] = []
    if _has_legacy_telegram_streaming_keys(telegram):
        paths.append("channels.telegram")
    accounts = telegram.get("accounts")
    if isinstance(accounts, dict):
        for account_id, account in accounts.items():
            if isinstance(account, dict) and _has_legacy_telegram_streaming_keys(account):
                paths.append(f"channels.telegram.accounts.{account_id}")
    return paths


def _iter_legacy_slack_streaming_paths(payload: dict[str, Any]) -> list[str]:
    slack = _legacy_channel_config(payload, "slack")
    if slack is None:
        return []
    paths: list[str] = []
    if _has_legacy_slack_streaming_keys(slack):
        paths.append("channels.slack")
    accounts = slack.get("accounts")
    if isinstance(accounts, dict):
        for account_id, account in accounts.items():
            if isinstance(account, dict) and _has_legacy_slack_streaming_keys(account):
                paths.append(f"channels.slack.accounts.{account_id}")
    return paths


def _iter_legacy_googlechat_stream_mode_paths(payload: dict[str, Any]) -> list[str]:
    googlechat = _legacy_channel_config(payload, "googlechat")
    if googlechat is None:
        return []
    paths: list[str] = []
    if _has_legacy_googlechat_stream_mode(googlechat):
        paths.append("channels.googlechat")
    accounts = googlechat.get("accounts")
    if isinstance(accounts, dict):
        for account_id, account in accounts.items():
            if isinstance(account, dict) and _has_legacy_googlechat_stream_mode(account):
                paths.append(f"channels.googlechat.accounts.{account_id}")
    return paths


def _iter_legacy_gateway_bind_alias_paths(payload: dict[str, Any]) -> list[str]:
    gateway = payload.get("gateway")
    if not isinstance(gateway, dict):
        return []
    return ["gateway.bind"] if _gateway_bind_alias_target(gateway.get("bind")) else []


def _iter_legacy_sandbox_per_session_paths(payload: dict[str, Any]) -> list[str]:
    agents = payload.get("agents")
    if not isinstance(agents, dict):
        return []
    paths: list[str] = []
    defaults = agents.get("defaults")
    if isinstance(defaults, dict):
        sandbox = defaults.get("sandbox")
        if isinstance(sandbox, dict) and "perSession" in sandbox:
            paths.append("agents.defaults.sandbox.perSession")
    agent_list = agents.get("list")
    if isinstance(agent_list, list):
        for index, agent in enumerate(agent_list):
            if not isinstance(agent, dict):
                continue
            sandbox = agent.get("sandbox")
            if isinstance(sandbox, dict) and "perSession" in sandbox:
                paths.append(f"agents.list.{index}.sandbox.perSession")
    return paths


def _iter_legacy_memory_search_paths(payload: dict[str, Any]) -> list[str]:
    return ["memorySearch"] if "memorySearch" in payload else []


def _iter_legacy_heartbeat_paths(payload: dict[str, Any]) -> list[str]:
    return ["heartbeat"] if "heartbeat" in payload else []


def _iter_legacy_tts_provider_paths(payload: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    messages = payload.get("messages")
    messages_tts = messages.get("tts") if isinstance(messages, dict) else None
    if isinstance(messages_tts, dict) and _has_legacy_tts_provider_keys(messages_tts):
        paths.append("messages.tts")

    plugins = payload.get("plugins")
    entries = plugins.get("entries") if isinstance(plugins, dict) else None
    if isinstance(entries, dict):
        for plugin_id, entry_value in entries.items():
            if plugin_id not in _LEGACY_TTS_PLUGIN_IDS or not isinstance(entry_value, dict):
                continue
            config = entry_value.get("config")
            tts = config.get("tts") if isinstance(config, dict) else None
            if isinstance(tts, dict) and _has_legacy_tts_provider_keys(tts):
                paths.append(f"plugins.entries.{plugin_id}.config.tts")
    return paths


def _has_legacy_tts_provider_keys(tts: dict[str, Any]) -> bool:
    return any(key in tts for key in _LEGACY_TTS_PROVIDER_KEYS)


def _legacy_channel_config(payload: dict[str, Any], channel: str) -> dict[str, Any] | None:
    channels = payload.get("channels")
    if not isinstance(channels, dict):
        return None
    value = channels.get(channel)
    return value if isinstance(value, dict) else None


def _has_legacy_telegram_streaming_keys(entry: dict[str, Any]) -> bool:
    return (
        "streamMode" in entry
        or isinstance(entry.get("streaming"), bool | str)
        or "chunkMode" in entry
        or "blockStreaming" in entry
        or "draftChunk" in entry
        or "blockStreamingCoalesce" in entry
    )


def _has_legacy_slack_streaming_keys(entry: dict[str, Any]) -> bool:
    return (
        "streamMode" in entry
        or isinstance(entry.get("streaming"), bool | str)
        or "chunkMode" in entry
        or "blockStreaming" in entry
        or "blockStreamingCoalesce" in entry
        or "nativeStreaming" in entry
    )


def _has_legacy_googlechat_stream_mode(entry: dict[str, Any]) -> bool:
    return "streamMode" in entry


def _migrate_legacy_telegram_streaming_keys(payload: dict[str, Any]) -> list[str]:
    telegram = _legacy_channel_config(payload, "telegram")
    if telegram is None:
        return []
    changes: list[str] = []
    _migrate_telegram_streaming_entry(
        telegram,
        path_label="channels.telegram",
        changes=changes,
    )
    accounts = telegram.get("accounts")
    if isinstance(accounts, dict):
        for account_id, account in accounts.items():
            if not isinstance(account, dict):
                continue
            _migrate_telegram_streaming_entry(
                account,
                path_label=f"channels.telegram.accounts.{account_id}",
                changes=changes,
            )
    return changes


def _migrate_telegram_streaming_entry(
    entry: dict[str, Any],
    *,
    path_label: str,
    changes: list[str],
) -> None:
    if not _has_legacy_telegram_streaming_keys(entry):
        return
    raw_streaming = entry.get("streaming")
    streaming = dict(raw_streaming) if isinstance(raw_streaming, dict) else {}
    has_streaming_record = isinstance(raw_streaming, dict)

    if "mode" not in streaming and (
        "streamMode" in entry or isinstance(raw_streaming, bool | str)
    ):
        mode = _resolve_telegram_streaming_mode(entry)
        streaming["mode"] = mode
        if "streamMode" in entry:
            changes.append(
                f"Moved {path_label}.streamMode to {path_label}.streaming.mode ({mode})."
            )
        elif isinstance(raw_streaming, bool):
            changes.append(
                f"Moved {path_label}.streaming (boolean) to "
                f"{path_label}.streaming.mode ({mode})."
            )
        elif isinstance(raw_streaming, str):
            changes.append(
                f"Moved {path_label}.streaming (scalar) to "
                f"{path_label}.streaming.mode ({mode})."
            )
    elif "streamMode" in entry or isinstance(raw_streaming, bool | str):
        changes.append(
            f"Removed legacy {path_label}.streaming mode aliases "
            f"({path_label}.streaming.mode already set)."
        )

    entry.pop("streamMode", None)
    if isinstance(raw_streaming, bool | str) and not has_streaming_record:
        entry["streaming"] = streaming

    if "chunkMode" in entry:
        if "chunkMode" not in streaming:
            streaming["chunkMode"] = entry["chunkMode"]
            changes.append(f"Moved {path_label}.chunkMode to {path_label}.streaming.chunkMode.")
        else:
            changes.append(
                f"Removed {path_label}.chunkMode "
                f"({path_label}.streaming.chunkMode already set)."
            )
        del entry["chunkMode"]

    raw_block = streaming.get("block")
    block = dict(raw_block) if isinstance(raw_block, dict) else {}
    if "blockStreaming" in entry:
        if "enabled" not in block:
            block["enabled"] = entry["blockStreaming"]
            changes.append(
                f"Moved {path_label}.blockStreaming to {path_label}.streaming.block.enabled."
            )
        else:
            changes.append(
                f"Removed {path_label}.blockStreaming "
                f"({path_label}.streaming.block.enabled already set)."
            )
        del entry["blockStreaming"]

    raw_preview = streaming.get("preview")
    preview = dict(raw_preview) if isinstance(raw_preview, dict) else {}
    if "draftChunk" in entry:
        if "chunk" not in preview:
            preview["chunk"] = entry["draftChunk"]
            changes.append(
                f"Moved {path_label}.draftChunk to {path_label}.streaming.preview.chunk."
            )
        else:
            changes.append(
                f"Removed {path_label}.draftChunk "
                f"({path_label}.streaming.preview.chunk already set)."
            )
        del entry["draftChunk"]

    if "blockStreamingCoalesce" in entry:
        if "coalesce" not in block:
            block["coalesce"] = entry["blockStreamingCoalesce"]
            changes.append(
                "Moved "
                f"{path_label}.blockStreamingCoalesce to "
                f"{path_label}.streaming.block.coalesce."
            )
        else:
            changes.append(
                f"Removed {path_label}.blockStreamingCoalesce "
                f"({path_label}.streaming.block.coalesce already set)."
            )
        del entry["blockStreamingCoalesce"]

    if block:
        streaming["block"] = block
    if preview:
        streaming["preview"] = preview
    if streaming:
        entry["streaming"] = streaming


def _migrate_legacy_googlechat_stream_mode(payload: dict[str, Any]) -> list[str]:
    googlechat = _legacy_channel_config(payload, "googlechat")
    if googlechat is None:
        return []
    changes: list[str] = []
    _migrate_googlechat_stream_mode_entry(
        googlechat,
        path_label="channels.googlechat",
        changes=changes,
    )
    accounts = googlechat.get("accounts")
    if isinstance(accounts, dict):
        for account_id, account in accounts.items():
            if not isinstance(account, dict):
                continue
            _migrate_googlechat_stream_mode_entry(
                account,
                path_label=f"channels.googlechat.accounts.{account_id}",
                changes=changes,
            )
    return changes


def _migrate_googlechat_stream_mode_entry(
    entry: dict[str, Any],
    *,
    path_label: str,
    changes: list[str],
) -> None:
    if "streamMode" not in entry:
        return
    del entry["streamMode"]
    changes.append(f"Removed {path_label}.streamMode (legacy key no longer used).")


def _migrate_legacy_audio_transcription(payload: dict[str, Any]) -> list[str]:
    audio = payload.get("audio")
    if not isinstance(audio, dict) or "transcription" not in audio:
        return []
    mapped = _map_legacy_audio_transcription(audio.get("transcription"))
    changes: list[str] = []
    if mapped is None:
        changes.append("Removed audio.transcription (invalid or empty command).")
    else:
        tools = _ensure_config_record(payload, "tools")
        media = _ensure_config_record(tools, "media")
        media_audio = _ensure_config_record(media, "audio")
        models = media_audio.get("models")
        if isinstance(models, list) and models:
            changes.append("Removed audio.transcription (tools.media.audio.models already set).")
        else:
            media_audio["enabled"] = True
            media_audio["models"] = [mapped]
            changes.append("Moved audio.transcription to tools.media.audio.models.")

    del audio["transcription"]
    if audio:
        payload["audio"] = audio
    else:
        payload.pop("audio", None)
    return changes


def _map_legacy_audio_transcription(value: object) -> dict[str, Any] | None:
    transcriber = value if isinstance(value, dict) else None
    command = transcriber.get("command") if transcriber is not None else None
    if not isinstance(command, list) or not command:
        return None
    if not all(isinstance(part, str) for part in command):
        return None
    executable = command[0].strip()
    if not _is_safe_executable_value(executable):
        return None
    mapped: dict[str, Any] = {"command": executable, "type": "cli"}
    args = command[1:]
    if args:
        mapped["args"] = args
    timeout = transcriber.get("timeoutSeconds") if transcriber is not None else None
    if isinstance(timeout, int | float) and not isinstance(timeout, bool):
        mapped["timeoutSeconds"] = timeout
    return mapped


def _is_safe_executable_value(value: str) -> bool:
    trimmed = value.strip()
    if not trimmed or "\0" in trimmed:
        return False
    if _EXEC_CONTROL_CHARS_PATTERN.search(trimmed):
        return False
    if _SHELL_METACHARS_PATTERN.search(trimmed):
        return False
    if _EXEC_QUOTE_CHARS_PATTERN.search(trimmed):
        return False
    if _is_likely_executable_path(trimmed):
        return True
    if trimmed.startswith("-"):
        return False
    return bool(_EXEC_BARE_NAME_PATTERN.fullmatch(trimmed))


def _is_likely_executable_path(value: str) -> bool:
    return (
        value.startswith(".")
        or value.startswith("~")
        or "/" in value
        or "\\" in value
        or bool(_EXEC_WINDOWS_DRIVE_PATTERN.match(value))
    )


def _migrate_legacy_sandbox_per_session(payload: dict[str, Any]) -> list[str]:
    agents = payload.get("agents")
    if not isinstance(agents, dict):
        return []
    changes: list[str] = []
    defaults = agents.get("defaults")
    if isinstance(defaults, dict):
        sandbox = defaults.get("sandbox")
        if isinstance(sandbox, dict):
            _migrate_sandbox_per_session_at(
                sandbox,
                path_label="agents.defaults.sandbox",
                changes=changes,
            )

    agent_list = agents.get("list")
    if isinstance(agent_list, list):
        for index, agent in enumerate(agent_list):
            if not isinstance(agent, dict):
                continue
            sandbox = agent.get("sandbox")
            if not isinstance(sandbox, dict):
                continue
            _migrate_sandbox_per_session_at(
                sandbox,
                path_label=f"agents.list.{index}.sandbox",
                changes=changes,
            )
    return changes


def _migrate_sandbox_per_session_at(
    sandbox: dict[str, Any],
    *,
    path_label: str,
    changes: list[str],
) -> None:
    if "perSession" not in sandbox:
        return
    raw_per_session = sandbox.get("perSession")
    if not isinstance(raw_per_session, bool):
        return
    if "scope" not in sandbox:
        scope = "session" if raw_per_session else "shared"
        sandbox["scope"] = scope
        changes.append(f"Moved {path_label}.perSession to {path_label}.scope ({scope}).")
    else:
        changes.append(f"Removed {path_label}.perSession ({path_label}.scope already set).")
    del sandbox["perSession"]


def _migrate_legacy_memory_search(payload: dict[str, Any]) -> list[str]:
    legacy_memory_search = payload.get("memorySearch")
    if not isinstance(legacy_memory_search, dict):
        return []
    agents = _ensure_config_record(payload, "agents")
    defaults = _ensure_config_record(agents, "defaults")
    existing = defaults.get("memorySearch")
    if not isinstance(existing, dict):
        defaults["memorySearch"] = legacy_memory_search
        changes = ["Moved memorySearch to agents.defaults.memorySearch."]
    else:
        merged = copy.deepcopy(existing)
        _merge_missing_config_values(merged, legacy_memory_search)
        defaults["memorySearch"] = merged
        changes = [
            "Merged memorySearch to agents.defaults.memorySearch "
            "(filled missing fields from legacy; kept explicit agents.defaults values)."
        ]
    del payload["memorySearch"]
    return changes


def _merge_missing_config_values(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if key not in target:
            target[key] = copy.deepcopy(value)
            continue
        existing = target[key]
        if isinstance(existing, dict) and isinstance(value, dict):
            _merge_missing_config_values(existing, value)


def _migrate_legacy_heartbeat(payload: dict[str, Any]) -> list[str]:
    legacy_heartbeat = payload.get("heartbeat")
    if not isinstance(legacy_heartbeat, dict):
        return []
    agent_heartbeat, channel_heartbeat = _split_legacy_heartbeat(legacy_heartbeat)
    changes: list[str] = []
    if agent_heartbeat:
        _merge_legacy_record_into_defaults(
            payload,
            root_key="agents",
            field_key="heartbeat",
            legacy_value=agent_heartbeat,
            changes=changes,
            moved_message="Moved heartbeat to agents.defaults.heartbeat.",
            merged_message=(
                "Merged heartbeat to agents.defaults.heartbeat "
                "(filled missing fields from legacy; kept explicit agents.defaults values)."
            ),
        )
    if channel_heartbeat:
        _merge_legacy_record_into_defaults(
            payload,
            root_key="channels",
            field_key="heartbeat",
            legacy_value=channel_heartbeat,
            changes=changes,
            moved_message="Moved heartbeat visibility to channels.defaults.heartbeat.",
            merged_message=(
                "Merged heartbeat visibility to channels.defaults.heartbeat "
                "(filled missing fields from legacy; kept explicit channels.defaults values)."
            ),
        )
    if not agent_heartbeat and not channel_heartbeat:
        changes.append("Removed empty top-level heartbeat.")
    del payload["heartbeat"]
    return changes


def _split_legacy_heartbeat(
    legacy_heartbeat: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    agent_heartbeat: dict[str, Any] = {}
    channel_heartbeat: dict[str, Any] = {}
    for key, value in legacy_heartbeat.items():
        if key in _CHANNEL_HEARTBEAT_KEYS:
            channel_heartbeat[key] = value
        elif key in _AGENT_HEARTBEAT_KEYS:
            agent_heartbeat[key] = value
        else:
            agent_heartbeat[key] = value
    return agent_heartbeat, channel_heartbeat


def _merge_legacy_record_into_defaults(
    payload: dict[str, Any],
    *,
    root_key: str,
    field_key: str,
    legacy_value: dict[str, Any],
    changes: list[str],
    moved_message: str,
    merged_message: str,
) -> None:
    root = _ensure_config_record(payload, root_key)
    defaults = _ensure_config_record(root, "defaults")
    existing = defaults.get(field_key)
    if not isinstance(existing, dict):
        defaults[field_key] = legacy_value
        changes.append(moved_message)
        return
    merged = copy.deepcopy(existing)
    _merge_missing_config_values(merged, legacy_value)
    defaults[field_key] = merged
    changes.append(merged_message)


def _migrate_legacy_tts_provider_config(payload: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    messages = payload.get("messages")
    messages_tts = messages.get("tts") if isinstance(messages, dict) else None
    if isinstance(messages_tts, dict):
        _migrate_legacy_tts_config_at(
            messages_tts,
            path_label="messages.tts",
            changes=changes,
        )

    plugins = payload.get("plugins")
    entries = plugins.get("entries") if isinstance(plugins, dict) else None
    if isinstance(entries, dict):
        for plugin_id, entry_value in entries.items():
            if plugin_id not in _LEGACY_TTS_PLUGIN_IDS or not isinstance(entry_value, dict):
                continue
            config = entry_value.get("config")
            tts = config.get("tts") if isinstance(config, dict) else None
            if not isinstance(tts, dict):
                continue
            _migrate_legacy_tts_config_at(
                tts,
                path_label=f"plugins.entries.{plugin_id}.config.tts",
                changes=changes,
            )
    return changes


def _migrate_legacy_tts_config_at(
    tts: dict[str, Any],
    *,
    path_label: str,
    changes: list[str],
) -> None:
    for legacy_key in _LEGACY_TTS_PROVIDER_KEYS:
        provider_id = _LEGACY_TTS_PROVIDER_TARGETS[legacy_key]
        legacy_value = tts.get(legacy_key)
        if not isinstance(legacy_value, dict):
            continue
        providers = _ensure_config_record(tts, "providers")
        existing = providers.get(provider_id)
        merged = copy.deepcopy(existing) if isinstance(existing, dict) else {}
        _merge_missing_config_values(merged, legacy_value)
        providers[provider_id] = merged
        del tts[legacy_key]
        changes.append(f"Moved {path_label}.{legacy_key} to {path_label}.providers.{provider_id}.")


def _migrate_gateway_control_ui_allowed_origins(payload: dict[str, Any]) -> list[str]:
    gateway = payload.get("gateway")
    if not isinstance(gateway, dict) or not _is_gateway_non_loopback_bind_mode(
        gateway.get("bind")
    ):
        return []
    control_ui = gateway.get("controlUi")
    next_control_ui = dict(control_ui) if isinstance(control_ui, dict) else {}
    if _has_configured_control_ui_allowed_origins(next_control_ui):
        return []
    port = _resolve_gateway_port_with_default(gateway.get("port"))
    origins = _build_default_control_ui_allowed_origins(
        port=port,
        bind=gateway.get("bind"),
        custom_bind_host=gateway.get("customBindHost"),
    )
    next_control_ui["allowedOrigins"] = origins
    gateway["controlUi"] = next_control_ui
    return [
        "Seeded gateway.controlUi.allowedOrigins "
        f"{json.dumps(origins)} for bind={gateway.get('bind')}. "
        "Required since v2026.2.26. Add other machine origins to "
        "gateway.controlUi.allowedOrigins if needed."
    ]


def _migrate_legacy_gateway_bind_alias(payload: dict[str, Any]) -> list[str]:
    gateway = payload.get("gateway")
    if not isinstance(gateway, dict):
        return []
    raw_bind = gateway.get("bind")
    mapped = _gateway_bind_alias_target(raw_bind)
    if mapped is None:
        return []
    gateway["bind"] = mapped
    return [f'Normalized gateway.bind "{_escape_control_for_log(raw_bind)}" to "{mapped}".']


def _is_gateway_non_loopback_bind_mode(value: object) -> bool:
    return value in {"lan", "tailnet", "custom", "auto"}


def _has_configured_control_ui_allowed_origins(control_ui: dict[str, Any]) -> bool:
    if control_ui.get("dangerouslyAllowHostHeaderOriginFallback") is True:
        return True
    allowed_origins = control_ui.get("allowedOrigins")
    return isinstance(allowed_origins, list) and any(
        isinstance(origin, str) and bool(origin.strip()) for origin in allowed_origins
    )


def _resolve_gateway_port_with_default(value: object) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value.is_integer() and value > 0:
        return int(value)
    return _OPENCLAW_DEFAULT_GATEWAY_PORT


def _build_default_control_ui_allowed_origins(
    *,
    port: int,
    bind: object,
    custom_bind_host: object,
) -> list[str]:
    origins = [
        f"http://localhost:{port}",
        f"http://127.0.0.1:{port}",
    ]
    if bind == "custom" and isinstance(custom_bind_host, str):
        trimmed = custom_bind_host.strip()
        if trimmed:
            origins.append(f"http://{trimmed}:{port}")
    return origins


def _gateway_bind_alias_target(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in {"0.0.0.0", "::", "[::]", "*"}:
        return "lan"
    if normalized in {"127.0.0.1", "localhost", "::1", "[::1]"}:
        return "loopback"
    return None


def _escape_control_for_log(value: object) -> str:
    text = str(value)
    return text.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")


def _migrate_legacy_slack_streaming_keys(payload: dict[str, Any]) -> list[str]:
    slack = _legacy_channel_config(payload, "slack")
    if slack is None:
        return []
    changes: list[str] = []
    _migrate_slack_streaming_entry(
        slack,
        path_label="channels.slack",
        changes=changes,
    )
    accounts = slack.get("accounts")
    if isinstance(accounts, dict):
        for account_id, account in accounts.items():
            if not isinstance(account, dict):
                continue
            _migrate_slack_streaming_entry(
                account,
                path_label=f"channels.slack.accounts.{account_id}",
                changes=changes,
            )
    return changes


def _migrate_slack_streaming_entry(
    entry: dict[str, Any],
    *,
    path_label: str,
    changes: list[str],
) -> None:
    if not _has_legacy_slack_streaming_keys(entry):
        return
    raw_streaming = entry.get("streaming")
    raw_native_streaming = entry.get("nativeStreaming")
    streaming = dict(raw_streaming) if isinstance(raw_streaming, dict) else {}
    has_streaming_record = isinstance(raw_streaming, dict)

    if "mode" not in streaming and (
        "streamMode" in entry or isinstance(raw_streaming, bool | str)
    ):
        mode = _resolve_slack_streaming_mode(entry)
        streaming["mode"] = mode
        if "streamMode" in entry:
            changes.append(
                f"Moved {path_label}.streamMode to {path_label}.streaming.mode ({mode})."
            )
        if isinstance(raw_streaming, bool):
            changes.append(
                f"Moved {path_label}.streaming (boolean) to "
                f"{path_label}.streaming.mode ({mode})."
            )
        elif isinstance(raw_streaming, str):
            changes.append(
                f"Moved {path_label}.streaming (scalar) to "
                f"{path_label}.streaming.mode ({mode})."
            )
    elif "streamMode" in entry or isinstance(raw_streaming, bool | str):
        changes.append(
            f"Removed legacy {path_label}.streaming mode aliases "
            f"({path_label}.streaming.mode already set)."
        )

    entry.pop("streamMode", None)
    if isinstance(raw_streaming, bool | str) and not has_streaming_record:
        entry["streaming"] = streaming

    if "chunkMode" in entry:
        if "chunkMode" not in streaming:
            streaming["chunkMode"] = entry["chunkMode"]
            changes.append(f"Moved {path_label}.chunkMode to {path_label}.streaming.chunkMode.")
        else:
            changes.append(
                f"Removed {path_label}.chunkMode "
                f"({path_label}.streaming.chunkMode already set)."
            )
        del entry["chunkMode"]

    raw_block = streaming.get("block")
    block = dict(raw_block) if isinstance(raw_block, dict) else {}
    if "blockStreaming" in entry:
        if "enabled" not in block:
            block["enabled"] = entry["blockStreaming"]
            changes.append(
                f"Moved {path_label}.blockStreaming to {path_label}.streaming.block.enabled."
            )
        else:
            changes.append(
                f"Removed {path_label}.blockStreaming "
                f"({path_label}.streaming.block.enabled already set)."
            )
        del entry["blockStreaming"]

    if "blockStreamingCoalesce" in entry:
        if "coalesce" not in block:
            block["coalesce"] = entry["blockStreamingCoalesce"]
            changes.append(
                "Moved "
                f"{path_label}.blockStreamingCoalesce to "
                f"{path_label}.streaming.block.coalesce."
            )
        else:
            changes.append(
                f"Removed {path_label}.blockStreamingCoalesce "
                f"({path_label}.streaming.block.coalesce already set)."
            )
        del entry["blockStreamingCoalesce"]

    if "nativeStreaming" in entry:
        if "nativeTransport" not in streaming:
            streaming["nativeTransport"] = _resolve_slack_native_transport(
                native_streaming=raw_native_streaming,
                streaming=raw_streaming,
            )
            changes.append(
                f"Moved {path_label}.nativeStreaming to "
                f"{path_label}.streaming.nativeTransport."
            )
        else:
            changes.append(
                f"Removed {path_label}.nativeStreaming "
                f"({path_label}.streaming.nativeTransport already set)."
            )
        del entry["nativeStreaming"]
    elif isinstance(raw_streaming, bool) and "nativeTransport" not in streaming:
        streaming["nativeTransport"] = _resolve_slack_native_transport(
            native_streaming=None,
            streaming=raw_streaming,
        )
        changes.append(
            f"Moved {path_label}.streaming (boolean) to "
            f"{path_label}.streaming.nativeTransport."
        )

    if block:
        streaming["block"] = block
    if streaming:
        entry["streaming"] = streaming


def _resolve_telegram_streaming_mode(entry: dict[str, Any]) -> str:
    raw_streaming = entry.get("streaming")
    streaming_mode = _parse_telegram_streaming_mode(raw_streaming)
    if streaming_mode is not None:
        return streaming_mode
    stream_mode = _parse_telegram_streaming_mode(entry.get("streamMode"))
    if stream_mode is not None:
        return stream_mode
    if isinstance(raw_streaming, bool):
        return "partial" if raw_streaming else "off"
    return "partial"


def _parse_telegram_streaming_mode(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized == "progress":
        return "partial"
    if normalized in {"off", "partial", "block"}:
        return normalized
    return None


def _resolve_slack_streaming_mode(entry: dict[str, Any]) -> str:
    raw_streaming = entry.get("streaming")
    streaming_mode = _parse_slack_streaming_mode(raw_streaming)
    if streaming_mode is not None:
        return streaming_mode
    stream_mode = _parse_slack_legacy_stream_mode(entry.get("streamMode"))
    if stream_mode is not None:
        return stream_mode
    if isinstance(raw_streaming, bool):
        return "partial" if raw_streaming else "off"
    return "partial"


def _parse_slack_streaming_mode(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in {"off", "partial", "block", "progress"}:
        return normalized
    return None


def _parse_slack_legacy_stream_mode(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized == "append":
        return "block"
    if normalized == "status_final":
        return "progress"
    if normalized == "replace":
        return "partial"
    return None


def _resolve_slack_native_transport(
    *,
    native_streaming: object,
    streaming: object,
) -> bool:
    if isinstance(native_streaming, bool):
        return native_streaming
    if isinstance(streaming, bool):
        return streaming
    return True
