"""Rank the highest-need hexes as suggested charger sites."""

from __future__ import annotations

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.h3grid import cell_centroid
from desertcharge.models import BestSite, HexScore

METERS_PER_MILE = 1609.34


async def rank_best_sites(session: AsyncSession, limit: int = 10) -> int:
    """Replace best_sites with the top-scoring underserved hexes. Returns row count."""
    stmt = (
        select(HexScore)
        .order_by(HexScore.desert_score.desc(), HexScore.population.desc())
        .limit(limit)
    )
    hexes = (await session.execute(stmt)).scalars().all()

    await session.execute(delete(BestSite))
    for rank, hex_row in enumerate(hexes, start=1):
        gap_miles = (
            hex_row.nearest_dc_fast_m / METERS_PER_MILE
            if hex_row.nearest_dc_fast_m is not None
            else 0.0
        )
        population = int(hex_row.population)
        lat, lng = cell_centroid(hex_row.h3_index)
        session.add(
            BestSite(
                h3_index=hex_row.h3_index,
                geom=WKTElement(f"POINT({lng} {lat})", srid=4326),
                rank=rank,
                est_population_served=population,
                gap_miles_closed=gap_miles,
                reason=(
                    f"A charger here would serve about {population:,} people "
                    f"and close a {gap_miles:.0f} mile gap."
                ),
            )
        )
    await session.commit()
    return len(hexes)
