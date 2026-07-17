"""Load tract records into the PostGIS census_tracts table (full replace)."""

from __future__ import annotations

from collections.abc import Sequence

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.ingest.census import TractRecord
from desertcharge.models import CensusTract


def _to_model(record: TractRecord) -> CensusTract:
    return CensusTract(
        geoid=record.geoid,
        state=record.state,
        centroid=WKTElement(f"POINT({record.lng} {record.lat})", srid=4326),
        population=record.population,
    )


async def load_tracts(session: AsyncSession, records: Sequence[TractRecord]) -> int:
    """Replace the census_tracts table with the given records. Returns row count."""
    await session.execute(delete(CensusTract))
    session.add_all([_to_model(record) for record in records])
    await session.commit()
    return len(records)
