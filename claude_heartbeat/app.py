"""Tray wiring. Runs under pythonw (no console), so failures must land in the log."""
import os
from pathlib import Path
from typing import Callable

from .logfile import LOG_PATH, setup_log
from .monitor import Monitor
from .state import State, tooltip
from .win import acquire_single_instance, count_processes

MUTEX_NAME = "Local\\ClaudeHeartbeat"


def main() -> int:
    # Third-party imports live here so a missing/broken dependency is caught by run_safely.
    import pystray

    from .icons import make_icon

    if not acquire_single_instance(MUTEX_NAME):
        return 0  # already running; one tray icon is enough
    log = setup_log()
    log.info("started")

    icon = pystray.Icon("claude-heartbeat", make_icon(State.WATCHING), tooltip(State.WATCHING, 0))

    def on_change(state: State, count: int) -> None:
        icon.icon = make_icon(state)
        icon.title = tooltip(state, count)
        icon.update_menu()

    monitor = Monitor(count_processes, on_change, log)

    def toggle() -> None:
        monitor.set_enabled(not monitor.enabled)

    def quit_() -> None:
        monitor.stop()
        log.info("quit")
        icon.stop()

    icon.menu = pystray.Menu(
        pystray.MenuItem("Keep awake while Claude runs", toggle,
                         checked=lambda _: monitor.enabled, default=True),
        pystray.MenuItem("Open log", lambda: os.startfile(LOG_PATH)),
        pystray.MenuItem("Quit", quit_),
    )

    def setup(tray) -> None:
        tray.visible = True
        monitor.start()

    icon.run(setup=setup)
    monitor.stop()  # tray loop ended some other way (e.g. sign-out): release on the way out
    return 0


def run_safely(main_fn: Callable[[], int], log_path: Path = LOG_PATH) -> int:
    try:
        return main_fn()
    except Exception:
        setup_log(log_path).exception("crashed")
        return 1
