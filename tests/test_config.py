from app.core.config import Settings


def test_settings_parse_comma_separated_cors_origins() -> None:
    settings = Settings(cors_origins="http://localhost:3000, https://example.test")

    assert settings.cors_origin_list == ["http://localhost:3000", "https://example.test"]


def test_settings_use_psycopg_driver_for_plain_postgresql_urls() -> None:
    settings = Settings(
        database_url="postgresql://user:password@localhost:5432/elibrary",
        test_database_url="postgresql://user:password@localhost:5432/elibrary_test",
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.test_database_url.startswith("postgresql+psycopg://")
