"""Lock the bike-infrastructure definition (protected/segregated or shared-use).

CLAUDE.md §8 + user decision 2026-07-17. If these change, it is a deliberate
metric-definition change, not an accident.
"""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import LineString

from cycleform.networks import is_bike_infrastructure


def _edges(rows: list[dict]) -> gpd.GeoDataFrame:
    geom = [LineString([(0, i), (1, i)]) for i in range(len(rows))]
    return gpd.GeoDataFrame(rows, geometry=geom, crs="EPSG:27700")


def test_included_infrastructure():
    edges = _edges(
        [
            {"highway": "cycleway"},
            {"highway": "bridleway"},
            {"highway": "residential", "cycleway:right": "track"},
            {"highway": "secondary", "cycleway:both": "track"},
            {"highway": "footway", "bicycle": "designated"},
            {"highway": "path", "bicycle": "yes"},
        ]
    )
    assert is_bike_infrastructure(edges).all()


def test_excluded_by_definition():
    edges = _edges(
        [
            {"highway": "residential", "cycleway:right": "lane"},  # painted lane
            {"highway": "residential", "bicycle_road": "yes"},  # cycle street
            {"highway": "residential", "motor_vehicle": "no"},  # modal filter
            {"highway": "secondary", "cycleway": "separate"},  # captured elsewhere
            {"highway": "primary"},  # plain road
            {"highway": "footway"},  # foot only, no bicycle tag
        ]
    )
    assert not is_bike_infrastructure(edges).any()


def test_robust_to_missing_columns():
    # only a highway column present -> must not raise, still finds cycleways
    edges = _edges([{"highway": "cycleway"}, {"highway": "primary"}])
    mask = is_bike_infrastructure(edges)
    assert mask.tolist() == [True, False]


def test_handles_list_valued_tags():
    edges = _edges([{"highway": ["residential", "unclassified"], "cycleway:left": ["track", "no"]}])
    assert is_bike_infrastructure(edges).iloc[0]
