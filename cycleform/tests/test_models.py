"""Smoke tests for the predictive model on a small synthetic analysis table."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cycleform import models


def _fake_table(n: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    x = rng.normal(size=n)
    return pd.DataFrame(
        {
            "place_key": [f"p{i}" for i in range(n)],
            "place_id": [f"Place {i}" for i in range(n)],
            "country": rng.choice(["UK", "DE", "FR"], size=n),
            "source": "oecd_fua",
            "value": 5 + 3 * x + rng.normal(scale=0.5, size=n),  # signal + noise
            "bikeable_length_share": x + rng.normal(scale=0.1, size=n),
            "circuity_avg_bike": -x + rng.normal(scale=0.1, size=n),
            "meshedness_bike": rng.normal(size=n),
        }
    )


def test_build_model_data():
    data = models.build_model_data(_fake_table())
    assert set(data.features) == {"bikeable_length_share", "circuity_avg_bike", "meshedness_bike"}
    assert "country" in data.X.columns
    assert len(data.y) == len(data.place_ids) == 40


def test_evaluate_returns_all_feature_sets():
    perf = models.evaluate(_fake_table(), folds=3)
    assert set(perf["feature_set"]) == {"form", "country", "form+country"}
    assert {"cv_r2", "cv_rmse", "n"} <= set(perf.columns)
    # a strong planted signal should give the form model positive predictive R2
    form_r2 = perf.loc[perf["feature_set"] == "form", "cv_r2"].max()
    assert form_r2 > 0.3


def test_feature_importance_excludes_country():
    imp = models.feature_importance(_fake_table(), top=5)
    assert "country" not in set(imp["metric"])
    assert imp["importance"].notna().all()
