"""Project registry use cases."""

from __future__ import annotations

import shutil
from pathlib import Path

from ai_dev_launcher.config.store import ConfigStore
from ai_dev_launcher.domain.project import Project
from ai_dev_launcher.errors import (
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
)
from ai_dev_launcher.services.preparation import ProjectPreparationService


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

    def create_project(self, name: str, parent: Path) -> Project:
        """Create, register, and initialize a new project with safe defaults."""

        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Project name cannot be empty")
        if normalized_name in {".", ".."} or any(
            character in normalized_name for character in '<>:"/\\|?*'
        ):
            raise ValueError("Project name contains characters that Windows cannot use")

        resolved_parent = parent.expanduser().resolve()
        if not resolved_parent.is_dir():
            raise ValueError(f"Save location does not exist: {resolved_parent}")

        project_path = resolved_parent / normalized_name
        if project_path.exists():
            raise ProjectAlreadyExistsError(
                f"A file or folder already exists at: {project_path}"
            )

        project_path.mkdir()
        try:
            project = self.add_project(normalized_name, project_path)
            self.set_default(project.name)
            ProjectPreparationService().prepare(project, initialize_git=True)
            return project
        except Exception:
            try:
                project_path.rmdir()
            except OSError:
                pass
            raise

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

    def update_project(self, current_name: str, new_name: str, parent: Path) -> tuple[Project, str, bool]:
        """Rename a registered project and optionally move its directory."""

        normalized_name = new_name.strip()
        if not normalized_name:
            raise ValueError("Project name cannot be empty")
        if normalized_name in {".", ".."} or any(
            character in normalized_name for character in '<>:"/\\|?*'
        ):
            raise ValueError("Project name contains characters that Windows cannot use")

        config = self.store.load()
        current = next(
            (item for item in config.projects if item.name.casefold() == current_name.casefold()),
            None,
        )
        if current is None:
            raise ProjectNotFoundError(f"Project '{current_name}' is not registered")
        if any(
            item.name.casefold() == normalized_name.casefold()
            and item.name.casefold() != current.name.casefold()
            for item in config.projects
        ):
            raise ProjectAlreadyExistsError(f"Project '{normalized_name}' is already registered")

        source = Path(current.path).resolve()
        if not source.is_dir():
            raise ValueError(f"Project directory does not exist: {source}")
        resolved_parent = parent.expanduser().resolve()
        if not resolved_parent.is_dir():
            raise ValueError(f"Save location does not exist: {resolved_parent}")
        if resolved_parent == source or resolved_parent.is_relative_to(source):
            raise ValueError("A project cannot be moved inside its own directory")

        destination = source if resolved_parent == source.parent else resolved_parent / source.name
        moved = destination != source
        if moved and destination.exists():
            raise ProjectAlreadyExistsError(f"A file or folder already exists at: {destination}")

        if moved:
            shutil.move(str(source), str(destination))
        updated = Project(
            name=normalized_name,
            path=str(destination),
            created_at=current.created_at,
        )
        config.projects = [updated if item.name.casefold() == current.name.casefold() else item for item in config.projects]
        if config.default_project and config.default_project.casefold() == current.name.casefold():
            config.default_project = updated.name
        try:
            self.store.save(config)
        except Exception:
            if moved and destination.exists() and not source.exists():
                shutil.move(str(destination), str(source))
            raise
        return updated, current.path, moved
