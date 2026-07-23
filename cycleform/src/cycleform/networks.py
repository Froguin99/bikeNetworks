"""Road, bike and street network construction from OSM.

Three layers, all returned as canonical LTS-tagged `Network` objects so metric
code cannot tell them from a grown network (§2):
- **road**: `network_type="drive"`, neatnet-simplified (structural metrics).
- **bike**: protected/segregated + shared-use cycle infrastructure, filtered from
  the `network_type="all"` fetch by `is_bike_infrastructure` (ported/extended
  from the old repo's notebook 00; CLAUDE.md §3, §8).
- **street**: the cyclable network -- roads a cyclist may use + cycle infra --
  filtered from the same `all` fetch by `is_cyclable`. LTS coverage and routing
  metrics run on this so cycle infrastructure counts.

The `all` fetch is done once and split into bike and street (see ingest.py).
"""

from __future__ import annotations

import contextlib
import logging
import random
import threading
import time

import geopandas as gpd
import osmnx as ox
import pandas as pd
import requests
from shapely.geometry.base import BaseGeometry

from cycleform.config import settings
from cycleform.lts import add_lts
from cycleform.metrics.base import Network
from cycleform.osm import configure_osmnx
from cycleform.simplify import renode, simplify_streets, transfer_attribute

log = logging.getLogger(__name__)

# Country-agnostic cycle-infrastructure classifier (CLAUDE.md §8). Definition
# (user, 2026-07-17): PROTECTED / SEGREGATED, or MIXED-USE WITH PEDESTRIANS only.
# Deliberately excludes painted on-road lanes, cycle streets and modal-filtered
# roads -- those are lower-stress but not physically separated from motor traffic.
_BIKE_HIGHWAY = {"cycleway", "bridleway"}  # dedicated / segregated ways
# On-road provision: only kerb-separated *tracks* count (protected). `lane`
# (painted) is excluded; `separate` is excluded because the cycleway is mapped as
# its own way (captured via highway=cycleway) and counting the road too would
# double-count length.
_CYCLEWAY_PROTECTED = {"track", "opposite_track"}
_CYCLEWAY_COLS = ("cycleway", "cycleway:left", "cycleway:right", "cycleway:both")
# Mixed-use-with-pedestrians paths: a foot/path way that bikes may use.
_SHARED_USE_HIGHWAY = {"footway", "path", "pedestrian"}
_SHARED_USE_BICYCLE = {"yes", "designated"}

# Cyclable road types for the street network: roads a cyclist may legally use.
# Motorways/steps/pure-pedestrian ways are excluded (the latter only enter the
# street network if they pass the bike-infrastructure filter, i.e. bicycle=yes).
_CYCLABLE_ROAD = {
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "unclassified",
    "residential",
    "living_street",
    "service",
    "road",
    "trunk",
    "trunk_link",
}


def _as_set(value: object) -> set[str]:
    """OSM tag values are str or list[str]. Normalise to a set for membership tests."""
    if isinstance(value, str):
        return {value}
    if isinstance(value, (list, tuple, set)):
        return {v for v in value if isinstance(v, str)}
    return set()


def _col(edges: gpd.GeoDataFrame, name: str) -> pd.Series:
    if name in edges.columns:
        return edges[name]
    return pd.Series([None] * len(edges), index=edges.index)


def _has(series: pd.Series, values: set[str]) -> pd.Series:
    return series.map(lambda v: bool(_as_set(v) & values))


def is_bike_infrastructure(edges: gpd.GeoDataFrame) -> pd.Series:
    """Boolean mask: protected/segregated or mixed-use-with-pedestrians cycle infra.

    Union of: dedicated segregated ways (highway=cycleway/bridleway); kerb-
    separated on-road tracks (any cycleway[:left|:right|:both]=track); and
    shared foot+cycle paths (highway in footway/path/pedestrian with
    bicycle=yes/designated). Painted lanes, cycle streets and modal-filtered
    roads are excluded by this definition. Robust to absent columns.
    """
    hw = _col(edges, "highway")
    keep = _has(hw, _BIKE_HIGHWAY)
    for c in _CYCLEWAY_COLS:
        keep = keep | _has(_col(edges, c), _CYCLEWAY_PROTECTED)
    keep = keep | (
        _has(_col(edges, "bicycle"), _SHARED_USE_BICYCLE) & _has(hw, _SHARED_USE_HIGHWAY)
    )
    return keep


def is_cyclable(edges: gpd.GeoDataFrame) -> pd.Series:
    """Boolean mask: the cyclable street network -- everything a cyclist may ride.

    Cyclable roads (excludes motorways/steps/pedestrian) OR cycle infrastructure
    (from `is_bike_infrastructure`, which already admits the bicycle=yes footways/
    paths), minus anything explicitly `bicycle=no`/`dismount`. This is the network
    the LTS coverage and routing metrics operate on, so cycleways (LTS 1) count.
    """
    on_road = _has(_col(edges, "highway"), _CYCLABLE_ROAD)
    keep = on_road | is_bike_infrastructure(edges)
    return keep & ~_has(_col(edges, "bicycle"), {"no", "dismount"})


@contextlib.contextmanager
def _heartbeat(label: str, interval: float):
    """Log '...still fetching' every `interval`s until the block exits, so a slow
    (large) place looks alive rather than hung. Fast fetches finish before the
    first beat and stay silent. A no-op when interval <= 0."""
    if interval <= 0:
        yield
        return
    stop = threading.Event()
    t0 = time.perf_counter()

    def _beat() -> None:
        while not stop.wait(interval):
            log.info("  ... still fetching %s (%.0fs elapsed)", label, time.perf_counter() - t0)

    thread = threading.Thread(target=_beat, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1.0)


def _overpass_reachable(endpoint: str, timeout: float) -> bool:
    """True if the endpoint answers a /status probe within `timeout` (any HTTP
    response counts -- we only care that the TCP connect succeeded, not the code).

    Lets a stalled/overloaded mirror be skipped in ~`timeout`s instead of waiting
    out the full requests_timeout (which is also the server-side query timeout, so
    it cannot be shortened just for the connect)."""
    try:
        requests.get(f"{endpoint}/status", timeout=timeout)
        return True
    except requests.RequestException:
        return False


def _edges_from_polygon(
    polygon: BaseGeometry, network_type: str, crs: object, retries: int | None = None
) -> gpd.GeoDataFrame:
    """Fetch a graph within a WGS84 polygon; return projected edges.

    Rotates through settings.overpass_endpoints (a quick reachability probe skips a
    dead mirror fast) and retries with backoff on transient Overpass errors
    (timeouts, throttling), which are common over a long batch. Only ever called
    with "drive"/"all", so a real place always has data: an empty response
    (InsufficientResponseError) is a bad mirror reply, not a genuinely empty area,
    so it rotates like any other error. osmnx caches HTTP-200 replies (empty ones
    included), so after a failure the cache is bypassed to stop a poisoned empty
    entry from failing the place on every future run.
    """
    configure_osmnx()
    endpoints = list(settings.overpass_endpoint_list) or [ox.settings.overpass_url]
    retries = settings.network_retries if retries is None else retries
    probe_timeout = settings.overpass_probe_timeout
    cache_setting = ox.settings.use_cache
    # random start spreads a single run's load; deterministic start (start=0) lets
    # parallel pinned shard processes each keep affinity to their own primary mirror
    start = random.randrange(len(endpoints)) if settings.overpass_shuffle_endpoints else 0
    last: Exception | None = None
    try:
        for attempt in range(retries):
            endpoint = endpoints[(start + attempt) % len(endpoints)]
            if len(endpoints) > 1 and not _overpass_reachable(endpoint, probe_timeout):
                log.warning(
                    "overpass %s: %s unreachable (attempt %d/%d), rotating mirror",
                    network_type, endpoint, attempt + 1, retries,
                )
                last = last or ConnectionError(f"{endpoint} unreachable")
                time.sleep(2)
                continue
            ox.settings.overpass_url = endpoint
            host = endpoint.split("//")[-1].split("/")[0]
            try:
                with _heartbeat(f"{network_type} via {host}", settings.fetch_heartbeat_seconds):
                    graph = ox.graph_from_polygon(
                        polygon, network_type=network_type, simplify=True, retain_all=False
                    )
                edges = ox.convert.graph_to_gdfs(graph, nodes=False)
                return edges.to_crs(crs)
            except Exception as exc:  # timeout / connection / server / empty response
                last = exc
                log.warning(
                    "overpass %s via %s failed (attempt %d/%d): %s",
                    network_type, endpoint, attempt + 1, retries, type(exc).__name__,
                )
                ox.settings.use_cache = False  # don't re-read a poisoned/empty cache
                if attempt < retries - 1:
                    time.sleep(min(60, 10 * (attempt + 1)))
        raise last
    finally:
        ox.settings.use_cache = cache_setting


class NetworkTooLarge(RuntimeError):
    """Raw drive network exceeds settings.max_road_edges; skip to protect compute."""


def road_network(polygon: BaseGeometry, crs: object, simplify: bool = True) -> Network:
    """Drive network within `polygon`, neatnet-simplified, LTS-tagged."""
    raw = _edges_from_polygon(polygon, "drive", crs)
    if len(raw) > settings.max_road_edges:
        raise NetworkTooLarge(f"{len(raw)} raw drive edges > {settings.max_road_edges}")
    if simplify:
        simplified = simplify_streets(raw)
        simplified = transfer_attribute(simplified, raw, "highway")
        nodes, edges = renode(simplified)
    else:
        nodes, edges = renode(raw[["highway", "geometry"]])
    edges = add_lts(edges)
    return Network(nodes=nodes, edges=edges)


def network_from_subset(edges: gpd.GeoDataFrame) -> Network:
    """Build a canonical, LTS-tagged Network from a subset of fetched edges.

    Not neatnet-simplified (neatnet's block logic is tuned for road networks, not
    cycle/all networks). Used for the cycle and street layers.
    """
    keep = [c for c in ("highway", "geometry") if c in edges.columns]
    nodes, e = renode(edges[keep])
    return Network(nodes=nodes, edges=add_lts(e))


def all_edges(polygon: BaseGeometry, crs: object) -> gpd.GeoDataFrame:
    """The full `network_type="all"` edges within `polygon`, projected. Fetched once,
    then filtered into the cycle and street layers (avoids a second Overpass call)."""
    return _edges_from_polygon(polygon, "all", crs)


def bike_network(polygon: BaseGeometry, crs: object) -> Network:
    """Cycle-infrastructure network (protected/segregated + shared-use paths)."""
    allp = all_edges(polygon, crs)
    return network_from_subset(allp[is_bike_infrastructure(allp)])


def street_network(polygon: BaseGeometry, crs: object) -> Network:
    """Cyclable street network -- roads a cyclist may use + cycle infrastructure."""
    allp = all_edges(polygon, crs)
    return network_from_subset(allp[is_cyclable(allp)])
