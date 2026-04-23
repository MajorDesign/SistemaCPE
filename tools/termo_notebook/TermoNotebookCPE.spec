# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['termo_notebook.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.png', '.'), ('VERSION', '.'), ('config.ini', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'PIL.ImageQt', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'scipy', 'pytest', 'test', 'unittest'],
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
    name='TermoNotebookCPE',
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
    icon=['logo.png'],
)
