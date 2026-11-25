"""Pure state logic: what the app should be doing, and how it describes it."""
from enum import Enum


class State(Enum):
    AWAKE = "awake"        # switch on, Claude running: holding the PC awake
    WATCHING = "watching"  # switch on, no Claude: normal sleep
    OFF = "off"            # switch off: normal sleep


def decide(enabled: bool, count: int) -> State:
    if not enabled:
        return State.OFF
    return State.AWAKE if count > 0 else State.WATCHING


def _sessions(count: int) -> str:
    return f"{count} session" if count == 1 else f"{count} sessions"


def tooltip(state: State, count: int) -> str:
    detail = {
        State.AWAKE: f"keeping PC awake ({_sessions(count)})",
        State.WATCHING: "watching, normal sleep",
        State.OFF: "off, normal sleep",
    }[state]
    return f"Claude Heartbeat — {detail}"


def log_line(state: State, count: int) -> str:
    return {
        State.AWAKE: f"awake — {_sessions(count)}",
        State.WATCHING: "watching — no Claude running, normal sleep",
        State.OFF: "off — normal sleep",
    }[state]
