"""Locate PostgreSQL client tools that must be embedded by PyInstaller."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _pg_dump_version(path: Path) -> tuple[int, ...]:
    """Return the client version, keeping unusable executables at the end."""
    try:
        result = subprocess.run(
            [str(path), "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
        )
    except OSError:
        return ()
    if result.returncode != 0:
        return ()
    match = re.search(r"\b(\d+(?:\.\d+){0,3})\b", result.stdout or result.stderr)
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def _is_complete_windows_client(pg_dump: Path) -> bool:
    if os.name != "nt":
        return True
    directory = pg_dump.parent
    return all(
        (directory / name).is_file()
        for name in ("pg_restore.exe", "psql.exe", "libpq.dll")
    )


def _meets_minimum_client_major(pg_dump: Path) -> bool:
    configured = os.getenv("GENTGRAN_MIN_PG_DUMP_MAJOR", "").strip()
    if not configured:
        return True
    try:
        minimum_major = int(configured)
    except ValueError as exc:
        raise SystemExit("GENTGRAN_MIN_PG_DUMP_MAJOR must be an integer.") from exc
    version = _pg_dump_version(pg_dump)
    return bool(version) and version[0] >= minimum_major


def _pg_dump_candidates() -> list[Path]:
    executable_name = "pg_dump.exe" if os.name == "nt" else "pg_dump"
    candidates: list[Path] = []

    configured = os.getenv("GENTGRAN_PG_DUMP", "").strip()
    if configured:
        candidates.append(Path(configured))

    if sys.platform == "darwin":
        candidates.extend(
            Path(path)
            for path in (
                "/opt/homebrew/opt/libpq/bin/pg_dump",
                "/usr/local/opt/libpq/bin/pg_dump",
                "/opt/homebrew/bin/pg_dump",
                "/usr/local/bin/pg_dump",
                "/Applications/Postgres.app/Contents/Versions/latest/bin/pg_dump",
            )
        )
    elif os.name == "nt":
        installed: list[Path] = []
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            root = os.getenv(variable)
            if not root:
                continue
            postgresql_root = Path(root) / "PostgreSQL"
            if postgresql_root.is_dir():
                installed.extend(postgresql_root.glob("*/bin/pg_dump.exe"))

        # pg_dump refuses to dump a server from a newer major release. Prefer
        # the newest installed client; lexicographical path sorting gets e.g.
        # PostgreSQL 9.6 and 18 in the wrong order.
        candidates.extend(
            sorted(installed, key=lambda path: _pg_dump_version(path), reverse=True)
        )

    discovered = shutil.which(executable_name)
    if discovered:
        candidates.append(Path(discovered))
    return candidates


def _binary_entries(tools: list[Path], *, windows: bool) -> list[tuple[str, str]]:
    entries = [(str(tool), "postgresql/bin") for tool in tools]
    if windows:
        # PostgreSQL's Windows distribution keeps the runtime DLL dependency
        # set beside pg_dump.exe. Embedding all of them avoids relying on a
        # PostgreSQL installation on the end user's computer.
        dlls = (
            path
            for path in tools[0].parent.iterdir()
            if path.is_file() and path.suffix.lower() == ".dll"
        )
        entries.extend((str(path), "postgresql/bin") for path in dlls)
    return entries


def postgresql_binaries() -> list[tuple[str, str]]:
    """Return PyInstaller entries for embedded PostgreSQL backup tools."""
    pg_dump = next(
        (
            path
            for path in _pg_dump_candidates()
            if (
                path.is_file()
                and _is_complete_windows_client(path)
                and _meets_minimum_client_major(path)
            )
        ),
        None,
    )
    if pg_dump is None:
        minimum_major = os.getenv("GENTGRAN_MIN_PG_DUMP_MAJOR", "").strip()
        requirement = f" version {minimum_major} or newer" if minimum_major else ""
        raise SystemExit(
            f"Cannot build GentGranBD: pg_dump{requirement} was not found. Install libpq/PostgreSQL "
            "client tools or set GENTGRAN_PG_DUMP to the executable path."
        )
    suffix = ".exe" if os.name == "nt" else ""
    tools = [pg_dump]
    for tool_name in ("pg_restore", "psql"):
        tool = pg_dump.with_name(f"{tool_name}{suffix}")
        if not tool.is_file():
            raise SystemExit(f"Cannot build GentGranBD: {tool_name} is missing beside {pg_dump}.")
        tools.append(tool)
    return _binary_entries(tools, windows=os.name == "nt")
