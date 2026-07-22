"""Journal-grade figures (CLAUDE.md: all plots must be publication quality).

Static matplotlib, saved as 300-dpi PNG to results/figures/.
Design follows the dataviz principles adapted for print: form chosen for the
data's job, one axis, thin recessive marks, direct labels when points are few,
and the Okabe-Ito categorical palette -- a published colourblind-safe scheme,
the academic standard, used in fixed order and never cycled.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cycleform.config import settings

# Okabe & Ito (2008) colourblind-safe qualitative palette, fixed order.
OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
NEUTRAL = "#9A9A9A"  # for the folded "Other" category
MAX_HUES = 6  # never cycle the palette; rarer categories fold into "Other"

# A fixed, consistent set of exemplar cities to label on the "_labeled" figures --
# spread across countries and the cycling-rate range. Matched by de-accented
# place_key; any not present in the data are simply skipped.
HIGHLIGHT_PLACES = {
    "newcastle upon tyne", "cambridge", "malmo", "antwerpen", "munster",
    "memphis", "trento", "nice", "fuji", "oslo",
}


def _highlight_key(place_id: object) -> str:
    """De-accented, country-stripped key for matching HIGHLIGHT_PLACES."""
    from cycleform.outcomes import place_key

    return place_key(str(place_id))


def set_style() -> None:
    """Restrained academic rcParams: serif, hairline spines, no top/right axes."""
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "font.family": "serif",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.6,
            "axes.grid": True,
            "grid.linewidth": 0.4,
            "grid.alpha": 0.4,
            "legend.frameon": False,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )


def _figures_dir() -> Path:
    d = settings.results / "figures"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(fig: plt.Figure, name: str) -> Path:
    """Save a figure as PNG to results/figures/; returns the path."""
    d = _figures_dir()
    fig.savefig(d / f"{name}.png", bbox_inches="tight")
    plt.close(fig)
    return d / f"{name}.png"


def _country_palette(countries: pd.Series) -> tuple[pd.Series, dict[str, str]]:
    """Fold to the MAX_HUES most frequent countries + 'Other'; assign fixed hues.

    Never cycles the palette (a dataviz non-negotiable): rarer countries share a
    neutral grey 'Other' rather than being given an ambiguous reused hue.
    """
    counts = countries.value_counts()
    keep = list(counts.index[:MAX_HUES])
    cmap = {c: OKABE_ITO[i] for i, c in enumerate(keep)}
    folded = countries.where(countries.isin(keep), "Other")
    if (folded == "Other").any():
        cmap["Other"] = NEUTRAL
    return folded, cmap


def fig_metric_ranked(wide: pd.DataFrame, metric: str, label: str | None = None) -> Path:
    """Ranked dot plot of one metric across places, coloured by country.

    Answers 'where does each city sit in the distribution' -- the Q1 framing.
    """
    set_style()
    d = wide.dropna(subset=[metric]).sort_values(metric)
    folded, cmap = _country_palette(d["country"]) if "country" in d.columns else (None, {})
    fig, ax = plt.subplots(figsize=(5.5, max(2.5, 0.28 * len(d))))
    y = np.arange(len(d))
    cvals = [cmap.get(c, OKABE_ITO[0]) for c in (folded if folded is not None else ["?"] * len(d))]
    ax.hlines(y, 0, d[metric], color="0.85", lw=0.8, zorder=1)
    ax.scatter(d[metric], y, c=cvals, s=28, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(d["place_id"] if "place_id" in d.columns else d.index)
    ax.set_xlabel(label or metric)
    ax.grid(axis="y", visible=False)
    if cmap:
        handles = [plt.Line2D([], [], marker="o", ls="", color=v, label=k) for k, v in cmap.items()]
        ax.legend(handles=handles, title="", loc="lower right", ncol=1)
    return save(fig, f"ranked_{metric}")


def fig_bike_vs_road(
    wide: pd.DataFrame, base: str, label: str | None = None, labels: bool = False
) -> Path:
    """Scatter of a metric on the bike vs road network, with the y=x reference.

    `labels=True` annotates the fixed HIGHLIGHT_PLACES exemplars and is saved with
    a `_labeled` suffix (consistent with the other per-city figures)."""
    set_style()
    rc, bc = f"{base}_road", f"{base}_bike"
    d = wide.dropna(subset=[rc, bc]).copy()
    folded, cmap = _country_palette(d["country"]) if "country" in d.columns else (None, {})
    d["_cc"] = folded if folded is not None else "?"
    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    lo = float(min(d[rc].min(), d[bc].min()))
    hi = float(max(d[rc].max(), d[bc].max()))
    ax.plot([lo, hi], [lo, hi], color="0.6", lw=0.8, ls="--", zorder=1)
    for c, sub in d.groupby("_cc"):
        ax.scatter(sub[rc], sub[bc], s=30, color=cmap.get(c, OKABE_ITO[0]), label=c, zorder=2)
    if labels:
        _annotate_highlights(ax, d, rc, bc)
    ax.set_xlabel(f"road: {label or base}")
    ax.set_ylabel(f"cycle: {label or base}")
    ax.set_aspect("equal", adjustable="datalim")
    if cmap:
        ax.legend(title="", loc="best")
    return save(fig, f"bike_vs_road_{base}" + ("_labeled" if labels else ""))


def fig_typology(typ, labels: bool = False) -> Path:
    """PCA scatter of places, colour = cluster. `labels=True` annotates the
    HIGHLIGHT_PLACES exemplars only (saved with a `_labeled` suffix)."""
    set_style()
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    scores, clusters = typ.scores, typ.labels
    for cl in sorted(set(clusters)):
        m = clusters == cl
        ax.scatter(scores[m, 0], scores[m, 1], s=42, color=OKABE_ITO[cl % len(OKABE_ITO)],
                   label=f"type {cl}", zorder=2)
    if labels:
        for i, name in enumerate(typ.place_ids):
            if _highlight_key(name) in HIGHLIGHT_PLACES:
                ax.annotate(str(name).split(",")[0], (scores[i, 0], scores[i, 1]),
                            fontsize=7, xytext=(3, 3), textcoords="offset points", color="0.25")
    ev = typ.explained_variance
    ax.set_xlabel(f"PC1 ({ev[0]:.0%} var)")
    ax.set_ylabel(f"PC2 ({ev[1]:.0%} var)" if len(ev) > 1 else "PC2")
    ax.set_title(f"Network-form typology (k={typ.k}, silhouette={typ.silhouette})")
    ax.legend(title="", loc="best")
    return save(fig, "typology_pca" + ("_labeled" if labels else ""))


def _annotate_highlights(ax, d: pd.DataFrame, xcol: str, ycol: str) -> None:
    """Label just the HIGHLIGHT_PLACES rows present in `d`."""
    if "place_id" not in d.columns:
        return
    keys = d["place_id"].map(_highlight_key)
    for _, r in d[keys.isin(HIGHLIGHT_PLACES)].iterrows():
        ax.annotate(
            str(r["place_id"]).split(",")[0],
            (r[xcol], r[ycol]),
            fontsize=7,
            xytext=(3, 3),
            textcoords="offset points",
            color="0.25",
        )


def fig_outcome_relationship(
    table: pd.DataFrame,
    metric: str,
    label: str | None = None,
    source: str = "oecd_fua",
    labels: bool = False,
) -> Path:
    """Scatter of a metric against cycling rate (the Q2 preview).

    One point per place (preferring `source`), coloured by country, with a
    Spearman correlation in the title. `labels=False` gives a clean points-only
    figure; `labels=True` annotates the fixed HIGHLIGHT_PLACES exemplars and is
    saved with a `_labeled` suffix.
    """
    set_style()
    d = table.dropna(subset=[metric, "value"]).copy()
    d = d.sort_values("source", key=lambda s: s.ne(source)).drop_duplicates("place_key")
    folded, cmap = _country_palette(d["country"]) if "country" in d.columns else (None, {})
    d["_cc"] = folded if folded is not None else "?"
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    for c, sub in d.groupby("_cc"):
        ax.scatter(
            sub[metric], sub["value"], s=32, color=cmap.get(c, OKABE_ITO[0]),
            label=c, zorder=2, edgecolor="white", linewidth=0.4,
        )
    if labels:
        _annotate_highlights(ax, d, metric, "value")
    _add_trend(ax, d[metric].to_numpy(), d["value"].to_numpy())
    rho, p = _spearman(d[metric], d["value"])
    ax.set_xlabel(label or metric)
    ax.set_ylabel("cycling rate (% mode share)")
    ax.set_title(f"n={len(d)}   Spearman rho={rho:.2f}, p={_pfmt(p)}")
    if cmap:
        ax.legend(title="", loc="best", ncol=2)
    return save(fig, f"outcome_vs_{metric}" + ("_labeled" if labels else ""))


def _spearman(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    from scipy import stats

    rho, p = stats.spearmanr(x, y)
    return float(rho), float(p)


def _pfmt(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def _add_trend(ax, x: np.ndarray, y: np.ndarray) -> None:
    """Least-squares trend line over the current x-range (guide to the eye)."""
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 3:
        return
    b, a = np.polyfit(x[ok], y[ok], 1)
    xs = np.linspace(x[ok].min(), x[ok].max(), 50)
    ax.plot(xs, a + b * xs, color="0.35", lw=1.2, ls="-", zorder=1)


def fig_outcome_correlations(corr: pd.DataFrame, top: int = 25) -> Path:
    """Ranked horizontal bars of each metric's Spearman correlation with cycling.

    The 'correlation matrix against cycling rate': the metrics by |rho| (all by
    default), blue = positive, orange = negative, p<0.05 ones with a solid edge.
    """
    set_style()
    d = corr.head(top).iloc[::-1] if top else corr.iloc[::-1]
    colors = [OKABE_ITO[0] if v >= 0 else OKABE_ITO[3] for v in d["spearman"]]
    edges = ["black" if s else "none" for s in d.get("significant", [False] * len(d))]
    fig, ax = plt.subplots(figsize=(6.0, max(3.0, 0.28 * len(d))))
    ax.barh(range(len(d)), d["spearman"], color=colors, edgecolor=edges, linewidth=0.8)
    ax.axvline(0, color="0.4", lw=0.6)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["metric"], fontsize=6)
    ax.set_xlabel("Spearman correlation with cycling rate")
    ax.set_title(f"{len(d)} metrics (solid edge = p<0.05, n~{int(corr['n'].median())})")
    ax.grid(axis="y", visible=False)
    return save(fig, "correlations_vs_cycling")


def fig_top_correlates(
    table: pd.DataFrame, corr: pd.DataFrame, n: int = 9, source: str = "oecd_fua"
) -> Path:
    """Small-multiples grid of the top-n significant metrics vs cycling rate.

    Each panel: scatter + trend line + Spearman rho and p. Points are one per
    place (preferring `source`); panels share the cycling-rate y-axis.
    """
    set_style()
    sig = corr[corr.get("significant", True)].head(n)
    if sig.empty:
        sig = corr.head(n)
    d = table.dropna(subset=["value"]).copy()
    d = d.sort_values("source", key=lambda s: s.ne(source)).drop_duplicates("place_key")
    ncol = 3
    nrow = int(np.ceil(len(sig) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.2 * ncol, 2.8 * nrow), squeeze=False)
    for ax in axes.flat:
        ax.set_visible(False)
    for i, (_, row) in enumerate(sig.iterrows()):
        m = row["metric"]
        ax = axes.flat[i]
        ax.set_visible(True)
        sub = d.dropna(subset=[m])
        ax.scatter(
            sub[m],
            sub["value"],
            s=14,
            color=OKABE_ITO[0],
            alpha=0.7,
            edgecolor="white",
            linewidth=0.3,
        )
        _add_trend(ax, sub[m].to_numpy(), sub["value"].to_numpy())
        ax.set_title(f"{m}\nrho={row['spearman']:.2f}, p={_pfmt(row['spearman_p'])}", fontsize=7.5)
        ax.tick_params(labelsize=6)
        if i % ncol == 0:
            ax.set_ylabel("cycling %", fontsize=7)
    fig.tight_layout()
    return save(fig, "top_correlates_grid")


def fig_pred_vs_actual(pred: pd.DataFrame, r2: float | None = None, labels: bool = False) -> Path:
    """Out-of-fold predicted vs actual cycling rate, coloured by country, y=x line.

    `labels=True` annotates the HIGHLIGHT_PLACES exemplars (saved `_labeled`)."""
    set_style()
    d = pred.dropna(subset=["actual", "predicted"]).copy()
    folded, cmap = _country_palette(d["country"]) if "country" in d.columns else (None, {})
    d["_cc"] = folded if folded is not None else "?"
    fig, ax = plt.subplots(figsize=(4.6, 4.6))
    lo = float(min(d["actual"].min(), d["predicted"].min()))
    hi = float(max(d["actual"].max(), d["predicted"].max()))
    ax.plot([lo, hi], [lo, hi], color="0.6", lw=0.8, ls="--", zorder=1)
    for c, sub in d.groupby("_cc"):
        ax.scatter(
            sub["actual"], sub["predicted"], s=26, color=cmap.get(c, OKABE_ITO[0]),
            label=c, zorder=2, edgecolor="white", linewidth=0.3,
        )
    if labels:
        _annotate_highlights(ax, d, "actual", "predicted")
    ax.set_xlabel("actual cycling rate (%)")
    ax.set_ylabel("predicted (cross-validated) %")
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title("out-of-fold prediction" + (f"   CV R2 = {r2:.2f}" if r2 is not None else ""))
    if cmap:
        ax.legend(title="", loc="best", ncol=2)
    return save(fig, "model_pred_vs_actual" + ("_labeled" if labels else ""))


def fig_feature_importance(imp: pd.DataFrame) -> Path:
    """Horizontal bars of permutation importance for the top predictors."""
    set_style()
    d = imp.iloc[::-1]
    fig, ax = plt.subplots(figsize=(6.0, max(3.0, 0.32 * len(d))))
    ax.barh(
        range(len(d)),
        d["importance"],
        xerr=d.get("importance_sd"),
        color=OKABE_ITO[0],
        error_kw={"elinewidth": 0.6, "ecolor": "0.5"},
    )
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["metric"], fontsize=7)
    ax.set_xlabel("permutation importance (drop in R² when shuffled)")
    ax.set_title("network-form predictors of cycling rate")
    ax.grid(axis="y", visible=False)
    return save(fig, "model_feature_importance")


def _short(place_id: object) -> str:
    """City name without the trailing country clause, for a plot label."""
    return str(place_id).split(",")[0]


def _safe(place_id: object) -> str:
    """Filename-safe slug for a place id."""
    return "".join(c if c.isalnum() else "_" for c in str(place_id)).strip("_")


def fig_scenario_shift(
    comparison: pd.DataFrame, place_id: str, dataset_wide: pd.DataFrame, top: int | None = None
) -> Path:
    """Dumbbell of how one place's metrics shift when the grown network is added.

    Each metric is z-scored against the full city dataset (SD units, 0 = dataset
    mean) so shifts are comparable and contextualised; grey dot = current, blue =
    with the grown network. Sorted by absolute shift. Answers 'how has this place
    moved across all the metrics'.
    """
    set_style()
    d = comparison[comparison["place_id"] == place_id]
    recs = []
    for _, r in d.iterrows():
        m = r["metric"]
        if m not in dataset_wide.columns or "baseline" not in r or "scenario" not in r:
            continue
        col = pd.to_numeric(dataset_wide[m], errors="coerce").dropna()
        sd = col.std(ddof=0)
        if len(col) < 3 or not np.isfinite(sd) or sd == 0:
            continue
        mu = col.mean()
        recs.append(
            {"metric": m, "base_z": (r["baseline"] - mu) / sd, "scen_z": (r["scenario"] - mu) / sd}
        )
    z = pd.DataFrame(recs)
    if z.empty:
        raise ValueError(f"no comparable metrics for {place_id}")
    z["shift"] = z["scen_z"] - z["base_z"]
    z = z.reindex(z["shift"].abs().sort_values().index)  # ascending -> biggest at top
    if top:
        z = z.tail(top)
    y = np.arange(len(z))
    fig, ax = plt.subplots(figsize=(6.2, max(2.5, 0.26 * len(z))))
    ax.axvline(0, color="0.4", lw=0.6, zorder=0)  # dataset mean
    ax.hlines(y, z["base_z"], z["scen_z"], color="0.8", lw=1.6, zorder=1)
    ax.scatter(z["base_z"], y, s=26, color=NEUTRAL, label="current", zorder=2)
    ax.scatter(z["scen_z"], y, s=26, color=OKABE_ITO[0], label="+ grown network", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(z["metric"], fontsize=6)
    ax.set_xlabel("standardised value (SD from all-city mean)")
    ax.set_title(f"{_short(place_id)}: network-form shift with grown cycle network")
    ax.grid(axis="y", visible=False)
    ax.legend(title="", loc="lower right")
    return save(fig, f"scenario_shift_{_safe(place_id)}")


def _prediction_dumbbell(
    pred: pd.DataFrame,
    base_col: str,
    scen_col: str,
    *,
    title: str,
    fname: str,
    base_label: str,
    scen_label: str,
) -> Path:
    """Shared dumbbell: baseline -> scenario predicted rate, one row per place."""
    set_style()
    d = pred.dropna(subset=[base_col, scen_col]).sort_values(scen_col)
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(5.6, max(2.2, 0.5 * len(d) + 1)))
    ax.hlines(y, d[base_col], d[scen_col], color="0.8", lw=2.0, zorder=1)
    ax.scatter(d[base_col], y, s=42, color=NEUTRAL, label=base_label, zorder=2)
    ax.scatter(d[scen_col], y, s=42, color=OKABE_ITO[0], label=scen_label, zorder=3)
    if "observed" in d.columns and d["observed"].notna().any():
        ax.scatter(
            d["observed"], y, marker="|", s=180, color="0.15", label="observed now", zorder=4
        )
    ax.set_yticks(y)
    ax.set_yticklabels([_short(p) for p in d["place_id"]])
    ax.set_xlabel("cycling rate (% mode share)")
    ax.set_title(title)
    ax.grid(axis="y", visible=False)
    # legend outside, below the plot (it collided with the dumbbells in the middle)
    ax.legend(
        title="",
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        frameon=False,
        fontsize=8,
    )
    return save(fig, fname)


def fig_scenario_prediction_shift(pred: pd.DataFrame) -> Path:
    """Predicted cycling rate now vs with the grown network, one row per place.

    Grey dot = predicted from the current network, blue = predicted with the grown
    network added; the tick (if present) marks the observed current rate. Directly
    answers 'would these places be predicted to cycle more if the network were built'.
    Predictions here come from a model fit on the full dataset (the borough included);
    see fig_scenario_oof_prediction_shift for the held-out version.
    """
    return _prediction_dumbbell(
        pred,
        "baseline_pred",
        "scenario_pred",
        title="Predicted effect of building the grown cycle network",
        fname="scenario_prediction_shift",
        base_label="predicted now",
        scen_label="predicted with grown network",
    )


def fig_scenario_oof_prediction_shift(pred: pd.DataFrame) -> Path:
    """Out-of-fold predicted shift: each borough is scored by a model trained with
    that borough held out, so neither the current-network nor the grown-network
    estimate is inflated by the model having already seen the place. This is the
    honest read of the predicted change (cf. fig_scenario_prediction_shift, which
    uses a model fit on the full dataset).
    """
    return _prediction_dumbbell(
        pred,
        "baseline_oof",
        "scenario_oof",
        title="Predicted effect of the grown network (out-of-fold)",
        fname="scenario_oof_prediction_shift",
        base_label="predicted now (held out)",
        scen_label="predicted with grown network (held out)",
    )


def fig_scenario_pred_vs_actual_shift(oof: pd.DataFrame, dataset_oof: pd.DataFrame) -> Path:
    """Out-of-fold predicted vs observed cycling rate (same axes as
    model_pred_vs_actual): every city is a grey point, and each grown borough is an
    arrow (style borrowed from fig_scenario_typology_shift) from its current
    out-of-fold prediction up to its grown-network prediction, at its observed rate
    on the x-axis. Open marker = current, filled = with the grown network.

    A borough needs an observed rate to sit on the actual axis; any without one are
    dropped here (make_scenario_report reports which).
    """
    set_style()
    ds = dataset_oof.dropna(subset=["actual", "predicted"])
    d = oof.dropna(subset=["observed", "baseline_oof", "scenario_oof"]).copy()
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    span = [
        *ds["actual"], *ds["predicted"],
        *d["observed"], *d["baseline_oof"], *d["scenario_oof"],
    ]
    lo, hi = (min(span), max(span)) if span else (0.0, 1.0)
    ax.plot(
        [lo, hi], [lo, hi], color="0.6", lw=0.8, ls="--", zorder=1, label="predicted = observed"
    )
    ax.scatter(
        ds["actual"], ds["predicted"], s=18, color="0.8", zorder=2,
        label="all cities (out-of-fold)",
    )
    for _, r in d.iterrows():
        x, y0, y1 = float(r["observed"]), float(r["baseline_oof"]), float(r["scenario_oof"])
        ax.annotate(
            "", xy=(x, y1), xytext=(x, y0),
            arrowprops={"arrowstyle": "->", "color": OKABE_ITO[3], "lw": 1.4}, zorder=3,
        )
        ax.scatter([x], [y0], s=44, facecolor="white", edgecolor=OKABE_ITO[0], zorder=4)
        ax.scatter([x], [y1], s=44, color=OKABE_ITO[0], zorder=4)
    # labels de-cluttered into a vertical stack to the right (the boroughs cluster
    # tightly, so in-place labels overlapped); a thin leader ties each to its marker
    ds_lab = d.sort_values("scenario_oof", ascending=False).reset_index(drop=True)
    if len(ds_lab):
        label_x = float(d["observed"].max()) + (hi - lo) * 0.06
        ytop = float(ds_lab["scenario_oof"].max())
        ybot = float(ds_lab["scenario_oof"].min())
        gap = max((hi - lo) * 0.055, (ytop - ybot) / max(1, len(ds_lab) - 1))
        for i, r in ds_lab.iterrows():
            ax.annotate(
                _short(r["place_id"]),
                xy=(float(r["observed"]), float(r["scenario_oof"])),
                xytext=(label_x, ytop - i * gap),
                fontsize=7, color="0.25", va="center", ha="left",
                arrowprops={"arrowstyle": "-", "color": "0.6", "lw": 0.5},
            )
    ax.set_xlabel("observed cycling rate (%)")
    ax.set_ylabel("predicted (out-of-fold) %")
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title("Grown-network predicted shift vs observed rate")
    ax.legend(title="", loc="lower right", fontsize=7)
    return save(fig, "scenario_pred_vs_actual_shift")


def fig_scenario_typology_shift(proj: dict, place_ids: list[str]) -> Path:
    """Movement of each place in form-space (PCA) when the grown network is added.

    Dataset cities are grey context; each place is an arrow from its current
    position (open) to its grown-network position (filled), labelled by name.
    """
    set_style()
    ev = proj["explained_variance"]
    ds, base, scen = proj["dataset"], proj["base"], proj["scen"]
    fig, ax = plt.subplots(figsize=(5.8, 5.0))
    ax.scatter(ds[:, 0], ds[:, 1], s=16, color="0.8", zorder=1, label="all cities")
    for i, pid in enumerate(place_ids):
        x0, y0 = base[i, 0], base[i, 1]
        x1, y1 = scen[i, 0], scen[i, 1]
        ax.annotate(
            "", xy=(x1, y1), xytext=(x0, y0),
            arrowprops={"arrowstyle": "->", "color": OKABE_ITO[3], "lw": 1.2}, zorder=2,
        )
        ax.scatter([x0], [y0], s=36, facecolor="white", edgecolor=OKABE_ITO[0], zorder=3)
        ax.scatter([x1], [y1], s=36, color=OKABE_ITO[0], zorder=3)
        ax.annotate(
            _short(pid), (x1, y1), fontsize=7, xytext=(3, 3),
            textcoords="offset points", color="0.25",
        )
    ax.set_xlabel(f"PC1 ({ev[0]:.0%} var)")
    ax.set_ylabel(f"PC2 ({ev[1]:.0%} var)" if len(ev) > 1 else "PC2")
    ax.set_title("Form-space movement with the grown cycle network")
    ax.legend(title="", loc="best")
    return save(fig, "scenario_typology_shift")


def fig_metric_correlation_heatmap(wide: pd.DataFrame, metrics: list[str] | None = None) -> Path:
    """Metric x metric Spearman correlation heatmap (shows redundancy among metrics).

    Defaults to every analysed metric column (redundant/bookkeeping excluded).
    """
    from cycleform.describe import _metric_cols

    set_style()
    cols = [
        m for m in (metrics if metrics is not None else _metric_cols(wide)) if m in wide.columns
    ]
    corr = wide[cols].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(0.28 * len(cols) + 2, 0.28 * len(cols) + 2))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=90, fontsize=5)
    ax.set_yticks(range(len(cols)))
    ax.set_yticklabels(cols, fontsize=5)
    fig.colorbar(im, ax=ax, shrink=0.6, label="Spearman rho")
    ax.set_title(f"metric-metric correlation ({len(cols)} metrics)")
    return save(fig, "metric_correlation_heatmap")
