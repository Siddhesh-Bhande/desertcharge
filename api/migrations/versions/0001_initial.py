"""initial schema: enable postgis and create tables

Revision ID: 0001
Revises:
"""

from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "chargers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("geom", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("power_kw", sa.Float(), nullable=True),
        sa.Column("connector_types", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("network", sa.String(length=128), nullable=True),
        sa.Column("num_ports", sa.Integer(), nullable=True),
        sa.Column("is_dc_fast", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chargers_is_dc_fast", "chargers", ["is_dc_fast"])

    op.create_table(
        "census_tracts",
        sa.Column("geoid", sa.String(length=11), primary_key=True),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("geom", geoalchemy2.Geometry("MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("population", sa.Integer(), server_default="0", nullable=False),
        sa.Column("households", sa.Integer(), nullable=True),
    )

    op.create_table(
        "hex_scores",
        sa.Column("h3_index", sa.String(length=16), primary_key=True),
        sa.Column("geom", geoalchemy2.Geometry("POLYGON", srid=4326), nullable=False),
        sa.Column("centroid", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("population", sa.Float(), server_default="0", nullable=False),
        sa.Column("nearest_dc_fast_m", sa.Float(), nullable=True),
        sa.Column("weighted_chargers_10mi", sa.Float(), server_default="0", nullable=False),
        sa.Column("desert_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "best_sites",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("h3_index", sa.String(length=16), nullable=False),
        sa.Column("geom", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("est_population_served", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gap_miles_closed", sa.Float(), server_default="0", nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("best_sites")
    op.drop_table("hex_scores")
    op.drop_table("census_tracts")
    op.drop_index("ix_chargers_is_dc_fast", table_name="chargers")
    op.drop_table("chargers")
