"""Golden-value and property tests against a tiny synthetic graph.

The 4x4 grid, 100 m spacing, is small enough to reason about by hand:
- 16 nodes, 24 edges (12 horizontal + 12 vertical), each 100 m -> 2400 m total.
- Degrees: 4 corners (deg 2), 8 edges (deg 3), 4 interior (deg 4).
  Intersections (deg >= 3) = 8 + 4 = 12. k_avg = 2*24/16 = 3.0.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from cycleform.geometry import gini, kl_divergence, orientation_histogram
from cycleform.lts import lts_for_highway
from cycleform.metrics import REGISTRY
from cycleform.synthetic import fake_grown_context, grid_network


def _run(ctx, col):
    (r,) = REGISTRY.run(ctx, only=[col])
    return r


def test_grid_shape():
    net = grid_network(4, spacing=100.0)
    assert net.n_nodes == 16
    assert net.n_edges == 24
    assert net.length_total_m == pytest.approx(2400.0)
    assert net.intersection_count == 12
    assert net.n_components == 1
    assert net.lcc_length_m == pytest.approx(2400.0)


def test_structural_golden_values():
    ctx = fake_grown_context(k=4)
    assert _run(ctx, "k_avg_road").value == pytest.approx(3.0)
    assert _run(ctx, "n_nodes_road").value == 16
    assert _run(ctx, "n_edges_road").value == 24
    assert _run(ctx, "intersection_count_road").value == 12
    assert _run(ctx, "length_km_road").value == pytest.approx(2.4)
    assert _run(ctx, "self_loop_proportion_road").value == 0.0
    # grid is perfectly straight edges -> circuity 1, linearity 1
    assert _run(ctx, "circuity_avg_road").value == pytest.approx(1.0)
    assert _run(ctx, "linearity_mean_road").value == pytest.approx(1.0)


def test_connectivity_indices_golden():
    ctx = fake_grown_context(k=4)  # n=16, m=24, 1 component
    assert _run(ctx, "connectivity_ratio_road").value == pytest.approx(24 / (3 * (16 - 2)))
    assert _run(ctx, "meshedness_road").value == pytest.approx((24 - 16 + 1) / (2 * 16 - 5))


def test_orientation_order_perfect_grid_is_one():
    ctx = fake_grown_context(k=4)  # bearings only N-S / E-W -> perfect grid
    assert _run(ctx, "orientation_order_road").value == pytest.approx(1.0)


def test_bike_offroad_share_all_cycleway():
    ctx = fake_grown_context(k=4)  # synthetic bike layer is all highway=cycleway
    assert _run(ctx, "bike_offroad_share").value == pytest.approx(1.0)


def test_intersection_ratio_positive():
    ctx = fake_grown_context(k=5)
    r = _run(ctx, "intersection_ratio_bike_road")
    assert r.status == "ok" and r.value >= 0


def test_degree_proportions_sum_sensibly():
    ctx = fake_grown_context(k=4)
    dead = _run(ctx, "dead_end_proportion_road").value
    three = _run(ctx, "three_way_proportion_road").value
    four = _run(ctx, "four_way_proportion_road").value
    assert dead == 0.0  # a 4x4 grid has no degree-1 nodes
    assert three == pytest.approx(8 / 16)
    assert four == pytest.approx(4 / 16)


def test_orientation_entropy_grid_is_low():
    # a pure grid has bearings only N-S and E-W -> low entropy vs uniform (~3.58)
    ctx = fake_grown_context(k=4)
    ent = _run(ctx, "orientation_entropy_road").value
    assert 0.0 <= ent < math.log(36)


def test_low_stress_coverage_all_residential_is_one():
    ctx = fake_grown_context(k=4)  # grid is all residential (LTS 2)
    assert _run(ctx, "low_stress_coverage").value == pytest.approx(1.0)


def test_lts_split_coverage():
    ctx = fake_grown_context(k=4)  # all residential (LTS 2) -> lts2=1, lts1=0
    assert _run(ctx, "lts2_coverage").value == pytest.approx(1.0)
    assert _run(ctx, "lts1_coverage").value == pytest.approx(0.0)


def test_lcc_length_km_connected_grid():
    ctx = fake_grown_context(k=4)  # fully connected -> LCC = total = 2.4 km
    assert _run(ctx, "lcc_length_km_road").value == pytest.approx(2.4)


def test_area_densities_golden():
    ctx = fake_grown_context(k=4)  # 0.09 km2 box; road 2.4 km, 12 intersections
    assert _run(ctx, "street_density_km2").value == pytest.approx(2.4 / 0.09)
    assert _run(ctx, "intersection_density_km2_road").value == pytest.approx(12 / 0.09)


def test_relational_metrics_present_and_bounded():
    ctx = fake_grown_context(k=5)
    assert 0.0 <= _run(ctx, "bikeable_length_share").value <= 1.5
    assert _run(ctx, "entropy_gap_kl").value >= 0.0
    md = _run(ctx, "modal_directness_gap").value
    assert md >= 1.0 or math.isnan(md)  # low-stress route can't beat the drive route


@pytest.mark.parametrize(
    "highway,expected",
    [
        ("motorway", 4),
        ("residential", 2),
        ("cycleway", 1),
        ("service", 1),  # unknown -> DEFAULT_LTS
        (["residential", "service"], 2),  # list -> max stress
        (["cycleway", "primary"], 4),
        (None, 1),
    ],
)
def test_lts_lookup(highway, expected):
    assert lts_for_highway(highway) == expected


# --- geometry helpers ------------------------------------------------------


def test_kl_zero_for_identical_distributions():
    p = np.array([0.1, 0.2, 0.3, 0.4])
    assert kl_divergence(p, p) == pytest.approx(0.0, abs=1e-9)


def test_gini_zero_for_equal():
    assert gini(np.array([5.0, 5.0, 5.0])) == pytest.approx(0.0, abs=1e-9)


def test_orientation_histogram_normalised():
    net = grid_network(4)
    h = orientation_histogram(net.edges)
    assert h.sum() == pytest.approx(1.0)


# --- property tests (CLAUDE.md §7) -----------------------------------------


def test_lcc_never_exceeds_total():
    net = grid_network(5)
    assert net.lcc_length_m <= net.length_total_m + 1e-9


def test_components_at_least_one_when_nodes_present():
    assert grid_network(3).n_components >= 1


def test_component_lengths_sorted_descending():
    lengths = grid_network(4).component_lengths_m
    assert np.all(np.diff(lengths) <= 0)


def test_coverage_within_unit_interval():
    assert 0.0 <= _run(fake_grown_context(k=6), "low_stress_coverage").value <= 1.0
