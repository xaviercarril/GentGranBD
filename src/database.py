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


def default_database_url() -> str:
    return _database_url()


def set_database_url(database_url: str | None) -> None:
    """Configure the process-wide SQLAlchemy engine and existing SessionLocal.

    Controllers import SessionLocal directly, so keep the same sessionmaker
    object and rebind it instead of replacing it.
    """
    global DATABASE_URL, engine

    new_url = (database_url or "").strip() or default_database_url()
    if new_url == DATABASE_URL:
        return

    try:
        engine.dispose()
    except Exception:
        pass

    DATABASE_URL = new_url
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv("SQLALCHEMY_ECHO", "").lower() in {"1", "true", "yes"},
        future=True,
        connect_args=_connect_args(DATABASE_URL),
    )
    SessionLocal.configure(bind=engine)


def _drop_personal_dni_sqlite() -> None:
    """Rebuild legacy SQLite personal table without the obsolete dniNie field."""
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("DROP TABLE IF EXISTS personal_new"))
        conn.execute(
            text(
                """
                CREATE TABLE personal_new (
                    id INTEGER NOT NULL,
                    nombre VARCHAR(50) NOT NULL,
                    apellido1 VARCHAR(50),
                    apellido2 VARCHAR(50),
                    email VARCHAR(100),
                    "telfMovil" VARCHAR(20),
                    observaciones TEXT,
                    tipo VARCHAR(50),
                    PRIMARY KEY (id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO personal_new (
                    id, nombre, apellido1, apellido2, email,
                    "telfMovil", observaciones, tipo
                )
                SELECT
                    id, nombre, apellido1, apellido2, email,
                    "telfMovil", observaciones, tipo
                FROM personal
                """
            )
        )
        conn.execute(text("DROP TABLE personal"))
        conn.execute(text("ALTER TABLE personal_new RENAME TO personal"))
        conn.execute(text("PRAGMA foreign_keys=ON"))


def _rebuild_matricula_pagos_sqlite_for_inscripcion_id() -> None:
    """Rebuild legacy SQLite payment table with nullable socioID and inscripcionID."""
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("DROP TABLE IF EXISTS matricula_pagos_new"))
        conn.execute(
            text(
                """
                CREATE TABLE matricula_pagos_new (
                    id INTEGER NOT NULL,
                    "socioID" INTEGER,
                    "actividadID" INTEGER NOT NULL,
                    "inscripcionID" INTEGER,
                    fecha DATE NOT NULL,
                    importe DECIMAL(10, 2) NOT NULL,
                    estado VARCHAR(7) NOT NULL,
                    observaciones TEXT,
                    PRIMARY KEY (id),
                    CONSTRAINT fk_matricula_inscripcion
                        FOREIGN KEY("socioID", "actividadID")
                        REFERENCES inscripciones ("socioID", "actividadID")
                        ON DELETE CASCADE
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO matricula_pagos_new (
                    id, "socioID", "actividadID", "inscripcionID",
                    fecha, importe, estado, observaciones
                )
                SELECT
                    p.id,
                    p."socioID",
                    p."actividadID",
                    (
                        SELECT i.id
                        FROM inscripciones i
                        WHERE i."socioID" = p."socioID"
                          AND i."actividadID" = p."actividadID"
                        LIMIT 1
                    ),
                    p.fecha,
                    p.importe,
                    p.estado,
                    p.observaciones
                FROM matricula_pagos p
                """
            )
        )
        conn.execute(text("DROP TABLE matricula_pagos"))
        conn.execute(text("ALTER TABLE matricula_pagos_new RENAME TO matricula_pagos"))
        conn.execute(text("PRAGMA foreign_keys=ON"))


def ensure_schema_updates() -> None:
    """Apply schema updates for existing installations."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "usuarios" not in table_names:
        from models import Usuario

        Usuario.__table__.create(bind=engine, checkfirst=True)
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
    if "socios" not in table_names:
        return

    socio_columns = {column["name"] for column in inspector.get_columns("socios")}
    personal_columns = (
        {column["name"] for column in inspector.get_columns("personal")}
        if "personal" in table_names
        else set()
    )
    inscripcion_columns = (
        {column["name"] for column in inspector.get_columns("inscripciones")}
        if "inscripciones" in table_names
        else set()
    )
    actividad_columns = (
        {column["name"] for column in inspector.get_columns("actividades")}
        if "actividades" in table_names
        else set()
    )
    pago_columns_info = (
        inspector.get_columns("matricula_pagos")
        if "matricula_pagos" in table_names
        else []
    )
    pago_columns = {column["name"] for column in pago_columns_info}
    pago_socio_not_null = any(
        column["name"] == "socioID" and not column.get("nullable", True)
        for column in pago_columns_info
    )
    statements: list[str] = []
    if "fechaNacimiento" not in socio_columns:
        statements.append('ALTER TABLE socios ADD COLUMN "fechaNacimiento" DATE')
    if "inscripciones" in table_names and "noSocioNombre" not in inscripcion_columns:
        statements.append('ALTER TABLE inscripciones ADD COLUMN "noSocioNombre" VARCHAR(100)')
    if "inscripciones" in table_names and "noSocioApellido1" not in inscripcion_columns:
        statements.append('ALTER TABLE inscripciones ADD COLUMN "noSocioApellido1" VARCHAR(100)')
    if "inscripciones" in table_names and "noSocioApellido2" not in inscripcion_columns:
        statements.append('ALTER TABLE inscripciones ADD COLUMN "noSocioApellido2" VARCHAR(100)')
    if "inscripciones" in table_names and "noSocioDni" not in inscripcion_columns:
        statements.append('ALTER TABLE inscripciones ADD COLUMN "noSocioDni" VARCHAR(20)')
    if "inscripciones" in table_names and "noSocioTelefono" not in inscripcion_columns:
        statements.append('ALTER TABLE inscripciones ADD COLUMN "noSocioTelefono" VARCHAR(20)')
    if "inscripciones" in table_names and "noSocioEmail" not in inscripcion_columns:
        statements.append('ALTER TABLE inscripciones ADD COLUMN "noSocioEmail" VARCHAR(100)')
    if "inscripciones" in table_names and "noSocioObservaciones" not in inscripcion_columns:
        statements.append('ALTER TABLE inscripciones ADD COLUMN "noSocioObservaciones" TEXT')
    if "actividades" in table_names and "tipo" not in actividad_columns:
        statements.append("ALTER TABLE actividades ADD COLUMN tipo VARCHAR(6) NOT NULL DEFAULT 'CURS'")
    rebuild_pagos_sqlite = (
        "matricula_pagos" in table_names
        and engine.url.get_backend_name() == "sqlite"
        and ("inscripcionID" not in pago_columns or pago_socio_not_null)
    )
    if "matricula_pagos" in table_names and engine.url.get_backend_name() != "sqlite":
        if "inscripcionID" not in pago_columns:
            statements.append('ALTER TABLE matricula_pagos ADD COLUMN "inscripcionID" INTEGER')
        if pago_socio_not_null:
            statements.append('ALTER TABLE matricula_pagos ALTER COLUMN "socioID" DROP NOT NULL')
    if "dniNie" in personal_columns and engine.url.get_backend_name() != "sqlite":
        statements.append('ALTER TABLE personal DROP COLUMN "dniNie"')

    if statements:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
            if "actividades" in table_names:
                conn.execute(text("UPDATE actividades SET tipo = 'CURS' WHERE tipo IS NULL OR tipo = ''"))
            if (
                "matricula_pagos" in table_names
                and "inscripcionID" not in pago_columns
                and engine.url.get_backend_name() != "sqlite"
            ):
                conn.execute(
                    text(
                        """
                        UPDATE matricula_pagos
                        SET "inscripcionID" = (
                            SELECT i.id
                            FROM inscripciones i
                            WHERE i."socioID" = matricula_pagos."socioID"
                              AND i."actividadID" = matricula_pagos."actividadID"
                            LIMIT 1
                        )
                        WHERE "inscripcionID" IS NULL
                        """
                    )
                )

    if "dniNie" in personal_columns and engine.url.get_backend_name() == "sqlite":
        _drop_personal_dni_sqlite()

    if rebuild_pagos_sqlite:
        _rebuild_matricula_pagos_sqlite_for_inscripcion_id()

    if not statements and "dniNie" not in personal_columns:
        return
