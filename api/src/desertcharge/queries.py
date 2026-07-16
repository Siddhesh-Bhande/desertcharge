"""Spatial queries over the chargers table."""

from __future__ import annotations

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.models import Charger


async def nearest_dc_fast_distance_m(session: AsyncSession, lat: float, lng: float) -> float | None:
    """Return meters to the nearest DC fast charger, or None if there are none."""
    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    distance = func.ST_Distance(
        cast(Charger.geom, Geography),
        cast(point, Geography),
    )
    stmt = select(distance).where(Charger.is_dc_fast.is_(True)).order_by(distance).limit(1)
    result = await session.execute(stmt)
    value = result.scalar_one_or_none()
    return float(value) if value is not None else None
