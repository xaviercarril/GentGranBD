"""Locate PostgreSQL client tools that must be embedded by PyInstaller."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _pg_dump_candidates() -> list[Path]:
    executable_name = "pg_dump.exe" if os.name == "nt" else "pg_dump"
    candidates: list[Path] = []

    configured = os.getenv("GENTGRAN_PG_DUMP", "").strip()
    if configured:
        candidates.append(Path(configured))

    discovered = shutil.which(executable_name)
    if discovered:
        candidates.append(Path(discovered))

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
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            root = os.getenv(variable)
            if not root:
                continue
            postgresql_root = Path(root) / "PostgreSQL"
            if postgresql_root.is_dir():
                candidates.extend(
                    sorted(
                        postgresql_root.glob("*/bin/pg_dump.exe"),
                        reverse=True,
                    )
                )
    return candidates


def _binary_entries(tools: list[Path], *, windows: bool) -> list[tuple[str, str]]:
    entries = [(str(tool), "postgresql/bin") for tool in tools]
    if windows:
        # PostgreSQL's Windows distribution keeps the runtime DLL dependency
        # set beside pg_dump.exe. Embedding all of them avoids relying on a
        # PostgreSQL installation on the end user's computer.
        entries.extend((str(path), "postgresql/bin") for path in tools[0].parent.glob("*.dll"))
    return entries


def postgresql_binaries() -> list[tuple[str, str]]:
    """Return PyInstaller entries for embedded PostgreSQL backup tools."""
    pg_dump = next((path for path in _pg_dump_candidates() if path.is_file()), None)
    if pg_dump is None:
        raise SystemExit(
            "Cannot build GentGranBD: pg_dump was not found. Install libpq/PostgreSQL "
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
