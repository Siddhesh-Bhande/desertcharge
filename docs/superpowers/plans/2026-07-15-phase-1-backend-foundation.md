# DesertCharge Phase 1: Backend Foundation and Scoring Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Python backend project to best-standard structure and build the pure scoring engine, H3 grid utilities, database schema, and one spatial query, all test-driven, plus the CI job that gates them.

**Architecture:** A `api/` package (uv-managed, src layout) holds the backend. Phase 1 delivers the intellectual core (the desert-score functions and H3 helpers) as pure, fully unit-tested functions with no I/O, then the SQLAlchemy 2.0 async models and an Alembic migration that enables PostGIS and creates the tables, verified against a real PostGIS container. External data ingest and the HTTP API are later phases; this phase is self-contained and testable in isolation.

**Tech Stack:** Python 3.12, uv, Ruff (lint + format), mypy (strict), pytest, SQLAlchemy 2.0 (async, asyncpg), GeoAlchemy2, Alembic (sync via psycopg2), h3 v4, shapely, pydantic-settings, testcontainers (PostGIS), GitHub Actions.

---

## Phased roadmap (context; only Phase 1 is detailed below)

Each phase is its own plan, merged via its own PR, green CI required. Dependency order:

1. **Backend foundation + scoring engine** (this plan): project scaffold, scoring functions, H3 utils, DB schema + migration, one spatial query, Python CI job.
2. **Data ingest pipeline**: fetch OpenChargeMap + NREL + Census, transform (areal weighting, H3 grid, scoring), load to PostGIS, export `grid.json`; scheduled GitHub Action that also keep-warms the API.
3. **HTTP API**: FastAPI endpoints (`/score`, `/chargers`, `/best-sites`, `/route`, `/geocode`, `/health`), rate limiting, tests, deploy to Fly.io.
4. **Frontend foundation**: Vite + React + TS scaffold, tokens to Tailwind theme, MapLibre + PMTiles basemap, app shell, frontend CI, deploy to Vercel.
5. **Core loop UI**: search/geocode, locate, score bottom sheet with the hex gauge, nearby chargers list.
6. **Charger layer + filters**.
7. **deck.gl heat layer + best-site markers**.
8. **Route/corridor + accessibility/performance pass + case-study README**.

---

## File structure (Phase 1)

Created under the repo root:

```
api/
  pyproject.toml                      project metadata, deps, tool config (ruff, mypy, pytest)
  README.md                           how to run the backend locally
  alembic.ini                         alembic config
  migrations/
    env.py                            alembic environment (sync engine)
    script.py.mako                    alembic template
    versions/
      0001_initial.py                 enable postgis, create tables + spatial indexes
  src/desertcharge/
    __init__.py
    config.py                         pydantic-settings Settings (DATABASE_URL, etc.)
    db.py                             async engine + session factory
    models.py                         SQLAlchemy 2.0 models: Charger, CensusTract, HexScore, BestSite
    scoring.py                        pure scoring functions + band/label mapping
    h3grid.py                         H3 helpers: point->cell, cell boundary, bbox fill
    queries.py                        spatial query: nearest DC fast charger distance
  tests/
    __init__.py
    conftest.py                       testcontainers PostGIS fixture + migrated session
    test_scoring.py
    test_h3grid.py
    test_models.py
    test_queries.py
.github/workflows/ci.yml              add the `backend` job (modify existing file)
```

Responsibilities are one-per-file: `scoring.py` is pure math, `h3grid.py` is pure geometry, `models.py` is schema only, `queries.py` is spatial SQL, `db.py` is connection wiring, `config.py` is settings.

---

### Task 1: Scaffold the backend project

**Files:**
- Create: `api/pyproject.toml`
- Create: `api/src/desertcharge/__init__.py`
- Create: `api/tests/__init__.py`
- Create: `api/README.md`

- [ ] **Step 1: Create `api/pyproject.toml`**

```toml
[project]
name = "desertcharge"
version = "0.1.0"
description = "DesertCharge backend: scoring engine, data pipeline, and API."
requires-python = ">=3.12"
dependencies = [
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29",
    "geoalchemy2>=0.15",
    "alembic>=1.13",
    "psycopg2-binary>=2.9",
    "h3>=4.1",
    "shapely>=2.0",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
]

[dependency-groups]
dev = [
    "ruff>=0.5",
    "mypy>=1.10",
    "pytest>=8.2",
    "pytest-cov>=5.0",
    "pytest-asyncio>=0.23",
    "testcontainers[postgres]>=4.5",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/desertcharge"]

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
mypy_path = "src"
files = ["src", "tests"]

[[tool.mypy.overrides]]
module = ["h3.*", "geoalchemy2.*", "testcontainers.*", "shapely.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create the package and test init files**

`api/src/desertcharge/__init__.py`:

```python
"""DesertCharge backend package."""

__all__: list[str] = []
```

`api/tests/__init__.py`:

```python
```

- [ ] **Step 3: Create `api/README.md`**

```markdown
# DesertCharge backend

Python backend: the desert-score engine, data pipeline, and API.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker (tests spin up a PostGIS container)

## Setup

```bash
cd api
uv sync
```

## Checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```
```

- [ ] **Step 4: Install and verify the toolchain**

Run:
```bash
cd api && uv sync
```
Expected: a `.venv` is created and dependencies resolve without error.

- [ ] **Step 5: Verify lint, format, and type check run clean on the empty scaffold**

Run:
```bash
cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy
```
Expected: all three pass (no files to fail yet).

- [ ] **Step 6: Commit**

```bash
git checkout -b phase-1/backend-foundation
git add api/pyproject.toml api/src/desertcharge/__init__.py api/tests/__init__.py api/README.md
git commit -m "chore(api): scaffold backend project with uv, ruff, mypy, pytest"
```

---

### Task 2: Score band and label mapping

The desert-score scale from the spec and design tokens: 0-20 served, 21-40 good, 41-60 moderate, 61-80 poor, 81-100 desert. Each band has a color from `docs/design/design-tokens.md`.

**Files:**
- Create: `api/src/desertcharge/scoring.py`
- Test: `api/tests/test_scoring.py`

- [ ] **Step 1: Write the failing test**

`api/tests/test_scoring.py`:

```python
from desertcharge.scoring import ScoreBand, band_for_score


def test_band_for_score_boundaries() -> None:
    assert band_for_score(0) is ScoreBand.SERVED
    assert band_for_score(20) is ScoreBand.SERVED
    assert band_for_score(21) is ScoreBand.GOOD
    assert band_for_score(40) is ScoreBand.GOOD
    assert band_for_score(41) is ScoreBand.MODERATE
    assert band_for_score(60) is ScoreBand.MODERATE
    assert band_for_score(61) is ScoreBand.POOR
    assert band_for_score(80) is ScoreBand.POOR
    assert band_for_score(81) is ScoreBand.DESERT
    assert band_for_score(100) is ScoreBand.DESERT


def test_band_label_and_color() -> None:
    assert ScoreBand.SERVED.label == "served"
    assert ScoreBand.SERVED.color == "#1B9E8A"
    assert ScoreBand.DESERT.label == "desert"
    assert ScoreBand.DESERT.color == "#B23A24"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && uv run pytest tests/test_scoring.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError: cannot import name 'ScoreBand'`.

- [ ] **Step 3: Write minimal implementation**

`api/src/desertcharge/scoring.py`:

```python
"""Pure desert-score functions and band mapping. No I/O."""

from __future__ import annotations

from enum import Enum


class ScoreBand(Enum):
    """A desert-score band, with its display label and token color."""

    SERVED = ("served", "#1B9E8A")
    GOOD = ("good", "#7FB069")
    MODERATE = ("moderate", "#E6B23A")
    POOR = ("poor", "#D57A33")
    DESERT = ("desert", "#B23A24")

    def __init__(self, label: str, color: str) -> None:
        self.label = label
        self.color = color


def band_for_score(score: int) -> ScoreBand:
    """Return the band for a 0-100 desert score."""
    if score <= 20:
        return ScoreBand.SERVED
    if score <= 40:
        return ScoreBand.GOOD
    if score <= 60:
        return ScoreBand.MODERATE
    if score <= 80:
        return ScoreBand.POOR
    return ScoreBand.DESERT
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && uv run pytest tests/test_scoring.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add api/src/desertcharge/scoring.py api/tests/test_scoring.py
git commit -m "feat(api): add desert-score band and label mapping"
```

---

### Task 3: Score math functions

Implements the spec formula:
```
demand_norm  = normalize(population, pop_min, pop_max)   # 0..1
access       = min(1, weighted_chargers_10mi / 3)        # 0..1 higher is better
distance_gap = clamp(nearest_dc_fast_miles / 30, 0, 1)   # 30 mi = full gap
supply_gap   = 0.5 * distance_gap + 0.5 * (1 - access)
desert_score = round(100 * sqrt(demand_norm) * supply_gap)
```

**Files:**
- Modify: `api/src/desertcharge/scoring.py`
- Test: `api/tests/test_scoring.py`

- [ ] **Step 1: Write the failing tests (append to the test file)**

Append to `api/tests/test_scoring.py`:

```python
import math

import pytest

from desertcharge.scoring import clamp, desert_score, normalize, supply_gap


def test_clamp() -> None:
    assert clamp(-1.0, 0.0, 1.0) == 0.0
    assert clamp(0.5, 0.0, 1.0) == 0.5
    assert clamp(2.0, 0.0, 1.0) == 1.0


def test_normalize_basic() -> None:
    assert normalize(50.0, 0.0, 100.0) == 0.5
    assert normalize(0.0, 0.0, 100.0) == 0.0
    assert normalize(100.0, 0.0, 100.0) == 1.0


def test_normalize_degenerate_range_returns_zero() -> None:
    assert normalize(5.0, 5.0, 5.0) == 0.0


def test_normalize_clamps_outside_range() -> None:
    assert normalize(-10.0, 0.0, 100.0) == 0.0
    assert normalize(150.0, 0.0, 100.0) == 1.0


def test_supply_gap_far_and_empty_is_worst() -> None:
    # 30+ miles away, zero chargers -> full supply gap
    assert supply_gap(nearest_dc_fast_miles=40.0, weighted_chargers_10mi=0.0) == 1.0


def test_supply_gap_close_and_dense_is_best() -> None:
    # on top of chargers, 3+ weighted ports within 10mi -> no supply gap
    assert supply_gap(nearest_dc_fast_miles=0.0, weighted_chargers_10mi=3.0) == 0.0


def test_desert_score_high_demand_no_supply() -> None:
    # full demand, full supply gap -> 100
    score = desert_score(
        population=1000.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=40.0,
        weighted_chargers_10mi=0.0,
    )
    assert score == 100


def test_desert_score_zero_demand_is_zero() -> None:
    # no people means it is not a charging desert regardless of supply
    score = desert_score(
        population=0.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=40.0,
        weighted_chargers_10mi=0.0,
    )
    assert score == 0


def test_desert_score_matches_formula() -> None:
    demand_norm = 0.25
    gap = supply_gap(nearest_dc_fast_miles=15.0, weighted_chargers_10mi=1.5)
    expected = round(100 * math.sqrt(demand_norm) * gap)
    score = desert_score(
        population=250.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=15.0,
        weighted_chargers_10mi=1.5,
    )
    assert score == expected


def test_desert_score_is_bounded_0_100() -> None:
    score = desert_score(
        population=1_000_000.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=999.0,
        weighted_chargers_10mi=0.0,
    )
    assert 0 <= score <= 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd api && uv run pytest tests/test_scoring.py -v`
Expected: FAIL with `ImportError: cannot import name 'clamp'`.

- [ ] **Step 3: Write the implementation (append to `scoring.py`)**

Append to `api/src/desertcharge/scoring.py`:

```python
import math

ACCESS_TARGET_PORTS = 3.0
FULL_GAP_MILES = 30.0


def clamp(value: float, low: float, high: float) -> float:
    """Constrain value to the inclusive range [low, high]."""
    return max(low, min(high, value))


def normalize(value: float, low: float, high: float) -> float:
    """Min-max normalize value into [0, 1]. A degenerate range maps to 0."""
    if high <= low:
        return 0.0
    return clamp((value - low) / (high - low), 0.0, 1.0)


def supply_gap(nearest_dc_fast_miles: float, weighted_chargers_10mi: float) -> float:
    """Return the 0..1 supply shortfall. Higher means worse coverage."""
    distance_gap = clamp(nearest_dc_fast_miles / FULL_GAP_MILES, 0.0, 1.0)
    access = min(1.0, weighted_chargers_10mi / ACCESS_TARGET_PORTS)
    return 0.5 * distance_gap + 0.5 * (1.0 - access)


def desert_score(
    population: float,
    pop_min: float,
    pop_max: float,
    nearest_dc_fast_miles: float,
    weighted_chargers_10mi: float,
) -> int:
    """Return the 0-100 desert score for one hex's inputs."""
    demand_norm = normalize(population, pop_min, pop_max)
    gap = supply_gap(nearest_dc_fast_miles, weighted_chargers_10mi)
    return round(100 * math.sqrt(demand_norm) * gap)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd api && uv run pytest tests/test_scoring.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Type check and lint**

Run: `cd api && uv run mypy && uv run ruff check .`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/scoring.py api/tests/test_scoring.py
git commit -m "feat(api): add desert-score math (normalize, supply gap, score)"
```

---

### Task 4: Composite hex scoring result

A single entry point returning the score plus the human-facing factors and band, so later phases (API, ingest) share one implementation.

**Files:**
- Modify: `api/src/desertcharge/scoring.py`
- Test: `api/tests/test_scoring.py`

- [ ] **Step 1: Write the failing test (append)**

Append to `api/tests/test_scoring.py`:

```python
from desertcharge.scoring import HexScoreResult, score_hex


def test_score_hex_returns_result_with_factors() -> None:
    result = score_hex(
        population=250.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=41.0,
        weighted_chargers_10mi=0.0,
    )
    assert isinstance(result, HexScoreResult)
    assert 0 <= result.score <= 100
    assert result.band.label in {"served", "good", "moderate", "poor", "desert"}
    assert result.nearest_dc_fast_miles == 41.0
    assert result.chargers_10mi == 0.0
    assert result.population == 250.0


def test_score_hex_band_matches_score() -> None:
    result = score_hex(
        population=1000.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=40.0,
        weighted_chargers_10mi=0.0,
    )
    assert result.score == 100
    assert result.band.label == "desert"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && uv run pytest tests/test_scoring.py::test_score_hex_returns_result_with_factors -v`
Expected: FAIL with `ImportError: cannot import name 'HexScoreResult'`.

- [ ] **Step 3: Write the implementation (append to `scoring.py`)**

Append to `api/src/desertcharge/scoring.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HexScoreResult:
    """The scored output for one hex, including factors for display."""

    score: int
    band: ScoreBand
    population: float
    nearest_dc_fast_miles: float
    chargers_10mi: float


def score_hex(
    population: float,
    pop_min: float,
    pop_max: float,
    nearest_dc_fast_miles: float,
    weighted_chargers_10mi: float,
) -> HexScoreResult:
    """Score one hex and return the score, band, and contributing factors."""
    score = desert_score(
        population=population,
        pop_min=pop_min,
        pop_max=pop_max,
        nearest_dc_fast_miles=nearest_dc_fast_miles,
        weighted_chargers_10mi=weighted_chargers_10mi,
    )
    return HexScoreResult(
        score=score,
        band=band_for_score(score),
        population=population,
        nearest_dc_fast_miles=nearest_dc_fast_miles,
        chargers_10mi=weighted_chargers_10mi,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd api && uv run pytest tests/test_scoring.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add api/src/desertcharge/scoring.py api/tests/test_scoring.py
git commit -m "feat(api): add composite score_hex result with factors and band"
```

---

### Task 5: H3 grid utilities

Wraps h3 v4 so the rest of the code has a small, typed surface: point to cell, cell centroid, cell boundary as GeoJSON-style coordinates, and cells covering a bounding box.

**Files:**
- Create: `api/src/desertcharge/h3grid.py`
- Test: `api/tests/test_h3grid.py`

- [ ] **Step 1: Write the failing tests**

`api/tests/test_h3grid.py`:

```python
from desertcharge.h3grid import (
    DEFAULT_RESOLUTION,
    cell_centroid,
    cell_ring_lnglat,
    cells_for_bbox,
    point_to_cell,
)

# A point in Baker, CA.
BAKER_LAT = 35.2686
BAKER_LNG = -116.0786


def test_point_to_cell_is_stable() -> None:
    cell = point_to_cell(BAKER_LAT, BAKER_LNG)
    assert isinstance(cell, str)
    assert point_to_cell(BAKER_LAT, BAKER_LNG) == cell


def test_point_to_cell_respects_resolution() -> None:
    coarse = point_to_cell(BAKER_LAT, BAKER_LNG, resolution=5)
    fine = point_to_cell(BAKER_LAT, BAKER_LNG, resolution=8)
    assert coarse != fine


def test_cell_centroid_round_trips_to_same_cell() -> None:
    cell = point_to_cell(BAKER_LAT, BAKER_LNG)
    lat, lng = cell_centroid(cell)
    assert point_to_cell(lat, lng) == cell


def test_cell_ring_is_closed_lnglat_ring() -> None:
    cell = point_to_cell(BAKER_LAT, BAKER_LNG)
    ring = cell_ring_lnglat(cell)
    # A hexagon boundary, closed (first point repeated at the end).
    assert len(ring) == 7
    assert ring[0] == ring[-1]
    # GeoJSON order is (lng, lat); longitudes here are negative.
    assert all(-180 <= lng <= 180 and -90 <= lat <= 90 for lng, lat in ring)


def test_cells_for_bbox_covers_region_and_uses_default_resolution() -> None:
    # A small bbox around Baker.
    cells = cells_for_bbox(
        min_lat=35.0, min_lng=-116.3, max_lat=35.5, max_lng=-115.8
    )
    assert len(cells) > 0
    assert point_to_cell(BAKER_LAT, BAKER_LNG, DEFAULT_RESOLUTION) in cells
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd api && uv run pytest tests/test_h3grid.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'desertcharge.h3grid'`.

- [ ] **Step 3: Write the implementation**

`api/src/desertcharge/h3grid.py`:

```python
"""Typed helpers over the h3 v4 library. Pure geometry, no I/O."""

from __future__ import annotations

import h3

# Resolution 7 hexagons are roughly 5 km across, the spec's scoring grid.
DEFAULT_RESOLUTION = 7


def point_to_cell(lat: float, lng: float, resolution: int = DEFAULT_RESOLUTION) -> str:
    """Return the H3 cell index containing the point."""
    return h3.latlng_to_cell(lat, lng, resolution)


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd api && uv run pytest tests/test_h3grid.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Type check and lint**

Run: `cd api && uv run mypy && uv run ruff check .`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/h3grid.py api/tests/test_h3grid.py
git commit -m "feat(api): add typed H3 grid utilities (point, centroid, ring, bbox fill)"
```

---

### Task 6: Settings and async database wiring

**Files:**
- Create: `api/src/desertcharge/config.py`
- Create: `api/src/desertcharge/db.py`

- [ ] **Step 1: Create `config.py`**

`api/src/desertcharge/config.py`:

```python
"""Application settings loaded from the environment."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration. Values come from the environment or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://desertcharge:desertcharge@localhost:5432/desertcharge"

    @property
    def sync_database_url(self) -> str:
        """The same database as a sync URL for Alembic (psycopg2 driver)."""
        return self.database_url.replace("+asyncpg", "+psycopg2")


def get_settings() -> Settings:
    """Return a fresh Settings instance."""
    return Settings()
```

- [ ] **Step 2: Create `db.py`**

`api/src/desertcharge/db.py`:

```python
"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from desertcharge.config import get_settings


def create_engine_from_settings() -> object:
    """Create an async engine using the configured database URL."""
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


def create_session_factory(engine: object) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a session and ensure it is closed."""
    async with factory() as session:
        yield session
```

- [ ] **Step 3: Verify type check and lint**

Run: `cd api && uv run mypy && uv run ruff check .`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add api/src/desertcharge/config.py api/src/desertcharge/db.py
git commit -m "feat(api): add settings and async database wiring"
```

---

### Task 7: SQLAlchemy models

Schema from spec section 7: `chargers`, `census_tracts`, `hex_scores`, `best_sites`, with PostGIS geometry columns.

**Files:**
- Create: `api/src/desertcharge/models.py`
- Test: `api/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`api/tests/test_models.py`:

```python
from geoalchemy2 import Geometry

from desertcharge.models import Base, BestSite, CensusTract, Charger, HexScore


def test_tables_registered_on_metadata() -> None:
    tables = set(Base.metadata.tables)
    assert {"chargers", "census_tracts", "hex_scores", "best_sites"} <= tables


def test_charger_has_point_geometry_and_key_columns() -> None:
    cols = Charger.__table__.columns
    assert isinstance(cols["geom"].type, Geometry)
    assert cols["geom"].type.geometry_type == "POINT"
    assert cols["geom"].type.srid == 4326
    assert "is_dc_fast" in cols
    assert "power_kw" in cols


def test_hex_score_primary_key_is_h3_index() -> None:
    assert HexScore.__table__.primary_key.columns.keys() == ["h3_index"]


def test_models_have_expected_tablenames() -> None:
    assert CensusTract.__tablename__ == "census_tracts"
    assert BestSite.__tablename__ == "best_sites"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && uv run pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'desertcharge.models'`.

- [ ] **Step 3: Write the implementation**

`api/src/desertcharge/models.py`:

```python
"""SQLAlchemy 2.0 models with PostGIS geometry columns."""

from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all models."""


class Charger(Base):
    __tablename__ = "chargers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(128))
    name: Mapped[str | None] = mapped_column(String(256))
    geom: Mapped[object] = mapped_column(Geometry("POINT", srid=4326))
    power_kw: Mapped[float | None] = mapped_column(Float)
    connector_types: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    network: Mapped[str | None] = mapped_column(String(128))
    num_ports: Mapped[int | None] = mapped_column(Integer)
    is_dc_fast: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CensusTract(Base):
    __tablename__ = "census_tracts"

    geoid: Mapped[str] = mapped_column(String(11), primary_key=True)
    state: Mapped[str] = mapped_column(String(2))
    geom: Mapped[object] = mapped_column(Geometry("MULTIPOLYGON", srid=4326))
    population: Mapped[int] = mapped_column(Integer, default=0)
    households: Mapped[int | None] = mapped_column(Integer)


class HexScore(Base):
    __tablename__ = "hex_scores"

    h3_index: Mapped[str] = mapped_column(String(16), primary_key=True)
    geom: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326))
    centroid: Mapped[object] = mapped_column(Geometry("POINT", srid=4326))
    population: Mapped[float] = mapped_column(Float, default=0.0)
    nearest_dc_fast_m: Mapped[float | None] = mapped_column(Float)
    weighted_chargers_10mi: Mapped[float] = mapped_column(Float, default=0.0)
    desert_score: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BestSite(Base):
    __tablename__ = "best_sites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    h3_index: Mapped[str] = mapped_column(String(16))
    geom: Mapped[object] = mapped_column(Geometry("POINT", srid=4326))
    rank: Mapped[int] = mapped_column(Integer)
    est_population_served: Mapped[int] = mapped_column(Integer, default=0)
    gap_miles_closed: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str | None] = mapped_column(String(256))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && uv run pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 5: Type check and lint**

Run: `cd api && uv run mypy && uv run ruff check .`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/models.py api/tests/test_models.py
git commit -m "feat(api): add PostGIS SQLAlchemy models"
```

---

### Task 8: Alembic migration and a PostGIS test container

Sets up Alembic (sync engine) and the initial migration that enables PostGIS and creates the tables and spatial indexes. Verifies it against a real PostGIS container via testcontainers.

**Files:**
- Create: `api/alembic.ini`
- Create: `api/migrations/env.py`
- Create: `api/migrations/script.py.mako`
- Create: `api/migrations/versions/0001_initial.py`
- Create: `api/tests/conftest.py`

- [ ] **Step 1: Create `alembic.ini`**

`api/alembic.ini`:

```ini
[alembic]
script_location = migrations
prepend_sys_path = src

[loggers]
keys = root

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 2: Create `migrations/script.py.mako`**

`api/migrations/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 3: Create `migrations/env.py`**

`api/migrations/env.py`:

```python
"""Alembic environment using a sync engine driven by app settings."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from desertcharge.config import get_settings
from desertcharge.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().sync_database_url)
target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

- [ ] **Step 4: Create the initial migration `migrations/versions/0001_initial.py`**

`api/migrations/versions/0001_initial.py`:

```python
"""initial schema: enable postgis and create tables

Revision ID: 0001
Revises:
"""
from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "chargers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("geom", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("power_kw", sa.Float(), nullable=True),
        sa.Column("connector_types", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("network", sa.String(length=128), nullable=True),
        sa.Column("num_ports", sa.Integer(), nullable=True),
        sa.Column("is_dc_fast", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chargers_is_dc_fast", "chargers", ["is_dc_fast"])

    op.create_table(
        "census_tracts",
        sa.Column("geoid", sa.String(length=11), primary_key=True),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("geom", geoalchemy2.Geometry("MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("population", sa.Integer(), server_default="0", nullable=False),
        sa.Column("households", sa.Integer(), nullable=True),
    )

    op.create_table(
        "hex_scores",
        sa.Column("h3_index", sa.String(length=16), primary_key=True),
        sa.Column("geom", geoalchemy2.Geometry("POLYGON", srid=4326), nullable=False),
        sa.Column("centroid", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("population", sa.Float(), server_default="0", nullable=False),
        sa.Column("nearest_dc_fast_m", sa.Float(), nullable=True),
        sa.Column("weighted_chargers_10mi", sa.Float(), server_default="0", nullable=False),
        sa.Column("desert_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "best_sites",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("h3_index", sa.String(length=16), nullable=False),
        sa.Column("geom", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("est_population_served", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gap_miles_closed", sa.Float(), server_default="0", nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("best_sites")
    op.drop_table("hex_scores")
    op.drop_table("census_tracts")
    op.drop_index("ix_chargers_is_dc_fast", table_name="chargers")
    op.drop_table("chargers")
```

Note: GeoAlchemy2 automatically creates a GiST spatial index for each geometry column, so no explicit spatial index statements are needed.

- [ ] **Step 5: Create `tests/conftest.py` with a migrated PostGIS container**

`api/tests/conftest.py`:

```python
"""Shared fixtures: a PostGIS test container migrated to head."""

from __future__ import annotations

import subprocess
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

API_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def postgis_url() -> Iterator[str]:
    """Start a PostGIS container, run migrations, and yield the async URL."""
    container = PostgresContainer("postgis/postgis:16-3.4", driver="asyncpg")
    with container:
        async_url = container.get_connection_url()
        sync_url = async_url.replace("+asyncpg", "+psycopg2")
        subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=API_DIR,
            check=True,
            env={"DATABASE_URL": async_url, "PATH": _path()},
        )
        yield async_url


def _path() -> str:
    import os

    return os.environ["PATH"]


@pytest_asyncio.fixture
async def session(postgis_url: str) -> AsyncIterator[AsyncSession]:
    """Yield a clean async session against the migrated test database."""
    engine = create_async_engine(postgis_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()
```

- [ ] **Step 6: Run the migration test against the container**

Run: `cd api && uv run pytest tests/test_models.py -v`
Expected: PASS (unit tests still pass; the container is only started when a test requests `session`, which these do not yet).

- [ ] **Step 7: Commit**

```bash
git add api/alembic.ini api/migrations api/tests/conftest.py
git commit -m "feat(api): add alembic migration and PostGIS test container fixture"
```

---

### Task 9: Nearest DC fast charger spatial query

Proves the PostGIS path end to end: seed chargers, then query the nearest DC fast charger distance from a point using a geography distance. This is the supply input the scoring engine needs.

**Files:**
- Create: `api/src/desertcharge/queries.py`
- Test: `api/tests/test_queries.py`

- [ ] **Step 1: Write the failing test**

`api/tests/test_queries.py`:

```python
import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.models import Charger
from desertcharge.queries import nearest_dc_fast_distance_m


async def _add_charger(
    session: AsyncSession, lat: float, lng: float, *, is_dc_fast: bool
) -> None:
    session.add(
        Charger(
            source="test",
            source_id=f"{lat},{lng}",
            name="test",
            geom=WKTElement(f"POINT({lng} {lat})", srid=4326),
            power_kw=150.0 if is_dc_fast else 7.0,
            is_dc_fast=is_dc_fast,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_nearest_dc_fast_returns_none_when_empty(session: AsyncSession) -> None:
    result = await nearest_dc_fast_distance_m(session, lat=35.0, lng=-116.0)
    assert result is None


@pytest.mark.asyncio
async def test_nearest_dc_fast_ignores_slow_chargers(session: AsyncSession) -> None:
    # A close slow charger and a far fast charger.
    await _add_charger(session, 35.0, -116.0, is_dc_fast=False)
    await _add_charger(session, 35.5, -116.0, is_dc_fast=True)
    result = await nearest_dc_fast_distance_m(session, lat=35.0, lng=-116.0)
    assert result is not None
    # ~55 km between 35.0 and 35.5 latitude.
    assert 50_000 < result < 60_000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd api && uv run pytest tests/test_queries.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'desertcharge.queries'`.

- [ ] **Step 3: Write the implementation**

`api/src/desertcharge/queries.py`:

```python
"""Spatial queries over the chargers table."""

from __future__ import annotations

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.models import Charger


async def nearest_dc_fast_distance_m(
    session: AsyncSession, lat: float, lng: float
) -> float | None:
    """Return meters to the nearest DC fast charger, or None if there are none."""
    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    distance = func.ST_Distance(
        cast(Charger.geom, Geography),
        cast(point, Geography),
    )
    stmt = (
        select(distance)
        .where(Charger.is_dc_fast.is_(True))
        .order_by(distance)
        .limit(1)
    )
    result = await session.execute(stmt)
    value = result.scalar_one_or_none()
    return float(value) if value is not None else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd api && uv run pytest tests/test_queries.py -v`
Expected: PASS (the PostGIS container starts here).

- [ ] **Step 5: Full check (all tests, types, lint, format)**

Run:
```bash
cd api && uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add api/src/desertcharge/queries.py api/tests/test_queries.py
git commit -m "feat(api): add nearest DC fast charger distance query"
```

---

### Task 10: Wire the backend CI job

Adds a `backend` job to the existing workflow so the Python code is linted, type checked, and tested on every push and PR. The PostGIS tests need Docker, which the GitHub-hosted runner provides.

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add the `backend` job (append after the `hygiene` job, before the trailing comment)**

Add this job under `jobs:` in `.github/workflows/ci.yml`:

```yaml
  backend:
    name: Backend
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: api
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "0.4.x"
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        run: uv sync
      - name: Format check
        run: uv run ruff format --check .
      - name: Lint
        run: uv run ruff check .
      - name: Type check
        run: uv run mypy
      - name: Test
        run: uv run pytest -v
```

- [ ] **Step 2: Push the branch and open a PR**

```bash
git push -u origin phase-1/backend-foundation
gh pr create --base main --head phase-1/backend-foundation \
  --title "feat(api): phase 1 backend foundation and scoring engine" \
  --body "Implements Phase 1: backend scaffold, desert-score engine, H3 utilities, PostGIS models and migration, nearest-charger query, and the backend CI job. All test-driven."
```

- [ ] **Step 3: Add the new required check to branch protection**

After the first `Backend` run appears on the PR, require it too:

```bash
gh api -X PATCH repos/Siddhesh-Bhande/desertcharge/branches/main/protection/required_status_checks \
  -H "Accept: application/vnd.github+json" \
  -f 'contexts[]=Repo hygiene' -f 'contexts[]=Backend'
```

- [ ] **Step 4: Watch CI and confirm green**

Run: `gh pr checks <pr-number> --watch --interval 5`
Expected: `Repo hygiene` and `Backend` both pass.

- [ ] **Step 5: Merge**

```bash
gh pr merge <pr-number> --squash --delete-branch
git checkout main && git pull origin main
```

---

## Self-review

**Spec coverage (Phase 1 slice):** The spec's scoring method (section 5) is covered by Tasks 2 to 4; the H3 grid (section 5) by Task 5; the data model (section 7) by Tasks 7 and 8; one live PostGIS spatial query (section 8 supply input) by Task 9; the quality gates (section 13) by Tasks 1 and 10. Ingest (section 9), API endpoints (section 8), the four features (section 10), the frontend (sections 1, 4), and deployment (section 12) are explicitly deferred to Phases 2 to 8 in the roadmap and are out of scope here.

**Placeholder scan:** No TBD/TODO. Every code step contains complete code. Commands have expected output.

**Type consistency:** `score_hex` returns `HexScoreResult` (Task 4), used consistently. `point_to_cell`, `cell_centroid`, `cell_ring_lnglat`, `cells_for_bbox` names match between Task 5 test and implementation. Model class names (`Charger`, `CensusTract`, `HexScore`, `BestSite`) match across Tasks 7, 8, 9. `nearest_dc_fast_distance_m` signature matches between Task 9 test and implementation. `sync_database_url` defined in Task 6 config is used by Task 8 `env.py`.

**Note for the executor:** the PostGIS tests require Docker running locally. If Docker is unavailable in the execution environment, Tasks 1 to 7 (pure functions, models registration) still run fully; Tasks 8 to 9 container tests will be validated in CI on the PR.
