# =============================================================================
# VaultMate MSI Setup Helper
# Bundled inside the .msi and called by a deferred Custom Action.
# CustomActionData format: "INSTALLDIR=C:\VaultMate;DESKTOP=1"
# =============================================================================
param()

$ErrorActionPreference = "Stop"

# ── Parse CustomActionData passed by MSI ─────────────────────────────────────
$raw = $env:VAULTMATE_CA_DATA   # set by the immediate CA via env var trick
if (-not $raw) { $raw = "INSTALLDIR=C:\VaultMate;DESKTOP=1" }

$data = @{}
foreach ($pair in $raw -split ";") {
    $kv = $pair -split "=", 2
    if ($kv.Count -eq 2) { $data[$kv[0].Trim()] = $kv[1].Trim() }
}

$InstallDir   = $data["INSTALLDIR"]
$WantDesktop  = $data["DESKTOP"]

if (-not $InstallDir) { $InstallDir = "C:\VaultMate" }

$logFile = "$env:TEMP\vaultmate_setup.log"
function Log($msg) {
    $ts = (Get-Date).ToString("HH:mm:ss")
    "$ts  $msg" | Tee-Object -FilePath $logFile -Append | Out-Null
    Write-Host "$ts  $msg"
}

Log "=== VaultMate Setup Helper Started ==="
Log "InstallDir : $InstallDir"
Log "Desktop    : $WantDesktop"

# ── 1. Check / Install Python ─────────────────────────────────────────────────
Log "Checking Python..."
$pythonOk = $false
try {
    $v = & python --version 2>&1
    if ($LASTEXITCODE -eq 0) { Log "Python found: $v"; $pythonOk = $true }
} catch {}

if (-not $pythonOk) {
    Log "Python not found. Downloading Python 3.11.9..."
    $pyUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $pyInstaller = "$env:TEMP\python_setup.exe"
    Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing
    Log "Installing Python silently..."
    $p = Start-Process $pyInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait -PassThru
    Remove-Item $pyInstaller -Force -ErrorAction SilentlyContinue
    if ($p.ExitCode -ne 0) { throw "Python install failed (exit $($p.ExitCode))" }
    # Refresh PATH so python.exe is visible
    $env:PATH = [Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [Environment]::GetEnvironmentVariable("PATH","User")
    Log "Python installed."
}

# ── 2. Download VaultMate source from GitHub ──────────────────────────────────
$zipUrl   = "https://github.com/webtech781/vaultmate-gui/archive/refs/heads/main.zip"
$zipPath  = "$env:TEMP\vaultmate-src.zip"
$exPath   = "$env:TEMP\vaultmate-extract"

Log "Downloading VaultMate source from GitHub..."
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
Log "Download complete."

# ── 3. Extract ────────────────────────────────────────────────────────────────
Log "Extracting..."
if (Test-Path $exPath)    { Remove-Item $exPath    -Recurse -Force }
Expand-Archive -Path $zipPath -DestinationPath $exPath -Force

$innerDir = (Get-ChildItem $exPath | Select-Object -First 1).FullName
if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force }
Move-Item -Path $innerDir -Destination $InstallDir -Force

Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item $exPath  -Recurse -Force -ErrorAction SilentlyContinue
Log "Source placed at $InstallDir"

# ── 4. Build VaultMate ────────────────────────────────────────────────────────
$buildBat = Join-Path $InstallDir "Application\build_windows.bat"
if (-not (Test-Path $buildBat)) { throw "build_windows.bat not found at $buildBat" }

Log "Running build_windows.bat (this takes 3-5 minutes)..."
$proc = Start-Process "cmd.exe" `
    -ArgumentList "/C `"$buildBat`" >> `"$logFile`" 2>&1" `
    -WorkingDirectory (Split-Path $buildBat) `
    -Wait -PassThru -NoNewWindow

if ($proc.ExitCode -ne 0) { throw "Build failed (exit $($proc.ExitCode)). See $logFile" }
Log "Build complete."

# ── 5. Desktop shortcut (if requested) ───────────────────────────────────────
$exePath = Join-Path $InstallDir "Application\dist\VaultMate\VaultMate.exe"
if ($WantDesktop -eq "1" -and (Test-Path $exePath)) {
    # CA runs as SYSTEM — $env:USERPROFILE would point to SYSTEM's profile,
    # not the real user's Desktop. Use the Public Desktop instead (visible to all users).
    $desktopPath = [Environment]::GetFolderPath('CommonDesktopDirectory')
    $shell    = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut("$desktopPath\VaultMate.lnk")
    $shortcut.TargetPath       = $exePath
    $shortcut.WorkingDirectory = Split-Path $exePath
    $shortcut.IconLocation     = $exePath
    $shortcut.Description      = "VaultMate Password Manager"
    $shortcut.Save()
    Log "Desktop shortcut created at $desktopPath\VaultMate.lnk"
}

Log "=== VaultMate Setup Helper Finished ==="
