"""OpenChargeMap client and parser."""

from __future__ import annotations

from typing import Any

import httpx

from desertcharge.ingest.records import ChargerRecord, normalize_connector
from desertcharge.region import Bbox

BASE_URL = "https://api.openchargemap.io/v3/poi/"


def _parse_poi(poi: dict[str, Any]) -> ChargerRecord | None:
    address = poi.get("AddressInfo") or {}
    lat = address.get("Latitude")
    lng = address.get("Longitude")
    if lat is None or lng is None:
        return None

    connections = poi.get("Connections") or []
    powers = [c.get("PowerKW") for c in connections if c.get("PowerKW")]
    connectors = {
        normalize_connector(title)
        for c in connections
        if (title := (c.get("ConnectionType") or {}).get("Title"))
    }
    is_dc_fast = any(
        c.get("LevelID") == 3
        or (c.get("Level") or {}).get("IsFastChargeCapable")
        or (c.get("PowerKW") or 0) >= 50
        for c in connections
    )
    operator = poi.get("OperatorInfo") or {}
    return ChargerRecord(
        source="openchargemap",
        source_id=f"OCM-{poi.get('ID')}",
        name=address.get("Title"),
        lat=float(lat),
        lng=float(lng),
        power_kw=max(powers) if powers else None,
        connector_types=tuple(sorted(connectors)),
        network=operator.get("Title"),
        num_ports=poi.get("NumberOfPoints"),
        is_dc_fast=bool(is_dc_fast),
    )


def parse_openchargemap(payload: list[dict[str, Any]]) -> list[ChargerRecord]:
    """Parse an OpenChargeMap POI list into charger records."""
    records = [_parse_poi(poi) for poi in payload]
    return [r for r in records if r is not None]


async def fetch_openchargemap(
    bbox: Bbox, api_key: str, client: httpx.AsyncClient
) -> list[ChargerRecord]:
    """Fetch chargers in the bbox from OpenChargeMap."""
    params: dict[str, str | int] = {
        "output": "json",
        "boundingbox": f"({bbox.max_lat},{bbox.min_lng}),({bbox.min_lat},{bbox.max_lng})",
        "maxresults": 5000,
        "key": api_key,
    }
    response = await client.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()
    return parse_openchargemap(response.json())
