# Workstation Tools installer: builds the exe, installs it for this user, starts it at login, and
# launches it. Safe to re-run: it replaces the running copy, but only after a good build.
# Usage: powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = 'Stop'

# App identity. For a new tool, change these two lines (and claude_heartbeat\__init__.py to match).
$AppName = 'Claude Heartbeat'   # shortcut name
$ExeName = 'ClaudeHeartbeat'    # exe, process, program folder, log folder

$root       = $PSScriptRoot
$venvPy     = Join-Path $root '.venv\Scripts\python.exe'
$entry      = Join-Path $root 'run.pyw'
$built      = Join-Path $root "dist\$ExeName\$ExeName.exe"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\$ExeName"
$exe        = Join-Path $installDir "$ExeName.exe"
$log        = Join-Path $env:LOCALAPPDATA "$ExeName\heartbeat.log"

function Get-RunningCopies {
    # The exe, plus any copy of the script version started with this folder's full run.pyw path
    # (a .venv launcher and the interpreter it spawns). Path match ignores case (C:\dev vs C:\Dev).
    @(Get-CimInstance Win32_Process -Filter "Name='$ExeName.exe' OR Name='pythonw.exe'" |
        Where-Object {
            $_.Name -eq "$ExeName.exe" -or
            ($_.CommandLine -and $_.CommandLine.IndexOf($entry, [StringComparison]::OrdinalIgnoreCase) -ge 0)
        })
}

# 1. Build environment.
if (-not (Test-Path $venvPy)) {
    Write-Host 'Creating venv...'
    python -m venv (Join-Path $root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'python -m venv failed' }
}
& $venvPy -m pip install --disable-pip-version-check -q -r (Join-Path $root 'requirements-build.txt')
if ($LASTEXITCODE -ne 0) { throw 'pip install failed. The running copy was left alone.' }

# 2. Build. The running copy keeps running: the build only writes to dist\ and build\.
#    PyInstaller logs to stderr, which PowerShell 5.1 can treat as an error, so output goes to files.
Write-Host "Building $ExeName.exe (about a minute)..."
New-Item -ItemType Directory -Path (Join-Path $root 'build') -Force | Out-Null
$buildOut = Join-Path $root 'build\make_exe.out.log'
$buildErr = Join-Path $root 'build\make_exe.err.log'
$build = Start-Process -FilePath $venvPy -ArgumentList "`"$(Join-Path $root 'make_exe.py')`"" `
    -WorkingDirectory $root -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $buildOut -RedirectStandardError $buildErr
if ($build.ExitCode -ne 0) {
    Get-Content $buildErr -Tail 20
    throw "Build failed (full log: $buildErr). The running copy was left alone."
}
if (-not (Test-Path $built)) {
    throw "Build finished but $built is missing. Check Windows Security > Protection history (quarantined?). The running copy was left alone."
}

# 3. Only now stop the running copy: otherwise the new one exits on the single-instance lock,
#    and the program folder can't be replaced while in use.
$old = Get-RunningCopies
foreach ($p in $old) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
foreach ($p in $old) { Wait-Process -Id $p.ProcessId -Timeout 10 -ErrorAction SilentlyContinue }
if ($old.Count) { Write-Host 'Stopped the running copy.' }

# 4. Install: replace the per-user program folder with the fresh build.
if (Test-Path $installDir) { Remove-Item $installDir -Recurse -Force }
New-Item -ItemType Directory -Path (Split-Path $installDir) -Force | Out-Null
Copy-Item (Split-Path $built) $installDir -Recurse
if (-not (Test-Path $exe)) { throw "$exe is missing after the copy (quarantined?)." }
Write-Host "Installed to $installDir"

# 5. Start at login.
$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) "$AppName.lnk"
$sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)  # overwrites if present
$sc.TargetPath       = $exe
$sc.Arguments        = ''
$sc.WorkingDirectory = $installDir
$sc.Description      = $AppName
$sc.Save()
Write-Host "Startup shortcut: $lnk"

# 6. Launch and confirm it stayed up.
Start-Process -FilePath $exe -WorkingDirectory $installDir
Start-Sleep -Seconds 3
if (@(Get-Process -Name $ExeName -ErrorAction SilentlyContinue).Count -eq 1) {
    Write-Host 'Started. Look for its icon in the tray.'
} else {
    Write-Host 'It did not stay running. If a test copy (pythonw run.pyw) is still open, Quit it from'
    Write-Host 'the tray and run this again: the two share a single-instance lock. Last log lines:'
    if (Test-Path $log) { Get-Content $log -Encoding UTF8 -Tail 5 }
    exit 1
}
