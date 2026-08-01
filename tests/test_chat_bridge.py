from ai_dev_launcher.bridge import handle_request


def test_chat_plan_is_process_isolated_and_disables_mcp_registration(tmp_path, monkeypatch):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    monkeypatch.setenv("AI_DEV_CONFIG_DIR", str(tmp_path / "config"))
    handle_request({"action": "projects.add", "payload": {"name": "sample", "path": str(project_dir)}})

    class FakeLauncher:
        def __init__(self, **kwargs): pass
        def build_plan(self, project, use_headroom, codex_args):
            assert use_headroom is True
            assert codex_args[:2] == ("exec", "--json")
            assert "workspace-write" in codex_args
            assert "--dangerously-bypass-approvals-and-sandbox" not in codex_args
            return type("Plan", (), {"to_dict": lambda self: {"command": ["headroom", "wrap", "codex", "--no-mcp", "--", *codex_args], "cwd": project.path, "environment_overrides": [["AI_DEV_LAUNCHER_ISOLATED", "1"]], "path_prepend": []}})()

    monkeypatch.setattr("ai_dev_launcher.bridge.LaunchService", FakeLauncher)
    result = handle_request({"action": "chat.plan", "payload": {"name": "sample", "prompt": "修复测试"}})

    assert "--no-mcp" in result["command"]
    assert result["environment_overrides"] == [["AI_DEV_LAUNCHER_ISOLATED", "1"]]


def test_chat_plan_passes_images_to_codex(tmp_path, monkeypatch):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    image = tmp_path / "clipboard.png"
    image.write_bytes(b"png")
    monkeypatch.setenv("AI_DEV_CONFIG_DIR", str(tmp_path / "config"))
    handle_request({"action": "projects.add", "payload": {"name": "sample", "path": str(project_dir)}})

    class FakeLauncher:
        def __init__(self, **kwargs): pass
        def build_plan(self, project, use_headroom, codex_args):
            assert ("--image", str(image)) == codex_args[-3:-1]
            return type("Plan", (), {"to_dict": lambda self: {"command": list(codex_args)}})()

    monkeypatch.setattr("ai_dev_launcher.bridge.LaunchService", FakeLauncher)
    handle_request({"action": "chat.plan", "payload": {"name": "sample", "prompt": "analyze", "images": [str(image)]}})
