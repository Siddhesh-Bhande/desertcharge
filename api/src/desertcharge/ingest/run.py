"""Orchestrate the charger ingest: fetch each source, merge, and load."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.config import get_settings
from desertcharge.db import create_engine_from_settings, create_session_factory
from desertcharge.ingest.load import load_chargers
from desertcharge.ingest.merge import merge_chargers
from desertcharge.ingest.nrel import fetch_nrel
from desertcharge.ingest.openchargemap import fetch_openchargemap
from desertcharge.ingest.records import ChargerRecord
from desertcharge.region import REGION

logger = logging.getLogger(__name__)


async def _safe_fetch(name: str, coro: Awaitable[list[ChargerRecord]]) -> list[ChargerRecord]:
    """Await a fetch, returning an empty list (logged) if the source fails."""
    try:
        return await coro
    except httpx.HTTPError as exc:
        logger.warning("Source %s failed: %s", name, exc)
        return []


async def _fetch_all() -> list[ChargerRecord]:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        ocm = await _safe_fetch(
            "openchargemap",
            fetch_openchargemap(REGION, settings.openchargemap_api_key, client),
        )
        nrel = await _safe_fetch("nrel", fetch_nrel(REGION, settings.nrel_api_key, client))
    merged = merge_chargers(ocm, nrel)
    logger.info("Fetched OCM=%d NREL=%d merged=%d", len(ocm), len(nrel), len(merged))
    return merged


async def ingest_chargers(session: AsyncSession | None = None) -> int:
    """Fetch chargers from all sources, merge, and load. Returns rows loaded.

    Pass a session to load through it (used in tests); otherwise a new engine and
    session are created from settings.
    """
    merged = await _fetch_all()
    if session is not None:
        return await load_chargers(session, merged)

    engine = create_engine_from_settings()
    factory = create_session_factory(engine)
    async with factory() as owned_session:
        count = await load_chargers(owned_session, merged)
    await engine.dispose()
    return count


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    count = asyncio.run(ingest_chargers())
    logger.info("Loaded %d chargers.", count)


if __name__ == "__main__":
    main()
