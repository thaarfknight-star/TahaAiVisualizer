# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller build.spec
# Output goes to dist/TahaAiVisualizer(.exe)

import sys
from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None

binaries = []
binaries += collect_dynamic_libs("soundcard")
binaries += collect_dynamic_libs("sounddevice")
binaries += collect_dynamic_libs("soundfile")

icon_file = "assets/icon.ico" if sys.platform.startswith("win") else None

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=[("assets", "assets")],
    hiddenimports=["soundcard", "sounddevice", "soundfile"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="TahaAiVisualizer",
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
    icon=icon_file,
)
