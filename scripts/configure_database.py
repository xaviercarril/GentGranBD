#!/usr/bin/env python3
"""Persist the production database URL for packaged GentGranBD builds."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path
from urllib.parse import quote


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import _user_data_dir


DEFAULT_HOST = "gentgranbd-do-user-39510891-0.h.db.ondigitalocean.com"
DEFAULT_PORT = 25060
DEFAULT_DATABASE = "gentgran"
DEFAULT_USER = "doadmin"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write GentGranBD database.env for the packaged app."
    )
    parser.add_argument("--url", help="Full PostgreSQL URL to store.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--password", help="Database password. If omitted, prompts securely.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Custom output path. Defaults to the app user data database.env.",
    )
    return parser.parse_args()


def build_url(args: argparse.Namespace) -> str:
    if args.url:
        return args.url
    password = args.password
    if password is None:
        password = getpass.getpass("Contrasenya BD DigitalOcean: ")
    return (
        "postgresql://"
        f"{quote(args.user)}:{quote(password)}@"
        f"{args.host}:{args.port}/{args.database}?sslmode=require"
    )


def main() -> int:
    args = parse_args()
    output = args.output or (_user_data_dir() / "database.env")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "GENTGRAN_DATABASE_URL='{}'\n".format(build_url(args).replace("'", "'\"'\"'")),
        encoding="utf-8",
    )
    try:
        output.chmod(0o600)
    except OSError:
        pass
    print(f"Configuracio guardada a: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
