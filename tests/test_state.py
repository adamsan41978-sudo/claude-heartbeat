from claude_heartbeat.state import State, decide, log_line, tooltip


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
