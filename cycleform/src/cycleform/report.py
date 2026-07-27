"""Standalone reporting: load saved results and (re)make tables + figures.

Fully decoupled from metric computation -- reads results/combined_metrics.csv and
results/analysis_table.csv, so figures can be regenerated and restyled any time
after a batch has run, without recomputing anything. Rebuild those tables from
per-place files with `assemble.build_analysis_table()` (which calls
`results.build_combined()`); this module only consumes them.
"""

from __future__ import annotations

from pathlib import Path

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
        # compact grids, one per metric family, for discussing a group at a time
        paths.extend(figures.fig_metric_group_grids(table, corr))
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
    from cycleform import figures, models, outcomes, scenarios, typology
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
    # Observed rate from the harmonised outcomes, NOT the analysis table: a borough
    # can have an observed rate without being in the metric dataset (e.g. Gateshead
    # is in max_value.csv but has no computed metrics, so a table-based lookup left
    # it blank). Prefer the OECD FUA construct where a place has several, to match
    # the outcome the model is trained on.
    obs = outcomes.prefer_outcome(outcomes.build_outcomes(save=False).dropna(subset=["value"]))
    observed = obs.set_index("place_key")["value"].astype(float)
    pred["observed"] = pred["place_id"].map(place_key).map(observed)
    paths.append(figures.fig_scenario_prediction_shift(pred))

    # 2b. out-of-fold predicted shift: refit with each borough held out, so its
    # current-network and grown-network estimates come from a model that never saw
    # it (the full-fit numbers above are optimistic for places in the dataset).
    scen_aligned = scen_w.reindex(base_w.index)
    keys = table["place_id"].map(place_key)
    oof_rows = []
    for pid in base_w.index:
        train = table[keys != place_key(pid)]
        loo_pipe, loo_feats = models.fit_predictor(train, feature_set="form")
        oof_rows.append(
            {
                "place_id": pid,
                "baseline_oof": float(
                    models.predict_rate(loo_pipe, base_w.loc[[pid]], loo_feats)[0]
                ),
                "scenario_oof": float(
                    models.predict_rate(loo_pipe, scen_aligned.loc[[pid]], loo_feats)[0]
                ),
            }
        )
    pred_oof = pd.DataFrame(oof_rows)
    pred_oof["shift"] = pred_oof["scenario_oof"] - pred_oof["baseline_oof"]
    pred_oof["observed"] = pred_oof["place_id"].map(place_key).map(observed)
    paths.append(figures.fig_scenario_oof_prediction_shift(pred_oof))

    # 2c. the same out-of-fold shift against the whole predicted-vs-observed cloud
    # (all cities grey); each borough is an arrow from its current prediction up to
    # its grown-network prediction, at its observed rate on the x-axis.
    dataset_oof = models.predictions(table, feature_set="form")
    paths.append(figures.fig_scenario_pred_vs_actual_shift(pred_oof, dataset_oof))

    # 3. movement in form-space (PCA fit on the full dataset)
    proj = typology.project_scenario(dataset_wide, base_w, scen_w.reindex(base_w.index))
    paths.append(figures.fig_scenario_typology_shift(proj, base_w.index.tolist()))

    comp.to_csv(settings.results / "scenario_comparison.csv", index=False)
    pred.to_csv(settings.results / "scenario_predictions.csv", index=False)
    pred_oof.to_csv(settings.results / "scenario_predictions_oof.csv", index=False)
    return {
        "comparison": comp,
        "predictions": pred,
        "predictions_oof": pred_oof,
        "figures": paths,
    }


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


# --- plain-text results digest (for pasting into an LLM) ----------------------


def _fmt(v) -> str:
    """Compact cell formatting: ints as ints, floats to 3 dp, NaN blank."""
    if pd.isna(v):
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "yes" if v else "no"
    f = float(v)
    return str(int(f)) if f.is_integer() else f"{f:.3f}"


def _md_table(df: pd.DataFrame, cols: list[str] | None = None) -> str:
    """Render a DataFrame as a GitHub-flavoured markdown table (no dependency)."""
    cols = cols or list(df.columns)
    head = "| " + " | ".join(cols) + " |"
    rule = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(_fmt(r[c]) for c in cols) + " |" for _, r in df.iterrows()]
    return "\n".join([head, rule, *rows])


def text_report(path: Path | str | None = None, top_corr: int = 20, top_pred: int = 12) -> Path:
    """Write a markdown digest of the results to results/report.md and return the path.

    Assembles the dataset snapshot, metric-vs-cycling correlations, model
    performance/predictors (from the saved model CSVs), UK-vs-rest and
    bike-vs-road contrasts, the typology, and the grown-network what-if (if run).
    Reads only saved tables -- fast, no recompute -- so it is safe to call any
    time. Designed to be self-describing so an LLM can reason about it directly.
    """
    import datetime as _dt

    from cycleform import scenarios

    wide = load_wide()
    table = load_analysis()
    ver = str(wide["metric_version"].dropna().iloc[0]) if "metric_version" in wide.columns else "?"
    out = []

    def w(*lines):
        out.extend(lines)

    # --- header + study framing -------------------------------------------
    w(
        "# cycleform — results summary",
        "",
        f"_Generated {_dt.date.today().isoformat()} · metric_version {ver} · "
        f"snapshot {settings.snapshot_date}_",
        "",
        "**Study question.** Is the *form/structure* of a city's cycle network "
        "(and the road network it sits in) associated with its cycling rate across "
        "many cities, and can cycling rate be predicted from network form? Metrics "
        "are computed identically on real OSM cities and on Chapter-5 grown "
        "networks. This is a descriptive + predictive screen, not causal inference.",
        "",
    )

    # --- 1. dataset -------------------------------------------------------
    from cycleform import outcomes

    labelled = table.dropna(subset=["value"])
    n_out = labelled["place_key"].nunique() if "place_key" in labelled.columns else len(labelled)
    used = outcomes.prefer_outcome(labelled) if "place_key" in labelled.columns else labelled
    src_counts = used["source"].value_counts().to_dict() if "source" in used.columns else {}
    top_countries = wide["country"].value_counts().head(8).to_dict() if "country" in wide else {}

    # friendly source labels + year range per source (from the harmonised outcomes,
    # which carry the definitive year info). Eurostat and the 2011 UK census are
    # combined in the legacy max_value.csv and cannot be split from it.
    src_labels = {
        "modalshare": "ModalShare (Prieto-Curiel et al.; commute cycling share)",
        "oecd_fua": "OECD FUA (bicycle commute mode share)",
        "legacy_max_value": "Eurostat + 2011 UK census (legacy max_value.csv, mixed)",
    }
    try:
        allout = outcomes.build_outcomes(save=False)
    except Exception:
        allout = pd.DataFrame(columns=["source", "year"])

    def _year_range(source: str) -> str:
        ys = pd.to_numeric(allout.loc[allout["source"] == source, "year"], errors="coerce").dropna()
        if ys.empty:
            return "unspecified"
        return str(int(ys.min())) if ys.min() == ys.max() else f"{int(ys.min())}–{int(ys.max())}"

    src_table = pd.DataFrame(
        [
            {"source": src_labels.get(s, s), "places used": n, "years": _year_range(s)}
            for s, n in sorted(src_counts.items(), key=lambda kv: -kv[1])
        ]
    )
    w(
        "## 1. Dataset",
        "",
        f"- **{len(wide)} input places** with network metrics computed.",
        f"- **{n_out}** of them have an observed cycling rate (the modelled sample).",
        f"- UK places: **{int(wide['is_uk'].sum()) if 'is_uk' in wide else 0}**.",
        f"- Top countries by place count: {top_countries}.",
        "",
        "Cycling-rate outcome by source (one preferred source per place, "
        "ModalShare first, then OECD FUA, then legacy):",
        "",
        _md_table(src_table) if not src_table.empty else "_no outcome sources_",
        "",
        "_All three sources measure commute-to-work cycling share. ModalShare is a "
        "harmonised multi-source dataset and takes priority; OECD FUA and the legacy "
        "max_value.csv (mixed Eurostat + 2011 UK census, year unspecified) fill the "
        "places ModalShare doesn't cover._",
        "",
    )

    # --- 2. cycling rate outcome ------------------------------------------
    if not labelled.empty:
        v = used["value"].astype(float)
        w(
            "## 2. Cycling rate (outcome, % mode share)",
            "",
            f"- n={len(v)}, min={v.min():.1f}, median={v.median():.1f}, "
            f"mean={v.mean():.1f}, max={v.max():.1f}, sd={v.std():.1f}.",
            "- Right-skewed; correlations below use Spearman (rank-based, robust).",
            "",
        )

    # --- 3. correlations with cycling rate --------------------------------
    corr = describe.correlate_with_outcome(table)
    if not corr.empty:
        show = corr.head(top_corr)[
            ["metric", "spearman", "spearman_p", "pearson", "n", "significant"]
        ].copy()
        show["spearman_p"] = show["spearman_p"].map(lambda p: "<0.001" if p < 0.001 else f"{p:.3f}")
        pos = corr[corr["spearman"] > 0].head(3)["metric"].tolist()
        neg = corr[corr["spearman"] < 0].head(3)["metric"].tolist()
        w(
            "## 3. Metric correlations with cycling rate",
            "",
            f"Ranked by |Spearman rho|, top {len(show)} of {len(corr)} analysed metrics. "
            "`significant` = two-sided p < 0.05. Correlation is a signpost, not a model.",
            "",
            _md_table(show),
            "",
            f"- Strongest **positive**: {', '.join(pos)}.",
            f"- Strongest **negative**: {', '.join(neg)}.",
            "",
        )

    # --- 4. predictive model (read saved CSVs) ----------------------------
    perf_p = settings.results / "model_performance.csv"
    imp_p = settings.results / "model_feature_importance.csv"
    if perf_p.exists():
        perf = pd.read_csv(perf_p)
        w(
            "## 4. Predictive model (cross-validated)",
            "",
            "Out-of-sample R² for three feature sets: network **form** only, "
            "**country** (national context) only, and **form+country**. "
            "Compares how much network form predicts beyond national context.",
            "",
            _md_table(perf),
            "",
        )
        if imp_p.exists():
            imp = pd.read_csv(imp_p).head(top_pred)
            w(
                f"Top {len(imp)} network-form predictors (random-forest permutation "
                "importance, form-only model):",
                "",
                _md_table(imp[["metric", "importance", "importance_sd"]]),
                "",
            )
    else:
        w(
            "## 4. Predictive model",
            "",
            "_Not available — run `report.make_model_report()` to generate "
            "model_performance.csv / model_feature_importance.csv._",
            "",
        )

    # --- 5. UK vs rest ----------------------------------------------------
    key = [
        "bikeable_length_share", "low_stress_coverage", "bike_lcc_share_of_road",
        "meshedness_bike", "circuity_avg_bike", "components_per_km_bike",
        "intersection_density_per_km_road",
    ]
    uvr = describe.uk_vs_rest(wide)
    uvr_k = uvr[uvr.index.isin(key)].reset_index().rename(columns={"index": "metric"})
    if not uvr_k.empty:
        w(
            "## 5. UK vs rest of sample (key metrics)",
            "",
            _md_table(uvr_k[["metric", "uk_mean", "rest_mean", "uk_minus_rest", "n_uk", "n_rest"]]),
            "",
        )

    # --- 6. bike vs road --------------------------------------------------
    bvr = describe.bike_vs_road(wide)
    if not bvr.empty:
        w(
            "## 6. Bike vs road network form",
            "",
            "`bike_gt_road_share` = fraction of cities where the cycle network "
            "exceeds the road network on that metric.",
            "",
            _md_table(bvr[["metric", "road_mean", "bike_mean", "bike_minus_road_mean",
                           "bike_gt_road_share", "n"]]),
            "",
        )

    # --- 7. typology ------------------------------------------------------
    try:
        typ = build_typology(wide)
        sizes = pd.Series(typ.labels).value_counts().sort_index().to_dict()
        prof = typ.profiles.reset_index().rename(columns={"cluster": "type"})
        w(
            "## 7. Network-form typology",
            "",
            f"Standardise → PCA → k-means. **k={typ.k}** (silhouette "
            f"{typ.silhouette}); cluster sizes {sizes}. Profiles are mean "
            "standardised (z) values per cluster (features: "
            f"{', '.join(typ.features)}):",
            "",
            _md_table(prof.round(2)),
            "",
        )
    except Exception as exc:  # typology needs enough complete rows
        w("## 7. Network-form typology", "", f"_Unavailable: {exc}_", "")

    # --- 8. grown-network what-if -----------------------------------------
    try:
        comp = scenarios.build_scenario_table()
    except Exception:
        comp = pd.DataFrame()
    pred_p = settings.results / "scenario_predictions.csv"
    if not comp.empty:
        w(
            "## 8. Grown-network what-if (Tyne & Wear)",
            "",
            "Merging each borough's Chapter-5 grown cycle network, then re-measuring.",
            "",
        )
        if pred_p.exists():
            pred = pd.read_csv(pred_p)
            cols = [c for c in ["place_id", "observed", "baseline_pred", "scenario_pred", "shift"]
                    if c in pred.columns]
            w("Predicted cycling rate now vs with the grown network "
              "(model fit on the full dataset, borough included):", "",
              _md_table(pred[cols]), "")
        oof_p = settings.results / "scenario_predictions_oof.csv"
        if oof_p.exists():
            oof = pd.read_csv(oof_p)
            cols = [c for c in ["place_id", "observed", "baseline_oof", "scenario_oof", "shift"]
                    if c in oof.columns]
            w("Out-of-fold predicted rate (each borough held out of training -- the "
              "honest estimate):", "", _md_table(oof[cols]), "")

    # --- 9. caveats -------------------------------------------------------
    w(
        "## 9. Key caveats",
        "",
        "- Correlations/predictions are descriptive + predictive, **not causal** "
        "(no confounder control yet; that is future work).",
        "- Spearman is primary (cycling rate is skewed); Pearson shown alongside.",
        "- A few metrics (entropy_gap_kl, bike centralities, components_per_km_bike) "
        "have extreme values driven by cities with a near-empty cycle network; these "
        "are kept (rank-based stats are robust), so plots show real outliers.",
        "- Bike layer is raw OSM; road layer is neatnet-simplified — so raw *count* "
        "metrics are comparable within a layer across cities, not bike-vs-road.",
        "- Densities are normalised by network length, not built-up area.",
        "- `n` varies by metric: ~45 places predate newer metrics (fixed by "
        "re-running) and some metrics are genuinely undefined (e.g. gini on a "
        "single-component network).",
        "",
    )

    text = "\n".join(out)
    path = Path(path or (settings.results / "report.md"))
    path.write_text(text, encoding="utf-8")
    return path
