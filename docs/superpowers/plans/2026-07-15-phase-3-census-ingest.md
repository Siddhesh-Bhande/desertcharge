# DesertCharge Phase 3: Census Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load tract-level population and centroids for the Desert Southwest (CA, NV, AZ) into the `census_tracts` table, using the keyless TIGERweb API.

**Architecture:** An async TIGERweb client fetches two things per state from the Tracts_Blocks map service: tract centroids (layer 0) and tract population summed from 2020 census blocks (layer 2, group by tract). They join by GEOID into a `TractRecord`. A migration reshapes `census_tracts` to hold a centroid point and population. A loader replaces the table. A CLI orchestrates the three states. No API key is required.

**Tech Stack:** httpx (async), TIGERweb ArcGIS REST, SQLAlchemy async, GeoAlchemy2, Alembic, PostGIS testcontainer.

---

## Confirmed TIGERweb behavior (verified live)

Service base: `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer`

- Layer 0 (Census Tracts): query `where=STATE='<fips>'`, `outFields=GEOID,CENTLAT,CENTLON`, `returnGeometry=false`, `f=json`. Returns features with string `CENTLAT` like `"+36.19"` and `CENTLON` like `"-115.07"`. Large result sets set `exceededTransferLimit: true`; page with `resultOffset`.
- Layer 2 (2020 Census Blocks): query `where=STATE='<fips>'`, `groupByFieldsForStatistics=STATE,COUNTY,TRACT`, `outStatistics=[{"statisticType":"sum","onStatisticField":"POP100","outStatisticFieldName":"pop"}]`, `returnGeometry=false`, `f=json`. Returns one row per tract with `STATE`, `COUNTY`, `TRACT`, and `pop`. GEOID is `STATE + COUNTY + TRACT` (2 + 3 + 6 digits).

State FIPS: CA=06, NV=32, AZ=04.

---

## File structure (Phase 3)

```
api/src/desertcharge/region.py                add REGION_STATES mapping (modify)
api/src/desertcharge/models.py                census_tracts: centroid POINT (modify)
api/migrations/versions/0002_tract_centroid.py  reshape census_tracts (create)
api/src/desertcharge/ingest/census.py         TIGERweb client + parsers (create)
api/src/desertcharge/ingest/census_load.py    load_tracts (create)
api/src/desertcharge/ingest/census_run.py     orchestrator + CLI (create)
api/tests/fixtures/tiger_centroids.json       (create)
api/tests/fixtures/tiger_population.json       (create)
api/tests/test_census.py                      (create)
api/tests/test_census_load.py                 (create)
```

---

### Task 1: Add state FIPS mapping and the TractRecord

**Files:**
- Modify: `api/src/desertcharge/region.py`
- Create: `api/src/desertcharge/ingest/census.py` (TractRecord only for now)
- Test: `api/tests/test_census.py`

- [ ] **Step 1: Add the state mapping to `region.py`**

Append to `api/src/desertcharge/region.py`:

```python
# State FIPS codes for the region, keyed by USPS abbreviation.
REGION_STATES: dict[str, str] = {"CA": "06", "NV": "32", "AZ": "04"}
```

- [ ] **Step 2: Write the failing test `api/tests/test_census.py`**

```python
from desertcharge.ingest.census import TractRecord, parse_centroids, parse_populations
from desertcharge.region import REGION_STATES


def test_region_states_are_ca_nv_az() -> None:
    assert REGION_STATES == {"CA": "06", "NV": "32", "AZ": "04"}


def test_tract_record_fields() -> None:
    record = TractRecord(geoid="32003005322", state="NV", population=1580, lat=36.1, lng=-115.0)
    assert record.geoid == "32003005322"
    assert record.population == 1580
```

- [ ] **Step 3: Run to verify failure**

Run: `cd api && uv run pytest tests/test_census.py -v`
Expected: FAIL with import error.

- [ ] **Step 4: Create `api/src/desertcharge/ingest/census.py` with the record**

```python
"""Census tract ingest from the keyless TIGERweb API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
        state, county, tract = attrs.get("STATE"), attrs.get("COUNTY"), attrs.get("TRACT")
        if state and county and tract:
            result[f"{state}{county}{tract}"] = int(attrs.get("pop") or 0)
    return result
```

- [ ] **Step 5: Run to verify pass**

Run: `cd api && uv run pytest tests/test_census.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/region.py api/src/desertcharge/ingest/census.py api/tests/test_census.py
git commit -m "feat(api): add TractRecord and TIGERweb response parsers"
```

---

### Task 2: Build tract records and the paginated fetch

**Files:**
- Modify: `api/src/desertcharge/ingest/census.py`
- Create: `api/tests/fixtures/tiger_centroids.json`, `api/tests/fixtures/tiger_population.json`
- Test: `api/tests/test_census.py`

- [ ] **Step 1: Create fixture `api/tests/fixtures/tiger_centroids.json`**

```json
{
  "exceededTransferLimit": false,
  "features": [
    {"attributes": {"GEOID": "32003005322", "CENTLAT": "+36.1000000", "CENTLON": "-115.1000000"}},
    {"attributes": {"GEOID": "32003005115", "CENTLAT": "+36.2000000", "CENTLON": "-115.2000000"}}
  ]
}
```

- [ ] **Step 2: Create fixture `api/tests/fixtures/tiger_population.json`**

```json
{
  "features": [
    {"attributes": {"STATE": "32", "COUNTY": "003", "TRACT": "005322", "pop": 1580}},
    {"attributes": {"STATE": "32", "COUNTY": "003", "TRACT": "005115", "pop": 2914}}
  ]
}
```

- [ ] **Step 3: Append failing tests to `api/tests/test_census.py`**

Add imports and tests:

```python
import json
from pathlib import Path

import httpx

from desertcharge.ingest.census import build_tract_records, fetch_tracts

FIX = Path(__file__).parent / "fixtures"


def test_build_tract_records_joins_on_geoid() -> None:
    centroids = {"32003005322": (36.1, -115.1), "32003005115": (36.2, -115.2)}
    pops = {"32003005322": 1580, "32003005115": 2914, "32999999999": 50}
    records = build_tract_records(centroids, pops, state="NV")
    # Only tracts present in both are kept.
    assert len(records) == 2
    by_id = {r.geoid: r for r in records}
    assert by_id["32003005322"].population == 1580
    assert by_id["32003005322"].lat == 36.1
    assert by_id["32003005322"].state == "NV"


async def test_fetch_tracts_queries_both_layers() -> None:
    centroids = json.loads((FIX / "tiger_centroids.json").read_text())
    populations = json.loads((FIX / "tiger_population.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "tigerweb.geo.census.gov"
        if "/0/query" in request.url.path:
            return httpx.Response(200, json=centroids)
        return httpx.Response(200, json=populations)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        records = await fetch_tracts("32", "NV", client=client)
    assert len(records) == 2
    assert sum(r.population for r in records) == 1580 + 2914
```

- [ ] **Step 4: Run to verify failure**

Run: `cd api && uv run pytest tests/test_census.py -v`
Expected: FAIL with import error for `build_tract_records`.

- [ ] **Step 5: Append implementation to `census.py`**

Add imports at the top (`import json`, `import httpx`) and append:

```python
BASE_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer"
_PAGE = 5000


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
                [{"statisticType": "sum", "onStatisticField": "POP100", "outStatisticFieldName": "pop"}]
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
```

- [ ] **Step 6: Run to verify pass**

Run: `cd api && uv run pytest tests/test_census.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add api/src/desertcharge/ingest/census.py api/tests/test_census.py api/tests/fixtures/tiger_centroids.json api/tests/fixtures/tiger_population.json
git commit -m "feat(api): add TIGERweb tract fetch with join and pagination"
```

---

### Task 3: Reshape census_tracts to a centroid point

**Files:**
- Modify: `api/src/desertcharge/models.py`
- Create: `api/migrations/versions/0002_tract_centroid.py`
- Test: `api/tests/test_models.py`

- [ ] **Step 1: Update the `CensusTract` model in `models.py`**

Replace the `CensusTract` class body's `geom` line. The class becomes:

```python
class CensusTract(Base):
    __tablename__ = "census_tracts"

    geoid: Mapped[str] = mapped_column(String(11), primary_key=True)
    state: Mapped[str] = mapped_column(String(2))
    centroid: Mapped[object] = mapped_column(Geometry("POINT", srid=4326))
    population: Mapped[int] = mapped_column(Integer, default=0)
    households: Mapped[int | None] = mapped_column(Integer)
```

- [ ] **Step 2: Add failing assertion to `api/tests/test_models.py`**

Append:

```python
def test_census_tract_has_point_centroid() -> None:
    from geoalchemy2 import Geometry

    cols = CensusTract.__table__.columns
    assert isinstance(cols["centroid"].type, Geometry)
    assert cols["centroid"].type.geometry_type == "POINT"
    assert "geom" not in cols
```

- [ ] **Step 3: Run to verify failure**

Run: `cd api && uv run pytest tests/test_models.py::test_census_tract_has_point_centroid -v`
Expected: FAIL (geom still present / centroid missing until model updated). If the model edit in Step 1 is done, this passes; run before editing to see it fail, then edit.

- [ ] **Step 4: Create migration `api/migrations/versions/0002_tract_centroid.py`**

```python
"""reshape census_tracts to a centroid point

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("census_tracts", "geom")
    op.add_column(
        "census_tracts",
        sa_column_centroid(),
    )


def downgrade() -> None:
    op.drop_column("census_tracts", "centroid")
    op.add_column(
        "census_tracts",
        op_geom_multipolygon(),
    )


def sa_column_centroid() -> object:
    import sqlalchemy as sa

    return sa.Column("centroid", geoalchemy2.Geometry("POINT", srid=4326), nullable=False)


def op_geom_multipolygon() -> object:
    import sqlalchemy as sa

    return sa.Column("geom", geoalchemy2.Geometry("MULTIPOLYGON", srid=4326), nullable=False)
```

- [ ] **Step 5: Run to verify pass**

Run: `cd api && uv run pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/models.py api/migrations/versions/0002_tract_centroid.py api/tests/test_models.py
git commit -m "feat(api): reshape census_tracts to a centroid point"
```

---

### Task 4: Load tracts into PostGIS

**Files:**
- Create: `api/src/desertcharge/ingest/census_load.py`
- Test: `api/tests/test_census_load.py`

- [ ] **Step 1: Write failing test `api/tests/test_census_load.py`**

```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.ingest.census import TractRecord
from desertcharge.ingest.census_load import load_tracts
from desertcharge.models import CensusTract


async def test_load_tracts_replaces_table(session: AsyncSession) -> None:
    first = [TractRecord("32003005322", "NV", 1580, 36.1, -115.1)]
    count = await load_tracts(session, first)
    assert count == 1

    total_pop = await session.scalar(select(func.sum(CensusTract.population)))
    assert total_pop == 1580

    second = [
        TractRecord("32003005115", "NV", 2914, 36.2, -115.2),
        TractRecord("04013010101", "AZ", 5000, 33.4, -112.0),
    ]
    count = await load_tracts(session, second)
    assert count == 2
    total_rows = await session.scalar(select(func.count()).select_from(CensusTract))
    assert total_rows == 2
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && uv run pytest tests/test_census_load.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Write `api/src/desertcharge/ingest/census_load.py`**

```python
"""Load tract records into the PostGIS census_tracts table (full replace)."""

from __future__ import annotations

from collections.abc import Sequence

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.ingest.census import TractRecord
from desertcharge.models import CensusTract


def _to_model(record: TractRecord) -> CensusTract:
    return CensusTract(
        geoid=record.geoid,
        state=record.state,
        centroid=WKTElement(f"POINT({record.lng} {record.lat})", srid=4326),
        population=record.population,
    )


async def load_tracts(session: AsyncSession, records: Sequence[TractRecord]) -> int:
    """Replace the census_tracts table with the given records. Returns row count."""
    await session.execute(delete(CensusTract))
    session.add_all([_to_model(record) for record in records])
    await session.commit()
    return len(records)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd api && uv run pytest tests/test_census_load.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/desertcharge/ingest/census_load.py api/tests/test_census_load.py
git commit -m "feat(api): add census tracts loader"
```

---

### Task 5: Orchestrator CLI and real validation

**Files:**
- Create: `api/src/desertcharge/ingest/census_run.py`

- [ ] **Step 1: Write `api/src/desertcharge/ingest/census_run.py`**

```python
"""Orchestrate the census ingest across the region's states."""

from __future__ import annotations

import asyncio
import logging

import httpx

from desertcharge.db import create_engine_from_settings, create_session_factory
from desertcharge.ingest.census import TractRecord, fetch_tracts
from desertcharge.ingest.census_load import load_tracts
from desertcharge.region import REGION_STATES

logger = logging.getLogger(__name__)


async def ingest_census() -> int:
    """Fetch tracts for every region state and load them. Returns rows loaded."""
    records: list[TractRecord] = []
    async with httpx.AsyncClient() as client:
        for state, fips in REGION_STATES.items():
            state_records = await fetch_tracts(fips, state, client)
            logger.info("Fetched %s tracts=%d", state, len(state_records))
            records.extend(state_records)

    engine = create_engine_from_settings()
    factory = create_session_factory(engine)
    async with factory() as session:
        count = await load_tracts(session, records)
    await engine.dispose()
    return count


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    count = asyncio.run(ingest_census())
    logger.info("Loaded %d tracts.", count)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Full check**

Run:
```bash
cd api && uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest
```
Expected: all pass.

- [ ] **Step 3: Real validation against a throwaway PostGIS container**

```bash
docker run -d --name dc-pg -e POSTGRES_PASSWORD=desertcharge -e POSTGRES_USER=desertcharge -e POSTGRES_DB=desertcharge -p 5433:5432 postgis/postgis:16-3.4
cd api
DATABASE_URL="postgresql+asyncpg://desertcharge:desertcharge@localhost:5433/desertcharge" uv run alembic upgrade head
DATABASE_URL="postgresql+asyncpg://desertcharge:desertcharge@localhost:5433/desertcharge" uv run python -m desertcharge.ingest.census_run
docker rm -f dc-pg
```
Expected: logs show tracts for CA, NV, AZ (roughly 9000, 780, 1770) and a loaded total near 11,500 with total population near 49 million.

- [ ] **Step 4: Commit**

```bash
git add api/src/desertcharge/ingest/census_run.py
git commit -m "feat(api): add census ingest orchestrator and CLI"
```

- [ ] **Step 5: Push and open the PR**

```bash
git push -u origin phase-3/census-ingest
gh pr create --base main --head phase-3/census-ingest \
  --title "feat(api): phase 3 census ingest (TIGERweb, keyless)" \
  --body "Loads tract population and centroids for CA, NV, AZ from the keyless TIGERweb API into census_tracts. Population is summed from 2020 census blocks per tract; centroids come from the tract layer. Parsers are fixture-tested; the loader runs against a real PostGIS container; a real run loads ~11,500 tracts."
```

- [ ] **Step 6: Watch CI and merge**

```bash
gh pr checks <pr-number> --watch --interval 15
gh pr merge <pr-number> --squash --delete-branch
git checkout main && git pull origin main
```

---

## Self-review

**Spec coverage (Phase 3 slice):** Spec section 9 step 2 (Census tract population and geometry) is covered, using centroids and block-summed population instead of ACS + polygons, which is a keyless simplification noted below. The H3 grid build, scoring, best sites, and grid.json export (section 9 steps 4 to 9) are Phase 4.

**Placeholder scan:** No TBD/TODO. Every code step has complete code. `<pr-number>` in Task 5 is a runtime value.

**Type consistency:** `TractRecord(geoid, state, population, lat, lng)` is identical across census.py, census_load.py, census_run.py, and the tests. `fetch_tracts(fips, state, client)`, `build_tract_records(centroids, populations, state)`, `parse_centroids`, and `parse_populations` signatures match between definition and use. `load_tracts(session, records)` matches its call in census_run.py.

**Simplifications (documented):** Population uses 2020 decennial block counts summed to tracts (not ACS 5-year estimates), and demand is assigned by tract centroid (not areal-weighted polygons). Both are keyless and adequate for the demo desert score; either can be upgraded later. The `households` column is retained but unused for now.
