"""The metric protocol and the context every metric reads from.

The binding constraint of this project (CLAUDE.md §2): metric code must run
identically on a real city from OSM and on a network grown by the Chapter-5
model. Both sources are normalised into `Network` / `PlaceContext` *before* any
metric sees them, so metric code cannot tell the difference and must never ask.
`PlaceContext.source` records provenance for reporting only -- branching on it
anywhere under metrics/ is a bug, and tests/test_invariant.py exists to catch it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import rustworkx as rx
from shapely.geometry.base import BaseGeometry

REQUIREMENTS = frozenset({"road", "bike", "street", "lts", "pop", "dem"})

NODE_COLUMNS = frozenset({"geometry"})
EDGE_COLUMNS = frozenset({"u", "v", "length", "geometry"})


class SchemaError(ValueError):
    """A Network was built from frames that do not meet the canonical schema."""


@dataclass
class Network:
    """A street network as nodes/edges frames in a projected CRS.

    The canonical representation both OSM and grown networks are converted into.
    `nodes` is indexed by node id with Point geometry. `edges` carries `u`, `v`
    (node ids), `length` (metres) and LineString geometry, plus optional
    attributes such as `lts` and `highway`.
    """

    nodes: gpd.GeoDataFrame
    edges: gpd.GeoDataFrame

    def __post_init__(self) -> None:
        missing_n = NODE_COLUMNS - set(self.nodes.columns)
        missing_e = EDGE_COLUMNS - set(self.edges.columns)
        if missing_n:
            raise SchemaError(f"nodes missing columns: {sorted(missing_n)}")
        if missing_e:
            raise SchemaError(f"edges missing columns: {sorted(missing_e)}")
        if self.nodes.crs is None or self.edges.crs is None:
            raise SchemaError("nodes and edges must both carry a CRS")
        if self.nodes.crs != self.edges.crs:
            raise SchemaError(f"CRS mismatch: nodes {self.nodes.crs} vs edges {self.edges.crs}")
        if self.nodes.crs.is_geographic:
            raise SchemaError(
                f"{self.nodes.crs} is geographic; lengths would be in degrees. Project first."
            )
        if not self.nodes.index.is_unique:
            raise SchemaError("node index must be unique")
        dangling = (set(self.edges["u"]) | set(self.edges["v"])) - set(self.nodes.index)
        if dangling:
            raise SchemaError(f"{len(dangling)} edge endpoints absent from nodes frame")

    @property
    def crs(self) -> Any:
        return self.nodes.crs

    @property
    def n_nodes(self) -> int:
        return len(self.nodes)

    @property
    def n_edges(self) -> int:
        return len(self.edges)

    @property
    def length_total_m(self) -> float:
        """Total edge length in metres."""
        return float(self.edges["length"].sum())

    @cached_property
    def graph(self) -> rx.PyGraph:
        """Undirected multigraph, edge payload = length in metres."""
        g = rx.PyGraph(multigraph=True)
        pos = {nid: g.add_node(nid) for nid in self.nodes.index}
        e = self.edges
        for u, v, length in zip(e["u"], e["v"], e["length"], strict=True):
            g.add_edge(pos[u], pos[v], float(length))
        return g

    @cached_property
    def nx_graph(self) -> nx.MultiGraph:
        """Undirected networkx multigraph with `length` edge weights.

        Used for sampled centralities where networkx's k-source support is the
        right tool; graph algorithms that don't need it use `graph` (rustworkx).
        """
        g = nx.MultiGraph()
        g.add_nodes_from(self.nodes.index)
        e = self.edges
        g.add_weighted_edges_from(zip(e["u"], e["v"], e["length"], strict=True), weight="length")
        return g

    @cached_property
    def degree(self) -> pd.Series:
        """Node degree, indexed like `nodes`. Self-loops count twice."""
        ends = pd.concat([self.edges["u"], self.edges["v"]], ignore_index=True)
        return ends.value_counts().reindex(self.nodes.index, fill_value=0).astype(int)

    @property
    def intersection_count(self) -> int:
        """Nodes of degree >= 3. Only comparable across countries post-neatnet."""
        return int((self.degree >= 3).sum())

    @cached_property
    def rx_index(self) -> dict[Any, int]:
        """Map node id -> rustworkx node index in `graph`."""
        g = self.graph
        return {g[i]: i for i in g.node_indices()}

    def sssp_lengths(self, source_id: Any) -> dict[Any, float]:
        """Shortest-path length (metres) from `source_id` to every reachable node."""
        g = self.graph
        res = rx.dijkstra_shortest_path_lengths(g, self.rx_index[source_id], edge_cost_fn=float)
        return {g[t]: float(c) for t, c in res.items()}

    @cached_property
    def _node_component(self) -> dict[Any, int]:
        """Map node id -> component label."""
        g = self.graph
        return {g[i]: label for label, comp in enumerate(rx.connected_components(g)) for i in comp}

    @cached_property
    def component_lengths_m(self) -> np.ndarray:
        """Edge length (m) per connected component, descending. Isolated nodes contribute 0."""
        label = self._node_component
        by_comp: dict[int, float] = {}
        for u, length in zip(self.edges["u"], self.edges["length"], strict=True):
            c = label[u]
            by_comp[c] = by_comp.get(c, 0.0) + float(length)
        if not by_comp:
            return np.zeros(0)
        return np.sort(np.fromiter(by_comp.values(), dtype=float))[::-1]

    @property
    def n_components(self) -> int:
        """Connected components, counting isolated nodes."""
        return len(rx.connected_components(self.graph)) if self.n_nodes else 0

    @property
    def lcc_length_m(self) -> float:
        """Edge length of the largest connected component, by length."""
        lengths = self.component_lengths_m
        return float(lengths[0]) if len(lengths) else 0.0

    def subset(self, mask: np.ndarray | Any) -> Network:
        """Edge-induced subnetwork, dropping nodes that lose all their edges."""
        edges = self.edges.loc[mask]
        keep = set(edges["u"]) | set(edges["v"])
        return Network(nodes=self.nodes.loc[list(keep)], edges=edges)


@dataclass
class PlaceContext:
    """Everything a metric may read about one place.

    Constructible from OSM (`cycleform.networks`) or from a grown network
    (`cycleform.scenarios`). Metrics declare what they need via `requires` and
    the registry checks it against `available` -- so an absent layer yields a
    logged NaN, never a silent zero.
    """

    place_id: str
    boundary: BaseGeometry
    """Analysis boundary, in the same projected CRS as the networks."""
    built_up_area_km2: float
    """Denominator for density metrics. Built-up area, not boundary area."""
    source: str
    """Provenance only ("osm" | "grown"). Never branch on this inside a metric."""
    snapshot_date: str
    road: Network | None = None
    bike: Network | None = None
    street: Network | None = None
    """Cyclable street network (roads + cycle infra), LTS-tagged. LTS coverage and
    routing metrics operate on this so cycle infrastructure counts (not `road`)."""
    pop: Any | None = None
    dem: Any | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.built_up_area_km2 <= 0:
            raise ValueError(f"{self.place_id}: built_up_area_km2 must be > 0")
        for name in ("road", "bike", "street"):
            net = getattr(self, name)
            if net is not None and not isinstance(net, Network):
                raise TypeError(f"{name} must be a Network, got {type(net).__name__}")

    @property
    def available(self) -> frozenset[str]:
        """Which requirements this context can satisfy."""
        got = set()
        if self.road is not None:
            got.add("road")
        if self.bike is not None:
            got.add("bike")
        if self.street is not None:
            got.add("street")
            if "lts" in self.street.edges.columns:
                got.add("lts")
        if self.pop is not None:
            got.add("pop")
        if self.dem is not None:
            got.add("dem")
        return frozenset(got)

    def missing(self, requires: frozenset[str]) -> frozenset[str]:
        return frozenset(requires) - self.available


@dataclass(frozen=True)
class NetworkMetric:
    """A metric computed on a single `Network`, run over one or more layers.

    The registry runs it on each layer in `layers` that the context provides,
    emitting one result per layer named `<name>_<layer>` (e.g. `circuity_road`,
    `circuity_bike`) -- mirroring the old repo's `_road`/`_bike` suffixes. `fn`
    receives only the Network, so it is inherently provenance-blind (§2).
    """

    name: str
    version: str
    fn: Callable[[Network], float]
    layers: tuple[str, ...] = ("road", "bike")


@dataclass(frozen=True)
class PlaceMetric:
    """A metric over the whole `PlaceContext` -- relational metrics live here.

    Declares `requires` (subset of REQUIREMENTS); the registry emits a logged
    NaN if the context can't satisfy it, never a silent zero.
    """

    name: str
    version: str
    requires: frozenset[str]
    fn: Callable[[PlaceContext], float]


@dataclass(frozen=True)
class MetricResult:
    """Outcome of one metric on one place. A failure is data, not an exception."""

    place_id: str
    name: str
    version: str
    value: float
    status: str
    """"ok" | "missing_requires" | "error"."""
    detail: str = ""
