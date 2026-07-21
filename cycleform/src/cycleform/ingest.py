"""Assemble a PlaceContext from OSM -- the real-city half of the §2 invariant.

`context_from_osm` mirrors `synthetic.fake_grown_context`: both return a
PlaceContext with the same schema, so `REGISTRY.run` executes identically on a
real city and on a grown network. The only visible difference is `source`,
which is provenance metadata and never branched on.
"""

from __future__ import annotations

import logging

from cycleform.config import settings
from cycleform.metrics.base import PlaceContext
from cycleform.networks import (
    all_edges,
    is_bike_infrastructure,
    is_cyclable,
    network_from_subset,
    road_network,
)
from cycleform.osm import configure_osmnx
from cycleform.places import resolve_boundary

log = logging.getLogger(__name__)


def context_from_osm(
    query: str,
    place_id: str | None = None,
    *,
    country: str = "",
    simplify: bool = True,
    cache: bool = True,
) -> PlaceContext:
    """Build a PlaceContext for one real place from OSM.

    Args:
        query: place name resolvable by Nominatim (e.g. "Newcastle upon Tyne, UK").
        place_id: stable id for outputs; defaults to `query`.
        country: 2-letter code (UK, DE, ...) used to disambiguate the outcome join.
        simplify: run neatnet on the road network (recommended; §3).
        cache: use osmnx's on-disk Overpass cache.
    """
    configure_osmnx(cache=cache)
    pid = place_id or query
    boundary = resolve_boundary(query, place_id=pid)
    log.info("%s: boundary %.1f km² in %s", pid, boundary.area_km2, boundary.crs)

    # road (drive, neatnet) first: its size guard fails fast before the "all" fetch
    road = road_network(boundary.geometry_wgs84, boundary.crs, simplify=simplify)
    # one "all" fetch, split into the cycle-infrastructure and cyclable-street layers
    allp = all_edges(boundary.geometry_wgs84, boundary.crs)
    bike = network_from_subset(allp[is_bike_infrastructure(allp)])
    street = network_from_subset(allp[is_cyclable(allp)])
    log.info(
        "%s: road %d, bike %d, street %d edges", pid, road.n_edges, bike.n_edges, street.n_edges
    )

    return PlaceContext(
        place_id=pid,
        boundary=boundary.geometry,
        built_up_area_km2=boundary.area_km2,
        source="osm",
        snapshot_date=settings.snapshot_date,
        road=road,
        bike=bike,
        street=street,
        meta={
            "query": query,
            "country": country,
            "crs": str(boundary.crs),
            "area_note": boundary.area_note,
        },
    )
