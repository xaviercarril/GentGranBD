#!/usr/bin/env python3
"""Migrate a Gent Gran SQLite database into PostgreSQL.

The script copies rows using the SQLAlchemy model metadata, preserving primary
keys and binary fields. It is intended for the PostgreSQL POC first; run it
against staging/production only after reviewing the summary output.

Examples:
    python scripts/migrate_sqlite_to_postgres.py src/gentgran.db --dry-run
    python scripts/migrate_sqlite_to_postgres.py /path/to/gentgran.db --truncate
    python scripts/migrate_sqlite_to_postgres.py --sqlite-path backup.db --postgres-url postgresql+psycopg://...
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, func, inspect, select, text

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models import Base, InscripcionSocio


DEFAULT_SQLITE_PATH = SRC_DIR / "gentgran.db"
DEFAULT_POSTGRES_URL = (
    "postgresql+psycopg://gentgran:gentgran_dev@localhost:5432/gentgran_poc"
)


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy Gent Gran data from SQLite to PostgreSQL."
    )
    parser.add_argument(
        "sqlite_db",
        nargs="?",
        type=Path,
        help=(
            "Path to any Gent Gran SQLite .db file. If omitted, uses "
            f"{DEFAULT_SQLITE_PATH} unless --sqlite-path is provided."
        ),
    )
    parser.add_argument(
        "--sqlite-path",
        "--source",
        type=Path,
        help="SQLite DB path. Overrides the positional sqlite_db argument.",
    )
    parser.add_argument(
        "--postgres-url",
        "--target",
        default=os.getenv("DATABASE_URL") or DEFAULT_POSTGRES_URL,
        help=(
            "Target PostgreSQL SQLAlchemy URL. Defaults to DATABASE_URL or "
            f"{DEFAULT_POSTGRES_URL}."
        ),
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete existing PostgreSQL rows before copying.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report source counts and duplicate checks.",
    )
    return parser.parse_args()


def resolve_sqlite_path(args: argparse.Namespace) -> Path:
    return (args.sqlite_path or args.sqlite_db or DEFAULT_SQLITE_PATH).expanduser()


def expected_table_names() -> set[str]:
    return {table.name for table in Base.metadata.sorted_tables}


def migratable_tables(actual_tables: set[str] | None = None):
    tables = list(Base.metadata.sorted_tables)
    if actual_tables is not None:
        tables = [table for table in tables if table.name in actual_tables]
    return tables


def validate_sqlite_schema(source_engine) -> list[str]:
    actual_tables = set(inspect(source_engine).get_table_names())
    optional_tables = {"usuarios"}
    missing = sorted((expected_table_names() - optional_tables) - actual_tables)
    if not missing:
        return []
    return [
        "The SQLite file does not look like a compatible Gent Gran database. "
        f"Missing tables: {', '.join(missing)}"
    ]


def table_count(conn, table) -> int:
    return conn.execute(select(func.count()).select_from(table)).scalar_one()


def fetch_rows(conn, table) -> list[dict[str, Any]]:
    result = conn.execute(select(table))
    return [dict(row._mapping) for row in result]


def truncate_target(conn) -> None:
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    if table_names:
        conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


def reset_postgres_sequences(conn) -> None:
    for table in Base.metadata.sorted_tables:
        id_column = table.columns.get("id")
        if id_column is None:
            continue
        conn.execute(
            text(
                "SELECT setval("
                "pg_get_serial_sequence(:table_name, 'id'), "
                f"COALESCE((SELECT MAX(id) FROM \"{table.name}\"), 1), "
                f"(SELECT MAX(id) IS NOT NULL FROM \"{table.name}\")"
                ")"
            ),
            {"table_name": table.name},
        )


def validate_sqlite_data(source_conn) -> list[str]:
    issues: list[str] = []
    duplicates = source_conn.execute(
        select(
            InscripcionSocio.socioID,
            InscripcionSocio.actividadID,
            func.count().label("count"),
        )
        .group_by(InscripcionSocio.socioID, InscripcionSocio.actividadID)
        .having(func.count() > 1)
    ).all()
    if duplicates:
        issues.append(
            "PostgreSQL requires unique inscripciones(socioID, actividadID); "
            f"found {len(duplicates)} duplicated pairs."
        )
    return issues


def main() -> int:
    args = parse_args()
    sqlite_path = resolve_sqlite_path(args)
    if not sqlite_path.exists():
        print(f"SQLite database not found: {sqlite_path}", file=sys.stderr)
        return 2

    source_engine = create_engine(sqlite_url(sqlite_path), future=True)
    source_table_names = set(inspect(source_engine).get_table_names())
    source_tables = migratable_tables(source_table_names)

    schema_issues = validate_sqlite_schema(source_engine)
    if schema_issues:
        print("Schema validation issues:", file=sys.stderr)
        for issue in schema_issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    with source_engine.connect() as source_conn:
        issues = validate_sqlite_data(source_conn)
        source_counts = {
            table.name: table_count(source_conn, table)
            for table in source_tables
        }

    print(f"Source SQLite: {sqlite_path.resolve()}")
    print("Source SQLite counts:")
    for table_name, count in source_counts.items():
        print(f"  {table_name}: {count}")

    if issues:
        print("\nValidation issues:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("\nDry run completed; no PostgreSQL changes were made.")
        return 0

    target_engine = create_engine(args.postgres_url, future=True)
    print(f"\nTarget PostgreSQL: {target_engine.url.render_as_string(hide_password=True)}")
    Base.metadata.create_all(bind=target_engine)

    with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
        if args.truncate:
            truncate_target(target_conn)

        for table in source_tables:
            rows = fetch_rows(source_conn, table)
            if rows:
                target_conn.execute(table.insert(), rows)
            print(f"Copied {len(rows)} rows into {table.name}")

        reset_postgres_sequences(target_conn)

    with target_engine.connect() as target_conn:
        target_counts = {
            table.name: table_count(target_conn, table)
            for table in Base.metadata.sorted_tables
        }

    mismatches = [
        (name, source_counts[name], target_counts[name])
        for name in source_counts
        if source_counts[name] != target_counts[name]
    ]
    if mismatches:
        print("\nCount mismatches:", file=sys.stderr)
        for name, source_count, target_count in mismatches:
            print(
                f"  - {name}: SQLite={source_count}, PostgreSQL={target_count}",
                file=sys.stderr,
            )
        return 1

    print("\nMigration completed. Target PostgreSQL counts match SQLite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
