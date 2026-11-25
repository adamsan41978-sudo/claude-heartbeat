# Claude Heartbeat installer: venv + deps + Startup shortcut, then launch. Safe to re-run.
# Usage: powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = 'Stop'
$root    = $PSScriptRoot
$venvPy  = Join-Path $root '.venv\Scripts\python.exe'
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$entry   = Join-Path $root 'run.pyw'

function Get-RunningCopies {
    # One copy = 2 processes (.venv launcher + the interpreter it spawns); match both, any path case.
    @(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object {
        $_.CommandLine -and $_.CommandLine.IndexOf($entry, [StringComparison]::OrdinalIgnoreCase) -ge 0
    })
}

# Stop the running copy first. Otherwise the relaunch exits on the single-instance lock and the
# old code keeps running, and pip can't replace files the old copy has loaded.
$old = Get-RunningCopies
foreach ($p in $old) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
foreach ($p in $old) { Wait-Process -Id $p.ProcessId -Timeout 10 -ErrorAction SilentlyContinue }
if ($old.Count) { Write-Host 'Stopped the running copy.' }

if (-not (Test-Path $venvPy)) {
    Write-Host 'Creating venv...'
    python -m venv (Join-Path $root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'python -m venv failed' }
} else {
    Write-Host 'Reusing existing venv.'
}

& $venvPy -m pip install --disable-pip-version-check -q -r (Join-Path $root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }
Write-Host 'Dependencies installed.'

$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Claude Heartbeat.lnk'
$sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)  # overwrites if present
$sc.TargetPath       = $pythonw
$sc.Arguments        = "`"$entry`""
$sc.WorkingDirectory = $root
$sc.Description      = 'Claude Heartbeat'
$sc.Save()
Write-Host "Startup shortcut: $lnk"

Start-Process -FilePath $pythonw -ArgumentList "`"$entry`"" -WorkingDirectory $root
Start-Sleep -Seconds 3
if ((Get-RunningCopies).Count) {
    Write-Host 'Started. Look for the heartbeat icon in the tray.'
} else {
    $log = Join-Path $env:LOCALAPPDATA 'ClaudeHeartbeat\heartbeat.log'
    Write-Host 'It did not stay running. Last log lines:'
    if (Test-Path $log) { Get-Content $log -Encoding UTF8 -Tail 5 }
    exit 1
}
