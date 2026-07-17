# DesertCharge Phase 4: Grid Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the loaded chargers and census tracts into the scored H3 grid (`hex_scores`), rank `best_sites`, and export `grid.json` for the heat layer.

**Architecture:** Demand is aggregated from tract centroids into H3 cells (pure). For each populated hex, supply is measured against PostGIS (nearest DC fast distance, weighted DC fast ports within 10 miles), then the Phase 1 scoring engine produces the desert score. Best sites are the highest-scoring hexes. `grid.json` is the compact `{h3, score}` array the frontend heat layer consumes. A CLI runs the whole build.

**Tech Stack:** h3, SQLAlchemy async, GeoAlchemy2/PostGIS, the Phase 1 `scoring` and `queries` modules.

---

## File structure (Phase 4)

```
api/src/desertcharge/grid/__init__.py       (create)
api/src/desertcharge/grid/demand.py          hex population + hex WKT helpers (create)
api/src/desertcharge/grid/supply.py          weighted DC fast ports query (create)
api/src/desertcharge/grid/build.py           build_hex_scores (create)
api/src/desertcharge/grid/best_sites.py      rank_best_sites (create)
api/src/desertcharge/grid/export.py          export_grid_json (create)
api/src/desertcharge/grid/run.py             orchestrator + CLI (create)
api/tests/test_grid_demand.py                (create)
api/tests/test_grid_build.py                 (create)
api/tests/test_grid_best_sites.py            (create)
api/tests/test_grid_export.py                (create)
```

---

### Task 1: Hex demand aggregation and geometry helpers

**Files:**
- Create: `api/src/desertcharge/grid/__init__.py`, `api/src/desertcharge/grid/demand.py`
- Test: `api/tests/test_grid_demand.py`

- [ ] **Step 1: Write failing test `api/tests/test_grid_demand.py`**

```python
from desertcharge.grid.demand import hex_polygon_wkt, hex_populations
from desertcharge.h3grid import point_to_cell
from desertcharge.ingest.census import TractRecord


def test_hex_populations_aggregates_by_cell() -> None:
    # Two tracts very close together share a hex; a far one does not.
    near_a = TractRecord("t1", "NV", 100, 36.100, -115.100)
    near_b = TractRecord("t2", "NV", 250, 36.101, -115.101)
    far = TractRecord("t3", "NV", 400, 40.000, -119.000)
    pops = hex_populations([near_a, near_b, far])
    cell = point_to_cell(36.100, -115.100)
    assert pops[cell] == 350
    assert len(pops) == 2


def test_hex_polygon_wkt_is_closed_polygon() -> None:
    cell = point_to_cell(36.1, -115.1)
    wkt = hex_polygon_wkt(cell)
    assert wkt.startswith("POLYGON((")
    assert wkt.endswith("))")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && uv run pytest tests/test_grid_demand.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Create `api/src/desertcharge/grid/__init__.py`**

```python
"""Grid build: aggregate demand, measure supply, score hexes, export."""
```

- [ ] **Step 4: Create `api/src/desertcharge/grid/demand.py`**

```python
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
```

- [ ] **Step 5: Run to verify pass**

Run: `cd api && uv run pytest tests/test_grid_demand.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/grid/__init__.py api/src/desertcharge/grid/demand.py api/tests/test_grid_demand.py
git commit -m "feat(api): add hex demand aggregation and geometry helpers"
```

---

### Task 2: Weighted DC fast ports supply query

**Files:**
- Create: `api/src/desertcharge/grid/supply.py`
- Test: `api/tests/test_grid_build.py` (supply part)

- [ ] **Step 1: Write failing test `api/tests/test_grid_build.py`**

```python
from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.grid.supply import weighted_dc_fast_ports_within
from desertcharge.models import Charger


async def _add_charger(
    session: AsyncSession, lat: float, lng: float, *, dc: bool, ports: int
) -> None:
    session.add(
        Charger(
            source="test",
            source_id=f"{lat},{lng}",
            name="t",
            geom=WKTElement(f"POINT({lng} {lat})", srid=4326),
            power_kw=150.0 if dc else 7.0,
            num_ports=ports,
            is_dc_fast=dc,
        )
    )
    await session.flush()


async def test_weighted_ports_counts_only_dc_fast_within_radius(
    session: AsyncSession,
) -> None:
    await _add_charger(session, 35.0, -116.0, dc=True, ports=4)  # on the point
    await _add_charger(session, 35.0, -116.0, dc=False, ports=9)  # slow, ignored
    await _add_charger(session, 36.0, -116.0, dc=True, ports=5)  # ~111 km away, outside
    weighted = await weighted_dc_fast_ports_within(session, 35.0, -116.0, 16093.0)
    assert weighted == 4.0
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && uv run pytest tests/test_grid_build.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Create `api/src/desertcharge/grid/supply.py`**

```python
"""Supply-side spatial measures over the chargers table."""

from __future__ import annotations

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.models import Charger


async def weighted_dc_fast_ports_within(
    session: AsyncSession, lat: float, lng: float, meters: float
) -> float:
    """Return the summed DC fast port count within `meters` of the point.

    Each charger contributes its port count (defaulting to 1 when unknown).
    """
    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    ports = func.coalesce(Charger.num_ports, 1)
    stmt = select(func.coalesce(func.sum(ports), 0)).where(
        Charger.is_dc_fast.is_(True),
        func.ST_DWithin(cast(Charger.geom, Geography), cast(point, Geography), meters),
    )
    return float(await session.scalar(stmt) or 0)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd api && uv run pytest tests/test_grid_build.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/desertcharge/grid/supply.py api/tests/test_grid_build.py
git commit -m "feat(api): add weighted DC fast ports supply query"
```

---

### Task 3: Build the scored hex grid

**Files:**
- Create: `api/src/desertcharge/grid/build.py`
- Test: `api/tests/test_grid_build.py`

- [ ] **Step 1: Append failing test to `api/tests/test_grid_build.py`**

```python
from sqlalchemy import func, select

from desertcharge.grid.build import build_hex_scores
from desertcharge.h3grid import point_to_cell
from desertcharge.ingest.census_load import load_tracts
from desertcharge.ingest.census import TractRecord
from desertcharge.models import HexScore


async def test_build_hex_scores_scores_a_desert_and_a_served_hex(
    session: AsyncSession,
) -> None:
    # A populated hex with a nearby DC fast charger (served) and one with none (desert).
    served = TractRecord("s1", "NV", 5000, 36.100, -115.100)
    desert = TractRecord("d1", "NV", 5000, 37.500, -117.500)
    await load_tracts(session, [served, desert])
    await _add_charger(session, 36.100, -115.100, dc=True, ports=6)  # at the served hex

    count = await build_hex_scores(session)
    assert count == 2

    served_cell = point_to_cell(36.100, -115.100)
    desert_cell = point_to_cell(37.500, -117.500)
    scores = dict(
        (await session.execute(select(HexScore.h3_index, HexScore.desert_score))).all()
    )
    assert scores[served_cell] < scores[desert_cell]
    assert scores[desert_cell] > 50  # far from any charger, real demand
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && uv run pytest tests/test_grid_build.py -v`
Expected: FAIL with import error for `build_hex_scores`.

- [ ] **Step 3: Create `api/src/desertcharge/grid/build.py`**

```python
"""Build the scored hex grid from tracts and chargers."""

from __future__ import annotations

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.grid.demand import hex_populations, hex_polygon_wkt
from desertcharge.grid.supply import weighted_dc_fast_ports_within
from desertcharge.h3grid import cell_centroid
from desertcharge.ingest.census import TractRecord
from desertcharge.models import CensusTract, HexScore
from desertcharge.queries import nearest_dc_fast_distance_m
from desertcharge.scoring import score_hex

TEN_MILES_M = 16093.4
METERS_PER_MILE = 1609.34
NO_CHARGER_MILES = 9999.0


async def _load_tract_records(session: AsyncSession) -> list[TractRecord]:
    stmt = select(
        CensusTract.geoid,
        CensusTract.state,
        CensusTract.population,
        func.ST_Y(CensusTract.centroid),
        func.ST_X(CensusTract.centroid),
    )
    rows = await session.execute(stmt)
    return [
        TractRecord(geoid=geoid, state=state, population=pop, lat=lat, lng=lng)
        for geoid, state, pop, lat, lng in rows
    ]


async def build_hex_scores(session: AsyncSession) -> int:
    """Aggregate demand, measure supply per hex, score, and replace hex_scores."""
    tracts = await _load_tract_records(session)
    populations = hex_populations(tracts)
    if not populations:
        return 0

    pop_min = float(min(populations.values()))
    pop_max = float(max(populations.values()))

    await session.execute(delete(HexScore))
    for cell, population in populations.items():
        lat, lng = cell_centroid(cell)
        nearest_m = await nearest_dc_fast_distance_m(session, lat, lng)
        weighted = await weighted_dc_fast_ports_within(session, lat, lng, TEN_MILES_M)
        nearest_miles = (
            nearest_m / METERS_PER_MILE if nearest_m is not None else NO_CHARGER_MILES
        )
        result = score_hex(
            population=float(population),
            pop_min=pop_min,
            pop_max=pop_max,
            nearest_dc_fast_miles=nearest_miles,
            weighted_chargers_10mi=weighted,
        )
        session.add(
            HexScore(
                h3_index=cell,
                geom=WKTElement(hex_polygon_wkt(cell), srid=4326),
                centroid=WKTElement(f"POINT({lng} {lat})", srid=4326),
                population=float(population),
                nearest_dc_fast_m=nearest_m,
                weighted_chargers_10mi=weighted,
                desert_score=result.score,
            )
        )
    await session.commit()
    return len(populations)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd api && uv run pytest tests/test_grid_build.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/desertcharge/grid/build.py api/tests/test_grid_build.py
git commit -m "feat(api): build the scored hex grid from tracts and chargers"
```

---

### Task 4: Rank best sites

**Files:**
- Create: `api/src/desertcharge/grid/best_sites.py`
- Test: `api/tests/test_grid_best_sites.py`

- [ ] **Step 1: Write failing test `api/tests/test_grid_best_sites.py`**

```python
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.grid.best_sites import rank_best_sites
from desertcharge.models import BestSite, HexScore


async def _add_hex(session: AsyncSession, cell: str, score: int, pop: float) -> None:
    session.add(
        HexScore(
            h3_index=cell,
            geom=WKTElement("POLYGON((0 0,0 1,1 1,1 0,0 0))", srid=4326),
            centroid=WKTElement("POINT(-116 35)", srid=4326),
            population=pop,
            nearest_dc_fast_m=50000.0,
            weighted_chargers_10mi=0.0,
            desert_score=score,
        )
    )
    await session.flush()


async def test_rank_best_sites_takes_top_scoring_hexes(session: AsyncSession) -> None:
    await _add_hex(session, "aaa", 90, 12000)
    await _add_hex(session, "bbb", 70, 8000)
    await _add_hex(session, "ccc", 10, 3000)

    count = await rank_best_sites(session, limit=2)
    assert count == 2

    sites = (
        await session.execute(select(BestSite).order_by(BestSite.rank))
    ).scalars().all()
    assert [s.h3_index for s in sites] == ["aaa", "bbb"]
    assert sites[0].rank == 1
    assert sites[0].est_population_served == 12000
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && uv run pytest tests/test_grid_best_sites.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Create `api/src/desertcharge/grid/best_sites.py`**

```python
"""Rank the highest-need hexes as suggested charger sites."""

from __future__ import annotations

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.h3grid import cell_centroid
from desertcharge.models import BestSite, HexScore

METERS_PER_MILE = 1609.34


async def rank_best_sites(session: AsyncSession, limit: int = 10) -> int:
    """Replace best_sites with the top-scoring underserved hexes. Returns row count."""
    stmt = (
        select(HexScore)
        .order_by(HexScore.desert_score.desc(), HexScore.population.desc())
        .limit(limit)
    )
    hexes = (await session.execute(stmt)).scalars().all()

    await session.execute(delete(BestSite))
    for rank, hex_row in enumerate(hexes, start=1):
        gap_miles = (
            hex_row.nearest_dc_fast_m / METERS_PER_MILE
            if hex_row.nearest_dc_fast_m is not None
            else 0.0
        )
        population = int(hex_row.population)
        lat, lng = cell_centroid(hex_row.h3_index)
        session.add(
            BestSite(
                h3_index=hex_row.h3_index,
                geom=WKTElement(f"POINT({lng} {lat})", srid=4326),
                rank=rank,
                est_population_served=population,
                gap_miles_closed=gap_miles,
                reason=(
                    f"A charger here would serve about {population:,} people "
                    f"and close a {gap_miles:.0f} mile gap."
                ),
            )
        )
    await session.commit()
    return len(hexes)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd api && uv run pytest tests/test_grid_best_sites.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/desertcharge/grid/best_sites.py api/tests/test_grid_best_sites.py
git commit -m "feat(api): rank best charger sites from the scored grid"
```

---

### Task 5: Export grid.json

**Files:**
- Create: `api/src/desertcharge/grid/export.py`
- Test: `api/tests/test_grid_export.py`

- [ ] **Step 1: Write failing test `api/tests/test_grid_export.py`**

```python
import json
from pathlib import Path

from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.grid.export import export_grid_json
from desertcharge.models import HexScore


async def test_export_grid_json_writes_h3_score_array(
    session: AsyncSession, tmp_path: Path
) -> None:
    session.add(
        HexScore(
            h3_index="aaa",
            geom=WKTElement("POLYGON((0 0,0 1,1 1,1 0,0 0))", srid=4326),
            centroid=WKTElement("POINT(-116 35)", srid=4326),
            population=1000.0,
            weighted_chargers_10mi=0.0,
            desert_score=88,
        )
    )
    await session.commit()

    out = tmp_path / "grid.json"
    count = await export_grid_json(session, out)
    assert count == 1
    data = json.loads(out.read_text())
    assert data == [{"h3": "aaa", "score": 88}]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd api && uv run pytest tests/test_grid_export.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Create `api/src/desertcharge/grid/export.py`**

```python
"""Export the scored grid as a compact JSON array for the heat layer."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.models import HexScore


async def export_grid_json(session: AsyncSession, path: Path) -> int:
    """Write [{h3, score}, ...] for every scored hex. Returns the record count."""
    rows = await session.execute(select(HexScore.h3_index, HexScore.desert_score))
    data = [{"h3": h3, "score": score} for h3, score in rows]
    path.write_text(json.dumps(data, separators=(",", ":")))
    return len(data)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd api && uv run pytest tests/test_grid_export.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/desertcharge/grid/export.py api/tests/test_grid_export.py
git commit -m "feat(api): export the scored grid as grid.json"
```

---

### Task 6: Orchestrator CLI and real validation

**Files:**
- Create: `api/src/desertcharge/grid/run.py`

- [ ] **Step 1: Create `api/src/desertcharge/grid/run.py`**

```python
"""Orchestrate the grid build: hex scores, best sites, and grid.json export."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from desertcharge.db import create_engine_from_settings, create_session_factory
from desertcharge.grid.best_sites import rank_best_sites
from desertcharge.grid.build import build_hex_scores
from desertcharge.grid.export import export_grid_json

logger = logging.getLogger(__name__)

DEFAULT_GRID_PATH = Path("grid.json")


async def build_grid(grid_path: Path = DEFAULT_GRID_PATH) -> tuple[int, int, int]:
    """Build hex scores, rank best sites, and export the grid. Returns their counts."""
    engine = create_engine_from_settings()
    factory = create_session_factory(engine)
    async with factory() as session:
        hexes = await build_hex_scores(session)
        sites = await rank_best_sites(session)
        exported = await export_grid_json(session, grid_path)
    await engine.dispose()
    return hexes, sites, exported


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    hexes, sites, exported = asyncio.run(build_grid())
    logger.info("Built hex_scores=%d best_sites=%d grid.json=%d", hexes, sites, exported)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Full check**

Run:
```bash
cd api && uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest
```
Expected: all pass.

- [ ] **Step 3: Real validation (chargers + census + grid) against a throwaway container**

```bash
docker run -d --name dc-pg -e POSTGRES_PASSWORD=desertcharge -e POSTGRES_USER=desertcharge -e POSTGRES_DB=desertcharge -p 5433:5432 postgis/postgis:16-3.4
# wait for readiness, then:
cd api
export DATABASE_URL="postgresql+asyncpg://desertcharge:desertcharge@localhost:5433/desertcharge"
uv run alembic upgrade head
uv run python -m desertcharge.ingest.run          # chargers
uv run python -m desertcharge.ingest.census_run   # census
uv run python -m desertcharge.grid.run            # scores + best sites + grid.json
# spot-check: Baker area should score high (desert), an LA hex low (served)
docker rm -f dc-pg
```
Expected: hex_scores in the thousands, best_sites=10, grid.json written; desert areas score high, urban areas low.

- [ ] **Step 4: Commit**

```bash
git add api/src/desertcharge/grid/run.py
git commit -m "feat(api): add grid build orchestrator and CLI"
```

- [ ] **Step 5: Push, open PR, watch CI, merge**

```bash
git push -u origin phase-4/grid-scoring
gh pr create --base main --head phase-4/grid-scoring --title "feat(api): phase 4 grid scoring (hex_scores, best_sites, grid.json)" --body "..."
gh pr checks <pr-number> --watch --interval 15
gh pr merge <pr-number> --squash --delete-branch
git checkout main && git pull origin main
```

---

## Self-review

**Spec coverage (Phase 4 slice):** Spec section 5 (desert-score method, H3 grid, best sites) and section 9 steps 4 to 9 (grid build, per-hex supply, scoring, best-site ranking, grid export) are covered by Tasks 1 to 6. The `grid.json` filtered to populated hexes falls out naturally because only populated hexes become `hex_scores` rows.

**Placeholder scan:** No TBD/TODO. Every code step has complete code. `<pr-number>` is a runtime value.

**Type consistency:** `hex_populations(tracts) -> dict[str, int]` and `hex_polygon_wkt(cell) -> str` match across demand.py, build.py, and tests. `weighted_dc_fast_ports_within(session, lat, lng, meters)` matches between supply.py and build.py. `build_hex_scores`, `rank_best_sites(session, limit)`, and `export_grid_json(session, path)` match between their modules, run.py, and tests. `TractRecord` and `score_hex` reuse the Phase 1 and Phase 3 signatures unchanged.

**Performance note:** `build_hex_scores` runs two PostGIS queries per populated hex. With a few thousand hexes this is tens of seconds offline, which is acceptable for a scheduled batch. If it becomes a bottleneck, replace the per-hex loop with a set-based LATERAL join.
