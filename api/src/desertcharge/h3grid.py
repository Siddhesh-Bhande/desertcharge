"""Typed helpers over the h3 v4 library. Pure geometry, no I/O."""

from __future__ import annotations

import h3

# Resolution 7 hexagons are roughly 5 km across, the spec's scoring grid.
DEFAULT_RESOLUTION = 7


def point_to_cell(lat: float, lng: float, resolution: int = DEFAULT_RESOLUTION) -> str:
    """Return the H3 cell index containing the point."""
    return str(h3.latlng_to_cell(lat, lng, resolution))


def cell_centroid(cell: str) -> tuple[float, float]:
    """Return the (lat, lng) centroid of a cell."""
    lat, lng = h3.cell_to_latlng(cell)
    return lat, lng


def cell_ring_lnglat(cell: str) -> list[tuple[float, float]]:
    """Return the cell boundary as a closed ring of (lng, lat) pairs (GeoJSON order)."""
    boundary = h3.cell_to_boundary(cell)
    ring = [(lng, lat) for lat, lng in boundary]
    ring.append(ring[0])
    return ring


def cells_for_bbox(
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    resolution: int = DEFAULT_RESOLUTION,
) -> list[str]:
    """Return all H3 cells whose center falls within the bounding box."""
    outer = [
        (min_lat, min_lng),
        (min_lat, max_lng),
        (max_lat, max_lng),
        (max_lat, min_lng),
        (min_lat, min_lng),
    ]
    poly = h3.LatLngPoly(outer)
    return list(h3.polygon_to_cells(poly, resolution))
