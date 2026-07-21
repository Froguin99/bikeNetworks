"""Central OpenStreetMap fetch configuration.

osmnx 2.x keeps only a small default `useful_tags_way`, which drops every
cycling tag (`cycleway`, `cycleway:left/right/both`, `bicycle`, `bicycle_road`).
Without them the bike classifier can only see `highway=cycleway` and silently
under-counts every country that tags on-road provision (Germany, NL, ...) --
the cross-national tagging risk in CLAUDE.md §8, which the pilot confirmed on
Freiburg/Münster. `configure_osmnx()` re-adds them and must run before any fetch.
"""

from __future__ import annotations

import osmnx as ox

CYCLING_WAY_TAGS = [
    "cycleway",
    "cycleway:left",
    "cycleway:right",
    "cycleway:both",
    "bicycle",
    "bicycle_road",
    "cyclestreet",
    "segregated",
    "foot",
    "motor_vehicle",
]

_configured = False


def configure_osmnx(cache: bool = True) -> None:
    """Idempotently set osmnx cache + retain cycling way tags. Safe to call often."""
    global _configured
    ox.settings.use_cache = cache
    ox.settings.log_console = False
    ox.settings.requests_timeout = 300  # big "all"-network queries need > default 180s
    ox.settings.overpass_rate_limit = True  # be polite over a long run
    if not _configured:
        current = set(ox.settings.useful_tags_way)
        ox.settings.useful_tags_way = sorted(current | set(CYCLING_WAY_TAGS))
        _configured = True
