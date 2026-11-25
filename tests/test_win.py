import os
import sys
import threading
import uuid
from pathlib import Path

from claude_heartbeat.win import (
    ES_CONTINUOUS,
    ES_SYSTEM_REQUIRED,
    acquire_single_instance,
    count_processes,
    hold,
    image_path,
    is_desktop_app,
    release,
)


def test_count_processes_is_case_insensitive():
    assert count_processes(Path(sys.executable).name.upper()) >= 1


def test_count_processes_sees_self():
    assert count_processes(Path(sys.executable).name) >= 1


def test_count_processes_none():
    assert count_processes("no-such-process-7f3a.exe") == 0


def test_is_desktop_app():
    assert is_desktop_app(r"C:\Users\x\.local\bin\claude.exe") is False
    assert is_desktop_app(
        r"C:\Program Files\WindowsApps\Claude_6.28899.6.0_x64__pzs8sxrjxfjjc\app\claude.exe") is True
    assert is_desktop_app(r"C:\Users\x\AppData\Local\AnthropicClaude\app-1.2.3\claude.exe") is True
    assert is_desktop_app("") is False  # path unreadable -> still counted (fail toward holding)


def test_image_path_of_self():
    assert Path(image_path(os.getpid())).name.lower() == Path(sys.executable).name.lower()


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
