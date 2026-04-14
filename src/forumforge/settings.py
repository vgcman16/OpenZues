from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    data_dir: Path = Path(".forumforge")
    db_path: Path = Path(".forumforge/forumforge.db")

