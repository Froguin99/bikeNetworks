"""Standalone reporting: load saved results and (re)make tables + figures.

Fully decoupled from metric computation -- reads results/combined_metrics.csv and
results/analysis_table.csv, so figures can be regenerated and restyled any time
after a batch has run, without recomputing anything. Rebuild those tables from
per-place files with `assemble.build_analysis_table()` (which calls
`results.build_combined()`); this module only consumes them.
"""

from __future__ import annotations

import pandas as pd

from cycleform import describe, figures
from cycleform.assemble import build_analysis_table
from cycleform.config import settings
from cycleform.results import build_combined
from cycleform.typology import build_typology


def refresh() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rebuild combined + analysis tables from the per-place files on disk.

    Call this to pick up places computed since the last rebuild -- so you can
    analyse and plot while a batch is still running. Returns (wide, analysis).
    """
    wide = build_combined()
    table, _ = build_analysis_table(save=True)
    return wide.reset_index(), table


def load_wide(refresh_first: bool = False) -> pd.DataFrame:
    """The combined per-place metric table (place_id as a column)."""
    if refresh_first:
        return refresh()[0]
    path = settings.results / "combined_metrics.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found -- run a batch / build_combined first")
    return pd.read_csv(path)


def load_analysis(refresh_first: bool = False) -> pd.DataFrame:
    """The metrics x cycling-rate analysis table."""
    if refresh_first:
        return refresh()[1]
    path = settings.results / "analysis_table.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found -- run assemble.build_analysis_table first")
    return pd.read_csv(path)


# Ranked dot-plots and bike-vs-road panels for a small curated set (these are
# per-place plots, too many to draw for everything). The metric-vs-cycling
# scatters are drawn for EVERY analysed metric (see make_figures).
RANKED_METRICS = ["bikeable_length_share", "bike_offroad_share", "meshedness_bike"]
BIKE_VS_ROAD = ["orientation_entropy", "meshedness", "lcc_length_share", "circuity_avg"]


def make_figures(
    ranked: list[str] | None = None,
    bike_vs_road: list[str] | None = None,
    refresh_first: bool = False,
    top_n: int = 9,
    all_scatters: bool = True,
) -> list:
    """Regenerate the standard figures from saved results. Returns output paths.

    Draws an individual metric-vs-cycling scatter for EVERY analysed metric
    (all_scatters), plus the correlation overview, top-N grid, metric-metric
    heatmap, typology, and the curated ranked / bike-vs-road panels. Set
    refresh_first=True to rebuild tables from per-place files first (useful
    while a batch is still running).
    """
    wide = load_wide(refresh_first=refresh_first)
    table = load_analysis()
    # Self-heal: figures are PNG-only now, so remove any legacy PDFs left by older
    # versions (the pipeline never writes PDFs; see figures.save).
    for stale in (settings.results / "figures").glob("*.pdf"):
        stale.unlink()
    corr = describe.correlate_with_outcome(table)
    typ = build_typology(wide)
    # typology + prediction-style figures come in unlabelled and labelled variants
    paths = [figures.fig_typology(typ, labels=False), figures.fig_typology(typ, labels=True)]
    if not corr.empty:
        paths.append(figures.fig_outcome_correlations(corr, top=None))  # every metric
        paths.append(figures.fig_top_correlates(table, corr, n=top_n))
        paths.append(figures.fig_metric_correlation_heatmap(wide))  # every metric
    # one scatter per analysed metric, in both unlabelled and labelled variants
    if all_scatters and not corr.empty:
        for m in corr["metric"]:
            if m in table.columns:
                paths.append(figures.fig_outcome_relationship(table, m, labels=False))
                paths.append(figures.fig_outcome_relationship(table, m, labels=True))
    for m in ranked or RANKED_METRICS:
        if m in wide.columns:
            paths.append(figures.fig_metric_ranked(wide, m))
    for base in bike_vs_road or BIKE_VS_ROAD:
        if f"{base}_road" in wide.columns and f"{base}_bike" in wide.columns:
            paths.append(figures.fig_bike_vs_road(wide, base, labels=False))
            paths.append(figures.fig_bike_vs_road(wide, base, labels=True))
    return paths


def make_model_report() -> dict:
    """Fit the predictive model, save its figures, and return the results tables.

    Returns {'performance': df, 'importance': df} and writes model_pred_vs_actual
    + model_feature_importance to results/figures/. Prediction, not causal
    inference (see models.py).
    """
    from cycleform import models

    table = load_analysis()
    perf = models.evaluate(table)
    imp = models.feature_importance(table)
    best_r2 = perf.loc[perf["feature_set"].eq("form"), "cv_r2"].max()
    pred = models.predictions(table, feature_set="form")
    figures.fig_pred_vs_actual(pred, r2=best_r2, labels=False)
    figures.fig_pred_vs_actual(pred, r2=best_r2, labels=True)
    figures.fig_feature_importance(imp)
    perf.to_csv(settings.results / "model_performance.csv", index=False)
    imp.to_csv(settings.results / "model_feature_importance.csv", index=False)
    return {"performance": perf, "importance": imp}


def make_scenario_report() -> dict:
    """Figures + tables for the grown-network what-if (cycleform.scenarios).

    Reads the saved baseline/scenario runs (results/scenarios/), and draws, for the
    Tyne & Wear boroughs: a per-place metric-shift dumbbell, the predicted
    cycling-rate shift (model fit on the full cross-city dataset), and movement in
    form-space. Writes scenario_comparison.csv + scenario_predictions.csv. Assumes
    `scenarios.run_scenarios()` has already produced the per-place files.
    """
    from cycleform import figures, models, scenarios, typology
    from cycleform.outcomes import place_key

    comp = scenarios.build_scenario_table()
    if comp.empty:
        raise FileNotFoundError(
            "no scenario results in results/scenarios/ -- run scenarios.run_scenarios() first"
        )
    dataset_wide = load_wide()
    table = load_analysis()
    paths = []

    # 1. metric-shift dumbbell per borough
    for pid in comp["place_id"].unique():
        paths.append(figures.fig_scenario_shift(comp, pid, dataset_wide))

    # 2. predicted cycling-rate shift (model fit on the full dataset, form features)
    pipe, feats = models.fit_predictor(table, feature_set="form")
    base_w, scen_w = scenarios.scenario_wide("baseline"), scenarios.scenario_wide("scenario")
    pred = pd.DataFrame(
        {
            "place_id": base_w.index,
            "baseline_pred": models.predict_rate(pipe, base_w, feats),
            "scenario_pred": models.predict_rate(pipe, scen_w.reindex(base_w.index), feats),
        }
    )
    pred["shift"] = pred["scenario_pred"] - pred["baseline_pred"]
    observed = (
        table.assign(_k=table["place_id"].map(place_key))
        .dropna(subset=["value"])
        .groupby("_k")["value"]
        .first()
    )
    pred["observed"] = pred["place_id"].map(place_key).map(observed)
    paths.append(figures.fig_scenario_prediction_shift(pred))

    # 3. movement in form-space (PCA fit on the full dataset)
    proj = typology.project_scenario(dataset_wide, base_w, scen_w.reindex(base_w.index))
    paths.append(figures.fig_scenario_typology_shift(proj, base_w.index.tolist()))

    comp.to_csv(settings.results / "scenario_comparison.csv", index=False)
    pred.to_csv(settings.results / "scenario_predictions.csv", index=False)
    return {"comparison": comp, "predictions": pred, "figures": paths}


def summary_tables() -> dict[str, pd.DataFrame]:
    """The Q1 descriptive tables + the metric-vs-cycling correlation ranking."""
    wide = load_wide()
    table = load_analysis()
    return {
        "bike_vs_road": describe.bike_vs_road(wide),
        "uk_vs_rest": describe.uk_vs_rest(wide),
        "by_country": describe.by_country(wide),
        "correlations": describe.correlate_with_outcome(table),
    }
