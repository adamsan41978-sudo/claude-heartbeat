# Claude Heartbeat installer: venv + deps + Startup shortcut, then launch. Safe to re-run.
# Usage: powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = 'Stop'
$root    = $PSScriptRoot
$venvPy  = Join-Path $root '.venv\Scripts\python.exe'
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$entry   = Join-Path $root 'run.pyw'

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
Write-Host 'Started. If it was already running, the new copy exits on its own.'
