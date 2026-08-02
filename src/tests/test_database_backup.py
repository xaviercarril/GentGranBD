import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text

import database_backup
from database_backup import (
    BackupError,
    BackupPermissionError,
    backup_extension,
    create_database_backup,
    restore_postgresql_backup,
)


def test_sqlite_backup_is_consistent_and_readable(tmp_path):
    source_path = tmp_path / "source.db"
    target_path = tmp_path / "backups" / "copy.db"
    engine = create_engine(f"sqlite:///{source_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE example (id INTEGER PRIMARY KEY, value TEXT)"))
        connection.execute(text("INSERT INTO example (value) VALUES ('guardat')"))

    result = create_database_backup(engine, target_path, user_role="ADMIN")

    assert result == target_path
    with sqlite3.connect(target_path) as connection:
        assert connection.execute("SELECT value FROM example").fetchone() == ("guardat",)


def test_sqlite_backup_does_not_overwrite_database_in_use(tmp_path):
    source_path = tmp_path / "source.db"
    engine = create_engine(f"sqlite:///{source_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE example (id INTEGER)"))

    with pytest.raises(BackupError, match="no pot sobreescriure"):
        create_database_backup(engine, source_path, user_role="ADMIN")


def test_backup_service_rejects_non_admin_before_writing(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    target = tmp_path / "forbidden.db"

    with pytest.raises(BackupPermissionError, match="administradors"):
        create_database_backup(engine, target, user_role="USER")

    assert not target.exists()


def test_postgresql_backup_uses_digitalocean_connection_securely(tmp_path, monkeypatch):
    engine = create_engine(
        "postgresql+psycopg://doadmin:secret@example.ondigitalocean.com:25060/"
        "gentgran?sslmode=require"
    )
    pg_dump = tmp_path / "pg_dump"
    pg_dump.write_text("")
    monkeypatch.setattr(database_backup, "_find_pg_dump", lambda: str(pg_dump))
    captured = {}

    def fake_run(command, **options):
        captured["command"] = command
        captured["options"] = options
        output_path = Path(command[command.index("--file") + 1])
        output_path.write_bytes(b"PGDMP-test")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(database_backup.subprocess, "run", fake_run)
    target = tmp_path / "digitalocean.dump"

    create_database_backup(engine, target, user_role="ADMIN")

    assert target.read_bytes() == b"PGDMP-test"
    assert "example.ondigitalocean.com" in captured["command"]
    assert "25060" in captured["command"]
    assert "secret" not in " ".join(captured["command"])
    assert captured["options"]["env"]["PGPASSWORD"] == "secret"
    assert captured["options"]["env"]["PGSSLMODE"] == "require"


def test_failed_postgresql_backup_leaves_no_output(tmp_path, monkeypatch):
    engine = create_engine("postgresql+psycopg://user:secret@db.example/gentgran")
    monkeypatch.setattr(database_backup, "_find_pg_dump", lambda: "/fake/pg_dump")
    monkeypatch.setattr(
        database_backup.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="connection failed"),
    )
    target = tmp_path / "failed.dump"

    with pytest.raises(BackupError, match="connection failed"):
        create_database_backup(engine, target, user_role="ADMIN")

    assert not target.exists()
    assert not list(tmp_path.glob("*.part"))


def test_postgresql_backup_explains_client_server_version_mismatch(tmp_path, monkeypatch):
    engine = create_engine("postgresql+psycopg://user:secret@db.example/gentgran")
    monkeypatch.setattr(database_backup, "_find_pg_dump", lambda: "/fake/pg_dump")
    monkeypatch.setattr(
        database_backup.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr=(
                "pg_dump: error: server version: 18.1; "
                "pg_dump version: 16.4\npg_dump: error: aborting because of server version mismatch"
            ),
        ),
    )

    with pytest.raises(BackupError, match="Actualitza GentGranBD"):
        create_database_backup(engine, tmp_path / "failed.dump", user_role="ADMIN")


def test_windows_pg_dump_prefers_its_embedded_dll_directory(tmp_path, monkeypatch):
    engine = create_engine("postgresql+psycopg://user:secret@db.example/gentgran")
    pg_dump = tmp_path / "postgresql" / "bin" / "pg_dump.exe"
    pg_dump.parent.mkdir(parents=True)
    pg_dump.write_bytes(b"exe")
    monkeypatch.setattr(database_backup, "_find_pg_dump", lambda: str(pg_dump))
    monkeypatch.setattr(database_backup, "_is_windows", lambda: True)
    monkeypatch.setenv("PATH", "C:\\Windows\\System32")
    captured = {}

    def fake_run(command, **options):
        captured.update(options)
        Path(command[command.index("--file") + 1]).write_bytes(b"PGDMP-test")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(database_backup.subprocess, "run", fake_run)
    create_database_backup(engine, tmp_path / "copy.dump", user_role="ADMIN")

    assert captured["env"]["PATH"].split(os.pathsep, 1)[0] == str(pg_dump.parent)
    assert captured["creationflags"] == database_backup._CREATE_NO_WINDOW


def test_backup_extensions():
    assert backup_extension(create_engine("sqlite:///:memory:")) == ".db"
    assert backup_extension(create_engine("postgresql+psycopg://u:p@host/db")) == ".dump"


def test_find_pg_dump_prefers_tool_embedded_by_pyinstaller(tmp_path, monkeypatch):
    embedded = tmp_path / "postgresql" / "bin" / "pg_dump"
    embedded.parent.mkdir(parents=True)
    embedded.write_bytes(b"embedded")
    monkeypatch.setattr(database_backup.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert database_backup._find_pg_dump() == str(embedded)


def test_postgresql_restore_uses_embedded_tool_and_safe_options(tmp_path, monkeypatch):
    engine = create_engine(
        "postgresql+psycopg://doadmin:secret@example.ondigitalocean.com:25060/"
        "gentgran?sslmode=require"
    )
    source = tmp_path / "backup.dump"
    source.write_bytes(b"PGDMP")
    monkeypatch.setattr(database_backup, "_find_pg_restore", lambda: "/bundle/pg_restore")
    captured = {}

    def fake_run(command, **options):
        captured["command"] = command
        captured["options"] = options
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(database_backup.subprocess, "run", fake_run)
    restore_postgresql_backup(engine, source, user_role="ADMIN")

    assert "--clean" in captured["command"]
    assert "--if-exists" in captured["command"]
    assert "--no-owner" in captured["command"]
    assert "--exit-on-error" in captured["command"]
    assert str(source) in captured["command"]
    assert "secret" not in " ".join(captured["command"])
    assert captured["options"]["env"]["PGPASSWORD"] == "secret"


def test_postgresql_restore_requires_admin(tmp_path):
    engine = create_engine("postgresql+psycopg://u:p@host/db")
    source = tmp_path / "backup.dump"
    source.write_bytes(b"PGDMP")

    with pytest.raises(BackupPermissionError, match="administradors"):
        restore_postgresql_backup(engine, source, user_role="USER")


def test_postgresql_restore_retries_older_server_without_transaction_timeout(tmp_path, monkeypatch):
    engine = create_engine("postgresql+psycopg://doadmin:secret@db.example/gentgran?sslmode=require")
    source = tmp_path / "backup.dump"
    source.write_bytes(b"PGDMP")
    monkeypatch.setattr(database_backup, "_find_pg_restore", lambda: "/bundle/pg_restore")
    monkeypatch.setattr(database_backup, "_find_psql", lambda: "/bundle/psql")
    commands = []

    def fake_run(command, **options):
        commands.append((command, options))
        if len(commands) == 1:
            return SimpleNamespace(
                returncode=1,
                stdout="",
                stderr='ERROR: unrecognized configuration parameter "transaction_timeout"',
            )
        if len(commands) == 2:
            output = Path(command[command.index("--file") + 1])
            output.write_text("SET transaction_timeout = 0;\nCREATE TABLE restored (id integer);\n")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        assert "transaction_timeout" not in Path(command[command.index("--file") + 1]).read_text()
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(database_backup.subprocess, "run", fake_run)
    restore_postgresql_backup(engine, source, user_role="ADMIN")

    assert len(commands) == 3
    assert commands[-1][0][0] == "/bundle/psql"
    assert commands[-1][1]["env"]["PGPASSWORD"] == "secret"
