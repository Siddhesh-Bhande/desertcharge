"""Route corridor analysis: an OpenRouteService drive, scored for charging deserts."""

from __future__ import annotations

import math
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.api.schemas import RouteResponse, RouteSample
from desertcharge.queries import nearest_dc_fast_distance_m

ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
METERS_PER_MILE = 1609.34
DESERT_THRESHOLD_MILES = 25.0
SAMPLE_COUNT = 25

# A (lng, lat) coordinate, matching GeoJSON order.
Coord = tuple[float, float]


def _haversine_miles(a: Coord, b: Coord) -> float:
    lng1, lat1 = a
    lng2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def parse_ors_geometry(payload: dict[str, Any]) -> tuple[list[Coord], float]:
    """Return the route coordinates (lng, lat) and total distance in meters."""
    feature = payload["features"][0]
    coords = [(float(c[0]), float(c[1])) for c in feature["geometry"]["coordinates"]]
    distance_m = float(feature["properties"]["summary"]["distance"])
    return coords, distance_m


def sample_along(
    coords: list[Coord], count: int = SAMPLE_COUNT
) -> list[tuple[float, float, float]]:
    """Sample the polyline at ``count`` evenly spaced points. Returns (lat, lng, fraction)."""
    if len(coords) < 2:
        return [(coords[0][1], coords[0][0], 0.0)] if coords else []

    cumulative = [0.0]
    for i in range(1, len(coords)):
        cumulative.append(cumulative[-1] + _haversine_miles(coords[i - 1], coords[i]))
    total = cumulative[-1]
    if total == 0:
        return [(coords[0][1], coords[0][0], 0.0)]

    samples: list[tuple[float, float, float]] = []
    segment = 0
    for step in range(count):
        target = total * step / (count - 1)
        while segment < len(cumulative) - 2 and cumulative[segment + 1] < target:
            segment += 1
        span = cumulative[segment + 1] - cumulative[segment]
        ratio = 0.0 if span == 0 else (target - cumulative[segment]) / span
        lng = coords[segment][0] + (coords[segment + 1][0] - coords[segment][0]) * ratio
        lat = coords[segment][1] + (coords[segment + 1][1] - coords[segment][1]) * ratio
        samples.append((lat, lng, target / total))
    return samples


def worst_gap_miles(samples: list[RouteSample], total_miles: float) -> float:
    """The longest contiguous stretch of the drive far from a DC fast charger."""
    worst = 0.0
    run_start: float | None = None
    for sample in samples:
        far = (
            sample.nearest_dc_fast_miles is None
            or sample.nearest_dc_fast_miles > DESERT_THRESHOLD_MILES
        )
        if far and run_start is None:
            run_start = sample.fraction
        elif not far and run_start is not None:
            worst = max(worst, (sample.fraction - run_start) * total_miles)
            run_start = None
    if run_start is not None:
        worst = max(worst, (samples[-1].fraction - run_start) * total_miles)
    return worst


async def fetch_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    api_key: str,
    client: httpx.AsyncClient,
) -> tuple[list[Coord], float]:
    """Call OpenRouteService for a driving route. origin/destination are (lat, lng)."""
    body = {
        "coordinates": [
            [origin[1], origin[0]],
            [destination[1], destination[0]],
        ]
    }
    response = await client.post(
        ORS_URL,
        json=body,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return parse_ors_geometry(response.json())


async def analyze_route(
    session: AsyncSession,
    origin: tuple[float, float],
    destination: tuple[float, float],
    api_key: str,
    client: httpx.AsyncClient,
) -> RouteResponse:
    """Fetch a route and score each sampled point for fast-charging access."""
    coords, distance_m = await fetch_route(origin, destination, api_key, client)
    total_miles = distance_m / METERS_PER_MILE

    samples: list[RouteSample] = []
    for lat, lng, fraction in sample_along(coords):
        nearest_m = await nearest_dc_fast_distance_m(session, lat, lng)
        miles = nearest_m / METERS_PER_MILE if nearest_m is not None else None
        samples.append(
            RouteSample(lat=lat, lng=lng, fraction=fraction, nearest_dc_fast_miles=miles)
        )

    return RouteResponse(
        geometry=coords,
        distance_miles=total_miles,
        worst_gap_miles=worst_gap_miles(samples, total_miles),
        samples=samples,
    )
