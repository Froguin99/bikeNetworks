"""Boundary resolution.

Phase 1 uses OSM/Nominatim geocoding (open-source) for the pilot cities. GISCO
(EU), ONS (UK) and GHSL built-up area are Phase 3 -- see CLAUDE.md §7. Until
then `area_km2` is the geocoded boundary area, which overstates the built-up
denominator; density metrics should be read as provisional and the substitution
is flagged in `Boundary.area_note`.

When Nominatim returns a large administrative unit (a county/province/region)
instead of the city itself -- e.g. "Bergamo, Italy" resolves to Bergamo province
(~2760 km2) rather than the city (~40 km2) -- we retry as a structured city query
and prefer the city boundary. This keeps the analysed network to the urban area.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import osmnx as ox
from shapely.geometry.base import BaseGeometry

log = logging.getLogger(__name__)

# Nominatim `addresstype` values that are bigger than a city -- if the top hit is
# one of these we try to fall back to the city proper.
_OVERSIZED_ADMIN = {
    "country", "state", "region", "province", "county", "district", "state_district",
}
# Settlement-level types we're willing to swap IN (so we never trade one oversized
# admin area for another).
_SETTLEMENT_TYPES = {"city", "town", "village", "municipality", "borough", "suburb", "hamlet"}


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


def _addresstype(gdf) -> str:
    """Nominatim addresstype of the first row, lowercased ('' if absent)."""
    if "addresstype" in gdf.columns and len(gdf):
        val = gdf["addresstype"].iloc[0]
        return str(val).lower() if val is not None else ""
    return ""


def _structured_city_query(query: str) -> dict[str, str] | None:
    """Turn "City, [State,] Country" into a Nominatim structured city query.

    Needs at least a name and a country (a comma); returns None otherwise so the
    caller keeps the original result.
    """
    parts = [p.strip() for p in query.split(",") if p.strip()]
    if len(parts) < 2:
        return None
    q = {"city": parts[0], "country": parts[-1]}
    if len(parts) >= 3:
        q["state"] = parts[-2]
    return q


def resolve_boundary(query: str, place_id: str | None = None) -> Boundary:
    """Geocode a place name to a projected boundary via OSM/Nominatim.

    Prefers the city boundary when the plain query lands on a larger admin unit.
    """
    gdf = ox.geocode_to_gdf(query)
    top_type = _addresstype(gdf)
    if top_type in _OVERSIZED_ADMIN:
        sq = _structured_city_query(query)
        if sq is not None:
            try:
                city = ox.geocode_to_gdf(sq)
                if _addresstype(city) in _SETTLEMENT_TYPES:
                    log.info(
                        "%s: preferred city boundary (%s) over the %s Nominatim returned",
                        place_id or query, _addresstype(city), top_type,
                    )
                    gdf = city
            except Exception:  # structured query failed -> keep the original result
                log.info(
                    "%s: city fallback failed, keeping %s boundary", place_id or query, top_type
                )
    wgs84 = gdf.geometry.iloc[0]
    projected = ox.projection.project_gdf(gdf)
    return Boundary(
        place_id=place_id or query,
        geometry=projected.geometry.iloc[0],
        crs=projected.crs,
        area_km2=float(projected.geometry.iloc[0].area / 1e6),
        geometry_wgs84=wgs84,
    )
