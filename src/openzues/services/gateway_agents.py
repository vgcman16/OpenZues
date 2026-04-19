from __future__ import annotations

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
            ],
        }

    async def get_identity(
        self,
        *,
        agent_id: str | None,
        session_key: str | None,
    ) -> dict[str, Any]:
        resolved_agent_id = self._resolve_requested_agent_id(
            agent_id=agent_id,
            session_key=session_key,
        )
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

    def _resolve_requested_agent_id(
        self,
        *,
        agent_id: str | None,
        session_key: str | None,
    ) -> str:
        requested_agent_id = None
        if agent_id is not None and agent_id.strip():
            requested_agent_id = self._canonical_agent_id(agent_id)
        session_agent_id = self._agent_id_from_session_key(session_key)
        if (
            requested_agent_id is not None
            and session_agent_id is not None
            and requested_agent_id != session_agent_id
        ):
            raise ValueError("agentId does not match sessionKey")
        return requested_agent_id or session_agent_id or DEFAULT_AGENT_ID

    def _agent_id_from_session_key(self, session_key: str | None) -> str | None:
        raw_session_key = str(session_key or "").strip()
        if not raw_session_key:
            return None
        parsed_session_key = parse_agent_session_key(raw_session_key)
        if raw_session_key.lower().startswith("agent:") and parsed_session_key is None:
            raise ValueError("sessionKey is malformed")
        if parsed_session_key is None:
            return DEFAULT_AGENT_ID
        return self._canonical_agent_id(parsed_session_key.agent_id)

    def _canonical_agent_id(self, agent_id: str) -> str:
        normalized_agent_id = agent_id.strip().lower()
        if normalized_agent_id not in _ALLOWED_AGENT_IDS:
            raise ValueError("unknown agent id")
        return DEFAULT_AGENT_ID

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
