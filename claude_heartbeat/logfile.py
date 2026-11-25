"""State-change log at %LOCALAPPDATA%\\ClaudeHeartbeat\\heartbeat.log (rotates, 1 backup)."""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_PATH = Path(os.environ["LOCALAPPDATA"]) / "ClaudeHeartbeat" / "heartbeat.log"


def setup_log(path: Path = LOG_PATH) -> logging.Logger:
    log = logging.getLogger("claude_heartbeat")
    log.setLevel(logging.INFO)
    log.propagate = False
    target = os.path.abspath(path)
    for h in list(log.handlers):
        if getattr(h, "baseFilename", None) == target:
            return log  # already writing here
        log.removeHandler(h)
        h.close()
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(target, maxBytes=256_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M"))
    log.addHandler(handler)
    return log
