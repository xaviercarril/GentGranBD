import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from database import engine
from models import Base
from pathlib import Path
import os
import shutil

def main():
    # Ensure current working directory is the app directory, so relative resources resolve
    try:
        app_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        os.chdir(app_dir)
    except Exception:
        pass

    # In PyInstaller >=6, data may live under _internal; ensure top-level resource dirs exist
    try:
        internal = Path("_internal")
        mappings = [
            (internal / "ui" / "assets", Path("ui") / "assets"),
            (internal / "extra", Path("extra")),
        ]
        for src, dst in mappings:
            if not dst.exists() and src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copytree(src, dst)
                except FileExistsError:
                    pass
    except Exception:
        pass

    Base.metadata.create_all(bind=engine)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()