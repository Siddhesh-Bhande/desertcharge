"""Orchestrate the grid build: hex scores, best sites, and grid.json export."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from desertcharge.db import create_engine_from_settings, create_session_factory
from desertcharge.grid.best_sites import rank_best_sites
from desertcharge.grid.build import build_hex_scores
from desertcharge.grid.export import export_grid_json

logger = logging.getLogger(__name__)

DEFAULT_GRID_PATH = Path("grid.json")


async def build_grid(grid_path: Path = DEFAULT_GRID_PATH) -> tuple[int, int, int]:
    """Build hex scores, rank best sites, and export the grid. Returns their counts."""
    engine = create_engine_from_settings()
    factory = create_session_factory(engine)
    async with factory() as session:
        hexes = await build_hex_scores(session)
        sites = await rank_best_sites(session)
        exported = await export_grid_json(session, grid_path)
    await engine.dispose()
    return hexes, sites, exported


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    hexes, sites, exported = asyncio.run(build_grid())
    logger.info("Built hex_scores=%d best_sites=%d grid.json=%d", hexes, sites, exported)


if __name__ == "__main__":
    main()
