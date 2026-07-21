"""neatnet simplification and re-noding into canonical node/edge frames.

neatnet.neatify collapses OSM representation conventions (dual carriageways,
roundabouts, sliproads) that vary by country and would otherwise destroy
cross-national intersection counts (CLAUDE.md §3, §8). It returns geometry only,
so `renode` rebuilds the u/v topology and `transfer_attribute` carries `highway`
back from the raw edges for LTS tagging.
"""

from __future__ import annotations

import geopandas as gpd
import neatnet
from shapely.geometry import Point

_COORD_DECIMALS = 3  # ~mm at metre scale; neatnet output shares endpoints exactly.


def simplify_streets(edges: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Run neatnet on a projected streets frame. Returns simplified LineStrings."""
    if edges.crs is None or edges.crs.is_geographic:
        raise ValueError("edges must be in a projected CRS before neatnet")
    return neatnet.neatify(edges[["geometry"]].reset_index(drop=True))


def renode(lines: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Build canonical (nodes, edges) frames from a frame of LineStrings.

    Endpoints that coincide (to mm) become shared nodes. `length` is the
    projected geometry length in metres. Any non-geometry columns on `lines`
    are carried onto the edges.
    """
    crs = lines.crs
    coord_to_id: dict[tuple[float, float], int] = {}

    def node_id(xy: tuple[float, float]) -> int:
        key = (round(xy[0], _COORD_DECIMALS), round(xy[1], _COORD_DECIMALS))
        if key not in coord_to_id:
            coord_to_id[key] = len(coord_to_id)
        return coord_to_id[key]

    us, vs = [], []
    for geom in lines.geometry:
        us.append(node_id(geom.coords[0]))
        vs.append(node_id(geom.coords[-1]))

    extra = [c for c in lines.columns if c not in ("geometry", "u", "v", "length")]
    data = {"u": us, "v": vs}
    data.update({c: lines[c].to_numpy() for c in extra})
    data["geometry"] = lines.geometry.to_numpy()
    edges = gpd.GeoDataFrame(data, crs=crs)
    edges["length"] = edges.geometry.length
    nodes = gpd.GeoDataFrame(
        {"geometry": [Point(x, y) for x, y in coord_to_id]},
        index=list(coord_to_id.values()),
        crs=crs,
    ).sort_index()
    return nodes, edges


def transfer_attribute(
    target: gpd.GeoDataFrame, source: gpd.GeoDataFrame, column: str, max_distance: float = 20.0
) -> gpd.GeoDataFrame:
    """Copy `column` from the nearest `source` edge onto each `target` edge.

    Used to recover `highway` after neatnet drops attributes. Matching is on the
    target edge midpoint; ties beyond `max_distance` metres get NaN (later mapped
    to the LTS default).
    """
    if target.crs != source.crs:
        source = source.to_crs(target.crs)
    mids = target.geometry.interpolate(0.5, normalized=True)
    probe = gpd.GeoDataFrame(geometry=mids, crs=target.crs)
    joined = gpd.sjoin_nearest(
        probe, source[[column, "geometry"]], how="left", max_distance=max_distance
    )
    joined = joined[~joined.index.duplicated(keep="first")]  # sjoin_nearest can tie
    out = target.copy()
    out[column] = joined[column].to_numpy()
    return out
