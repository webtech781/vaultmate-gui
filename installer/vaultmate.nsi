; VaultMate NSIS Installer Script
; Produces: VaultMate-Setup-{VERSION}-windows.exe
; Requires: NSIS 3.x  (available in GitHub Actions via chocolatey)

!define APP_NAME "VaultMate"
!define APP_VERSION "$%VAULTMATE_VERSION%"
!define APP_PUBLISHER "webtech781"
!define APP_URL "https://github.com/webtech781/vaultmate-gui"
!define APP_EXE "VaultMate.exe"
!define INSTALL_DIR "$PROGRAMFILES64\VaultMate"

; Modern UI
!include "MUI2.nsh"
!include "LogicLib.nsh"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "..\VaultMate-Setup-${APP_VERSION}-windows.exe"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKCU "Software\VaultMate" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

; --- MUI Pages ---
!define MUI_ABORTWARNING
!define MUI_ICON "..\Application\vaultmate.ico"
!define MUI_UNICON "..\Application\vaultmate.ico"
!define MUI_WELCOMEPAGE_TITLE "Welcome to VaultMate Setup"
!define MUI_WELCOMEPAGE_TEXT "VaultMate is an offline password manager and software passkey authenticator.$\n$\nThis wizard will install VaultMate on your computer.$\n$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch VaultMate now"
!define MUI_FINISHPAGE_LINK "Visit VaultMate on GitHub"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; --- Install Section ---
Section "VaultMate (required)" SecMain
    SectionIn RO

    SetOutPath "$INSTDIR"

    ; Copy all files from the PyInstaller dist folder
    File /r "dist\VaultMate\*.*"

    ; Write install location to registry
    WriteRegStr HKCU "Software\VaultMate" "InstallDir" "$INSTDIR"

    ; Create Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\VaultMate"
    CreateShortcut "$SMPROGRAMS\VaultMate\VaultMate.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

    ; Create Desktop shortcut
    CreateShortcut "$DESKTOP\VaultMate.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Register in Add/Remove Programs
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "URLInfoAbout" "${APP_URL}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate" \
        "DisplayVersion" "${APP_VERSION}"
SectionEnd

; --- Uninstall Section ---
Section "Uninstall"
    ; Remove installed files
    RMDir /r "$INSTDIR"

    ; Remove Start Menu and Desktop shortcuts
    Delete "$SMPROGRAMS\VaultMate\VaultMate.lnk"
    RMDir "$SMPROGRAMS\VaultMate"
    Delete "$DESKTOP\VaultMate.lnk"

    ; Clean registry
    DeleteRegKey HKCU "Software\VaultMate"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VaultMate"
SectionEnd
