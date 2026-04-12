from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class GitHubService:
    def _run(self, args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

    def inspect_project(self, path: str) -> dict[str, Any]:
        project_path = Path(path).expanduser()
        result: dict[str, Any] = {
            "exists": project_path.exists(),
            "is_git_repo": False,
            "branch": None,
            "git_status": None,
            "recent_commits": [],
            "pull_requests": [],
        }
        if not result["exists"]:
            return result

        git_check = self._run(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(project_path))
        if git_check.returncode != 0 or "true" not in git_check.stdout:
            return result
        result["is_git_repo"] = True

        branch = self._run(["git", "branch", "--show-current"], cwd=str(project_path))
        if branch.returncode == 0:
            result["branch"] = branch.stdout.strip() or None

        status = self._run(["git", "status", "--short", "--branch"], cwd=str(project_path))
        if status.returncode == 0:
            result["git_status"] = status.stdout.strip()

        commits = self._run(["git", "log", "--oneline", "--decorate", "-5"], cwd=str(project_path))
        if commits.returncode == 0:
            result["recent_commits"] = [
                {"summary": line.strip()} for line in commits.stdout.splitlines() if line.strip()
            ]

        prs = self._run(
            [
                "gh",
                "pr",
                "list",
                "--limit",
                "5",
                "--json",
                "number,title,state,url,headRefName,baseRefName,isDraft",
            ],
            cwd=str(project_path),
        )
        if prs.returncode == 0 and prs.stdout.strip():
            result["pull_requests"] = json.loads(prs.stdout)

        return result
