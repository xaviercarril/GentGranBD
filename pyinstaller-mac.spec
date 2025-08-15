# macOS .app spec for GentGranBD
# Build with: python -m PyInstaller pyinstaller-mac.spec

import os
block_cipher = None

app_script = os.path.join('src', 'ui', 'app.py')

# Include assets via datas (directory copies)
datas = [
    (os.path.join('src', 'ui', 'assets'), 'ui/assets'),
    (os.path.join('src', 'extra'), 'extra'),
]

hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtPrintSupport',
    'PySide6.QtPdf',
    'PySide6.QtSvg',
]

excludes = [
    'PySide6.Qt3DCore', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DRender',
    'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtDesigner', 'PySide6.QtGraphs', 'PySide6.QtHelp', 'PySide6.QtHttpServer',
    'PySide6.QtLocation', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtNetworkAuth', 'PySide6.QtNfc', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
    'PySide6.QtPositioning', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtRemoteObjects', 'PySide6.QtScxml',
    'PySide6.QtSensors', 'PySide6.QtSerialBus', 'PySide6.QtSerialPort', 'PySide6.QtSpatialAudio', 'PySide6.QtStateMachine',
    'PySide6.QtTest', 'PySide6.QtTextToSpeech', 'PySide6.QtUiTools', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
    'PySide6.QtWebSockets', 'PySide6.QtWebView',
]

a = Analysis([
    app_script,
],
    pathex=['.', 'src'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Important: do NOT exclude binaries. Pass them to EXE.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GentGranBD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
)

app = BUNDLE(
    exe,
    name='GentGranBD.app',
    icon=None,
    bundle_identifier='org.gentgranbd.app',
    info_plist={
        'CFBundleName': 'GentGranBD',
        'CFBundleDisplayName': 'GentGranBD',
        'NSHighResolutionCapable': True,
    },
)
