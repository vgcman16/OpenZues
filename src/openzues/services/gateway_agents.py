from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from openzues.database import Database
from openzues.services.session_keys import (
    DEFAULT_AGENT_ID,
    DEFAULT_MAIN_KEY,
    parse_agent_session_key,
)

_ALLOWED_AGENT_IDS = {"main", "openzues"}
_DEFAULT_AGENT_NAME = "OpenZues"
_DEFAULT_AGENT_AVATAR = "/static/favicon.svg"
_DEFAULT_MODEL = "gpt-5.4"
_INVALID_AGENT_ID_CHARS_RE = re.compile(r"[^a-z0-9_-]+")
_VALID_AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.IGNORECASE)


class GatewayAgentsService:
    def __init__(
        self,
        *,
        database: Database | None = None,
        workspace_dir: Path | str | None = None,
    ) -> None:
        self._database = database
        self._workspace_dir = Path(workspace_dir) if workspace_dir is not None else None

    async def list_agents(self) -> dict[str, Any]:
        workspace_dir = await self._resolve_workspace_dir()
        custom_agents = await self._list_custom_agents()
        return {
            "defaultId": DEFAULT_AGENT_ID,
            "mainKey": DEFAULT_MAIN_KEY,
            "scope": "global",
            "agents": [
                {
                    "id": DEFAULT_AGENT_ID,
                    "name": _DEFAULT_AGENT_NAME,
                    "identity": self._identity_summary(),
                    "workspace": str(workspace_dir),
                    "model": {"primary": await self._resolve_primary_model()},
                }
            ]
            + custom_agents,
        }

    async def create_agent(
        self,
        *,
        name: str,
        workspace: str,
        model: str | None,
        emoji: str | None,
        avatar: str | None,
    ) -> dict[str, Any]:
        if self._database is None:
            raise RuntimeError("agent registry unavailable")
        safe_name = _sanitize_identity_line(name)
        agent_id = _normalize_agent_id(safe_name)
        if agent_id == DEFAULT_AGENT_ID:
            raise ValueError(f'"{DEFAULT_AGENT_ID}" is reserved')
        workspace_dir = Path(workspace).expanduser()
        workspace_dir.mkdir(parents=True, exist_ok=True)
        await _write_identity_file(
            workspace_dir,
            name=safe_name,
            emoji=_optional_clean_identity_line(emoji),
            avatar=_optional_clean_identity_line(avatar),
        )
        row = await self._database.create_gateway_agent(
            agent_id=agent_id,
            name=safe_name,
            workspace=str(workspace_dir),
            model=_optional_clean_identity_line(model),
            emoji=_optional_clean_identity_line(emoji),
            avatar=_optional_clean_identity_line(avatar),
        )
        return {
            "ok": True,
            "agentId": row["agent_id"],
            "name": row["name"],
            "workspace": row["workspace"],
            "model": row["model"],
        }

    async def update_agent(
        self,
        *,
        agent_id: str,
        name: str | None,
        workspace: str | None,
        model: str | None,
        emoji: str | None,
        avatar: str | None,
    ) -> dict[str, Any]:
        if self._database is None:
            raise RuntimeError("agent registry unavailable")
        normalized_agent_id = _normalize_agent_id(agent_id)
        if normalized_agent_id == DEFAULT_AGENT_ID:
            raise ValueError(f'agent "{normalized_agent_id}" not found')
        existing = await self._database.get_gateway_agent(normalized_agent_id)
        if existing is None:
            raise ValueError(f'agent "{normalized_agent_id}" not found')
        safe_name = _optional_clean_identity_line(name)
        workspace_dir = Path(workspace).expanduser() if workspace is not None else None
        if workspace_dir is not None:
            workspace_dir.mkdir(parents=True, exist_ok=True)
        row = await self._database.update_gateway_agent(
            agent_id=normalized_agent_id,
            name=safe_name,
            workspace=str(workspace_dir) if workspace_dir is not None else None,
            model=_optional_clean_identity_line(model),
            emoji=_optional_clean_identity_line(emoji),
            avatar=_optional_clean_identity_line(avatar),
        )
        if row is None:
            raise ValueError(f'agent "{normalized_agent_id}" not found')
        identity_workspace = Path(str(row["workspace"]))
        identity_workspace.mkdir(parents=True, exist_ok=True)
        await _write_identity_file(
            identity_workspace,
            name=str(row["name"]),
            emoji=_string_or_none(row.get("emoji")),
            avatar=_string_or_none(row.get("avatar")),
        )
        return {"ok": True, "agentId": normalized_agent_id}

    async def delete_agent(
        self,
        *,
        agent_id: str,
        delete_files: bool,
    ) -> dict[str, Any]:
        del delete_files
        if self._database is None:
            raise RuntimeError("agent registry unavailable")
        normalized_agent_id = _normalize_agent_id(agent_id)
        if normalized_agent_id == DEFAULT_AGENT_ID:
            raise ValueError(f'"{DEFAULT_AGENT_ID}" cannot be deleted')
        deleted = await self._database.delete_gateway_agent(normalized_agent_id)
        if deleted is None:
            raise ValueError(f'agent "{normalized_agent_id}" not found')
        return {"ok": True, "agentId": normalized_agent_id, "removedBindings": []}

    async def agent_exists(self, agent_id: str | None) -> bool:
        normalized_agent_id = _normalize_agent_id(agent_id or DEFAULT_AGENT_ID)
        if normalized_agent_id in _ALLOWED_AGENT_IDS:
            return True
        if self._database is None:
            return False
        return await self._database.get_gateway_agent(normalized_agent_id) is not None

    async def get_identity(
        self,
        *,
        agent_id: str | None,
        session_key: str | None,
    ) -> dict[str, Any]:
        resolved_agent_id = await self._resolve_requested_agent_id(
            agent_id=agent_id,
            session_key=session_key,
        )
        if resolved_agent_id != DEFAULT_AGENT_ID:
            if self._database is None:
                raise ValueError("unknown agent id")
            row = await self._database.get_gateway_agent(resolved_agent_id)
            if row is None:
                raise ValueError("unknown agent id")
            return {
                "agentId": row["agent_id"],
                "name": row["name"],
                "avatar": _string_or_none(row.get("avatar")),
                "emoji": _string_or_none(row.get("emoji")),
            }
        return {
            "agentId": resolved_agent_id,
            "name": _DEFAULT_AGENT_NAME,
            "avatar": _DEFAULT_AGENT_AVATAR,
            "emoji": None,
        }

    async def _resolve_workspace_dir(self) -> Path:
        if self._workspace_dir is not None:
            return self._workspace_dir
        bootstrap = await self._load_bootstrap()
        default_cwd = str((bootstrap or {}).get("default_cwd") or "").strip()
        if default_cwd:
            return Path(default_cwd)
        preferred_project_id = _int_or_none((bootstrap or {}).get("preferred_project_id"))
        if preferred_project_id is not None and self._database is not None:
            project = await self._database.get_project(preferred_project_id)
            project_path = str((project or {}).get("path") or "").strip()
            if project_path:
                return Path(project_path)
        return Path.cwd()

    async def _resolve_primary_model(self) -> str:
        bootstrap = await self._load_bootstrap()
        model = str((bootstrap or {}).get("model") or "").strip()
        return model or _DEFAULT_MODEL

    async def _load_bootstrap(self) -> dict[str, Any] | None:
        if self._database is None:
            return None
        return await self._database.get_gateway_bootstrap()

    async def _list_custom_agents(self) -> list[dict[str, Any]]:
        if self._database is None:
            return []
        rows = await self._database.list_gateway_agents()
        return [_agent_payload(row) for row in rows]

    async def _resolve_requested_agent_id(
        self,
        *,
        agent_id: str | None,
        session_key: str | None,
    ) -> str:
        requested_agent_id = None
        if agent_id is not None and agent_id.strip():
            requested_agent_id = await self._canonical_agent_id(agent_id)
        session_agent_id = await self._agent_id_from_session_key(session_key)
        if (
            requested_agent_id is not None
            and session_agent_id is not None
            and requested_agent_id != session_agent_id
        ):
            raise ValueError("agentId does not match sessionKey")
        return requested_agent_id or session_agent_id or DEFAULT_AGENT_ID

    async def _agent_id_from_session_key(self, session_key: str | None) -> str | None:
        raw_session_key = str(session_key or "").strip()
        if not raw_session_key:
            return None
        parsed_session_key = parse_agent_session_key(raw_session_key)
        if raw_session_key.lower().startswith("agent:") and parsed_session_key is None:
            raise ValueError("sessionKey is malformed")
        if parsed_session_key is None:
            return DEFAULT_AGENT_ID
        return await self._canonical_agent_id(parsed_session_key.agent_id)

    async def _canonical_agent_id(self, agent_id: str) -> str:
        normalized_agent_id = agent_id.strip().lower()
        if normalized_agent_id in _ALLOWED_AGENT_IDS:
            return DEFAULT_AGENT_ID
        if self._database is None:
            raise ValueError("unknown agent id")
        row = await self._database.get_gateway_agent(normalized_agent_id)
        if row is None:
            raise ValueError("unknown agent id")
        return str(row["agent_id"])

    def _identity_summary(self) -> dict[str, Any]:
        return {
            "name": _DEFAULT_AGENT_NAME,
            "avatar": _DEFAULT_AGENT_AVATAR,
            "avatarUrl": _DEFAULT_AGENT_AVATAR,
            "emoji": None,
        }


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _normalize_agent_id(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return DEFAULT_AGENT_ID
    lowered = trimmed.lower()
    if _VALID_AGENT_ID_RE.match(trimmed):
        return lowered
    normalized = _INVALID_AGENT_ID_CHARS_RE.sub("-", lowered).strip("-")
    return (normalized[:64] or DEFAULT_AGENT_ID)


def _sanitize_identity_line(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ").strip()


def _optional_clean_identity_line(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _sanitize_identity_line(value)
    return cleaned or None


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _agent_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["agent_id"],
        "name": row["name"],
        "identity": {
            "name": row["name"],
            "avatar": row.get("avatar"),
            "avatarUrl": row.get("avatar"),
            "emoji": row.get("emoji"),
        },
        "workspace": row["workspace"],
        "model": {"primary": row.get("model") or _DEFAULT_MODEL},
    }


async def _write_identity_file(
    workspace_dir: Path,
    *,
    name: str,
    emoji: str | None,
    avatar: str | None,
) -> None:
    lines = [
        "# Identity",
        "",
        f"Name: {name}",
    ]
    if emoji:
        lines.append(f"Emoji: {emoji}")
    if avatar:
        lines.append(f"Avatar: {avatar}")
    (workspace_dir / "IDENTITY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
