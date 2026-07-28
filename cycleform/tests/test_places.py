"""Coordinate-anchored geocoding: pick the boundary that sits at the expected point,
reject a wrong same-named place. Deterministic -- Nominatim is monkeypatched."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import box

from cycleform import places
from cycleform.places import GeocodeMismatch, _geocode_near_point

# Copenhagen (lat, lon); Point is (lon, lat).
CPH_LAT, CPH_LON = 55.6798, 12.5856


def _gdf(geom, addresstype):
    return gpd.GeoDataFrame(
        {"addresstype": [addresstype], "display_name": ["x"]},
        geometry=[geom],
        crs="EPSG:4326",
    )


def _fake_geocoder(results):
    """Return a stand-in ox.geocode_to_gdf yielding results[which_result-1]."""
    def _g(query, which_result=None, by_osmid=False):
        i = 1 if which_result is None else which_result
        if i > len(results):
            raise ValueError("no such Nominatim result")
        return results[i - 1]
    return _g


def test_prefers_the_polygon_that_contains_the_point(monkeypatch):
    far = _gdf(box(-75.8, 43.8, -75.6, 44.0), "hamlet")          # Copenhagen, NY
    right = _gdf(box(12.4, 55.55, 12.72, 55.80), "municipality")  # contains CPH
    monkeypatch.setattr(places.ox, "geocode_to_gdf", _fake_geocoder([far, right]))
    got = _geocode_near_point("Copenhagen, Denmark", CPH_LAT, CPH_LON, 25.0)
    assert got is right


def test_skips_oversized_admin_even_when_it_contains_the_point(monkeypatch):
    state = _gdf(box(0, 50, 20, 60), "state")                    # big, contains CPH
    city = _gdf(box(12.5, 55.6, 12.7, 55.8), "city")             # the real city
    monkeypatch.setattr(places.ox, "geocode_to_gdf", _fake_geocoder([state, city]))
    got = _geocode_near_point("Copenhagen, Denmark", CPH_LAT, CPH_LON, 25.0)
    assert got is city


def test_raises_when_every_candidate_is_far(monkeypatch):
    far1 = _gdf(box(-76, 43, -75, 44), "hamlet")                 # New York
    far2 = _gdf(box(2, 48, 3, 49), "town")                       # France
    monkeypatch.setattr(places.ox, "geocode_to_gdf", _fake_geocoder([far1, far2]))
    with pytest.raises(GeocodeMismatch):
        _geocode_near_point("Copenhagen, Denmark", CPH_LAT, CPH_LON, 25.0)
