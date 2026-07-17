"""Build the scored hex grid from tracts and chargers."""

from __future__ import annotations

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.grid.demand import hex_polygon_wkt, hex_populations
from desertcharge.grid.supply import weighted_dc_fast_ports_within
from desertcharge.h3grid import cell_centroid
from desertcharge.ingest.census import TractRecord
from desertcharge.models import CensusTract, HexScore
from desertcharge.queries import nearest_dc_fast_distance_m
from desertcharge.scoring import score_hex

TEN_MILES_M = 16093.4
METERS_PER_MILE = 1609.34
NO_CHARGER_MILES = 9999.0


async def _load_tract_records(session: AsyncSession) -> list[TractRecord]:
    stmt = select(
        CensusTract.geoid,
        CensusTract.state,
        CensusTract.population,
        func.ST_Y(CensusTract.centroid),
        func.ST_X(CensusTract.centroid),
    )
    rows = await session.execute(stmt)
    return [
        TractRecord(geoid=geoid, state=state, population=pop, lat=lat, lng=lng)
        for geoid, state, pop, lat, lng in rows
    ]


async def build_hex_scores(session: AsyncSession) -> int:
    """Aggregate demand, measure supply per hex, score, and replace hex_scores."""
    tracts = await _load_tract_records(session)
    populations = hex_populations(tracts)
    if not populations:
        return 0

    pop_min = float(min(populations.values()))
    pop_max = float(max(populations.values()))

    await session.execute(delete(HexScore))
    for cell, population in populations.items():
        lat, lng = cell_centroid(cell)
        nearest_m = await nearest_dc_fast_distance_m(session, lat, lng)
        weighted = await weighted_dc_fast_ports_within(session, lat, lng, TEN_MILES_M)
        nearest_miles = nearest_m / METERS_PER_MILE if nearest_m is not None else NO_CHARGER_MILES
        result = score_hex(
            population=float(population),
            pop_min=pop_min,
            pop_max=pop_max,
            nearest_dc_fast_miles=nearest_miles,
            weighted_chargers_10mi=weighted,
        )
        session.add(
            HexScore(
                h3_index=cell,
                geom=WKTElement(hex_polygon_wkt(cell), srid=4326),
                centroid=WKTElement(f"POINT({lng} {lat})", srid=4326),
                population=float(population),
                nearest_dc_fast_m=nearest_m,
                weighted_chargers_10mi=weighted,
                desert_score=result.score,
            )
        )
    await session.commit()
    return len(populations)
