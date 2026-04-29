from __future__ import annotations

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
    model = dict(raw_model) if isinstance(raw_model, dict) else {}
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
    )
    if any(snapshot.get(section) is None for section in omitted_null_sections):
        snapshot = dict(snapshot)
        for section in omitted_null_sections:
            if snapshot.get(section) is None:
                snapshot.pop(section, None)
    return snapshot
