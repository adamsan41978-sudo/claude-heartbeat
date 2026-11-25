# Claude Heartbeat

Keeps the PC awake while any Claude Code session (`claude.exe`) is running, so long unattended
runs don't die when Windows sleeps. With no Claude running, or the switch off, your normal power
plan applies. The power plan is never edited: the app asks Windows to stay awake the same way a
video player does, and Windows drops that request automatically if the app stops or crashes.
The screen can still turn off.

## Tray icon

| Icon | Meaning |
|---|---|
| Green heartbeat | Claude is running: PC held awake. Hover shows the session count. |
| Dim grey-blue heartbeat | Switch on, no Claude running: normal sleep. |
| Flat grey line | Switch off: normal sleep. |

- **Left-click** toggles the switch. **Right-click** menu: `Keep awake while Claude runs`,
  `Open log`, `Quit`.
- The switch starts **on** every launch. It checks for Claude every 30 seconds.

## Install / uninstall

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1     # venv, deps, starts at login, launches now
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1   # stops it, removes the login shortcut
```

`install.ps1` is safe to re-run. After uninstalling, a leftover icon can linger in the tray until
the mouse passes over it; that's Windows, not a running copy.

## Log

`%LOCALAPPDATA%\ClaudeHeartbeat\heartbeat.log`. State changes only, for example
`2026-11-25 02:14 awake — 3 sessions`. Rotates at 256 KB. Use `Open log` from the tray menu, or
in PowerShell 5.1: `Get-Content "$env:LOCALAPPDATA\ClaudeHeartbeat\heartbeat.log" -Encoding UTF8 -Tail 20`.

## Check that it's holding (admin terminal)

```powershell
powercfg /requests
```

While the icon is green, `pythonw.exe` appears under `SYSTEM:`. Switch off or Quit and it's gone.

## What it does not do

- It doesn't block Windows Update restarts. Set **Settings > Windows Update > Advanced options >
  Active hours** to cover your overnight runs.
- It doesn't stop a manual Sleep or Shutdown, or a power loss.
- An idle Claude window counts as running. That's deliberate: a loop waiting for its next tick
  looks idle. Close idle sessions, or switch it off, if you want the PC to sleep.

## Development

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```
