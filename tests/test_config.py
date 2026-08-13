import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_parse_comma_separated_cors_origins() -> None:
    settings = Settings(
        jwt_secret_key="test-secret",
        cors_origins="http://localhost:3000, https://example.test",
        cors_allow_methods="GET,post",
        cors_allow_headers="Authorization, Content-Type",
    )

    assert settings.cors_origin_list == ["http://localhost:3000", "https://example.test"]
    assert settings.cors_method_list == ["GET", "POST"]
    assert settings.cors_header_list == ["Authorization", "Content-Type"]


def test_settings_reject_cors_wildcard_when_credentials_are_enabled() -> None:
    with pytest.raises(ValidationError, match="CORS origins must be explicit"):
        Settings(jwt_secret_key="test-secret", cors_origins="*")


def test_settings_use_psycopg_driver_for_plain_postgresql_urls() -> None:
    settings = Settings(
        jwt_secret_key="test-secret",
        database_url="postgresql://user:password@localhost:5432/elibrary",
        test_database_url="postgresql://user:password@localhost:5432/elibrary_test",
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.test_database_url.startswith("postgresql+psycopg://")
