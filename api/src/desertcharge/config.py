"""Application settings loaded from the environment."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_URL = "postgresql+asyncpg://desertcharge:desertcharge@localhost:5432/desertcharge"


class Settings(BaseSettings):
    """Backend configuration. Values come from the environment or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = DEFAULT_DATABASE_URL

    @property
    def sync_database_url(self) -> str:
        """The same database as a sync URL for Alembic (psycopg2 driver)."""
        return self.database_url.replace("+asyncpg", "+psycopg2")


def get_settings() -> Settings:
    """Return a fresh Settings instance."""
    return Settings()
