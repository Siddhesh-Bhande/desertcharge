"""Pure desert-score functions and band mapping. No I/O."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

ACCESS_TARGET_PORTS = 3.0
FULL_GAP_MILES = 30.0


class ScoreBand(Enum):
    """A desert-score band, with its display label and token color."""

    SERVED = ("served", "#1B9E8A")
    GOOD = ("good", "#7FB069")
    MODERATE = ("moderate", "#E6B23A")
    POOR = ("poor", "#D57A33")
    DESERT = ("desert", "#B23A24")

    def __init__(self, label: str, color: str) -> None:
        self.label = label
        self.color = color


def band_for_score(score: int) -> ScoreBand:
    """Return the band for a 0-100 desert score."""
    if score <= 20:
        return ScoreBand.SERVED
    if score <= 40:
        return ScoreBand.GOOD
    if score <= 60:
        return ScoreBand.MODERATE
    if score <= 80:
        return ScoreBand.POOR
    return ScoreBand.DESERT


def clamp(value: float, low: float, high: float) -> float:
    """Constrain value to the inclusive range [low, high]."""
    return max(low, min(high, value))


def normalize(value: float, low: float, high: float) -> float:
    """Min-max normalize value into [0, 1]. A degenerate range maps to 0."""
    if high <= low:
        return 0.0
    return clamp((value - low) / (high - low), 0.0, 1.0)


def supply_gap(nearest_dc_fast_miles: float, weighted_chargers_10mi: float) -> float:
    """Return the 0..1 supply shortfall. Higher means worse coverage."""
    distance_gap = clamp(nearest_dc_fast_miles / FULL_GAP_MILES, 0.0, 1.0)
    access = min(1.0, weighted_chargers_10mi / ACCESS_TARGET_PORTS)
    return 0.5 * distance_gap + 0.5 * (1.0 - access)


def desert_score(
    population: float,
    pop_min: float,
    pop_max: float,
    nearest_dc_fast_miles: float,
    weighted_chargers_10mi: float,
) -> int:
    """Return the 0-100 desert score for one hex's inputs."""
    demand_norm = normalize(population, pop_min, pop_max)
    gap = supply_gap(nearest_dc_fast_miles, weighted_chargers_10mi)
    return round(100 * math.sqrt(demand_norm) * gap)


@dataclass(frozen=True, slots=True)
class HexScoreResult:
    """The scored output for one hex, including factors for display."""

    score: int
    band: ScoreBand
    population: float
    nearest_dc_fast_miles: float
    chargers_10mi: float


def score_hex(
    population: float,
    pop_min: float,
    pop_max: float,
    nearest_dc_fast_miles: float,
    weighted_chargers_10mi: float,
) -> HexScoreResult:
    """Score one hex and return the score, band, and contributing factors."""
    score = desert_score(
        population=population,
        pop_min=pop_min,
        pop_max=pop_max,
        nearest_dc_fast_miles=nearest_dc_fast_miles,
        weighted_chargers_10mi=weighted_chargers_10mi,
    )
    return HexScoreResult(
        score=score,
        band=band_for_score(score),
        population=population,
        nearest_dc_fast_miles=nearest_dc_fast_miles,
        chargers_10mi=weighted_chargers_10mi,
    )
