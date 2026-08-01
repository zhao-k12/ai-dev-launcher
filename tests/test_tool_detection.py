from __future__ import annotations

import subprocess

from ai_dev_launcher.domain.tool import ToolSpec, ToolStatus
from ai_dev_launcher.services.tools import ToolDetectionService, executable_candidates


def _spec() -> ToolSpec:
    return ToolSpec(
        key="sample",
        display_name="Sample",
        commands=("sample",),
        version_args=("--version",),
        install_hint="Install Sample",
    )


def test_executable_candidates_preserves_path_order(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "sample").write_text("", encoding="utf-8")
    (second / "sample").write_text("", encoding="utf-8")

    result = executable_candidates(
        "sample",
        {"PATH": f"{first}{__import__('os').pathsep}{second}", "PATHEXT": ""},
    )

    assert result == [(first / "sample").resolve(), (second / "sample").resolve()]


def test_windows_user_bins_are_fallback_locations(tmp_path, monkeypatch):
    user_profile = tmp_path / "user"
    local_bin = user_profile / ".local" / "bin"
    local_bin.mkdir(parents=True)
    executable = local_bin / "sample.exe"
    executable.write_text("", encoding="utf-8")
    monkeypatch.setattr("ai_dev_launcher.services.tools.os.name", "nt")

    result = executable_candidates(
        "sample",
        {
            "PATH": "",
            "PATHEXT": ".EXE",
            "USERPROFILE": str(user_profile),
            "APPDATA": str(user_profile / "AppData" / "Roaming"),
        },
    )

    assert executable.resolve() in result


def test_available_tool_reports_path_and_version(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "sample"
    executable.write_text("", encoding="utf-8")

    def runner(command, timeout):
        return subprocess.CompletedProcess(command, 0, "sample 1.2.3\n", "")

    service = ToolDetectionService(
        [_spec()],
        runner=runner,
        environment={"PATH": str(bin_dir), "PATHEXT": ""},
    )

    result = service.check_all()[0]

    assert result.status is ToolStatus.AVAILABLE
    assert result.version == "sample 1.2.3"
    assert result.path == str(executable.resolve())


def test_missing_tool_has_install_hint():
    service = ToolDetectionService(
        [_spec()],
        environment={"PATH": "", "PATHEXT": ""},
    )

    result = service.check_all()[0]

    assert result.status is ToolStatus.MISSING
    assert result.install_hint == "Install Sample"


def test_inaccessible_candidate_falls_through_to_next(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    bad = first / "sample"
    good = second / "sample"
    bad.write_text("", encoding="utf-8")
    good.write_text("", encoding="utf-8")

    def runner(command, timeout):
        if command[0] == str(bad.resolve()):
            raise PermissionError("access denied")
        return subprocess.CompletedProcess(command, 0, "sample 2.0", "")

    service = ToolDetectionService(
        [_spec()],
        runner=runner,
        environment={
            "PATH": f"{first}{__import__('os').pathsep}{second}",
            "PATHEXT": "",
        },
    )

    result = service.check_all()[0]

    assert result.status is ToolStatus.AVAILABLE
    assert result.path == str(good.resolve())


def test_nonzero_version_command_is_error(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "sample").write_text("", encoding="utf-8")

    def runner(command, timeout):
        return subprocess.CompletedProcess(command, 7, "", "broken")

    service = ToolDetectionService(
        [_spec()],
        runner=runner,
        environment={"PATH": str(bin_dir), "PATHEXT": ""},
    )

    result = service.check_all()[0]

    assert result.status is ToolStatus.ERROR
    assert "exited with 7" in (result.detail or "")


def test_timeout_is_error(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "sample").write_text("", encoding="utf-8")

    def runner(command, timeout):
        raise subprocess.TimeoutExpired(command, timeout)

    service = ToolDetectionService(
        [_spec()],
        runner=runner,
        environment={"PATH": str(bin_dir), "PATHEXT": ""},
    )

    result = service.check_all()[0]

    assert result.status is ToolStatus.ERROR
    assert "timed out" in (result.detail or "")


def test_default_version_check_uses_detection_environment(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "sample").write_text("", encoding="utf-8")
    captured = {}

    def run(command, **options):
        captured["environment"] = options.get("env")
        return subprocess.CompletedProcess(command, 0, "sample 3.0", "")

    monkeypatch.setattr("ai_dev_launcher.services.tools.subprocess.run", run)
    environment = {"PATH": str(bin_dir), "PATHEXT": "", "NODE_HOME": "private"}

    result = ToolDetectionService([_spec()], environment=environment).check_all()[0]

    assert result.status is ToolStatus.AVAILABLE
    assert captured["environment"] == environment
