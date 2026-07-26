"""Command-line interface for AI Dev Launcher."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from ai_dev_launcher import __version__
from ai_dev_launcher.config import ConfigStore, default_config_dir
from ai_dev_launcher.errors import LauncherError
from ai_dev_launcher.services import (
    LaunchService,
    ProjectPreparationService,
    ProjectService,
    ToolDetectionService,
)

app = typer.Typer(
    name="ai-dev",
    help="Manage local AI development projects on Windows.",
    invoke_without_command=True,
)
projects_app = typer.Typer(help="Register and manage projects.", no_args_is_help=True)
config_app = typer.Typer(help="Inspect launcher configuration.", no_args_is_help=True)
app.add_typer(projects_app, name="projects")
app.add_typer(config_app, name="config")


def _store() -> ConfigStore:
    return ConfigStore(default_config_dir())


def _service() -> ProjectService:
    return ProjectService(_store())


def _tool_service() -> ToolDetectionService:
    return ToolDetectionService()


def _preparation_service() -> ProjectPreparationService:
    return ProjectPreparationService()


def _launch_service() -> LaunchService:
    return LaunchService(tool_service=_tool_service())


def _resolve_launch_target(
    project_service: ProjectService,
    name: str | None,
    extra_args: tuple[str, ...],
):
    """Resolve the project while preserving leading option arguments.

    Click may bind the first value after ``--`` to the optional project
    argument. A leading dash cannot be a useful project name here, so treat it
    as a Codex argument and use the configured default project.
    """

    if name and name.startswith("-"):
        return project_service.get_default_project(), (name, *extra_args)
    project = (
        project_service.get_project(name)
        if name
        else project_service.get_default_project()
    )
    return project, extra_args


def _fail(exc: Exception) -> None:
    typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"AI Dev Launcher {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the installed version.",
        ),
    ] = None,
) -> None:
    """Manage local AI development projects on Windows."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@projects_app.command("add")
def add_project(
    name: Annotated[str, typer.Argument(help="Unique project name.")],
    path: Annotated[
        Path,
        typer.Argument(
            help="Existing project directory.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
) -> None:
    """Register an existing project directory."""

    try:
        project = _service().add_project(name, path)
    except (LauncherError, ValueError) as exc:
        _fail(exc)
        return
    typer.secho(f"Registered '{project.name}'", fg=typer.colors.GREEN)
    typer.echo(project.path)


@projects_app.command("list")
def list_projects() -> None:
    """List registered projects."""

    try:
        config = _store().load()
        projects = _service().list_projects()
    except LauncherError as exc:
        _fail(exc)
        return

    if not projects:
        typer.echo("No projects registered.")
        return
    for project in projects:
        marker = "*" if project.name == config.default_project else " "
        typer.echo(f"{marker} {project.name}\t{project.path}")


@projects_app.command("show")
def show_project(
    name: Annotated[str, typer.Argument(help="Registered project name.")],
) -> None:
    """Show one registered project as JSON."""

    try:
        project = _service().get_project(name)
    except LauncherError as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(project.to_dict(), indent=2, ensure_ascii=False))


@projects_app.command("remove")
def remove_project(
    name: Annotated[str, typer.Argument(help="Registered project name.")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Remove without confirmation.")
    ] = False,
) -> None:
    """Unregister a project without deleting its files."""

    if not force and not typer.confirm(f"Unregister project '{name}'?"):
        typer.echo("Cancelled.")
        return
    try:
        project = _service().remove_project(name)
    except LauncherError as exc:
        _fail(exc)
        return
    typer.secho(f"Unregistered '{project.name}'", fg=typer.colors.GREEN)


@projects_app.command("default")
def set_default_project(
    name: Annotated[str, typer.Argument(help="Registered project name.")],
) -> None:
    """Set the default project."""

    try:
        project = _service().set_default(name)
    except LauncherError as exc:
        _fail(exc)
        return
    typer.secho(f"Default project: {project.name}", fg=typer.colors.GREEN)


@projects_app.command("prepare")
def prepare_project(
    name: Annotated[str, typer.Argument(help="Registered project name.")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview without changing files.")
    ] = False,
    initialize_git: Annotated[
        bool,
        typer.Option(
            "--git-init/--no-git-init",
            help="Initialize Git when the project is not already a repository.",
        ),
    ] = True,
    as_json: Annotated[
        bool, typer.Option("--json", help="Return machine-readable JSON.")
    ] = False,
) -> None:
    """Prepare AGENTS.md, launcher metadata, and optional Git."""

    try:
        project = _service().get_project(name)
        result = _preparation_service().prepare(
            project,
            dry_run=dry_run,
            initialize_git=initialize_git,
        )
    except LauncherError as exc:
        _fail(exc)
        return

    if as_json:
        typer.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return
    heading = "Preparation plan" if dry_run else "Project prepared"
    typer.secho(f"{heading}: {project.name}", fg=typer.colors.GREEN)
    for action in result.actions:
        typer.echo(f"[{action.status.upper()}] {action.kind}: {action.detail}")
        typer.echo(f"           {action.target}")


@config_app.command("path")
def config_path() -> None:
    """Print the configuration file path."""

    typer.echo(_store().path)


@config_app.command("show")
def show_config() -> None:
    """Print the current configuration as JSON."""

    try:
        config = _store().load()
    except LauncherError as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))


def _render_tool_results(*, as_json: bool) -> tuple[int, int]:
    results = _tool_service().check_all()
    if as_json:
        typer.echo(
            json.dumps(
                {"tools": [result.to_dict() for result in results]},
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        for result in results:
            if result.is_available:
                typer.secho(f"[OK]      {result.display_name}", fg=typer.colors.GREEN)
                typer.echo(f"          {result.version or 'Version unknown'}")
                typer.echo(f"          {result.path}")
            else:
                if result.required:
                    label = (
                        "[MISSING]" if result.status.value == "missing" else "[ERROR]  "
                    )
                    color = typer.colors.RED
                else:
                    label = "[OPTIONAL]"
                    color = typer.colors.YELLOW
                typer.secho(f"{label} {result.display_name}", fg=color)
                typer.echo(f"          {result.detail}")
                typer.echo(f"          {result.install_hint}")
    required_issues = sum(
        not result.is_available and result.required for result in results
    )
    all_issues = sum(not result.is_available for result in results)
    return required_issues, all_issues


@app.command("status")
def tool_status(
    as_json: Annotated[
        bool, typer.Option("--json", help="Return machine-readable JSON.")
    ] = False,
) -> None:
    """Show availability and versions of supported development tools."""

    _, missing_count = _render_tool_results(as_json=as_json)
    if not as_json:
        typer.echo()
        typer.echo(
            f"{5 - missing_count}/5 tools available; "
            f"{missing_count} need attention."
        )


@app.command("doctor")
def doctor(
    as_json: Annotated[
        bool, typer.Option("--json", help="Return machine-readable JSON.")
    ] = False,
) -> None:
    """Validate supported tools; fail when any tool needs attention."""

    issue_count, optional_and_required_issues = _render_tool_results(as_json=as_json)
    if issue_count:
        if not as_json:
            typer.secho(
                f"\nDoctor found {issue_count} tool issue(s).",
                fg=typer.colors.RED,
            )
        raise typer.Exit(code=1)
    if not as_json:
        optional_issues = optional_and_required_issues - issue_count
        suffix = (
            f" ({optional_issues} optional tool(s) not installed)"
            if optional_issues
            else ""
        )
        typer.secho(f"\nAll required tools are ready{suffix}.", fg=typer.colors.GREEN)


@app.command(
    "launch",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def launch(
    ctx: typer.Context,
    name: Annotated[
        str | None,
        typer.Argument(help="Registered project name; defaults to the selected project."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show preparation and launch plans only."),
    ] = False,
    prepare: Annotated[
        bool,
        typer.Option(
            "--prepare/--no-prepare",
            help="Prepare AGENTS.md, metadata, and Git before launch.",
        ),
    ] = True,
    use_headroom: Annotated[
        bool,
        typer.Option(
            "--headroom/--no-headroom",
            help="Route Codex through Headroom.",
        ),
    ] = True,
) -> None:
    """Prepare a project and launch its Codex development environment.

    Add ``--`` before arguments that should be passed directly to Codex.
    """

    try:
        project_service = _service()
        project, codex_args = _resolve_launch_target(
            project_service,
            name,
            tuple(ctx.args),
        )
        if prepare:
            preparation = _preparation_service().prepare(
                project,
                dry_run=dry_run,
                initialize_git=True,
            )
            for action in preparation.actions:
                typer.echo(
                    f"[{action.status.upper()}] {action.kind}: {action.detail}"
                )

        launcher = _launch_service()
        plan = launcher.build_plan(
            project,
            use_headroom=use_headroom,
            codex_args=codex_args,
        )
    except LauncherError as exc:
        _fail(exc)
        return

    if dry_run:
        typer.echo(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
        return

    mode = "Codex + Headroom" if use_headroom else "Codex"
    typer.secho(
        f"Launching {mode} for '{project.name}' in {project.path}",
        fg=typer.colors.GREEN,
    )
    try:
        exit_code = launcher.execute(plan)
    except LauncherError as exc:
        _fail(exc)
        return
    if exit_code:
        typer.secho(
            f"Development environment exited with code {exit_code}.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
