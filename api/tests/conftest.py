"""Shared fixtures: a PostGIS test container migrated to head."""

from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

API_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def postgis_url() -> Iterator[str]:
    """Start a PostGIS container, run migrations, and yield the async URL."""
    with PostgresContainer("postgis/postgis:16-3.4", driver="asyncpg") as container:
        async_url: str = container.get_connection_url()
        env = {**os.environ, "DATABASE_URL": async_url}
        subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=API_DIR,
            check=True,
            env=env,
        )
        yield async_url


@pytest.fixture
async def session(postgis_url: str) -> AsyncIterator[AsyncSession]:
    """Yield a clean async session against the migrated test database."""
    engine = create_async_engine(postgis_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()
