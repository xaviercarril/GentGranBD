#!/usr/bin/env python3
"""Import socios from CSV/Excel from a separate process.

This keeps the Qt UI process isolated from pandas/database work.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from importador.importar_socios_excel import importar_socios_desde_excel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Gent Gran socios.")
    parser.add_argument("path", help="CSV/XLS/XLSX file to import.")
    return parser.parse_args()


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> int:
    args = parse_args()
    warnings: list[str] = []
    warning_count = 0
    error_count = 0

    def on_progress(done: int, total: int):
        if done == 1 or done == total or done % 250 == 0:
            emit({"type": "progress", "done": done, "total": total})

    def on_warning(idx: int, msg: str):
        nonlocal warning_count
        warning_count += 1
        if len(warnings) < 200:
            warnings.append(f"Fila {idx + 1}: {msg}")

    def on_error(idx: int, msg: str):
        nonlocal error_count
        error_count += 1

    try:
        created, failed_rows = importar_socios_desde_excel(
            args.path,
            on_progress=on_progress,
            on_warning=on_warning,
            on_error=on_error,
        )
    except Exception as exc:
        emit({"type": "error", "message": str(exc)})
        return 1

    emit(
        {
            "type": "result",
            "created": created,
            "failed": len(failed_rows),
            "warning_count": warning_count,
            "error_count": error_count,
            "warnings": warnings,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
