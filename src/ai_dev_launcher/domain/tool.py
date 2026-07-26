"""Development tool domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ToolStatus(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """How to discover and query a development tool."""

    key: str
    display_name: str
    commands: tuple[str, ...]
    version_args: tuple[str, ...]
    install_hint: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Result of checking one development tool."""

    key: str
    display_name: str
    status: ToolStatus
    required: bool = True
    command: str | None = None
    path: str | None = None
    version: str | None = None
    detail: str | None = None
    install_hint: str | None = None

    @property
    def is_available(self) -> bool:
        return self.status is ToolStatus.AVAILABLE

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value
