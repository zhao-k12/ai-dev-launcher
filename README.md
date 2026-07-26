# AI Dev Launcher

AI Dev Launcher is a Windows-first Python CLI for managing local AI development
projects and, in later phases, launching a complete tool-assisted development
environment.

## Desktop GUI

The Electron + Vue 3 desktop interface is under `desktop/`. GUI Phase 1
includes:

- Windows 11 Fluent-style project workspace
- Empty, loading, success, and error states
- Add projects with a native folder picker
- Select projects and inspect their details
- Set a default project
- Remove a project registration without deleting its files
- A secure Electron preload/IPC boundary
- A JSON bridge that reuses the existing Python services and configuration

GUI Phase 2 adds:

- Automatic Git, Codex, Headroom, jCodeMunch, and Repomix detection
- A detailed environment panel with versions, paths, and install guidance
- Required versus optional tool states
- One-click Codex + Headroom startup in an independent terminal window
- Launch readiness checks and clear success/failure feedback
- Headroom telemetry and update checks remain disabled by the Python core

GUI Phase 3 adds:

- A three-step project initialization wizard
- Git initialization as an explicit user option
- Mandatory dry-run preview before changes are applied
- Safe AGENTS.md managed-block updates and timestamped backups
- `.ai-dev-launcher/project.json` metadata generation
- Clear per-action results and completion feedback

### Windows installer

The release installer is generated at:

```text
desktop\release\AI-Dev-Launcher-Setup-1.0.0.exe
```

It installs for the current Windows user, creates Start menu and desktop
shortcuts, and bundles the Python application core. The installed GUI does not
depend on this source directory or its virtual environment. Git, Codex, and
Headroom remain external development tools and are detected from the user's
machine.

The installer is not code-signed, so Windows may show an unknown-publisher
warning. No administrator account is required for the default per-user install.

Build a fresh installer:

```powershell
.\.venv\Scripts\pyinstaller.exe --clean --noconfirm --onefile --name ai-dev-core --paths src --distpath desktop\python-dist --workpath work\pyinstaller --specpath work\pyinstaller src\ai_dev_launcher\bridge.py
cd desktop
npm install
npm run package:win
```

Run the desktop app for development:

```powershell
cd desktop
npm install
npm run dev
```

Desktop verification:

```powershell
npm test
npm run build
npm run test:e2e
```

## Current status: Phase 4

Phase 1 provides:

- A packaged `ai-dev` command built with Typer
- A modular application structure
- Registration of existing project directories
- Project listing, lookup, default selection, and removal
- User-level JSON configuration with schema validation and atomic writes
- Pytest coverage for configuration, project management, and basic CLI behavior

Phase 2 adds:

- Detection of Git, Codex, Headroom, jCodeMunch, and Repomix
- Executable path and version reporting
- Windows PATH shadowing protection by trying every matching executable
- Fallback discovery in common user-level CLI directories when PATH is stale
- Actionable installation guidance for missing or broken tools
- Human-readable and JSON status output
- A strict doctor command suitable for scripts and CI

Phase 3 adds:

- Repeatable project preparation through `ai-dev projects prepare`
- Managed `AGENTS.md` generation without replacing user-authored instructions
- Timestamped backups before existing `AGENTS.md` files are changed
- Launcher metadata under `.ai-dev-launcher/project.json`
- Optional automatic `git init`
- A no-write `--dry-run` preview and JSON output

Phase 4 adds:

- One-command project startup with `ai-dev launch`
- Automatic default-project selection
- Automatic Phase 3 preparation before startup
- Codex routing through Headroom with privacy settings enforced
- Codex argument passthrough after `--`
- Direct Codex mode when Headroom is intentionally disabled
- Child-process exit-code forwarding and Ctrl+C handling
- Dry-run launch plans that expose commands without running them

## Requirements

- Windows 10 or 11
- Python 3.11 or newer
- PowerShell

## Install for development

```powershell
cd path\to\ai-dev-launcher
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

If PowerShell script execution is restricted, invoke the virtual environment's
Python executable directly as shown above; activation is optional.

## Install locally

From the project directory, install the CLI for the current Windows user:

```powershell
uv tool install .
```

Open a new PowerShell window and verify:

```powershell
ai-dev --version
ai-dev doctor
```

To reinstall an updated local build:

```powershell
uv tool install --force .
```

To remove the installed command:

```powershell
uv tool uninstall ai-dev-launcher
```

## Usage

Show the CLI help:

```powershell
ai-dev --help
```

Register a project:

```powershell
ai-dev projects add my-app C:\src\my-app
```

List projects (`*` marks the default):

```powershell
ai-dev projects list
```

Show project details:

```powershell
ai-dev projects show my-app
```

Choose the default project:

```powershell
ai-dev projects default my-app
```

Unregister a project:

```powershell
ai-dev projects remove my-app
```

This only changes the registry. It never deletes the project directory.

Inspect configuration:

```powershell
ai-dev config path
ai-dev config show
```

Check development tools:

```powershell
ai-dev status
ai-dev status --json
```

Run strict diagnostics:

```powershell
ai-dev doctor
```

`status` always exits successfully after displaying results. `doctor` exits
with code 1 when a required tool is missing or cannot report its version.
jCodeMunch and Repomix are optional: their absence is reported but does not
fail `doctor`. Neither command installs software or changes system
configuration.

Prepare a registered project:

```powershell
ai-dev projects prepare my-app --dry-run
ai-dev projects prepare my-app
```

Skip Git initialization when needed:

```powershell
ai-dev projects prepare my-app --no-git-init
```

Preparation creates or updates a marker-delimited section in `AGENTS.md`,
preserving instructions outside that section. Existing files are backed up
under `.ai-dev-launcher/backups/` before modification. Re-running preparation
is safe and does not duplicate the managed block.

Launch the default project's development environment:

```powershell
ai-dev launch
```

Launch a named project:

```powershell
ai-dev launch my-app
```

Pass arguments or a prompt directly to Codex:

```powershell
ai-dev launch my-app -- "Review this project and suggest the next task"
```

Preview everything without writing files or starting processes:

```powershell
ai-dev launch my-app --dry-run -- --version
```

Skip preparation or Headroom explicitly:

```powershell
ai-dev launch my-app --no-prepare
ai-dev launch my-app --no-headroom
```

The default Headroom launch disables automatic context-tool, tokensave, and
Serena installation. jCodeMunch and Repomix remain optional and are never
installed by `launch`.

On Windows, configuration is stored at:

```text
%LOCALAPPDATA%\AI Dev Launcher\config.json
```

## Architecture

```text
src/ai_dev_launcher/
├── cli.py                 # Typer commands and terminal presentation
├── errors.py              # Expected application errors
├── config/
│   ├── models.py          # Versioned configuration model
│   ├── paths.py           # Platform-aware configuration location
│   └── store.py           # Atomic JSON persistence
├── domain/
│   ├── preparation.py     # Preparation action/result models
│   ├── project.py         # Project entity
│   └── tool.py            # Tool detection models
└── services/
    ├── launch.py          # Codex/Headroom process orchestration
    ├── preparation.py     # Safe project preparation
    ├── projects.py        # Project management use cases
    └── tools.py           # Local tool discovery
```

The CLI depends on services, services depend on domain/configuration modules,
and lower layers do not import the CLI. This keeps future tool detection and
launcher orchestration independently testable.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Planned phases

All four planned implementation phases are complete. Further work should begin
only after user acceptance and may focus on packaging, installation, or new
requirements.

The phase plan is intentionally incremental and can be adjusted after each
phase review.

## Safety and data behavior

- Removing a project from the registry never removes project files.
- Configuration writes use a temporary file and atomic replacement.
- Project paths are normalized to absolute paths.
- Project names are unique without regard to letter case.
- `AGENTS.md` user content is preserved outside launcher-owned markers.
- Dry-run mode does not create or modify any project files.
- Launch mode forwards child exit codes and maps Ctrl+C to exit code 130.
- Headroom telemetry and update checks are disabled in launched sessions.

## License

MIT
