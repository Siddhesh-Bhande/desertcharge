"""FastAPI application factory."""

from __future__ import annotations

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from desertcharge.api.geocode import USER_AGENT
from desertcharge.api.routes import router
from desertcharge.config import get_settings
from desertcharge.db import create_engine_from_settings, create_session_factory


def create_app(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> FastAPI:
    """Build the API app. Pass a session factory and client in tests."""
    factory = session_factory or create_session_factory(create_engine_from_settings())
    app = FastAPI(title="DesertCharge API", version="0.1.0")
    app.state.session_factory = factory
    app.state.http_client = http_client or httpx.AsyncClient(headers={"User-Agent": USER_AGENT})

    # Rate limit every endpoint; this covers the ones that call external services.
    limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])
    app.state.limiter = limiter
    # slowapi's handler is typed for RateLimitExceeded, narrower than Starlette expects.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    origins = [
        origin.strip() for origin in get_settings().allowed_origins.split(",") if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    return app


app = create_app()
