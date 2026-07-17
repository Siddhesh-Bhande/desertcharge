# DesertCharge Phase 5: HTTP API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the scored data over a typed FastAPI: health, point score (with a nearest-hex fallback), chargers in a bbox with filters, and best sites. Include CORS, an async DB dependency, tests against real PostGIS, and deploy config.

**Architecture:** An app factory builds the FastAPI app with a session factory in app state and a `get_session` dependency. Read queries live in one module; Pydantic schemas type the responses; routes are thin. Tests drive the app with an httpx ASGI client against a migrated PostGIS container. A Dockerfile and fly.toml prepare (but do not perform) the Fly.io deploy.

**Tech Stack:** FastAPI, uvicorn, httpx (async test client), SQLAlchemy async, PostGIS.

---

## File structure (Phase 5)

```
api/pyproject.toml                          add fastapi, uvicorn (modify)
api/src/desertcharge/config.py              add allowed_origins (modify)
api/src/desertcharge/api/__init__.py        (create)
api/src/desertcharge/api/deps.py            get_session dependency (create)
api/src/desertcharge/api/schemas.py         Pydantic response models + verdict (create)
api/src/desertcharge/api/read.py            read queries (create)
api/src/desertcharge/api/routes.py          route handlers (create)
api/src/desertcharge/api/app.py             app factory (create)
api/Dockerfile                              (create)
api/fly.toml                                (create)
api/tests/test_api.py                       (create)
```

---

### Task 1: Dependencies and settings

- [ ] **Step 1: Add to `dependencies` in `api/pyproject.toml`**

```toml
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
```

- [ ] **Step 2: Add `allowed_origins` to `Settings` in `config.py`**

Add this field after `nrel_api_key`:

```python
    allowed_origins: str = "http://localhost:5173"
```

- [ ] **Step 3: Sync**

Run: `cd api && uv sync`
Expected: fastapi and uvicorn installed.

- [ ] **Step 4: Commit**

```bash
git checkout -b phase-5/http-api 2>/dev/null || true
git add api/pyproject.toml api/uv.lock api/src/desertcharge/config.py
git commit -m "chore(api): add fastapi, uvicorn, and allowed_origins setting"
```

---

### Task 2: Schemas and the session dependency

**Files:**
- Create: `api/src/desertcharge/api/__init__.py`, `deps.py`, `schemas.py`

- [ ] **Step 1: Create `api/src/desertcharge/api/__init__.py`**

```python
"""The DesertCharge HTTP API."""
```

- [ ] **Step 2: Create `api/src/desertcharge/api/deps.py`**

```python
"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a database session from the app's session factory."""
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session
```

- [ ] **Step 3: Create `api/src/desertcharge/api/schemas.py`**

```python
"""Pydantic response models and the verdict helper."""

from __future__ import annotations

from pydantic import BaseModel

from desertcharge.scoring import ScoreBand, band_for_score

FAR_MILES = 900.0


def verdict_for(score: int, nearest_miles: float | None) -> str:
    """A short, plain-language verdict for a score."""
    band = band_for_score(score)
    if band in (ScoreBand.SERVED, ScoreBand.GOOD):
        return "Well served. Fast charging is nearby."
    if nearest_miles is None or nearest_miles > FAR_MILES:
        return "Charging desert. No fast charger for a long way."
    return f"Underserved. Nearest fast charger is {round(nearest_miles)} miles away."


class ScoreResponse(BaseModel):
    score: int
    band: str
    verdict: str
    population: int
    nearest_dc_fast_miles: float | None
    chargers_10mi: float
    hex_index: str
    exact: bool


class ChargerOut(BaseModel):
    id: int
    name: str | None
    network: str | None
    power_kw: float | None
    connector_types: list[str]
    is_dc_fast: bool
    lat: float
    lng: float


class BestSiteOut(BaseModel):
    rank: int
    lat: float
    lng: float
    est_population_served: int
    gap_miles_closed: float
    reason: str | None
```

- [ ] **Step 4: Verify import + type check**

Run: `cd api && uv run mypy && uv run ruff check .`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/desertcharge/api/__init__.py api/src/desertcharge/api/deps.py api/src/desertcharge/api/schemas.py
git commit -m "feat(api): add API schemas and session dependency"
```

---

### Task 3: Read queries

**Files:**
- Create: `api/src/desertcharge/api/read.py`
- Test: `api/tests/test_api.py` (read part, exercised via routes in Task 5)

- [ ] **Step 1: Create `api/src/desertcharge/api/read.py`**

```python
"""Read queries backing the API endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.models import BestSite, Charger, HexScore

METERS_PER_MILE = 1609.34
MAX_CHARGERS = 2000


@dataclass(frozen=True, slots=True)
class ScoredPoint:
    hex_index: str
    desert_score: int
    population: int
    nearest_dc_fast_miles: float | None
    chargers_10mi: float
    exact: bool


def _point(lat: float, lng: float) -> object:
    return func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)


async def score_point(session: AsyncSession, lat: float, lng: float) -> ScoredPoint | None:
    """Score a point using its hex, falling back to the nearest scored hex."""
    point = _point(lat, lng)
    contained = (
        await session.execute(
            select(HexScore).where(func.ST_Contains(HexScore.geom, point)).limit(1)
        )
    ).scalar_one_or_none()
    exact = contained is not None
    hex_row = contained
    if hex_row is None:
        hex_row = (
            await session.execute(
                select(HexScore).order_by(HexScore.centroid.op("<->")(point)).limit(1)
            )
        ).scalar_one_or_none()
    if hex_row is None:
        return None
    miles = (
        hex_row.nearest_dc_fast_m / METERS_PER_MILE
        if hex_row.nearest_dc_fast_m is not None
        else None
    )
    return ScoredPoint(
        hex_index=hex_row.h3_index,
        desert_score=hex_row.desert_score,
        population=int(hex_row.population),
        nearest_dc_fast_miles=miles,
        chargers_10mi=hex_row.weighted_chargers_10mi,
        exact=exact,
    )


async def chargers_in_bbox(
    session: AsyncSession,
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    speed: str | None = None,
    network: str | None = None,
    connector: str | None = None,
) -> list[dict[str, object]]:
    """Return chargers within the bbox, filtered."""
    envelope = func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
    conditions = [Charger.geom.op("&&")(envelope)]
    if speed == "dc":
        conditions.append(Charger.is_dc_fast.is_(True))
    elif speed == "level2":
        conditions.append(Charger.is_dc_fast.is_(False))
    if network:
        conditions.append(Charger.network == network)
    if connector:
        conditions.append(Charger.connector_types.contains([connector]))

    stmt = (
        select(
            Charger.id,
            Charger.name,
            Charger.network,
            Charger.power_kw,
            Charger.connector_types,
            Charger.is_dc_fast,
            func.ST_Y(Charger.geom),
            func.ST_X(Charger.geom),
        )
        .where(*conditions)
        .limit(MAX_CHARGERS)
    )
    rows = await session.execute(stmt)
    return [
        {
            "id": cid,
            "name": name,
            "network": network_name,
            "power_kw": power,
            "connector_types": connectors or [],
            "is_dc_fast": dc,
            "lat": lat,
            "lng": lng,
        }
        for cid, name, network_name, power, connectors, dc, lat, lng in rows
    ]


async def list_best_sites(session: AsyncSession, limit: int) -> list[dict[str, object]]:
    """Return the ranked best sites."""
    stmt = (
        select(
            BestSite.rank,
            BestSite.est_population_served,
            BestSite.gap_miles_closed,
            BestSite.reason,
            func.ST_Y(BestSite.geom),
            func.ST_X(BestSite.geom),
        )
        .order_by(BestSite.rank)
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return [
        {
            "rank": rank,
            "est_population_served": pop,
            "gap_miles_closed": gap,
            "reason": reason,
            "lat": lat,
            "lng": lng,
        }
        for rank, pop, gap, reason, lat, lng in rows
    ]
```

- [ ] **Step 2: Type check**

Run: `cd api && uv run mypy && uv run ruff check .`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add api/src/desertcharge/api/read.py
git commit -m "feat(api): add read queries for score, chargers, and best sites"
```

---

### Task 4: Routes and app factory

**Files:**
- Create: `api/src/desertcharge/api/routes.py`, `app.py`

- [ ] **Step 1: Create `api/src/desertcharge/api/routes.py`**

```python
"""API route handlers."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.api.deps import get_session
from desertcharge.api.read import (
    chargers_in_bbox,
    list_best_sites,
    score_point,
)
from desertcharge.api.schemas import (
    BestSiteOut,
    ChargerOut,
    ScoreResponse,
    verdict_for,
)
from desertcharge.scoring import band_for_score

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/score", response_model=ScoreResponse)
async def score(
    session: SessionDep,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
) -> ScoreResponse:
    scored = await score_point(session, lat, lng)
    if scored is None:
        raise HTTPException(status_code=404, detail="No scored data near this point.")
    return ScoreResponse(
        score=scored.desert_score,
        band=band_for_score(scored.desert_score).label,
        verdict=verdict_for(scored.desert_score, scored.nearest_dc_fast_miles),
        population=scored.population,
        nearest_dc_fast_miles=scored.nearest_dc_fast_miles,
        chargers_10mi=scored.chargers_10mi,
        hex_index=scored.hex_index,
        exact=scored.exact,
    )


@router.get("/chargers", response_model=list[ChargerOut])
async def chargers(
    session: SessionDep,
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    speed: str | None = None,
    network: str | None = None,
    connector: str | None = None,
) -> list[ChargerOut]:
    rows = await chargers_in_bbox(
        session, min_lat, min_lng, max_lat, max_lng, speed, network, connector
    )
    return [ChargerOut(**row) for row in rows]  # type: ignore[arg-type]


@router.get("/best-sites", response_model=list[BestSiteOut])
async def best_sites(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[BestSiteOut]:
    rows = await list_best_sites(session, limit)
    return [BestSiteOut(**row) for row in rows]  # type: ignore[arg-type]
```

- [ ] **Step 2: Create `api/src/desertcharge/api/app.py`**

```python
"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.cors import CORSMiddleware

from desertcharge.api.routes import router
from desertcharge.config import get_settings
from desertcharge.db import create_engine_from_settings, create_session_factory


def create_app(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    """Build the API app. Pass a session factory in tests; otherwise build from settings."""
    factory = session_factory or create_session_factory(create_engine_from_settings())
    app = FastAPI(title="DesertCharge API", version="0.1.0")
    app.state.session_factory = factory

    origins = [o.strip() for o in get_settings().allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    return app


app = create_app()
```

- [ ] **Step 3: Type check and lint**

Run: `cd api && uv run mypy && uv run ruff check .`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add api/src/desertcharge/api/routes.py api/src/desertcharge/api/app.py
git commit -m "feat(api): add routes and the FastAPI app factory"
```

---

### Task 5: API tests against PostGIS

**Files:**
- Create: `api/tests/test_api.py`

- [ ] **Step 1: Write `api/tests/test_api.py`**

```python
from collections.abc import AsyncIterator

import pytest
from geoalchemy2.elements import WKTElement
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from desertcharge.api.app import create_app
from desertcharge.grid.demand import hex_polygon_wkt
from desertcharge.h3grid import point_to_cell
from desertcharge.models import BestSite, Charger, HexScore


@pytest.fixture
async def client(postgis_url: str) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(postgis_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app(session_factory=factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    await engine.dispose()


async def _seed(session: AsyncSession) -> str:
    cell = point_to_cell(35.0, -116.0)
    session.add(
        HexScore(
            h3_index=cell,
            geom=WKTElement(hex_polygon_wkt(cell), srid=4326),
            centroid=WKTElement("POINT(-116 35)", srid=4326),
            population=8000.0,
            nearest_dc_fast_m=64373.0,  # 40 miles
            weighted_chargers_10mi=0.0,
            desert_score=88,
        )
    )
    session.add(
        Charger(
            source="test",
            source_id="c1",
            name="Baker EA",
            geom=WKTElement("POINT(-116.0 35.0)", srid=4326),
            power_kw=150.0,
            connector_types=["CCS"],
            network="Electrify America",
            num_ports=4,
            is_dc_fast=True,
        )
    )
    session.add(
        BestSite(
            h3_index=cell,
            geom=WKTElement("POINT(-116 35)", srid=4326),
            rank=1,
            est_population_served=12000,
            gap_miles_closed=40.0,
            reason="A charger here would serve about 12,000 people.",
        )
    )
    await session.commit()
    return cell


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_score_returns_band_and_verdict(
    client: AsyncClient, session: AsyncSession
) -> None:
    cell = await _seed(session)
    response = await client.get("/api/score", params={"lat": 35.0, "lng": -116.0})
    assert response.status_code == 200
    body = response.json()
    assert body["hex_index"] == cell
    assert body["score"] == 88
    assert body["band"] == "desert"
    assert body["exact"] is True
    assert "miles away" in body["verdict"]


async def test_score_falls_back_to_nearest_hex(
    client: AsyncClient, session: AsyncSession
) -> None:
    await _seed(session)
    # A point far from the only hex still gets a score, marked non-exact.
    response = await client.get("/api/score", params={"lat": 36.0, "lng": -117.0})
    assert response.status_code == 200
    assert response.json()["exact"] is False


async def test_chargers_filter_by_speed(
    client: AsyncClient, session: AsyncSession
) -> None:
    await _seed(session)
    response = await client.get(
        "/api/chargers",
        params={
            "min_lat": 34.0,
            "min_lng": -117.0,
            "max_lat": 36.0,
            "max_lng": -115.0,
            "speed": "dc",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["network"] == "Electrify America"
    assert data[0]["connector_types"] == ["CCS"]


async def test_best_sites(client: AsyncClient, session: AsyncSession) -> None:
    await _seed(session)
    response = await client.get("/api/best-sites", params={"limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert data[0]["rank"] == 1
    assert data[0]["est_population_served"] == 12000
```

- [ ] **Step 2: Run tests**

Run: `cd api && uv run pytest tests/test_api.py -v`
Expected: PASS (all five).

- [ ] **Step 3: Full check**

Run:
```bash
cd api && uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add api/tests/test_api.py
git commit -m "test(api): add API tests against PostGIS"
```

---

### Task 6: Deploy config and local smoke test

**Files:**
- Create: `api/Dockerfile`, `api/fly.toml`

- [ ] **Step 1: Create `api/Dockerfile`**

```dockerfile
FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.11.26
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY . .
RUN uv sync --no-dev --frozen

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "desertcharge.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `api/fly.toml`**

```toml
app = "desertcharge-api"
primary_region = "sjc"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

[[http_service.checks]]
  path = "/api/health"
  interval = "30s"
  timeout = "5s"

[env]
  ALLOWED_ORIGINS = "http://localhost:5173"
```

- [ ] **Step 3: Local smoke test against a container**

Start PostGIS, migrate, load a little data, run the API, and curl it.

```bash
docker run -d --name dc-pg -e POSTGRES_PASSWORD=desertcharge -e POSTGRES_USER=desertcharge -e POSTGRES_DB=desertcharge -p 5433:5432 postgis/postgis:16-3.4
# wait for readiness
cd api
export DATABASE_URL="postgresql+asyncpg://desertcharge:desertcharge@localhost:5433/desertcharge"
uv run alembic upgrade head
uv run python -m desertcharge.ingest.run
uv run python -m desertcharge.ingest.census_run
uv run python -m desertcharge.grid.run
uv run uvicorn desertcharge.api.app:app --port 8000 &
sleep 3
curl -s "http://localhost:8000/api/health"
curl -s "http://localhost:8000/api/score?lat=35.27&lng=-116.08"
curl -s "http://localhost:8000/api/best-sites?limit=2"
kill %1
docker rm -f dc-pg
```
Expected: health ok; score returns a desert score for the Baker area (via fallback if needed); best sites returned.

- [ ] **Step 4: Commit**

```bash
git add api/Dockerfile api/fly.toml
git commit -m "chore(api): add Dockerfile and fly.toml for deploy"
```

- [ ] **Step 5: Push, PR, watch CI, merge**

```bash
git push -u origin phase-5/http-api
gh pr create --base main --head phase-5/http-api --title "feat(api): phase 5 HTTP API (health, score, chargers, best-sites)" --body "..."
gh pr checks <pr-number> --watch --interval 15
gh pr merge <pr-number> --squash --delete-branch
git checkout main && git pull origin main
```

---

## Self-review

**Spec coverage (Phase 5 slice):** Spec section 8 endpoints `/health`, `/score`, `/chargers`, `/best-sites` are covered by Tasks 4 and 5, including the score nearest-hex fallback (a documented follow-up from Phase 4). `/geocode` and `/route`, rate limiting, and the actual Fly.io deploy are deferred to Phase 6 because they need external services and accounts. Section 12 deploy config (Dockerfile, fly.toml) is prepared in Task 6.

**Placeholder scan:** No TBD/TODO. Every code step has complete code. `<pr-number>` is a runtime value.

**Type consistency:** `ScoredPoint`, `score_point`, `chargers_in_bbox`, and `list_best_sites` signatures match between read.py and routes.py. `ScoreResponse`, `ChargerOut`, `BestSiteOut`, and `verdict_for` match between schemas.py and routes.py. `get_session` matches between deps.py and routes.py. `create_app(session_factory=...)` matches between app.py and test_api.py. The two `ChargerOut(**row)` and `BestSiteOut(**row)` calls carry a targeted `type: ignore[arg-type]` because the row dicts are typed loosely as `dict[str, object]`.

**Deploy note:** the Fly.io deploy is not executed here; it needs a Fly account, a provisioned Postgres (Supabase or Fly Postgres), and secrets. Task 6 only adds the config and smoke-tests the app locally.
