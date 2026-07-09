# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\eigenes program\\MediaHub\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\eigenes program\\MediaHub\\assets', 'assets')],
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
    name='MediaHub',
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
    version='D:\\eigenes program\\MediaHub\\version_info.txt',
    icon=['D:\\eigenes program\\MediaHub\\assets\\icons\\mediahub.ico'],
)
