from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "dist" / "GentGranBD.app"
EXECUTABLE = APP_PATH / "Contents" / "MacOS" / "GentGranBD"


def main() -> int:
    if not APP_PATH.exists():
        print(f"No existeix l'app empaquetada: {APP_PATH}", file=sys.stderr)
        print("Executa primer la tasca package:mac-app.", file=sys.stderr)
        return 1
    if not EXECUTABLE.exists():
        print(f"No existeix l'executable: {EXECUTABLE}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env.setdefault("QT_MAC_WANTS_LAYER", "1")
    return subprocess.call([str(EXECUTABLE)], cwd=str(ROOT), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
