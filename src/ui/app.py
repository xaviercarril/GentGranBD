import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow
from database import engine
from models import Base
from pathlib import Path
import os
import shutil

def main():
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
    except Exception:
        pass

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
                        except Exception:
                            pass
                        break
    except Exception:
        pass

    Base.metadata.create_all(bind=engine)
    app = QApplication(sys.argv)
    try:
        app.setWindowIcon(QIcon(str(Path("extra") / "icon.png")))
    except Exception:
        pass
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()