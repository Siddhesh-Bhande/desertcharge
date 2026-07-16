"""Load charger records into the PostGIS chargers table (full replace)."""

from __future__ import annotations

from collections.abc import Sequence

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.ingest.records import ChargerRecord
from desertcharge.models import Charger


def _to_model(record: ChargerRecord) -> Charger:
    return Charger(
        source=record.source,
        source_id=record.source_id,
        name=record.name,
        geom=WKTElement(f"POINT({record.lng} {record.lat})", srid=4326),
        power_kw=record.power_kw,
        connector_types=list(record.connector_types),
        network=record.network,
        num_ports=record.num_ports,
        is_dc_fast=record.is_dc_fast,
    )


async def load_chargers(session: AsyncSession, records: Sequence[ChargerRecord]) -> int:
    """Replace the chargers table with the given records. Returns the row count."""
    await session.execute(delete(Charger))
    session.add_all([_to_model(record) for record in records])
    await session.commit()
    return len(records)
