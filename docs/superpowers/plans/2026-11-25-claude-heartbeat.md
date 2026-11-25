# Claude Heartbeat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Windows tray app that keeps the PC awake while any `claude.exe` runs, and lets it sleep normally otherwise, with an on/off switch.

**Architecture:** A worker thread polls for `claude.exe` every 30 s and holds/releases a Windows keep-awake request (`SetThreadExecutionState`) on state edges. A `pystray` icon shows the state and toggles the switch. The power plan is never touched; Windows drops the request if the process dies.

**Tech Stack:** Python 3.12 (`pythonw`), `pystray`, `Pillow`, `ctypes` (kernel32), `pytest`; PowerShell 5.1 install scripts.

**Spec:** `docs/superpowers/specs/2026-11-25-claude-heartbeat-design.md`

## Global Constraints

- Project root: `C:\dev\claude-heartbeat`. venv at `.venv`. All commands are PowerShell, run from the root.
- Runtime deps only `pystray>=0.19.5,<0.20` and `Pillow>=10`; dev dep `pytest>=8`. Everything else stdlib.
- Never call `powercfg` to change settings, never edit the power plan.
- Keep-awake flags: `ES_CONTINUOUS = 0x80000000`, `ES_SYSTEM_REQUIRED = 0x00000001`. Never set `ES_DISPLAY_REQUIRED` (display may turn off).
- Process to watch: `claude.exe`, matched case-insensitively. Poll interval: `30.0` s.
- Switch starts ON at every launch. Single-instance mutex name: `Local\ClaudeHeartbeat`.
- Log: `%LOCALAPPDATA%\ClaudeHeartbeat\heartbeat.log`, state changes only, rotates at 256 000 bytes with 1 backup.
- Tooltip copy (exact): `Claude Heartbeat — keeping PC awake (3 sessions)` (`1 session` singular) / `Claude Heartbeat — watching, normal sleep` / `Claude Heartbeat — off, normal sleep`.
- Menu copy (exact): `Keep awake while Claude runs` (checkbox, default/left-click action), `Open log`, `Quit`.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (pass as a second `-m`).

## Review Focus

1. A poll fails (process snapshot error) mid-run → keep the last good count, log it, keep polling; never release mid-run because of an error, and the OFF switch must still release. → Task 4 `test_count_error_reuses_last_count`.
2. The process name arrives as `Claude.exe` / `CLAUDE.EXE` → still counted. → Task 2 `test_count_matching_is_case_insensitive`.
3. A startup crash under `pythonw` is invisible (no console) → the traceback lands in `heartbeat.log`. → Task 5 `test_run_safely_logs_traceback`.
4. First run on a clean profile has no log folder; months of uptime grow the log → folder created, file rotates. → Task 4 `test_setup_log_creates_dir_and_rotates`.
5. `install.ps1` run twice (re-install after an edit) → one shortcut, venv reused, still one tray icon. → Task 6 Step 3.

---

## File Structure

```
claude-heartbeat\
  .gitignore  requirements.txt  requirements-dev.txt  README.md
  run.pyw                     entry point for pythonw (Task 5)
  install.ps1  uninstall.ps1  (Task 6)
  claude_heartbeat\
    __init__.py
    state.py                  pure: State enum, decide(), tooltip(), log_line()  (Task 1)
    win.py                    ctypes: process count, hold/release, mutex        (Task 2)
    icons.py                  Pillow: make_icon()                               (Task 3)
    logfile.py                setup_log(), LOG_PATH                             (Task 4)
    monitor.py                Monitor thread                                    (Task 4)
    app.py                    tray wiring, main(), run_safely()                 (Task 5)
  tests\  test_state.py test_win.py test_icons.py test_monitor.py test_app.py
```

---

### Task 1: Project setup + state logic

**Files:**
- Create: `.gitignore` (`.venv/`, `__pycache__/`, `.pytest_cache/`), `requirements.txt`, `requirements-dev.txt` (`-r requirements.txt` + `pytest>=8`), `claude_heartbeat\__init__.py` (empty), `claude_heartbeat\state.py`
- Test: `tests\test_state.py`

**Interfaces:**
- Produces: `class State(Enum)` with members `AWAKE`, `WATCHING`, `OFF`; `decide(enabled: bool, count: int) -> State`; `tooltip(state: State, count: int) -> str`; `log_line(state: State, count: int) -> str`.

- [ ] **Step 1: Write the four setup files above, then init repo and venv**

Run: `git init; python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`
Expected: `Successfully installed ... pystray-0.19.x ...`; `git status` shows the files.

- [ ] **Step 2: Write the failing tests** in `tests\test_state.py`

```python
def test_decide():
    assert decide(True, 3) is State.AWAKE
    assert decide(True, 0) is State.WATCHING
    assert decide(False, 3) is State.OFF
    assert decide(False, 0) is State.OFF

def test_tooltip_copy():
    assert tooltip(State.AWAKE, 3) == "Claude Heartbeat — keeping PC awake (3 sessions)"
    assert tooltip(State.AWAKE, 1) == "Claude Heartbeat — keeping PC awake (1 session)"
    assert tooltip(State.WATCHING, 0) == "Claude Heartbeat — watching, normal sleep"
    assert tooltip(State.OFF, 2) == "Claude Heartbeat — off, normal sleep"

def test_log_line():
    assert log_line(State.AWAKE, 1) == "awake — 1 session"
    assert log_line(State.AWAKE, 3) == "awake — 3 sessions"
    assert log_line(State.WATCHING, 0) == "watching — no Claude running, normal sleep"
    assert log_line(State.OFF, 2) == "off — normal sleep"
```

- [ ] **Step 3: Run to verify failure** — `.\.venv\Scripts\python.exe -m pytest tests\test_state.py -v` → FAIL (`ModuleNotFoundError: claude_heartbeat.state`).
- [ ] **Step 4: Implement `state.py`** with the three functions above.
- [ ] **Step 5: Run to verify pass** — same command → 3 passed.
- [ ] **Step 6: Commit** — `git add -A; git commit -m "feat: project setup and state logic" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"` (this first commit also carries `docs\`).

---

### Task 2: Windows glue (process count, keep-awake, single instance)

**Files:**
- Create: `claude_heartbeat\win.py`
- Test: `tests\test_win.py`

**Interfaces:**
- Produces:
  - `ES_CONTINUOUS: int`, `ES_SYSTEM_REQUIRED: int`
  - `count_matching(names: Iterable[str], target: str) -> int` — case-insensitive equality count.
  - `count_processes(name: str = "claude.exe") -> int` — `CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS)` + `Process32FirstW/NextW` over `PROCESSENTRY32W`, feeds `szExeFile` names to `count_matching`, closes the handle in `finally`, raises `OSError` if the snapshot fails.
  - `hold() -> int` / `release() -> int` — `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` / `SetThreadExecutionState(ES_CONTINUOUS)`; return the previous state (the API's return value). Set `argtypes`/`restype` to `c_uint32`. Thread-scoped: callers must hold and release on the same thread.
  - `acquire_single_instance(name: str) -> bool` — `CreateMutexW(None, False, name)` via `WinDLL("kernel32", use_last_error=True)`; False if `get_last_error() == 183` (`ERROR_ALREADY_EXISTS`). Keep the handle in a module-level list so it lives for the process.

- [ ] **Step 1: Write the failing tests**

```python
def test_count_matching_is_case_insensitive():
    assert count_matching(["Claude.exe", "node.exe", "CLAUDE.EXE"], "claude.exe") == 2

def test_count_processes_sees_self():
    assert count_processes(Path(sys.executable).name) >= 1

def test_count_processes_none():
    assert count_processes("no-such-process-7f3a.exe") == 0

def test_hold_then_release_reports_previous_state():
    seen = []
    def worker():
        hold()
        seen.append(release())   # previous state = held
        seen.append(release())   # previous state = released
    t = threading.Thread(target=worker); t.start(); t.join()
    assert seen == [ES_CONTINUOUS | ES_SYSTEM_REQUIRED, ES_CONTINUOUS]

def test_single_instance():
    name = f"Local\\ClaudeHeartbeatTest-{uuid.uuid4()}"
    assert acquire_single_instance(name) is True
    assert acquire_single_instance(name) is False
```

- [ ] **Step 2: Run to verify failure** — `.\.venv\Scripts\python.exe -m pytest tests\test_win.py -v` → FAIL (import error).
- [ ] **Step 3: Implement `win.py`** per the Interfaces block.
- [ ] **Step 4: Run to verify pass** → 5 passed.
- [ ] **Step 5: Live check** — `.\.venv\Scripts\python.exe -c "from claude_heartbeat.win import count_processes; print(count_processes())"` → prints the number of open Claude Code sessions (≥ 1 while this session runs), and no console flashes.
- [ ] **Step 6: Commit** — `git add -A; git commit -m "feat: Windows process count, keep-awake, single-instance" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 3: Tray icons

**Files:**
- Create: `claude_heartbeat\icons.py`
- Test: `tests\test_icons.py`

**Interfaces:**
- Consumes: `State` (Task 1).
- Produces: `TILE = "#14213D"`; `COLORS: dict[State, str] = {AWAKE: "#2EE59D", WATCHING: "#5C7A99", OFF: "#6B6B6B"}`; `make_icon(state: State, size: int = 64) -> PIL.Image.Image` (RGBA).

Drawing (no anti-aliasing, so exact colors exist for tests): transparent canvas; `rounded_rectangle` over the full canvas, radius `size // 5`, fill `TILE`. Glyph width `max(2, size // 9)`. AWAKE/WATCHING: polyline through these fractions of `size`: `(0.12,0.55) (0.35,0.55) (0.45,0.25) (0.55,0.78) (0.63,0.55) (0.88,0.55)`, joint `"curve"`. OFF: straight line `(0.12,0.55)→(0.88,0.55)`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("state", list(State))
def test_icon_shape(state):
    img = make_icon(state, 64)
    assert img.size == (64, 64) and img.mode == "RGBA"
    assert img.getpixel((0, 0))[3] == 0          # rounded corner is transparent

def _pixels(state, rgb):
    img = make_icon(state, 64)
    return [(x, y) for y in range(64) for x in range(64) if img.getpixel((x, y))[:3] == rgb]

def test_awake_is_green_watching_is_not():
    green = ImageColor.getrgb(COLORS[State.AWAKE])
    assert _pixels(State.AWAKE, green)
    assert not _pixels(State.WATCHING, green)

def test_off_glyph_is_flat():
    rows = {y for _, y in _pixels(State.OFF, ImageColor.getrgb(COLORS[State.OFF]))}
    assert rows and max(rows) - min(rows) <= 64 // 9 + 1
```

- [ ] **Step 2: Run to verify failure** — `.\.venv\Scripts\python.exe -m pytest tests\test_icons.py -v` → FAIL.
- [ ] **Step 3: Implement `icons.py`.**
- [ ] **Step 4: Run to verify pass** → 5 passed.
- [ ] **Step 5: Preview for the user** — write `docs\icon-preview.png`: the three states side by side at 64 px, and again downscaled to 16 px (tray size), on a mid-grey background. Show it to the user; adjust colors/geometry only if they ask (non-blocking).
- [ ] **Step 6: Commit** — `git add -A; git commit -m "feat: heartbeat tray icons" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 4: Log file + Monitor thread

**Files:**
- Create: `claude_heartbeat\logfile.py`, `claude_heartbeat\monitor.py`
- Test: `tests\test_monitor.py`

**Interfaces:**
- Consumes: `State`, `decide`, `log_line` (Task 1); `hold`, `release`, `count_processes` (Task 2).
- Produces:
  - `LOG_PATH: Path` = `Path(os.environ["LOCALAPPDATA"]) / "ClaudeHeartbeat" / "heartbeat.log"`
  - `setup_log(path: Path = LOG_PATH) -> logging.Logger` — logger `"claude_heartbeat"`, creates parent dirs, `RotatingFileHandler(path, maxBytes=256_000, backupCount=1, encoding="utf-8")`, format `"%(asctime)s %(message)s"`, datefmt `"%Y-%m-%d %H:%M"`, level INFO, `propagate = False`. Exactly one handler: same path again is a no-op; a different path closes and replaces the old handler (keeps tests from writing into each other's files).
  - `class Monitor(threading.Thread)` (daemon):
    `__init__(self, count_fn: Callable[[], int], on_change: Callable[[State, int], None], log: logging.Logger, interval: float = 30.0, hold_fn: Callable[[], object] = hold, release_fn: Callable[[], object] = release)`;
    `enabled: bool` (read-only property, starts True); `set_enabled(self, on: bool) -> None`; `stop(self, timeout: float = 5.0) -> None`.

Rules the tests pin (the implementer writes the loop):
- `hold_fn`/`release_fn` are called **only from `run()`** — never from `stop()` or `set_enabled()` — because the request is thread-scoped. `run()` releases in a `finally` if holding.
- Edge-triggered: `hold_fn` on entering AWAKE, `release_fn` on leaving it; never twice in a row.
- `set_enabled()` and `stop()` set a `threading.Event` that cuts the `interval` wait short, so the change applies within ~1 s.
- `count_fn` raising → `log.exception(...)`, reuse the last good count (0 if none), continue.
- `on_change(state, count)` fires when `(state, count)` differs from the last call; an exception in it is logged and swallowed.
- `log.info(log_line(state, count))` only when `state` changes.

- [ ] **Step 1: Write the failing tests** (fakes record calls + `threading.get_ident()`; `wait_for(pred, timeout=2)` polls every 10 ms; `counts` helper returns successive values then repeats the last, `"err"` entries raise `OSError`)

```python
def test_holds_when_claude_running(): ...
    # counts [2], interval=0.01 → hold called once; on_change last == (State.AWAKE, 2)

def test_releases_when_claude_exits(): ...
    # counts [2, 0] → hold once, release once; last == (State.WATCHING, 0)

def test_toggle_off_releases_immediately(): ...
    # counts [1], interval=60 → AWAKE; set_enabled(False) → release within 1 s; last == (State.OFF, 1)
    # set_enabled(True) → hold again within 1 s

def test_stop_releases_and_exits(): ...
    # AWAKE, then m.stop() → release called once; not m.is_alive()

def test_hold_and_release_same_thread(): ...
    # recorded idents for hold and release are equal and != threading.get_ident()

def test_count_error_reuses_last_count(): ...
    # counts [2, "err"], interval=0.01 → stays AWAKE, release never called, m.is_alive(),
    # log contains "Traceback"; then set_enabled(False) → release within 1 s

def test_on_change_error_does_not_kill_thread(): ...
    # on_change raises → m.is_alive() after 3 polls, hold still called once

def test_logs_state_changes_only(tmp_path): ...
    # counts [1, 2, 3, 0] → log file lines end with exactly:
    # ["awake — 1 session", "watching — no Claude running, normal sleep"]

def test_setup_log_creates_dir_and_rotates(tmp_path):
    path = tmp_path / "a" / "b" / "h.log"
    log = setup_log(path)
    for _ in range(4000): log.info("x" * 100)
    assert path.exists() and path.with_name("h.log.1").exists()
    assert path.stat().st_size <= 256_000
```

Each test calls `m.stop()` in a `finally`. Test loggers use `setup_log(tmp_path / "t.log")`.

- [ ] **Step 2: Run to verify failure** — `.\.venv\Scripts\python.exe -m pytest tests\test_monitor.py -v` → FAIL.
- [ ] **Step 3: Implement `logfile.py` and `monitor.py`.**
- [ ] **Step 4: Run to verify pass** → 9 passed. Then the full suite `.\.venv\Scripts\python.exe -m pytest -v` → 22 passed, run twice to check for flaky timing.
- [ ] **Step 5: Commit** — `git add -A; git commit -m "feat: monitor thread and state-change log" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 5: Tray app + entry point

**Files:**
- Create: `claude_heartbeat\app.py`, `run.pyw`
- Test: `tests\test_app.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `main() -> int`; `run_safely(main_fn: Callable[[], int], log_path: Path = LOG_PATH) -> int`.

`main()`: if `not acquire_single_instance("Local\\ClaudeHeartbeat")` → return 0. `log = setup_log()`; `log.info("started")`. Build `pystray.Icon("claude-heartbeat", make_icon(State.WATCHING), tooltip(State.WATCHING, 0), menu)`. Menu: `MenuItem("Keep awake while Claude runs", toggle, checked=lambda _: monitor.enabled, default=True)`, `MenuItem("Open log", lambda: os.startfile(LOG_PATH))`, `MenuItem("Quit", quit_)`. `on_change` sets `icon.icon`, `icon.title`, calls `icon.update_menu()`. Start the monitor inside `icon.run(setup=...)` after `icon.visible = True`. `quit_`: `monitor.stop()`, `log.info("quit")`, `icon.stop()`. Return 0.

`run_safely()`: call `main_fn()`; on any `Exception`, write the traceback via `setup_log(log_path).exception("crashed")` and return 1.

`run.pyw`: `sys.exit(run_safely(main))`.

- [ ] **Step 1: Write the failing test**

```python
def test_run_safely_logs_traceback(tmp_path):
    def boom(): raise RuntimeError("tray failed")
    assert run_safely(boom, tmp_path / "h.log") == 1
    text = (tmp_path / "h.log").read_text(encoding="utf-8")
    assert "Traceback" in text and "tray failed" in text

def test_run_safely_passes_through(tmp_path):
    assert run_safely(lambda: 0, tmp_path / "h.log") == 0
```

- [ ] **Step 2: Run to verify failure** — `.\.venv\Scripts\python.exe -m pytest tests\test_app.py -v` → FAIL.
- [ ] **Step 3: Implement `app.py` and `run.pyw`.**
- [ ] **Step 4: Run to verify pass** — full suite → 24 passed.
- [ ] **Step 5: Manual run** — `Start-Process .\.venv\Scripts\pythonw.exe -ArgumentList '"C:\dev\claude-heartbeat\run.pyw"'`. Expected: a green heartbeat icon in the tray (Claude is running); hover shows `Claude Heartbeat — keeping PC awake (N sessions)`; `Get-Content $env:LOCALAPPDATA\ClaudeHeartbeat\heartbeat.log -Tail 3` shows `started` then `awake — N sessions`.
- [ ] **Step 6: Second launch** — run the same `Start-Process` again → still one icon; `Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object CommandLine -like '*run.pyw*'` → 1 result.
- [ ] **Step 7: Toggle + quit** — left-click the icon → turns flat grey, log `off — normal sleep`; click again → green; menu `Quit` → icon gone, log `quit`.
- [ ] **Step 8: Commit** — `git add -A; git commit -m "feat: tray app and pythonw entry point" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 6: Install / uninstall + README

**Files:**
- Create: `install.ps1`, `uninstall.ps1`, `README.md`

**Interfaces:**
- Consumes: `run.pyw`, `requirements.txt`.
- Produces: Startup shortcut `Claude Heartbeat.lnk` in `[Environment]::GetFolderPath('Startup')`.

`install.ps1` (PowerShell 5.1, `$ErrorActionPreference = 'Stop'`, paths from `$PSScriptRoot`): create `.venv` only if missing; `pip install -r requirements.txt`; (re)write the shortcut via `WScript.Shell` — Target `.venv\Scripts\pythonw.exe`, Arguments `"<root>\run.pyw"` (quoted), WorkingDirectory root, Description `Claude Heartbeat`; then launch it (the mutex makes a relaunch harmless); print what it did.
`uninstall.ps1`: stop any `pythonw.exe` whose CommandLine contains `run.pyw` and the project root; remove the shortcut; print what it did. Leaves `.venv` and the log.
`README.md`: what it does, the three icon states, install/uninstall commands (`powershell -ExecutionPolicy Bypass -File .\install.ps1`), log location, the elevated `powercfg /requests` check, and the note that Windows Update restarts are not blocked (set Active hours).

- [ ] **Step 1: Write the scripts and README.**
- [ ] **Step 2: Install** — `powershell -ExecutionPolicy Bypass -File .\install.ps1` → shortcut exists (`Test-Path "$([Environment]::GetFolderPath('Startup'))\Claude Heartbeat.lnk"` → True), icon appears.
- [ ] **Step 3: Install again** (Review Focus 5) → no error, `Get-ChildItem` of the Startup folder shows one `Claude Heartbeat.lnk`, the `Win32_Process` query from Task 5 Step 6 → 1 result.
- [ ] **Step 4: Uninstall = process-killed release path** — `powershell -ExecutionPolicy Bypass -File .\uninstall.ps1` → icon gone, query → 0 results, shortcut gone. Then reinstall so it's left running.
- [ ] **Step 5: Elevated end-to-end check (user, admin terminal)** — `powercfg /requests` lists `pythonw.exe` under `SYSTEM:` while green; after left-click to OFF it no longer appears; back ON → listed; `Quit` → gone. (The "all Claude closed" path is covered by `test_releases_when_claude_exits`; the "process killed" path by Step 4 plus Windows' own cleanup.) Hand this step to the user with the exact command.
- [ ] **Step 6: Commit** — `git add -A; git commit -m "feat: install/uninstall scripts and README" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`
- [ ] **Step 7: Review** — dispatch `code-reviewer` on the full repo against the spec; fix findings before calling it done.
