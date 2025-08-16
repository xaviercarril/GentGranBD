# Windows one-file executable with installer preparation
# Build app with: py -m PyInstaller pyinstaller-win.spec

import os
from pathlib import Path
block_cipher = None

app_script = os.path.join('src', 'ui', 'app.py')

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

def _ensure_ico(png_path: str, ico_path: str) -> str | None:
    p_png = Path(png_path)
    p_ico = Path(ico_path)
    if p_ico.exists():
        return str(p_ico)
    if not p_png.exists():
        return None
    try:
        # Generate a multi-size ICO from PNG using Pillow
        from PIL import Image
        img = Image.open(p_png).convert("RGBA")
        sizes = [(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)]
        # Save ICO with multiple sizes; Pillow will resize as needed
        img.save(p_ico, format='ICO', sizes=sizes)
        return str(p_ico)
    except Exception:
        return None

ico = _ensure_ico('src/extra/icon.png', 'src/extra/icon.ico') or (str(Path('src/extra/icon.ico')) if Path('src/extra/icon.ico').exists() else None)

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
    icon=ico,
)
