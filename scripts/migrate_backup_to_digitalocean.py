#!/usr/bin/env python3
"""Pick a Gent Gran SQLite backup and migrate it to DigitalOcean PostgreSQL."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_SCRIPT = PROJECT_ROOT / "scripts" / "migrate_sqlite_to_postgres.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Select a Gent Gran SQLite .db backup and run the PostgreSQL migration. "
            "Set DATABASE_URL to your DigitalOcean connection string or pass --postgres-url."
        )
    )
    parser.add_argument(
        "sqlite_db",
        nargs="?",
        type=Path,
        help="SQLite .db backup to migrate. If omitted, an interactive selector is shown.",
    )
    parser.add_argument(
        "--postgres-url",
        "--target",
        default=os.getenv("DATABASE_URL") or os.getenv("GENTGRAN_DATABASE_URL"),
        help="DigitalOcean PostgreSQL URL. Defaults to DATABASE_URL/GENTGRAN_DATABASE_URL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show source counts without modifying PostgreSQL.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not truncate target tables before copying. Usually not recommended.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip the destructive confirmation prompt.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Only list discovered .db backups.",
    )
    return parser.parse_args()


def candidate_dirs() -> list[Path]:
    dirs = [
        PROJECT_ROOT / "src",
        PROJECT_ROOT,
        Path.cwd(),
        Path.home() / "Desktop",
        Path.home() / "Downloads",
        Path.home() / "Library" / "Application Support" / "GentGranBD" / "backups",
    ]
    seen: set[Path] = set()
    unique_dirs: list[Path] = []
    for directory in dirs:
        try:
            resolved = directory.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        unique_dirs.append(resolved)
    return unique_dirs


def discover_backups() -> list[Path]:
    candidates: list[Path] = []
    seen: set[Path] = set()
    for directory in candidate_dirs():
        for path in sorted(directory.glob("*.db")):
            if not path.is_file() or not is_sqlite_database(path):
                continue
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(resolved)
    return candidates


def is_sqlite_database(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


def print_backups(candidates: list[Path]) -> None:
    if not candidates:
        print("No .db backups found in the usual locations.")
        return
    print("Backups encontrados:")
    for index, path in enumerate(candidates, start=1):
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  {index}. {path} ({size_mb:.1f} MB)")


def select_backup(args: argparse.Namespace) -> Path:
    if args.sqlite_db:
        return args.sqlite_db.expanduser()

    candidates = discover_backups()
    print_backups(candidates)
    if args.list:
        raise SystemExit(0)

    choice = input("\nNumero de backup o ruta manual: ").strip()
    if not choice:
        raise SystemExit("No se selecciono ningun backup.")

    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(candidates):
            return candidates[index - 1]
        raise SystemExit(f"Numero fuera de rango: {choice}")

    return Path(choice).expanduser()


def confirm_destructive(source: Path, postgres_url: str, args: argparse.Namespace) -> None:
    if args.dry_run or args.keep_existing or args.yes:
        return

    safe_url = postgres_url
    if "@" in safe_url:
        prefix, suffix = safe_url.split("@", 1)
        if ":" in prefix:
            safe_url = prefix.split(":", 1)[0] + ":***@" + suffix

    print("\nAVISO: se vaciaran las tablas del PostgreSQL destino antes de copiar.")
    print(f"Origen SQLite: {source}")
    print(f"Destino PostgreSQL: {safe_url}")
    answer = input("Escribe MIGRAR para continuar: ").strip()
    if answer != "MIGRAR":
        raise SystemExit("Migracion cancelada.")


def run_migration(source: Path, args: argparse.Namespace) -> int:
    if not source.exists():
        print(f"SQLite backup not found: {source}", file=sys.stderr)
        return 2
    if not is_sqlite_database(source):
        print(f"Selected file is not a SQLite database: {source}", file=sys.stderr)
        return 2

    command = [
        sys.executable,
        str(MIGRATION_SCRIPT),
        str(source),
    ]

    if args.postgres_url:
        command.extend(["--postgres-url", args.postgres_url])
    elif not args.dry_run:
        print(
            "Falta DATABASE_URL/GENTGRAN_DATABASE_URL o --postgres-url para migrar.",
            file=sys.stderr,
        )
        return 2

    if args.dry_run:
        command.append("--dry-run")
    elif not args.keep_existing:
        command.append("--truncate")

    return subprocess.call(command, cwd=PROJECT_ROOT)


def main() -> int:
    args = parse_args()
    source = select_backup(args)
    if not args.list:
        confirm_destructive(source, args.postgres_url or "", args)
    return run_migration(source, args)


if __name__ == "__main__":
    raise SystemExit(main())
