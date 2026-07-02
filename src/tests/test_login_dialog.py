from ui.login_dialog import (
    _builtin_connection_profiles,
    _initial_connection_url,
    _profile_connection_url,
    _profile_display_url,
    _profile_from_settings_item,
    _url_has_credentials,
    _url_without_credentials,
)


def test_url_without_credentials_hides_database_password():
    clean = _url_without_credentials(
        "postgresql+psycopg://doadmin:secret@example.com:25060/gentgran?sslmode=require"
    )

    assert clean == "postgresql+psycopg://example.com:25060/gentgran?sslmode=require"


def test_url_without_credentials_preserves_plain_postgres_url():
    clean = _url_without_credentials(
        "postgresql://example.com:25060/gentgran?sslmode=require"
    )

    assert clean == "postgresql://example.com:25060/gentgran?sslmode=require"


def test_configured_url_with_credentials_wins_over_saved_display_url():
    saved_url = "postgresql://example.com:25060/gentgran?sslmode=require"
    configured_url = (
        "postgresql+psycopg://doadmin:secret@example.com:25060/"
        "gentgran?sslmode=require"
    )

    assert _initial_connection_url(saved_url, configured_url) == configured_url
    assert _url_has_credentials(configured_url) is True
    assert _url_has_credentials(saved_url) is False


def test_builtin_connection_profiles_only_include_local():
    configured_url = (
        "postgresql+psycopg://doadmin:secret@example.ondigitalocean.com:25060/"
        "gentgran?sslmode=require"
    )

    profiles = _builtin_connection_profiles(configured_url)

    assert len(profiles) == 1
    assert profiles[0]["id"] == "local"
    assert profiles[0]["name"] == "Local"
    assert profiles[0]["url"].startswith("sqlite:///")
    assert profiles[0]["builtin"] is True


def test_connection_profile_builds_url_from_parameters():
    profile = {
        "name": "DigitalOcean VPC",
        "driver": "postgresql",
        "host": "private-do-db.example.internal",
        "port": "25060",
        "database": "gentgran",
        "db_username": "doadmin",
        "db_password": "secret",
        "sslmode": "require",
    }

    url = _profile_connection_url(profile)

    assert url == (
        "postgresql+psycopg://doadmin:secret@private-do-db.example.internal:"
        "25060/gentgran?sslmode=require"
    )
    assert _profile_display_url(profile) == (
        "postgresql+psycopg://private-do-db.example.internal:25060/"
        "gentgran?sslmode=require"
    )


def test_legacy_url_profile_is_converted_to_parameters():
    profile = _profile_from_settings_item(
        {
            "id": "legacy",
            "name": "Antic",
            "url": (
                "postgresql+psycopg://doadmin:secret@example.com:25060/"
                "gentgran?sslmode=require"
            ),
        }
    )

    assert profile["id"] == "legacy"
    assert profile["driver"] == "postgresql"
    assert profile["host"] == "example.com"
    assert profile["port"] == "25060"
    assert profile["database"] == "gentgran"
    assert profile["db_username"] == "doadmin"
    assert profile["db_password"] == "secret"
