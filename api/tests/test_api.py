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


async def test_score_returns_band_and_verdict(client: AsyncClient, session: AsyncSession) -> None:
    cell = await _seed(session)
    response = await client.get("/api/score", params={"lat": 35.0, "lng": -116.0})
    assert response.status_code == 200
    body = response.json()
    assert body["hex_index"] == cell
    assert body["score"] == 88
    assert body["band"] == "desert"
    assert body["exact"] is True
    assert "miles away" in body["verdict"]


async def test_score_falls_back_to_nearest_hex(client: AsyncClient, session: AsyncSession) -> None:
    await _seed(session)
    # A point far from the only hex still gets a score, marked non-exact.
    response = await client.get("/api/score", params={"lat": 36.0, "lng": -117.0})
    assert response.status_code == 200
    assert response.json()["exact"] is False


async def test_chargers_filter_by_speed(client: AsyncClient, session: AsyncSession) -> None:
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
