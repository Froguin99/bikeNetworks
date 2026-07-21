"""Real-OSM ingestion test. Network-gated: opt in with CYCLEFORM_RUN_OSM_TESTS=1.

Kept out of the default run so the suite stays offline and fast. This is the
real-city half of the §2 gate; test_invariant.py covers the grown-network half
offline. Run explicitly when touching ingest/networks/simplify.
"""

from __future__ import annotations

import os

import pytest

RUN = os.environ.get("CYCLEFORM_RUN_OSM_TESTS") == "1"
pytestmark = pytest.mark.skipif(not RUN, reason="set CYCLEFORM_RUN_OSM_TESTS=1 to run OSM tests")


def test_real_city_runs_full_registry():
    from cycleform.ingest import context_from_osm
    from cycleform.metrics import REGISTRY

    ctx = context_from_osm("City of Chester, United Kingdom", place_id="Chester")
    assert ctx.source == "osm"
    assert {"road", "bike", "lts"} <= ctx.available
    results = REGISTRY.run(ctx)
    errored = [(r.name, r.detail) for r in results if r.status == "error"]
    assert not errored, f"errors on real city: {errored}"
    # sanity ranges: shares in [0,1], densities positive
    by = {r.name: r.value for r in results}
    assert 0.0 <= by["lcc_length_share_bike"] <= 1.0
    assert 0.0 <= by["low_stress_coverage"] <= 1.0
    assert by["intersection_density_per_km_road"] > 0
    assert by["length_km_bike"] > 0
    assert by["modal_directness_gap"] >= 1.0
