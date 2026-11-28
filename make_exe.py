"""Build ClaudeHeartbeat.exe (PyInstaller, one-folder, no console) into dist\\ClaudeHeartbeat\\.

Usage: .\\.venv\\Scripts\\python.exe make_exe.py   (install.ps1 runs this for you)
"""
from pathlib import Path

from claude_heartbeat import APP_NAME, EXE_NAME, PUBLISHER, VERSION

ROOT = Path(__file__).resolve().parent


def version_info_text() -> str:
    """PyInstaller --version-file contents: what Task Manager and Explorer show for the exe."""
    nums = tuple(int(n) for n in VERSION.split(".")) + (0,)
    strings = {
        "CompanyName": PUBLISHER,
        "FileDescription": APP_NAME,
        "FileVersion": VERSION,
        "InternalName": EXE_NAME,
        "OriginalFilename": f"{EXE_NAME}.exe",
        "ProductName": APP_NAME,
        "ProductVersion": VERSION,
    }
    table = ", ".join(f"StringStruct({k!r}, {v!r})" for k, v in strings.items())
    return (
        "VSVersionInfo(\n"
        f"  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0,\n"
        "                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n"
        "  kids=[\n"
        f"    StringFileInfo([StringTable('040904B0', [{table}])]),\n"
        "    VarFileInfo([VarStruct('Translation', [1033, 1200])]),\n"
        "  ],\n"
        ")\n"
    )


def build() -> Path:
    """Run PyInstaller; return the absolute path of the built exe.

    Every path is absolute: PyInstaller resolves some relative ones (like --icon) against
    --specpath, which would silently drop the icon or version info."""
    import PyInstaller.__main__

    from claude_heartbeat.icons import save_ico

    work = ROOT / "build"
    work.mkdir(exist_ok=True)
    ico = work / "heartbeat.ico"
    version_file = work / "version_info.txt"
    save_ico(ico)
    version_file.write_text(version_info_text(), encoding="utf-8")
    PyInstaller.__main__.run([
        str(ROOT / "run.pyw"),
        "--name", EXE_NAME,
        "--onedir", "--windowed", "--noconfirm", "--clean",
        "--icon", str(ico),
        "--version-file", str(version_file),
        "--hidden-import", "pystray._win32",  # pystray picks its backend at runtime
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(work / "pyi"),
        "--specpath", str(work),
    ])
    return ROOT / "dist" / EXE_NAME / f"{EXE_NAME}.exe"


if __name__ == "__main__":
    print(build())
