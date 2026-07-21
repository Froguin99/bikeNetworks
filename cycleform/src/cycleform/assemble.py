"""Assemble the analysis table: metrics x cycling-rate outcomes (Phase 3).

Joins the wide metric table (`results/combined_metrics.csv`, one row per place)
to the harmonised outcomes (`results/outcomes_long.csv`, one row per place x
source) on a normalised `place_key`. The result stays long on the outcome side:
one row per (place, outcome observation), so `source` and `measure_type` remain
available as fixed effects (CLAUDE.md §4).

Matching is exact on `place_key`, plus an optional manual `aliases` map for the
inevitable name mismatches (e.g. OSM "Munster" vs OECD "Munster (Westf)"). Every
unmatched place is logged and returned, never silently dropped (§10).
"""

from __future__ import annotations

import logging

import pandas as pd

from cycleform.config import settings
from cycleform.outcomes import build_outcomes, place_key

log = logging.getLogger(__name__)

# Manual place-key aliases: metric place_key -> outcome place_key. Populated as
# name mismatches surface (the outcome sources name FUAs differently from OSM).
# TODO: the join is not yet country-aware, so a bare "york" matches two OECD FUAs
# named York; add country to the key to disambiguate.
ALIASES: dict[str, str] = {
    "chester": "cheshire west and chester",
    "bath": "bath and north east somerset",
    "florence": "firenze",  # OECD uses the Italian endonym
    "ghent": "gent",  # OECD uses the Dutch endonym
}


def load_metrics_wide() -> pd.DataFrame:
    """The combined per-place metric table, with a `place_key` column added."""
    path = settings.results / "combined_metrics.csv"
    wide = pd.read_csv(path)
    wide["place_key"] = wide["place_id"].map(place_key)
    return wide


def build_analysis_table(
    aliases: dict[str, str] | None = None, save: bool = True
) -> tuple[pd.DataFrame, dict]:
    """Join metrics to outcomes on place_key. Returns (table, coverage report).

    `aliases` maps a metric place_key to the outcome place_key it should match
    (applied to the metric side before joining). The returned report counts
    matched/unmatched places on both sides so missingness is a visible number.
    """
    metrics = load_metrics_wide()
    metrics["place_key"] = metrics["place_key"].replace({**ALIASES, **(aliases or {})})
    outcomes = build_outcomes(save=False)

    table = outcomes.merge(metrics, on="place_key", how="inner", suffixes=("_outcome", ""))
    # country-aware: keep a joined row only when the outcome has no country (legacy,
    # matched on name alone) or its country matches the metric place's country.
    # This drops cross-country false matches (e.g. a non-UK FUA also named "York").
    if "country_outcome" in table.columns and "country" in table.columns:
        oc = table["country_outcome"]
        table = table[oc.isna() | (oc == "") | (oc == table["country"])]

    matched = set(table["place_key"])
    metric_keys = set(metrics["place_key"])
    unmatched_metrics = sorted(metric_keys - matched)
    report = {
        "metric_places": len(metric_keys),
        "outcome_places": outcomes["place_key"].nunique(),
        "matched_places": len(matched),
        "analysis_rows": len(table),
        "metric_places_without_outcome": unmatched_metrics,
    }
    log.info(
        "analysis table: %d metric places, %d matched an outcome -> %d rows",
        report["metric_places"],
        report["matched_places"],
        report["analysis_rows"],
    )
    if unmatched_metrics:
        log.info("metric places with no outcome match: %s", unmatched_metrics)
    if save:
        settings.results.mkdir(parents=True, exist_ok=True)
        out = settings.results / "analysis_table.csv"
        table.to_csv(out, index=False)
        log.info("analysis table -> %s", out)
    return table, report
