"""Synthetic networks for tests and the §2 invariant guard.

`grid_network` builds a deterministic k*k lattice as canonical nodes/edges
frames. `fake_grown_context` assembles a PlaceContext that mimics what
`cycleform.scenarios` produces from a Chapter-5 grown network -- the same
schema an OSM place yields -- so tests can prove the registry runs on grown
input without any real growth-model output.
"""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import LineString, Point, box

from cycleform.lts import add_lts
from cycleform.metrics.base import Network, PlaceContext

PROJECTED_CRS = "EPSG:27700"  # British National Grid; metres.


def grid_network(k: int = 4, spacing: float = 100.0, highway: str = "residential") -> Network:
    """A k*k grid graph, nodes `spacing` metres apart, in a projected CRS."""
    idx_of = {(i, j): i * k + j for i in range(k) for j in range(k)}
    nodes = gpd.GeoDataFrame(
        {"geometry": [Point(j * spacing, i * spacing) for i in range(k) for j in range(k)]},
        index=[i * k + j for i in range(k) for j in range(k)],
        crs=PROJECTED_CRS,
    )
    u, v, geoms = [], [], []
    for (i, j), here in idx_of.items():
        for di, dj in ((0, 1), (1, 0)):  # east and north neighbours
            there = idx_of.get((i + di, j + dj))
            if there is not None:
                u.append(here)
                v.append(there)
                geoms.append(
                    LineString([nodes.geometry[here].coords[0], nodes.geometry[there].coords[0]])
                )
    edges = gpd.GeoDataFrame(
        {"u": u, "v": v, "highway": [highway] * len(u), "geometry": geoms}, crs=PROJECTED_CRS
    )
    edges["length"] = edges.geometry.length
    return Network(nodes=nodes, edges=add_lts(edges))


def fake_grown_context(place_id: str = "SYNTH_GROWN", k: int = 4) -> PlaceContext:
    """A PlaceContext standing in for a Chapter-5 grown network.

    Road layer is the full grid with LTS; bike layer is a subset (every other
    edge relabelled cycleway) that is deliberately fragmented; street layer is
    the full cyclable grid (roads + cycle infra) on which LTS/routing metrics run.
    """
    road = grid_network(k)
    bike_edges = road.edges.iloc[::2].copy()
    bike_edges["highway"] = "cycleway"
    bike = Network(nodes=road.nodes, edges=add_lts(bike_edges))
    street = grid_network(k)  # cyclable street network (all residential -> LTS 2)
    minx, miny, maxx, maxy = road.nodes.total_bounds
    boundary = box(minx, miny, maxx, maxy)
    return PlaceContext(
        place_id=place_id,
        boundary=boundary,
        built_up_area_km2=max(boundary.area / 1e6, 1e-6),
        source="grown",
        snapshot_date="synthetic",
        road=road,
        bike=bike,
        street=street,
    )


def fake_osm_context(place_id: str = "SYNTH_OSM", k: int = 4) -> PlaceContext:
    """Same topology as `fake_grown_context` but tagged source='osm'.

    The invariant test builds both and asserts every metric returns identical
    values -- proving metric code never branches on provenance.
    """
    ctx = fake_grown_context(place_id=place_id, k=k)
    ctx.source = "osm"
    return ctx
