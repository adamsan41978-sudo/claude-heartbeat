from claude_heartbeat.app import build_menu, run_safely


class FakeMonitor:
    def __init__(self):
        self.enabled = True

    def set_enabled(self, on):
        self.enabled = on


def test_menu_toggles_only_from_right_click_menu():
    m = FakeMonitor()
    items = list(build_menu(m, lambda: None, lambda: None).items)
    assert [i.text for i in items] == ["Keep awake while Claude runs", "Open log", "Quit"]
    assert not any(i.default for i in items)  # a stray left-click must not switch the hold off
    assert items[0].checked is True
    items[0](None)  # choose the menu item
    assert m.enabled is False and items[0].checked is False


def test_run_safely_logs_traceback(tmp_path):
    def boom():
        raise RuntimeError("tray failed")

    assert run_safely(boom, tmp_path / "h.log") == 1
    text = (tmp_path / "h.log").read_text(encoding="utf-8")
    assert "Traceback" in text and "tray failed" in text


def test_run_safely_passes_through(tmp_path):
    assert run_safely(lambda: 0, tmp_path / "h.log") == 0
