"""Boundary resolution.

Phase 1 uses OSM/Nominatim geocoding (open-source) for the pilot cities. GISCO
(EU), ONS (UK) and GHSL built-up area are Phase 3 -- see CLAUDE.md §7. Until
then `area_km2` is the geocoded boundary area, which overstates the built-up
denominator; density metrics should be read as provisional and the substitution
is flagged in `Boundary.area_note`.
"""

from __future__ import annotations

from dataclasses import dataclass

import osmnx as ox
from shapely.geometry.base import BaseGeometry


@dataclass
class Boundary:
    place_id: str
    geometry: BaseGeometry
    """Boundary polygon in the projected (metric) CRS."""
    crs: object
    """Local UTM chosen by osmnx; metres."""
    area_km2: float
    geometry_wgs84: BaseGeometry
    """Same boundary in EPSG:4326, for fetching OSM within it."""
    area_note: str = "geocoded boundary area; GHSL built-up pending (Phase 3)"


def resolve_boundary(query: str, place_id: str | None = None) -> Boundary:
    """Geocode a place name to a projected boundary via OSM/Nominatim."""
    gdf = ox.geocode_to_gdf(query)
    wgs84 = gdf.geometry.iloc[0]
    projected = ox.projection.project_gdf(gdf)
    return Boundary(
        place_id=place_id or query,
        geometry=projected.geometry.iloc[0],
        crs=projected.crs,
        area_km2=float(projected.geometry.iloc[0].area / 1e6),
        geometry_wgs84=wgs84,
    )
