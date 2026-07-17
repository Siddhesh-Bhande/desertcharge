"""SQLAlchemy 2.0 models with PostGIS geometry columns."""

from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all models."""


class Charger(Base):
    __tablename__ = "chargers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(128))
    name: Mapped[str | None] = mapped_column(String(256))
    geom: Mapped[object] = mapped_column(Geometry("POINT", srid=4326))
    power_kw: Mapped[float | None] = mapped_column(Float)
    connector_types: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    network: Mapped[str | None] = mapped_column(String(128))
    num_ports: Mapped[int | None] = mapped_column(Integer)
    is_dc_fast: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CensusTract(Base):
    __tablename__ = "census_tracts"

    geoid: Mapped[str] = mapped_column(String(11), primary_key=True)
    state: Mapped[str] = mapped_column(String(2))
    centroid: Mapped[object] = mapped_column(Geometry("POINT", srid=4326))
    population: Mapped[int] = mapped_column(Integer, default=0)
    households: Mapped[int | None] = mapped_column(Integer)


class HexScore(Base):
    __tablename__ = "hex_scores"

    h3_index: Mapped[str] = mapped_column(String(16), primary_key=True)
    geom: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326))
    centroid: Mapped[object] = mapped_column(Geometry("POINT", srid=4326))
    population: Mapped[float] = mapped_column(Float, default=0.0)
    nearest_dc_fast_m: Mapped[float | None] = mapped_column(Float)
    weighted_chargers_10mi: Mapped[float] = mapped_column(Float, default=0.0)
    desert_score: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BestSite(Base):
    __tablename__ = "best_sites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    h3_index: Mapped[str] = mapped_column(String(16))
    geom: Mapped[object] = mapped_column(Geometry("POINT", srid=4326))
    rank: Mapped[int] = mapped_column(Integer)
    est_population_served: Mapped[int] = mapped_column(Integer, default=0)
    gap_miles_closed: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str | None] = mapped_column(String(256))
