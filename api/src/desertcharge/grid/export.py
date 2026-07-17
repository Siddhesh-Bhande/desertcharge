"""Export the scored grid as a compact JSON array for the heat layer."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from desertcharge.models import HexScore


async def export_grid_json(session: AsyncSession, path: Path) -> int:
    """Write [{h3, score}, ...] for every scored hex. Returns the record count."""
    rows = await session.execute(select(HexScore.h3_index, HexScore.desert_score))
    data = [{"h3": h3, "score": score} for h3, score in rows]
    path.write_text(json.dumps(data, separators=(",", ":")))
    return len(data)
