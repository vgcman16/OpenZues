from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openzues.services.github import GitHubService


class ProjectService:
    def __init__(self, github_service: GitHubService) -> None:
        self.github_service = github_service

    def inspect(self, project_row: dict[str, Any]) -> dict[str, Any]:
        path = Path(project_row["path"]).expanduser()
        details = self.github_service.inspect_project(str(path))
        return {
            "id": project_row["id"],
            "path": str(path),
            "label": project_row["label"],
            "last_scan_at": datetime.now(UTC).isoformat(),
            **details,
        }
