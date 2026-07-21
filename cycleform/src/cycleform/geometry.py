"""Geometry helpers shared across metrics: bearings, orientation, circuity, Gini.

All operate on an edges GeoDataFrame (projected, LineString geometry) or plain
arrays, so they are network-source-agnostic (§2).
"""

from __future__ import annotations

import numpy as np
from geopandas import GeoDataFrame

BEARING_BINS = 36  # 10-degree bins over 0-360, following Boeing (2019).


def edge_endpoints(edges: GeoDataFrame) -> tuple[np.ndarray, np.ndarray]:
    """First and last coordinate of each edge as (n, 2) arrays."""
    start = np.array([g.coords[0] for g in edges.geometry])
    end = np.array([g.coords[-1] for g in edges.geometry])
    return start, end


def euclidean_length(edges: GeoDataFrame) -> np.ndarray:
    """Straight-line endpoint distance per edge (metres)."""
    start, end = edge_endpoints(edges)
    return np.hypot(end[:, 0] - start[:, 0], end[:, 1] - start[:, 1])


def circuity(edges: GeoDataFrame) -> float:
    """Total network length / total straight-line endpoint distance.

    >= 1; higher means more sinuous. Undefined (NaN) if all edges are loops.
    """
    straight = euclidean_length(edges).sum()
    if straight == 0:
        return float("nan")
    return float(edges["length"].sum() / straight)


def bearings(edges: GeoDataFrame) -> np.ndarray:
    """Compass bearing of each edge (degrees, 0-360) from first to last point."""
    start, end = edge_endpoints(edges)
    dx, dy = end[:, 0] - start[:, 0], end[:, 1] - start[:, 1]
    deg = np.degrees(np.arctan2(dx, dy))  # 0 = north, clockwise (projected xy)
    return np.mod(deg, 360.0)


def orientation_histogram(edges: GeoDataFrame, bins: int = BEARING_BINS) -> np.ndarray:
    """Length-weighted, normalised distribution of edge bearings.

    Each undirected edge contributes to both its bearing and the reciprocal
    (+180 deg), so the distribution is direction-symmetric (Boeing 2019).
    """
    b = bearings(edges)
    both = np.concatenate([b, np.mod(b + 180.0, 360.0)])
    w = np.concatenate([edges["length"].to_numpy(), edges["length"].to_numpy()])
    counts, _ = np.histogram(both, bins=bins, range=(0.0, 360.0), weights=w)
    total = counts.sum()
    if total == 0:
        return np.full(bins, 1.0 / bins)
    return counts / total


def orientation_entropy(edges: GeoDataFrame, bins: int = BEARING_BINS) -> float:
    """Shannon entropy (nats) of the orientation distribution."""
    p = orientation_histogram(edges, bins)
    nz = p[p > 0]
    return float(-(nz * np.log(nz)).sum())


def orientation_order(edges: GeoDataFrame, bins: int = BEARING_BINS) -> float:
    """Boeing (2019) orientation order phi: 1 = perfect grid, 0 = uniform/disordered.

    phi = 1 - ((H - Hg) / (Hmax - Hg))^2, where H is the orientation entropy,
    Hmax = ln(bins) (uniform) and Hg = ln(4) (a perfect four-way grid). Clamped
    to [0, 1]. A single cheap number for "how gridded is this network".
    """
    h = orientation_entropy(edges, bins)
    h_max = np.log(bins)
    h_grid = np.log(4)
    phi = 1.0 - ((h - h_grid) / (h_max - h_grid)) ** 2
    return float(min(1.0, max(0.0, phi)))


def kl_divergence(p: np.ndarray, q: np.ndarray, eps: float = 1e-12) -> float:
    """KL(p || q) in nats, with epsilon smoothing so zeros don't blow up."""
    p = p + eps
    q = q + eps
    p = p / p.sum()
    q = q / q.sum()
    return float((p * np.log(p / q)).sum())


def gini(values: np.ndarray) -> float:
    """Gini coefficient of non-negative values. 0 = equal, ->1 = concentrated."""
    v = np.sort(np.asarray(values, dtype=float))
    n = v.size
    if n == 0 or v.sum() == 0:
        return float("nan")
    idx = np.arange(1, n + 1)
    return float((2.0 * (idx * v).sum()) / (n * v.sum()) - (n + 1.0) / n)
