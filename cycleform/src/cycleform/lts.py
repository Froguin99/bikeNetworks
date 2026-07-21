"""Level of Traffic Stress classification.

PORTED from bikenwgrowth/code/tag_lts.py (the Chapter-5 growth model), NOT
rewritten -- CLAUDE.md §3 requires LTS to stay identical across the two
chapters. The lookup and the default are copied verbatim; the only addition is
a documented rule for OSM's list-valued `highway`, which the growth repo never
hits because it reads a scalar `highway` column from its edge CSVs.

This is a highway-tag lookup only. It ignores `cycleway:*`, maxspeed and
physical separation -- the known limitation behind the cross-national tagging
risk in CLAUDE.md §8. Do not "improve" it here without changing the growth
chapter too; that is a metric-definition change and needs sign-off (§10).
"""

from __future__ import annotations

from collections.abc import Iterable

# Verbatim from bikenwgrowth/code/tag_lts.py. Do not edit without §10 sign-off.
TAG_LTS: dict[str, int] = {
    "motorway": 4,
    "motorway_link": 4,
    "trunk": 4,
    "trunk_link": 4,
    "primary": 4,
    "primary_link": 4,
    "secondary": 4,
    "secondary_link": 4,
    "tertiary": 3,
    "tertiary_link": 3,
    "unclassified": 3,
    "residential": 2,
    "living_street": 2,
    "cycleway": 1,
    "track": 1,
    "path": 1,
    "bridleway": 1,
}

DEFAULT_LTS = 1
"""Growth repo uses `tag_lts.get(highway, 1)`; unknown highway types are LTS 1."""


def lts_for_highway(highway: object) -> int:
    """LTS for one edge's `highway` value.

    OSM stores `highway` as either a string or a list (e.g. `["residential",
    "service"]`). The growth repo only ever sees scalars. For lists we take the
    most stressful (max) LTS present, so a mixed edge is never optimistically
    classed as low-stress.
    """
    if isinstance(highway, str):
        return TAG_LTS.get(highway, DEFAULT_LTS)
    if isinstance(highway, Iterable):
        vals = [TAG_LTS.get(h, DEFAULT_LTS) for h in highway if isinstance(h, str)]
        return max(vals) if vals else DEFAULT_LTS
    return DEFAULT_LTS


def add_lts(edges, highway_col: str = "highway", out_col: str = "lts"):
    """Return a copy of an edges frame with an integer `lts` column."""
    edges = edges.copy()
    edges[out_col] = edges[highway_col].map(lts_for_highway).astype("int8")
    return edges
