"""Structural / morphological metrics computed on a single network.

Each is a NetworkMetric, so the registry runs it on both the road and bike
layers and emits `<name>_road` / `<name>_bike` -- the old repo's suffix scheme.
This is the basic_stats-equivalent suite (n, m, k_avg, lengths, circuity,
self-loops, node-degree structure) plus orientation entropy, linearity and
connectivity (components, LCC, size Gini), computed directly on the canonical
`Network` rather than via osmnx so it runs identically on grown networks (§2).

Densities are normalised by network length (per km of edge), not by area --
built-up area is deliberately not used (a project decision); street length is
the size control.
"""

from __future__ import annotations

import numpy as np

from cycleform import geometry as geo
from cycleform.metrics.base import Network
from cycleform.metrics.registry import network_metric

# --- size ------------------------------------------------------------------


@network_metric("n_nodes")
def n_nodes(net: Network) -> float:
    return float(net.n_nodes)


@network_metric("n_edges")
def n_edges(net: Network) -> float:
    return float(net.n_edges)


@network_metric("length_km")
def length_km(net: Network) -> float:
    return net.length_total_m / 1000.0


@network_metric("edge_length_avg_m")
def edge_length_avg_m(net: Network) -> float:
    return float(net.edges["length"].mean()) if net.n_edges else float("nan")


# --- connectivity / degree structure ---------------------------------------


@network_metric("k_avg")
def k_avg(net: Network) -> float:
    """Mean node degree = 2m / n."""
    return 2.0 * net.n_edges / net.n_nodes if net.n_nodes else float("nan")


@network_metric("intersection_count")
def intersection_count(net: Network) -> float:
    return float(net.intersection_count)


@network_metric("intersection_density_per_km")
def intersection_density_per_km(net: Network) -> float:
    """True intersections per km of network length (size-normalised, no area)."""
    km = net.length_total_m / 1000.0
    return net.intersection_count / km if km > 0 else float("nan")


def _degree_proportion(net: Network, k: int) -> float:
    if net.n_nodes == 0:
        return float("nan")
    if k == 4:  # fold 4-and-above together, as high-degree nodes are rare
        return float((net.degree >= 4).sum()) / net.n_nodes
    return float((net.degree == k).sum()) / net.n_nodes


@network_metric("dead_end_proportion")
def dead_end_proportion(net: Network) -> float:
    """Share of nodes that are dead-ends (degree 1). High => low permeability."""
    return _degree_proportion(net, 1)


@network_metric("three_way_proportion")
def three_way_proportion(net: Network) -> float:
    return _degree_proportion(net, 3)


@network_metric("four_way_proportion")
def four_way_proportion(net: Network) -> float:
    """Share of nodes with degree >= 4 (grid-like crossings)."""
    return _degree_proportion(net, 4)


@network_metric("self_loop_proportion")
def self_loop_proportion(net: Network) -> float:
    if net.n_edges == 0:
        return float("nan")
    return float((net.edges["u"] == net.edges["v"]).sum()) / net.n_edges


# --- shape ------------------------------------------------------------------


@network_metric("circuity_avg")
def circuity_avg(net: Network) -> float:
    return geo.circuity(net.edges)


@network_metric("linearity_mean")
def linearity_mean(net: Network) -> float:
    """Mean of per-edge straightness (euclidean / along-edge length), in [0, 1]."""
    if net.n_edges == 0:
        return float("nan")
    ratio = geo.euclidean_length(net.edges) / net.edges["length"].to_numpy()
    return float(np.nanmean(np.clip(ratio, 0, 1)))


@network_metric("linearity_median")
def linearity_median(net: Network) -> float:
    if net.n_edges == 0:
        return float("nan")
    ratio = geo.euclidean_length(net.edges) / net.edges["length"].to_numpy()
    return float(np.nanmedian(np.clip(ratio, 0, 1)))


@network_metric("orientation_entropy")
def orientation_entropy(net: Network) -> float:
    """Shannon entropy of edge bearings (Boeing 2019). High => less gridded."""
    return geo.orientation_entropy(net.edges)


@network_metric("orientation_order")
def orientation_order(net: Network) -> float:
    """Boeing orientation order phi: 1 = perfect grid, 0 = disordered. Griddedness."""
    return geo.orientation_order(net.edges)


# --- connectivity indices (classic transport-network topology) -------------


@network_metric("connectivity_ratio")
def connectivity_ratio(net: Network) -> float:
    """Connectivity ratio (the classic gamma index): edges / max planar edges.

    m / (3(n-2)), in [0, 1]. A tree scores low; a fully meshed grid approaches 1.
    Cycle networks tend to be tree-like (low); road grids are more connected.
    """
    if net.n_nodes < 3:
        return float("nan")
    return net.n_edges / (3.0 * (net.n_nodes - 2))


@network_metric("meshedness")
def meshedness(net: Network) -> float:
    """Meshedness (the classic alpha index): independent loops over the maximum.

    (m - n + p) / (2n - 5), p = components; in [0, 1]. 0 = no loops (a tree,
    every trip has one path); higher = more alternative routes -- directly
    relevant to whether a cyclist has a choice of low-stress paths.
    """
    if net.n_nodes < 3:
        return float("nan")
    return (net.n_edges - net.n_nodes + net.n_components) / (2.0 * net.n_nodes - 5.0)


# --- fragmentation ----------------------------------------------------------


@network_metric("n_components")
def n_components(net: Network) -> float:
    return float(net.n_components)


@network_metric("components_per_km")
def components_per_km(net: Network) -> float:
    """Disconnected components per km of network -- fragmentation, size-normalised."""
    km = net.length_total_m / 1000.0
    return net.n_components / km if km > 0 else float("nan")


@network_metric("lcc_length_share")
def lcc_length_share(net: Network) -> float:
    """Fraction of network length in the largest connected component."""
    total = net.length_total_m
    return net.lcc_length_m / total if total > 0 else float("nan")


@network_metric("lcc_length_km")
def lcc_length_km(net: Network) -> float:
    """Absolute length of the largest connected component (km)."""
    return net.lcc_length_m / 1000.0


@network_metric("component_size_gini")
def component_size_gini(net: Network) -> float:
    """Gini of component lengths. 0 = even, ->1 = one component dominates.

    NaN when there is a single component (inequality undefined / degenerate).
    """
    lengths = net.component_lengths_m
    if len(lengths) < 2:
        return float("nan")
    return geo.gini(lengths)
