# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the SamboTL *client* executable (one-file build).

Build:  pyinstaller launcher/client.spec
Output: dist/SamboTLClient.exe

The client is a portable native window (pywebview / WebView2) with buttons that
open the operator screens of the server found on the LAN.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# SPECPATH is the folder that contains this spec file (./launcher).
HERE = Path(SPECPATH).resolve()
ROOT = HERE.parent

datas = [
    (str(HERE / "client_ui.html"), "launcher"),
]

hiddenimports = [
    "webview",
    "webview.platforms.edgechromium",
    "clr_loader",
    "pythonnet",
]
hiddenimports += collect_submodules("webview")

a = Analysis(
    [str(HERE / "client.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SamboTLClient",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)