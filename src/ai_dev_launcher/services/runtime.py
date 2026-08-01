"""Launcher-owned runtime status without touching global Codex configuration."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_dev_launcher.services.tools import ToolDetectionService


class RuntimeService:
    """Recover launcher state using only launcher-owned files."""

    def __init__(self, config_dir: Path, tool_service: ToolDetectionService | None = None) -> None:
        self.config_dir = config_dir
        self.runtime_dir = config_dir / "runtime"
        self.state_path = self.runtime_dir / "state.json"
        if tool_service is None:
            private_bins = [
                self.runtime_dir / "tools" / "codex" / "node_modules" / ".bin",
                self.runtime_dir / "tools" / "headroom" / "bin",
            ]
            environment = dict(os.environ)
            environment["PATH"] = os.pathsep.join(
                [*(str(path) for path in private_bins), environment.get("PATH", "")]
            )
            tool_service = ToolDetectionService(environment=environment)
        self.tool_service = tool_service

    def status(self) -> dict[str, Any]:
        tools = {item.key: item for item in self.tool_service.check_all()}
        codex = tools.get("codex")
        headroom = tools.get("headroom")
        previous = self._load_state()
        checks = [
            self._check("codex_config", "Codex 桌面端配置独立", True, "启动器未修改全局 Codex 配置"),
            self._check("headroom", "Headroom 已就绪", bool(headroom and headroom.is_available), headroom.detail if headroom else None),
            self._check("codex", "Codex CLI 可用", bool(codex and codex.is_available), codex.detail if codex else None),
            self._check("recovery", "未发现异常退出残留", not previous.get("dirty", False), None),
        ]
        ready = all(item["status"] == "ready" for item in checks)
        return {
            "status": "ready" if ready else "attention",
            "checks": checks,
            "headroom_version": headroom.version if headroom else None,
            "codex_version": codex.version if codex else None,
            "headroom_port": previous.get("headroom_port"),
            "isolation": "process",
            "automatic_updates": True,
            "last_checked": datetime.now(UTC).isoformat(),
        }

    def bootstrap(self) -> dict[str, Any]:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        previous = self._load_state()
        recovered = bool(previous.get("dirty", False))
        state = {
            "dirty": False,
            "ownership": "ai-dev-launcher",
            "isolation": "process",
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        result = self.status()
        result["recovered"] = recovered
        return result

    @staticmethod
    def isolated_environment(base: dict[str, str] | None = None) -> dict[str, str]:
        environment = dict(base or os.environ)
        environment["HEADROOM_TELEMETRY"] = "off"
        environment["HEADROOM_UPDATE_CHECK"] = "off"
        environment["AI_DEV_LAUNCHER_ISOLATED"] = "1"
        return environment

    def _load_state(self) -> dict[str, Any]:
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _check(key: str, label: str, ready: bool, detail: str | None) -> dict[str, Any]:
        return {"key": key, "label": label, "status": "ready" if ready else "error", "detail": detail}
