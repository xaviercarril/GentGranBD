"""Consistent database backups for the desktop application."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import Engine, URL

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


class BackupError(RuntimeError):
    """Raised when a database backup cannot be completed."""


class BackupPermissionError(BackupError):
    """Raised when a non-administrator requests a backup."""


def _is_windows() -> bool:
    return os.name == "nt"


def backup_extension(engine: Engine) -> str:
    backend = engine.url.get_backend_name()
    if backend == "sqlite":
        return ".db"
    if backend == "postgresql":
        return ".dump"
    raise BackupError(f"El motor de base de dades «{backend}» no és compatible.")


def create_database_backup(engine: Engine, target: str | Path, *, user_role: str) -> Path:
    """Create a consistent backup of *engine* at *target*.

    SQLite uses its online backup API, so a copy made while the application is
    open is still consistent. PostgreSQL uses pg_dump's custom archive format.
    A temporary file is atomically moved into place only after success.
    """
    if user_role != "ADMIN":
        raise BackupPermissionError(
            "Només els administradors poden fer còpies de seguretat de la BD."
        )

    target_path = Path(target).expanduser()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target_path.with_name(f".{target_path.name}.{uuid4().hex}.part")

    try:
        backend = engine.url.get_backend_name()
        if backend == "sqlite":
            _backup_sqlite(engine, temporary_path, target_path)
        elif backend == "postgresql":
            _backup_postgresql(engine.url, temporary_path)
        else:
            raise BackupError(f"El motor de base de dades «{backend}» no és compatible.")
        os.replace(temporary_path, target_path)
    except BackupError:
        temporary_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary_path.unlink(missing_ok=True)
        raise BackupError(str(exc)) from exc

    return target_path


def _backup_sqlite(engine: Engine, temporary_path: Path, target_path: Path) -> None:
    database = engine.url.database
    if database and database != ":memory:":
        try:
            if Path(database).resolve() == target_path.resolve():
                raise BackupError("La còpia no pot sobreescriure la base de dades en ús.")
        except OSError:
            pass

    source = engine.raw_connection()
    destination = sqlite3.connect(temporary_path)
    try:
        driver_connection = getattr(source, "driver_connection", source)
        driver_connection.backup(destination)
    finally:
        destination.close()
        source.close()


def _find_pg_dump() -> str:
    return _find_postgresql_tool("pg_dump")


def _find_pg_restore() -> str:
    return _find_postgresql_tool("pg_restore")


def _find_psql() -> str:
    return _find_postgresql_tool("psql")


def _find_postgresql_tool(tool_name: str) -> str:
    executable_name = f"{tool_name}.exe" if os.name == "nt" else tool_name
    configured = os.getenv(f"GENTGRAN_{tool_name.upper()}", "").strip()
    candidates = [configured] if configured else []
    configured_dump = os.getenv("GENTGRAN_PG_DUMP", "").strip()
    if configured_dump:
        candidates.append(str(Path(configured_dump).with_name(executable_name)))

    # PyInstaller extracts one-file applications under sys._MEIPASS. Prefer
    # the embedded client so users never need to install PostgreSQL tools.
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    candidates.extend(
        str(path)
        for path in (
            bundle_root / "postgresql" / "bin" / executable_name,
            Path(sys.executable).resolve().parent / "postgresql" / "bin" / executable_name,
            Path(sys.executable).resolve().parent
            / "_internal"
            / "postgresql"
            / "bin"
            / executable_name,
        )
    )
    discovered = shutil.which(executable_name)
    if discovered:
        candidates.append(discovered)

    if sys.platform == "darwin":
        candidates.extend(
            [
                f"/opt/homebrew/opt/libpq/bin/{tool_name}",
                f"/usr/local/opt/libpq/bin/{tool_name}",
                f"/opt/homebrew/bin/{tool_name}",
                f"/usr/local/bin/{tool_name}",
                f"/Applications/Postgres.app/Contents/Versions/latest/bin/{tool_name}",
            ]
        )

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise BackupError(
        f"No s'ha trobat l'eina {tool_name}. La versió distribuïda de l'aplicació "
        "l'hauria d'incloure; torna a instal·lar l'última versió."
    )


def _postgres_environment(url: URL) -> dict[str, str]:
    environment = os.environ.copy()
    values = {
        "PGPASSWORD": url.password,
        "PGSSLMODE": url.query.get("sslmode"),
        "PGSSLROOTCERT": url.query.get("sslrootcert"),
        "PGSSLCERT": url.query.get("sslcert"),
        "PGSSLKEY": url.query.get("sslkey"),
    }
    for key, value in values.items():
        if value:
            environment[key] = str(value)
    return environment


def _postgres_tool_environment(url: URL, tool: str) -> dict[str, str]:
    environment = _postgres_environment(url)
    if _is_windows():
        # pg_dump's DLLs are embedded beside the executable. Explicitly put
        # that directory first so transitive DLL loads do not resolve against
        # another PostgreSQL installation (or fail on machines without one).
        tool_directory = str(Path(tool).resolve().parent)
        current_path = environment.get("PATH", "")
        environment["PATH"] = (
            tool_directory + (os.pathsep + current_path if current_path else "")
        )
    return environment


def _backup_postgresql(url: URL, temporary_path: Path) -> None:
    if not url.host or not url.database:
        raise BackupError("La connexió PostgreSQL no indica el servidor o la base de dades.")

    pg_dump = _find_pg_dump()
    command = [
        pg_dump,
        "--format=custom",
        "--no-password",
        "--file",
        str(temporary_path),
        "--host",
        url.host,
        "--port",
        str(url.port or 5432),
        "--dbname",
        url.database,
    ]
    if url.username:
        command.extend(["--username", url.username])

    run_options = {
        "env": _postgres_tool_environment(url, pg_dump),
        "capture_output": True,
        "text": True,
        "errors": "replace",
        "check": False,
    }
    if _is_windows():
        run_options["creationflags"] = _CREATE_NO_WINDOW

    try:
        result = subprocess.run(command, **run_options)
    except OSError as exc:
        raise BackupError(
            "Windows no ha pogut iniciar pg_dump. Torna a instal·lar l'última "
            f"versió de GentGranBD.\nDetall: {exc}"
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Error desconegut de pg_dump").strip()
        if "server version:" in detail and "pg_dump version:" in detail:
            detail += (
                "\nLa versió de pg_dump inclosa és més antiga que el servidor. "
                "Actualitza GentGranBD a l'última versió."
            )
        raise BackupError(f"pg_dump no ha pogut crear la còpia:\n{detail}")
    if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
        raise BackupError("pg_dump ha finalitzat sense crear un arxiu de còpia vàlid.")


def restore_postgresql_backup(engine: Engine, source: str | Path, *, user_role: str) -> None:
    """Restore a custom PostgreSQL archive into the database of *engine*."""
    if user_role != "ADMIN":
        raise BackupPermissionError("Només els administradors poden restaurar la BD.")
    if engine.url.get_backend_name() != "postgresql":
        raise BackupError("La restauració PostgreSQL requereix una connexió PostgreSQL activa.")

    source_path = Path(source).expanduser()
    if not source_path.is_file():
        raise BackupError("No s'ha trobat l'arxiu de còpia seleccionat.")
    if source_path.stat().st_size == 0:
        raise BackupError("L'arxiu de còpia seleccionat està buit.")

    # Release pooled application connections before pg_restore drops tables.
    engine.dispose()
    _restore_postgresql(engine.url, source_path)


def _restore_postgresql(url: URL, source_path: Path) -> None:
    if not url.host or not url.database:
        raise BackupError("La connexió PostgreSQL no indica el servidor o la base de dades.")

    command = [
        _find_pg_restore(),
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
        "--no-password",
        "--host",
        url.host,
        "--port",
        str(url.port or 5432),
        "--dbname",
        url.database,
        str(source_path),
    ]
    if url.username:
        command.extend(["--username", url.username])

    run_options = {
        "env": _postgres_environment(url),
        "capture_output": True,
        "text": True,
        "check": False,
    }
    if _is_windows():
        run_options["creationflags"] = _CREATE_NO_WINDOW
    result = subprocess.run(command, **run_options)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Error desconegut de pg_restore").strip()
        if "transaction_timeout" in detail and "unrecognized configuration parameter" in detail:
            _restore_without_transaction_timeout(url, source_path)
            return
        raise BackupError(f"pg_restore no ha pogut restaurar la còpia:\n{detail}")


def _restore_without_transaction_timeout(url: URL, source_path: Path) -> None:
    """Restore archives made by PostgreSQL 18 to older server versions.

    PostgreSQL 18 writes ``SET transaction_timeout = 0`` into dumps. Older
    managed clusters reject that otherwise harmless command. Render the custom
    archive to SQL, remove only that setting, and execute it atomically.
    """
    rendered_path: Path | None = None
    sanitized_path: Path | None = None
    try:
        rendered_fd, rendered_name = tempfile.mkstemp(suffix=".sql", prefix="gentgran_restore_")
        os.close(rendered_fd)
        rendered_path = Path(rendered_name)
        sanitized_fd, sanitized_name = tempfile.mkstemp(suffix=".sql", prefix="gentgran_restore_")
        os.close(sanitized_fd)
        sanitized_path = Path(sanitized_name)

        render_command = [
            _find_pg_restore(),
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(rendered_path),
            str(source_path),
        ]
        render_result = subprocess.run(
            render_command,
            capture_output=True,
            text=True,
            check=False,
        )
        if render_result.returncode != 0:
            detail = (render_result.stderr or render_result.stdout or "Error desconegut de pg_restore").strip()
            raise BackupError(f"pg_restore no ha pogut preparar la restauració:\n{detail}")

        with rendered_path.open(encoding="utf-8") as rendered, sanitized_path.open("w", encoding="utf-8") as sanitized:
            for line in rendered:
                if line.strip().startswith("SET transaction_timeout"):
                    continue
                sanitized.write(line)

        command = [
            _find_psql(),
            "--no-password",
            "--set=ON_ERROR_STOP=1",
            "--single-transaction",
            "--host",
            url.host or "",
            "--port",
            str(url.port or 5432),
            "--dbname",
            url.database or "",
            "--file",
            str(sanitized_path),
        ]
        if url.username:
            command.extend(["--username", url.username])
        result = subprocess.run(
            command,
            env=_postgres_environment(url),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Error desconegut de psql").strip()
            raise BackupError(f"No s'ha pogut restaurar la còpia compatible:\n{detail}")
    finally:
        if rendered_path:
            rendered_path.unlink(missing_ok=True)
        if sanitized_path:
            sanitized_path.unlink(missing_ok=True)
