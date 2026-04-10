from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ForumForge"
    host: str = "127.0.0.1"
    port: int = 8890
    data_dir: Path = Field(default_factory=lambda: Path.cwd() / ".forumforge")
    db_path: Path | None = None
    model_config = SettingsConfigDict(env_prefix="FORUMFORGE_", env_file=".env", extra="ignore")

    @property
    def effective_db_path(self) -> Path:
        if self.db_path is not None:
            return self.db_path
        return self.data_dir / "forumforge.db"

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).parent / "web" / "templates"

    @property
    def static_dir(self) -> Path:
        return Path(__file__).parent / "web" / "static"


settings = Settings()
