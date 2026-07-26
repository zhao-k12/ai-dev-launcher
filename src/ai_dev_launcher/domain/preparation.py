"""Project preparation result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PreparationAction:
    """One planned or completed project preparation action."""

    kind: str
    target: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PreparationResult:
    """Summary of a project preparation run."""

    project: str
    dry_run: bool
    actions: tuple[PreparationAction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "dry_run": self.dry_run,
            "actions": [action.to_dict() for action in self.actions],
        }
