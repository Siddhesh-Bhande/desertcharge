"""Aggregate tract demand into H3 hexes and build hex geometry WKT."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from desertcharge.h3grid import cell_ring_lnglat, point_to_cell
from desertcharge.ingest.census import TractRecord


def hex_populations(tracts: Sequence[TractRecord]) -> dict[str, int]:
    """Sum tract population into the H3 cell containing each tract centroid."""
    totals: dict[str, int] = defaultdict(int)
    for tract in tracts:
        totals[point_to_cell(tract.lat, tract.lng)] += tract.population
    return dict(totals)


def hex_polygon_wkt(cell: str) -> str:
    """Return the hex boundary as a POLYGON WKT string (lng lat order)."""
    ring = cell_ring_lnglat(cell)
    coords = ", ".join(f"{lng} {lat}" for lng, lat in ring)
    return f"POLYGON(({coords}))"
