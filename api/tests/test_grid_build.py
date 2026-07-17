from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.grid.build import build_hex_scores
from desertcharge.grid.supply import weighted_dc_fast_ports_within
from desertcharge.h3grid import point_to_cell
from desertcharge.ingest.census import TractRecord
from desertcharge.ingest.census_load import load_tracts
from desertcharge.models import Charger, HexScore


async def _add_charger(
    session: AsyncSession, lat: float, lng: float, *, dc: bool, ports: int
) -> None:
    session.add(
        Charger(
            source="test",
            source_id=f"{lat},{lng}",
            name="t",
            geom=WKTElement(f"POINT({lng} {lat})", srid=4326),
            power_kw=150.0 if dc else 7.0,
            num_ports=ports,
            is_dc_fast=dc,
        )
    )
    await session.flush()


async def test_weighted_ports_counts_only_dc_fast_within_radius(
    session: AsyncSession,
) -> None:
    await _add_charger(session, 35.0, -116.0, dc=True, ports=4)  # on the point
    await _add_charger(session, 35.0, -116.0, dc=False, ports=9)  # slow, ignored
    await _add_charger(session, 36.0, -116.0, dc=True, ports=5)  # ~111 km away, outside
    weighted = await weighted_dc_fast_ports_within(session, 35.0, -116.0, 16093.0)
    assert weighted == 4.0


async def test_build_hex_scores_scores_a_desert_and_a_served_hex(
    session: AsyncSession,
) -> None:
    # Two high-demand hexes (one served, one not) plus a low-demand hex to give the
    # min-max population normalization a real range.
    served = TractRecord("s1", "NV", 5000, 36.100, -115.100)
    desert = TractRecord("d1", "NV", 5000, 37.500, -117.500)
    sparse = TractRecord("p1", "AZ", 100, 34.000, -111.000)
    await load_tracts(session, [served, desert, sparse])
    await _add_charger(session, 36.100, -115.100, dc=True, ports=6)  # at the served hex

    count = await build_hex_scores(session)
    assert count == 3

    served_cell = point_to_cell(36.100, -115.100)
    desert_cell = point_to_cell(37.500, -117.500)
    rows = (await session.execute(select(HexScore.h3_index, HexScore.desert_score))).all()
    scores = {h3: score for h3, score in rows}
    assert scores[served_cell] < scores[desert_cell]
    assert scores[desert_cell] > 50  # high demand, far from any charger
