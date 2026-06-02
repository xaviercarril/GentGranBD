from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from version import APP_VERSION


REPO = os.getenv("GENTGRAN_RELEASE_REPO", "xaviercarril/GentGranBD")
GITHUB_API = "https://api.github.com"
HTTP_TIMEOUT = 20


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    tag: str
    release_url: str
    body: str
    asset: ReleaseAsset
    sha256_asset: ReleaseAsset


@dataclass(frozen=True)
class InstallResult:
    launched: bool
    message: str
    backup_path: Path | None = None


def parse_version(value: str) -> tuple[int, ...]:
    raw = value.strip()
    if raw.startswith(("v", "V")):
        raw = raw[1:]
    main = raw.split("-", 1)[0].split("+", 1)[0]
    parts = main.split(".")
    if not parts or any(not p.isdigit() for p in parts):
        raise ValueError(f"Versió no vàlida: {value}")
    return tuple(int(p) for p in parts)


def is_newer_version(candidate: str, current: str = APP_VERSION) -> bool:
    candidate_parts = parse_version(candidate)
    current_parts = parse_version(current)
    width = max(len(candidate_parts), len(current_parts))
    return candidate_parts + (0,) * (width - len(candidate_parts)) > current_parts + (0,) * (width - len(current_parts))


def _request_json(url: str, token: str | None = None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "GentGranBD-updater",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise UpdateError(f"GitHub ha retornat HTTP {exc.code}") from exc
    except URLError as exc:
        raise UpdateError(f"No s'ha pogut connectar amb GitHub: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise UpdateError("La resposta de GitHub no és JSON vàlid") from exc


def _platform_asset_prefix() -> str:
    if sys.platform == "win32":
        return "GentGranBD-Setup-Windows-"
    if sys.platform == "darwin":
        return "GentGranBD-macOS-"
    raise UpdateError("Les actualitzacions automàtiques només estan disponibles a Windows i macOS.")


def select_platform_asset(assets: list[dict], system: str | None = None) -> ReleaseAsset:
    system_name = system or platform.system()
    if system_name == "Windows":
        prefix = "GentGranBD-Setup-Windows-"
        suffix = ".exe"
    elif system_name == "Darwin":
        prefix = "GentGranBD-macOS-"
        suffix = ".zip"
    else:
        raise UpdateError("Plataforma no suportada per l'actualitzador.")

    for asset in assets:
        name = str(asset.get("name", ""))
        url = str(asset.get("browser_download_url", ""))
        if name.startswith(prefix) and name.endswith(suffix) and url:
            return ReleaseAsset(name=name, download_url=url)
    raise UpdateError(f"No s'ha trobat cap asset d'actualització per a {system_name}.")


def select_sha256_asset(assets: list[dict], asset_name: str) -> ReleaseAsset:
    expected = f"{asset_name}.sha256"
    for asset in assets:
        name = str(asset.get("name", ""))
        url = str(asset.get("browser_download_url", ""))
        if name == expected and url:
            return ReleaseAsset(name=name, download_url=url)
    raise UpdateError(f"No s'ha trobat el hash SHA256 per a {asset_name}.")


def check_for_update(current_version: str = APP_VERSION, token: str | None = None) -> UpdateInfo | None:
    github_token = token if token is not None else os.getenv("GENTGRAN_GITHUB_TOKEN")
    release = _request_json(f"{GITHUB_API}/repos/{REPO}/releases/latest", github_token)
    if release.get("prerelease"):
        return None

    tag = str(release.get("tag_name", "")).strip()
    if not tag:
        raise UpdateError("El release no té tag.")
    if not is_newer_version(tag, current_version):
        return None

    assets = list(release.get("assets") or [])
    asset = select_platform_asset(assets)
    sha256_asset = select_sha256_asset(assets, asset.name)

    return UpdateInfo(
        current_version=current_version,
        latest_version=tag.lstrip("vV"),
        tag=tag,
        release_url=str(release.get("html_url") or ""),
        body=str(release.get("body") or ""),
        asset=asset,
        sha256_asset=sha256_asset,
    )


def download_file(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "GentGranBD-updater"})
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT) as response, destination.open("wb") as fh:
            shutil.copyfileobj(response, fh)
    except HTTPError as exc:
        raise UpdateError(f"No s'ha pogut descarregar l'actualització: HTTP {exc.code}") from exc
    except URLError as exc:
        raise UpdateError(f"No s'ha pogut descarregar l'actualització: {exc.reason}") from exc
    return destination


def parse_sha256_file(path: Path) -> str:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise UpdateError("El fitxer SHA256 és buit.")
    digest = content.split()[0].strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise UpdateError("El fitxer SHA256 no conté un hash vàlid.")
    return digest


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_sha256(path: Path, expected_digest: str) -> None:
    actual = file_sha256(path)
    if actual.lower() != expected_digest.lower():
        raise UpdateError("La verificació SHA256 ha fallat. No s'executarà l'actualització.")


def _user_data_dir() -> Path:
    try:
        from database import _user_data_dir as db_user_data_dir

        return Path(db_user_data_dir())
    except Exception:
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        elif os.name == "nt":
            base = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
        else:
            base = Path.home() / ".local" / "share"
        target = base / "GentGranBD"
        target.mkdir(parents=True, exist_ok=True)
        return target


def auto_backup_sqlite() -> Path | None:
    from database import engine

    if engine.url.get_backend_name() != "sqlite":
        return None
    db_location = engine.url.database
    if not db_location:
        return None
    db_path = Path(db_location)
    if not db_path.exists():
        return None

    backup_dir = _user_data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"{db_path.stem}_pre_update_{timestamp}{db_path.suffix or '.db'}"
    shutil.copy2(db_path, target)
    return target


def _download_update_assets(update: UpdateInfo) -> tuple[Path, Path]:
    updates_dir = _user_data_dir() / "updates" / update.tag
    installer_path = updates_dir / update.asset.name
    sha_path = updates_dir / update.sha256_asset.name
    download_file(update.asset.download_url, installer_path)
    download_file(update.sha256_asset.download_url, sha_path)
    verify_sha256(installer_path, parse_sha256_file(sha_path))
    return installer_path, sha_path


def install_update(update: UpdateInfo, app_path: Path | None = None) -> InstallResult:
    installer_path, _ = _download_update_assets(update)
    backup_path = auto_backup_sqlite()
    if sys.platform == "win32":
        _launch_windows_helper(installer_path)
        return InstallResult(True, "S'ha preparat l'instal·lador de Windows.", backup_path)
    if sys.platform == "darwin":
        _launch_macos_helper(installer_path, app_path=app_path)
        return InstallResult(True, "S'ha iniciat l'actualitzador de macOS.", backup_path)
    raise UpdateError("Plataforma no suportada per instal·lar automàticament.")


def _launch_windows_helper(installer_path: Path) -> None:
    if os.name != "nt":
        raise UpdateError("L'instal·lador de Windows només es pot executar a Windows.")
    helper_path = _user_data_dir() / "updates" / "install_windows_update.cmd"
    helper_path.write_text(
        f"""@echo off
setlocal
set PID={os.getpid()}
set INSTALLER={installer_path}
:wait
tasklist /FI "PID eq %PID%" | find "%PID%" > nul
if not errorlevel 1 (
  timeout /t 1 /nobreak > nul
  goto wait
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%INSTALLER%' -ArgumentList '/S /LAUNCH' -Verb RunAs"
endlocal
""",
        encoding="utf-8",
    )
    subprocess.Popen(["cmd.exe", "/c", str(helper_path)], close_fds=True)


def _current_macos_app_path() -> Path:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        for parent in [executable, *executable.parents]:
            if parent.suffix == ".app":
                return parent
    raise UpdateError("No s'ha pogut determinar la ubicació de GentGranBD.app.")


def _launch_macos_helper(zip_path: Path, app_path: Path | None = None) -> None:
    target_app = app_path or _current_macos_app_path()
    if target_app.suffix != ".app":
        raise UpdateError("La ubicació actual no sembla una aplicació .app.")

    extract_dir = Path(tempfile.mkdtemp(prefix="gentgran-update-"))
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)

    candidates = list(extract_dir.glob("*.app"))
    if not candidates:
        candidates = list(extract_dir.glob("**/*.app"))
    if not candidates:
        raise UpdateError("El paquet macOS no conté cap .app.")
    new_app = candidates[0]

    helper_path = _user_data_dir() / "updates" / "install_macos_update.sh"
    helper_path.write_text(
        f"""#!/bin/sh
set -eu
TARGET_APP={_sh_quote(str(target_app))}
NEW_APP={_sh_quote(str(new_app))}
PARENT_DIR=$(dirname "$TARGET_APP")
APP_NAME=$(basename "$TARGET_APP")
for i in $(seq 1 60); do
  if ! pgrep -f "$TARGET_APP/Contents/MacOS" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
rm -rf "$TARGET_APP.old"
if [ -d "$TARGET_APP" ]; then
  mv "$TARGET_APP" "$TARGET_APP.old"
fi
cp -R "$NEW_APP" "$PARENT_DIR/$APP_NAME"
xattr -dr com.apple.quarantine "$PARENT_DIR/$APP_NAME" >/dev/null 2>&1 || true
open "$PARENT_DIR/$APP_NAME"
rm -rf "$TARGET_APP.old"
""",
        encoding="utf-8",
    )
    helper_path.chmod(0o755)
    subprocess.Popen(["/bin/sh", str(helper_path)], start_new_session=True)


def _sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
