from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_hermes_source_path() -> Path | None:
    candidate = Path(__file__).resolve().parents[2].with_name("hermes-agent-main")
    if candidate.exists():
        return candidate
    return None


def _default_ecc_source_path() -> Path | None:
    candidate = Path(__file__).resolve().parents[2].with_name("everything-claude-code-main")
    if candidate.exists():
        return candidate
    return None


class Settings(BaseSettings):
    app_name: str = "OpenZues"
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = Field(default_factory=lambda: Path.cwd() / ".openzues")
    db_path: Path | None = None
    master_key: str | None = None
    master_key_path: Path | None = None
    default_codex_command: str = "codex"
    default_codex_args: str = "app-server"
    desktop_approval_policy: str | None = "never"
    desktop_sandbox_mode: str | None = Field(
        default_factory=lambda: (
            "danger-full-access" if sys.platform.startswith("win") else "workspace-write"
        )
    )
    cron_webhook_url: str | None = None
    cron_webhook_token: str | None = None
    cron_failure_alert: dict[str, Any] | None = None
    attention_queue_enabled: bool = True
    attention_queue_poll_interval_seconds: int = 30
    websocket_ping_interval_seconds: int = 20
    auto_self_update_enabled: bool = True
    auto_self_update_poll_interval_seconds: int = 20
    apns_team_id: str | None = None
    apns_key_id: str | None = None
    apns_private_key_p8: str | None = None
    apns_private_key_path: Path | None = None
    apns_timeout_ms: int = 10_000
    apns_relay_base_url: str | None = None
    apns_relay_timeout_ms: int = 10_000
    apns_relay_allow_http: bool = False
    gateway_node_allow_commands: tuple[str, ...] = ()
    gateway_node_deny_commands: tuple[str, ...] = ()
    hermes_learning_poll_interval_seconds: int = 300
    hermes_source_path: Path | None = Field(default_factory=_default_hermes_source_path)
    ecc_source_path: Path | None = Field(default_factory=_default_ecc_source_path)
    model_config = SettingsConfigDict(env_prefix="OPENZUES_", env_file=".env", extra="ignore")

    @property
    def effective_db_path(self) -> Path:
        if self.db_path is not None:
            return self.db_path
        return self.data_dir / "openzues.db"

    @property
    def effective_master_key_path(self) -> Path:
        if self.master_key_path is not None:
            return self.master_key_path
        return self.data_dir / "master.key"

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).parent / "web" / "templates"

    @property
    def static_dir(self) -> Path:
        return Path(__file__).parent / "web" / "static"


settings = Settings()
