# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the SamboTL *server* executable (one-file build).

Build:  pyinstaller launcher/server.spec
Output: dist/SamboTLServer.exe

The server bundles Django + Channels (daphne), WhiteNoise static files and the
Vue SPA, so a single .exe serves the whole tournament over the LAN.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# SPECPATH is the folder that contains this spec file (./launcher).
ROOT = Path(SPECPATH).resolve().parent

datas = []
# Collected static (admin/Unfold/DRF) — served by WhiteNoise from _MEIPASS/staticfiles.
staticfiles = ROOT / "staticfiles"
if staticfiles.exists():
    datas.append((str(staticfiles), "staticfiles"))
# SPA assets (also reachable at /static/spa/ and used by the /app/ view).
spa = ROOT / "static" / "spa"
if spa.exists():
    datas.append((str(spa), "static/spa"))
# Project templates, if present.
templates = ROOT / "templates"
if templates.exists():
    datas.append((str(templates), "templates"))
# The visual GUI assets (server panel + client operator UI).
datas.append((str(ROOT / "launcher" / "server_gui.html"), "launcher"))
# Data files (templates/static) bundled with third-party packages.
for package in ("autobahn", "daphne", "channels", "rest_framework", "unfold"):
    datas += collect_data_files(package)

hiddenimports = [
    "daphne",
    "daphne.server",
    "daphne.endpoints",
    "launcher.server_gui",
    "webview",
    "channels",
    "channels.layers",
    "channels.routing",
    "channels.auth",
    "asgiref",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authentication",
    "rest_framework.renderers",
    "rest_framework.pagination",
    "corsheaders",
    "corsheaders.middleware",
    "corsheaders.apps",
    "whitenoise",
    "whitenoise.middleware",
]
# Django loads apps by dotted string — discover everything dynamically.
hiddenimports += collect_submodules("config")
hiddenimports += collect_submodules("apps")
hiddenimports += collect_submodules("launcher")
for package in (
    "unfold",
    "corsheaders",
    "whitenoise",
    "rest_framework",
    "channels",
    "daphne",
):
    hiddenimports += collect_submodules(package)

a = Analysis(
    [str(ROOT / "launcher" / "server.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "numpy", "pandas", "PyQt5", "PySide6",
        # Optional native WebSocket accelerators — pure-Python fallback is used.
        "autobahn.nvx",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SamboTLServer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
)

