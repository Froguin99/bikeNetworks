"""The grown-network merge behaves as specified (cycleform.scenarios).

The user's model (2026-07-20): merging a grown cycle network leaves the ROAD
network untouched, grows the BIKE network, and upgrades the STREET network's LTS
in place (same topology and length, grown corridors -> LTS 1). These tests pin
that contract on synthetic data, with no OSM or pickle I/O.
"""

from __future__ import annotations

import geopandas as gpd
import networkx as nx
import numpy as np
from shapely.geometry import LineString

from cycleform import scenarios
from cycleform.metrics import REGISTRY
from cycleform.synthetic import fake_osm_context


def _lts1_length_share(net) -> float:
    e = net.edges
    return float(e.loc[e["lts"] == 1, "length"].sum() / e["length"].sum())


def _grown_over_street(street, n: int = 4) -> gpd.GeoDataFrame:
    """A few of the street network's own edges, presented as grown cycleways."""
    sub = street.edges.iloc[:n]
    gdf = gpd.GeoDataFrame(
        {"highway": ["cycleway"] * len(sub), "geometry": list(sub.geometry.values)},
        crs=street.crs,
    )
    gdf["length"] = gdf.geometry.length
    return gdf


def test_road_layer_is_unchanged():
    ctx = fake_osm_context()
    grown = _grown_over_street(ctx.street)
    sctx = scenarios.scenario_context(ctx, grown)
    assert sctx.road is ctx.road  # identical object -> road metrics cannot move


def test_bike_layer_grows():
    ctx = fake_osm_context()
    grown = _grown_over_street(ctx.street)
    sctx = scenarios.scenario_context(ctx, grown)
    assert sctx.bike.n_edges > ctx.bike.n_edges
    assert sctx.bike.length_total_m > ctx.bike.length_total_m


def test_street_topology_and_length_unchanged_but_lts_upgraded():
    ctx = fake_osm_context()
    grown = _grown_over_street(ctx.street, n=4)
    sctx = scenarios.scenario_context(ctx, grown)
    # same graph: node and edge counts and total length identical
    assert sctx.street.n_nodes == ctx.street.n_nodes
    assert sctx.street.n_edges == ctx.street.n_edges
    assert np.isclose(sctx.street.length_total_m, ctx.street.length_total_m)
    # but the grown corridors are now LTS 1 where they were not before
    assert _lts1_length_share(ctx.street) == 0.0
    assert _lts1_length_share(sctx.street) > 0.0


def test_empty_grown_leaves_street_untouched():
    ctx = fake_osm_context()
    empty = gpd.GeoDataFrame(
        {"highway": [], "geometry": [], "length": []}, geometry="geometry", crs=ctx.street.crs
    )
    sctx = scenarios.scenario_context(ctx, empty)
    assert _lts1_length_share(sctx.street) == _lts1_length_share(ctx.street)


def test_registry_runs_clean_on_scenario_context():
    ctx = fake_osm_context()
    sctx = scenarios.scenario_context(ctx, _grown_over_street(ctx.street))
    results = REGISTRY.run(sctx)
    errored = [(r.name, r.detail) for r in results if r.status == "error"]
    assert not errored, f"metrics errored on scenario context: {errored}"


def test_grown_edges_gdf_dedupes_projects_and_carries_ids():
    """Reciprocal directions collapse; output is projected and carries OSM ids."""
    g = nx.MultiDiGraph(crs="EPSG:4326")
    g.add_node(1, x=-1.6000, y=55.0000)
    g.add_node(2, x=-1.6010, y=55.0010)
    g.add_node(3, x=-1.6020, y=55.0000)
    g.add_edge(1, 2, highway="cycleway", osmid=100)
    g.add_edge(2, 1, highway="cycleway", osmid=100)  # reciprocal -> deduped
    g.add_edge(2, 3, highway="cycleway", osmid=101)
    gdf = scenarios._grown_edges_gdf(g, "EPSG:27700")
    assert len(gdf) == 2  # {1,2} and {2,3}; the reciprocal dropped
    assert gdf.crs is not None and not gdf.crs.is_geographic
    assert (gdf["length"] > 0).all()
    assert set(gdf["highway"]) == {"cycleway"}
    assert {"osm_u", "osm_v", "osmid"} <= set(gdf.columns)


# --- OSM node-pair matching (the old-repo-faithful upgrade) -------------------


def _street_with_ids():
    """Three collinear residential segments (LTS 2) that all share one OSM way id."""
    pts = {1: (0, 0), 2: (100, 0), 3: (200, 0), 4: (300, 0)}
    rows = [
        {"highway": "residential", "osm_u": a, "osm_v": b, "osmid": 100,
         "geometry": LineString([pts[a], pts[b]])}
        for a, b in [(1, 2), (2, 3), (3, 4)]
    ]
    return scenarios._build_layer(gpd.GeoDataFrame(rows, crs="EPSG:27700"))


def _grown_segment(u, v, osmid, coords) -> gpd.GeoDataFrame:
    g = gpd.GeoDataFrame(
        [{"highway": "cycleway", "osm_u": u, "osm_v": v, "osmid": osmid,
          "geometry": LineString(coords)}],
        crs="EPSG:27700",
    )
    g["length"] = g.geometry.length
    return g


def test_street_upgrade_matches_node_pair_not_whole_way():
    """Only the used segment upgrades -- NOT the whole OSM way (node-pair > osmid)."""
    street = _street_with_ids()
    grown = _grown_segment(1, 2, 100, [(0, 0), (100, 0)])  # uses one segment of way 100
    up = scenarios._upgrade_street(street, grown, tol_m=15.0, cover_frac=0.5)
    # exactly one of the three segments of way 100 becomes LTS 1
    assert int((up.edges["lts"] == 1).sum()) == 1
    upgraded = up.edges.loc[up.edges["lts"] == 1]
    pairs = {
        frozenset((a, b))
        for a, b in zip(upgraded["osm_u"], upgraded["osm_v"], strict=True)
    }
    assert pairs == {frozenset((1, 2))}


def test_street_upgrade_spatial_fallback_for_drifted_ids():
    """A grown segment whose node ids match nothing still upgrades via geometry."""
    street = _street_with_ids()
    # geometry sits on the (2,3) segment, but the node ids are 'drifted' (unknown)
    grown = _grown_segment(9990, 9991, 777, [(100, 0), (200, 0)])
    up = scenarios._upgrade_street(street, grown, tol_m=15.0, cover_frac=0.5)
    assert int((up.edges["lts"] == 1).sum()) == 1
