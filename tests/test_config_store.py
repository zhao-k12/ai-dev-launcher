from __future__ import annotations

import json

import pytest

from ai_dev_launcher.config import AppConfig, ConfigStore
from ai_dev_launcher.errors import ConfigurationError


def test_missing_config_returns_defaults(tmp_path):
    store = ConfigStore(tmp_path)

    config = store.load()

    assert config == AppConfig()
    assert not store.path.exists()


def test_save_and_load_round_trip(tmp_path):
    store = ConfigStore(tmp_path)
    config = AppConfig(default_project=None)

    store.save(config)

    assert store.load() == config
    assert json.loads(store.path.read_text(encoding="utf-8"))["schema_version"] == 1


def test_invalid_json_has_clear_error(tmp_path):
    store = ConfigStore(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{broken", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Could not read configuration"):
        store.load()


def test_unknown_schema_is_rejected(tmp_path):
    store = ConfigStore(tmp_path)
    store.path.write_text('{"schema_version": 99}', encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Unsupported configuration schema"):
        store.load()

