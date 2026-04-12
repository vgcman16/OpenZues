from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openzues.services.ecc_catalog import (
    inspect_ecc_harness_surface,
    run_ecc_workspace_install,
    run_ecc_workspace_repair,
    run_ecc_workspace_uninstall,
    serialize_ecc_repair_run,
    serialize_ecc_workspace_surface,
)
from openzues.services.github import GitHubService


class ProjectService:
    def __init__(self, github_service: GitHubService) -> None:
        self.github_service = github_service

    def inspect_harness(self, project_row: dict[str, Any]) -> dict[str, Any] | None:
        path = Path(project_row["path"]).expanduser()
        harness = inspect_ecc_harness_surface(path)
        return serialize_ecc_workspace_surface(harness)

    def inspect(self, project_row: dict[str, Any]) -> dict[str, Any]:
        path = Path(project_row["path"]).expanduser()
        details = self.github_service.inspect_project(str(path))
        return {
            "id": project_row["id"],
            "path": str(path),
            "label": project_row["label"],
            "last_scan_at": datetime.now(UTC).isoformat(),
            "agent_harness": self.inspect_harness(project_row),
            **details,
        }

    def run_harness_operation(
        self,
        project_row: dict[str, Any],
        mode: str,
        *,
        profile: str | None = None,
    ) -> dict[str, Any]:
        path = Path(project_row["path"]).expanduser()
        if mode == "repair_preview":
            run = run_ecc_workspace_repair(path, apply=False)
        elif mode == "repair_apply":
            run = run_ecc_workspace_repair(path, apply=True)
        elif mode == "install_preview":
            run = run_ecc_workspace_install(path, profile=profile, apply=False)
        elif mode == "install_apply":
            run = run_ecc_workspace_install(path, profile=profile, apply=True)
        elif mode == "uninstall_preview":
            run = run_ecc_workspace_uninstall(path, apply=False)
        elif mode == "uninstall_apply":
            run = run_ecc_workspace_uninstall(path, apply=True)
        else:  # pragma: no cover - API schema constrains this
            raise ValueError(f"Unsupported project harness operation: {mode}")
        return serialize_ecc_repair_run(run)
