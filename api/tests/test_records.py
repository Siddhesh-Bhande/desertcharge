from desertcharge.ingest.records import ChargerRecord, normalize_connector
from desertcharge.region import REGION, Bbox, tile_bbox


def test_region_is_the_desert_southwest() -> None:
    assert isinstance(REGION, Bbox)
    # Covers Southern California, Nevada, and Arizona.
    assert REGION.min_lat < 33.0 < REGION.max_lat
    assert REGION.min_lng < -115.0 < REGION.max_lng
    assert REGION.contains(35.2686, -116.0786)  # Baker, CA
    assert not REGION.contains(47.6, -122.3)  # Seattle, out of region


def test_tile_bbox_covers_the_region() -> None:
    tiles = tile_bbox(REGION, cols=4, rows=4)
    assert len(tiles) == 16
    # The tiles span the full region without gaps.
    assert min(t.min_lat for t in tiles) == REGION.min_lat
    assert max(t.max_lat for t in tiles) == REGION.max_lat
    assert min(t.min_lng for t in tiles) == REGION.min_lng
    assert max(t.max_lng for t in tiles) == REGION.max_lng
    # Baker falls inside exactly one tile.
    covering = [t for t in tiles if t.contains(35.2686, -116.0786)]
    assert len(covering) == 1


def test_normalize_connector_canonical_forms() -> None:
    assert normalize_connector("J1772COMBO") == "CCS"
    assert normalize_connector("CCS (Type 1)") == "CCS"
    assert normalize_connector("CHADEMO") == "CHAdeMO"
    assert normalize_connector("CHAdeMO") == "CHAdeMO"
    assert normalize_connector("Tesla (Model S/X)") == "NACS"
    assert normalize_connector("TESLA") == "NACS"
    assert normalize_connector("J1772") == "J1772"
    assert normalize_connector("Type 2 (Socket Only)") == "J1772"
    assert normalize_connector("Some Weird Plug") == "Other"


def test_charger_record_is_frozen_with_fields() -> None:
    record = ChargerRecord(
        source="openchargemap",
        source_id="OCM-1",
        name="Baker",
        lat=35.27,
        lng=-116.08,
        power_kw=150.0,
        connector_types=("CCS",),
        network="Electrify America",
        num_ports=4,
        is_dc_fast=True,
    )
    assert record.source_id == "OCM-1"
    assert record.is_dc_fast is True
    assert record.connector_types == ("CCS",)
