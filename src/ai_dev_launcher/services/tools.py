"""Local development tool discovery."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from ai_dev_launcher.domain.tool import ToolResult, ToolSpec, ToolStatus

TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        key="git",
        display_name="Git",
        commands=("git",),
        version_args=("--version",),
        install_hint="Install with: winget install --id Git.Git -e",
    ),
    ToolSpec(
        key="codex",
        display_name="Codex",
        commands=("codex",),
        version_args=("--version",),
        install_hint="Install with: npm install -g @openai/codex",
    ),
    ToolSpec(
        key="headroom",
        display_name="Headroom",
        commands=("headroom",),
        version_args=("--version",),
        install_hint='Install with: uv tool install "headroom-ai[proxy,mcp,code]"',
    ),
    ToolSpec(
        key="jcodemunch",
        display_name="jCodeMunch",
        commands=("jcodemunch-mcp", "jcodemunch"),
        version_args=("--version",),
        install_hint="Install with: uv tool install jcodemunch-mcp",
        required=False,
    ),
    ToolSpec(
        key="repomix",
        display_name="Repomix",
        commands=("repomix",),
        version_args=("--version",),
        install_hint="Install with: npm install -g repomix",
        required=False,
    ),
)

CommandRunner = Callable[[list[str], float], subprocess.CompletedProcess[str]]


def _run_command(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        encoding="utf-8",
        errors="replace",
    )


def executable_candidates(
    command: str,
    environment: Mapping[str, str] | None = None,
) -> list[Path]:
    """Return every matching executable on PATH, in PATH order.

    Trying all matches matters on Windows, where an inaccessible WindowsApps
    alias can shadow a working user-level CLI.
    """

    env = environment or os.environ
    path_entries = env.get("PATH", "").split(os.pathsep)
    if os.name == "nt":
        home = Path(env.get("USERPROFILE", str(Path.home())))
        app_data = Path(env.get("APPDATA", str(home / "AppData" / "Roaming")))
        common_user_bins = [
            home / ".local" / "bin",
            app_data / "npm",
        ]
        python_root = app_data / "Python"
        if python_root.is_dir():
            common_user_bins.extend(python_root.glob("Python*/Scripts"))
        path_entries.extend(str(path) for path in common_user_bins)
    if os.name == "nt":
        extensions = env.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
    else:
        extensions = ("",)

    command_path = Path(command)
    names: list[str]
    if command_path.suffix:
        names = [command]
    else:
        names = [command + extension.lower() for extension in extensions]
        names += [command + extension.upper() for extension in extensions]
        if "" not in extensions:
            names.append(command)

    found: list[Path] = []
    seen: set[str] = set()
    for entry in path_entries:
        if not entry:
            continue
        for name in names:
            candidate = Path(entry) / name
            try:
                if not candidate.is_file():
                    continue
            except OSError:
                continue
            identity = str(candidate.resolve()).casefold()
            if identity not in seen:
                seen.add(identity)
                found.append(candidate.resolve())
    return found


class ToolDetectionService:
    """Detect configured developer tools and query their versions."""

    def __init__(
        self,
        specs: Iterable[ToolSpec] = TOOL_SPECS,
        *,
        runner: CommandRunner = _run_command,
        environment: Mapping[str, str] | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.specs = tuple(specs)
        self.runner = runner
        self.environment = environment
        self.timeout = timeout

    def check_all(self) -> list[ToolResult]:
        return [self.check(spec) for spec in self.specs]

    def check(self, spec: ToolSpec) -> ToolResult:
        errors: list[str] = []
        discovered = False
        for command in spec.commands:
            for path in executable_candidates(command, self.environment):
                discovered = True
                try:
                    result = self.runner(
                        [str(path), *spec.version_args],
                        self.timeout,
                    )
                except subprocess.TimeoutExpired:
                    errors.append(f"{path}: version check timed out")
                    continue
                except OSError as exc:
                    errors.append(f"{path}: {exc}")
                    continue

                output = (result.stdout or result.stderr).strip()
                first_line = output.splitlines()[0] if output else None
                if result.returncode == 0:
                    return ToolResult(
                        key=spec.key,
                        display_name=spec.display_name,
                        status=ToolStatus.AVAILABLE,
                        required=spec.required,
                        command=command,
                        path=str(path),
                        version=first_line,
                    )
                errors.append(
                    f"{path}: exited with {result.returncode}"
                    + (f" ({first_line})" if first_line else "")
                )

        if discovered:
            return ToolResult(
                key=spec.key,
                display_name=spec.display_name,
                status=ToolStatus.ERROR,
                required=spec.required,
                detail="; ".join(errors),
                install_hint=spec.install_hint,
            )
        return ToolResult(
            key=spec.key,
            display_name=spec.display_name,
            status=ToolStatus.MISSING,
            required=spec.required,
            detail="No matching executable found on PATH",
            install_hint=spec.install_hint,
        )
