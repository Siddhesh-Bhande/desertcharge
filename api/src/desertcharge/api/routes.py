"""API route handlers."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.api.deps import get_session
from desertcharge.api.read import chargers_in_bbox, list_best_sites, score_point
from desertcharge.api.schemas import BestSiteOut, ChargerOut, ScoreResponse, verdict_for
from desertcharge.scoring import band_for_score

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/score", response_model=ScoreResponse)
async def score(
    session: SessionDep,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
) -> ScoreResponse:
    scored = await score_point(session, lat, lng)
    if scored is None:
        raise HTTPException(status_code=404, detail="No scored data near this point.")
    return ScoreResponse(
        score=scored.desert_score,
        band=band_for_score(scored.desert_score).label,
        verdict=verdict_for(scored.desert_score, scored.nearest_dc_fast_miles),
        population=scored.population,
        nearest_dc_fast_miles=scored.nearest_dc_fast_miles,
        chargers_10mi=scored.chargers_10mi,
        hex_index=scored.hex_index,
        exact=scored.exact,
    )


@router.get("/chargers", response_model=list[ChargerOut])
async def chargers(
    session: SessionDep,
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    speed: str | None = None,
    network: str | None = None,
    connector: str | None = None,
) -> list[ChargerOut]:
    rows = await chargers_in_bbox(
        session, min_lat, min_lng, max_lat, max_lng, speed, network, connector
    )
    return [ChargerOut(**row) for row in rows]


@router.get("/best-sites", response_model=list[BestSiteOut])
async def best_sites(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[BestSiteOut]:
    rows = await list_best_sites(session, limit)
    return [BestSiteOut(**row) for row in rows]
