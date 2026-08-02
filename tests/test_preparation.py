from __future__ import annotations

import json
import subprocess

import pytest

from ai_dev_launcher.domain.project import Project
from ai_dev_launcher.errors import PreparationError
from ai_dev_launcher.services.preparation import (
    BEGIN_MARKER,
    END_MARKER,
    ProjectPreparationService,
)


def _project(path):
    return Project("sample", str(path.resolve()), "2026-01-01T00:00:00+00:00")


def test_dry_run_makes_no_changes(tmp_path):
    service = ProjectPreparationService()

    result = service.prepare(_project(tmp_path), dry_run=True)

    assert result.dry_run is True
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".ai-dev-launcher").exists()
    assert not (tmp_path / ".git").exists()


def test_prepare_writes_agents_metadata_and_initializes_git(tmp_path):
    calls = []

    def git_runner(path):
        calls.append(path)
        (path / ".git").mkdir()
        return subprocess.CompletedProcess(["git", "init"], 0, "ok", "")

    service = ProjectPreparationService(git_runner=git_runner)

    result = service.prepare(_project(tmp_path))

    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    metadata = json.loads(
        (tmp_path / ".ai-dev-launcher" / "project.json").read_text(encoding="utf-8")
    )
    assert BEGIN_MARKER in agents
    assert END_MARKER in agents
    assert metadata["name"] == "sample"
    assert metadata["git_initialized"] is True
    assert calls == [tmp_path]
    assert any(action.kind == "git" for action in result.actions)


def test_existing_agents_content_is_preserved_and_backed_up(tmp_path):
    original = "# Existing instructions\n\nKeep this."
    (tmp_path / "AGENTS.md").write_text(original, encoding="utf-8")
    service = ProjectPreparationService()

    service.prepare(_project(tmp_path), initialize_git=False)

    updated = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    backups = list((tmp_path / ".ai-dev-launcher" / "backups").glob("*.bak"))
    assert original in updated
    assert BEGIN_MARKER in updated
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == original


def test_managed_block_is_updated_without_duplication(tmp_path):
    service = ProjectPreparationService()
    service.prepare(_project(tmp_path), initialize_git=False)
    first = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

    service.prepare(_project(tmp_path), initialize_git=False)
    second = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

    assert second == first
    assert second.count(BEGIN_MARKER) == 1


def test_incomplete_marker_block_is_rejected(tmp_path):
    (tmp_path / "AGENTS.md").write_text(BEGIN_MARKER, encoding="utf-8")
    service = ProjectPreparationService()

    with pytest.raises(PreparationError, match="incomplete"):
        service.prepare(_project(tmp_path), initialize_git=False)


def test_git_failure_stops_before_metadata_write(tmp_path):
    original = "# Existing instructions\n\nKeep this."
    (tmp_path / "AGENTS.md").write_text(original, encoding="utf-8")

    def git_runner(path):
        return subprocess.CompletedProcess(["git", "init"], 1, "", "git failed")

    service = ProjectPreparationService(git_runner=git_runner)

    with pytest.raises(PreparationError, match="git failed"):
        service.prepare(_project(tmp_path))

    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == original
    assert not (tmp_path / ".ai-dev-launcher" / "project.json").exists()
