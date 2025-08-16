# macOS .app spec for GentGranBD
# Build with: python -m PyInstaller pyinstaller-mac.spec

import os
import sys
from pathlib import Path
import subprocess
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

# Try to ensure ICNS exists from PNG
def _ensure_icns(png_path: str, icns_path: str) -> str | None:
    p_png = Path(png_path)
    p_icns = Path(icns_path)
    if p_icns.exists():
        return str(p_icns)
    try:
        iconset = Path('build') / 'icon.iconset'
        iconset.mkdir(parents=True, exist_ok=True)
        sizes = [16, 32, 64, 128, 256, 512]
        for s in sizes:
            out = iconset / f'icon_{s}x{s}.png'
            subprocess.run(['sips', '-z', str(s), str(s), str(p_png), '--out', str(out)], check=True, stdout=subprocess.DEVNULL)
        # Create 2x versions for mac
        for s in [16, 32, 128, 256, 512]:
            out2 = iconset / f'icon_{s}x{s}@2x.png'
            subprocess.run(['sips', '-z', str(s*2), str(s*2), str(p_png), '--out', str(out2)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['iconutil', '-c', 'icns', str(iconset), '-o', str(p_icns)], check=True, stdout=subprocess.DEVNULL)
        return str(p_icns)
    except Exception:
        return None

icon_png = os.path.join('src', 'extra', 'icon.png')
icon_icns = os.path.join('src', 'extra', 'icon.icns')
bundle_icon = _ensure_icns(icon_png, icon_icns) or (icon_icns if Path(icon_icns).exists() else None)

app = BUNDLE(
    exe,
    name='GentGranBD.app',
    icon=bundle_icon,
    bundle_identifier='org.gentgranbd.app',
    info_plist={
        'CFBundleName': 'GentGranBD',
        'CFBundleDisplayName': 'GentGranBD',
        'NSHighResolutionCapable': True,
    },
)
