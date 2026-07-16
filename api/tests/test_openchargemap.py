import json
from pathlib import Path

import httpx

from desertcharge.ingest.openchargemap import fetch_openchargemap, parse_openchargemap
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

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        records = await fetch_openchargemap(REGION, api_key="k", client=client)
    assert len(records) == 2
