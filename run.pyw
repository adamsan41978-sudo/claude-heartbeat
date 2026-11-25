"""Entry point for pythonw.exe (no console window). See README.md."""
import sys

from claude_heartbeat.app import main, run_safely

sys.exit(run_safely(main))
