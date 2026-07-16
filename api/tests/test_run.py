import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.ingest import run as run_module
from desertcharge.ingest.records import ChargerRecord
from desertcharge.models import Charger


def _record(source: str, sid: str, lat: float) -> ChargerRecord:
    return ChargerRecord(
        source=source,
        source_id=sid,
        name=sid,
        lat=lat,
        lng=-116.0,
        power_kw=150.0,
        connector_types=("CCS",),
        network="net",
        num_ports=2,
        is_dc_fast=True,
    )


async def test_ingest_is_resilient_to_a_failing_source(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def ok(*args: object, **kwargs: object) -> list[ChargerRecord]:
        return [_record("openchargemap", "OCM-1", 35.0)]

    async def boom(*args: object, **kwargs: object) -> list[ChargerRecord]:
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(run_module, "fetch_openchargemap", ok)
    monkeypatch.setattr(run_module, "fetch_nrel", boom)

    count = await run_module.ingest_chargers(session=session)
    assert count == 1

    total = await session.scalar(select(func.count()).select_from(Charger))
    assert total == 1
