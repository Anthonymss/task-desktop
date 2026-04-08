import os

common_hiddenimports = [
    'apscheduler',
    'apscheduler.schedulers',
    'apscheduler.schedulers.background',
]

excluded_modules = [
    'PySide6.QtWebEngine', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets',
    'PySide6.Qt3D', 'PySide6.QtCharts', 'PySide6.QtDataVisualization',
    'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
    'PySide6.QtPositioning', 'PySide6.QtLocation',
    'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtSensors',
    'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtStateMachine',
    'PySide6.QtTest', 'PySide6.QtXml', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets'
]

a_ui = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=common_hiddenimports + ['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=False,
    optimize=0,
)
pyz_ui = PYZ(a_ui.pure)

exe_ui = EXE(
    pyz_ui,
    a_ui.scripts,
    a_ui.binaries,
    a_ui.datas,
    [],
    name='CronVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=['resources/cronvault.ico'],
)

a_svc = Analysis(
    ['src/service.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=common_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'shiboken6', 'PyQt6', 'PyQt5'],
    noarchive=False,
    optimize=0,
)
pyz_svc = PYZ(a_svc.pure)

exe_svc = EXE(
    pyz_svc,
    a_svc.scripts,
    a_svc.binaries,
    a_svc.datas,
    [],
    name='CronVaultService',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
)
