#!/usr/bin/env python3
"""Check the configured database connection and print core table counts."""

import sys
from pathlib import Path

from sqlalchemy import text

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import engine


TABLES = [
    "socios",
    "personal",
    "curso_academico",
    "trimestres",
    "actividades",
    "clases",
    "inscripciones",
    "matricula_pagos",
]


def main() -> None:
    safe_url = engine.url.render_as_string(hide_password=True)
    print(f"Database: {engine.url.get_backend_name()} {safe_url}")
    with engine.connect() as conn:
        print(f"SELECT 1: {conn.execute(text('SELECT 1')).scalar_one()}")
        for table in TABLES:
            count = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
            print(f"{table}: {count}")


if __name__ == "__main__":
    main()
