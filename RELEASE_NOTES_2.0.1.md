# AI Dev Launcher 2.0.1

Patch release fixing startup of the bundled Python core when AI Dev Launcher is opened from a parent process that contains stale PyInstaller `_PYI_*` environment variables.

- Clears inherited `_PYI_*` variables before invoking `ai-dev-core.exe`.
- Sets `PYINSTALLER_RESET_ENVIRONMENT=1` so every bridge invocation receives a valid extraction directory.
- Prevents `python312.dll` load failures referencing a deleted `%TEMP%\_MEI...` directory.

All v2.0 workbench features remain unchanged.
