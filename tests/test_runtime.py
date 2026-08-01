import json

from ai_dev_launcher.domain.tool import ToolResult, ToolStatus
from ai_dev_launcher.services.runtime import RuntimeService


class FakeTools:
    def check_all(self):
        return [
            ToolResult("codex", "Codex", ToolStatus.AVAILABLE, True, "codex", "C:/private/codex.cmd", "codex 2.0"),
            ToolResult("headroom", "Headroom", ToolStatus.AVAILABLE, True, "headroom", "C:/private/headroom.exe", "headroom 2.0"),
        ]


def test_runtime_bootstrap_recovers_only_launcher_state(tmp_path):
    runtime = RuntimeService(tmp_path, FakeTools())
    runtime.runtime_dir.mkdir(parents=True)
    runtime.state_path.write_text(json.dumps({"dirty": True}), encoding="utf-8")

    result = runtime.bootstrap()

    assert result["recovered"] is True
    assert result["status"] == "ready"
    assert result["isolation"] == "process"
    assert json.loads(runtime.state_path.read_text())["dirty"] is False


def test_isolated_environment_never_sets_global_codex_route():
    result = RuntimeService.isolated_environment({"PATH": "C:/bin"})

    assert result["AI_DEV_LAUNCHER_ISOLATED"] == "1"
    assert result["HEADROOM_TELEMETRY"] == "off"
    assert not any(key.startswith("CODEX_") for key in result)
