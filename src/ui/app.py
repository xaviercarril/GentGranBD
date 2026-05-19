import sys
import os
from pathlib import Path
import shutil
import traceback
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STARTUP_LOG = PROJECT_ROOT / "logs" / "app-startup.log"
RUN_ID = datetime.now().strftime("%Y%m%d-%H%M%S")


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} [{RUN_ID}] [app.py] {message}"
    print(line, flush=True)
    try:
        STARTUP_LOG.parent.mkdir(parents=True, exist_ok=True)
        with STARTUP_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def _log_exception(exc_type, exc, tb) -> None:
    detail = "".join(traceback.format_exception(exc_type, exc, tb))
    _log("Unhandled exception:\n" + detail)
    sys.__excepthook__(exc_type, exc, tb)


sys.excepthook = _log_exception

# Ensure running as a script works (python src/ui/app.py)
try:
    _src_dir = Path(__file__).resolve().parents[1]
    if str(_src_dir) not in sys.path:
        sys.path.insert(0, str(_src_dir))
except Exception as exc:
    _log(f"Could not prepare sys.path: {exc}")

def main():
    _log("=" * 72)
    _log(f"Starting app. executable={sys.executable}")
    _log(f"cwd={Path.cwd()}")
    _log(f"sys.path[0:3]={sys.path[:3]}")

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from ui.main_window import MainWindow
    from database import engine, ensure_schema_updates
    from models import Base

    safe_url = engine.url.render_as_string(hide_password=True)
    _log(f"Database backend={engine.url.get_backend_name()} url={safe_url}")

    # 1) Pick a sensible working directory that contains our resources
    resource_candidates: list[Path] = []
    try:
        resource_candidates.append(Path.cwd())
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            resource_candidates.append(exe_dir)
            # macOS .app Resources folder
            resource_candidates.append(exe_dir.parent / "Resources")
            # PyInstaller one-file extraction dir
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                resource_candidates.append(Path(meipass))
        else:
            # Dev mode: project src root
            resource_candidates.append(Path(__file__).resolve().parent.parent)
        # PyInstaller one-folder data location
        resource_candidates.append(Path("_internal"))
    except Exception:
        pass

    def _has_assets(root: Path) -> bool:
        try:
            return (root / "ui" / "assets").exists() or (root / "_internal" / "ui" / "assets").exists()
        except Exception:
            return False

    chosen_root = None
    for r in resource_candidates:
        if r and _has_assets(r):
            chosen_root = r
            break
    if chosen_root is None and resource_candidates:
        chosen_root = resource_candidates[0]

    try:
        if chosen_root:
            os.chdir(chosen_root)
            _log(f"Changed cwd to resource root={chosen_root}")
    except Exception as exc:
        _log(f"Could not change cwd to resource root: {exc}")

    # 2) Ensure resource dirs exist in the working directory (copy from available sources)
    try:
        sources: list[Path] = []
        # look in chosen root first, then other candidates
        if chosen_root:
            sources.append(Path(chosen_root))
        for r in resource_candidates:
            if r and r not in sources:
                sources.append(r)

        dest_assets = Path("ui") / "assets"
        dest_extra = Path("extra")

        for dest_rel, subpath in ((dest_assets, Path("ui") / "assets"), (dest_extra, Path("extra"))):
            needs_copy = not dest_rel.exists()
            try:
                if dest_rel.exists():
                    needs_copy = not any(dest_rel.iterdir())
            except Exception:
                needs_copy = True
            if needs_copy:
                for src_base in sources:
                    candidate = src_base / subpath
                    if candidate.exists():
                        dest_rel.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            shutil.copytree(candidate, dest_rel, dirs_exist_ok=True)
                        except Exception as exc:
                            _log(f"Could not copy resources from {candidate} to {dest_rel}: {exc}")
                        break
    except Exception as exc:
        _log(f"Resource preparation failed: {exc}")

    _log("Creating database schema if needed")
    Base.metadata.create_all(bind=engine)
    ensure_schema_updates()
    _log("Creating QApplication")
    app = QApplication(sys.argv)
    try:
        app.setWindowIcon(QIcon(str(Path("extra") / "icon.png")))
    except Exception as exc:
        _log(f"Could not set app icon: {exc}")
    _log("Creating MainWindow")
    win = MainWindow()
    _log("Showing MainWindow")
    win.show()
    win.raise_()
    win.activateWindow()
    _log("Entering Qt event loop")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
