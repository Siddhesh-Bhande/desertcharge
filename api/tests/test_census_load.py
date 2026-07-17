from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.ingest.census import TractRecord
from desertcharge.ingest.census_load import load_tracts
from desertcharge.models import CensusTract


async def test_load_tracts_replaces_table(session: AsyncSession) -> None:
    first = [TractRecord("32003005322", "NV", 1580, 36.1, -115.1)]
    count = await load_tracts(session, first)
    assert count == 1

    total_pop = await session.scalar(select(func.sum(CensusTract.population)))
    assert total_pop == 1580

    second = [
        TractRecord("32003005115", "NV", 2914, 36.2, -115.2),
        TractRecord("04013010101", "AZ", 5000, 33.4, -112.0),
    ]
    count = await load_tracts(session, second)
    assert count == 2
    total_rows = await session.scalar(select(func.count()).select_from(CensusTract))
    assert total_rows == 2
