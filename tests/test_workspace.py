import subprocess

import pytest

from ai_dev_launcher.domain.project import Project
from ai_dev_launcher.services.workspace import WorkspaceService


def service(tmp_path):
    return WorkspaceService(Project("sample", str(tmp_path), "now"))


def test_tree_and_read_stay_inside_project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')", encoding="utf-8")
    workspace = service(tmp_path)

    assert any(item["path"] == "src/app.py" for item in workspace.tree()["items"])
    assert workspace.read("src/app.py")["content"] == "print('ok')"
    with pytest.raises(ValueError, match="inside"):
        workspace.read("../secret.txt")


def test_git_stage_and_restore(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    path = tmp_path / "file.txt"
    path.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True, capture_output=True)
    path.write_text("after\n", encoding="utf-8")
    workspace = service(tmp_path)

    assert "after" in workspace.git_diff("file.txt")["diff"]
    assert workspace.stage("file.txt")["status"] == "accepted"
    path.write_text("changed again\n", encoding="utf-8")
    assert workspace.restore("file.txt")["status"] == "restored"
