"""Configuration models and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ai_dev_launcher.domain.project import Project
from ai_dev_launcher.errors import ConfigurationError


@dataclass(slots=True)
class AppConfig:
    """Persisted application configuration."""

    schema_version: int = 1
    default_project: str | None = None
    projects: list[Project] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AppConfig":
        try:
            schema_version = int(value.get("schema_version", 1))
            if schema_version != 1:
                raise ConfigurationError(
                    f"Unsupported configuration schema: {schema_version}"
                )
            projects = [
                Project.from_dict(item) for item in value.get("projects", [])
            ]
            default_project = value.get("default_project")
            if default_project is not None:
                default_project = str(default_project)
            return cls(
                schema_version=schema_version,
                default_project=default_project,
                projects=projects,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigurationError(f"Invalid configuration: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["projects"] = [project.to_dict() for project in self.projects]
        return result

