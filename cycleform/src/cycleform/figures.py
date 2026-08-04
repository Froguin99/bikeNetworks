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
# A clear red for annotation lines (elbow / peak markers) -- distinct from the
# Okabe-Ito vermillion #D55E00 used for the 4th series, so they never clash.
ACCENT_RED = "#D7191C"

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


def fig_metric_ranked(
    wide: pd.DataFrame, metric: str, label: str | None = None, max_places: int = 40
) -> Path:
    """Ranked dot plot of one metric across places, coloured by country.

    Answers 'where does each city sit in the distribution' -- the Q1 framing. With
    more than `max_places` places the full ranking is unreadable (and overflows
    matplotlib's 65,536-px height limit), so it shows the lowest and highest
    `max_places // 2` with a break between them.
    """
    set_style()
    d = wide.dropna(subset=[metric]).sort_values(metric)
    n_total = len(d)
    truncated = n_total > max_places
    if truncated:
        h = max_places // 2
        d = pd.concat([d.head(h), d.tail(h)])
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
    if truncated:
        h = max_places // 2
        ax.axhline(h - 0.5, color="0.7", ls=":", lw=0.8)  # break between bottom & top
        ax.set_title(f"lowest {h} + highest {h} of {n_total} places", fontsize=8)
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
    labels: bool = False,
) -> Path:
    """Scatter of a metric against cycling rate (the Q2 preview).

    One point per place (highest-priority outcome source, ModalShare-first),
    coloured by country, with a Spearman correlation in the title. `labels=False`
    gives a clean points-only figure; `labels=True` annotates the fixed
    HIGHLIGHT_PLACES exemplars and is saved with a `_labeled` suffix.
    """
    from cycleform.outcomes import prefer_outcome

    set_style()
    d = prefer_outcome(table.dropna(subset=[metric, "value"]).copy())
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
    # The fit line is drawn with a label so it lands in the legend, directly under
    # the country colour dots -- a stable spot that dense points / a shifting
    # legend never overwrite (loc="best" keeps the whole box clear of the data).
    _add_trend(ax, d[metric].to_numpy(), d["value"].to_numpy())
    rho, p = _spearman(d[metric], d["value"])
    ax.set_xlabel(label or metric)
    ax.set_ylabel("cycling rate (% mode share)")
    ax.set_title(f"n={len(d)}   Spearman rho={rho:.2f}, p={_pfmt(p)}")
    ax.legend(title="", loc="best", ncol=2 if cmap else 1, fontsize=7)
    return save(fig, f"outcome_vs_{metric}" + ("_labeled" if labels else ""))


def _spearman(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    from scipy import stats

    rho, p = stats.spearmanr(x, y)
    return float(rho), float(p)


def _pfmt(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def _fit_trend(x: np.ndarray, y: np.ndarray):
    """Best-fitting monotone guide from a FIXED candidate set, chosen by AICc.

    The line is only a guide to the eye -- the reported inference is the Spearman
    rho (monotone, form-free). To let the shape vary between panels without
    cherry-picking, the SAME three monotone forms are fitted to every panel and
    the winner is picked by one objective criterion (AICc); the procedure is
    uniform even though the chosen form differs. See cycleform ASSUMPTIONS.md.

    Candidates (both monotone, both fitted on the RAW cycling-rate scale so their
    AICc is directly comparable -- the exponential via non-linear least squares,
    NOT by regressing log y, which would put its residuals on a different scale):
      - linear:      y = a + b*x
      - exponential: y = a*exp(b*x)       (multiplicative; stays >= 0)
    Both have the same parameter count, so AICc, AIC and R^2 rank them identically
    here; AICc is used so the method stays valid if a higher-order form is ever
    added. Returns (name, predict_fn, r2) or None.
    """
    from scipy.optimize import curve_fit

    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = x.size
    if n < 5:
        return None
    ss_tot = float(np.sum((y - y.mean()) ** 2)) or 1e-12
    cands: dict[str, tuple] = {}
    b, a = np.polyfit(x, y, 1)
    cands["linear"] = (lambda xx, a=a, b=b: a + b * xx, 2)
    try:
        popt, _ = curve_fit(
            lambda xx, a, b: a * np.exp(b * xx), x, y,
            p0=[max(float(y.mean()), 1e-3), 0.0], maxfev=10000,
        )
        cands["exponential"] = (lambda xx, a=popt[0], b=popt[1]: a * np.exp(b * xx), 2)
    except Exception:  # curve_fit may not converge; just drop this candidate
        pass
    best = None
    for name, (fn, k) in cands.items():
        resid = y - fn(x)
        rss = float(np.sum(resid ** 2))
        if not np.isfinite(rss):
            continue
        rss = max(rss, 1e-12)
        kk = k + 1  # +1 for the residual variance
        aic = n * np.log(rss / n) + 2 * kk
        aicc = aic + (2 * kk * (kk + 1)) / max(n - kk - 1, 1)
        r2 = 1.0 - rss / ss_tot
        if best is None or aicc < best[0]:
            best = (aicc, name, fn, r2)
    if best is None:
        return None
    _, name, fn, r2 = best
    return name, fn, r2


def _add_trend(ax, x: np.ndarray, y: np.ndarray) -> str | None:
    """Draw the best-fitting monotone guide curve and floor the axis at 0.

    Drawn ON TOP of the points (points are often dense enough to hide a line
    behind them), dashed and semi-transparent so it reads as a guide rather than
    a fitted model, and clipped at 0 -- cycling rate can never be negative.
    Returns a short 'exponential fit (R²=0.34)' label for the caller to place in
    the legend or title (NOT floating on the axes, where dense points or a
    shifting legend would overwrite it); None if too few points to fit.
    """
    fit = _fit_trend(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    if fit is None:
        return None
    name, fn, r2 = fit
    ok = np.isfinite(x) & np.isfinite(y)
    xs = np.linspace(float(np.min(x[ok])), float(np.max(x[ok])), 100)
    ys = np.clip(fn(xs), 0.0, None)
    label = f"{name} fit (R²={r2:.2f})"
    ax.plot(xs, ys, color="0.15", lw=1.4, ls=(0, (5, 2)), alpha=0.85, zorder=6, label=label)
    ax.set_ylim(bottom=0)
    return label


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


def fig_top_correlates(table: pd.DataFrame, corr: pd.DataFrame, n: int = 9) -> Path:
    """Small-multiples grid of the top-n significant metrics vs cycling rate.

    Each panel: scatter + trend line + Spearman rho and p. Points are one per
    place (highest-priority outcome source, ModalShare-first); panels share the
    cycling-rate y-axis.
    """
    from cycleform.outcomes import prefer_outcome

    set_style()
    sig = corr[corr.get("significant", True)].head(n)
    if sig.empty:
        sig = corr.head(n)
    d = prefer_outcome(table.dropna(subset=["value"]).copy())
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
        lbl = _add_trend(ax, sub[m].to_numpy(), sub["value"].to_numpy())
        sub_t = f"\n{lbl}" if lbl else ""
        ax.set_title(
            f"{m}\nrho={row['spearman']:.2f}, p={_pfmt(row['spearman_p'])}{sub_t}", fontsize=7.5
        )
        ax.tick_params(labelsize=6)
        if i % ncol == 0:
            ax.set_ylabel("cycling %", fontsize=7)
    fig.tight_layout()
    return save(fig, "top_correlates_grid")


# Metric taxonomy for the grouped small-multiple grids (fig_metric_group_grid).
# Groups follow the thesis subsections so each figure backs one paragraph. Entries
# are BASE names -- the _bike / _road layer variants present in the table are added
# automatically -- or exact single-layer metric names. Order here sets panel order.
METRIC_GROUPS: dict[str, list[str]] = {
    "size": [
        "length_km", "n_edges", "n_nodes", "intersection_count", "edge_length_avg_m",
        "street_density_km2", "cycle_network_density_km2",
        "intersection_density_km2", "intersection_density_per_km",
    ],
    "connectivity_edge": ["connectivity_ratio", "meshedness", "k_avg"],
    "connectivity_node": [
        "dead_end_proportion", "three_way_proportion", "four_way_proportion",
        "self_loop_proportion",
    ],
    "fragmentation": [
        "n_components", "components_per_km", "lcc_length_km",
        "lcc_length_share", "component_size_gini",
    ],
    "shape_orientation": ["circuity_avg", "orientation_entropy", "orientation_order"],
    "centrality": [
        "betweenness_mean", "betweenness_median", "closeness_mean",
        "closeness_median", "clustering_mean",
    ],
    "lts_coverage": ["low_stress_coverage", "lts1_coverage", "lts2_coverage"],
    "relational": [
        "bikeable_length_share", "bike_offroad_share", "bike_lcc_share_of_road",
        "intersection_ratio_bike_road", "entropy_gap_kl", "modal_directness_gap",
        "low_stress_route_fraction", "mean_route_lts",
    ],
}
GROUP_LABELS: dict[str, str] = {
    "size": "Size",
    "connectivity_edge": "Connectivity (edge-based)",
    "connectivity_node": "Connectivity (node-based)",
    "fragmentation": "Fragmentation",
    "shape_orientation": "Shape and orientation",
    "centrality": "Centrality",
    "lts_coverage": "LTS coverage",
    "relational": "Relational comparisons",
}


def _resolve_group_metrics(base: str, columns) -> list[str]:
    """A base name -> the actual metric columns present (exact, or _bike/_road)."""
    if base in columns:
        return [base]
    return [base + s for s in ("_bike", "_road") if base + s in columns]


def fig_metric_group_grid(
    table: pd.DataFrame, group: str, corr: pd.DataFrame | None = None
) -> Path | None:
    """Compact small-multiple grid of one metric family vs cycling rate.

    A deliberately small-panelled companion to the individual scatters, so a paper
    can discuss one metric family (Size, Connectivity, ...) at a time. Every metric
    in the group gets a panel (both bike and road layers where they exist); each has
    the same guide curve as the main scatters (dashed, on top, clipped at 0) and a
    title carrying Spearman rho (if `corr` given) and the fit type + R². Returns the
    saved path, or None if the group has no metrics present.
    """
    from cycleform.outcomes import prefer_outcome

    set_style()
    metrics = [
        m for base in METRIC_GROUPS[group] for m in _resolve_group_metrics(base, table.columns)
    ]
    if not metrics:
        return None
    d = prefer_outcome(table.dropna(subset=["value"]).copy())
    rho = dict(zip(corr["metric"], corr["spearman"])) if corr is not None else {}
    ncol = min(4, len(metrics))
    nrow = int(np.ceil(len(metrics) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(2.5 * ncol, 2.15 * nrow), squeeze=False)
    for ax in axes.flat:
        ax.set_visible(False)
    for i, m in enumerate(metrics):
        ax = axes.flat[i]
        ax.set_visible(True)
        sub = d.dropna(subset=[m])
        ax.scatter(
            sub[m], sub["value"], s=7, color=OKABE_ITO[0], alpha=0.5,
            edgecolor="white", linewidth=0.2, zorder=2,
        )
        lbl = _add_trend(ax, sub[m].to_numpy(), sub["value"].to_numpy())
        bits = []
        if m in rho:
            bits.append(f"ρ={rho[m]:.2f}")
        if lbl:
            bits.append(lbl)
        subtitle = ("\n" + "  ·  ".join(bits)) if bits else ""
        ax.set_title(f"{m}{subtitle}", fontsize=6.5)
        ax.tick_params(labelsize=5.5)
        if i % ncol == 0:
            ax.set_ylabel("cycling %", fontsize=6)
    fig.suptitle(GROUP_LABELS.get(group, group), fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    return save(fig, f"group_{group}")


def fig_metric_group_grids(table: pd.DataFrame, corr: pd.DataFrame | None = None) -> list[Path]:
    """Draw every metric-family grid (see METRIC_GROUPS); returns the saved paths."""
    out = []
    for group in METRIC_GROUPS:
        p = fig_metric_group_grid(table, group, corr=corr)
        if p is not None:
            out.append(p)
    return out


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
    """Movement of each place in form-space (PCA) when the grown network is added,
    over the typology clusters.

    Dataset cities are coloured by typology cluster; each borough is an arrow from
    its current position (open) to its grown-network position (filled). The label
    carries the cluster it belongs to, and `type a->b` when the grown network moves
    it into a different cluster.
    """
    set_style()
    ev = proj["explained_variance"]
    ds, base, scen = proj["dataset"], proj["base"], proj["scen"]
    ds_lab = proj.get("dataset_labels")
    base_lab, scen_lab = proj.get("base_labels"), proj.get("scen_labels")
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    handles = []
    if ds_lab is not None:
        for cl in sorted({int(c) for c in ds_lab}):
            col = OKABE_ITO[cl % len(OKABE_ITO)]
            ax.scatter(ds[ds_lab == cl, 0], ds[ds_lab == cl, 1], s=16, color=col, alpha=0.45, zorder=1)
            handles.append(plt.Line2D([], [], marker="o", ls="", color=col, alpha=0.8, label=f"type {cl}"))
    else:
        ax.scatter(ds[:, 0], ds[:, 1], s=16, color="0.8", zorder=1)
    info = []  # (x1, y1, label) for the stacked de-cluttered labels
    for i, pid in enumerate(place_ids):
        x0, y0, x1, y1 = base[i, 0], base[i, 1], scen[i, 0], scen[i, 1]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops={"arrowstyle": "->", "color": "0.15", "lw": 1.3}, zorder=3)
        ax.scatter([x0], [y0], s=44, facecolor="white", edgecolor="0.15", linewidth=1.2, zorder=4)
        ax.scatter([x1], [y1], s=44, color="0.15", zorder=4)
        lbl = _short(pid)
        if base_lab is not None and scen_lab is not None:
            b, s = int(base_lab[i]), int(scen_lab[i])
            lbl += f"  (type {b}→{s})" if b != s else f"  (type {b})"
        info.append((x1, y1, lbl))
    # boroughs cluster tightly, so stack labels in a vertical column to the right of
    # them with thin leader lines (in-place labels overlapped).
    if info:
        xmin, xmax = float(ds[:, 0].min()), float(ds[:, 0].max())
        ymin, ymax = float(ds[:, 1].min()), float(ds[:, 1].max())
        lab_x = max(x for x, _, _ in info) + (xmax - xmin) * 0.10
        order = sorted(range(len(info)), key=lambda i: info[i][1], reverse=True)
        gap = (ymax - ymin) * 0.09
        ytop = float(np.mean([y for _, y, _ in info])) + gap * (len(info) - 1) / 2
        for rank, i in enumerate(order):
            x1, y1, lbl = info[i]
            ax.annotate(
                lbl, xy=(x1, y1), xytext=(lab_x, ytop - rank * gap),
                fontsize=7, color="0.1", va="center", ha="left",
                arrowprops={"arrowstyle": "-", "color": "0.6", "lw": 0.5},
            )
    handles += [
        plt.Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor="0.15",
                   label="current network"),
        plt.Line2D([], [], marker="o", ls="", color="0.15", label="future network"),
    ]
    ax.set_xlabel(f"PC1 ({ev[0]:.0%} var)")
    ax.set_ylabel(f"PC2 ({ev[1]:.0%} var)" if len(ev) > 1 else "PC2")
    kbit = f" (k={proj.get('k')})" if proj.get("k") else ""
    ax.set_title(f"Form-space movement with the grown cycle network{kbit}")
    ax.legend(handles=handles, title="", loc="best", fontsize=7)
    return save(fig, "scenario_typology_shift")


def fig_scenario_shift_combined(
    comparison: pd.DataFrame, dataset_wide: pd.DataFrame, top: int = 15
) -> Path:
    """Average metric shift across all grown boroughs -- the top `top` by |shift|.

    A compact summary of the per-borough fig_scenario_shift: each metric is z-scored
    per borough against the full city dataset, then averaged over boroughs (grey =
    current, blue = with the grown network). Only the most-shifted metrics are shown
    so it stays readable instead of listing all ~60.
    """
    set_style()
    recs = []
    for _, r in comparison.iterrows():
        m = r["metric"]
        if m not in dataset_wide.columns or pd.isna(r.get("baseline")) or pd.isna(r.get("scenario")):
            continue
        col = pd.to_numeric(dataset_wide[m], errors="coerce").dropna()
        sd = col.std(ddof=0)
        if len(col) < 3 or not np.isfinite(sd) or sd == 0:
            continue
        mu = col.mean()
        recs.append({"metric": m, "base_z": (r["baseline"] - mu) / sd, "scen_z": (r["scenario"] - mu) / sd})
    z = pd.DataFrame(recs)
    if z.empty:
        raise ValueError("no comparable metrics for the combined scenario shift")
    agg = z.groupby("metric")[["base_z", "scen_z"]].mean()
    agg["shift"] = agg["scen_z"] - agg["base_z"]
    agg = agg.reindex(agg["shift"].abs().sort_values().index).tail(top)  # biggest shift at top
    y = np.arange(len(agg))
    fig, ax = plt.subplots(figsize=(6.4, max(2.6, 0.32 * len(agg))))
    ax.axvline(0, color="0.4", lw=0.6, zorder=0)
    ax.hlines(y, agg["base_z"], agg["scen_z"], color="0.8", lw=1.8, zorder=1)
    ax.scatter(agg["base_z"], y, s=30, color=NEUTRAL, label="current", zorder=2)
    ax.scatter(agg["scen_z"], y, s=30, color=OKABE_ITO[0], label="+ grown network", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(agg.index, fontsize=7)
    ax.set_xlabel("standardised value (SD from all-city mean), averaged over LADs")
    n = comparison["place_id"].nunique()
    ax.set_title(f"Average network-form shift with the grown network  ({n} LADs, top {len(agg)} metrics)")
    ax.grid(axis="y", visible=False)
    # legend outside the panel (upper right) so it never sits on a dumbbell
    ax.legend(title="", loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8)
    return save(fig, "scenario_shift_combined")


def fig_growth_curve(curve: pd.DataFrame, y: str = "predicted_rate", ylabel: str | None = None) -> Path:
    """Performance vs distance invested along the grown-network build-out.

    One line per place (predicted cycling rate, or any metric column `y`, against the
    km of new protected cycleway built), plus a bold Tyne & Wear average with the
    diminishing-returns elbow (the best trade-off) marked.
    """
    from cycleform.scenarios import _elbow_index

    set_style()
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for i, pid in enumerate(sorted(curve["place_id"].unique())):
        g = curve[curve["place_id"] == pid].sort_values("invested_km")
        ax.plot(g["invested_km"], g[y], marker="o", ms=3.5, lw=1.0,
                color=OKABE_ITO[i % len(OKABE_ITO)], alpha=0.45, label=_short(pid), zorder=2)
    avg = (
        curve.groupby("stage").agg(invested_km=("invested_km", "mean"), yv=(y, "mean"))
        .reset_index().sort_values("invested_km")
    )
    ax.plot(avg["invested_km"], avg["yv"], color="0.1", lw=2.6, marker="s", ms=5,
            label="Tyne & Wear avg", zorder=5)
    km, yv = avg["invested_km"].to_numpy(float), avg["yv"].to_numpy(float)
    ei = _elbow_index(km, yv)
    if ei:
        ax.axvline(km[ei], color=ACCENT_RED, ls="--", lw=1.3, zorder=1,
                   label="Elbow (best trade-off)")
        ax.scatter([km[ei]], [yv[ei]], s=70, facecolor="none", edgecolor=ACCENT_RED,
                   lw=1.6, zorder=6)
    ax.set_xlabel("distance invested (km of new protected cycleway)")
    ax.set_ylabel(ylabel or ("predicted cycling rate (%)" if y == "predicted_rate" else y))
    ax.set_title(
        "Predicted cycling rate vs distance invested" if y == "predicted_rate"
        else f"{y} vs distance invested"
    )
    ax.legend(title="", loc="best", fontsize=7)
    return save(fig, f"growth_curve_{y}")


def fig_growth_marginal(curve: pd.DataFrame, y: str = "predicted_rate") -> Path:
    """Marginal return along the build-out: predicted-rate gain PER KM at each step,
    one line per place + the average, with the logistic inflection (steepest gain)
    marked. The peak of this curve is where each extra km buys the most.
    """
    from cycleform.scenarios import growth_curve_marginals

    set_style()
    marg = growth_curve_marginals(curve, y=y)
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for i, pid in enumerate(sorted(marg["place_id"].unique())):
        g = marg[marg["place_id"] == pid].sort_values("invested_km")
        ax.plot(g["invested_km"], g["gain_per_km"], marker="o", ms=3.5, lw=1.0,
                color=OKABE_ITO[i % len(OKABE_ITO)], alpha=0.45, label=_short(pid), zorder=2)
    avg = (
        marg.groupby("stage").agg(invested_km=("invested_km", "mean"), gpk=("gain_per_km", "mean"))
        .reset_index().sort_values("invested_km")
    )
    ax.plot(avg["invested_km"], avg["gpk"], color="0.1", lw=2.4, marker="s", ms=5,
            label="Tyne & Wear avg", zorder=5)
    # empirical peak of the average marginal (data-driven 'best gain per km')
    if len(avg):
        pk = avg.iloc[int(avg["gpk"].to_numpy().argmax())]
        ax.axvline(pk["invested_km"], color=ACCENT_RED, ls="--", lw=1.3, zorder=1,
                   label="Peak marginal efficiency")
    ax.axhline(0, color="0.6", lw=0.5, zorder=0)
    ax.set_xlabel("distance invested (km of new protected cycleway)")
    ax.set_ylabel("marginal gain (pp of predicted rate, per km)")
    ax.set_title("Marginal return: predicted-rate gain per km built")
    ax.legend(title="", loc="best", fontsize=7)
    return save(fig, "growth_marginal")


# Key metrics for the UK-vs-rest contrasts (provision, connectivity, directness).
UK_KEY_METRICS = [
    "bikeable_length_share", "intersection_ratio_bike_road", "bike_lcc_share_of_road",
    "cycle_network_density_km2", "circuity_avg_bike", "low_stress_coverage",
    "components_per_km_bike", "mean_route_lts", "meshedness_bike",
    "modal_directness_gap", "orientation_order_bike", "street_density_km2",
]


def _one_per_place(table: pd.DataFrame) -> pd.DataFrame:
    """Highest-priority outcome row per place (ModalShare-first), value present."""
    from cycleform.outcomes import prefer_outcome

    return prefer_outcome(table.dropna(subset=["value"]).copy())


def fig_cycling_rate_distribution(table: pd.DataFrame) -> Path:
    """Distribution of cycling rate across all places (a single violin).

    One horizontal axis: the violin is the density; thin reference lines mark the
    median and mean. Plain title -- describe the skew in the caption.
    """
    set_style()
    d = _one_per_place(table)
    v = d["value"].astype(float).to_numpy()
    med, mean = float(np.median(v)), float(v.mean())
    fig, ax = plt.subplots(figsize=(6.2, 2.9))
    parts = ax.violinplot(v, positions=[0], vert=False, showextrema=False, widths=1.4)
    for body in parts["bodies"]:
        body.set_facecolor(OKABE_ITO[0])
        body.set_alpha(0.30)
        body.set_edgecolor("none")
    ax.axvline(med, color=OKABE_ITO[3], lw=1.4, zorder=5, label=f"median {med:.1f}%")
    ax.axvline(mean, color="0.2", lw=1.2, ls="--", zorder=5, label=f"mean {mean:.1f}%")
    ax.set_yticks([])
    ax.set_ylim(-1.0, 1.0)
    ax.set_xlabel("cycling rate (% commute mode share)")
    ax.set_xlim(left=0)
    ax.set_title(f"Cycling rate across {len(v)} places")
    ax.grid(axis="y", visible=False)
    ax.legend(title="", loc="upper right")
    return save(fig, "cycling_rate_distribution")


def fig_cycling_rate_by_country(table: pd.DataFrame, min_places: int = 1) -> Path:
    """Two panels sharing a country axis: mean cycling rate and the number of places
    per country. Sorted by mean rate; the UK is highlighted.

    Two panels rather than one dual-axis chart (a dataviz non-negotiable): rate and
    count are different scales, so each gets its own axis. Every country is shown by
    default (min_places=1); the n-places panel makes small samples visible so the
    reader can weight a 1-city 'mean' accordingly. Raise min_places to hide them.
    """
    set_style()
    d = _one_per_place(table)
    g = d.groupby("country")["value"]
    stat = pd.DataFrame({"n": g.size(), "mean": g.mean()}).dropna(subset=["mean"])
    dropped = int((stat["n"] < min_places).sum())
    stat = stat[stat["n"] >= min_places].sort_values("mean")
    y = np.arange(len(stat))
    is_uk = stat.index == "UK"
    rate_c = [OKABE_ITO[3] if u else OKABE_ITO[0] for u in is_uk]
    n_c = [OKABE_ITO[3] if u else NEUTRAL for u in is_uk]
    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(7.6, max(3.0, 0.24 * len(stat) + 0.8)),
        sharey=True, gridspec_kw={"width_ratios": [3, 1]},
    )
    axL.barh(y, stat["mean"], color=rate_c, zorder=2)
    axL.set_yticks(y)
    axL.set_yticklabels(stat.index)
    axL.set_xlabel("mean cycling rate (%)")
    axL.grid(axis="y", visible=False)
    for tick, u in zip(axL.get_yticklabels(), is_uk):
        if u:
            tick.set_color(OKABE_ITO[3])
            tick.set_fontweight("bold")
    axR.barh(y, stat["n"], color=n_c, zorder=2)
    axR.set_xlabel("n places")
    axR.grid(axis="y", visible=False)
    note = f"  ({dropped} countries with < {min_places} places omitted)" if dropped else ""
    fig.suptitle(f"Mean cycling rate and number of places, by country{note}", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    return save(fig, "cycling_rate_by_country")


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Pooled-SD standardised mean difference (a - b)."""
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return float((a.mean() - b.mean()) / sp) if sp else np.nan


def fig_uk_vs_rest_metrics(table: pd.DataFrame, metrics: list[str] | None = None) -> Path:
    """How UK cycle-network form differs from the rest, per metric, as a standardised
    difference (Cohen's d, UK minus rest). Blue = UK higher, orange = UK lower; a
    solid edge marks a significant Mann-Whitney difference (p < 0.05).
    """
    from scipy import stats

    set_style()
    d = _one_per_place(table)
    uk, rest = d[d["country"].eq("UK")], d[~d["country"].eq("UK")]
    rows = []
    for m in metrics or UK_KEY_METRICS:
        if m not in d.columns:
            continue
        a, b = uk[m].dropna().to_numpy(), rest[m].dropna().to_numpy()
        if len(a) < 3 or len(b) < 3:
            continue
        p = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
        rows.append({"metric": m, "d": _cohens_d(a, b), "sig": p < 0.05})
    s = pd.DataFrame(rows).dropna(subset=["d"]).sort_values("d")
    colors = [OKABE_ITO[0] if v >= 0 else OKABE_ITO[3] for v in s["d"]]
    edges = ["black" if x else "none" for x in s["sig"]]
    fig, ax = plt.subplots(figsize=(6.0, max(2.6, 0.34 * len(s))))
    ax.barh(range(len(s)), s["d"], color=colors, edgecolor=edges, linewidth=0.9, zorder=2)
    ax.axvline(0, color="0.4", lw=0.6)
    ax.set_yticks(range(len(s)))
    ax.set_yticklabels(s["metric"], fontsize=7)
    ax.set_xlabel("UK − rest  (SD units, Cohen's d)")
    ax.set_title("UK − rest difference in cycle-network form  (solid edge: p<0.05)")
    ax.grid(axis="y", visible=False)
    return save(fig, "uk_vs_rest_metrics")


def fig_uk_vs_rest_relationship(
    table: pd.DataFrame, metric: str = "bikeable_length_share", label: str | None = None
) -> Path:
    """The metric-vs-cycling relationship, UK vs the rest, with a trend line for each.

    The headline 'different trends' figure: rest cities are grey with their fit, UK
    cities are highlighted with theirs. The UK slope is flatter and sits lower --
    form predicts UK cycling more weakly, and the UK cycles below what its provision
    predicts. Spearman rho for each group is in the legend.
    """
    from scipy import stats

    set_style()
    d = _one_per_place(table).dropna(subset=[metric, "value"])
    uk, rest = d[d["country"].eq("UK")], d[~d["country"].eq("UK")]
    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    ax.scatter(rest[metric], rest["value"], s=16, color=NEUTRAL, alpha=0.55,
               edgecolor="white", linewidth=0.3, zorder=2, label="rest of sample")
    ax.scatter(uk[metric], uk["value"], s=26, color=OKABE_ITO[3],
               edgecolor="white", linewidth=0.4, zorder=3, label="UK")

    def _fit_line(sub, color, name):
        x = sub[metric].to_numpy(dtype=float)
        yv = sub["value"].to_numpy(dtype=float)
        if len(x) < 5:
            return
        b, a = np.polyfit(x, yv, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        rho, _ = stats.spearmanr(x, yv)
        ax.plot(xs, np.clip(a + b * xs, 0, None), color=color, lw=1.8, zorder=4,
                label=f"{name} fit (ρ={rho:.2f}, n={len(x)})")

    _fit_line(rest, "0.35", "rest")
    _fit_line(uk, OKABE_ITO[3], "UK")
    ax.set_xlabel(label or metric)
    ax.set_ylabel("cycling rate (% mode share)")
    ax.set_ylim(bottom=0)
    ax.set_title(f"Cycling rate vs {label or metric}, UK vs rest")
    ax.legend(title="", loc="upper left", fontsize=7.5)
    return save(fig, "uk_vs_rest_relationship")


def fig_implementation_gap_by_country(pred: pd.DataFrame, min_places: int = 5) -> Path:
    """Implementation gap: does a country cycle more or less than its network form
    predicts? Mean out-of-fold residual (observed − predicted, form-only model) per
    country, ±SEM. Blue = cycles above what its form predicts, orange = below; the
    UK bar is outlined and its label bold.

    `pred` is a models.predictions(feature_set="form") frame (place_id, country,
    actual, predicted). Countries with < min_places places are dropped.
    """
    set_style()
    d = pred.dropna(subset=["actual", "predicted", "country"]).copy()
    d["resid"] = d["actual"].astype(float) - d["predicted"].astype(float)
    g = d.groupby("country")["resid"]
    s = pd.DataFrame({"n": g.size(), "mean": g.mean(), "sem": g.sem()})
    s = s[s["n"] >= min_places].sort_values("mean")
    y = np.arange(len(s))
    is_uk = s.index == "UK"
    colors = [OKABE_ITO[0] if v >= 0 else OKABE_ITO[3] for v in s["mean"]]
    edges = ["black" if u else "none" for u in is_uk]
    fig, ax = plt.subplots(figsize=(6.0, max(2.6, 0.30 * len(s))))
    ax.barh(y, s["mean"], xerr=s["sem"], color=colors, edgecolor=edges, linewidth=1.2,
            error_kw={"elinewidth": 0.6, "ecolor": "0.5"}, zorder=2)
    ax.axvline(0, color="0.4", lw=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(s.index)
    for tick, u in zip(ax.get_yticklabels(), is_uk):
        if u:
            tick.set_color(OKABE_ITO[3])
            tick.set_fontweight("bold")
    ax.set_xlabel("observed − predicted cycling rate (percentage points)")
    ax.set_title("Observed − predicted cycling rate, by country")
    ax.grid(axis="y", visible=False)
    return save(fig, "implementation_gap_by_country")


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
