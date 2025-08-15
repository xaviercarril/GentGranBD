# Packaging GentGranBD for macOS and Windows

This app uses PySide6 and bundles as a standalone executable via PyInstaller.

## Prerequisites
- Python 3.11+ installed
- On macOS: Xcode Command Line Tools installed (for codesign if needed)
- On Windows: Python launcher `py` available

## One-time setup
Install dependencies:

```sh
# macOS / Linux
python3 -m pip install -r requirements.txt

# Windows
py -m pip install -r requirements.txt
```

## Build

Using VS Code tasks:
- Run the task "package:mac" (macOS one-folder)
- Run the task "package:mac-app" (macOS .app bundle)
- Run the task "package:win" (Windows one-folder)
- Run the task "installer:win" (Windows installer via NSIS)

Or from terminal:

```sh
# macOS/Linux
pyinstaller pyinstaller.spec

# Windows
pyinstaller pyinstaller.spec
```

Artifacts will be under `dist/GentGranBD/`.
- macOS one-folder: `GentGranBD/GentGranBD` binary
- macOS .app: `GentGranBD/GentGranBD.app`
- Windows: `GentGranBD/GentGranBD.exe`

## Notes
- The SQLite database is stored in a user-writable directory:
  - macOS: `~/Library/Application Support/GentGranBD/gentgran.db`
  - Windows: `%APPDATA%\\GentGranBD\\gentgran.db`
  - Linux: `~/.local/share/GentGranBD/gentgran.db`
- Assets under `src/ui/assets` and `src/extra` are bundled; relative paths like `ui/assets/...` and `extra/logo.png` are resolved at runtime.
- If you need a macOS `.app` bundle or notarization, we can add a macOS-specific spec using `BUNDLE` and a proper Info.plist.
 
### macOS .app
Build a native app bundle:
```sh
python3 -m PyInstaller pyinstaller-mac.spec
open dist/GentGranBD/GentGranBD.app
```

### Windows installer
1) Build app:
```bat
py -m PyInstaller pyinstaller-win.spec
```
2) Build installer with NSIS (requires NSIS installed):
```bat
makensis installer\installer.nsi
```
