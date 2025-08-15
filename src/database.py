import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _user_data_dir(app_name: str = "GentGranBD") -> Path:
    """Return a writable user-data directory per platform.
    macOS: ~/Library/Application Support/<app_name>
    Windows: %APPDATA%\\<app_name>
    Linux/Other: ~/.local/share/<app_name>
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path.home() / ".local" / "share"
    target = base / app_name
    target.mkdir(parents=True, exist_ok=True)
    return target


def _db_path() -> Path:
    """Compute the SQLite DB path.
    - In a frozen executable, store under the user-data dir.
    - In dev (non-frozen), store alongside source (src/gentgran.db).
    """
    if getattr(sys, "frozen", False):
        return _user_data_dir() / "gentgran.db"
    # dev: put DB in repo src folder
    return Path(__file__).resolve().parent / "gentgran.db"


def _sqlite_url(path: Path) -> str:
    # SQLAlchemy SQLite URL for absolute path
    # Use POSIX path to avoid backslash escaping issues on Windows
    return f"sqlite:///{path.resolve().as_posix()}"


# Ruta de la base de datos SQLite
DATABASE_URL = _sqlite_url(_db_path())

# Crear el motor de conexión
engine = create_engine(DATABASE_URL, echo=False, future=True)

# Crear clase de sesión
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)