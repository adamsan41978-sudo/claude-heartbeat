# Packaged ClaudeHeartbeat.exe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Claude Heartbeat as a one-folder PyInstaller exe (`ClaudeHeartbeat.exe`, publisher Workstation Tools) installed per-user and started at login.

**Architecture:** `make_exe.py` writes a multi-size .ico and a version-info file, then runs PyInstaller one-folder/windowed on `run.pyw`. `install.ps1` stops any running copy, builds, copies `dist\ClaudeHeartbeat\` to `%LOCALAPPDATA%\Programs\ClaudeHeartbeat\`, points the Startup shortcut at the exe, and launches it.

**Tech Stack:** Python 3.12 venv, PyInstaller 6.x, Pillow, PowerShell 5.1.

**Spec:** `docs/superpowers/specs/2026-11-25-packaged-exe-design.md` (builds on `2026-11-25-claude-heartbeat-design.md`)

## Global Constraints

- Identity (exact): exe `ClaudeHeartbeat.exe`; FileDescription and ProductName `Claude Heartbeat`; CompanyName `Workstation Tools`; version `1.0.0` (file/product version tuple `(1, 0, 0, 0)`).
- Install dir `%LOCALAPPDATA%\Programs\ClaudeHeartbeat\`; Startup shortcut stays `Claude Heartbeat.lnk`.
- One-folder, windowed (`--onedir --windowed`). Never `--onefile`.
- Single-instance mutex unchanged (`Local\ClaudeHeartbeat`). Log path unchanged.
- `.gitignore` adds `build/` and `dist/`. PowerShell scripts stay ASCII-only.
- Commits on branch `feat/packaged-exe`, each ending with `-m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`.

## Review Focus

1. Upgrading from the script version: the old `pythonw.exe run.pyw` copy holds the mutex, so a new exe would exit at once → install stops both kinds of copy. → Task 3 Step 3.
2. PyInstaller resolves some relative paths against `--specpath`, so the icon/version file silently go missing → pass absolute paths; check the exe's icon and version info. → Task 2 Steps 3-4.
3. PyInstaller misses pystray's dynamically imported Windows backend → the exe runs with no tray icon → `--hidden-import pystray._win32`; check the process stays up and the log shows `awake`. → Task 3 Step 3.
4. Re-install while the exe is running would hit locked files → install stops and waits first. → Task 3 Step 4.
5. Defender quarantines the fresh build → it would fail later with an obscure error → check the exe still exists after the build; install reports the log tail if launch fails. → Task 2 Step 5.

---

### Task 1: Identity, icon file, version info

**Files:**
- Modify: `claude_heartbeat/__init__.py`, `claude_heartbeat/icons.py`, `.gitignore`, `requirements-dev.txt` (becomes `-r requirements-build.txt` + `pytest>=8`)
- Create: `requirements-build.txt` (`-r requirements.txt` + `pyinstaller>=6.10,<7`), `make_exe.py`
- Test: `tests/test_make_exe.py`

**Interfaces:**
- Produces: in `claude_heartbeat/__init__.py`: `APP_NAME = "Claude Heartbeat"`, `EXE_NAME = "ClaudeHeartbeat"`, `PUBLISHER = "Workstation Tools"`, `VERSION = "1.0.0"`.
  `icons.save_ico(path: Path) -> None` — AWAKE icon; each of sizes 16, 20, 24, 32, 40, 48, 64, 128, 256 drawn natively with `make_icon` (passed as `append_images`), not downscaled.
  `make_exe.version_info_text() -> str` — PyInstaller `VSVersionInfo(...)` literal built from the identity constants (StringTable `040904B0`; CompanyName, FileDescription, FileVersion, InternalName, OriginalFilename `ClaudeHeartbeat.exe`, ProductName, ProductVersion; Translation `[1033, 1200]`).

- [ ] **Step 1: Branch + deps** — `git checkout -b feat/packaged-exe`; write the requirements files; `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` → `Successfully installed ... pyinstaller-6.x`.
- [ ] **Step 2: Write the failing tests**

```python
def test_ico_has_explorer_and_tray_sizes(tmp_path):
    path = tmp_path / "h.ico"
    save_ico(path)
    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= Image.open(path).info["sizes"]

def test_version_info_parses_with_pyinstaller(tmp_path):
    f = tmp_path / "v.txt"
    f.write_text(version_info_text(), encoding="utf-8")
    vi = load_version_info_from_text_file(str(f))   # PyInstaller.utils.win32.versioninfo
    text = str(vi)
    for s in ("Workstation Tools", "Claude Heartbeat", "ClaudeHeartbeat.exe", "1.0.0"):
        assert s in text
    assert vi.ffi.fileVersionMS == 1 << 16 and vi.ffi.fileVersionLS == 0
```

- [ ] **Step 3: Run to verify failure** — `.\.venv\Scripts\python.exe -m pytest tests\test_make_exe.py -v` → FAIL (import error).
- [ ] **Step 4: Implement** the constants, `save_ico`, and `version_info_text` (PyInstaller imported inside functions that need it, not at module top of `make_exe.py`).
- [ ] **Step 5: Run to verify pass** → 2 passed; full suite → 29 passed.
- [ ] **Step 6: Commit** — `feat: app identity, multi-size icon, version info`.

---

### Task 2: Build the exe

**Files:**
- Modify: `make_exe.py`

**Interfaces:**
- Consumes: Task 1.
- Produces: `make_exe.build() -> Path` (returns the absolute path of `dist\ClaudeHeartbeat\ClaudeHeartbeat.exe`); running `python make_exe.py` prints that path.

`build()`: under `ROOT = Path(__file__).resolve().parent`, write `build\heartbeat.ico` and `build\version_info.txt`, then `PyInstaller.__main__.run([...])` with **absolute** paths: script `ROOT\run.pyw`, `--name ClaudeHeartbeat --onedir --windowed --noconfirm --clean`, `--icon`, `--version-file`, `--hidden-import pystray._win32`, `--distpath ROOT\dist`, `--workpath ROOT\build\pyi`, `--specpath ROOT\build`.

- [ ] **Step 1: Implement `build()`.**
- [ ] **Step 2: Build** — `.\.venv\Scripts\python.exe make_exe.py` → ends with the exe path; `Test-Path dist\ClaudeHeartbeat\ClaudeHeartbeat.exe` → True.
- [ ] **Step 3: Version info** — `(Get-Item dist\ClaudeHeartbeat\ClaudeHeartbeat.exe).VersionInfo | Select-Object FileDescription, CompanyName, ProductName, ProductVersion, OriginalFilename` → `Claude Heartbeat`, `Workstation Tools`, `Claude Heartbeat`, `1.0.0`, `ClaudeHeartbeat.exe`.
- [ ] **Step 4: Icon is ours** — `Add-Type -AssemblyName System.Drawing; $b = [System.Drawing.Icon]::ExtractAssociatedIcon("<abs exe path>").ToBitmap()`; count pixels whose RGB is `#14213D` (navy tile) and `#2EE59D` (green) → both > 0.
- [ ] **Step 5: Defender** — 10 s after the build, `Test-Path` on the exe → still True. If False: stop and report to the user (four-stop rule: security-sensitive).
- [ ] **Step 6: Commit** — `feat: one-folder PyInstaller build`.

---

### Task 3: Install / uninstall / README

**Files:**
- Modify: `install.ps1`, `uninstall.ps1`, `README.md`

**Interfaces:**
- Consumes: `make_exe.py` (Task 2), `requirements-build.txt` (Task 1).

`install.ps1`: `Get-RunningCopies` = `ClaudeHeartbeat.exe` processes **plus** `pythonw.exe` whose CommandLine contains `run.pyw` under this root (case-insensitive) → stop + `Wait-Process`; create venv if missing; `pip install -r requirements-build.txt`; `python make_exe.py` (throw on non-zero exit); replace `%LOCALAPPDATA%\Programs\ClaudeHeartbeat\` with `dist\ClaudeHeartbeat\` (remove, then copy); shortcut Target = installed exe, no Arguments, WorkingDirectory = install dir, Description `Claude Heartbeat`; launch; after 3 s confirm exactly one `ClaudeHeartbeat.exe`, else print the log tail and `exit 1`.
`uninstall.ps1`: stop both kinds of copy; remove shortcut; remove the install dir; keep the log.
`README.md`: Task Manager identity (name, icon, Publisher column in Startup apps), install dir, `make_exe.py` for builds, `run.pyw` for quick tests (Quit the exe first — they share the single-instance lock), `powercfg /requests` now lists `ClaudeHeartbeat.exe`.

- [ ] **Step 1: Write the scripts and README;** ASCII check `grep -nP '[^\x00-\x7F]' install.ps1 uninstall.ps1` → no output.
- [ ] **Step 2: Install (migration from the script version)** — `powershell -ExecutionPolicy Bypass -File .\install.ps1` → `Started.`
- [ ] **Step 3: Verify** — `Get-Process ClaudeHeartbeat` → 1; no `pythonw.exe` with `run.pyw`; shortcut `TargetPath` = `%LOCALAPPDATA%\Programs\ClaudeHeartbeat\ClaudeHeartbeat.exe`; log tail `started` then `awake — N sessions`; process still alive 30 s later (tray backend loaded).
- [ ] **Step 4: Re-install replaces** — note the PID, run install again → a different PID, still exactly 1 process.
- [ ] **Step 5: Uninstall** → 0 processes, no shortcut, no install dir; then reinstall and leave it running.
- [ ] **Step 6: Commit** — `feat: install the packaged exe`.
- [ ] **Step 7: Review** — `code-reviewer` (opus) on `main..HEAD`; fix Critical/Important with a failing check first.
- [ ] **Step 8: Hand to user** — Task Manager: Processes tab shows **Claude Heartbeat** with the heartbeat icon; Startup apps shows **Claude Heartbeat**, Publisher **Workstation Tools**; admin `powercfg /requests` lists `ClaudeHeartbeat.exe` under `SYSTEM:` while green.
