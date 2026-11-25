# Claude Heartbeat installer: builds ClaudeHeartbeat.exe, installs it for this user, starts it at
# login, and launches it. Safe to re-run: it replaces the running copy.
# Usage: powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = 'Stop'
$root       = $PSScriptRoot
$venvPy     = Join-Path $root '.venv\Scripts\python.exe'
$entry      = Join-Path $root 'run.pyw'
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\ClaudeHeartbeat'
$exe        = Join-Path $installDir 'ClaudeHeartbeat.exe'

function Get-RunningCopies {
    # The exe, plus any copy of the script version (pythonw.exe running this folder's run.pyw:
    # a .venv launcher and the interpreter it spawns). Path match ignores case (C:\dev vs C:\Dev).
    @(Get-CimInstance Win32_Process -Filter "Name='ClaudeHeartbeat.exe' OR Name='pythonw.exe'" |
        Where-Object {
            $_.Name -eq 'ClaudeHeartbeat.exe' -or
            ($_.CommandLine -and $_.CommandLine.IndexOf($entry, [StringComparison]::OrdinalIgnoreCase) -ge 0)
        })
}

# 1. Stop the running copy. Otherwise the new one exits on the single-instance lock, and its
#    files can't be replaced while in use.
$old = Get-RunningCopies
foreach ($p in $old) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
foreach ($p in $old) { Wait-Process -Id $p.ProcessId -Timeout 10 -ErrorAction SilentlyContinue }
if ($old.Count) { Write-Host 'Stopped the running copy.' }

# 2. Build environment.
if (-not (Test-Path $venvPy)) {
    Write-Host 'Creating venv...'
    python -m venv (Join-Path $root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'python -m venv failed' }
}
& $venvPy -m pip install --disable-pip-version-check -q -r (Join-Path $root 'requirements-build.txt')
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }

# 3. Build the exe. PyInstaller logs to stderr, which PowerShell 5.1 can treat as an error,
#    so its output goes to files instead.
Write-Host 'Building ClaudeHeartbeat.exe (about a minute)...'
New-Item -ItemType Directory -Path (Join-Path $root 'build') -Force | Out-Null
$buildOut = Join-Path $root 'build\make_exe.out.log'
$buildErr = Join-Path $root 'build\make_exe.err.log'
$build = Start-Process -FilePath $venvPy -ArgumentList "`"$(Join-Path $root 'make_exe.py')`"" `
    -WorkingDirectory $root -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $buildOut -RedirectStandardError $buildErr
if ($build.ExitCode -ne 0) {
    Get-Content $buildErr -Tail 20
    throw "Build failed (full log: $buildErr)"
}

# 4. Install: replace the per-user program folder with the fresh build.
if (Test-Path $installDir) { Remove-Item $installDir -Recurse -Force }
New-Item -ItemType Directory -Path (Split-Path $installDir) -Force | Out-Null
Copy-Item (Join-Path $root 'dist\ClaudeHeartbeat') $installDir -Recurse
Write-Host "Installed to $installDir"

# 5. Start at login.
$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Claude Heartbeat.lnk'
$sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)  # overwrites if present
$sc.TargetPath       = $exe
$sc.Arguments        = ''
$sc.WorkingDirectory = $installDir
$sc.Description      = 'Claude Heartbeat'
$sc.Save()
Write-Host "Startup shortcut: $lnk"

# 6. Launch and confirm it stayed up.
Start-Process -FilePath $exe -WorkingDirectory $installDir
Start-Sleep -Seconds 3
if (@(Get-Process -Name ClaudeHeartbeat -ErrorAction SilentlyContinue).Count -eq 1) {
    Write-Host 'Started. Look for the heartbeat icon in the tray.'
} else {
    $log = Join-Path $env:LOCALAPPDATA 'ClaudeHeartbeat\heartbeat.log'
    Write-Host 'It did not stay running. Last log lines:'
    if (Test-Path $log) { Get-Content $log -Encoding UTF8 -Tail 5 }
    exit 1
}
