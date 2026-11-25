import threading
import time

import pytest

from claude_heartbeat.logfile import setup_log
from claude_heartbeat.monitor import Monitor
from claude_heartbeat.state import State


def wait_for(pred, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.01)
    return pred()


class Fakes:
    """count() returns successive values, then repeats the last; "err" raises OSError."""

    def __init__(self, seq, on_change_raises=False):
        self.seq, self.i = list(seq), 0
        self.holds, self.releases, self.changes = [], [], []
        self.on_change_raises = on_change_raises

    def count(self):
        v = self.seq[min(self.i, len(self.seq) - 1)]
        self.i += 1
        if v == "err":
            raise OSError("snapshot failed")
        return v

    def hold(self):
        self.holds.append(threading.get_ident())

    def release(self):
        self.releases.append(threading.get_ident())

    def on_change(self, state, count):
        self.changes.append((state, count))
        if self.on_change_raises:
            raise RuntimeError("icon update failed")

    @property
    def last(self):
        return self.changes[-1] if self.changes else None


@pytest.fixture
def log_path(tmp_path):
    return tmp_path / "t.log"


@pytest.fixture
def start(log_path):
    started = []

    def _start(fakes, interval=0.01):
        m = Monitor(fakes.count, fakes.on_change, setup_log(log_path), interval=interval,
                    hold_fn=fakes.hold, release_fn=fakes.release)
        m.start()
        started.append(m)
        return m

    yield _start
    for m in started:
        m.stop()


def test_holds_when_claude_running(start):
    f = Fakes([2])
    start(f)
    assert wait_for(lambda: f.last == (State.AWAKE, 2))
    assert wait_for(lambda: f.i >= 5)
    assert len(f.holds) == 1


def test_releases_when_claude_exits(start):
    f = Fakes([2, 0])
    start(f)
    assert wait_for(lambda: f.last == (State.WATCHING, 0))
    assert wait_for(lambda: f.i >= 5)
    assert len(f.holds) == 1 and len(f.releases) == 1


def test_toggle_off_releases_immediately(start):
    f = Fakes([1])
    m = start(f, interval=60)
    assert wait_for(lambda: f.last == (State.AWAKE, 1))
    m.set_enabled(False)
    assert wait_for(lambda: len(f.releases) == 1, timeout=1)
    assert f.last == (State.OFF, 1) and m.enabled is False
    m.set_enabled(True)
    assert wait_for(lambda: len(f.holds) == 2, timeout=1)


def test_stop_releases_and_exits(start):
    f = Fakes([1])
    m = start(f, interval=60)
    assert wait_for(lambda: f.last == (State.AWAKE, 1))
    m.stop()
    assert len(f.releases) == 1
    assert not m.is_alive()


def test_hold_and_release_same_thread(start):
    f = Fakes([1, 0])
    start(f)
    assert wait_for(lambda: len(f.releases) == 1)
    assert f.holds[0] == f.releases[0] != threading.get_ident()


def test_count_error_reuses_last_count(start, log_path):
    f = Fakes([2, "err"])
    m = start(f)
    assert wait_for(lambda: f.i >= 5)
    assert f.last == (State.AWAKE, 2)
    assert f.releases == [] and m.is_alive()
    assert "Traceback" in log_path.read_text(encoding="utf-8")
    m.set_enabled(False)
    assert wait_for(lambda: len(f.releases) == 1, timeout=1)
    assert f.last == (State.OFF, 2)


def test_on_change_error_does_not_kill_thread(start):
    f = Fakes([1], on_change_raises=True)
    m = start(f)
    assert wait_for(lambda: f.i >= 3)
    assert m.is_alive() and len(f.holds) == 1


def test_logs_state_changes_only(start, log_path):
    f = Fakes([1, 2, 3, 0])
    m = start(f)
    assert wait_for(lambda: f.last == (State.WATCHING, 0))
    m.stop()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert [line.split(" ", 2)[2] for line in lines] == [
        "awake — 1 session",
        "watching — no Claude running, normal sleep",
    ]


def test_setup_log_creates_dir_and_rotates(tmp_path):
    path = tmp_path / "a" / "b" / "h.log"
    log = setup_log(path)
    for _ in range(4000):
        log.info("x" * 100)
    assert path.exists() and path.with_name("h.log.1").exists()
    assert path.stat().st_size <= 256_000
