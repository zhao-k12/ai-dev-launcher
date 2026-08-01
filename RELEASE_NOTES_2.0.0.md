# AI Dev Launcher 2.0.0

AI Dev Launcher 2.0 upgrades the Windows launcher into an integrated AI development workbench.

## Highlights

- Create and initialize projects from a name and save location.
- Chat with Codex inside the app with streamed execution events, stop, follow-up, and project-local sessions.
- Standard project-only and explicitly warned full-access permission modes.
- File tree, UTF-8 preview, Git status and diff, accept/stage, and confirmed restore.
- Integrated project PowerShell with stdout, stderr, and exit codes.
- Headroom health and token-saving statistics.
- Automatic launcher-private Codex CLI and Headroom updates with validation, daily rate limiting, and rollback.
- Process-only Headroom routing with `--no-mcp`; Codex Desktop and global Codex configuration remain independent.

## Verification

- 51 Python tests passed.
- 8 Vue component tests passed.
- TypeScript and production build passed.
- Electron end-to-end project, environment, terminal, Git-change, and statistics flows passed.
- Packaged `win-unpacked` build passed project creation and PowerShell execution tests.
- Live Headroom + Codex JSONL smoke test completed using the existing Codex login.

## Windows

Download `AI-Dev-Launcher-Setup-2.0.0.exe`. The installer is per-user and currently unsigned, so Windows may show an unknown-publisher warning.
