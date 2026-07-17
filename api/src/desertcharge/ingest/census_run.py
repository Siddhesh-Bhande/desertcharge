"""Orchestrate the census ingest across the region's states."""

from __future__ import annotations

import asyncio
import logging

import httpx

from desertcharge.db import create_engine_from_settings, create_session_factory
from desertcharge.ingest.census import TractRecord, fetch_tracts
from desertcharge.ingest.census_load import load_tracts
from desertcharge.region import REGION_STATES

logger = logging.getLogger(__name__)


async def ingest_census() -> int:
    """Fetch tracts for every region state and load them. Returns rows loaded."""
    records: list[TractRecord] = []
    async with httpx.AsyncClient() as client:
        for state, fips in REGION_STATES.items():
            state_records = await fetch_tracts(fips, state, client)
            logger.info("Fetched %s tracts=%d", state, len(state_records))
            records.extend(state_records)

    engine = create_engine_from_settings()
    factory = create_session_factory(engine)
    async with factory() as session:
        count = await load_tracts(session, records)
    await engine.dispose()
    return count


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    count = asyncio.run(ingest_census())
    logger.info("Loaded %d tracts.", count)


if __name__ == "__main__":
    main()
