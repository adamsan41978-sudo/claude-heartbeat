# Claude Heartbeat as its own .exe — design (short)

Date: 2026-11-25 · Size: small change · Builds on `2026-11-25-claude-heartbeat-design.md`

## Intent
Task Manager shows the app as a generic "Python" (two `pythonw.exe` processes). The user is starting
a family of workstation-specific tools and wants each one identifiable at a glance: its own process
name, icon, and a shared publisher so they group together.

## Goals
- Task Manager shows one process, `ClaudeHeartbeat.exe`, described as **Claude Heartbeat**, with
  the heartbeat icon.
- Version info: Publisher/CompanyName **Workstation Tools** (user's choice; reused by every future
  tool), ProductName Claude Heartbeat, version 1.0.0.
- `install.ps1` builds, installs to `%LOCALAPPDATA%\Programs\ClaudeHeartbeat\`, points the Startup
  shortcut at the exe, launches it. Re-runnable. `uninstall.ps1` removes process, shortcut, folder.
- `run.pyw` remains for testing changes without a rebuild.

## Non-goals
- Code signing; an installer/MSI; a shared library for future tools (the pattern is documented,
  not abstracted, until a second tool exists).

## Approaches
- **One-folder PyInstaller build (picked):** one process, instant start, no temp unpacking.
- Single-file PyInstaller build: two same-named processes, unpacks to %TEMP% each launch, more
  antivirus false positives. Rejected.
- Renamed copy of the venv launcher: the real interpreter still shows as `pythonw.exe`. Rejected.

## Decisions (my calls unless noted)
- Build into `dist\` in the repo, then copy to `%LOCALAPPDATA%\Programs\ClaudeHeartbeat\` so editing
  the repo never touches the running copy.
- Exe icon = the AWAKE (green) heartbeat on the navy tile, multi-size .ico drawn natively per size.
- Same single-instance mutex as before, so the script and the exe can never both run.
- Built locally → no SmartScreen prompt. If Defender flags the build, stop and report.

## Verification
Exe version info read back via `(Get-Item).VersionInfo`; one `ClaudeHeartbeat.exe` running and no
`pythonw.exe run.pyw`; re-install replaces it; uninstall leaves nothing; user confirms Task Manager
(Processes name + icon, Startup apps Publisher) and `powercfg /requests` lists `ClaudeHeartbeat.exe`.
