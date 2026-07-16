"""Merge charger records across sources, de-duplicating by proximity."""

from __future__ import annotations

import math

from desertcharge.ingest.records import ChargerRecord

# Two chargers closer than this are treated as the same physical site.
DEDUPE_METERS = 75.0
EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance in meters between two points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def merge_chargers(*groups: list[ChargerRecord]) -> list[ChargerRecord]:
    """Concatenate record groups and drop near-duplicates. Earlier groups win."""
    kept: list[ChargerRecord] = []
    for group in groups:
        for record in group:
            duplicate = any(
                haversine_m(record.lat, record.lng, other.lat, other.lng) < DEDUPE_METERS
                for other in kept
            )
            if not duplicate:
                kept.append(record)
    return kept
