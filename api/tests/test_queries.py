from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.models import Charger
from desertcharge.queries import nearest_dc_fast_distance_m


async def _add_charger(session: AsyncSession, lat: float, lng: float, *, is_dc_fast: bool) -> None:
    session.add(
        Charger(
            source="test",
            source_id=f"{lat},{lng}",
            name="test",
            geom=WKTElement(f"POINT({lng} {lat})", srid=4326),
            power_kw=150.0 if is_dc_fast else 7.0,
            is_dc_fast=is_dc_fast,
        )
    )
    # Flush (not commit) so rows are visible in this transaction but roll back
    # when the session closes, keeping tests isolated on the shared database.
    await session.flush()


async def test_nearest_dc_fast_returns_none_when_empty(session: AsyncSession) -> None:
    result = await nearest_dc_fast_distance_m(session, lat=35.0, lng=-116.0)
    assert result is None


async def test_nearest_dc_fast_ignores_slow_chargers(session: AsyncSession) -> None:
    # A close slow charger and a far fast charger.
    await _add_charger(session, 35.0, -116.0, is_dc_fast=False)
    await _add_charger(session, 35.5, -116.0, is_dc_fast=True)
    result = await nearest_dc_fast_distance_m(session, lat=35.0, lng=-116.0)
    assert result is not None
    # ~55 km between 35.0 and 35.5 latitude.
    assert 50_000 < result < 60_000
