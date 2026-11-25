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

- **Right-click** for the menu: `Keep awake while Claude runs` (the on/off switch, check mark =
  on), `Open log`, `Quit`. Left-click does nothing, so a stray click can't turn the hold off.
- The switch starts **on** every launch. It checks for Claude every 30 seconds.

## Install / uninstall

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1     # build the exe, install, start at login, launch now
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1   # stop it, remove the login shortcut and program folder
```

The app installs to `%LOCALAPPDATA%\Programs\ClaudeHeartbeat\ClaudeHeartbeat.exe`. `install.ps1`
is safe to re-run: after editing the code, run it again to rebuild and replace the running copy.
After uninstalling, a leftover icon can linger in the tray until the mouse passes over it; that's
Windows, not a running copy.

## In Task Manager

One process, **Claude Heartbeat** (`ClaudeHeartbeat.exe`), with the heartbeat icon. Its version
info names the publisher **Workstation Tools**, the shared publisher for this workstation's own
tools, so they line up together in the Startup apps tab's Publisher column.

## Log

`%LOCALAPPDATA%\ClaudeHeartbeat\heartbeat.log`. State changes only, for example
`2026-11-25 02:14 awake — 3 sessions`. Rotates at 256 KB. Use `Open log` from the tray menu, or
in PowerShell 5.1: `Get-Content "$env:LOCALAPPDATA\ClaudeHeartbeat\heartbeat.log" -Encoding UTF8 -Tail 20`.

## Check that it's holding (admin terminal)

```powershell
powercfg /requests
```

While the icon is green, `SYSTEM:` lists `[PROCESS] \Device\...\ClaudeHeartbeat.exe`. Switch off
or Quit and it's gone.

## What it does not do

- It doesn't block Windows Update restarts. Set **Settings > Windows Update > Advanced options >
  Active hours** to cover your overnight runs.
- It doesn't stop a manual Sleep or Shutdown, or a power loss.
- The Claude Desktop chat app is also named `claude.exe`, but it isn't counted. Only Claude Code
  sessions hold the PC awake.
- An idle Claude window counts as running. That's deliberate: a loop waiting for its next tick
  looks idle. Close idle sessions, or switch it off, if you want the PC to sleep.

## Development

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe make_exe.py          # build only, into dist\ClaudeHeartbeat\
```

To try a change without rebuilding, Quit the tray app first (the two share a single-instance
lock), then run `.\.venv\Scripts\pythonw.exe "$PWD\run.pyw"`. Use the full path, as shown, so
`install.ps1` and `uninstall.ps1` can find and stop the test copy. Run `install.ps1` when you're done.

## Starting the next Workstation Tools app

Copy these four files and set the new app's identity in each:

| File | What to change |
|---|---|
| `claude_heartbeat\__init__.py` | `APP_NAME`, `EXE_NAME`, `VERSION` (keep `PUBLISHER = "Workstation Tools"`) |
| `make_exe.py` | nothing beyond the package it imports from |
| `install.ps1` | the `$AppName` / `$ExeName` lines at the top |
| `uninstall.ps1` | the same two lines |

Give it its own icon on the shared navy tile (see `claude_heartbeat\icons.py`), its own
single-instance lock name, and its own log folder. If you miss a rename in the scripts, the new
app's install would stop and replace Claude Heartbeat's program folder instead of its own.
