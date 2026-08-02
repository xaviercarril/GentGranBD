from pathlib import Path
from types import SimpleNamespace

from scripts import pyinstaller_postgresql
from scripts.pyinstaller_postgresql import (
    _binary_entries,
    _meets_minimum_client_major,
    _pg_dump_version,
)


def test_windows_bundle_includes_pg_dump_and_runtime_dlls(tmp_path):
    pg_dump = tmp_path / "pg_dump.exe"
    pg_restore = tmp_path / "pg_restore.exe"
    psql = tmp_path / "psql.exe"
    pg_dump.write_bytes(b"exe")
    pg_restore.write_bytes(b"exe")
    psql.write_bytes(b"exe")
    (tmp_path / "libpq.dll").write_bytes(b"dll")
    (tmp_path / "libssl-3-x64.dll").write_bytes(b"dll")
    (tmp_path / "unrelated.txt").write_text("ignored")

    entries = _binary_entries([pg_dump, pg_restore, psql], windows=True)

    assert (str(pg_dump), "postgresql/bin") in entries
    assert (str(pg_restore), "postgresql/bin") in entries
    assert (str(psql), "postgresql/bin") in entries
    assert (str(tmp_path / "libpq.dll"), "postgresql/bin") in entries
    assert (str(tmp_path / "libssl-3-x64.dll"), "postgresql/bin") in entries
    assert not any(source.endswith("unrelated.txt") for source, _ in entries)


def test_macos_bundle_only_declares_pg_dump_and_pyinstaller_collects_dylibs(tmp_path):
    pg_dump = tmp_path / "pg_dump"
    pg_restore = tmp_path / "pg_restore"
    psql = tmp_path / "psql"
    pg_dump.write_bytes(b"binary")
    pg_restore.write_bytes(b"binary")
    psql.write_bytes(b"binary")

    assert _binary_entries([pg_dump, pg_restore, psql], windows=False) == [
        (str(pg_dump), "postgresql/bin"),
        (str(pg_restore), "postgresql/bin"),
        (str(psql), "postgresql/bin"),
    ]


def test_pg_dump_versions_are_compared_numerically(monkeypatch, tmp_path):
    old_client = tmp_path / "PostgreSQL" / "9.6" / "bin" / "pg_dump.exe"
    new_client = tmp_path / "PostgreSQL" / "18" / "bin" / "pg_dump.exe"
    old_client.parent.mkdir(parents=True)
    new_client.parent.mkdir(parents=True)
    old_client.write_bytes(b"exe")
    new_client.write_bytes(b"exe")

    def fake_run(command, **options):
        version = "9.6.24" if command[0] == str(old_client) else "18.1"
        return SimpleNamespace(returncode=0, stdout=f"pg_dump (PostgreSQL) {version}", stderr="")

    monkeypatch.setattr(pyinstaller_postgresql.subprocess, "run", fake_run)

    assert _pg_dump_version(new_client) > _pg_dump_version(old_client)


def test_windows_bundle_includes_uppercase_dll_extension(tmp_path):
    tools = [tmp_path / name for name in ("pg_dump.exe", "pg_restore.exe", "psql.exe")]
    for tool in tools:
        tool.write_bytes(b"exe")
    uppercase_dll = tmp_path / "LIBPQ.DLL"
    uppercase_dll.write_bytes(b"dll")

    assert (str(uppercase_dll), "postgresql/bin") in _binary_entries(tools, windows=True)


def test_packaging_rejects_client_older_than_required_server_major(monkeypatch, tmp_path):
    pg_dump = tmp_path / "pg_dump"
    pg_dump.write_bytes(b"binary")
    monkeypatch.setenv("GENTGRAN_MIN_PG_DUMP_MAJOR", "18")
    monkeypatch.setattr(
        pyinstaller_postgresql,
        "_pg_dump_version",
        lambda path: (17, 10),
    )

    assert not _meets_minimum_client_major(pg_dump)

    monkeypatch.setattr(
        pyinstaller_postgresql,
        "_pg_dump_version",
        lambda path: (18, 4),
    )
    assert _meets_minimum_client_major(pg_dump)
