"""What-if: merge a Chapter-5 grown cycle network into a real place and re-measure.

For the Tyne & Wear boroughs the Chapter-5 growth model produced a proposed
protected cycle network (`bikenwgrowth`, `current_ltn_scenario`). This module
answers: *if that network were built, how does the place's network form shift,
and would the regression now predict a higher cycling rate?* It is the mirror
image of the §2 invariant -- the same metric code runs on the merged network.

The merge (user-specified, 2026-07-20): the grown corridors are protected cycle
infrastructure added *to existing streets* (like a kerb-separated track along the
road), so
  - **road**  layer: unchanged (the drive network is untouched);
  - **bike**  layer: grows -- the grown corridors are added as new protected
    infrastructure, changing its length, circuity, connectivity and density;
  - **street** layer: same topology and total length, but every street edge that
    lies on a grown corridor has its LTS dropped to 1 in place (no parallel
    length added), so the stress-coverage and routing metrics improve while the
    structural metrics (grid-ness, circuity, node counts) stay put.

**Corridor matching is by OSM identity, not geometry** (following the old repo's
`04-analyse-grown-networks.ipynb`, which merged on `['u','v','key']`). The growth
model built the grown network on the same OSM graph, so a grown segment shares its
endpoint OSM node ids (and way `osmid`) with the base network. Matching on the
undirected OSM node *pair* is exact and per-segment -- crucially finer than the way
`osmid`, since one OSM way spans many segments (up to ~184 here) and the grown
network may use only part of it. cycleform's canonical nodes are re-noded from
geometry, so we carry the original OSM ids (`osm_u`, `osm_v`, `osmid`) alongside as
edge columns; metric values are therefore identical to the main pipeline. A
**spatial fallback** (buffer + coverage) catches the minority of grown segments
whose node ids drifted between the growth snapshot and the current OSM fetch.

Grown geometry is reconstructed as straight segments between the grown graph's OSM
nodes (the pickle stores no edge geometry). Baseline and scenario are both measured
from the *same* freshly-built context, so a metric shift is attributable only to
the merge, not to a re-fetch.
"""

from __future__ import annotations

import logging
import pickle
import time
from dataclasses import dataclass

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from shapely.geometry import LineString

from cycleform.config import settings
from cycleform.lts import add_lts
from cycleform.metrics import REGISTRY
from cycleform.metrics.base import Network, PlaceContext
from cycleform.metrics.registry import results_to_frame
from cycleform.networks import all_edges, is_bike_infrastructure, is_cyclable, road_network
from cycleform.osm import configure_osmnx
from cycleform.places import resolve_boundary
from cycleform.results import _safe_name
from cycleform.simplify import renode

log = logging.getLogger(__name__)


# --- loading the grown network ------------------------------------------------


def grown_pickle_path(
    growth_placeid: str,
    *,
    prune_measure: str | None = None,
    poi_source: str | None = None,
    scenario: str | None = None,
):
    """Path to a grown-network pickle in the Chapter-5 results tree (read-only)."""
    prune_measure = prune_measure or settings.scenario_prune_measure
    poi_source = poi_source or settings.scenario_poi_source
    scenario = scenario or settings.scenario_name
    fname = f"{growth_placeid}_poi_{poi_source}_{prune_measure}_weighted_{scenario}.pickle"
    return settings.grown_results_dir / growth_placeid / scenario / fname


def load_grown_graph(growth_placeid: str, *, quantile_index: int = -1, **kw) -> nx.MultiDiGraph:
    """The grown network at one prune quantile (default -1 = the fully-grown graph).

    The pickle is a dict; `GTs` is the list of greedy-triangulation graphs at
    increasing prune quantiles, so `GTs[-1]` is the complete grown network.
    """
    path = grown_pickle_path(growth_placeid, **kw)
    with path.open("rb") as fh:
        obj = pickle.load(fh)
    return obj["GTs"][quantile_index]


def _grown_edges_gdf(graph: nx.MultiDiGraph, target_crs) -> gpd.GeoDataFrame:
    """Grown edges as projected cycleways, carrying their OSM ids for matching.

    Columns: `osm_u`, `osm_v` (endpoint OSM node ids), `osmid` (way id), `highway`
    (=cycleway), `geometry` (straight node-to-node), `length`. Reciprocal
    MultiDiGraph directions are de-duplicated; zero-length / coordinate-less edges
    dropped.
    """
    xs = nx.get_node_attributes(graph, "x")
    ys = nx.get_node_attributes(graph, "y")
    seen: set[tuple] = set()
    recs: list[dict] = []
    for u, v, data in graph.edges(data=True):
        if u not in xs or v not in xs:
            continue
        key = (u, v) if u <= v else (v, u)
        if key in seen:
            continue
        seen.add(key)
        recs.append(
            {
                "osm_u": u,
                "osm_v": v,
                "osmid": data.get("osmid"),
                "highway": "cycleway",
                "geometry": LineString([(xs[u], ys[u]), (xs[v], ys[v])]),
            }
        )
    src_crs = graph.graph.get("crs", "EPSG:4326")
    gdf = gpd.GeoDataFrame(recs, crs=src_crs).to_crs(target_crs)
    gdf["length"] = gdf.geometry.length
    return gdf[gdf["length"] > 0].reset_index(drop=True)


def load_grown_edges(growth_placeid: str, target_crs, *, quantile_index: int = -1, **kw):
    """Grown-network edges for one place, projected to `target_crs`, as cycleways."""
    graph = load_grown_graph(growth_placeid, quantile_index=quantile_index, **kw)
    return _grown_edges_gdf(graph, target_crs)


# --- OSM-id-preserving layer construction -------------------------------------

# Columns carried onto a scenario Network's edges: the canonical (highway,
# geometry) plus the original OSM ids used for exact corridor matching. renode
# preserves any of these it is handed and still assigns cycleform's canonical
# node ids, so metric values match the main pipeline exactly.
_KEEP_COLS = ("highway", "osm_u", "osm_v", "osmid")


def _uv_key(a, b) -> frozenset:
    """Undirected OSM node-pair key (order-independent), for matching edges."""
    return frozenset((a, b))


def _build_layer(edges: gpd.GeoDataFrame) -> Network:
    """A canonical, LTS-tagged Network that also carries OSM ids for matching."""
    keep = [c for c in _KEEP_COLS if c in edges.columns] + ["geometry"]
    nodes, e = renode(edges[keep])
    return Network(nodes=nodes, edges=add_lts(e))


def _osm_id_layers(polygon_wgs84, crs) -> tuple[Network, Network]:
    """Bike + cyclable-street Networks that retain OSM (u, v) and osmid columns.

    Same source and filters as `ingest.context_from_osm` (the one `all` fetch,
    `is_bike_infrastructure` / `is_cyclable`), so the resulting metrics are
    identical -- only the extra id columns differ.
    """
    allp = all_edges(polygon_wgs84, crs).reset_index().rename(columns={"u": "osm_u", "v": "osm_v"})
    bike = _build_layer(allp[is_bike_infrastructure(allp)])
    street = _build_layer(allp[is_cyclable(allp)])
    return bike, street


def scenario_base_context(spec: ScenarioSpec, *, simplify: bool = True) -> PlaceContext:
    """Baseline PlaceContext for a borough, with OSM ids kept on bike/street.

    Mirrors `ingest.context_from_osm` but preserves OSM node ids so the grown
    network can be matched by identity. Road layer is built identically to the
    main pipeline.
    """
    configure_osmnx()
    boundary = resolve_boundary(spec.query, place_id=spec.place_id)
    log.info("%s: boundary %.1f km² in %s", spec.place_id, boundary.area_km2, boundary.crs)
    road = road_network(boundary.geometry_wgs84, boundary.crs, simplify=simplify)
    bike, street = _osm_id_layers(boundary.geometry_wgs84, boundary.crs)
    return PlaceContext(
        place_id=spec.place_id,
        boundary=boundary.geometry,
        built_up_area_km2=boundary.area_km2,
        source="osm",
        snapshot_date=settings.snapshot_date,
        road=road,
        bike=bike,
        street=street,
        meta={
            "query": spec.query,
            "country": spec.country,
            "crs": str(boundary.crs),
            "area_note": boundary.area_note,
        },
    )


# --- building the merged (scenario) context -----------------------------------


def _merged_bike(bike: Network, grown_edges: gpd.GeoDataFrame) -> Network:
    """Baseline cycle network plus the grown corridors as new protected infra.

    Grown corridors already present as cycle infrastructure (same OSM node pair)
    are dropped so their length is not double-counted -- the inclusive merge from
    the old repo's notebook 04. Where OSM ids are absent (e.g. synthetic tests)
    every grown corridor is simply appended.
    """
    base_cols = [c for c in (*_KEEP_COLS, "geometry") if c in bike.edges.columns]
    grown_cols = [c for c in (*_KEEP_COLS, "geometry") if c in grown_edges.columns]
    new = grown_edges
    ids = {"osm_u", "osm_v"}
    if ids <= set(bike.edges.columns) and ids <= set(grown_edges.columns):
        base_uv = {
            _uv_key(a, b)
            for a, b in zip(bike.edges["osm_u"], bike.edges["osm_v"], strict=True)
        }
        keep = [
            _uv_key(a, b) not in base_uv
            for a, b in zip(grown_edges["osm_u"], grown_edges["osm_v"], strict=True)
        ]
        new = grown_edges[keep]
    merged = pd.concat([bike.edges[base_cols], new[grown_cols]], ignore_index=True)
    merged = gpd.GeoDataFrame(merged, geometry="geometry", crs=bike.crs)
    return _build_layer(merged)


def _upgrade_street(
    street: Network, grown_edges: gpd.GeoDataFrame, tol_m: float, cover_frac: float
) -> Network:
    """Street network with grown corridors' LTS set to 1 in place (length unchanged).

    Primary match is exact on the undirected OSM node pair (per-segment, so a
    partly-used way is not wholly upgraded). Grown segments whose node ids match no
    street edge (id drift between snapshots, or genuinely new links) fall back to a
    spatial match: a street edge is upgraded if >= `cover_frac` of its length lies
    within `tol_m` of such a corridor. Topology, geometry and total length are
    identical to the baseline street network -- only the `lts` column changes.
    """
    edges = street.edges.copy()
    if "lts" not in edges.columns:
        edges = add_lts(edges)
    if not len(grown_edges):
        return Network(nodes=street.nodes, edges=edges)

    matched = pd.Series(False, index=edges.index)
    st_has_ids = {"osm_u", "osm_v"} <= set(edges.columns)
    grown_has_ids = {"osm_u", "osm_v"} <= set(grown_edges.columns)
    grown_uv = (
        [_uv_key(a, b) for a, b in zip(grown_edges["osm_u"], grown_edges["osm_v"], strict=True)]
        if grown_has_ids
        else []
    )
    st_uv_set: set = set()
    if st_has_ids and grown_has_ids:
        grown_uv_set = set(grown_uv)
        st_uv = [_uv_key(a, b) for a, b in zip(edges["osm_u"], edges["osm_v"], strict=True)]
        st_uv_set = set(st_uv)
        matched = pd.Series([uv in grown_uv_set for uv in st_uv], index=edges.index)

    # spatial fallback for grown corridors not matched to any street edge by id
    if grown_has_ids:
        residual = grown_edges[[uv not in st_uv_set for uv in grown_uv]]
    else:
        residual = grown_edges  # no ids at all -> match everything spatially
    if len(residual):
        buf = residual.geometry.union_all().buffer(tol_m)
        covered = edges.geometry.intersection(buf).length
        frac = (covered / edges["length"].replace(0, np.nan)).fillna(0.0)
        matched = matched | (frac >= cover_frac)

    edges.loc[matched, "lts"] = np.int8(1)
    return Network(nodes=street.nodes, edges=edges)


def scenario_context(
    ctx: PlaceContext,
    grown_edges: gpd.GeoDataFrame,
    *,
    place_id: str | None = None,
    tol_m: float | None = None,
    cover_frac: float | None = None,
) -> PlaceContext:
    """A PlaceContext with the grown cycle network merged into `ctx`.

    Road unchanged; bike gains the grown corridors; street keeps its topology but
    the grown corridors become LTS 1 (see module docstring). Metrics run on this
    exactly as on any other context (§2).
    """
    tol_m = settings.scenario_match_tol_m if tol_m is None else tol_m
    cover_frac = settings.scenario_cover_frac if cover_frac is None else cover_frac
    return PlaceContext(
        place_id=place_id or f"{ctx.place_id} [grown]",
        boundary=ctx.boundary,
        built_up_area_km2=ctx.built_up_area_km2,
        source="grown",
        snapshot_date=ctx.snapshot_date,
        road=ctx.road,
        bike=_merged_bike(ctx.bike, grown_edges),
        street=_upgrade_street(ctx.street, grown_edges, tol_m, cover_frac),
        pop=ctx.pop,
        dem=ctx.dem,
        meta={**ctx.meta, "scenario": settings.scenario_name, "base_place_id": ctx.place_id},
    )


# --- the Tyne & Wear run ------------------------------------------------------


@dataclass
class ScenarioSpec:
    """One borough: its growth-results id, its OSM query, and output id."""

    growth_placeid: str
    query: str
    place_id: str
    country: str = "UK"


def _tw(growth_placeid: str, name: str) -> ScenarioSpec:
    """A Tyne & Wear borough: growth-results id + its 'Name, United Kingdom' query."""
    query = f"{name}, United Kingdom"
    return ScenarioSpec(growth_placeid, query, query, "UK")


TYNE_AND_WEAR: list[ScenarioSpec] = [
    _tw("newcastle", "Newcastle upon Tyne"),
    _tw("gateshead", "Gateshead"),
    _tw("sunderland", "Sunderland"),
    _tw("north_tyneside", "North Tyneside"),
    _tw("south_tyneside", "South Tyneside"),
]


def _scenario_path(place_id: str, variant: str):
    return settings.results_scenarios / f"{_safe_name(place_id)}__{variant}.csv"


def _save_variant(
    ctx: PlaceContext, results, variant: str, spec: ScenarioSpec, grown_edges: int
) -> None:
    settings.results_scenarios.mkdir(parents=True, exist_ok=True)
    frame = results_to_frame(results)
    frame.insert(0, "grown_edges", grown_edges)
    frame.insert(0, "metric_version", settings.metric_version)
    frame.insert(0, "variant", variant)
    frame.insert(0, "country", spec.country)
    frame.insert(0, "place_id", spec.place_id)  # base id for both variants
    frame.to_csv(_scenario_path(spec.place_id, variant), index=False)


def _cached(spec: ScenarioSpec) -> bool:
    """Both variants already written at the current metric_version."""
    for variant in ("baseline", "scenario"):
        p = _scenario_path(spec.place_id, variant)
        if not p.exists():
            return False
        head = pd.read_csv(p, nrows=1)
        if str(head.get("metric_version", pd.Series(["?"])).iloc[0]) != settings.metric_version:
            return False
    return True


def run_scenario(spec: ScenarioSpec, *, simplify: bool = True, force: bool = False) -> dict:
    """Build one borough's baseline + grown-scenario metrics and save both.

    Baseline and scenario are measured from the same freshly-built context, so the
    grown pickle is the only difference between the two rows.
    """
    if not force and _cached(spec):
        return {"place_id": spec.place_id, "status": "cached", "grown_edges": 0, "seconds": 0.0}
    t0 = time.perf_counter()
    try:
        ctx = scenario_base_context(spec, simplify=simplify)
        grown = load_grown_edges(spec.growth_placeid, ctx.road.crs)
        sctx = scenario_context(ctx, grown, place_id=f"{spec.place_id} [grown]")
        _save_variant(ctx, REGISTRY.run(ctx), "baseline", spec, len(grown))
        _save_variant(sctx, REGISTRY.run(sctx), "scenario", spec, len(grown))
        log.info(
            "%s: baseline bike %d edges -> scenario bike %d edges (+%d grown)",
            spec.place_id, ctx.bike.n_edges, sctx.bike.n_edges, len(grown),
        )
        return {
            "place_id": spec.place_id,
            "status": "ok",
            "grown_edges": len(grown),
            "seconds": round(time.perf_counter() - t0, 1),
        }
    except Exception as exc:  # a failed borough is logged, never kills the run
        log.exception("%s scenario failed", spec.place_id)
        return {
            "place_id": spec.place_id,
            "status": "failed",
            "grown_edges": 0,
            "seconds": round(time.perf_counter() - t0, 1),
            "detail": f"{type(exc).__name__}: {exc}",
        }


def run_scenarios(
    specs: list[ScenarioSpec] | None = None, *, simplify: bool = True, force: bool = False
) -> pd.DataFrame:
    """Run the grown-network comparison for a list of boroughs (default Tyne & Wear)."""
    specs = specs or TYNE_AND_WEAR
    rows = []
    for i, spec in enumerate(specs, 1):
        log.info("[%d/%d] scenario %s", i, len(specs), spec.place_id)
        rows.append(run_scenario(spec, simplify=simplify, force=force))
    status = pd.DataFrame(rows)
    log.info("scenarios done: %s", status["status"].value_counts().to_dict())
    return status


# --- reading the results back -------------------------------------------------


def scenario_long() -> pd.DataFrame:
    """Tidy long table of every saved scenario cell (ok cells only)."""
    files = sorted(settings.results_scenarios.glob("*__*.csv"))
    if not files:
        return pd.DataFrame()
    long = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    return long[long["status"] == "ok"].copy()


def scenario_wide(variant: str) -> pd.DataFrame:
    """Wide (place_id x metric) table for one variant, with a `country` column."""
    long = scenario_long()
    d = long[long["variant"] == variant]
    wide = d.pivot_table(index="place_id", columns="metric", values="value", aggfunc="first")
    wide.insert(0, "country", d.groupby("place_id")["country"].first())
    return wide.rename_axis(columns=None)


def build_scenario_table() -> pd.DataFrame:
    """Per-(place, metric) baseline vs scenario with the delta. The comparison table."""
    long = scenario_long()
    if long.empty:
        return long
    piv = long.pivot_table(
        index=["place_id", "country", "metric"], columns="variant", values="value", aggfunc="first"
    ).reset_index()
    piv = piv.rename_axis(columns=None)
    if "baseline" in piv.columns and "scenario" in piv.columns:
        piv["delta"] = piv["scenario"] - piv["baseline"]
    return piv
