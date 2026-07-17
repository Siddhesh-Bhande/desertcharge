from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.grid.supply import weighted_dc_fast_ports_within
from desertcharge.models import Charger


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
