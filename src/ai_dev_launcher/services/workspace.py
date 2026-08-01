"""Safe project workspace inspection and command execution."""

from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from ai_dev_launcher.domain.project import Project


class WorkspaceService:
    def __init__(self, project: Project) -> None:
        self.project = project
        self.root = Path(project.path).resolve()

    def tree(self, max_items: int = 600) -> dict[str, Any]:
        ignored = {".git", "node_modules", ".venv", "dist", "release", "__pycache__"}
        items: list[dict[str, Any]] = []
        for path in sorted(self.root.rglob("*"), key=lambda item: (not item.is_dir(), str(item).casefold())):
            relative = path.relative_to(self.root)
            if any(part in ignored for part in relative.parts):
                continue
            items.append({"path": relative.as_posix(), "name": path.name, "kind": "directory" if path.is_dir() else "file"})
            if len(items) >= max_items:
                break
        return {"items": items, "truncated": len(items) >= max_items}

    def read(self, relative_path: str) -> dict[str, Any]:
        path = self._path(relative_path)
        if not path.is_file():
            raise ValueError(f"File does not exist: {relative_path}")
        if path.stat().st_size > 1_000_000:
            raise ValueError("File is too large to preview")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Only UTF-8 text files can be previewed") from exc
        return {"path": relative_path, "content": content}

    def git_diff(self, relative_path: str | None = None) -> dict[str, Any]:
        command = ["git", "diff", "--no-ext-diff", "--"]
        if relative_path:
            self._path(relative_path)
            command.append(relative_path)
        diff = self._run(command)
        status = self._run(["git", "status", "--short"])
        return {"diff": diff.stdout, "status": status.stdout.splitlines()}

    def stage(self, relative_path: str) -> dict[str, Any]:
        self._path(relative_path)
        self._check(["git", "add", "--", relative_path])
        return {"path": relative_path, "status": "accepted"}

    def restore(self, relative_path: str) -> dict[str, Any]:
        self._path(relative_path)
        self._check(["git", "restore", "--", relative_path])
        return {"path": relative_path, "status": "restored"}

    def run_terminal(self, command: str) -> dict[str, Any]:
        if not command.strip():
            raise ValueError("Command cannot be empty")
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        return {"command": command, "stdout": completed.stdout, "stderr": completed.stderr, "exit_code": completed.returncode}

    def headroom_stats(self, port: int = 8787) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/stats?cached=1", timeout=2) as response:
                payload = json.load(response)
            project_key = self.project.name.casefold().replace("_", "-").replace(" ", "-")
            project = payload.get("savings", {}).get("per_project", {}).get(project_key, {})
            totals = payload.get("agent_usage", {}).get("totals", {})
            return {
                "available": True,
                "tokens_saved": project.get("tokens_saved", totals.get("tokens_saved", 0)),
                "savings_percent": project.get("savings_percent", totals.get("savings_percent", 0)),
                "requests": project.get("requests", totals.get("requests", 0)),
            }
        except (OSError, ValueError, json.JSONDecodeError):
            return {"available": False, "tokens_saved": 0, "savings_percent": 0, "requests": 0}

    def _path(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("Path must stay inside the current project")
        return candidate

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30, check=False, encoding="utf-8", errors="replace")

    def _check(self, command: list[str]) -> None:
        result = self._run(command)
        if result.returncode != 0:
            raise ValueError((result.stderr or result.stdout or "Git operation failed").strip())
