# Claude Heartbeat uninstaller: stops the app, removes the login shortcut and the program folder.
# Leaves the source folder, .venv and the log. Usage: powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
$ErrorActionPreference = 'Stop'
$entry      = Join-Path $PSScriptRoot 'run.pyw'
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\ClaudeHeartbeat'

# The exe, plus any copy of the script version (pythonw.exe running this folder's run.pyw: a .venv
# launcher and the interpreter it spawns, which holds the keep-awake request). Path match ignores case.
$procs = @(Get-CimInstance Win32_Process -Filter "Name='ClaudeHeartbeat.exe' OR Name='pythonw.exe'" |
    Where-Object {
        $_.Name -eq 'ClaudeHeartbeat.exe' -or
        ($_.CommandLine -and $_.CommandLine.IndexOf($entry, [StringComparison]::OrdinalIgnoreCase) -ge 0)
    })
foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
foreach ($p in $procs) { Wait-Process -Id $p.ProcessId -Timeout 10 -ErrorAction SilentlyContinue }
Write-Host "Stopped $($procs.Count) process(es). Windows drops the keep-awake request with them."

$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Claude Heartbeat.lnk'
if (Test-Path $lnk) { Remove-Item $lnk; Write-Host "Removed $lnk" } else { Write-Host 'No Startup shortcut found.' }

if (Test-Path $installDir) { Remove-Item $installDir -Recurse -Force; Write-Host "Removed $installDir" }
else { Write-Host 'No program folder found.' }
