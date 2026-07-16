"""NREL Alternative Fuels Data Center client and parser."""

from __future__ import annotations

from typing import Any

import httpx

from desertcharge.ingest.records import ChargerRecord, normalize_connector
from desertcharge.region import Bbox

BASE_URL = "https://developer.nrel.gov/api/alt-fuel-stations/v1.json"


def _port_count(station: dict[str, Any]) -> int:
    return sum(
        int(station.get(field) or 0)
        for field in ("ev_dc_fast_num", "ev_level2_evse_num", "ev_level1_evse_num")
    )


def _parse_station(station: dict[str, Any]) -> ChargerRecord | None:
    lat = station.get("latitude")
    lng = station.get("longitude")
    if lat is None or lng is None:
        return None

    connectors = {normalize_connector(c) for c in (station.get("ev_connector_types") or [])}
    is_dc_fast = int(station.get("ev_dc_fast_num") or 0) > 0
    return ChargerRecord(
        source="nrel",
        source_id=f"NREL-{station.get('id')}",
        name=station.get("station_name"),
        lat=float(lat),
        lng=float(lng),
        power_kw=None,
        connector_types=tuple(sorted(connectors)),
        network=station.get("ev_network"),
        num_ports=_port_count(station) or None,
        is_dc_fast=is_dc_fast,
    )


def parse_nrel(payload: dict[str, Any]) -> list[ChargerRecord]:
    """Parse an NREL AFDC response into charger records."""
    stations = payload.get("fuel_stations") or []
    records = [_parse_station(s) for s in stations]
    return [r for r in records if r is not None]


async def fetch_nrel(bbox: Bbox, api_key: str, client: httpx.AsyncClient) -> list[ChargerRecord]:
    """Fetch chargers in the region from NREL (filtered to CA, NV, AZ)."""
    params = {
        "fuel_type": "ELEC",
        "state": "CA,NV,AZ",
        "limit": "all",
        "api_key": api_key,
    }
    response = await client.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()
    return parse_nrel(response.json())
