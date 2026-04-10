from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OpenZues"
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = Field(default_factory=lambda: Path.cwd() / ".openzues")
    db_path: Path | None = None
    default_codex_command: str = "codex"
    default_codex_args: str = "app-server"
    websocket_ping_interval_seconds: int = 20
    model_config = SettingsConfigDict(env_prefix="OPENZUES_", env_file=".env", extra="ignore")

    @property
    def effective_db_path(self) -> Path:
        if self.db_path is not None:
            return self.db_path
        return self.data_dir / "openzues.db"

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).parent / "web" / "templates"

    @property
    def static_dir(self) -> Path:
        return Path(__file__).parent / "web" / "static"


settings = Settings()

