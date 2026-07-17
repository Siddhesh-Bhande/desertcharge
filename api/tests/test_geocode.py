from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from desertcharge.api.app import create_app
from desertcharge.api.geocode import geocode, parse_nominatim

SAMPLE = [
    {"display_name": "Baker, CA", "lat": "35.2686", "lon": "-116.0786", "type": "town"},
    {"display_name": "Barstow, CA", "lat": "34.8958", "lon": "-117.0173", "type": "city"},
]


def test_parse_nominatim_maps_fields() -> None:
    results = parse_nominatim(SAMPLE)
    assert len(results) == 2
    assert results[0].name == "Baker, CA"
    assert results[0].lat == 35.2686
    assert results[0].lng == -116.0786
    assert results[0].kind == "town"


async def test_geocode_calls_nominatim() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "nominatim.openstreetmap.org"
        assert request.url.params["bounded"] == "1"
        return httpx.Response(200, json=SAMPLE)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        results = await geocode("baker", client)
    assert [r.name for r in results] == ["Baker, CA", "Barstow, CA"]


@pytest.fixture
async def geocode_api() -> AsyncIterator[AsyncClient]:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE)

    mock = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app = create_app(http_client=mock)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    await mock.aclose()


async def test_geocode_route_returns_results(geocode_api: AsyncClient) -> None:
    response = await geocode_api.get("/api/geocode", params={"q": "baker"})
    assert response.status_code == 200
    data = response.json()
    assert data[0]["name"] == "Baker, CA"
    assert data[0]["lng"] == -116.0786
