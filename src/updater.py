from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import ssl
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


def _ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


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
        with urlopen(request, timeout=HTTP_TIMEOUT, context=_ssl_context()) as response:
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
        with urlopen(request, timeout=HTTP_TIMEOUT, context=_ssl_context()) as response, destination.open("wb") as fh:
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


def _update_log(message: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [updater.py] {message}"
    print(line, flush=True)
    try:
        log_path = _user_data_dir() / "updates" / "updater.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


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
    _update_log(f"Descarregant actualització: {update.asset.name}")
    download_file(update.asset.download_url, installer_path)
    _update_log(f"Actualització descarregada: {installer_path}")
    _update_log(f"Descarregant SHA256: {update.sha256_asset.name}")
    download_file(update.sha256_asset.download_url, sha_path)
    _update_log(f"SHA256 descarregat: {sha_path}")
    verify_sha256(installer_path, parse_sha256_file(sha_path))
    _update_log("SHA256 verificat correctament")
    return installer_path, sha_path


def install_update(update: UpdateInfo, app_path: Path | None = None) -> InstallResult:
    _update_log(f"Iniciant instal·lació de {update.latest_version}")
    installer_path, _ = _download_update_assets(update)
    _update_log("Creant còpia de seguretat de la base de dades")
    backup_path = auto_backup_sqlite()
    if sys.platform == "win32":
        _update_log("Llançant helper de Windows")
        _launch_windows_helper(installer_path)
        return InstallResult(True, "S'ha preparat l'instal·lador de Windows.", backup_path)
    if sys.platform == "darwin":
        _update_log("Llançant helper de macOS")
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

    updates_dir = _user_data_dir() / "updates"
    helper_path = updates_dir / "install_macos_update.sh"
    helper_log = updates_dir / "install_macos_update.log"
    current_pid = os.getpid()
    helper_path.write_text(
        f"""#!/bin/sh
set -eu
LOG={_sh_quote(str(helper_log))}
APP_PID={current_pid}
TARGET_APP={_sh_quote(str(target_app))}
NEW_APP={_sh_quote(str(new_app))}
PARENT_DIR=$(dirname "$TARGET_APP")
APP_NAME=$(basename "$TARGET_APP")

log() {{
  printf '%s [install_macos_update.sh] %s\\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "$LOG"
}}

log "Helper iniciat. APP_PID=$APP_PID TARGET_APP=$TARGET_APP NEW_APP=$NEW_APP"
while kill -0 "$APP_PID" >/dev/null 2>&1; do
  log "Esperant que es tanqui GentGranBD..."
  sleep 1
done
log "GentGranBD tancat. Instal·lant actualització."
rm -rf "$TARGET_APP.old"
if [ -d "$TARGET_APP" ]; then
  log "Movent app actual a $TARGET_APP.old"
  mv "$TARGET_APP" "$TARGET_APP.old"
fi
log "Copiant nova app"
cp -R "$NEW_APP" "$PARENT_DIR/$APP_NAME"
log "Eliminant quarantine"
xattr -dr com.apple.quarantine "$PARENT_DIR/$APP_NAME" >/dev/null 2>&1 || true

BUNDLE_EXEC=$(/usr/libexec/PlistBuddy -c 'Print CFBundleExecutable' "$PARENT_DIR/$APP_NAME/Contents/Info.plist" 2>/dev/null || printf 'GentGranBD')
APP_EXEC="$PARENT_DIR/$APP_NAME/Contents/MacOS/$BUNDLE_EXEC"
log "Executable detectat: $APP_EXEC"
ls -la "$PARENT_DIR/$APP_NAME/Contents/MacOS" >> "$LOG" 2>&1 || true
chmod +x "$APP_EXEC" >/dev/null 2>&1 || true

if [ -f "$APP_EXEC" ]; then
  log "Executable preparat"
else
  log "No existeix l'executable esperat: $APP_EXEC"
fi

log "Obrint nova app amb open -n"
if open -n "$PARENT_DIR/$APP_NAME" >> "$LOG" 2>&1; then
  log "Nova app oberta correctament amb open -n"
  log "Eliminant còpia antiga"
  rm -rf "$TARGET_APP.old"
  log "Actualització completada"
  exit 0
fi

if [ -f "$APP_EXEC" ]; then
  log "open -n ha fallat. Intentant arrencar l'executable directament amb nohup."
  nohup "$APP_EXEC" >> "$LOG" 2>&1 &
  NEW_PID=$!
  sleep 2
  if kill -0 "$NEW_PID" >/dev/null 2>&1; then
    log "Executable arrencat directament amb PID=$NEW_PID"
    log "Eliminant còpia antiga"
    rm -rf "$TARGET_APP.old"
    log "Actualització completada"
    exit 0
  fi
  log "L'executable directe també ha sortit immediatament."
fi

log "No s'ha pogut obrir la nova app. Restaurant la versió anterior."
rm -rf "$PARENT_DIR/$APP_NAME"
if [ -d "$TARGET_APP.old" ]; then
  mv "$TARGET_APP.old" "$PARENT_DIR/$APP_NAME"
fi
log "Actualització revertida perquè la nova app no s'ha pogut obrir"
exit 1
""",
        encoding="utf-8",
    )
    helper_path.chmod(0o755)
    _update_log(f"Helper macOS escrit a {helper_path}")
    _update_log(f"Log del helper macOS: {helper_log}")
    subprocess.Popen(["/bin/sh", str(helper_path)], start_new_session=True)


def _sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
