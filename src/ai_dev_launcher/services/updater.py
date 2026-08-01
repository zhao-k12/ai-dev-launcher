"""Automatic updates for launcher-private command line tools."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

UpdateRunner = Callable[[list[str], Mapping[str, str]], subprocess.CompletedProcess[str]]


def _run(command: list[str], environment: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, env=dict(environment), capture_output=True, text=True, timeout=300, check=False)


class PrivateToolUpdateService:
    """Install updates into launcher-owned paths with directory rollback."""

    def __init__(self, config_dir: Path, runner: UpdateRunner = _run) -> None:
        self.root = config_dir / "runtime" / "tools"
        self.runner = runner

    def update_all(self) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        state_path = self.root / "update-state.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            last_attempt = datetime.fromisoformat(str(state.get("last_attempt")))
            if datetime.now(UTC) - last_attempt < timedelta(hours=24):
                return {"tools": [], "skipped": "automatic update check already ran today"}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        results = [self._update_codex(), self._update_headroom()]
        state_path.write_text(json.dumps({"last_attempt": datetime.now(UTC).isoformat(), "results": results}, indent=2) + "\n", encoding="utf-8")
        return {"tools": results}

    def _update_codex(self) -> dict[str, Any]:
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            return self._result("codex", "skipped", "npm is unavailable; existing version was kept")
        stage = self.root / "codex.next"
        environment = dict(os.environ)
        command = [npm, "install", "--prefix", str(stage), "@openai/codex@latest", "--no-audit", "--no-fund"]
        return self._install("codex", stage, command, environment, Path("node_modules/.bin/codex.cmd" if os.name == "nt" else "node_modules/.bin/codex"))

    def _update_headroom(self) -> dict[str, Any]:
        uv = shutil.which("uv.exe" if os.name == "nt" else "uv")
        if not uv:
            return self._result("headroom", "skipped", "uv is unavailable; existing version was kept")
        stage = self.root / "headroom.next"
        environment = dict(os.environ)
        environment["UV_TOOL_DIR"] = str(stage / "packages")
        environment["UV_TOOL_BIN_DIR"] = str(stage / "bin")
        command = [uv, "tool", "install", "--upgrade", "headroom-ai[proxy,mcp,code]"]
        executable = Path("bin/headroom.exe" if os.name == "nt" else "bin/headroom")
        return self._install("headroom", stage, command, environment, executable)

    def _install(self, key: str, stage: Path, command: list[str], environment: Mapping[str, str], executable: Path) -> dict[str, Any]:
        target = self.root / key
        backup = self.root / f"{key}.previous"
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)
        try:
            completed = self.runner(command, environment)
            if completed.returncode != 0 or not (stage / executable).is_file():
                detail = (completed.stderr or completed.stdout or "update validation failed").strip().splitlines()[-1]
                return self._result(key, "rolled_back" if target.exists() else "failed", detail)
            verification = self.runner([str(stage / executable), "--version"], environment)
            if verification.returncode != 0:
                detail = (verification.stderr or verification.stdout or "version verification failed").strip().splitlines()[-1]
                return self._result(key, "rolled_back" if target.exists() else "failed", detail)
            if backup.exists():
                shutil.rmtree(backup)
            if target.exists():
                target.rename(backup)
            stage.rename(target)
            return self._result(key, "updated", "private tool update installed and verified")
        except (OSError, subprocess.SubprocessError) as exc:
            if not target.exists() and backup.exists():
                backup.rename(target)
            return self._result(key, "rolled_back" if target.exists() else "failed", str(exc))
        finally:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)

    @staticmethod
    def _result(key: str, status: str, detail: str) -> dict[str, str]:
        return {"key": key, "status": status, "detail": detail}
