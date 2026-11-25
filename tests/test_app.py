from claude_heartbeat.app import run_safely


def test_run_safely_logs_traceback(tmp_path):
    def boom():
        raise RuntimeError("tray failed")

    assert run_safely(boom, tmp_path / "h.log") == 1
    text = (tmp_path / "h.log").read_text(encoding="utf-8")
    assert "Traceback" in text and "tray failed" in text


def test_run_safely_passes_through(tmp_path):
    assert run_safely(lambda: 0, tmp_path / "h.log") == 0
