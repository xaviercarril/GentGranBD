#!/usr/bin/env python3
"""Create the Gent Gran database schema for the configured DATABASE_URL."""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import DATABASE_URL, engine
from models import Base


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print(f"Schema ready on {engine.url.get_backend_name()}: {DATABASE_URL}")
    print(f"Tables: {len(Base.metadata.tables)}")


if __name__ == "__main__":
    main()
