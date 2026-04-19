from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _default_codex_home() -> Path:
    configured = os.getenv("CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex"


def _normalize_secret_input(value: str) -> str:
    return "".join(ch for ch in value if ch not in {"\r", "\n"}).strip()


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
        try:
            payload = json.loads(self._config_path().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
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

    def _config_path(self) -> Path:
        return self.workspace_root / ".codex" / "gateway-skill-config.json"

    def _write_entries(self, entries: dict[str, dict[str, Any]]) -> None:
        path = self._config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"skills": {"entries": entries}}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
