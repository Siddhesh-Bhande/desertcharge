# DesertCharge Phase 2: Charger Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch EV chargers for the Desert Southwest from OpenChargeMap and NREL, normalize both into a common record, merge and dedupe them, and load the result into the PostGIS `chargers` table, driven by a resilient CLI.

**Architecture:** Two async httpx clients (one per source) each parse their provider's JSON into a shared `ChargerRecord`. A pure merge step concatenates and de-duplicates across sources by proximity. A loader replaces the `chargers` table contents transactionally. A CLI orchestrates fetch, merge, and load, and tolerates a single source failing (logged, not fatal). Client parsing is tested against fixtures; merge is a pure unit; the loader is tested against a real PostGIS container.

**Tech Stack:** httpx (async), SQLAlchemy async, GeoAlchemy2, pytest with httpx MockTransport, PostGIS testcontainer.

---

## Confirmed source shapes

OpenChargeMap POI (verified live): each POI has `ID`, `AddressInfo{Title, Latitude,
Longitude}`, `OperatorInfo{Title}`, `NumberOfPoints`, and `Connections[]` where each
connection has `PowerKW`, `LevelID` (3 means DC fast), `ConnectionType{Title}`, and
`Level{IsFastChargeCapable}`.

NREL AFDC ELEC station: `id`, `station_name`, `latitude`, `longitude`, `ev_network`,
`ev_connector_types[]` (for example `J1772`, `J1772COMBO`, `CHADEMO`, `TESLA`),
`ev_dc_fast_num`, `ev_level2_evse_num`, `ev_level1_evse_num`.

---

## File structure (Phase 2)

```
api/pyproject.toml                         add httpx dependency (modify)
api/src/desertcharge/config.py             add API keys, read repo-root .env (modify)
api/src/desertcharge/region.py             Bbox type + REGION constant (create)
api/src/desertcharge/ingest/__init__.py    (create)
api/src/desertcharge/ingest/records.py     ChargerRecord + connector/flags helpers (create)
api/src/desertcharge/ingest/openchargemap.py  OCM client + parser (create)
api/src/desertcharge/ingest/nrel.py        NREL client + parser (create)
api/src/desertcharge/ingest/merge.py       proximity dedupe (create)
api/src/desertcharge/ingest/load.py        replace chargers table (create)
api/src/desertcharge/ingest/run.py         orchestrator + CLI main (create)
api/tests/fixtures/ocm_sample.json         (create)
api/tests/fixtures/nrel_sample.json        (create)
api/tests/test_records.py                  (create)
api/tests/test_openchargemap.py            (create)
api/tests/test_nrel.py                     (create)
api/tests/test_merge.py                    (create)
api/tests/test_load.py                     (create)
.github/workflows/ci.yml                   backend job already runs these (no change)
```

---

### Task 1: Add httpx and region constants

**Files:**
- Modify: `api/pyproject.toml`
- Create: `api/src/desertcharge/region.py`
- Test: `api/tests/test_records.py` (region part)

- [ ] **Step 1: Add httpx to dependencies in `pyproject.toml`**

In the `dependencies` list, add:

```toml
    "httpx>=0.27",
```

- [ ] **Step 2: Sync**

Run: `cd api && uv sync`
Expected: httpx installed.

- [ ] **Step 3: Write the failing test**

`api/tests/test_records.py`:

```python
from desertcharge.region import REGION, Bbox


def test_region_is_the_desert_southwest() -> None:
    assert isinstance(REGION, Bbox)
    # Covers Southern California, Nevada, and Arizona.
    assert REGION.min_lat < 33.0 < REGION.max_lat
    assert REGION.min_lng < -115.0 < REGION.max_lng
    assert REGION.contains(35.2686, -116.0786)  # Baker, CA
    assert not REGION.contains(47.6, -122.3)  # Seattle, out of region
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd api && uv run pytest tests/test_records.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'desertcharge.region'`.

- [ ] **Step 5: Write `region.py`**

```python
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
        return (
            self.min_lat <= lat <= self.max_lat
            and self.min_lng <= lng <= self.max_lng
        )


# Southern California, Nevada, and Arizona.
REGION = Bbox(min_lat=31.3, min_lng=-120.6, max_lat=42.1, max_lng=-108.9)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd api && uv run pytest tests/test_records.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add api/pyproject.toml api/uv.lock api/src/desertcharge/region.py api/tests/test_records.py
git commit -m "feat(api): add httpx and Desert Southwest region bbox"
```

---

### Task 2: The ChargerRecord and normalization helpers

**Files:**
- Create: `api/src/desertcharge/ingest/__init__.py`
- Create: `api/src/desertcharge/ingest/records.py`
- Test: `api/tests/test_records.py`

- [ ] **Step 1: Append failing tests to `api/tests/test_records.py`**

Add at the top import line and new tests:

```python
from desertcharge.ingest.records import ChargerRecord, normalize_connector
```

Append these tests:

```python
def test_normalize_connector_canonical_forms() -> None:
    assert normalize_connector("J1772COMBO") == "CCS"
    assert normalize_connector("CCS (Type 1)") == "CCS"
    assert normalize_connector("CHADEMO") == "CHAdeMO"
    assert normalize_connector("CHAdeMO") == "CHAdeMO"
    assert normalize_connector("Tesla (Model S/X)") == "NACS"
    assert normalize_connector("TESLA") == "NACS"
    assert normalize_connector("J1772") == "J1772"
    assert normalize_connector("Type 2 (Socket Only)") == "J1772"
    assert normalize_connector("Some Weird Plug") == "Other"


def test_charger_record_is_frozen_with_fields() -> None:
    record = ChargerRecord(
        source="openchargemap",
        source_id="OCM-1",
        name="Baker",
        lat=35.27,
        lng=-116.08,
        power_kw=150.0,
        connector_types=("CCS",),
        network="Electrify America",
        num_ports=4,
        is_dc_fast=True,
    )
    assert record.source_id == "OCM-1"
    assert record.is_dc_fast is True
    assert record.connector_types == ("CCS",)
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && uv run pytest tests/test_records.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'desertcharge.ingest'`.

- [ ] **Step 3: Create `api/src/desertcharge/ingest/__init__.py`**

```python
"""Data ingest: fetch, normalize, merge, and load chargers."""
```

- [ ] **Step 4: Create `api/src/desertcharge/ingest/records.py`**

```python
"""The common charger record shared by all sources, and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChargerRecord:
    """One charger, normalized across sources."""

    source: str
    source_id: str
    name: str | None
    lat: float
    lng: float
    power_kw: float | None
    connector_types: tuple[str, ...]
    network: str | None
    num_ports: int | None
    is_dc_fast: bool


def normalize_connector(raw: str) -> str:
    """Map a source's connector label to a canonical token."""
    text = raw.lower()
    if "combo" in text or "ccs" in text:
        return "CCS"
    if "chademo" in text:
        return "CHAdeMO"
    if "tesla" in text or "nacs" in text or "j3400" in text:
        return "NACS"
    if "j1772" in text or "type 1" in text or "type 2" in text or "mennekes" in text:
        return "J1772"
    return "Other"
```

- [ ] **Step 5: Run to verify pass**

Run: `cd api && uv run pytest tests/test_records.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/ingest/__init__.py api/src/desertcharge/ingest/records.py api/tests/test_records.py
git commit -m "feat(api): add ChargerRecord and connector normalization"
```

---

### Task 3: OpenChargeMap client and parser

**Files:**
- Create: `api/tests/fixtures/ocm_sample.json`
- Create: `api/src/desertcharge/ingest/openchargemap.py`
- Test: `api/tests/test_openchargemap.py`

- [ ] **Step 1: Create the fixture `api/tests/fixtures/ocm_sample.json`**

```json
[
  {
    "ID": 12345,
    "AddressInfo": {"Title": "Baker Travel Center", "Latitude": 35.2686, "Longitude": -116.0786},
    "OperatorInfo": {"Title": "Electrify America"},
    "NumberOfPoints": 4,
    "Connections": [
      {"PowerKW": 150.0, "LevelID": 3, "ConnectionType": {"Title": "CCS (Type 1)"}, "Level": {"IsFastChargeCapable": true}},
      {"PowerKW": 50.0, "LevelID": 3, "ConnectionType": {"Title": "CHAdeMO"}, "Level": {"IsFastChargeCapable": true}}
    ]
  },
  {
    "ID": 67890,
    "AddressInfo": {"Title": "Barstow Library", "Latitude": 34.8958, "Longitude": -117.0173},
    "OperatorInfo": {"Title": "ChargePoint"},
    "NumberOfPoints": 2,
    "Connections": [
      {"PowerKW": 6.6, "LevelID": 2, "ConnectionType": {"Title": "J1772"}, "Level": {"IsFastChargeCapable": false}}
    ]
  }
]
```

- [ ] **Step 2: Write failing test `api/tests/test_openchargemap.py`**

```python
import json
from pathlib import Path

import httpx

from desertcharge.ingest.openchargemap import parse_openchargemap
from desertcharge.region import REGION

FIXTURE = Path(__file__).parent / "fixtures" / "ocm_sample.json"


def test_parse_openchargemap_maps_fields() -> None:
    payload = json.loads(FIXTURE.read_text())
    records = parse_openchargemap(payload)
    assert len(records) == 2

    baker = records[0]
    assert baker.source == "openchargemap"
    assert baker.source_id == "OCM-12345"
    assert baker.name == "Baker Travel Center"
    assert baker.lat == 35.2686
    assert baker.network == "Electrify America"
    assert baker.num_ports == 4
    assert baker.power_kw == 150.0  # the max across connections
    assert baker.is_dc_fast is True
    assert set(baker.connector_types) == {"CCS", "CHAdeMO"}

    barstow = records[1]
    assert barstow.is_dc_fast is False
    assert barstow.connector_types == ("J1772",)


async def test_fetch_openchargemap_uses_mock_transport() -> None:
    payload = json.loads(FIXTURE.read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.openchargemap.io"
        return httpx.Response(200, json=payload)

    from desertcharge.ingest.openchargemap import fetch_openchargemap

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        records = await fetch_openchargemap(REGION, api_key="k", client=client)
    assert len(records) == 2
```

- [ ] **Step 3: Run to verify failure**

Run: `cd api && uv run pytest tests/test_openchargemap.py -v`
Expected: FAIL with import error.

- [ ] **Step 4: Write `api/src/desertcharge/ingest/openchargemap.py`**

```python
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
        normalize_connector(t)
        for c in connections
        if (t := (c.get("ConnectionType") or {}).get("Title"))
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
    params = {
        "output": "json",
        "boundingbox": f"({bbox.max_lat},{bbox.min_lng}),({bbox.min_lat},{bbox.max_lng})",
        "maxresults": 5000,
        "key": api_key,
    }
    response = await client.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()
    return parse_openchargemap(response.json())
```

- [ ] **Step 5: Run to verify pass**

Run: `cd api && uv run pytest tests/test_openchargemap.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/ingest/openchargemap.py api/tests/test_openchargemap.py api/tests/fixtures/ocm_sample.json
git commit -m "feat(api): add OpenChargeMap client and parser"
```

---

### Task 4: NREL client and parser

**Files:**
- Create: `api/tests/fixtures/nrel_sample.json`
- Create: `api/src/desertcharge/ingest/nrel.py`
- Test: `api/tests/test_nrel.py`

- [ ] **Step 1: Create fixture `api/tests/fixtures/nrel_sample.json`**

```json
{
  "fuel_stations": [
    {
      "id": 1001,
      "station_name": "Primm Valley Casino",
      "latitude": 35.6103,
      "longitude": -115.3897,
      "ev_network": "Tesla",
      "ev_connector_types": ["TESLA", "J1772COMBO"],
      "ev_dc_fast_num": 8,
      "ev_level2_evse_num": 2,
      "ev_level1_evse_num": null
    },
    {
      "id": 1002,
      "station_name": "Kingman City Hall",
      "latitude": 35.1894,
      "longitude": -114.0530,
      "ev_network": "Non-Networked",
      "ev_connector_types": ["J1772"],
      "ev_dc_fast_num": null,
      "ev_level2_evse_num": 2,
      "ev_level1_evse_num": null
    }
  ]
}
```

- [ ] **Step 2: Write failing test `api/tests/test_nrel.py`**

```python
import json
from pathlib import Path

import httpx

from desertcharge.ingest.nrel import parse_nrel
from desertcharge.region import REGION

FIXTURE = Path(__file__).parent / "fixtures" / "nrel_sample.json"


def test_parse_nrel_maps_fields() -> None:
    payload = json.loads(FIXTURE.read_text())
    records = parse_nrel(payload)
    assert len(records) == 2

    primm = records[0]
    assert primm.source == "nrel"
    assert primm.source_id == "NREL-1001"
    assert primm.name == "Primm Valley Casino"
    assert primm.network == "Tesla"
    assert primm.is_dc_fast is True
    assert primm.num_ports == 10  # 8 dc + 2 l2
    assert set(primm.connector_types) == {"NACS", "CCS"}

    kingman = records[1]
    assert kingman.is_dc_fast is False
    assert kingman.num_ports == 2
    assert kingman.connector_types == ("J1772",)


async def test_fetch_nrel_uses_mock_transport() -> None:
    payload = json.loads(FIXTURE.read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "developer.nrel.gov"
        return httpx.Response(200, json=payload)

    from desertcharge.ingest.nrel import fetch_nrel

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        records = await fetch_nrel(REGION, api_key="k", client=client)
    assert len(records) == 2
```

- [ ] **Step 3: Run to verify failure**

Run: `cd api && uv run pytest tests/test_nrel.py -v`
Expected: FAIL with import error.

- [ ] **Step 4: Write `api/src/desertcharge/ingest/nrel.py`**

```python
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

    connectors = {
        normalize_connector(c) for c in (station.get("ev_connector_types") or [])
    }
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


async def fetch_nrel(
    bbox: Bbox, api_key: str, client: httpx.AsyncClient
) -> list[ChargerRecord]:
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
```

- [ ] **Step 5: Run to verify pass**

Run: `cd api && uv run pytest tests/test_nrel.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/ingest/nrel.py api/tests/test_nrel.py api/tests/fixtures/nrel_sample.json
git commit -m "feat(api): add NREL client and parser"
```

---

### Task 5: Merge and dedupe across sources

**Files:**
- Create: `api/src/desertcharge/ingest/merge.py`
- Test: `api/tests/test_merge.py`

- [ ] **Step 1: Write failing test `api/tests/test_merge.py`**

```python
from desertcharge.ingest.merge import haversine_m, merge_chargers
from desertcharge.ingest.records import ChargerRecord


def _record(source: str, sid: str, lat: float, lng: float) -> ChargerRecord:
    return ChargerRecord(
        source=source,
        source_id=sid,
        name=sid,
        lat=lat,
        lng=lng,
        power_kw=150.0,
        connector_types=("CCS",),
        network="net",
        num_ports=2,
        is_dc_fast=True,
    )


def test_haversine_known_distance() -> None:
    # 0.5 degrees of latitude is about 55.6 km.
    d = haversine_m(35.0, -116.0, 35.5, -116.0)
    assert 54_000 < d < 57_000


def test_merge_dedupes_near_duplicates_across_sources() -> None:
    ocm = [_record("openchargemap", "OCM-1", 35.2686, -116.0786)]
    # Same physical spot, ~30 m away, from the other source.
    nrel = [_record("nrel", "NREL-9", 35.2688, -116.0786)]
    merged = merge_chargers(ocm, nrel)
    assert len(merged) == 1
    assert merged[0].source == "openchargemap"  # first group wins


def test_merge_keeps_distinct_chargers() -> None:
    ocm = [_record("openchargemap", "OCM-1", 35.0, -116.0)]
    nrel = [_record("nrel", "NREL-9", 35.5, -116.0)]  # ~55 km away
    merged = merge_chargers(ocm, nrel)
    assert len(merged) == 2
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && uv run pytest tests/test_merge.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Write `api/src/desertcharge/ingest/merge.py`**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `cd api && uv run pytest tests/test_merge.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/desertcharge/ingest/merge.py api/tests/test_merge.py
git commit -m "feat(api): add cross-source charger merge and dedupe"
```

---

### Task 6: Load chargers into PostGIS

**Files:**
- Create: `api/src/desertcharge/ingest/load.py`
- Test: `api/tests/test_load.py`

- [ ] **Step 1: Write failing test `api/tests/test_load.py`**

```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.ingest.load import load_chargers
from desertcharge.ingest.records import ChargerRecord
from desertcharge.models import Charger


def _record(sid: str, lat: float, lng: float, *, dc: bool) -> ChargerRecord:
    return ChargerRecord(
        source="openchargemap",
        source_id=sid,
        name=sid,
        lat=lat,
        lng=lng,
        power_kw=150.0 if dc else 7.0,
        connector_types=("CCS",),
        network="Electrify America",
        num_ports=2,
        is_dc_fast=dc,
    )


async def test_load_chargers_replaces_table(session: AsyncSession) -> None:
    first = [_record("OCM-1", 35.0, -116.0, dc=True)]
    count = await load_chargers(session, first)
    assert count == 1

    total = await session.scalar(select(func.count()).select_from(Charger))
    assert total == 1

    # A second load replaces, not appends.
    second = [
        _record("OCM-2", 35.1, -116.1, dc=True),
        _record("OCM-3", 35.2, -116.2, dc=False),
    ]
    count = await load_chargers(session, second)
    assert count == 2
    total = await session.scalar(select(func.count()).select_from(Charger))
    assert total == 2
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && uv run pytest tests/test_load.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Write `api/src/desertcharge/ingest/load.py`**

```python
"""Load charger records into the PostGIS chargers table (full replace)."""

from __future__ import annotations

from collections.abc import Sequence

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.ingest.records import ChargerRecord
from desertcharge.models import Charger


def _to_model(record: ChargerRecord) -> Charger:
    return Charger(
        source=record.source,
        source_id=record.source_id,
        name=record.name,
        geom=WKTElement(f"POINT({record.lng} {record.lat})", srid=4326),
        power_kw=record.power_kw,
        connector_types=list(record.connector_types),
        network=record.network,
        num_ports=record.num_ports,
        is_dc_fast=record.is_dc_fast,
    )


async def load_chargers(session: AsyncSession, records: Sequence[ChargerRecord]) -> int:
    """Replace the chargers table with the given records. Returns the row count."""
    await session.execute(delete(Charger))
    session.add_all([_to_model(record) for record in records])
    await session.flush()
    await session.commit()
    return len(records)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd api && uv run pytest tests/test_load.py -v`
Expected: PASS (uses the PostGIS container).

- [ ] **Step 5: Commit**

```bash
git add api/src/desertcharge/ingest/load.py api/tests/test_load.py
git commit -m "feat(api): add chargers table loader (full replace)"
```

---

### Task 7: Orchestrator CLI, resilient to a failing source, plus keys in settings

**Files:**
- Modify: `api/src/desertcharge/config.py`
- Create: `api/src/desertcharge/ingest/run.py`
- Test: `api/tests/test_records.py` (settings part) or a new small test in `run`

- [ ] **Step 1: Update `config.py` to read the repo-root .env and hold the keys**

Replace the contents of `api/src/desertcharge/config.py` with:

```python
"""Application settings loaded from the environment."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_URL = "postgresql+asyncpg://desertcharge:desertcharge@localhost:5432/desertcharge"

# The .env lives at the repository root, one level above the api/ package.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Backend configuration. Values come from the environment or the root .env file."""

    model_config = SettingsConfigDict(env_file=_ROOT_ENV, extra="ignore")

    database_url: str = DEFAULT_DATABASE_URL
    openchargemap_api_key: str = ""
    nrel_api_key: str = ""

    @property
    def sync_database_url(self) -> str:
        """The same database as a sync URL for Alembic (psycopg2 driver)."""
        return self.database_url.replace("+asyncpg", "+psycopg2")


def get_settings() -> Settings:
    """Return a fresh Settings instance."""
    return Settings()
```

- [ ] **Step 2: Write the orchestrator `api/src/desertcharge/ingest/run.py`**

```python
"""Orchestrate the charger ingest: fetch each source, merge, and load."""

from __future__ import annotations

import asyncio
import logging

import httpx

from desertcharge.config import get_settings
from desertcharge.db import create_engine_from_settings, create_session_factory
from desertcharge.ingest.load import load_chargers
from desertcharge.ingest.merge import merge_chargers
from desertcharge.ingest.nrel import fetch_nrel
from desertcharge.ingest.openchargemap import fetch_openchargemap
from desertcharge.ingest.records import ChargerRecord
from desertcharge.region import REGION

logger = logging.getLogger(__name__)


async def _safe_fetch(name: str, coro: object) -> list[ChargerRecord]:
    """Await a fetch, returning an empty list (logged) if the source fails."""
    try:
        return await coro  # type: ignore[misc]
    except (httpx.HTTPError, httpx.InvalidURL) as exc:
        logger.warning("Source %s failed: %s", name, exc)
        return []


async def ingest_chargers() -> int:
    """Fetch chargers from all sources, merge, and load. Returns rows loaded."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        ocm = await _safe_fetch(
            "openchargemap",
            fetch_openchargemap(REGION, settings.openchargemap_api_key, client),
        )
        nrel = await _safe_fetch(
            "nrel", fetch_nrel(REGION, settings.nrel_api_key, client)
        )

    merged = merge_chargers(ocm, nrel)
    logger.info("Fetched OCM=%d NREL=%d merged=%d", len(ocm), len(nrel), len(merged))

    engine = create_engine_from_settings()
    factory = create_session_factory(engine)
    async with factory() as session:
        count = await load_chargers(session, merged)
    await engine.dispose()
    return count


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    count = asyncio.run(ingest_chargers())
    logger.info("Loaded %d chargers.", count)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write a test that the orchestrator merges and loads, `api/tests/test_run.py`**

```python
import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.ingest import run as run_module
from desertcharge.ingest.records import ChargerRecord
from desertcharge.models import Charger


def _record(source: str, sid: str, lat: float) -> ChargerRecord:
    return ChargerRecord(
        source=source,
        source_id=sid,
        name=sid,
        lat=lat,
        lng=-116.0,
        power_kw=150.0,
        connector_types=("CCS",),
        network="net",
        num_ports=2,
        is_dc_fast=True,
    )


async def test_ingest_is_resilient_to_a_failing_source(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def ok(*args: object, **kwargs: object) -> list[ChargerRecord]:
        return [_record("openchargemap", "OCM-1", 35.0)]

    async def boom(*args: object, **kwargs: object) -> list[ChargerRecord]:
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(run_module, "fetch_openchargemap", ok)
    monkeypatch.setattr(run_module, "fetch_nrel", boom)
    # Point the loader at the test session's engine via its bind.
    monkeypatch.setattr(
        run_module, "create_engine_from_settings", lambda: session.get_bind()
    )
    monkeypatch.setattr(
        run_module, "create_session_factory", lambda engine: _factory(session)
    )

    count = await run_module.ingest_chargers()
    assert count == 1
    total = await session.scalar(select(func.count()).select_from(Charger))
    assert total == 1


def _factory(session: AsyncSession):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def factory():
        yield session

    return factory
```

Note: this test overrides the engine and session factory so the orchestrator writes
through the test session bound to the PostGIS container, and forces the NREL source to
fail to prove resilience.

- [ ] **Step 4: Run to verify pass**

Run: `cd api && uv run pytest tests/test_run.py -v`
Expected: PASS.

- [ ] **Step 5: Full check**

Run:
```bash
cd api && uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/config.py api/src/desertcharge/ingest/run.py api/tests/test_run.py
git commit -m "feat(api): add resilient charger ingest orchestrator and CLI"
```

---

### Task 8: Validate a real OpenChargeMap ingest and open the PR

**Files:** none (verification and PR).

- [ ] **Step 1: Run a real ingest locally against a throwaway PostGIS container**

Start a PostGIS container, point the app at it, and run the CLI. NREL is unreachable
from this machine, so it will be skipped (logged), and OCM will load.

```bash
docker run -d --name dc-pg -e POSTGRES_PASSWORD=desertcharge -e POSTGRES_USER=desertcharge -e POSTGRES_DB=desertcharge -p 5433:5432 postgis/postgis:16-3.4
cd api
DATABASE_URL="postgresql+asyncpg://desertcharge:desertcharge@localhost:5433/desertcharge" uv run alembic upgrade head
DATABASE_URL="postgresql+asyncpg://desertcharge:desertcharge@localhost:5433/desertcharge" uv run python -m desertcharge.ingest.run
```
Expected: logs show `Fetched OCM=<N>` with N in the hundreds or thousands, `NREL failed` (unreachable here), and `Loaded <N> chargers.`

- [ ] **Step 2: Tear down the throwaway container**

```bash
docker rm -f dc-pg
```

- [ ] **Step 3: Push and open the PR**

```bash
git push -u origin phase-2/charger-ingest
gh pr create --base main --head phase-2/charger-ingest \
  --title "feat(api): phase 2 charger ingest (OpenChargeMap + NREL)" \
  --body "Implements Phase 2: async OCM and NREL clients, cross-source merge and dedupe, PostGIS loader, and a resilient orchestrator CLI. Client parsing is fixture-tested; the loader runs against a real PostGIS container. OpenChargeMap validated live."
```

- [ ] **Step 4: Watch CI and merge**

```bash
gh pr checks <pr-number> --watch --interval 15
gh pr merge <pr-number> --squash --delete-branch
git checkout main && git pull origin main
```

---

## Self-review

**Spec coverage (Phase 2 slice):** Spec section 9 steps 1 to 3 (fetch OCM + NREL, merge/dedupe, load raw) are covered by Tasks 3 to 7. Section 14 (keys server-side) is covered by Task 7 settings. The H3 grid build, areal weighting, scoring, best-sites, and grid.json export (section 9 steps 4 to 9) are Phase 3, out of scope here.

**Placeholder scan:** No TBD/TODO. Every code step has complete code. The `<pr-number>` and `<N>` markers in Task 8 are runtime values, not code placeholders.

**Type consistency:** `ChargerRecord` fields are identical across records.py, both parsers, merge, load, and run. `fetch_openchargemap(bbox, api_key, client)` and `fetch_nrel(bbox, api_key, client)` share the same signature, used consistently in run.py. `merge_chargers(*groups)` matches its call in run.py. `load_chargers(session, records)` matches Task 6 and Task 7 usage.

**Note:** NREL is unreachable from this dev machine (DNS), so its live fetch is validated only in CI mocks and the scheduled Action, not in the Task 8 manual run. This is expected and documented.
