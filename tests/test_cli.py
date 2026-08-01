from __future__ import annotations

from typer.testing import CliRunner

from ai_dev_launcher.cli import _resolve_launch_target, app
from ai_dev_launcher.domain.tool import ToolResult, ToolStatus

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "AI Dev Launcher 2.0.2" in result.stdout


def test_no_args_shows_help():
    result = runner.invoke(app)

    assert result.exit_code == 0
    assert "Manage local AI development projects" in result.stdout


def test_status_reports_tools_without_failing(monkeypatch):
    results = [
        ToolResult(
            key="git",
            display_name="Git",
            status=ToolStatus.AVAILABLE,
            path="C:\\bin\\git.exe",
            version="git version 2.0",
        ),
        ToolResult(
            key="codex",
            display_name="Codex",
            status=ToolStatus.MISSING,
            detail="not found",
            install_hint="install codex",
        ),
    ]
    monkeypatch.setattr(
        "ai_dev_launcher.cli._tool_service",
        lambda: type("Service", (), {"check_all": lambda self: results})(),
    )

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "[OK]" in result.stdout
    assert "[MISSING]" in result.stdout


def test_doctor_fails_when_tool_is_missing(monkeypatch):
    results = [
        ToolResult(
            key="codex",
            display_name="Codex",
            status=ToolStatus.MISSING,
            detail="not found",
            install_hint="install codex",
        )
    ]
    monkeypatch.setattr(
        "ai_dev_launcher.cli._tool_service",
        lambda: type("Service", (), {"check_all": lambda self: results})(),
    )

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 1
    assert '"status": "missing"' in result.stdout


def test_doctor_allows_missing_optional_tool(monkeypatch):
    results = [
        ToolResult(
            key="repomix",
            display_name="Repomix",
            status=ToolStatus.MISSING,
            required=False,
            detail="not found",
            install_hint="install repomix",
        )
    ]
    monkeypatch.setattr(
        "ai_dev_launcher.cli._tool_service",
        lambda: type("Service", (), {"check_all": lambda self: results})(),
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "All required tools are ready" in result.stdout


def test_launch_leading_option_uses_default_project():
    project = object()

    class Projects:
        def get_default_project(self):
            return project

        def get_project(self, name):
            raise AssertionError("leading option must not be treated as a project")

    resolved, arguments = _resolve_launch_target(Projects(), "--version", ())

    assert resolved is project
    assert arguments == ("--version",)
