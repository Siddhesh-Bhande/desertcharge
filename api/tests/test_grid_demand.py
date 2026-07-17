from desertcharge.grid.demand import hex_polygon_wkt, hex_populations
from desertcharge.h3grid import point_to_cell
from desertcharge.ingest.census import TractRecord


def test_hex_populations_aggregates_by_cell() -> None:
    # Two tracts very close together share a hex; a far one does not.
    near_a = TractRecord("t1", "NV", 100, 36.100, -115.100)
    near_b = TractRecord("t2", "NV", 250, 36.101, -115.101)
    far = TractRecord("t3", "NV", 400, 40.000, -119.000)
    pops = hex_populations([near_a, near_b, far])
    cell = point_to_cell(36.100, -115.100)
    assert pops[cell] == 350
    assert len(pops) == 2


def test_hex_polygon_wkt_is_closed_polygon() -> None:
    cell = point_to_cell(36.1, -115.1)
    wkt = hex_polygon_wkt(cell)
    assert wkt.startswith("POLYGON((")
    assert wkt.endswith("))")
