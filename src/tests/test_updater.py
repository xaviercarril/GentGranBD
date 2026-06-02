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
