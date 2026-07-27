"""Predictive model: can network form predict a city's cycling rate? (Phase 5-lite)

A cross-validated *predictive* screen for the thesis chapter -- "is cycling rate
predictable from network form, and which metrics carry the signal?". Deliberately
simple and dependency-light (scikit-learn): a regularised linear model
(ElasticNet, which copes with the many collinear metrics) and a random forest
(captures non-linearity, gives permutation importances). Performance is honest
out-of-sample (k-fold CV), never in-sample R^2.

Three feature sets are compared so the chapter can say how much network form adds
*beyond national context* (the dominant confounder):
  - form     : the network metrics only
  - country  : national context only (a fixed effect per country)
  - form+country

This is prediction, not causal inference. The fuller confounder-controlled model
(topography, climate, socio-economics; a proportion likelihood) is future work.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNetCV
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from cycleform.describe import _metric_cols

SEED = 42
_L1_GRID = [0.1, 0.5, 0.7, 0.9, 0.95, 0.99, 1.0]


@dataclass
class ModelData:
    X: pd.DataFrame  # metric columns + `country`
    y: pd.Series  # cycling rate (%)
    features: list[str]  # metric feature names
    place_ids: list[str]


def build_model_data(table: pd.DataFrame) -> ModelData:
    """One row per place: network metrics + country + cycling rate.

    Keeps the highest-priority outcome source per place (outcomes.SOURCE_PRIORITY,
    ModalShare-first). Drops places without an outcome; metric NaNs are imputed
    inside the CV pipeline (not here).
    """
    from cycleform.outcomes import prefer_outcome

    d = prefer_outcome(table.dropna(subset=["value"]).copy())
    feats = _metric_cols(d)
    X = d[feats].copy()
    X["country"] = d["country"].fillna("NA").to_numpy()
    return ModelData(
        X=X, y=d["value"].astype(float), features=feats, place_ids=d["place_id"].tolist()
    )


def _pipeline(model, features: list[str], use_metrics: bool, use_country: bool) -> Pipeline:
    steps = []
    if use_metrics:
        steps.append(
            (
                "metrics",
                Pipeline(
                    [("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
                ),
                features,
            )
        )
    if use_country:
        steps.append(("country", OneHotEncoder(handle_unknown="ignore"), ["country"]))
    return Pipeline([("prep", ColumnTransformer(steps)), ("model", model)])


def _models() -> dict:
    return {
        "elasticnet": ElasticNetCV(l1_ratio=_L1_GRID, cv=5, max_iter=20000, random_state=SEED),
        "random_forest": RandomForestRegressor(n_estimators=400, random_state=SEED, n_jobs=-1),
    }


def evaluate(table: pd.DataFrame, folds: int = 5) -> pd.DataFrame:
    """Cross-validated R^2 and RMSE for each (feature set x model). Honest out-of-sample.

    Returns a tidy table so the chapter can report: does network form predict
    cycling rate, and does it add beyond national context?
    """
    data = build_model_data(table)
    cv = KFold(n_splits=folds, shuffle=True, random_state=SEED)
    scoring = {"r2": "r2", "rmse": "neg_root_mean_squared_error"}
    rows = []
    for set_name, (use_m, use_c) in _FEATURE_SETS.items():
        for model_name, model in _models().items():
            pipe = _pipeline(model, data.features, use_metrics=use_m, use_country=use_c)
            res = cross_validate(pipe, data.X, data.y, cv=cv, scoring=scoring)
            rows.append(
                {
                    "feature_set": set_name,
                    "model": model_name,
                    "cv_r2": res["test_r2"].mean(),
                    "cv_r2_sd": res["test_r2"].std(),
                    "cv_rmse": -res["test_rmse"].mean(),
                    "n": len(data.y),
                }
            )
    return pd.DataFrame(rows).round(3)


def feature_importance(table: pd.DataFrame, top: int = 20) -> pd.DataFrame:
    """Permutation importance of the network metrics (random forest, form-only).

    Permutation importance is model-agnostic and robust to the metric collinearity
    (unlike raw impurity importance). Ranked, most important first.
    """
    data = build_model_data(table)
    pipe = _pipeline(_models()["random_forest"], data.features, use_metrics=True, use_country=False)
    pipe.fit(data.X, data.y)
    # permutation_importance defaults to joblib's loky (process) backend, which
    # crashes in a Jupyter kernel on Windows (OSError [Errno 22] from the loky
    # resource tracker on worker spawn). Force the THREADING backend instead: its
    # inner work is RF.predict, which releases the GIL (Cython), so threads still
    # parallelise well and no worker process is ever spawned. (The RF itself uses
    # n_jobs=-1 for the same reason -- tree building is threaded, so it is safe.)
    import joblib

    with joblib.parallel_backend("threading"):
        imp = permutation_importance(
            pipe, data.X, data.y, n_repeats=20, random_state=SEED, n_jobs=-1
        )
    out = pd.DataFrame(
        {
            "metric": list(data.X.columns),  # metrics + the unused country column
            "importance": imp.importances_mean,
            "importance_sd": imp.importances_std,
        }
    )
    out = out[out["metric"].isin(data.features)]  # drop country (not used in form-only model)
    return out.sort_values("importance", ascending=False).head(top).reset_index(drop=True).round(4)


_FEATURE_SETS = {"form": (True, False), "country": (False, True), "form+country": (True, True)}


def fit_predictor(
    table: pd.DataFrame, feature_set: str = "form", model: str = "random_forest"
) -> tuple[Pipeline, list[str]]:
    """Fit the predictor on all labelled places; return (pipeline, feature names).

    Unlike `evaluate`/`predictions` (which are cross-validated for honest scores),
    this returns a model fit on the full dataset, for scoring *new* rows such as a
    grown-network what-if (cycleform.scenarios). Returned features let the caller
    line up the columns of the new rows.
    """
    data = build_model_data(table)
    use_m, use_c = _FEATURE_SETS[feature_set]
    pipe = _pipeline(_models()[model], data.features, use_metrics=use_m, use_country=use_c)
    pipe.fit(data.X, data.y)
    return pipe, data.features


def predict_rate(pipe: Pipeline, wide: pd.DataFrame, features: list[str]) -> np.ndarray:
    """Predict cycling rate for new places from a fitted `fit_predictor` pipeline.

    Aligns `wide` to the model's feature columns (missing -> NaN, imputed inside
    the pipeline) and supplies a `country` column so either feature set works.
    """
    X = pd.DataFrame(index=wide.index)
    for f in features:
        X[f] = wide[f] if f in wide.columns else np.nan
    X["country"] = wide["country"] if "country" in wide.columns else "NA"
    return pipe.predict(X)


def predictions(table: pd.DataFrame, feature_set: str = "form") -> pd.DataFrame:
    """Out-of-fold predictions vs actual cycling rate (for a predicted-vs-actual plot)."""
    from sklearn.model_selection import cross_val_predict

    data = build_model_data(table)
    use_m, use_c = _FEATURE_SETS[feature_set]
    pipe = _pipeline(
        _models()["random_forest"], data.features, use_metrics=use_m, use_country=use_c
    )
    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)
    pred = cross_val_predict(pipe, data.X, data.y, cv=cv)
    return pd.DataFrame(
        {
            "place_id": data.place_ids,
            "country": data.X["country"].to_numpy(),
            "actual": data.y.to_numpy(),
            "predicted": np.asarray(pred),
        }
    )
