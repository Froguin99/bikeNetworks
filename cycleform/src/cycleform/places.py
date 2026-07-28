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
import math
import time
from dataclasses import dataclass

import osmnx as ox
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from cycleform.config import settings

log = logging.getLogger(__name__)

# When an expected coordinate is supplied, scan up to this many Nominatim results
# and accept a candidate whose centroid is within this distance of the point.
_MAX_CANDIDATES = 10
_GEOCODE_TOL_KM = 25.0
# Reverse fallback: search admin boundaries within this radius of the point and
# accept the largest that still fits a city (not a whole region/province).
_REVERSE_DIST_M = 25000
_CITY_CAP_KM2 = 800.0

# Nominatim `addresstype` values that are bigger than a city -- if the top hit is
# one of these we try to fall back to the city proper.
_OVERSIZED_ADMIN = {
    "country", "state", "region", "province", "county", "district", "state_district",
}
# Settlement-level types we're willing to swap IN (so we never trade one oversized
# admin area for another).
_SETTLEMENT_TYPES = {"city", "town", "village", "municipality", "borough", "suburb", "hamlet"}


class BoundaryTooLarge(RuntimeError):
    """Geocoded boundary exceeds settings.max_boundary_km2 -- a region-scale
    mis-geocode; skip it before fetching (osmnx would tile it into many slow
    sub-queries)."""


class GeocodeMismatch(RuntimeError):
    """The geocoded boundary is nowhere near the expected coordinate -- a wrong
    same-named place (e.g. "Copenhagen, Denmark" -> a hamlet in New York). Raised
    so the place is recorded as failed, never measured on the wrong network."""


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


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _area_km2(gdf) -> float:
    """Projected area (km2) of a one-row geocode result."""
    return float(ox.projection.project_gdf(gdf).geometry.iloc[0].area / 1e6)


def _geocode_near_point(
    query: str, lat: float, lon: float, tol_km: float, place_id: str | None = None
):
    """Return the Nominatim result that actually sits at (lat, lon).

    Scans the top results and, among (Multi)Polygons that CONTAIN the point and are
    no bigger than a city (<= max_boundary_km2), returns the SMALLEST -- so a city
    tagged by Nominatim as a county (e.g. the German Kreisfreie Stadt Fürth) is kept
    while a whole state/region that merely encloses the point is not. Falls back to
    the nearest candidate within tol_km, else raises GeocodeMismatch (the wrong-same-
    named-place guard: "Copenhagen, Denmark" -> a New York hamlet).
    """
    pt = Point(lon, lat)
    containing: list[tuple[float, object]] = []
    best_gdf, best_km = None, float("inf")
    for i in range(1, _MAX_CANDIDATES + 1):
        try:
            cand = ox.geocode_to_gdf(query, which_result=i)
        except Exception:
            continue  # this rank is not a (Multi)Polygon, or no Nth result exists
        geom = cand.geometry.iloc[0]
        if geom.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        if geom.contains(pt):
            area = _area_km2(cand)
            if area <= settings.max_boundary_km2:
                containing.append((area, cand))
        else:
            c = geom.centroid
            d = _haversine_km(lat, lon, c.y, c.x)
            if d < best_km:
                best_gdf, best_km = cand, d
    if containing:
        return min(containing, key=lambda t: t[0])[1]  # smallest boundary at the point
    if best_gdf is not None and best_km <= tol_km:
        log.info(
            "%s: no polygon contained the point; took nearest candidate (%.0f km away)",
            place_id or query, best_km,
        )
        return best_gdf
    raise GeocodeMismatch(
        f"{place_id or query}: no geocode within {tol_km:.0f} km of "
        f"({lat:.4f}, {lon:.4f}); nearest candidate {best_km:.0f} km away"
    )


def _reverse_boundary_gdf(lat: float, lon: float):
    """Find the enclosing settlement boundary at a point via OSM admin areas (or None).

    The fallback for when a forward name search never surfaces the right polygon
    (e.g. "Copenhagen, Denmark" -> a New York hamlet, while the boundary is filed
    under "Kobenhavns Kommune"; or a duplicate like the wrong Quelimane). Fetches the
    administrative boundaries around the point, keeps those that contain it, and
    returns the LARGEST that still fits a city (<= _CITY_CAP_KM2) -- i.e. the
    municipality, not a neighbourhood inside it nor the region around it. Returns
    None on any failure so the caller falls back to raising GeocodeMismatch.
    """
    pt = Point(lon, lat)
    feats = None
    for attempt in range(1, 4):  # Overpass can be flaky under load; retry transient errors
        try:
            feats = ox.features_from_point(
                (lat, lon), tags={"boundary": "administrative"}, dist=_REVERSE_DIST_M
            )
            break
        except Exception as exc:
            if attempt == 3:
                log.info("reverse geocode at (%.4f, %.4f) failed after 3 tries: %s", lat, lon, exc)
                return None
            time.sleep(2 * attempt)
    feats = feats[feats.geometry.type.isin(("Polygon", "MultiPolygon"))]
    feats = feats[feats.geometry.contains(pt)]
    if feats.empty:
        return None
    areas = ox.projection.project_gdf(feats).geometry.area / 1e6
    feats = feats.assign(_area_km2=areas.to_numpy())
    fits = feats[feats["_area_km2"] <= _CITY_CAP_KM2].sort_values("_area_km2")
    if fits.empty:
        return None
    return fits.iloc[[-1]].drop(columns="_area_km2").reset_index(drop=True)


def resolve_boundary(
    query: str,
    place_id: str | None = None,
    *,
    expect_lat: float | None = None,
    expect_lon: float | None = None,
    tol_km: float = _GEOCODE_TOL_KM,
) -> Boundary:
    """Geocode a place name to a projected boundary via OSM/Nominatim.

    When expect_lat/expect_lon are given (e.g. a ModalShare coordinate), the result
    is coordinate-anchored: choose the boundary that actually sits at that point,
    so a wrong same-named place is rejected (GeocodeMismatch). Without a coordinate,
    fall back to the plain query and prefer the city boundary when Nominatim lands
    on a larger admin unit.
    """
    if expect_lat is not None and expect_lon is not None:
        try:
            gdf = _geocode_near_point(query, expect_lat, expect_lon, tol_km, place_id)
        except GeocodeMismatch:
            # name search never found the right place; try reverse-geocoding the point
            gdf = _reverse_boundary_gdf(expect_lat, expect_lon)
            pt = Point(expect_lon, expect_lat)
            if gdf is None or not (
                gdf.geometry.iloc[0].contains(pt)
                or _haversine_km(
                    expect_lat, expect_lon,
                    gdf.geometry.iloc[0].centroid.y, gdf.geometry.iloc[0].centroid.x,
                ) <= tol_km
            ):
                raise
            log.info("%s: resolved by reverse-geocoding the coordinate", place_id or query)
    else:
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
