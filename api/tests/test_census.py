import json
from pathlib import Path

import httpx

from desertcharge.ingest.census import (
    TractRecord,
    build_tract_records,
    fetch_tracts,
    parse_centroids,
    parse_populations,
)
from desertcharge.region import REGION_STATES

FIX = Path(__file__).parent / "fixtures"


def test_region_states_are_ca_nv_az() -> None:
    assert REGION_STATES == {"CA": "06", "NV": "32", "AZ": "04"}


def test_tract_record_fields() -> None:
    record = TractRecord(geoid="32003005322", state="NV", population=1580, lat=36.1, lng=-115.0)
    assert record.geoid == "32003005322"
    assert record.population == 1580


def test_parse_centroids_reads_signed_coordinates() -> None:
    payload = json.loads((FIX / "tiger_centroids.json").read_text())
    centroids = parse_centroids(payload)
    assert centroids["32003005322"] == (36.1, -115.1)


def test_parse_populations_builds_geoid() -> None:
    payload = json.loads((FIX / "tiger_population.json").read_text())
    pops = parse_populations(payload)
    assert pops["32003005322"] == 1580
    assert pops["32003005115"] == 2914


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
