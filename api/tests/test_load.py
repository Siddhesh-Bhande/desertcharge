from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.ingest.load import load_chargers
from desertcharge.ingest.records import ChargerRecord
from desertcharge.models import Charger


def _record(sid: str, lat: float, lng: float, *, dc: bool) -> ChargerRecord:
    return ChargerRecord(
        source="openchargemap",
        source_id=sid,
        name=sid,
        lat=lat,
        lng=lng,
        power_kw=150.0 if dc else 7.0,
        connector_types=("CCS",),
        network="Electrify America",
        num_ports=2,
        is_dc_fast=dc,
    )


async def test_load_chargers_replaces_table(session: AsyncSession) -> None:
    first = [_record("OCM-1", 35.0, -116.0, dc=True)]
    count = await load_chargers(session, first)
    assert count == 1

    total = await session.scalar(select(func.count()).select_from(Charger))
    assert total == 1

    # A second load replaces, not appends.
    second = [
        _record("OCM-2", 35.1, -116.1, dc=True),
        _record("OCM-3", 35.2, -116.2, dc=False),
    ]
    count = await load_chargers(session, second)
    assert count == 2
    total = await session.scalar(select(func.count()).select_from(Charger))
    assert total == 2
