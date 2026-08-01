from pathlib import Path


def test_windows_installer_preserves_projects_while_resetting_settings() -> None:
    root = Path(__file__).parents[1]
    script = (root / "desktop" / "build" / "installer.nsh").read_text(encoding="utf-8")
    package = (root / "desktop" / "package.json").read_text(encoding="utf-8")

    assert 'StrCmp $0 "${VERSION}" same_version_installed upgrade_existing_installation' in script
    assert 'MessageBox MB_OK|MB_ICONINFORMATION "AI Dev Launcher ${VERSION} 已安装。"' in script
    assert 'CopyFiles /SILENT "$LOCALAPPDATA\\AI Dev Launcher\\config.json"' in script
    assert 'RMDir /r "$LOCALAPPDATA\\AI Dev Launcher"' in script
    assert '"$LOCALAPPDATA\\AI Dev Launcher\\config.json"' in script
    assert ".codex" not in script
    assert '"include": "build/installer.nsh"' in package
