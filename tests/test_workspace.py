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


def test_tree_and_images_prune_large_dependency_directories(tmp_path):
    dependency = tmp_path / "node_modules" / "package"
    dependency.mkdir(parents=True)
    (dependency / "hidden.js").write_text("large dependency", encoding="utf-8")
    (dependency / "hidden.png").write_bytes(b"png")
    (tmp_path / "visible.py").write_text("print('ok')", encoding="utf-8")
    workspace = service(tmp_path)

    paths = {item["path"] for item in workspace.tree()["items"]}
    assert "visible.py" in paths
    assert not any(path.startswith("node_modules") for path in paths)
    assert workspace.recent_images(0)["images"] == []


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


def test_recent_images_and_preview_path_stay_inside_project(tmp_path):
    image_dir = tmp_path / "关键帧"
    image_dir.mkdir()
    image = image_dir / "S01.png"
    image.write_bytes(b"png")
    workspace = service(tmp_path)

    result = workspace.recent_images(0)

    assert result["images"][0]["path"] == "关键帧/S01.png"
    assert workspace.image_path("关键帧/S01.png")["path"] == str(image.resolve())
    assert workspace.image_paths(["关键帧/S01.png"])["images"][0]["relative_path"] == "关键帧/S01.png"
    with pytest.raises(ValueError):
        workspace.image_path("../outside.png")


def test_image_preview_batch_is_bounded(tmp_path):
    workspace = service(tmp_path)

    with pytest.raises(ValueError, match="24"):
        workspace.image_paths([f"image-{index}.png" for index in range(25)])


def test_chat_link_only_opens_safe_project_files(tmp_path):
    page = tmp_path / "preview" / "index.html"
    page.parent.mkdir()
    page.write_text("<h1>Preview</h1>", encoding="utf-8")
    workspace = service(tmp_path)

    assert workspace.link_path("preview/index.html")["path"] == str(page.resolve())
    assert workspace.link_path(page.as_uri())["path"] == str(page.resolve())
    with pytest.raises(ValueError, match="inside"):
        workspace.link_path("../outside.html")
    script = tmp_path / "unsafe.exe"
    script.write_bytes(b"unsafe")
    with pytest.raises(ValueError, match="type"):
        workspace.link_path("unsafe.exe")
