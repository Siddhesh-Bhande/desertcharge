"""Geocoding via a proxied Nominatim search, scoped to the region."""

from __future__ import annotations

from typing import Any

import httpx

from desertcharge.api.schemas import GeocodeResult
from desertcharge.region import REGION

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DesertCharge/0.1 (https://github.com/Siddhesh-Bhande/desertcharge)"


def parse_nominatim(payload: list[dict[str, Any]]) -> list[GeocodeResult]:
    """Parse a Nominatim search response into geocode results."""
    results = []
    for item in payload:
        lat = item.get("lat")
        lng = item.get("lon")
        if lat is None or lng is None:
            continue
        results.append(
            GeocodeResult(
                name=item.get("display_name", ""),
                lat=float(lat),
                lng=float(lng),
                kind=item.get("type"),
            )
        )
    return results


async def geocode(query: str, client: httpx.AsyncClient) -> list[GeocodeResult]:
    """Search Nominatim for a place, bounded to the region."""
    params: dict[str, str | int] = {
        "q": query,
        "format": "json",
        "limit": 5,
        "countrycodes": "us",
        "viewbox": f"{REGION.min_lng},{REGION.max_lat},{REGION.max_lng},{REGION.min_lat}",
        "bounded": 1,
    }
    response = await client.get(
        NOMINATIM_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    return parse_nominatim(response.json())
