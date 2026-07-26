from __future__ import annotations

from ai_dev_launcher.bridge import handle_request


def test_bridge_project_management_round_trip(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    monkeypatch.setenv("AI_DEV_CONFIG_DIR", str(config_dir))

    added = handle_request(
        {
            "action": "projects.add",
            "payload": {
                "name": "desktop-app",
                "path": str(project_dir),
                "make_default": True,
            },
        }
    )
    listed = handle_request({"action": "projects.list"})

    assert added["project"]["name"] == "desktop-app"
    assert listed["default_project"] == "desktop-app"
    assert listed["projects"][0]["path"] == str(project_dir.resolve())

    removed = handle_request(
        {"action": "projects.remove", "payload": {"name": "desktop-app"}}
    )
    assert removed["project"]["name"] == "desktop-app"
    assert handle_request({"action": "projects.list"})["projects"] == []


def test_bridge_previews_and_prepares_project(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    monkeypatch.setenv("AI_DEV_CONFIG_DIR", str(config_dir))
    handle_request(
        {
            "action": "projects.add",
            "payload": {"name": "sample", "path": str(project_dir)},
        }
    )

    preview = handle_request(
        {
            "action": "projects.prepare",
            "payload": {
                "name": "sample",
                "dry_run": True,
                "initialize_git": False,
            },
        }
    )
    assert preview["dry_run"] is True
    assert not (project_dir / "AGENTS.md").exists()

    result = handle_request(
        {
            "action": "projects.prepare",
            "payload": {
                "name": "sample",
                "dry_run": False,
                "initialize_git": False,
            },
        }
    )
    assert result["dry_run"] is False
    assert (project_dir / "AGENTS.md").exists()
    assert (project_dir / ".ai-dev-launcher" / "project.json").exists()
