"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables and an optional .env file."""

    app_env: str = "development"
    debug: bool = False

    database_url: str = "postgresql://postgres:password@localhost:5432/elibrary"
    test_database_url: str = "postgresql://postgres:password@localhost:5432/elibrary_test"

    jwt_secret_key: str
    jwt_access_token_expire_minutes: int = Field(default=30, gt=0)
    jwt_refresh_token_expire_days: int = Field(default=7, gt=0)

    ai_api_base_url: str = "https://ai-api.userfacet.com"
    ai_api_token: str = ""
    ai_api_timeout_seconds: float = Field(default=15.0, gt=0)
    ai_summary_max_source_chars: int = Field(default=12000, gt=0, le=50000)
    ai_summary_rate_limit: str = "10/hour"
    catalog_bulk_max_items: int = Field(default=50, ge=1, le=500)
    book_storage_root: str = "storage"
    max_book_file_size_mb: int = Field(default=100, gt=0, le=1024)

    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def use_installed_postgresql_driver(cls, value: object) -> object:
        """Use psycopg v3 when a standard PostgreSQL URL is supplied."""
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """Return normalized CORS origins from a comma-separated setting."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_book_file_size_bytes(self) -> int:
        """Return the configured upload limit in bytes."""
        return self.max_book_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return one immutable settings instance for the application process."""
    return Settings()
