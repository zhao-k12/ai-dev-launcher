"""Codex and Headroom process orchestration."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

from ai_dev_launcher.domain.launch import LaunchPlan
from ai_dev_launcher.domain.project import Project
from ai_dev_launcher.domain.tool import ToolResult
from ai_dev_launcher.errors import LaunchError
from ai_dev_launcher.services.tools import ToolDetectionService

ProcessRunner = Callable[[list[str], Path, Mapping[str, str]], int]
ProcessStarter = Callable[[list[str], Path, Mapping[str, str]], int]


def _run_interactive(
    command: list[str],
    cwd: Path,
    environment: Mapping[str, str],
) -> int:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=dict(environment),
            check=False,
        )
        return completed.returncode
    except KeyboardInterrupt:
        return 130


def _start_detached(
    command: list[str],
    cwd: Path,
    environment: Mapping[str, str],
) -> int:
    options: dict[str, object] = {
        "cwd": cwd,
        "env": dict(environment),
    }
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    else:
        options["start_new_session"] = True
    process = subprocess.Popen(command, **options)  # noqa: S603 - trusted tool paths
    return process.pid


class LaunchService:
    """Build and execute a local AI development environment plan."""

    def __init__(
        self,
        *,
        tool_service: ToolDetectionService | None = None,
        runner: ProcessRunner = _run_interactive,
        starter: ProcessStarter = _start_detached,
        environment: Mapping[str, str] | None = None,
        private_tool_root: Path | None = None,
    ) -> None:
        if tool_service is None and private_tool_root is not None:
            private_bins = [
                private_tool_root / "codex" / "node_modules" / ".bin",
                private_tool_root / "headroom" / "bin",
            ]
            detection_environment = dict(environment or os.environ)
            detection_environment["PATH"] = os.pathsep.join(
                [*(str(path) for path in private_bins), detection_environment.get("PATH", "")]
            )
            tool_service = ToolDetectionService(environment=detection_environment)
        self.tool_service = tool_service or ToolDetectionService()
        self.runner = runner
        self.starter = starter
        self.environment = environment

    def build_plan(
        self,
        project: Project,
        *,
        use_headroom: bool = True,
        codex_args: tuple[str, ...] = (),
    ) -> LaunchPlan:
        root = Path(project.path)
        if not root.is_dir():
            raise LaunchError(f"Project directory does not exist: {root}")

        results = {result.key: result for result in self.tool_service.check_all()}
        codex = self._require_tool(results, "codex", "Codex")
        headroom = (
            self._require_tool(results, "headroom", "Headroom")
            if use_headroom
            else None
        )

        if headroom:
            command = (
                str(headroom.path),
                "wrap",
                "codex",
                "--no-context-tool",
                "--no-mcp",
                "--no-tokensave",
                "--no-serena",
                "--",
                *codex_args,
            )
            tool_paths = (str(Path(headroom.path).parent), str(Path(codex.path).parent))
        else:
            command = (str(codex.path), *codex_args)
            tool_paths = (str(Path(codex.path).parent),)

        path_prepend = tuple(dict.fromkeys(tool_paths))
        overrides = (
            ("HEADROOM_TELEMETRY", "off"),
            ("HEADROOM_UPDATE_CHECK", "off"),
            ("AI_DEV_LAUNCHER_ISOLATED", "1"),
        )
        return LaunchPlan(
            project=project.name,
            cwd=str(root),
            command=command,
            use_headroom=use_headroom,
            path_prepend=path_prepend,
            environment_overrides=overrides,
        )

    def execute(self, plan: LaunchPlan) -> int:
        environment = self._launch_environment(plan)
        try:
            return self.runner(list(plan.command), Path(plan.cwd), environment)
        except OSError as exc:
            raise LaunchError(f"Could not start development environment: {exc}") from exc

    def start(self, plan: LaunchPlan) -> int:
        """Start a visible independent session and return its process id."""

        environment = self._launch_environment(plan)
        try:
            return self.starter(list(plan.command), Path(plan.cwd), environment)
        except OSError as exc:
            raise LaunchError(f"Could not start development environment: {exc}") from exc

    def _launch_environment(self, plan: LaunchPlan) -> dict[str, str]:
        environment = dict(self.environment or os.environ)
        current_path = environment.get("PATH", "")
        prefix = os.pathsep.join(plan.path_prepend)
        environment["PATH"] = (
            f"{prefix}{os.pathsep}{current_path}" if current_path else prefix
        )
        environment.update(dict(plan.environment_overrides))
        return environment

    @staticmethod
    def _require_tool(
        results: dict[str, ToolResult],
        key: str,
        display_name: str,
    ) -> ToolResult:
        result = results.get(key)
        if result is None or not result.is_available or not result.path:
            hint = result.install_hint if result else None
            suffix = f" {hint}" if hint else ""
            raise LaunchError(f"{display_name} is required but unavailable.{suffix}")
        return result
