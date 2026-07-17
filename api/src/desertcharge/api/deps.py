"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a database session from the app's session factory."""
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return the app's shared HTTP client for outbound calls."""
    client: httpx.AsyncClient = request.app.state.http_client
    return client
