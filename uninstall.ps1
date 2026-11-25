# Claude Heartbeat uninstaller: stops the app and removes the Startup shortcut.
# Leaves .venv and the log in place. Usage: powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
$ErrorActionPreference = 'Stop'
$entry = Join-Path $PSScriptRoot 'run.pyw'

# One running copy = 2 processes: the .venv pythonw.exe launcher and the real interpreter it
# spawns. The child holds the keep-awake request, so stop both. Case-insensitive match
# because C:\dev vs C:\Dev can differ between how it was launched and $PSScriptRoot.
$procs = @(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object {
    $_.CommandLine -and $_.CommandLine.IndexOf($entry, [StringComparison]::OrdinalIgnoreCase) -ge 0
})
foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host "Stopped $($procs.Count) process(es). Windows drops the keep-awake request with them."

$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Claude Heartbeat.lnk'
if (Test-Path $lnk) {
    Remove-Item $lnk
    Write-Host "Removed $lnk"
} else {
    Write-Host 'No Startup shortcut found.'
}
