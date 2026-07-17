"""Census tract ingest from the keyless TIGERweb API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

BASE_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer"
_PAGE = 5000


@dataclass(frozen=True, slots=True)
class TractRecord:
    """One census tract: its population and centroid."""

    geoid: str
    state: str
    population: int
    lat: float
    lng: float


def parse_centroids(payload: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """Map GEOID to (lat, lng) from a TIGERweb layer-0 response."""
    result: dict[str, tuple[float, float]] = {}
    for feature in payload.get("features", []):
        attrs = feature.get("attributes", {})
        geoid = attrs.get("GEOID")
        lat = attrs.get("CENTLAT")
        lng = attrs.get("CENTLON")
        if geoid and lat and lng:
            result[geoid] = (float(lat), float(lng))
    return result


def parse_populations(payload: dict[str, Any]) -> dict[str, int]:
    """Map GEOID to population from a TIGERweb layer-2 groupBy response."""
    result: dict[str, int] = {}
    for feature in payload.get("features", []):
        attrs = feature.get("attributes", {})
        state = attrs.get("STATE")
        county = attrs.get("COUNTY")
        tract = attrs.get("TRACT")
        if state and county and tract:
            result[f"{state}{county}{tract}"] = int(attrs.get("pop") or 0)
    return result


def build_tract_records(
    centroids: dict[str, tuple[float, float]], populations: dict[str, int], state: str
) -> list[TractRecord]:
    """Join centroids and populations by GEOID into tract records."""
    records = []
    for geoid, population in populations.items():
        if geoid in centroids:
            lat, lng = centroids[geoid]
            records.append(
                TractRecord(geoid=geoid, state=state, population=population, lat=lat, lng=lng)
            )
    return records


async def _fetch_centroids(client: httpx.AsyncClient, fips: str) -> dict[str, tuple[float, float]]:
    centroids: dict[str, tuple[float, float]] = {}
    offset = 0
    while True:
        response = await client.get(
            f"{BASE_URL}/0/query",
            params={
                "where": f"STATE='{fips}'",
                "outFields": "GEOID,CENTLAT,CENTLON",
                "returnGeometry": "false",
                "f": "json",
                "resultOffset": offset,
                "resultRecordCount": _PAGE,
            },
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        page = parse_centroids(payload)
        centroids.update(page)
        if not payload.get("exceededTransferLimit") or not page:
            break
        offset += len(page)
    return centroids


async def _fetch_populations(client: httpx.AsyncClient, fips: str) -> dict[str, int]:
    response = await client.get(
        f"{BASE_URL}/2/query",
        params={
            "where": f"STATE='{fips}'",
            "groupByFieldsForStatistics": "STATE,COUNTY,TRACT",
            "outStatistics": json.dumps(
                [
                    {
                        "statisticType": "sum",
                        "onStatisticField": "POP100",
                        "outStatisticFieldName": "pop",
                    }
                ]
            ),
            "returnGeometry": "false",
            "f": "json",
        },
        timeout=120,
    )
    response.raise_for_status()
    return parse_populations(response.json())


async def fetch_tracts(fips: str, state: str, client: httpx.AsyncClient) -> list[TractRecord]:
    """Fetch and join tract centroids and population for one state."""
    centroids = await _fetch_centroids(client, fips)
    populations = await _fetch_populations(client, fips)
    return build_tract_records(centroids, populations, state)
