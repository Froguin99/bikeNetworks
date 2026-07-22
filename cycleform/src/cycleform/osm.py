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

from cycleform.config import settings

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
    ox.settings.requests_timeout = settings.overpass_query_timeout
    # Rate limiting OFF on purpose. With it ON, osmnx polls the server /status before
    # every request and, when no slot is free, SLEEPS for the server-dictated wait
    # (and recurses every 5s while a query is "Currently" running) -- on an overloaded
    # public endpoint that blocks a single small place for many minutes to over an
    # hour. Instead we fail fast per attempt and rotate mirrors
    # (networks._edges_from_polygon), pause between places (batch_pause_seconds), and
    # rely on the server's own bounded 429/504 back-off. Less pre-emptively polite,
    # but no unbounded slot-wait.
    ox.settings.overpass_rate_limit = False
    if not _configured:
        current = set(ox.settings.useful_tags_way)
        ox.settings.useful_tags_way = sorted(current | set(CYCLING_WAY_TAGS))
        _configured = True
