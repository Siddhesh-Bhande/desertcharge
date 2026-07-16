from desertcharge.ingest.merge import haversine_m, merge_chargers
from desertcharge.ingest.records import ChargerRecord


def _record(source: str, sid: str, lat: float, lng: float) -> ChargerRecord:
    return ChargerRecord(
        source=source,
        source_id=sid,
        name=sid,
        lat=lat,
        lng=lng,
        power_kw=150.0,
        connector_types=("CCS",),
        network="net",
        num_ports=2,
        is_dc_fast=True,
    )


def test_haversine_known_distance() -> None:
    # 0.5 degrees of latitude is about 55.6 km.
    d = haversine_m(35.0, -116.0, 35.5, -116.0)
    assert 54_000 < d < 57_000


def test_merge_dedupes_near_duplicates_across_sources() -> None:
    ocm = [_record("openchargemap", "OCM-1", 35.2686, -116.0786)]
    # Same physical spot, about 30 m away, from the other source.
    nrel = [_record("nrel", "NREL-9", 35.2688, -116.0786)]
    merged = merge_chargers(ocm, nrel)
    assert len(merged) == 1
    assert merged[0].source == "openchargemap"  # first group wins


def test_merge_keeps_distinct_chargers() -> None:
    ocm = [_record("openchargemap", "OCM-1", 35.0, -116.0)]
    nrel = [_record("nrel", "NREL-9", 35.5, -116.0)]  # about 55 km away
    merged = merge_chargers(ocm, nrel)
    assert len(merged) == 2
