#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE="${1:-.env.staging}"
if [ ! -f "$ENV_FILE" ]; then
  echo "No existe $ENV_FILE"
  echo "Crea el archivo con GENTGRAN_DATABASE_URL o DATABASE_URL."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

PYTHON_BIN="${PYTHON_BIN:-venv/bin/python}"
exec "$PYTHON_BIN" src/ui/app.py
