"""Sampled centrality metrics -- the expensive ones.

The old repo skipped these unless `fast_mode` was off. Here they always run but
on a representative sample of source nodes (config.centrality_sample), seeded
for reproducibility. Graphs at or below the sample size are computed exactly.
Betweenness uses networkx's k-source estimator; closeness averages exact
single-source shortest paths over the sample (an unbiased estimator of the mean).
"""

from __future__ import annotations

import networkx as nx
import numpy as np
import rustworkx as rx

from cycleform.config import settings
from cycleform.metrics.base import Network
from cycleform.metrics.registry import network_metric


def _sample_indices(n: int, k: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if n <= k:
        return np.arange(n)
    return rng.choice(n, size=k, replace=False)


@network_metric("betweenness_mean")
def betweenness_mean(net: Network) -> float:
    """Mean node betweenness (length-weighted, k-sampled sources)."""
    n = net.n_nodes
    if n < 3:
        return float("nan")
    k = min(settings.centrality_sample, n)
    bc = nx.betweenness_centrality(
        nx.Graph(net.nx_graph),
        k=k,
        weight="length",
        seed=settings.centrality_seed,
        normalized=True,
    )
    return float(np.mean(list(bc.values())))


@network_metric("betweenness_median")
def betweenness_median(net: Network) -> float:
    n = net.n_nodes
    if n < 3:
        return float("nan")
    k = min(settings.centrality_sample, n)
    bc = nx.betweenness_centrality(
        nx.Graph(net.nx_graph),
        k=k,
        weight="length",
        seed=settings.centrality_seed,
        normalized=True,
    )
    return float(np.median(list(bc.values())))


def _sampled_closeness(net: Network) -> np.ndarray:
    """Closeness for a sample of source nodes (Wasserman-Faust, disconnection-aware)."""
    g = net.graph
    n = net.n_nodes
    idx = _sample_indices(n, settings.centrality_sample, settings.centrality_seed)
    out = []
    for s in idx:
        dist = rx.dijkstra_shortest_path_lengths(g, int(s), edge_cost_fn=float)
        reach = len(dist)  # reachable others (excludes source)
        total = sum(dist.values())
        if reach == 0 or total == 0:
            out.append(0.0)
        else:
            out.append((reach / (n - 1)) * (reach / total))
    return np.asarray(out, dtype=float)


@network_metric("closeness_mean")
def closeness_mean(net: Network) -> float:
    if net.n_nodes < 2:
        return float("nan")
    return float(np.mean(_sampled_closeness(net)))


@network_metric("closeness_median")
def closeness_median(net: Network) -> float:
    if net.n_nodes < 2:
        return float("nan")
    return float(np.median(_sampled_closeness(net)))


@network_metric("clustering_mean")
def clustering_mean(net: Network) -> float:
    """Mean node clustering coefficient (exact; cheap even on large graphs)."""
    if net.n_nodes < 3:
        return float("nan")
    return float(nx.average_clustering(nx.Graph(net.nx_graph)))
