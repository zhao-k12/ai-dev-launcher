!ifndef BUILD_UNINSTALLER
Var resetLauncherSettings

!macro customInit
  StrCpy $resetLauncherSettings "0"
  ReadRegStr $0 HKCU "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
  StrCmp $0 "" installer_version_check_done
  StrCmp $0 "${VERSION}" same_version_installed upgrade_existing_installation

  same_version_installed:
    MessageBox MB_OK|MB_ICONINFORMATION "AI Dev Launcher ${VERSION} 已安装。" /SD IDOK
    Quit

  upgrade_existing_installation:
    StrCpy $resetLauncherSettings "1"

  installer_version_check_done:
!macroend

!macro customInstall
  StrCmp $resetLauncherSettings "1" 0 launcher_settings_reset_done
  InitPluginsDir
  ClearErrors
  CopyFiles /SILENT "$LOCALAPPDATA\AI Dev Launcher\config.json" "$PLUGINSDIR\ai-dev-launcher-projects.json"
  RMDir /r "$LOCALAPPDATA\AI Dev Launcher"
  IfFileExists "$PLUGINSDIR\ai-dev-launcher-projects.json" 0 launcher_settings_reset_done
  CreateDirectory "$LOCALAPPDATA\AI Dev Launcher"
  CopyFiles /SILENT "$PLUGINSDIR\ai-dev-launcher-projects.json" "$LOCALAPPDATA\AI Dev Launcher\config.json"
  launcher_settings_reset_done:
!macroend
!endif
