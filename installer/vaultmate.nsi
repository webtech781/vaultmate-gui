; =============================================================================
; VaultMate NSIS Installer Script
; Produces: VaultMate-Setup-{VERSION}-windows.exe
; Requires: NSIS 3.x + NsExec / INetC plugins
;
; WHAT THIS INSTALLER DOES:
;   1. Checks if Python 3.10+ is installed (downloads & installs if missing)
;   2. Downloads the VaultMate source from GitHub to C:\VaultMate (or chosen dir)
;   3. Runs build_windows.bat silently in the background (builds the .exe)
;   4. Creates Start Menu shortcut (always)
;   5. Creates Desktop shortcut (optional — user checkbox)
; =============================================================================

!define APP_NAME        "VaultMate"
!define APP_VERSION     "$%VAULTMATE_VERSION%"
!define APP_PUBLISHER   "webtech781"
!define APP_URL         "https://github.com/webtech781/vaultmate-gui"
!define GITHUB_ZIP_URL  "https://github.com/webtech781/vaultmate-gui/archive/refs/heads/main.zip"
!define APP_EXE         "VaultMate.exe"
!define DEFAULT_DIR     "C:\VaultMate"
!define PYTHON_URL      "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
!define REG_ROOT        "HKCU"
!define REG_KEY         "Software\VaultMate"

; ── Plugins ──────────────────────────────────────────────────────────────────
; INetC is needed for in-installer downloads. The CI step installs it via:
;   choco install nsis-inetc  -or-  copy INetC.dll to NSIS\Plugins\x86-unicode\
; NsExec is built into NSIS 3.x.
; ─────────────────────────────────────────────────────────────────────────────

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "..\VaultMate-Setup-${APP_VERSION}-windows.exe"
InstallDir "${DEFAULT_DIR}"
InstallDirRegKey ${REG_ROOT} "${REG_KEY}" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

; ── Custom property for Desktop Shortcut ─────────────────────────────────────
Var DesktopShortcut   ; 1 = create, 0 = skip

; ── MUI Configuration ────────────────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_ICON                    "..\Application\vaultmate.ico"
!define MUI_UNICON                  "..\Application\vaultmate.ico"
!define MUI_WELCOMEPAGE_TITLE       "Welcome to VaultMate Setup"
!define MUI_WELCOMEPAGE_TEXT        "VaultMate is an offline password manager and passkey authenticator.$\n$\nThis installer will:$\n  • Download VaultMate source from GitHub$\n  • Build the application on your computer$\n  • Create Start Menu (and optionally Desktop) shortcuts$\n$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN          "$INSTDIR\dist\VaultMate\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch VaultMate now"
!define MUI_FINISHPAGE_LINK         "Visit VaultMate on GitHub"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"
!define MUI_COMPONENTSPAGE_SMALLDESC

; ── Pages ─────────────────────────────────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE       "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
Page custom DesktopShortcutPage DesktopShortcutPageLeave   ; custom checkbox page
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; =============================================================================
; Custom page: Desktop Shortcut checkbox
; =============================================================================
!define MUI_BGCOLOR "FFFFFF"

Function DesktopShortcutPage
    !insertmacro MUI_HEADER_TEXT "Additional Options" "Choose optional components."

    nsDialogs::Create 1018
    Pop $0
    ${If} $0 == error
        Abort
    ${EndIf}

    ; Checkbox label
    ${NSD_CreateCheckbox} 10u 30u 280u 14u "&Create Desktop Shortcut"
    Pop $1
    ; Default: checked
    ${NSD_SetState} $1 ${BST_CHECKED}
    GetFunctionAddress $2 OnDesktopCheckbox
    nsDialogs::OnClick $1 $2

    nsDialogs::Show
FunctionEnd

Function OnDesktopCheckbox
    Pop $0
    ${NSD_GetState} $0 $DesktopShortcut
FunctionEnd

Function DesktopShortcutPageLeave
    ; If DesktopShortcut is still unset, default to checked
    ${If} $DesktopShortcut == ""
        StrCpy $DesktopShortcut ${BST_CHECKED}
    ${EndIf}
FunctionEnd

; =============================================================================
; Helper: Check if Python 3.10+ is available in PATH
; =============================================================================
Function CheckPython
    ; Try to run python --version, capture to temp file
    nsExec::ExecToStack 'cmd.exe /C python --version 2>&1'
    Pop $0   ; exit code
    Pop $1   ; stdout text
    ; If exit code != 0, Python not found
    ${If} $0 != 0
        Call InstallPython
    ${EndIf}
FunctionEnd

Function InstallPython
    DetailPrint "Python not found. Downloading Python 3.11..."
    inetc::get "${PYTHON_URL}" "$TEMP\python_installer.exe" /END
    Pop $0
    ${If} $0 != "OK"
        MessageBox MB_ICONSTOP "Failed to download Python installer. Please install Python 3.11+ manually from python.org, then re-run this installer."
        Abort
    ${EndIf}
    DetailPrint "Installing Python 3.11 (silent)..."
    ; /quiet InstallAllUsers=1 PrependPath=1 are standard Python installer switches
    nsExec::ExecToLog '"$TEMP\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_ICONSTOP "Python installation failed (code $0). Please install Python 3.11+ manually, then re-run this installer."
        Abort
    ${EndIf}
    DetailPrint "Python installed successfully."
    Delete "$TEMP\python_installer.exe"
FunctionEnd

; =============================================================================
; Helper: Download & extract VaultMate source from GitHub
; =============================================================================
Function DownloadSource
    DetailPrint "Downloading VaultMate source from GitHub..."
    inetc::get /CAPTION "Downloading VaultMate" /BANNER "Please wait while we download VaultMate from GitHub..." \
        "${GITHUB_ZIP_URL}" "$TEMP\vaultmate-source.zip" /END
    Pop $0
    ${If} $0 != "OK"
        MessageBox MB_ICONSTOP "Download failed: $0$\n$\nCheck your internet connection and try again."
        Abort
    ${EndIf}
    DetailPrint "Download complete. Extracting..."
FunctionEnd

Function ExtractSource
    ; Use PowerShell to expand the ZIP into $INSTDIR
    DetailPrint "Extracting VaultMate source to $INSTDIR..."
    nsExec::ExecToLog 'powershell.exe -NoProfile -NonInteractive -Command \
        "Expand-Archive -Path \"$TEMP\vaultmate-source.zip\" -DestinationPath \"$TEMP\vaultmate-extract\" -Force"'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_ICONSTOP "Extraction failed. Please try again."
        Abort
    ${EndIf}

    ; Move the inner folder (vaultmate-gui-main) content to INSTDIR
    ; GitHub ZIP always produces: vaultmate-gui-main\ (or vaultmate-gui-<branch>\)
    nsExec::ExecToLog 'powershell.exe -NoProfile -NonInteractive -Command \
        "$src = (Get-ChildItem \"$TEMP\vaultmate-extract\" | Select-Object -First 1).FullName; \
         if (Test-Path \"$INSTDIR\") { Remove-Item \"$INSTDIR\" -Recurse -Force }; \
         Move-Item -Path $src -Destination \"$INSTDIR\" -Force"'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_ICONSTOP "Failed to place VaultMate files into $INSTDIR. Try running as Administrator."
        Abort
    ${EndIf}

    Delete "$TEMP\vaultmate-source.zip"
    RMDir /r "$TEMP\vaultmate-extract"
    DetailPrint "Source extracted to $INSTDIR"
FunctionEnd

; =============================================================================
; Helper: Run build_windows.bat
; =============================================================================
Function BuildVaultMate
    DetailPrint "Building VaultMate (this may take 3-5 minutes)..."
    DetailPrint "Running build_windows.bat in $INSTDIR\Application..."

    ; Run synchronously so installer waits for completion
    ; /V1 gives us live output in the detail pane via nsExec::ExecToLog
    nsExec::ExecToLog 'cmd.exe /C ""$INSTDIR\Application\build_windows.bat""'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_ICONSTOP "Build failed (code $0).$\n$\nCheck that Python is installed and internet is available, then try again."
        Abort
    ${EndIf}
    DetailPrint "Build completed successfully!"
FunctionEnd

; =============================================================================
; INSTALL SECTION
; =============================================================================
Section "VaultMate (required)" SecMain
    SectionIn RO

    SetOutPath "$INSTDIR"

    ; Step 1 – Verify / install Python
    Call CheckPython

    ; Step 2 – Download source from GitHub
    Call DownloadSource

    ; Step 3 – Extract source
    Call ExtractSource

    ; Step 4 – Build from source
    Call BuildVaultMate

    ; Step 5 – Write install dir to registry
    WriteRegStr ${REG_ROOT} "${REG_KEY}" "InstallDir" "$INSTDIR"

    ; Step 6 – Start Menu shortcut (always created)
    CreateDirectory "$SMPROGRAMS\VaultMate"
    CreateShortcut "$SMPROGRAMS\VaultMate\VaultMate.lnk" \
        "$INSTDIR\Application\dist\VaultMate\${APP_EXE}" "" \
        "$INSTDIR\Application\dist\VaultMate\${APP_EXE}" 0 \
        SW_SHOWNORMAL "" "VaultMate Password Manager"
    CreateShortcut "$SMPROGRAMS\VaultMate\Uninstall VaultMate.lnk" \
        "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0

    ; Step 7 – Desktop shortcut (optional)
    ${If} $DesktopShortcut == ${BST_CHECKED}
        CreateShortcut "$DESKTOP\VaultMate.lnk" \
            "$INSTDIR\Application\dist\VaultMate\${APP_EXE}" "" \
            "$INSTDIR\Application\dist\VaultMate\${APP_EXE}" 0 \
            SW_SHOWNORMAL "" "VaultMate Password Manager"
    ${EndIf}

    ; Step 8 – Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Step 9 – Register in Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "DisplayName"     "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "DisplayIcon"     "$INSTDIR\Application\dist\VaultMate\${APP_EXE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "Publisher"       "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "URLInfoAbout"    "${APP_URL}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "DisplayVersion"  "${APP_VERSION}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "NoRepair"  1

SectionEnd

; =============================================================================
; UNINSTALL SECTION
; =============================================================================
Section "Uninstall"
    ; Remove shortcuts
    Delete "$SMPROGRAMS\VaultMate\VaultMate.lnk"
    Delete "$SMPROGRAMS\VaultMate\Uninstall VaultMate.lnk"
    RMDir  "$SMPROGRAMS\VaultMate"
    Delete "$DESKTOP\VaultMate.lnk"

    ; Remove installed folder
    RMDir /r "$INSTDIR"

    ; Clean registry
    DeleteRegKey ${REG_ROOT} "${REG_KEY}"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate"
SectionEnd
