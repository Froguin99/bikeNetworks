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
    # results_to_frame already carries the context's place_id (which for the
    # scenario variant is "<place> [grown]"); overwrite it with the base id so
    # both variants share one id and build_scenario_table can pair them.
    frame["place_id"] = spec.place_id
    frame.insert(0, "grown_edges", grown_edges)
    frame.insert(0, "metric_version", settings.metric_version)
    frame.insert(0, "variant", variant)
    frame.insert(0, "country", spec.country)
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


# --- growth curve: form / prediction vs DISTANCE INVESTED, over prune stages ----
#
# The grown pickle holds ~100 graphs GTs[i] at increasing prune quantiles (GTs[-1] =
# fully grown). Sweeping them shows how network form / predicted cycling rate improve
# as more of the proposed network is built. The x-axis is DISTANCE INVESTED, not the
# grown network's size: grown corridors that already exist as cycle infrastructure
# (same OSM node pair) cost nothing, so only the genuinely-new length is counted
# (mirrors the _merged_bike de-dup). This finds the best trade-off (predicted gain per
# km built).

# Compact set of metrics tracked along the curve (the full metric set is still
# computed for the prediction).
CURVE_METRICS = [
    "bikeable_length_share", "bike_lcc_share_of_road", "low_stress_coverage",
    "low_stress_route_fraction", "mean_route_lts", "cycle_network_density_km2",
    "circuity_avg_bike", "modal_directness_gap",
]


def _invested_km(bike: Network, grown_edges: gpd.GeoDataFrame) -> float:
    """New protected length (km) the grown corridors ADD -- grown minus the corridors
    the base cycle network already provides (matched by undirected OSM node pair).

    This is the *distance invested*: grown corridors already present as cycle
    infrastructure cost nothing to build, so they are excluded (same de-dup as
    `_merged_bike`). Falls back to total grown length when OSM ids are absent.
    """
    if grown_edges is None or not len(grown_edges):
        return 0.0
    new = grown_edges
    ids = {"osm_u", "osm_v"}
    if ids <= set(bike.edges.columns) and ids <= set(grown_edges.columns):
        base_uv = {
            _uv_key(a, b) for a, b in zip(bike.edges["osm_u"], bike.edges["osm_v"], strict=True)
        }
        new = grown_edges[[
            _uv_key(a, b) not in base_uv
            for a, b in zip(grown_edges["osm_u"], grown_edges["osm_v"], strict=True)
        ]]
    return round(float(new["length"].sum()) / 1000.0, 3)


def _default_growth_stages(n_total: int) -> list[int]:
    """Clean round prune-stage indices into the GTs list: every 10th (0, 10, 20, ...,
    90), plus the very first grown stage (index 1) and the final network (n_total-1).
    Not linspace 11ths."""
    stages = {0, 1, n_total - 1} | set(range(0, n_total, 10))
    return sorted(s for s in stages if 0 <= s < n_total)


def _curve_row(spec: ScenarioSpec, metrics_frame, *, stage, quantile, invested, predictor, features):
    """One growth-curve row: id, stage, invested km, key metrics, predicted rate."""
    ok = metrics_frame[metrics_frame["status"] == "ok"]
    vals = dict(zip(ok["metric"], ok["value"]))
    row = {
        "place_id": spec.place_id, "stage": stage, "quantile": round(quantile, 3),
        "invested_km": invested,
    }
    for m in CURVE_METRICS:
        row[m] = vals.get(m)
    if predictor is not None:
        from cycleform import models

        wide = pd.DataFrame([vals])
        wide["country"] = spec.country
        row["predicted_rate"] = round(float(models.predict_rate(predictor, wide, features)[0]), 3)
    return row


def run_growth_curve(
    spec: ScenarioSpec,
    *,
    stages: list[int] | None = None,
    simplify: bool = True,
    predictor=None,
    features=None,
) -> pd.DataFrame:
    """Sweep one borough's grown-network prune stages: at each stage merge the grown
    corridors, measure metrics, record the distance invested, and (if a fitted form
    predictor is given) predict the cycling rate.

    `stages` are GTs prune-quantile indices; default = 0, 1, 10, 20, ..., 90, final.
    The base context is built once and reused, so only the merge+measure repeats.
    Returns one row per stage; stage=-1 is the current network (0 km invested).
    """
    configure_osmnx()
    ctx = scenario_base_context(spec, simplify=simplify)
    with grown_pickle_path(spec.growth_placeid).open("rb") as fh:
        n_total = len(pickle.load(fh)["GTs"])
    stages = stages if stages is not None else _default_growth_stages(n_total)
    rows = [_curve_row(spec, results_to_frame(REGISTRY.run(ctx)), stage=-1, quantile=0.0,
                       invested=0.0, predictor=predictor, features=features)]
    for q in stages:
        grown = load_grown_edges(spec.growth_placeid, ctx.road.crs, quantile_index=q)
        invested = _invested_km(ctx.bike, grown)
        sctx = scenario_context(ctx, grown, place_id=f"{spec.place_id} [q{q}]")
        rows.append(_curve_row(spec, results_to_frame(REGISTRY.run(sctx)), stage=q,
                               quantile=round((q + 1) / n_total, 3), invested=invested,
                               predictor=predictor, features=features))
        log.info("%s stage q%d: invested %.1f km, predicted %.2f%%", spec.place_id, q,
                 invested, rows[-1].get("predicted_rate", float("nan")))
    return pd.DataFrame(rows)


def run_growth_curves(
    specs: list[ScenarioSpec] | None = None,
    *,
    stages: list[int] | None = None,
    simplify: bool = True,
    save: bool = True,
) -> pd.DataFrame:
    """Growth-curve sweep for each borough (default Tyne & Wear), predicting cycling
    rate with the form model fit on the full dataset. Saves + returns the combined
    per-(place, stage) table (results/scenarios/growth_curve.csv). `stages` default =
    0, 1, 10, 20, ..., 90, final."""
    from cycleform import models
    from cycleform.report import load_analysis

    specs = specs or TYNE_AND_WEAR
    predictor, features = models.fit_predictor(load_analysis(), feature_set="form")
    frames = []
    for i, spec in enumerate(specs, 1):
        log.info("[%d/%d] growth curve %s", i, len(specs), spec.place_id)
        try:
            df = run_growth_curve(spec, stages=stages, simplify=simplify,
                                  predictor=predictor, features=features)
        except Exception:  # a failed borough is logged, never kills the multi-hour run
            log.exception("%s growth curve failed", spec.place_id)
            continue
        frames.append(df)
        if save:  # save incrementally so a long run keeps partial progress
            settings.results_scenarios.mkdir(parents=True, exist_ok=True)
            pd.concat(frames, ignore_index=True).to_csv(
                settings.results_scenarios / "growth_curve.csv", index=False
            )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_growth_curve() -> pd.DataFrame:
    """The saved growth-curve table (results/scenarios/growth_curve.csv), or empty."""
    p = settings.results_scenarios / "growth_curve.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def _elbow_index(km: np.ndarray, y: np.ndarray) -> int:
    """Index of the diminishing-returns 'knee' on a (distance, benefit) curve.

    The point of greatest perpendicular distance from the chord joining the first
    and last points, after scaling both axes to [0, 1] (Kneedle-style). For a
    saturating curve this is the best trade-off: most benefit captured per km before
    it plateaus. Returns 0 if the curve is degenerate.
    """
    if len(km) < 3 or km.max() == km.min():
        return 0
    xn = (km - km.min()) / (km.max() - km.min())
    yn = (y - y.min()) / (y.max() - y.min()) if y.max() > y.min() else np.zeros_like(y)
    dx, dy = xn[-1] - xn[0], yn[-1] - yn[0]
    denom = np.hypot(dx, dy) or 1.0
    dist = np.abs(dy * (xn - xn[0]) - dx * (yn - yn[0])) / denom
    return int(np.argmax(dist))


def growth_curve_summary(curve: pd.DataFrame, y: str = "predicted_rate") -> pd.DataFrame:
    """Per-place best-trade-off summary of a growth curve.

    For each place: total km invested to fully build the grown network, the total
    predicted-rate gain, and the diminishing-returns elbow -- the km built, the
    fraction of the total km that is, and the fraction of the total predicted gain
    already captured there. The averaged row (place_id 'AVERAGE') means over places.
    """
    rows = []
    for pid, g in curve.groupby("place_id"):
        g = g.sort_values("invested_km")
        km = g["invested_km"].to_numpy(float)
        yv = g[y].to_numpy(float)
        if len(g) < 2 or km.max() == 0:
            continue
        ei = _elbow_index(km, yv)
        total_gain = yv[-1] - yv[0]
        elbow_gain = yv[ei] - yv[0]
        rows.append({
            "place_id": pid,
            "total_invested_km": round(float(km[-1]), 1),
            "total_gain_pp": round(float(total_gain), 2),
            "elbow_km": round(float(km[ei]), 1),
            "elbow_km_frac": round(float(km[ei] / km[-1]), 2) if km[-1] else float("nan"),
            f"elbow_{y}": round(float(yv[ei]), 2),
            "elbow_gain_captured_frac": round(float(elbow_gain / total_gain), 2)
            if total_gain else float("nan"),
        })
    out = pd.DataFrame(rows)
    if len(out) > 1:
        avg = out.drop(columns="place_id").mean(numeric_only=True).round(2)
        avg["place_id"] = "AVERAGE"
        out = pd.concat([out, pd.DataFrame([avg])[out.columns]], ignore_index=True)
    return out


def growth_curve_marginals(curve: pd.DataFrame, y: str = "predicted_rate") -> pd.DataFrame:
    """Per-step marginal analysis of a growth curve: the discrete gain each step adds.

    One row per (place, step): the step's added km, the marginal gain in `y`
    (percentage points), the efficiency (gain per km built), and the % increase in
    `y` relative to the previous step. Answers 'where does each extra km pay off'.
    """
    rows = []
    for pid, g in curve.groupby("place_id"):
        g = g.sort_values("invested_km").reset_index(drop=True)
        for i in range(1, len(g)):
            d_km = float(g["invested_km"][i] - g["invested_km"][i - 1])
            d_gain = float(g[y][i] - g[y][i - 1])
            prev = float(g[y][i - 1])
            rows.append({
                "place_id": pid,
                "stage": g["stage"][i],
                "invested_km": round(float(g["invested_km"][i]), 1),
                y: round(float(g[y][i]), 2),
                "step_km": round(d_km, 1),
                "marginal_gain_pp": round(d_gain, 2),
                "gain_per_km": round(d_gain / d_km, 3) if d_km else float("nan"),
                "pct_increase": round(100 * d_gain / prev, 1) if prev else float("nan"),
            })
    return pd.DataFrame(rows)


def fit_growth_logistic(km, y) -> dict | None:
    """Fit a 4-parameter logistic to (distance invested, benefit).

    y = c + (L - c) / (1 + exp(-k (x - x0))). Returns the floor `c`, asymptote `L`
    (the ceiling the metric saturates toward), inflection `x0` (km of STEEPEST gain
    = where each km buys the most -- the 'best marginal gain'), steepness `k`, a
    `predict` fn, and R². None if it will not fit. For a purely concave (no slow
    start) curve x0 comes out at/below 0, i.e. the best gains are right at the start.
    """
    from scipy.optimize import curve_fit

    km = np.asarray(km, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(km) & np.isfinite(y)
    km, y = km[ok], y[ok]
    if len(km) < 4 or km.max() == km.min():
        return None

    def logistic(x, c, L, x0, k):
        return c + (L - c) / (1 + np.exp(-k * (x - x0)))

    span = km.max() - km.min()
    p0 = [y.min(), y.max(), km[int(np.argmax(np.gradient(y, km)))], 4.0 / span]
    try:
        popt, _ = curve_fit(
            logistic, km, y, p0=p0, maxfev=20000,
            bounds=([y.min() - 5, y.min(), km.min() - span, 1e-4],
                    [y.max() + 5, y.max() + 20, km.max() + span, 10.0]),
        )
    except Exception:
        return None
    resid = y - logistic(km, *popt)
    ss_tot = float(np.sum((y - y.mean()) ** 2)) or 1e-12
    c, ll, x0, k = (float(v) for v in popt)
    return {
        "c": c, "L": ll, "x0": x0, "k": k,
        "r2": round(1 - float(np.sum(resid ** 2)) / ss_tot, 3),
        "predict": lambda x, p=popt: logistic(np.asarray(x, dtype=float), *p),
    }


def growth_logistic_summary(curve: pd.DataFrame, y: str = "predicted_rate") -> pd.DataFrame:
    """Per-place logistic fit of the growth curve: asymptote (ceiling), inflection km
    (steepest / best marginal gain), steepness, and R². Adds an AVERAGE row.
    """
    rows = []
    for pid, g in curve.groupby("place_id"):
        g = g.sort_values("invested_km")
        fit = fit_growth_logistic(g["invested_km"], g[y])
        if fit is None:
            continue
        rows.append({
            "place_id": pid,
            "asymptote_pp": round(fit["L"], 2),
            "inflection_km": round(fit["x0"], 1),
            "steepness_k": round(fit["k"], 4),
            "r2": fit["r2"],
        })
    out = pd.DataFrame(rows)
    if len(out) > 1:
        avg = out.drop(columns="place_id").mean(numeric_only=True).round(2)
        avg["place_id"] = "AVERAGE"
        out = pd.concat([out, pd.DataFrame([avg])[out.columns]], ignore_index=True)
    return out


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
