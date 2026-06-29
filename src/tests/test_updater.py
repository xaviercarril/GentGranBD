from pathlib import Path

import pytest

import updater


def test_parse_version_accepta_tag_v():
    assert updater.parse_version("v1.2.3") == (1, 2, 3)


def test_is_newer_version_compara_semver_basico():
    assert updater.is_newer_version("v1.2.4", "1.2.3") is True
    assert updater.is_newer_version("v1.2.3", "1.2.3") is False
    assert updater.is_newer_version("v1.2.3", "1.2.4") is False


def test_parse_version_rechaza_tags_invalidos():
    with pytest.raises(ValueError):
        updater.parse_version("release-final")


def test_select_platform_asset_windows():
    asset = updater.select_platform_asset(
        [
            {"name": "GentGranBD-macOS-v1.0.0.zip", "browser_download_url": "https://example.test/mac.zip"},
            {"name": "GentGranBD-Setup-Windows-v1.0.0.exe", "browser_download_url": "https://example.test/win.exe"},
        ],
        system="Windows",
    )

    assert asset.name == "GentGranBD-Setup-Windows-v1.0.0.exe"


def test_select_platform_asset_macos():
    asset = updater.select_platform_asset(
        [{"name": "GentGranBD-macOS-v1.0.0.zip", "browser_download_url": "https://example.test/mac.zip"}],
        system="Darwin",
    )

    assert asset.name == "GentGranBD-macOS-v1.0.0.zip"


def test_select_sha256_asset_exige_hash_correspondiente():
    asset = updater.select_sha256_asset(
        [
            {
                "name": "GentGranBD-Setup-Windows-v1.0.0.exe.sha256",
                "browser_download_url": "https://example.test/win.exe.sha256",
            }
        ],
        "GentGranBD-Setup-Windows-v1.0.0.exe",
    )

    assert asset.name.endswith(".sha256")


def test_verify_sha256_detecta_mismatch(tmp_path):
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"gentgran")

    updater.verify_sha256(payload, updater.file_sha256(payload))
    with pytest.raises(updater.UpdateError):
        updater.verify_sha256(payload, "0" * 64)


def test_parse_sha256_file_acepta_formato_sha256sum(tmp_path):
    sha_file = tmp_path / "asset.sha256"
    sha_file.write_text("a" * 64 + "  asset.exe\n", encoding="utf-8")

    assert updater.parse_sha256_file(sha_file) == "a" * 64


def test_check_for_update_no_exige_token(monkeypatch):
    monkeypatch.delenv("GENTGRAN_GITHUB_TOKEN", raising=False)
    captured = {"token": "not-called"}

    def fake_json(url, token=None):
        captured["token"] = token
        return {"tag_name": "v1.0.0", "prerelease": False}

    monkeypatch.setattr(updater, "_request_json", fake_json)

    assert updater.check_for_update(current_version="1.0.0") is None
    assert captured["token"] is None


def test_check_for_update_devuelve_none_si_no_es_mas_nueva(monkeypatch):
    def fake_json(url, token=None):
        return {"tag_name": "v1.0.0", "prerelease": False}

    monkeypatch.setattr(updater, "_request_json", fake_json)

    assert updater.check_for_update(current_version="1.0.0", token="token") is None


def test_check_for_update_resuelve_release_publico(monkeypatch):
    def fake_json(url, token=None):
        return {
            "tag_name": "v1.1.0",
            "prerelease": False,
            "body": "Notes",
            "html_url": "https://github.example/release",
            "assets": [
                {
                    "name": "GentGranBD-Setup-Windows-v1.1.0.exe",
                    "browser_download_url": "https://example.test/setup.exe",
                },
                {
                    "name": "GentGranBD-Setup-Windows-v1.1.0.exe.sha256",
                    "browser_download_url": "https://example.test/setup.exe.sha256",
                },
            ],
        }

    monkeypatch.setattr(updater, "_request_json", fake_json)
    monkeypatch.setattr(updater.platform, "system", lambda: "Windows")

    info = updater.check_for_update(current_version="1.0.0", token="token")

    assert info is not None
    assert info.latest_version == "1.1.0"
    assert info.asset.name == "GentGranBD-Setup-Windows-v1.1.0.exe"
    assert info.release_url == "https://github.example/release"


def test_check_for_update_falla_si_falta_hash(monkeypatch):
    def fake_json(url, token=None):
        return {
            "tag_name": "v1.1.0",
            "prerelease": False,
            "assets": [
                {
                    "name": "GentGranBD-Setup-Windows-v1.1.0.exe",
                    "browser_download_url": "https://example.test/setup.exe",
                }
            ]
        }

    monkeypatch.setattr(updater, "_request_json", fake_json)
    monkeypatch.setattr(updater.platform, "system", lambda: "Windows")

    with pytest.raises(updater.UpdateError):
        updater.check_for_update(current_version="1.0.0", token="token")


def test_launch_windows_helper_pasa_directorio_actual_al_instalador(monkeypatch, tmp_path):
    monkeypatch.setattr(updater.os, "name", "nt")
    monkeypatch.setattr(updater.os, "getpid", lambda: 1234)
    monkeypatch.setattr(updater, "_current_windows_install_dir", lambda: tmp_path / "App Dir")
    monkeypatch.setattr(updater, "_user_data_dir", lambda: tmp_path / "data")

    popen_calls = []

    def fake_popen(args, **kwargs):
        popen_calls.append((args, kwargs))

    monkeypatch.setattr(updater.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(updater.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    updater._launch_windows_helper(tmp_path / "downloads" / "GentGranBD-Setup.exe")

    helper = tmp_path / "data" / "updates" / "install_windows_update.cmd"
    content = helper.read_text(encoding="utf-8")
    assert 'set "INSTALL_DIR=' in content
    assert str(tmp_path / "App Dir") in content
    assert "'/LAUNCH /D=' + $env:INSTALL_DIR" in content
    assert "'/S /LAUNCH" not in content
    assert "-Wait -PassThru" in content
    assert 'del /f /q "%INSTALLER%"' in content
    assert 'del /f /q "%INSTALLER%.sha256"' in content
    assert "exit /b %ERRORLEVEL%" in content
    assert popen_calls == [
        (["cmd.exe", "/c", str(helper)], {"close_fds": True, "creationflags": 0x08000000})
    ]


def test_cleanup_old_update_downloads_conserva_tag_actual(monkeypatch, tmp_path):
    updates_dir = tmp_path / "updates"
    keep = updates_dir / "v1.2.0"
    old = updates_dir / "v1.1.0"
    keep.mkdir(parents=True)
    old.mkdir()
    (keep / "current.exe").write_text("current", encoding="utf-8")
    (old / "old.exe").write_text("old", encoding="utf-8")
    (updates_dir / "updater.log").write_text("log", encoding="utf-8")

    monkeypatch.setattr(updater, "_user_data_dir", lambda: tmp_path)

    updater._cleanup_old_update_downloads(keep_tag="v1.2.0")

    assert keep.exists()
    assert not old.exists()
    assert (updates_dir / "updater.log").exists()
