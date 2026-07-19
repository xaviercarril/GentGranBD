# Packaging GentGranBD for macOS and Windows

This app uses PySide6 and bundles as a standalone executable via PyInstaller.

## Prerequisites
- Python 3.11+ installed
- On macOS: Xcode Command Line Tools and `libpq` from Homebrew installed
- On Windows: Python launcher `py` and PostgreSQL client tools available during the build

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
- Run the task "package:win" (Windows one-file)
- Run the task "installer:win" (Windows installer via NSIS)

Or from terminal:

```sh
# macOS/Linux
pyinstaller pyinstaller.spec

# Windows
py -m PyInstaller pyinstaller-win.spec --noconfirm
```

Artifacts will be under `dist/`.
- macOS one-folder: `GentGranBD/GentGranBD` binary
- macOS .app: `GentGranBD/GentGranBD.app`
- Windows one-file: `dist/GentGranBD.exe`

All distributable artifacts embed `pg_dump` (and its required dynamic
libraries on Windows/macOS). End users therefore do not need Homebrew,
PostgreSQL or any separate client installation to back up DigitalOcean. The
build intentionally fails if `pg_dump` cannot be found, preventing publication
of an incomplete application. `GENTGRAN_PG_DUMP` can select a specific client
binary at build time.

## Notes
- The SQLite database is stored in a user-writable directory:
  - macOS: `~/Library/Application Support/GentGranBD/gentgran.db`
  - Windows: `%APPDATA%\\GentGranBD\\gentgran.db`
  - Linux: `~/.local/share/GentGranBD/gentgran.db`
- For PostgreSQL/DigitalOcean in packaged builds, store the connection in:
  - macOS: `~/Library/Application Support/GentGranBD/database.env`
  - Windows: `%APPDATA%\\GentGranBD\\database.env`
  - Linux: `~/.local/share/GentGranBD/database.env`
- Assets under `src/ui/assets` and `src/extra` are bundled; relative paths like `ui/assets/...` and `extra/logo.png` are resolved at runtime.
- If you need a macOS `.app` bundle or notarization, we can add a macOS-specific spec using `BUNDLE` and a proper Info.plist.

Create the production database config once on each machine:

```sh
python3 scripts/configure_database.py
```

The script prompts for the DigitalOcean password and writes `database.env` outside the app/repo. After that, the packaged app can be opened from Finder/Explorer without entering the database URL each time.
 
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
makensis -DAPP_EXE=dist\GentGranBD.exe installer\installer.nsi
```

Do not pass `dist\GentGranBD\GentGranBD.exe` as `APP_EXE`: that is the launcher from a PyInstaller one-folder build and needs the adjacent `_internal` runtime directory. Packaging only that EXE causes startup errors such as `Failed to load Python DLL ... python311.dll`.
