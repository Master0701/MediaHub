# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path.cwd()

MAIN_FILE = ROOT / "main.py"
ASSETS_DIR = ROOT / "assets"
ICON_FILE = ROOT / "assets" / "icons" / "mediahub.ico"
VERSION_FILE = ROOT / "version_info.txt"

datas = []

if ASSETS_DIR.exists():
    datas.append((str(ASSETS_DIR), "assets"))

a = Analysis(
    [str(MAIN_FILE)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MediaHub",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
    icon=[str(ICON_FILE)] if ICON_FILE.exists() else None,
)