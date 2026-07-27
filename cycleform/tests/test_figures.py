"""Trend-guide selection (figures._fit_trend / _add_trend).

The overlaid scatter curve is a guide to the eye chosen from a fixed candidate set
by AICc (see ASSUMPTIONS.md > Figures). These tests pin the two behaviours that
make it defensible: the objective form selection, and the physical floor (cycling
rate can never be negative, so the drawn curve and axis must not go below 0).
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cycleform.figures import (
    GROUP_LABELS,
    METRIC_GROUPS,
    _add_trend,
    _fit_trend,
)


def _x() -> np.ndarray:
    return np.linspace(50.0, 400.0, 300)


def test_selects_linear_for_linear_data():
    rng = np.random.default_rng(0)
    x = _x()
    y = np.clip(30 - 0.05 * x + rng.normal(0, 2, x.size), 0, None)
    name, _, r2 = _fit_trend(x, y)
    assert name == "linear"
    assert r2 > 0.5


def test_selects_exponential_for_exponential_decay():
    rng = np.random.default_rng(1)
    x = _x()
    y = np.clip(40 * np.exp(-0.01 * x) + rng.normal(0, 1, x.size), 0, None)
    name, _, _ = _fit_trend(x, y)
    assert name == "exponential"


def test_candidate_set_is_linear_or_exponential_only():
    """The log form was dropped (2026-07-24): only linear/exponential are offered."""
    rng = np.random.default_rng(2)
    x = _x()
    y = np.clip(2 + 5 * np.log(x) + rng.normal(0, 1, x.size), 0, None)
    name, _, _ = _fit_trend(x, y)
    assert name in {"linear", "exponential"}


def test_curve_and_axis_never_go_negative():
    """A steeply declining relationship must not draw below 0 or floor the axis
    negative -- the bug this fix addresses (impossible negative cycling rates)."""
    rng = np.random.default_rng(3)
    x = _x()
    y = np.clip(35 - 0.09 * x + rng.normal(0, 1, x.size), 0, None)  # crosses 0 within range
    fig, ax = plt.subplots()
    ax.scatter(x, y, s=3)
    _add_trend(ax, x, y)
    line = ax.lines[-1]
    assert line.get_ydata().min() >= 0.0
    assert ax.get_ylim()[0] == 0.0
    plt.close(fig)


def test_too_few_points_returns_none():
    assert _fit_trend(np.array([1.0, 2.0]), np.array([1.0, 2.0])) is None


def test_metric_group_taxonomy_is_consistent():
    """Every group has a label and no base metric is assigned to two groups (so a
    metric can never orphan or be double-counted across the family grids)."""
    assert set(METRIC_GROUPS) == set(GROUP_LABELS)
    seen: set[str] = set()
    for bases in METRIC_GROUPS.values():
        for base in bases:
            assert base not in seen, f"{base} assigned to more than one group"
            seen.add(base)
