"""Descriptive analysis for Q1 -- how bike vs road network form differs, and
where UK cities sit in the distribution (CLAUDE.md §9 Phase 4).

Pure summarisation over the wide metric table; no plotting (see figures.py) and
no modelling. Every function returns a tidy DataFrame.
"""

from __future__ import annotations

import pandas as pd

# Metric columns that exist for both layers, given as base names (no suffix).
PAIRED_BASES = [
    "n_nodes",
    "n_edges",
    "length_km",
    "k_avg",
    "intersection_density_per_km",
    "dead_end_proportion",
    "four_way_proportion",
    "circuity_avg",
    "orientation_entropy",
    "lcc_length_share",
    "components_per_km",
    "self_loop_proportion",
    "betweenness_mean",
    "closeness_mean",
    "clustering_mean",
]


# Bookkeeping / outcome columns that are numeric but are NOT network metrics.
_NON_METRIC = {
    "place_id",
    "country",
    "place_key",
    "is_uk",
    "metric_version",
    "value",
    "year",
    "numerator",
    "denominator",
    "sample_n",
}
# Redundant metrics excluded from analysis (still computed, just not analysed):
# circuity captures directness, so both linearity measures are dropped; and the
# median linearity duplicates the mean. Keeps the metric set non-redundant.
_REDUNDANT = {
    "linearity_mean_road",
    "linearity_mean_bike",
    "linearity_median_road",
    "linearity_median_bike",
}


def _metric_cols(wide: pd.DataFrame) -> list[str]:
    """Numeric network-metric columns (excludes id / outcome / bookkeeping / redundant)."""
    return [
        c
        for c in wide.columns
        if c not in _NON_METRIC and c not in _REDUNDANT and pd.api.types.is_numeric_dtype(wide[c])
    ]


def metric_summary(wide: pd.DataFrame) -> pd.DataFrame:
    """Per-metric distribution summary across places (count, mean, sd, quartiles)."""
    cols = _metric_cols(wide)
    desc = wide[cols].describe(percentiles=[0.25, 0.5, 0.75]).T
    desc["n_missing"] = wide[cols].isna().sum()
    return desc.round(4)


def bike_vs_road(wide: pd.DataFrame) -> pd.DataFrame:
    """Paired bike-vs-road comparison per metric base that exists for both layers.

    Returns mean of each layer, the mean bike-minus-road difference, and the
    share of places where bike exceeds road -- the raw material for "the cycle
    network is more/less X than the roads it sits in".
    """
    rows = []
    for base in PAIRED_BASES:
        rc, bc = f"{base}_road", f"{base}_bike"
        if rc not in wide.columns or bc not in wide.columns:
            continue
        pair = wide[[rc, bc]].dropna()
        if pair.empty:
            continue
        diff = pair[bc] - pair[rc]
        rows.append(
            {
                "metric": base,
                "road_mean": pair[rc].mean(),
                "bike_mean": pair[bc].mean(),
                "bike_minus_road_mean": diff.mean(),
                "bike_gt_road_share": (diff > 0).mean(),
                "n": len(pair),
            }
        )
    return pd.DataFrame(rows).round(4)


def by_country(wide: pd.DataFrame, metrics: list[str] | None = None) -> pd.DataFrame:
    """Mean of each metric by country (place counts in the `n` column)."""
    if "country" not in wide.columns:
        raise KeyError("wide table has no `country` column")
    cols = metrics or _metric_cols(wide)
    g = wide.groupby("country")
    out = g[cols].mean()
    out.insert(0, "n_places", g.size())
    return out.round(4)


def uk_vs_rest(wide: pd.DataFrame, metrics: list[str] | None = None) -> pd.DataFrame:
    """UK vs non-UK means per metric, with the gap -- the thesis's framing question."""
    if "country" not in wide.columns:
        raise KeyError("wide table has no `country` column")
    cols = metrics or _metric_cols(wide)
    is_uk = wide["country"].eq("UK")
    uk, rest = wide[is_uk], wide[~is_uk]
    out = pd.DataFrame(
        {
            "uk_mean": uk[cols].mean(),
            "rest_mean": rest[cols].mean(),
            "uk_minus_rest": uk[cols].mean() - rest[cols].mean(),
            "n_uk": is_uk.sum(),
            "n_rest": (~is_uk).sum(),
        }
    )
    return out.round(4)


def correlate_with_outcome(
    table: pd.DataFrame, outcome: str = "value", min_n: int = 8
) -> pd.DataFrame:
    """Spearman & Pearson correlation (with p-values) of each metric vs cycling rate.

    A Phase 4->5 bridge, not a model: one row per place (highest-priority outcome
    source, ModalShare-first), ranked by absolute Spearman. `significant` flags
    two-sided Spearman p < 0.05. Spearman is primary -- cycling rate is skewed and
    several relationships are monotonic-but-curved -- with Pearson reported
    alongside. Correlation is not causation and ignores the confounders Q2 controls
    for; read it as a signpost.
    """
    from scipy import stats

    from cycleform.outcomes import prefer_outcome

    d = prefer_outcome(table.dropna(subset=[outcome]).copy())
    rows = []
    for c in (col for col in _metric_cols(d) if col != outcome):
        pair = d[[c, outcome]].dropna()
        if len(pair) < min_n or pair[c].nunique() < 3:
            continue
        rho, p_s = stats.spearmanr(pair[c], pair[outcome])
        r, p_p = stats.pearsonr(pair[c], pair[outcome])
        rows.append(
            {
                "metric": c,
                "spearman": rho,
                "spearman_p": p_s,
                "pearson": r,
                "pearson_p": p_p,
                "n": len(pair),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.reindex(out["spearman"].abs().sort_values(ascending=False).index).reset_index(
        drop=True
    )
    out["significant"] = out["spearman_p"] < 0.05
    num = ["spearman", "spearman_p", "pearson", "pearson_p"]
    out[num] = out[num].round(4)
    return out
