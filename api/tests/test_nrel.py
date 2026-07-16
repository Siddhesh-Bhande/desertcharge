import json
from pathlib import Path

import httpx

from desertcharge.ingest.nrel import fetch_nrel, parse_nrel
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

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        records = await fetch_nrel(REGION, api_key="k", client=client)
    assert len(records) == 2
