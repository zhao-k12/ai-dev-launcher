# AI Dev Launcher 2.0

AI Dev Launcher is a Windows desktop AI development workbench built with Electron, Vue 3, TypeScript, and a reusable Python core.

## Features

- Create a project from a name and parent directory; Git, `AGENTS.md`, and launcher metadata are initialized automatically.
- Run Codex conversations inside the app with JSONL event streaming, stop support, follow-up via session resume, and project-local history.
- Choose standard `workspace-write` permission or an explicitly warned full-access mode.
- Browse project files, preview UTF-8 text, inspect Git status and diffs, stage accepted files, and restore tracked changes with confirmation.
- Run PowerShell commands in the project and display stdout, stderr, and exit codes.
- Read Headroom health and token-saving statistics from the project proxy.
- Automatically update launcher-private Codex CLI and Headroom installations with staged validation and rollback.

## Codex Desktop independence

This is a hard product invariant:

- AI Dev Launcher never changes Codex Desktop's permanent routing.
- Headroom is applied only to launcher-created child processes.
- `headroom wrap codex` is invoked with `--no-mcp`, `--no-context-tool`, `--no-tokensave`, and `--no-serena` to avoid global registration and installation side effects.
- No system proxy or global Codex configuration is written.
- Launcher-private tool updates do not replace the user's global Codex CLI.
- Codex Desktop remains usable when the launcher is closed, crashed, or uninstalled.

The launcher reuses the existing Codex login available to the CLI; no API key is required for the first release.

## Windows installer

Expected release artifact:

```text
desktop\release\AI-Dev-Launcher-Setup-2.0.0.exe
```

The per-user installer bundles the Python bridge. Git remains an external prerequisite. The installer is not code-signed, so Windows may display an unknown-publisher warning.

Build the installer:

```powershell
.\.venv\Scripts\pyinstaller.exe --clean --noconfirm --onefile --name ai-dev-core --paths src --distpath desktop\python-dist --workpath work\pyinstaller --specpath work\pyinstaller src\ai_dev_launcher\bridge.py
Set-Location desktop
npm.cmd install
npm.cmd run package:win
```

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Set-Location desktop
npm.cmd install
npm.cmd run dev
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
Set-Location desktop
npm.cmd test -- --run
npm.cmd run build
npm.cmd run test:e2e
```

## Configuration and migration

Configuration remains at:

```text
%LOCALAPPDATA%\AI Dev Launcher\config.json
```

The v2 application reads the v1 project registry directly. Existing projects remain registered. New conversations are stored per project by the desktop workspace.

Launcher-owned runtime files and private tools are stored below its application configuration directory. They do not replace user-global Codex or Headroom installations.

## Python CLI

The existing `ai-dev` commands remain available for compatibility:

```powershell
ai-dev --version
ai-dev status
ai-dev doctor
ai-dev projects list
ai-dev projects prepare my-project --dry-run
ai-dev launch my-project
```

jCodeMunch and Repomix remain optional and are never installed automatically.

## Safety

- File reads and Git actions are restricted to the selected project path.
- Standard Codex mode uses `workspace-write` sandboxing.
- Full access requires an explicit visible selection.
- Restoring a tracked file requires confirmation; untracked files are never automatically deleted.
- PowerShell runs with the project as its working directory and reports the exit code.
- Update staging and rollback operate only inside launcher-owned tool directories.

## License

MIT
