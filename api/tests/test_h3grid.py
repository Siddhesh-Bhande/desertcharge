from desertcharge.h3grid import (
    DEFAULT_RESOLUTION,
    cell_centroid,
    cell_ring_lnglat,
    cells_for_bbox,
    point_to_cell,
)

# A point in Baker, CA.
BAKER_LAT = 35.2686
BAKER_LNG = -116.0786


def test_point_to_cell_is_stable() -> None:
    cell = point_to_cell(BAKER_LAT, BAKER_LNG)
    assert isinstance(cell, str)
    assert point_to_cell(BAKER_LAT, BAKER_LNG) == cell


def test_point_to_cell_respects_resolution() -> None:
    coarse = point_to_cell(BAKER_LAT, BAKER_LNG, resolution=5)
    fine = point_to_cell(BAKER_LAT, BAKER_LNG, resolution=8)
    assert coarse != fine


def test_cell_centroid_round_trips_to_same_cell() -> None:
    cell = point_to_cell(BAKER_LAT, BAKER_LNG)
    lat, lng = cell_centroid(cell)
    assert point_to_cell(lat, lng) == cell


def test_cell_ring_is_closed_lnglat_ring() -> None:
    cell = point_to_cell(BAKER_LAT, BAKER_LNG)
    ring = cell_ring_lnglat(cell)
    # A hexagon boundary, closed (first point repeated at the end).
    assert len(ring) == 7
    assert ring[0] == ring[-1]
    # GeoJSON order is (lng, lat); longitudes here are negative.
    assert all(-180 <= lng <= 180 and -90 <= lat <= 90 for lng, lat in ring)


def test_cells_for_bbox_covers_region_and_uses_default_resolution() -> None:
    # A small bbox around Baker.
    cells = cells_for_bbox(min_lat=35.0, min_lng=-116.3, max_lat=35.5, max_lng=-115.8)
    assert len(cells) > 0
    assert point_to_cell(BAKER_LAT, BAKER_LNG, DEFAULT_RESOLUTION) in cells
