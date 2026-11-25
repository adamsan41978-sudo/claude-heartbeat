import sys
import threading
import uuid
from pathlib import Path

from claude_heartbeat.win import (
    ES_CONTINUOUS,
    ES_SYSTEM_REQUIRED,
    acquire_single_instance,
    count_matching,
    count_processes,
    hold,
    release,
)


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
        seen.append(release())  # previous state = held
        seen.append(release())  # previous state = released

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert seen == [ES_CONTINUOUS | ES_SYSTEM_REQUIRED, ES_CONTINUOUS]


def test_single_instance():
    name = f"Local\\ClaudeHeartbeatTest-{uuid.uuid4()}"
    assert acquire_single_instance(name) is True
    assert acquire_single_instance(name) is False
