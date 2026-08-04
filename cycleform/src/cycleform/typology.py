"""City typology for Q1 -- cluster places by network form (CLAUDE.md §9 Phase 4).

The old repo used self-organising maps; here we use standardise -> PCA ->
k-means, choosing k by silhouette. This is interpretable and dependency-light
(scikit-learn only). SOM (minisom) can be added later if wanted -- new dep, so
ask first (CLAUDE.md §10).

Meaningful only with enough places (p features >> n places otherwise); on the
10-city pilot this is a smoke test. Real typology needs the scale-up run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

# A compact, interpretable feature set for typology (avoids p >> n with the full
# 54 columns). Relational + key form metrics; edit deliberately.
DEFAULT_FEATURES = [
    "bikeable_length_share",
    "low_stress_coverage",
    "modal_directness_gap",
    "entropy_gap_kl",
    "bike_lcc_share_of_road",
    "lcc_length_share_bike",
    "circuity_avg_bike",
    "orientation_entropy_bike",
    "intersection_density_per_km_road",
    "orientation_entropy_road",
    "circuity_avg_road",
]


@dataclass
class Typology:
    features: list[str]
    place_ids: list[str]
    X_scaled: np.ndarray
    scores: np.ndarray  # PCA scores (n x 2 for plotting)
    explained_variance: np.ndarray
    loadings: pd.DataFrame
    labels: np.ndarray
    k: int
    silhouette: float
    profiles: pd.DataFrame = field(default=None)


def prepare_features(
    wide: pd.DataFrame, features: list[str] | None = None
) -> tuple[pd.DataFrame, list[str]]:
    """Select feature columns present in `wide`, drop places with any NaN feature."""
    feats = [f for f in (features or DEFAULT_FEATURES) if f in wide.columns]
    sub = wide.dropna(subset=feats)
    return sub, feats


def _kmeans_by_silhouette(X: np.ndarray, k_range: range = range(2, 7)):
    """Fit k-means for each k in k_range, keep the best by silhouette.

    Returns (k, labels, fitted_model, silhouette). Falls back to a single cluster if
    there are too few rows.
    """
    best = None
    for k in k_range:
        if k >= len(X):
            break
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
        score = silhouette_score(X, km.labels_) if len(set(km.labels_)) > 1 else -1.0
        if best is None or score > best[3]:
            best = (k, km.labels_, km, score)
    if best is None:
        return 1, np.zeros(len(X), int), None, float("nan")
    return best


def project_scenario(
    dataset_wide: pd.DataFrame,
    base_wide: pd.DataFrame,
    scen_wide: pd.DataFrame,
    features: list[str] | None = None,
) -> dict:
    """Fit standardise->PCA(2) + k-means on the full dataset, then project & cluster
    the baseline & scenario.

    Used by the grown-network what-if to show where a place moves in form-space when
    its cycle network grows, and whether that move crosses into a different typology
    cluster. New rows with a missing feature are imputed with the dataset median so a
    place is never dropped for one gap. Returns the dataset scores + ids + cluster
    labels, the baseline/scenario scores + cluster labels, and explained variance.
    """
    sub, feats = prepare_features(dataset_wide, features)
    med = sub[feats].median()
    scaler = StandardScaler().fit(sub[feats].to_numpy())
    Xs = scaler.transform(sub[feats].to_numpy())
    pca = PCA(n_components=min(2, len(feats))).fit(Xs)
    k, ds_labels, km, sil = _kmeans_by_silhouette(Xs)

    def project(w: pd.DataFrame) -> np.ndarray:
        X = w.reindex(columns=feats).fillna(med)
        return pca.transform(scaler.transform(X.to_numpy()))

    def cluster(w: pd.DataFrame) -> np.ndarray:
        if km is None:
            return np.zeros(len(w), int)
        X = w.reindex(columns=feats).fillna(med)
        return km.predict(scaler.transform(X.to_numpy()))

    ids = sub["place_id"].tolist() if "place_id" in sub.columns else sub.index.tolist()
    return {
        "dataset": pca.transform(Xs),
        "dataset_ids": ids,
        "dataset_labels": ds_labels,
        "base": project(base_wide),
        "scen": project(scen_wide),
        "base_labels": cluster(base_wide),
        "scen_labels": cluster(scen_wide),
        "k": k,
        "silhouette": round(float(sil), 3) if sil == sil else float("nan"),
        "explained_variance": pca.explained_variance_ratio_,
        "features": feats,
    }


def build_typology(
    wide: pd.DataFrame, features: list[str] | None = None, k_range: range = range(2, 7)
) -> Typology:
    """Standardise -> PCA(2) -> k-means with k chosen by silhouette."""
    sub, feats = prepare_features(wide, features)
    ids = sub["place_id"].tolist() if "place_id" in sub.columns else sub.index.tolist()
    X = StandardScaler().fit_transform(sub[feats].to_numpy())

    pca = PCA(n_components=min(2, X.shape[1]))
    scores = pca.fit_transform(X)
    loadings = pd.DataFrame(
        pca.components_.T, index=feats, columns=[f"PC{i + 1}" for i in range(pca.n_components_)]
    )

    k, labels, _km, sil = _kmeans_by_silhouette(X, k_range)

    profiles = (
        pd.DataFrame(X, columns=feats, index=ids)
        .assign(cluster=labels)
        .groupby("cluster")
        .mean()
        .round(3)
    )
    return Typology(
        features=feats,
        place_ids=ids,
        X_scaled=X,
        scores=scores,
        explained_variance=pca.explained_variance_ratio_,
        loadings=loadings.round(3),
        labels=labels,
        k=k,
        silhouette=round(float(sil), 3),
        profiles=profiles,
    )
