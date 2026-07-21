"""Persist metric results to 2026_edition/results/.

Layout:
    results/places/<place_id>.csv   one file per place, all metrics (long form,
                                    keeps status/detail so missingness is visible)
    results/combined_metrics.csv    one row per place, one column per metric (wide)

Per-place files are the source of truth and are written as each place finishes,
so a long run can be resumed. `build_combined` stitches them into the wide table.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from cycleform.config import settings
from cycleform.metrics.base import MetricResult, PlaceContext
from cycleform.metrics.registry import results_to_frame

log = logging.getLogger(__name__)


def _safe_name(place_id: str) -> str:
    return "".join(c if c.isalnum() or c in " -_,." else "_" for c in place_id).strip()


def place_path(place_id: str) -> Path:
    """Path to a place's per-place results CSV (whether or not it exists)."""
    return settings.results_places / f"{_safe_name(place_id)}.csv"


def cached_version(place_id: str) -> str | None:
    """The metric_version a place was last computed under, or None if not cached."""
    p = place_path(place_id)
    if not p.exists():
        return None
    head = pd.read_csv(p, nrows=1)
    return str(head["metric_version"].iloc[0]) if "metric_version" in head.columns else None


def is_cached(place_id: str, version: str | None = None) -> bool:
    """True if the place is already computed under `version` (default: current)."""
    return cached_version(place_id) == (version or settings.metric_version)


def save_place(ctx: PlaceContext, results: Iterable[MetricResult]) -> str:
    """Write one place's results to results/places/<place_id>.csv. Returns the path."""
    settings.results_places.mkdir(parents=True, exist_ok=True)
    frame = results_to_frame(results)
    frame.insert(0, "metric_version", settings.metric_version)
    frame.insert(0, "country", ctx.meta.get("country", ""))
    frame.insert(0, "source", ctx.source)
    frame.insert(0, "snapshot_date", ctx.snapshot_date)
    path = place_path(ctx.place_id)
    frame.to_csv(path, index=False)
    n_ok = int((frame["status"] == "ok").sum())
    log.info("%s: wrote %d metrics (%d ok) -> %s", ctx.place_id, len(frame), n_ok, path.name)
    return str(path)


def load_place(place_id: str) -> pd.DataFrame:
    """Read back one place's long results frame."""
    return pd.read_csv(settings.results_places / f"{_safe_name(place_id)}.csv")


def build_combined() -> pd.DataFrame:
    """Stitch every per-place file into the wide combined table and save it.

    Missing/errored metrics stay NaN. A `status` breakdown is logged so dropped
    values are never silent (CLAUDE.md §10).
    """
    files = sorted(settings.results_places.glob("*.csv"))
    if not files:
        log.warning("no per-place files in %s", settings.results_places)
        return pd.DataFrame()
    frames = [pd.read_csv(f) for f in files]
    long = pd.concat(frames, ignore_index=True)
    wide = long.pivot_table(
        index="place_id", columns="metric", values="value", aggfunc="first"
    ).rename_axis(columns=None)
    for col in ("metric_version", "country"):  # carry per-place bookkeeping onto wide
        if col in long.columns:
            wide.insert(0, col, long.groupby("place_id")[col].first())
    if "country" in wide.columns:  # explicit UK flag for easy plotting
        wide.insert(wide.columns.get_loc("country") + 1, "is_uk", wide["country"].eq("UK"))
    not_ok = long[long["status"] != "ok"]
    if len(not_ok):
        by_status = not_ok["status"].value_counts().to_dict()
        log.info("combined: %d non-ok cells across places: %s", len(not_ok), by_status)
    out = settings.results / "combined_metrics.csv"
    wide.to_csv(out)
    log.info("combined: %d places x %d metrics -> %s", wide.shape[0], wide.shape[1], out)
    return wide
