from PIL import Image
from PyInstaller.utils.win32.versioninfo import load_version_info_from_text_file

from claude_heartbeat.icons import save_ico
from make_exe import version_info_text


def test_ico_has_explorer_and_tray_sizes(tmp_path):
    path = tmp_path / "h.ico"
    save_ico(path)
    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= Image.open(path).info["sizes"]


def test_version_info_parses_with_pyinstaller(tmp_path):
    f = tmp_path / "v.txt"
    f.write_text(version_info_text(), encoding="utf-8")
    vi = load_version_info_from_text_file(str(f))
    text = str(vi)
    for s in ("Workstation Tools", "Claude Heartbeat", "ClaudeHeartbeat.exe", "1.0.0"):
        assert s in text
    assert vi.ffi.fileVersionMS == 1 << 16 and vi.ffi.fileVersionLS == 0
