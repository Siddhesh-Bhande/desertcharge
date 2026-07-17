"""Pydantic response models and the verdict helper."""

from __future__ import annotations

from pydantic import BaseModel

from desertcharge.scoring import ScoreBand, band_for_score

FAR_MILES = 900.0


def verdict_for(score: int, nearest_miles: float | None) -> str:
    """A short, plain-language verdict for a score."""
    band = band_for_score(score)
    if band in (ScoreBand.SERVED, ScoreBand.GOOD):
        return "Well served. Fast charging is nearby."
    if nearest_miles is None or nearest_miles > FAR_MILES:
        return "Charging desert. No fast charger for a long way."
    return f"Underserved. Nearest fast charger is {round(nearest_miles)} miles away."


class ScoreResponse(BaseModel):
    score: int
    band: str
    verdict: str
    population: int
    nearest_dc_fast_miles: float | None
    chargers_10mi: float
    hex_index: str
    exact: bool


class ChargerOut(BaseModel):
    id: int
    name: str | None
    network: str | None
    power_kw: float | None
    connector_types: list[str]
    is_dc_fast: bool
    lat: float
    lng: float


class BestSiteOut(BaseModel):
    rank: int
    lat: float
    lng: float
    est_population_served: int
    gap_miles_closed: float
    reason: str | None
