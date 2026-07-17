"""Supply-side spatial measures over the chargers table."""

from __future__ import annotations

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.models import Charger


async def weighted_dc_fast_ports_within(
    session: AsyncSession, lat: float, lng: float, meters: float
) -> float:
    """Return the summed DC fast port count within ``meters`` of the point.

    Each charger contributes its port count (defaulting to 1 when unknown).
    """
    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    ports = func.coalesce(Charger.num_ports, 1)
    stmt = select(func.coalesce(func.sum(ports), 0)).where(
        Charger.is_dc_fast.is_(True),
        func.ST_DWithin(cast(Charger.geom, Geography), cast(point, Geography), meters),
    )
    return float(await session.scalar(stmt) or 0)
