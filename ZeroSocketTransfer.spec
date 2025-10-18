# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[('img', 'img')],
    hiddenimports=['PIL._tkinter_finder'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=None
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='ZeroSocketTransfer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    onefile=True,
    icon='img/icon.png'
)
