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
    service = PrivateToolUpdateService(tmp_path)
    service.root.mkdir(parents=True)
    (service.root / "update-state.json").write_text('{"last_attempt":"2999-01-01T00:00:00+00:00"}', encoding="utf-8")

    result = service.update_all()

    assert result["tools"] == []
    assert "already ran" in result["skipped"]
