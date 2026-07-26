"""Project registry use cases."""

from __future__ import annotations

from pathlib import Path

from ai_dev_launcher.config.store import ConfigStore
from ai_dev_launcher.domain.project import Project
from ai_dev_launcher.errors import (
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
)


class ProjectService:
    """Manage registered projects without depending on CLI details."""

    def __init__(self, store: ConfigStore) -> None:
        self.store = store

    def list_projects(self) -> list[Project]:
        return sorted(self.store.load().projects, key=lambda item: item.name.casefold())

    def add_project(self, name: str, path: Path) -> Project:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Project name cannot be empty")

        resolved_path = path.expanduser().resolve()
        if not resolved_path.is_dir():
            raise ValueError(f"Project directory does not exist: {resolved_path}")

        config = self.store.load()
        if any(
            project.name.casefold() == normalized_name.casefold()
            for project in config.projects
        ):
            raise ProjectAlreadyExistsError(
                f"Project '{normalized_name}' is already registered"
            )

        project = Project.create(normalized_name, resolved_path)
        config.projects.append(project)
        if config.default_project is None:
            config.default_project = project.name
        self.store.save(config)
        return project

    def get_project(self, name: str) -> Project:
        for project in self.store.load().projects:
            if project.name.casefold() == name.casefold():
                return project
        raise ProjectNotFoundError(f"Project '{name}' is not registered")

    def get_default_project(self) -> Project:
        config = self.store.load()
        if not config.default_project:
            raise ProjectNotFoundError(
                "No default project is configured; pass a project name"
            )
        for project in config.projects:
            if project.name.casefold() == config.default_project.casefold():
                return project
        raise ProjectNotFoundError(
            f"Default project '{config.default_project}' is not registered"
        )

    def remove_project(self, name: str) -> Project:
        config = self.store.load()
        project = next(
            (
                item
                for item in config.projects
                if item.name.casefold() == name.casefold()
            ),
            None,
        )
        if project is None:
            raise ProjectNotFoundError(f"Project '{name}' is not registered")

        config.projects = [
            item for item in config.projects if item.name.casefold() != name.casefold()
        ]
        if config.default_project and config.default_project.casefold() == name.casefold():
            config.default_project = config.projects[0].name if config.projects else None
        self.store.save(config)
        return project

    def set_default(self, name: str) -> Project:
        config = self.store.load()
        project = next(
            (
                item
                for item in config.projects
                if item.name.casefold() == name.casefold()
            ),
            None,
        )
        if project is None:
            raise ProjectNotFoundError(f"Project '{name}' is not registered")
        config.default_project = project.name
        self.store.save(config)
        return project
