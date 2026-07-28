"""UK-vs-rest trend comparison: the within-UK relationship should come out weaker
than the within-rest one when the data is built that way."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cycleform import describe


def _synthetic() -> pd.DataFrame:
    """40 'rest' places with a strong metric->cycling link + 20 UK with a flat one."""
    rng = np.random.RandomState(0)
    rows = []
    for i in range(40):
        m = rng.rand()
        rows.append({"place_key": f"r{i}", "place_id": f"R{i}", "source": "modalshare",
                     "country": "DE", "value": 30 * m + rng.rand(), "bikeable_length_share": m})
    for i in range(20):
        m = rng.rand()
        rows.append({"place_key": f"u{i}", "place_id": f"U{i}", "source": "modalshare",
                     "country": "UK", "value": 3 + 0.5 * rng.rand(), "bikeable_length_share": m})
    return pd.DataFrame(rows)


def test_uk_vs_rest_trends_shape_and_weaker_uk():
    t = describe.uk_vs_rest_trends(
        _synthetic(), metrics=["bikeable_length_share"], min_n=5
    )
    assert list(t.columns) == ["metric", "rho_uk", "rho_rest", "diff", "n_uk"]
    row = t.iloc[0]
    assert row["n_uk"] == 20
    assert row["rho_rest"] > row["rho_uk"]  # rest relationship built to be stronger
