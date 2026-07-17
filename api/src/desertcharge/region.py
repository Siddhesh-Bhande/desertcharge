"""The geographic region DesertCharge covers: the US Desert Southwest."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Bbox:
    """A lat/lng bounding box."""

    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float

    def contains(self, lat: float, lng: float) -> bool:
        """Return True if the point falls inside the box."""
        return self.min_lat <= lat <= self.max_lat and self.min_lng <= lng <= self.max_lng


# Southern California, Nevada, and Arizona.
REGION = Bbox(min_lat=31.3, min_lng=-120.6, max_lat=42.1, max_lng=-108.9)

# State FIPS codes for the region, keyed by USPS abbreviation.
REGION_STATES: dict[str, str] = {"CA": "06", "NV": "32", "AZ": "04"}


def tile_bbox(bbox: Bbox, cols: int, rows: int) -> list[Bbox]:
    """Split a bbox into a cols-by-rows grid of sub-boxes.

    OpenChargeMap caps results per request, so fetching per tile avoids missing
    chargers in dense areas.
    """
    lat_step = (bbox.max_lat - bbox.min_lat) / rows
    lng_step = (bbox.max_lng - bbox.min_lng) / cols
    tiles: list[Bbox] = []
    for row in range(rows):
        for col in range(cols):
            tiles.append(
                Bbox(
                    min_lat=bbox.min_lat + row * lat_step,
                    min_lng=bbox.min_lng + col * lng_step,
                    max_lat=bbox.min_lat + (row + 1) * lat_step,
                    max_lng=bbox.min_lng + (col + 1) * lng_step,
                )
            )
    return tiles
