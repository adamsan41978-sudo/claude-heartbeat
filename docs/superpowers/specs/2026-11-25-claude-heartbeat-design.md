# Claude Heartbeat — design (short)

Date: 2026-11-25 · Size: small tool

## Intent
Long unattended Claude runs (loops, overnight jobs, runs while at the day job) die when the PC
sleeps after 15 min idle. A dead run costs more than no run: you then have to audit what
finished and repair the project. This tool keeps the PC awake whenever Claude is running, and
lets it sleep normally otherwise, without the user having to remember anything.

## Goals
- While the switch is ON and any `claude.exe` process exists → PC does not idle-sleep.
- No `claude.exe`, or switch OFF → normal Balanced-plan behavior (sleep 15 min, display 10 min).
- Display may still turn off while held awake (system awake, screen off).
- Tray icon shows the state at a glance; right-click to toggle; starts ON with every launch.
- Starts automatically at Windows login.

## Non-goals
- Does not judge whether Claude is *working* — an idle window counts. (Activity detection
  would sleep the PC during a loop's 20–30 min wait between ticks: the exact failure to avoid.)
- Does not block Windows Update restarts, manual Sleep/Shutdown, or power loss.
- Does not detect Claude run via `node` (npm install); this machine uses the native `claude.exe`.

## Anti-goals (failure even if it "works")
- Editing the power plan. It is never touched; nothing to restore.
- PC left stuck awake after Claude exits, the switch goes OFF, or the app quits/crashes.

## Approaches
- **A. Python tray app (picked).** `pythonw` + `pystray` + `Pillow` in a project venv. User's
  main language, easy to maintain. Risk: a Python move/upgrade can break the startup shortcut.
- B. PowerShell tray app. Zero installs, survives Python changes; clunkier to modify.
- Dropped: headless task + on/off shortcuts — no visible state, defeats "don't have to remember."

## How it works (my calls unless noted)
- **Keep-awake:** Windows `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` from
  one worker thread while Claude runs; `ES_CONTINUOUS` alone releases it. Windows drops the
  request automatically if the process dies — this is what satisfies the anti-goal.
- **Detection:** every 30 s, check for a process named `claude.exe` (stdlib only, no console
  flash). 30 s is far under the 15 min sleep timer.
- **Single instance:** a named mutex, so a second launch exits instead of adding a 2nd icon.
- **Log:** state changes only (e.g. `02:14 awake — 3 sessions`, `06:40 released — none`) to
  `%LOCALAPPDATA%\ClaudeHeartbeat\heartbeat.log`, so after a run you can see it held.
- **Install/uninstall:** `install.ps1` builds the venv, installs deps, adds a Startup-folder
  shortcut; `uninstall.ps1` removes the shortcut.

## Icon (user asked: custom, distinct from other tools)
A "system tools" family frame: dark navy rounded tile. Future tools reuse the tile and swap the
glyph + accent color. This tool's glyph is a heartbeat pulse line.

```
 AWAKE (holding)       WATCHING (on, no Claude)   OFF
 ┌──────────┐          ┌──────────┐               ┌──────────┐
 │ __/\  __ │ bright   │ __/\  __ │ dim           │ ──────── │ flat
 │     \/   │ green    │     \/   │ grey-blue     │          │ grey
 └──────────┘          └──────────┘               └──────────┘
```
Tooltip: `Claude Heartbeat — keeping PC awake (3 sessions)` / `— watching, normal sleep` /
`— off, normal sleep`. Menu: `✓ Keep awake while Claude runs`, `Open log`, `Quit`.

## Verification
`powercfg /requests` lists `pythonw.exe` under SYSTEM while holding, and nothing after each
release path: Claude closed, switch OFF, Quit, and process killed.

## Left to the builder
File layout, exact colors and pixel art, menu wording polish.
