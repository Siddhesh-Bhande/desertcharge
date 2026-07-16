"""Pure desert-score functions and band mapping. No I/O."""

from __future__ import annotations

from enum import Enum


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
