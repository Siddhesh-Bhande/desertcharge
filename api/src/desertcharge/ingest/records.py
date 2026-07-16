"""The common charger record shared by all sources, and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChargerRecord:
    """One charger, normalized across sources."""

    source: str
    source_id: str
    name: str | None
    lat: float
    lng: float
    power_kw: float | None
    connector_types: tuple[str, ...]
    network: str | None
    num_ports: int | None
    is_dc_fast: bool


def normalize_connector(raw: str) -> str:
    """Map a source's connector label to a canonical token."""
    text = raw.lower()
    if "combo" in text or "ccs" in text:
        return "CCS"
    if "chademo" in text:
        return "CHAdeMO"
    if "tesla" in text or "nacs" in text or "j3400" in text:
        return "NACS"
    if "j1772" in text or "type 1" in text or "type 2" in text or "mennekes" in text:
        return "J1772"
    return "Other"
