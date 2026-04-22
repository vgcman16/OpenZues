from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

_PATH_INDEX_RE = re.compile(r"\[(\d+)\]")


def _default_codex_home() -> Path:
    configured = os.getenv("CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex"


def _normalize_secret_input(value: str) -> str:
    return "".join(ch for ch in value if ch not in {"\r", "\n"}).strip()


def _is_truthy(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _resolve_config_path(payload: object, path: str) -> object:
    normalized_path = _PATH_INDEX_RE.sub(r".\1", path.strip())
    current: object = payload
    for segment in normalized_path.split("."):
        if not segment:
            continue
        if isinstance(current, list) and segment.isdigit():
            index = int(segment)
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        if not isinstance(current, dict):
            return None
        if segment not in current:
            return None
        current = current[segment]
    return current


class GatewaySkillConfigService:
    def __init__(
        self,
        *,
        codex_home: Path | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self.codex_home = (codex_home or _default_codex_home()).expanduser()
        self.workspace_root = (workspace_root or Path.cwd()).expanduser()

    def load_entries(self) -> dict[str, dict[str, Any]]:
        payload = self.load_payload()
        skills = payload.get("skills") if isinstance(payload, dict) else None
        entries = skills.get("entries") if isinstance(skills, dict) else None
        if not isinstance(entries, dict):
            return {}
        resolved: dict[str, dict[str, Any]] = {}
        for key, value in entries.items():
            skill_key = str(key or "").strip()
            if not skill_key or not isinstance(value, dict):
                continue
            resolved[skill_key] = dict(value)
        return resolved

    def load_payload(self) -> dict[str, Any]:
        try:
            payload = json.loads(self._config_path().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def update_entry(
        self,
        *,
        skill_key: str,
        enabled: bool | None,
        api_key: str | None,
        env: dict[str, str] | None,
    ) -> dict[str, Any]:
        entries = self.load_entries()
        current = dict(entries.get(skill_key) or {})
        if enabled is not None:
            current["enabled"] = enabled
        if api_key is not None:
            normalized_api_key = _normalize_secret_input(api_key)
            if normalized_api_key:
                current["apiKey"] = normalized_api_key
            else:
                current.pop("apiKey", None)
        if env is not None:
            current_env = current.get("env")
            next_env = dict(current_env) if isinstance(current_env, dict) else {}
            for raw_key, raw_value in env.items():
                normalized_key = str(raw_key or "").strip()
                if not normalized_key:
                    continue
                normalized_value = str(raw_value or "").strip()
                if normalized_value:
                    next_env[normalized_key] = normalized_value
                else:
                    next_env.pop(normalized_key, None)
            current["env"] = next_env
        entries[skill_key] = current
        self._write_entries(entries)
        return current

    def is_config_path_truthy(
        self,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        resolved_payload = payload if payload is not None else self.load_payload()
        return _is_truthy(_resolve_config_path(resolved_payload, path))

    def _config_path(self) -> Path:
        return self.workspace_root / ".codex" / "gateway-skill-config.json"

    def _write_entries(self, entries: dict[str, dict[str, Any]]) -> None:
        path = self._config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"skills": {"entries": entries}}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
