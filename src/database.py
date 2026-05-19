import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
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


def _database_url() -> str:
    """Return the configured DB URL.

    By default the desktop app keeps using the local SQLite database. For the
    PostgreSQL POC, set DATABASE_URL or GENTGRAN_DATABASE_URL in the environment.
    """
    return (
        os.getenv("GENTGRAN_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or _sqlite_url(_db_path())
    )


def _connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


DATABASE_URL = _database_url()

# Crear el motor de conexión
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQLALCHEMY_ECHO", "").lower() in {"1", "true", "yes"},
    future=True,
    connect_args=_connect_args(DATABASE_URL),
)

# Crear clase de sesión
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def ensure_schema_updates() -> None:
    """Apply small additive schema updates for existing installations."""
    inspector = inspect(engine)
    if "socios" not in inspector.get_table_names():
        return

    socio_columns = {column["name"] for column in inspector.get_columns("socios")}
    statements: list[str] = []
    if "fechaNacimiento" not in socio_columns:
        statements.append('ALTER TABLE socios ADD COLUMN "fechaNacimiento" DATE')

    if not statements:
        return

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
