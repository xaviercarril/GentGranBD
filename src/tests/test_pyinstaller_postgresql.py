from pathlib import Path

from scripts.pyinstaller_postgresql import _binary_entries


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
