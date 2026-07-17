"""Application settings loaded from the environment."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_URL = "postgresql+asyncpg://desertcharge:desertcharge@localhost:5432/desertcharge"

# The .env lives at the repository root, three levels above this module.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Backend configuration. Values come from the environment or the root .env file."""

    model_config = SettingsConfigDict(env_file=_ROOT_ENV, extra="ignore")

    database_url: str = DEFAULT_DATABASE_URL
    openchargemap_api_key: str = ""
    nrel_api_key: str = ""
    openrouteservice_api_key: str = ""
    allowed_origins: str = "http://localhost:5173"

    @property
    def sync_database_url(self) -> str:
        """The same database as a sync URL for Alembic (psycopg2 driver)."""
        return self.database_url.replace("+asyncpg", "+psycopg2")


def get_settings() -> Settings:
    """Return a fresh Settings instance."""
    return Settings()
