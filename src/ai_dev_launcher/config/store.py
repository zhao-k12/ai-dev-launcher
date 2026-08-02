"""Atomic JSON configuration persistence."""

from __future__ import annotations

import json
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

from ai_dev_launcher.config.models import AppConfig
from ai_dev_launcher.config.locking import file_lock
from ai_dev_launcher.errors import ConfigurationError


class ConfigStore:
    """Load and save application configuration."""

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self.path = config_dir / "config.json"
        self.lock_path = config_dir / "config.lock"

    @contextmanager
    def _lock(self) -> Iterator[None]:
        with file_lock(self.lock_path):
            yield

    def load(self) -> AppConfig:
        with self._lock():
            return self._load_unlocked()

    def _load_unlocked(self) -> AppConfig:
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
        with self._lock():
            self._save_unlocked(config)

    def _save_unlocked(self, config: AppConfig) -> None:
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

    @contextmanager
    def edit(self) -> Iterator[AppConfig]:
        """Lock the complete read-modify-write transaction across processes."""

        with self._lock():
            config = self._load_unlocked()
            yield config
            self._save_unlocked(config)
