import subprocess
from pathlib import Path

from ai_dev_launcher.services.updater import PrivateToolUpdateService


def test_failed_private_update_preserves_existing_version(tmp_path, monkeypatch):
    target = tmp_path / "runtime" / "tools" / "codex"
    target.mkdir(parents=True)
    (target / "old.txt").write_text("working", encoding="utf-8")
    monkeypatch.setattr("ai_dev_launcher.services.updater.shutil.which", lambda command: "npm.cmd" if "npm" in command else None)
    service = PrivateToolUpdateService(tmp_path, lambda command, env: subprocess.CompletedProcess(command, 1, "", "network failed"))

    result = service.update_all()

    assert result["tools"][0]["status"] == "rolled_back"
    assert (target / "old.txt").read_text() == "working"


def test_successful_private_codex_update_swaps_verified_stage(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_dev_launcher.services.updater.os.name", "nt")
    monkeypatch.setattr("ai_dev_launcher.services.updater.shutil.which", lambda command: "npm.cmd" if "npm" in command else None)

    def runner(command, environment):
        if "--prefix" in command:
            prefix = Path(command[command.index("--prefix") + 1])
            executable = prefix / "node_modules" / ".bin" / "codex.cmd"
            executable.parent.mkdir(parents=True)
            executable.write_text("private", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    result = PrivateToolUpdateService(tmp_path, runner).update_all()

    assert result["tools"][0]["status"] == "updated"
    assert (tmp_path / "runtime" / "tools" / "codex" / "node_modules" / ".bin" / "codex.cmd").exists()


def test_automatic_updates_are_rate_limited_after_an_attempt(tmp_path):
    def runner(command, environment):
        return subprocess.CompletedProcess(command, 0, "ok", "")

    service = PrivateToolUpdateService(tmp_path, runner)
    service.root.mkdir(parents=True)
    headroom = service.root / "headroom"
    (headroom / "bin").mkdir(parents=True)
    (headroom / "bin" / "headroom.exe").write_text("shim", encoding="utf-8")
    python = headroom / "packages" / "headroom-ai" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("python", encoding="utf-8")
    (service.root / "update-state.json").write_text('{"last_attempt":"2999-01-01T00:00:00+00:00"}', encoding="utf-8")

    result = service.update_all()

    assert result["tools"] == []
    assert "already ran" in result["skipped"]


def test_headroom_update_pins_working_onnx_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_dev_launcher.services.updater.os.name", "nt")
    monkeypatch.setattr("ai_dev_launcher.services.updater.shutil.which", lambda command: "uv.exe" if "uv" in command else None)
    commands = []

    def runner(command, environment):
        commands.append(command)
        if command[0] == "uv.exe":
            bin_dir = Path(environment["UV_TOOL_BIN_DIR"])
            tool_dir = Path(environment["UV_TOOL_DIR"]) / "headroom-ai" / "Scripts"
            bin_dir.mkdir(parents=True, exist_ok=True)
            tool_dir.mkdir(parents=True, exist_ok=True)
            (bin_dir / "headroom.exe").write_text("shim", encoding="utf-8")
            (tool_dir / "python.exe").write_text("python", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    result = PrivateToolUpdateService(tmp_path, runner).update_all()

    headroom_result = next(item for item in result["tools"] if item["key"] == "headroom")
    assert headroom_result["status"] == "updated"
    install_command = next(command for command in commands if command[0] == "uv.exe")
    assert "onnxruntime==1.19.2" in install_command
    assert install_command[install_command.index("--python") + 1] == "3.12"
