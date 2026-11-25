"""Background thread: poll for Claude, hold/release the keep-awake request on state edges."""
import logging
import threading
from typing import Callable

from .state import State, decide, log_line
from .win import hold, release


class Monitor(threading.Thread):
    """Owns the keep-awake request. hold_fn/release_fn are only ever called from run(),
    because Windows scopes the request to the thread that made it."""

    def __init__(
        self,
        count_fn: Callable[[], int],
        on_change: Callable[[State, int], None],
        log: logging.Logger,
        interval: float = 30.0,
        hold_fn: Callable[[], object] = hold,
        release_fn: Callable[[], object] = release,
    ):
        super().__init__(name="claude-heartbeat-monitor", daemon=True)
        self._count_fn = count_fn
        self._on_change = on_change
        self._log = log
        self._interval = interval
        self._hold_fn = hold_fn
        self._release_fn = release_fn
        self._enabled = True
        self._wake = threading.Event()
        self._stopping = threading.Event()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, on: bool) -> None:
        self._enabled = bool(on)
        self._wake.set()  # apply now, not at the next 30 s tick

    def stop(self, timeout: float = 5.0) -> None:
        self._stopping.set()
        self._wake.set()
        if self.is_alive():
            self.join(timeout)

    def run(self) -> None:
        holding = False
        count = 0  # last good count; reused if a process check fails
        logged_state = None
        notified = None
        try:
            while not self._stopping.is_set():
                self._wake.clear()
                try:
                    count = self._count_fn()
                except Exception:
                    self._log.exception("process check failed, keeping last count (%d)", count)
                state = decide(self._enabled, count)
                if state is State.AWAKE and not holding:
                    self._hold_fn()
                    holding = True
                elif state is not State.AWAKE and holding:
                    self._release_fn()
                    holding = False
                if state is not logged_state:
                    self._log.info(log_line(state, count))
                    logged_state = state
                if (state, count) != notified:
                    try:
                        self._on_change(state, count)
                        notified = (state, count)
                    except Exception:
                        self._log.exception("tray update failed")
                self._wake.wait(self._interval)
        finally:
            if holding:
                self._release_fn()
