"""Safe, repeatable project preparation."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from ai_dev_launcher.domain.preparation import PreparationAction, PreparationResult
from ai_dev_launcher.domain.project import Project
from ai_dev_launcher.errors import PreparationError

BEGIN_MARKER = "<!-- AI-DEV-LAUNCHER:BEGIN -->"
END_MARKER = "<!-- AI-DEV-LAUNCHER:END -->"

GitRunner = Callable[[Path], subprocess.CompletedProcess[str]]


def _run_git_init(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "init"],
        cwd=path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )


def _managed_agents_block(project: Project) -> str:
    return f"""\
{BEGIN_MARKER}
## AI Dev Launcher

Project: `{project.name}`

### Working agreement

- Work only inside this project unless the user explicitly expands the scope.
- Inspect existing files and tests before changing behavior.
- Preserve unrelated user changes.
- Prefer small, modular changes and verify them with the project's tests.
- Never commit secrets, generated credentials, or local environment files.
- Record project-specific build, test, lint, and run commands below as they become known.

### Project commands

- Build: not configured
- Test: not configured
- Lint: not configured
- Run: not configured
{END_MARKER}
"""


def _merge_agents(existing: str, managed_block: str) -> str:
    begin = existing.find(BEGIN_MARKER)
    end = existing.find(END_MARKER)
    if begin == -1 and end == -1:
        prefix = existing.rstrip()
        return f"{prefix}\n\n{managed_block}" if prefix else managed_block
    if begin == -1 or end == -1 or end < begin:
        raise PreparationError(
            "AGENTS.md contains an incomplete AI Dev Launcher marker block"
        )
    end += len(END_MARKER)
    return existing[:begin] + managed_block.rstrip() + existing[end:]


class ProjectPreparationService:
    """Initialize launcher metadata, AGENTS.md, and optionally Git."""

    def __init__(self, *, git_runner: GitRunner = _run_git_init) -> None:
        self.git_runner = git_runner

    def prepare(
        self,
        project: Project,
        *,
        dry_run: bool = False,
        initialize_git: bool = True,
    ) -> PreparationResult:
        root = Path(project.path)
        if not root.is_dir():
            raise PreparationError(f"Project directory does not exist: {root}")

        actions: list[PreparationAction] = []
        metadata_dir = root / ".ai-dev-launcher"
        agents_path = root / "AGENTS.md"
        existing_agents = (
            agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
        )
        merged_agents = _merge_agents(existing_agents, _managed_agents_block(project))

        if existing_agents == merged_agents:
            actions.append(
                PreparationAction(
                    "agents", str(agents_path), "unchanged", "Managed block is current"
                )
            )
        else:
            if existing_agents:
                backup_path = (
                    metadata_dir
                    / "backups"
                    / f"AGENTS.md.{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}.bak"
                )
                actions.append(
                    PreparationAction(
                        "backup",
                        str(backup_path),
                        "planned" if dry_run else "created",
                        "Backup existing AGENTS.md",
                    )
                )
                if not dry_run:
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    backup_path.write_text(existing_agents, encoding="utf-8")
            actions.append(
                PreparationAction(
                    "agents",
                    str(agents_path),
                    "planned" if dry_run else "written",
                    "Create or update the managed AGENTS.md block",
                )
            )
            if not dry_run:
                agents_path.write_text(merged_agents, encoding="utf-8")

        git_dir = root / ".git"
        git_initialized = git_dir.exists()
        if initialize_git and not git_initialized:
            actions.append(
                PreparationAction(
                    "git",
                    str(git_dir),
                    "planned" if dry_run else "initialized",
                    "Initialize a Git repository",
                )
            )
            if not dry_run:
                try:
                    result = self.git_runner(root)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise PreparationError(f"Git initialization failed: {exc}") from exc
                if result.returncode != 0:
                    detail = (result.stderr or result.stdout).strip()
                    raise PreparationError(
                        f"Git initialization failed: {detail or result.returncode}"
                    )
                git_initialized = True
        elif initialize_git:
            actions.append(
                PreparationAction(
                    "git", str(git_dir), "unchanged", "Git repository already exists"
                )
            )
        else:
            actions.append(
                PreparationAction(
                    "git", str(git_dir), "skipped", "Git initialization disabled"
                )
            )

        metadata_path = metadata_dir / "project.json"
        metadata = {
            "schema_version": 1,
            "name": project.name,
            "path": project.path,
            "prepared_at": datetime.now(UTC).isoformat(),
            "agents_file": str(agents_path),
            "git_initialized": git_initialized,
        }
        actions.append(
            PreparationAction(
                "metadata",
                str(metadata_path),
                "planned" if dry_run else "written",
                "Write AI Dev Launcher project metadata",
            )
        )
        if not dry_run:
            metadata_dir.mkdir(parents=True, exist_ok=True)
            temporary = metadata_path.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temporary.replace(metadata_path)

        return PreparationResult(project.name, dry_run, tuple(actions))
