"""Read queries backing the API endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.models import BestSite, Charger, HexScore

METERS_PER_MILE = 1609.34
MAX_CHARGERS = 2000


@dataclass(frozen=True, slots=True)
class ScoredPoint:
    hex_index: str
    desert_score: int
    population: int
    nearest_dc_fast_miles: float | None
    chargers_10mi: float
    exact: bool


def _point(lat: float, lng: float) -> object:
    return func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)


async def score_point(session: AsyncSession, lat: float, lng: float) -> ScoredPoint | None:
    """Score a point using its hex, falling back to the nearest scored hex."""
    point = _point(lat, lng)
    contained = (
        await session.execute(
            select(HexScore).where(func.ST_Contains(HexScore.geom, point)).limit(1)
        )
    ).scalar_one_or_none()
    exact = contained is not None
    hex_row = contained
    if hex_row is None:
        hex_row = (
            await session.execute(
                select(HexScore).order_by(HexScore.centroid.op("<->")(point)).limit(1)
            )
        ).scalar_one_or_none()
    if hex_row is None:
        return None
    miles = (
        hex_row.nearest_dc_fast_m / METERS_PER_MILE
        if hex_row.nearest_dc_fast_m is not None
        else None
    )
    return ScoredPoint(
        hex_index=hex_row.h3_index,
        desert_score=hex_row.desert_score,
        population=int(hex_row.population),
        nearest_dc_fast_miles=miles,
        chargers_10mi=hex_row.weighted_chargers_10mi,
        exact=exact,
    )


async def chargers_in_bbox(
    session: AsyncSession,
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    speed: str | None = None,
    network: str | None = None,
    connector: str | None = None,
) -> list[dict[str, object]]:
    """Return chargers within the bbox, filtered."""
    envelope = func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
    conditions: list[Any] = [Charger.geom.op("&&")(envelope)]
    if speed == "dc":
        conditions.append(Charger.is_dc_fast.is_(True))
    elif speed == "level2":
        conditions.append(Charger.is_dc_fast.is_(False))
    if network:
        conditions.append(Charger.network == network)
    if connector:
        conditions.append(Charger.connector_types.contains([connector]))

    stmt = (
        select(
            Charger.id,
            Charger.name,
            Charger.network,
            Charger.power_kw,
            Charger.connector_types,
            Charger.is_dc_fast,
            func.ST_Y(Charger.geom),
            func.ST_X(Charger.geom),
        )
        .where(*conditions)
        .limit(MAX_CHARGERS)
    )
    rows = await session.execute(stmt)
    return [
        {
            "id": cid,
            "name": name,
            "network": network_name,
            "power_kw": power,
            "connector_types": connectors or [],
            "is_dc_fast": dc,
            "lat": lat,
            "lng": lng,
        }
        for cid, name, network_name, power, connectors, dc, lat, lng in rows
    ]


async def list_best_sites(session: AsyncSession, limit: int) -> list[dict[str, object]]:
    """Return the ranked best sites."""
    stmt = (
        select(
            BestSite.rank,
            BestSite.est_population_served,
            BestSite.gap_miles_closed,
            BestSite.reason,
            func.ST_Y(BestSite.geom),
            func.ST_X(BestSite.geom),
        )
        .order_by(BestSite.rank)
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return [
        {
            "rank": rank,
            "est_population_served": pop,
            "gap_miles_closed": gap,
            "reason": reason,
            "lat": lat,
            "lng": lng,
        }
        for rank, pop, gap, reason, lat, lng in rows
    ]
