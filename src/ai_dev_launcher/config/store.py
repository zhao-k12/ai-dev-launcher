"""Atomic JSON configuration persistence."""

from __future__ import annotations

import json
from pathlib import Path

from ai_dev_launcher.config.models import AppConfig
from ai_dev_launcher.errors import ConfigurationError


class ConfigStore:
    """Load and save application configuration."""

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self.path = config_dir / "config.json"

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"Could not read configuration at {self.path}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise ConfigurationError("Configuration root must be a JSON object")
        return AppConfig.from_dict(value)

    def save(self, config: AppConfig) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".json.tmp")
        payload = json.dumps(config.to_dict(), indent=2, ensure_ascii=False) + "\n"
        try:
            temporary_path.write_text(payload, encoding="utf-8")
            temporary_path.replace(self.path)
        except OSError as exc:
            raise ConfigurationError(
                f"Could not save configuration at {self.path}: {exc}"
            ) from exc

