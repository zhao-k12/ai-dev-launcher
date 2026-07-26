"""Windows-friendly application data paths."""

from __future__ import annotations

import os
from pathlib import Path


def default_config_dir() -> Path:
    """Return the user-level configuration directory.

    Windows uses LOCALAPPDATA. Other platforms get a small compatibility
    fallback so the core remains easy to test and develop.
    """

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "AI Dev Launcher"
    return Path.home() / ".config" / "ai-dev-launcher"

