from __future__ import annotations

from pathlib import Path

import pytest

from ai_dev_launcher.config import ConfigStore
from ai_dev_launcher.errors import (
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
)
from ai_dev_launcher.services import ProjectService


@pytest.fixture
def service(tmp_path):
    return ProjectService(ConfigStore(tmp_path / "config"))


def test_add_project_registers_and_sets_first_default(service, tmp_path):
    project_dir = tmp_path / "alpha"
    project_dir.mkdir()

    project = service.add_project("alpha", project_dir)

    assert project.name == "alpha"
    assert project.path == str(project_dir.resolve())
    assert service.store.load().default_project == "alpha"


def test_duplicate_project_name_is_case_insensitive(service, tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    service.add_project("Alpha", first)

    with pytest.raises(ProjectAlreadyExistsError):
        service.add_project("alpha", second)


def test_add_requires_existing_directory(service, tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        service.add_project("missing", tmp_path / "missing")


def test_list_projects_is_sorted(service, tmp_path):
    for name in ("Zulu", "alpha"):
        path = tmp_path / name
        path.mkdir()
        service.add_project(name, path)

    assert [project.name for project in service.list_projects()] == ["alpha", "Zulu"]


def test_remove_project_does_not_delete_directory(service, tmp_path):
    project_dir = tmp_path / "alpha"
    project_dir.mkdir()
    service.add_project("alpha", project_dir)

    removed = service.remove_project("ALPHA")

    assert removed.name == "alpha"
    assert project_dir.exists()
    assert service.list_projects() == []
    assert service.store.load().default_project is None


def test_remove_unknown_project_fails(service):
    with pytest.raises(ProjectNotFoundError):
        service.remove_project("unknown")


def test_set_default_project(service, tmp_path):
    for name in ("alpha", "beta"):
        path = tmp_path / name
        path.mkdir()
        service.add_project(name, path)

    service.set_default("beta")

    assert service.store.load().default_project == "beta"


def test_get_default_project(service, tmp_path):
    path = tmp_path / "alpha"
    path.mkdir()
    service.add_project("alpha", path)

    assert service.get_default_project().name == "alpha"


def test_get_default_project_requires_configuration(service):
    with pytest.raises(ProjectNotFoundError, match="No default project"):
        service.get_default_project()


def test_create_project_creates_and_initializes_directory(service, tmp_path):
    project = service.create_project("new-app", tmp_path)

    root = tmp_path / "new-app"
    assert project.path == str(root.resolve())
    assert (root / "AGENTS.md").exists()
    assert (root / ".ai-dev-launcher" / "project.json").exists()
    assert service.store.load().default_project == "new-app"


def test_create_project_rejects_existing_destination(service, tmp_path):
    (tmp_path / "existing").mkdir()

    with pytest.raises(ProjectAlreadyExistsError):
        service.create_project("existing", tmp_path)


def test_create_project_rolls_back_directory_and_registration_on_preparation_failure(service, tmp_path, monkeypatch):
    def fail_preparation(*args, **kwargs):
        root = tmp_path / "broken-app"
        (root / "partial.txt").write_text("partial", encoding="utf-8")
        raise RuntimeError("preparation failed")

    monkeypatch.setattr("ai_dev_launcher.services.projects.ProjectPreparationService.prepare", fail_preparation)

    with pytest.raises(RuntimeError, match="preparation failed"):
        service.create_project("broken-app", tmp_path)

    assert not (tmp_path / "broken-app").exists()
    assert service.store.load().projects == []


def test_update_project_renames_and_moves_directory(service, tmp_path):
    source_parent = tmp_path / "source"
    target_parent = tmp_path / "target"
    source_parent.mkdir()
    target_parent.mkdir()
    source = source_parent / "sample"
    source.mkdir()
    (source / "keep.txt").write_text("content", encoding="utf-8")
    service.add_project("sample", source)

    updated, old_path, moved = service.update_project("sample", "renamed", target_parent)

    destination = target_parent / "sample"
    assert updated.name == "renamed"
    assert Path(updated.path) == destination
    assert old_path == str(source.resolve())
    assert moved is True
    assert (destination / "keep.txt").read_text(encoding="utf-8") == "content"
    assert not source.exists()
    assert service.get_default_project().name == "renamed"


def test_update_project_refuses_existing_destination(service, tmp_path):
    source_parent = tmp_path / "source"
    target_parent = tmp_path / "target"
    source_parent.mkdir()
    target_parent.mkdir()
    source = source_parent / "sample"
    source.mkdir()
    (target_parent / "sample").mkdir()
    service.add_project("sample", source)

    with pytest.raises(ProjectAlreadyExistsError):
        service.update_project("sample", "sample", target_parent)

    assert source.exists()
