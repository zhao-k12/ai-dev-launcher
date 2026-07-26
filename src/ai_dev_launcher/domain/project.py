"""Project domain model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Project:
    """A local development project registered with the launcher."""

    name: str
    path: str
    created_at: str

    @classmethod
    def create(cls, name: str, path: Path) -> "Project":
        return cls(
            name=name,
            path=str(path.resolve()),
            created_at=datetime.now(UTC).isoformat(),
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Project":
        return cls(
            name=str(value["name"]),
            path=str(value["path"]),
            created_at=str(value["created_at"]),
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

