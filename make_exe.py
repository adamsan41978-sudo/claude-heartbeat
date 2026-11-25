"""Build ClaudeHeartbeat.exe (PyInstaller, one-folder, no console) into dist\\ClaudeHeartbeat\\.

Usage: .\\.venv\\Scripts\\python.exe make_exe.py   (install.ps1 runs this for you)
"""
from claude_heartbeat import APP_NAME, EXE_NAME, PUBLISHER, VERSION


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
