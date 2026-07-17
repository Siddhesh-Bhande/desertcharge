import json
from pathlib import Path

from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.grid.export import export_grid_json
from desertcharge.h3grid import point_to_cell
from desertcharge.models import HexScore


async def test_export_grid_json_writes_h3_score_array(
    session: AsyncSession, tmp_path: Path
) -> None:
    cell = point_to_cell(35.0, -116.0)
    session.add(
        HexScore(
            h3_index=cell,
            geom=WKTElement("POLYGON((0 0,0 1,1 1,1 0,0 0))", srid=4326),
            centroid=WKTElement("POINT(-116 35)", srid=4326),
            population=1000.0,
            weighted_chargers_10mi=0.0,
            desert_score=88,
        )
    )
    await session.commit()

    out = tmp_path / "grid.json"
    count = await export_grid_json(session, out)
    assert count == 1
    data = json.loads(out.read_text())
    assert data == [{"h3": cell, "score": 88}]
