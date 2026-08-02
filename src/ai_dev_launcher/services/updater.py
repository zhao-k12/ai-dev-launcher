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
from uuid import uuid4

from ai_dev_launcher.config.locking import file_lock

UpdateRunner = Callable[[list[str], Mapping[str, str]], subprocess.CompletedProcess[str]]


def _run(command: list[str], environment: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, env=dict(environment), capture_output=True, text=True, timeout=900, check=False)


class PrivateToolUpdateService:
    """Install updates into launcher-owned paths with directory rollback."""

    def __init__(self, config_dir: Path, runner: UpdateRunner = _run) -> None:
        self.root = config_dir / "runtime" / "tools"
        self.runner = runner

    def update_all(self) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        with file_lock(self.root / "update.lock"):
            state_path = self.root / "update-state.json"
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                last_attempt = datetime.fromisoformat(str(state.get("last_attempt")))
                if datetime.now(UTC) - last_attempt < timedelta(hours=24) and not self._private_tools_need_repair():
                    return {"tools": [], "skipped": "automatic update check already ran today"}
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass
            results = [self._update_codex(), self._update_headroom()]
            temporary = state_path.with_suffix(".json.tmp")
            try:
                temporary.write_text(json.dumps({"last_attempt": datetime.now(UTC).isoformat(), "results": results}, indent=2) + "\n", encoding="utf-8")
                temporary.replace(state_path)
            except OSError:
                temporary.unlink(missing_ok=True)
            return {"tools": results}

    def _update_codex(self) -> dict[str, Any]:
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            return self._result("codex", "skipped", "npm is unavailable; existing version was kept")
        stage = self.root / f"codex.next-{uuid4().hex}"
        environment = dict(os.environ)
        command = [npm, "install", "--prefix", str(stage), "@openai/codex@latest", "--no-audit", "--no-fund"]
        return self._install("codex", stage, command, environment, Path("node_modules/.bin/codex.cmd" if os.name == "nt" else "node_modules/.bin/codex"))

    def _update_headroom(self) -> dict[str, Any]:
        uv = shutil.which("uv.exe" if os.name == "nt" else "uv")
        if not uv:
            return self._result("headroom", "skipped", "uv is unavailable; existing version was kept")
        # A unique stage avoids Windows native-DLL locks left by an older uv
        # environment or a still-running MCP process.
        stage = self.root / f"headroom.next-{uuid4().hex}"
        environment = dict(os.environ)
        environment["UV_TOOL_DIR"] = str(stage / "packages")
        environment["UV_TOOL_BIN_DIR"] = str(stage / "bin")
        # ONNX Runtime 1.22+ fails DLL initialization on some fully patched
        # Windows 10 systems. This tested Python 3.12 combination keeps
        # Headroom's Kompress backend available without installing Torch.
        command = [uv, "tool", "install", "--force", "--python", "3.12", "--with", "onnxruntime==1.19.2", "headroom-ai[proxy,mcp,code]"]
        executable = Path("bin/headroom.exe" if os.name == "nt" else "bin/headroom")
        python = Path("packages/headroom-ai/Scripts/python.exe" if os.name == "nt" else "packages/headroom-ai/bin/python")
        result = self._install("headroom", stage, command, environment, executable, (python, "-c", "import onnxruntime"))
        if result["status"] != "updated":
            return result
        # uv's Windows launchers remember their installation directory. The
        # verified stage is renamed atomically, so reinstall once from cache at
        # the stable final path to refresh those trampoline paths.
        target = self.root / "headroom"
        final_environment = dict(environment)
        final_environment["UV_TOOL_DIR"] = str(target / "packages")
        final_environment["UV_TOOL_BIN_DIR"] = str(target / "bin")
        relocated = self.runner(command, final_environment)
        final_executable = target / executable
        final_python = target / python
        if relocated.returncode != 0 or not final_executable.is_file() or not final_python.is_file():
            detail = (relocated.stderr or relocated.stdout or "relocated Headroom validation failed").strip().splitlines()[-1]
            restored = self._restore_previous("headroom")
            return self._result("headroom", "rolled_back" if restored else "failed", detail)
        version = self.runner([str(final_executable), "--version"], final_environment)
        compression = self.runner([str(final_python), "-c", "import onnxruntime"], final_environment)
        if version.returncode != 0 or compression.returncode != 0:
            detail = (version.stderr or compression.stderr or "relocated Headroom verification failed").strip().splitlines()[-1]
            restored = self._restore_previous("headroom")
            return self._result("headroom", "rolled_back" if restored else "failed", detail)
        return result

    def _restore_previous(self, key: str) -> bool:
        """Restore the newest verified backup after post-swap validation fails."""

        target = self.root / key
        backups = sorted(
            self.root.glob(f"{key}.previous*"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not backups:
            return False
        failed = self.root / f"{key}.failed-{uuid4().hex}"
        try:
            if target.exists():
                target.rename(failed)
            backups[0].rename(target)
            if failed.exists():
                shutil.rmtree(failed, ignore_errors=True)
            return True
        except OSError:
            if not target.exists() and failed.exists():
                try:
                    failed.rename(target)
                except OSError:
                    pass
            return False

    def _install(self, key: str, stage: Path, command: list[str], environment: Mapping[str, str], executable: Path, extra_verification: tuple[Path | str, ...] | None = None) -> dict[str, Any]:
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
            if extra_verification:
                check = [str(stage / item) if isinstance(item, Path) else item for item in extra_verification]
                verification = self.runner(check, environment)
                if verification.returncode != 0:
                    detail = (verification.stderr or verification.stdout or "compression runtime verification failed").strip().splitlines()[-1]
                    return self._result(key, "rolled_back" if target.exists() else "failed", detail)
            if backup.exists():
                try:
                    shutil.rmtree(backup)
                except OSError:
                    # Windows may keep native extension files locked while an
                    # older Headroom/MCP process is still alive. Preserve that
                    # recoverable backup and rotate to a unique backup path.
                    backup = self.root / f"{key}.previous-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
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

    def _private_tools_need_repair(self) -> bool:
        headroom = self.root / "headroom"
        executable = headroom / ("bin/headroom.exe" if os.name == "nt" else "bin/headroom")
        python = headroom / ("packages/headroom-ai/Scripts/python.exe" if os.name == "nt" else "packages/headroom-ai/bin/python")
        if not executable.is_file() or not python.is_file():
            return True
        try:
            version = self.runner([str(executable), "--version"], os.environ)
            compression = self.runner([str(python), "-c", "import onnxruntime"], os.environ)
            return version.returncode != 0 or compression.returncode != 0
        except (OSError, subprocess.SubprocessError):
            return True
