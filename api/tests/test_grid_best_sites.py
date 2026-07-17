from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.grid.best_sites import rank_best_sites
from desertcharge.h3grid import point_to_cell
from desertcharge.models import BestSite, HexScore

CELL_A = point_to_cell(35.0, -116.0)
CELL_B = point_to_cell(36.0, -115.0)
CELL_C = point_to_cell(34.0, -117.0)


async def _add_hex(session: AsyncSession, cell: str, score: int, pop: float) -> None:
    session.add(
        HexScore(
            h3_index=cell,
            geom=WKTElement("POLYGON((0 0,0 1,1 1,1 0,0 0))", srid=4326),
            centroid=WKTElement("POINT(-116 35)", srid=4326),
            population=pop,
            nearest_dc_fast_m=50000.0,
            weighted_chargers_10mi=0.0,
            desert_score=score,
        )
    )
    await session.flush()


async def test_rank_best_sites_takes_top_scoring_hexes(session: AsyncSession) -> None:
    await _add_hex(session, CELL_A, 90, 12000)
    await _add_hex(session, CELL_B, 70, 8000)
    await _add_hex(session, CELL_C, 10, 3000)

    count = await rank_best_sites(session, limit=2)
    assert count == 2

    sites = (await session.execute(select(BestSite).order_by(BestSite.rank))).scalars().all()
    assert [s.h3_index for s in sites] == [CELL_A, CELL_B]
    assert sites[0].rank == 1
    assert sites[0].est_population_served == 12000
