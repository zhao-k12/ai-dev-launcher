"""Development environment launch models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LaunchPlan:
    """A safe-to-display process launch plan."""

    project: str
    cwd: str
    command: tuple[str, ...]
    use_headroom: bool
    path_prepend: tuple[str, ...]
    environment_overrides: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "cwd": self.cwd,
            "command": list(self.command),
            "use_headroom": self.use_headroom,
            "path_prepend": list(self.path_prepend),
            "environment_overrides": dict(self.environment_overrides),
        }
