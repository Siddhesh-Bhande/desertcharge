"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from desertcharge.api.routes import router
from desertcharge.config import get_settings
from desertcharge.db import create_engine_from_settings, create_session_factory


def create_app(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    """Build the API app. Pass a session factory in tests; else build from settings."""
    factory = session_factory or create_session_factory(create_engine_from_settings())
    app = FastAPI(title="DesertCharge API", version="0.1.0")
    app.state.session_factory = factory

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
