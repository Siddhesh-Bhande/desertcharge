from geoalchemy2 import Geometry

from desertcharge.models import Base, BestSite, CensusTract, Charger, HexScore


def test_tables_registered_on_metadata() -> None:
    tables = set(Base.metadata.tables)
    assert {"chargers", "census_tracts", "hex_scores", "best_sites"} <= tables


def test_charger_has_point_geometry_and_key_columns() -> None:
    cols = Charger.__table__.columns
    assert isinstance(cols["geom"].type, Geometry)
    assert cols["geom"].type.geometry_type == "POINT"
    assert cols["geom"].type.srid == 4326
    assert "is_dc_fast" in cols
    assert "power_kw" in cols


def test_hex_score_primary_key_is_h3_index() -> None:
    pk_names = [column.name for column in HexScore.__table__.primary_key]
    assert pk_names == ["h3_index"]


def test_models_have_expected_tablenames() -> None:
    assert CensusTract.__tablename__ == "census_tracts"
    assert BestSite.__tablename__ == "best_sites"


def test_census_tract_has_point_centroid() -> None:
    cols = CensusTract.__table__.columns
    assert isinstance(cols["centroid"].type, Geometry)
    assert cols["centroid"].type.geometry_type == "POINT"
    assert "geom" not in cols
