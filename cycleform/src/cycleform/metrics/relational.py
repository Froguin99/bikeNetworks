"""Relational metrics (CLAUDE.md §5c) -- the cycle network measured against the
road network it inhabits. This is the project's headline novelty.

These are PlaceMetrics: they read more than one layer of the context. Each
declares `requires` so a place missing a layer yields a logged NaN, not a zero.
"""

from __future__ import annotations

import numpy as np
import rustworkx as rx

from cycleform import geometry as geo
from cycleform.config import settings
from cycleform.metrics.base import Network, PlaceContext
from cycleform.metrics.registry import place_metric


def _lts_share(ctx: PlaceContext, mask_fn) -> float:
    """Length-weighted LTS share on the cyclable STREET network (incl. cycle infra)."""
    edges = ctx.street.edges
    total = edges["length"].sum()
    if total == 0:
        return float("nan")
    return float(edges.loc[mask_fn(edges["lts"]), "length"].sum() / total)


@place_metric("low_stress_coverage", requires={"street"})
def low_stress_coverage(ctx: PlaceContext) -> float:
    """Share of the cyclable street network that is low-stress (LTS <= 2).

    On the street network (roads + cycle infrastructure), so dedicated cycleways
    (LTS 1) count -- unlike a road-only measure, which ignored them entirely.
    """
    return _lts_share(ctx, lambda lts: lts <= 2)


@place_metric("lts1_coverage", requires={"street"})
def lts1_coverage(ctx: PlaceContext) -> float:
    """Share of the cyclable street network at LTS 1 (dedicated cycle infra + quietest)."""
    return _lts_share(ctx, lambda lts: lts == 1)


@place_metric("lts2_coverage", requires={"street"})
def lts2_coverage(ctx: PlaceContext) -> float:
    """Share of the cyclable street network at LTS 2 (mostly residential streets)."""
    return _lts_share(ctx, lambda lts: lts == 2)


@place_metric("bikeable_length_share", requires={"road", "bike"})
def bikeable_length_share(ctx: PlaceContext) -> float:
    """Cycle-network length as a fraction of road-network length.

    The old "share of road length bikeable" metric. > 1 is possible where cycle
    paths exist off the road network (parks, canals), which is informative.
    """
    road = ctx.road.length_total_m
    if road == 0:
        return float("nan")
    return ctx.bike.length_total_m / road


@place_metric("entropy_gap_kl", requires={"road", "bike"})
def entropy_gap_kl(ctx: PlaceContext) -> float:
    """KL divergence of the cycle network's orientation from the road network's.

    Quantifies "the cycle network only runs N-S while the roads run every way".
    0 means the cycle network points the same way as the roads; larger means it
    is oriented differently (Boeing-style orientation distributions, 36 bins).
    """
    p_bike = geo.orientation_histogram(ctx.bike.edges)
    q_road = geo.orientation_histogram(ctx.road.edges)
    return geo.kl_divergence(p_bike, q_road)


@place_metric("bike_lcc_share_of_road", requires={"road", "bike"})
def bike_lcc_share_of_road(ctx: PlaceContext) -> float:
    """Largest cycle component's length as a fraction of road-network length.

    Fragmentation normalised by city size (via road length, not area): a single
    joined-up cycle network scores high, scattered fragments score low.
    """
    road = ctx.road.length_total_m
    if road == 0:
        return float("nan")
    return ctx.bike.lcc_length_m / road


@place_metric("intersection_ratio_bike_road", requires={"road", "bike"})
def intersection_ratio_bike_road(ctx: PlaceContext) -> float:
    """Cycle-network intersections per road intersection.

    How dense the cycle network's junctions are relative to the street grid it
    sits in -- a size-free measure of how finely the cycle network is woven in.
    """
    road_i = ctx.road.intersection_count
    if road_i == 0:
        return float("nan")
    return ctx.bike.intersection_count / road_i


# Cycle infrastructure on its own alignment, away from motor traffic.
_OFFROAD_HIGHWAY = {"cycleway", "path", "bridleway", "footway", "pedestrian", "track"}


@place_metric("bike_offroad_share", requires={"bike"})
def bike_offroad_share(ctx: PlaceContext) -> float:
    """Share of cycle-network length that is physically separate from roads.

    Length on dedicated/off-road ways (highway=cycleway/path/footway/...) over
    total cycle length; the remainder is on-road tracks alongside traffic. A
    quality-of-separation measure, not just quantity.
    """
    edges = ctx.bike.edges
    total = edges["length"].sum()
    if total == 0 or "highway" not in edges.columns:
        return float("nan")

    def is_offroad(v: object) -> bool:
        if isinstance(v, str):
            return v in _OFFROAD_HIGHWAY
        if isinstance(v, (list, tuple, set)):
            return any(h in _OFFROAD_HIGHWAY for h in v if isinstance(h, str))
        return False

    mask = edges["highway"].map(is_offroad)
    return float(edges.loc[mask, "length"].sum() / total)


def _low_stress_subnetwork(ctx: PlaceContext) -> Network:
    edges = ctx.street.edges
    return ctx.street.subset(edges["lts"] <= 2)


def _modal_sample(ctx: PlaceContext) -> tuple[np.ndarray, float, np.ndarray]:
    """Cached wrapper: modal_directness_gap, low_stress_route_fraction and
    mean_route_lts share the same expensive OD sampling, so compute it once."""
    cached = ctx.meta.get("_modal_sample")
    if cached is None:
        cached = _modal_sample_compute(ctx)
        ctx.meta["_modal_sample"] = cached
    return cached


def _weighted_street_graph(net: Network) -> tuple[rx.PyGraph, dict]:
    """Simple graph with edge payload (actual_length, lts_cost = length x LTS, lts).

    Parallel edges collapse to the lowest lts_cost one. The cyclist routes to
    minimise lts_cost (avoid stress); the shortest baseline routes to minimise
    actual_length; distances and the LTS actually ridden are read back per edge.
    """
    best: dict[tuple, tuple[float, float, int]] = {}
    e = net.edges
    lts = e["lts"] if "lts" in e.columns else None
    for i, (u, v, length) in enumerate(zip(e["u"], e["v"], e["length"], strict=True)):
        if u == v:
            continue
        stress = int(lts.iloc[i]) if lts is not None else 1
        cost = float(length) * max(stress, 1)
        key = (u, v) if u <= v else (v, u)
        cur = best.get(key)
        if cur is None or cost < cur[1]:
            best[key] = (float(length), cost, stress)
    g = rx.PyGraph(multigraph=False)
    idx: dict = {}
    for (a, b), payload in best.items():
        for n in (a, b):
            if n not in idx:
                idx[n] = g.add_node(n)
        g.add_edge(idx[a], idx[b], payload)
    return g, idx


def _modal_sample_compute(ctx: PlaceContext) -> tuple[np.ndarray, float, np.ndarray]:
    """Sample OD pairs on the cyclable STREET network. Returns three arrays/values:

    - directness ratios: actual length of the LTS-weighted (low-stress-seeking)
      route / length of the shortest-distance route. >= 1; always defined.
    - low-stress fraction: share of connected pairs that also have a route staying
      entirely on LTS<=2 streets (a hard-filter connectivity signal).
    - route LTS: for each pair, the length-weighted mean LTS ridden along the
      low-stress-seeking route (the stress a cyclist actually experiences).
    All pairs among the sample are used, so ~k^2 comparisons from O(k) trees.
    """
    g, idx = _weighted_street_graph(ctx.street)  # rustworkx PyGraph
    if g.num_nodes() < 2:
        return np.array([]), float("nan"), np.array([])
    low = _low_stress_subnetwork(ctx)
    rng = np.random.default_rng(settings.centrality_seed)
    nodes = list(idx)
    # sample size scales with street length (comparable density across places),
    # clamped so small places stay stable and large ones stay affordable
    length_km = ctx.street.length_total_m / 1000.0
    target = int(round(length_km * settings.modal_od_per_km))
    k = min(max(target, settings.modal_od_min), settings.modal_od_max, len(nodes))
    sample = rng.choice(nodes, size=k, replace=False)
    sample_set = set(sample.tolist())
    low_nodes = set(low.nodes.index)

    ratios: list[float] = []
    route_lts: list[float] = []
    connected = 0
    reachable_low = 0
    for o in sample:
        src = idx[o]
        short = dict(rx.dijkstra_shortest_path_lengths(g, src, edge_cost_fn=lambda p: p[0]))
        paths = dict(rx.dijkstra_shortest_paths(g, src, weight_fn=lambda p: p[1]))
        d_low = low.sssp_lengths(o) if o in low_nodes else {}
        for d in sample_set:
            if d == o:
                continue
            di = idx[d]
            short_len = short.get(di)
            if not short_len or short_len <= 0:
                continue
            connected += 1
            if d in d_low:
                reachable_low += 1
            path = paths.get(di)
            if not path:
                continue
            segs = [g.get_edge_data(a, b) for a, b in zip(path[:-1], path[1:], strict=True)]
            cyc_len = sum(s[0] for s in segs)
            ratios.append(cyc_len / short_len)
            if cyc_len > 0:
                route_lts.append(sum(s[0] * s[2] for s in segs) / cyc_len)
    frac = reachable_low / connected if connected else float("nan")
    return np.asarray(ratios, dtype=float), frac, np.asarray(route_lts, dtype=float)


@place_metric("modal_directness_gap", requires={"street"})
def modal_directness_gap(ctx: PlaceContext) -> float:
    """Median (low-stress-seeking cycling distance / shortest available distance).

    On the cyclable street network, the cyclist routes on an LTS-weighted graph
    (length x LTS, so stressful roads are avoided, matching the Chapter-5
    `sp_lts_distance`), but the route's *actual* length is measured. 1.0 means the
    low-stress route is no longer than the most direct one; 1.9 = nearly double
    the distance to stay comfortable. Sampled OD pairs (config.modal_od_sample).
    """
    ratios, _, _ = _modal_sample(ctx)
    return float(np.median(ratios)) if ratios.size else float("nan")


@place_metric("low_stress_route_fraction", requires={"street"})
def low_stress_route_fraction(ctx: PlaceContext) -> float:
    """Fraction of connected OD pairs with a route entirely on LTS<=2 streets."""
    _, frac, _ = _modal_sample(ctx)
    return frac


@place_metric("mean_route_lts", requires={"street"})
def mean_route_lts(ctx: PlaceContext) -> float:
    """Typical stress a cyclist experiences on a sensible route.

    Routes low-stress-seeking paths between sampled OD pairs on the street
    network, takes each route's length-weighted mean LTS (a long LTS-4 stretch
    weighs more than a short one), and returns the median over pairs. Lower = a
    rider can get around mostly on comfortable streets.
    """
    _, _, route_lts = _modal_sample(ctx)
    return float(np.median(route_lts)) if route_lts.size else float("nan")
