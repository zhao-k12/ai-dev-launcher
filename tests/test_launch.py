from __future__ import annotations

import os

import pytest

from ai_dev_launcher.domain.project import Project
from ai_dev_launcher.domain.tool import ToolResult, ToolStatus
from ai_dev_launcher.errors import LaunchError
from ai_dev_launcher.services.launch import LaunchService, find_node_runtime_dir


class FakeTools:
    def __init__(self, results):
        self.results = results

    def check_all(self):
        return self.results


def _available(key, name, path):
    return ToolResult(
        key=key,
        display_name=name,
        status=ToolStatus.AVAILABLE,
        path=str(path),
        version="1.0",
    )


def test_headroom_plan_wraps_codex_without_extra_tools(tmp_path):
    headroom = tmp_path / "bin" / "headroom.exe"
    codex = tmp_path / "npm" / "codex.cmd"
    project = Project("sample", str(tmp_path), "now")
    service = LaunchService(
        tool_service=FakeTools(
            [
                _available("headroom", "Headroom", headroom),
                _available("codex", "Codex", codex),
            ]
        )
    )

    plan = service.build_plan(project, codex_args=("fix the bug",))

    assert plan.command == (
        str(headroom),
        "wrap",
        "codex",
        "--no-context-tool",
        "--no-mcp",
        "--no-tokensave",
        "--no-serena",
        "--",
        "fix the bug",
    )
    assert plan.use_headroom is True


def test_direct_codex_plan_does_not_require_headroom(tmp_path):
    codex = tmp_path / "codex.cmd"
    project = Project("sample", str(tmp_path), "now")
    service = LaunchService(
        tool_service=FakeTools([_available("codex", "Codex", codex)])
    )

    plan = service.build_plan(project, use_headroom=False, codex_args=("--version",))

    assert plan.command == (str(codex), "--version")


def test_missing_headroom_has_actionable_error(tmp_path):
    codex = tmp_path / "codex.cmd"
    project = Project("sample", str(tmp_path), "now")
    service = LaunchService(
        tool_service=FakeTools(
            [
                _available("codex", "Codex", codex),
                ToolResult(
                    key="headroom",
                    display_name="Headroom",
                    status=ToolStatus.MISSING,
                    install_hint="Install Headroom",
                ),
            ]
        )
    )

    with pytest.raises(LaunchError, match="Install Headroom"):
        service.build_plan(project)


def test_execute_sets_path_privacy_and_forwards_exit_code(tmp_path):
    captured = {}

    def runner(command, cwd, environment):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["environment"] = environment
        return 17

    codex = tmp_path / "tools" / "codex.cmd"
    project = Project("sample", str(tmp_path), "now")
    service = LaunchService(
        tool_service=FakeTools([_available("codex", "Codex", codex)]),
        runner=runner,
        environment={"PATH": "existing"},
    )
    plan = service.build_plan(project, use_headroom=False)

    exit_code = service.execute(plan)

    assert exit_code == 17
    assert captured["cwd"] == tmp_path
    assert captured["environment"]["PATH"].startswith(str(codex.parent) + os.pathsep)
    assert captured["environment"]["HEADROOM_TELEMETRY"] == "off"
    assert captured["environment"]["AI_DEV_LAUNCHER_ISOLATED"] == "1"
    assert captured["environment"]["HEADROOM_UPDATE_CHECK"] == "off"


def test_start_uses_detached_starter_and_returns_pid(tmp_path):
    captured = {}

    def starter(command, cwd, environment):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["environment"] = environment
        return 4242

    codex = tmp_path / "codex.cmd"
    project = Project("sample", str(tmp_path), "now")
    service = LaunchService(
        tool_service=FakeTools([_available("codex", "Codex", codex)]),
        starter=starter,
        environment={"PATH": "existing"},
    )
    plan = service.build_plan(project, use_headroom=False)

    process_id = service.start(plan)

    assert process_id == 4242
    assert captured["cwd"] == tmp_path
    assert captured["environment"]["HEADROOM_TELEMETRY"] == "off"


def test_missing_project_directory_is_rejected(tmp_path):
    project = Project("missing", str(tmp_path / "missing"), "now")
    service = LaunchService(tool_service=FakeTools([]))

    with pytest.raises(LaunchError, match="does not exist"):
        service.build_plan(project)


@pytest.mark.skipif(os.name != "nt", reason="Windows Node discovery")
def test_node_runtime_is_found_when_desktop_path_is_stale(tmp_path):
    node = tmp_path / "Programs" / "nodejs" / "node.exe"
    node.parent.mkdir(parents=True)
    node.write_bytes(b"node")

    result = find_node_runtime_dir(
        {"PATH": "", "ProgramFiles": str(tmp_path / "Programs")}
    )

    assert result == node.parent
