import httpx
from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.api.route import (
    analyze_route,
    parse_ors_geometry,
    sample_along,
    worst_gap_miles,
)
from desertcharge.api.schemas import RouteSample
from desertcharge.models import Charger

# A short line from near (35, -116) to (36, -115), about 124 miles.
ORS_FIXTURE = {
    "features": [
        {
            "geometry": {
                "coordinates": [
                    [-116.0, 35.0],
                    [-115.75, 35.25],
                    [-115.5, 35.5],
                    [-115.25, 35.75],
                    [-115.0, 36.0],
                ],
            },
            "properties": {"summary": {"distance": 200000.0}},
        }
    ]
}


def test_parse_ors_geometry() -> None:
    coords, distance_m = parse_ors_geometry(ORS_FIXTURE)
    assert coords[0] == (-116.0, 35.0)
    assert coords[-1] == (-115.0, 36.0)
    assert distance_m == 200000.0


def test_sample_along_covers_endpoints() -> None:
    coords, _ = parse_ors_geometry(ORS_FIXTURE)
    samples = sample_along(coords, count=10)
    assert len(samples) == 10
    assert samples[0][2] == 0.0
    assert samples[-1][2] == 1.0
    # First sample sits at the origin.
    assert round(samples[0][0], 2) == 35.0


def test_worst_gap_miles_finds_longest_far_stretch() -> None:
    samples = [
        RouteSample(lat=0, lng=0, fraction=0.0, nearest_dc_fast_miles=2.0),
        RouteSample(lat=0, lng=0, fraction=0.25, nearest_dc_fast_miles=40.0),
        RouteSample(lat=0, lng=0, fraction=0.5, nearest_dc_fast_miles=50.0),
        RouteSample(lat=0, lng=0, fraction=0.75, nearest_dc_fast_miles=3.0),
        RouteSample(lat=0, lng=0, fraction=1.0, nearest_dc_fast_miles=None),
    ]
    # 0.25 -> 0.75 is a far stretch of 0.5 * 100 = 50 miles.
    assert worst_gap_miles(samples, total_miles=100.0) == 50.0


async def test_analyze_route_scores_the_corridor(session: AsyncSession) -> None:
    # One DC fast charger near the origin; the far end becomes a desert stretch.
    session.add(
        Charger(
            source="test",
            source_id="c1",
            name="Origin EA",
            geom=WKTElement("POINT(-116.0 35.0)", srid=4326),
            power_kw=150.0,
            is_dc_fast=True,
        )
    )
    await session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.openrouteservice.org"
        return httpx.Response(200, json=ORS_FIXTURE)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await analyze_route(session, (35.0, -116.0), (36.0, -115.0), "key", client)

    assert len(result.samples) == 25
    assert round(result.distance_miles) == 124
    assert result.samples[0].nearest_dc_fast_miles is not None
    assert result.samples[0].nearest_dc_fast_miles < 5
    assert result.worst_gap_miles > 0
