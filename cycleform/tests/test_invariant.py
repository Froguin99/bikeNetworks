"""The §2 invariant: metric code runs identically on OSM and grown networks.

If this test fails, the project's primary constraint is broken. It is not a
nicety -- Q3 (applying the fitted model to grown networks) is impossible if a
metric cannot be computed on a grown network, or computes differently there.
"""

from __future__ import annotations

import math

from cycleform.metrics import REGISTRY
from cycleform.synthetic import fake_grown_context, fake_osm_context


def test_registry_runs_over_grown_network():
    """Every metric produces a result on a grown network -- none errors out."""
    ctx = fake_grown_context()
    results = REGISTRY.run(ctx)
    assert len(results) == len(REGISTRY.output_columns())
    errored = [r for r in results if r.status == "error"]
    assert not errored, f"metrics errored on grown network: {[(r.name, r.detail) for r in errored]}"


def test_grown_network_has_no_missing_requirements():
    """The synthetic grown context supplies road+bike+lts, so nothing is skipped."""
    ctx = fake_grown_context()
    skipped = [r for r in REGISTRY.run(ctx) if r.status == "missing_requires"]
    assert not skipped, f"unexpectedly missing: {[(r.name, r.detail) for r in skipped]}"


def test_identical_values_regardless_of_source():
    """Same geometry, source='osm' vs source='grown' -> identical values.

    This is the operational meaning of "no `if is_simulated:` branching".
    """
    osm = {r.name: r.value for r in REGISTRY.run(fake_osm_context())}
    grown = {r.name: r.value for r in REGISTRY.run(fake_grown_context())}
    assert osm.keys() == grown.keys()
    for name in osm:
        a, b = osm[name], grown[name]
        if math.isnan(a) and math.isnan(b):
            continue
        assert a == b, f"{name}: osm={a} != grown={b}"
