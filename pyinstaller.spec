# PyInstaller spec file for GentGranBD
# Build with: pyinstaller pyinstaller.spec

import os
import subprocess
from pathlib import Path
from PyInstaller.building.datastruct import Tree, TOC

block_cipher = None

# Application entry
app_script = os.path.join('src', 'ui', 'app.py')

datas = []

# Minimal hidden imports for PySide6 (avoid pulling entire Qt stack)
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtPrintSupport',
    'PySide6.QtPdf',
    'PySide6.QtSvg',
]

# Mac: bundle as app, Win: onefolder by default

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
    excludes=[
        # Exclude heavy Qt modules we do not use
        'PySide6.Qt3DCore', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DRender',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtDesigner', 'PySide6.QtGraphs', 'PySide6.QtHelp', 'PySide6.QtHttpServer',
        'PySide6.QtLocation', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtNetworkAuth', 'PySide6.QtNfc', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
        'PySide6.QtPositioning', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtRemoteObjects', 'PySide6.QtScxml',
        'PySide6.QtSensors', 'PySide6.QtSerialBus', 'PySide6.QtSerialPort', 'PySide6.QtSpatialAudio', 'PySide6.QtStateMachine',
        'PySide6.QtTest', 'PySide6.QtTextToSpeech', 'PySide6.QtUiTools', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
        'PySide6.QtWebSockets', 'PySide6.QtWebView',
    ],
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GentGranBD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
)

# macOS .app bundle
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    # Include asset directories
    Tree(os.path.join('src', 'ui', 'assets'), prefix='ui/assets'),
    Tree(os.path.join('src', 'extra'), prefix='extra'),
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GentGranBD'
)

# Windows icon embed (convert PNG to ICO if needed)
def _ensure_ico(png: str, ico: str) -> str | None:
    p_png = Path(png)
    p_ico = Path(ico)
    if p_ico.exists():
        return str(p_ico)
    try:
        # Use powershell and .NET to create an ICO with multiple sizes when on Windows runners
        if os.name == 'nt':
            ps = (
                '$png="{}"; $ico="{}"; '
                '$sizes=@(16,32,48,64,128,256); '
                '$b=new-object System.Drawing.Bitmap($png); '
                '$fs=new-object System.IO.FileStream($ico,[System.IO.FileMode]::Create); '
                '$ci=System.Reflection.Assembly::Load("System.Drawing").GetType("System.Drawing.IconLib.IconInputOutput"); '
                'if($ci -eq $null){$fs.Close(); return}; '
                '$fs.Close();'
            ).format(p_png, p_ico)
            subprocess.run(["powershell", "-Command", ps], check=False)
        return str(p_ico) if p_ico.exists() else None
    except Exception:
        return None

ico_path = _ensure_ico('src/extra/icon.png', 'src/extra/icon.ico') or ('src/extra/icon.ico' if Path('src/extra/icon.ico').exists() else None)
if ico_path:
    exe.icon = ico_path
