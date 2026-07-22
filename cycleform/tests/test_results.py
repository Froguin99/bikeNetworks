"""Persistence layer (cycleform.results).

Pins the legacy-metric-name canonicalisation: a place computed by an older
interpreter (a long-running build started before the gamma/alpha -> connectivity_
ratio/meshedness rename, which keeps the pre-rename code in memory) still emits
the old names. build_combined must fold those into the current columns so the
combined table, analysis table, figures and report never show the old names.
"""

from __future__ import annotations

import pandas as pd

from cycleform import results


def test_canonicalize_metric_names_maps_legacy_prefixes():
    s = pd.Series(
        [
            "gamma_index_bike",
            "gamma_index_road",
            "alpha_index_bike",
            "alpha_index_road",
            "bikeable_length_share",  # not legacy -> unchanged
            "circuity_avg_bike",  # substring 'alpha'/'gamma' absent -> unchanged
        ]
    )
    out = list(results._canonicalize_metric_names(s))
    assert out == [
        "connectivity_ratio_bike",
        "connectivity_ratio_road",
        "meshedness_bike",
        "meshedness_road",
        "bikeable_length_share",
        "circuity_avg_bike",
    ]


def _place_long(place_id: str, country: str, rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "snapshot_date": "2025-01-01",
                "source": "osm",
                "country": country,
                "metric_version": "0.5.0",
                "place_id": place_id,
                "metric": metric,
                "version": "0.1.0",
                "value": value,
                "status": "ok",
                "detail": "",
            }
            for metric, value in rows
        ]
    )


def test_build_combined_folds_legacy_names_into_current_columns(tmp_path, monkeypatch):
    monkeypatch.setattr(results.settings, "edition_root", tmp_path)
    results.settings.results_places.mkdir(parents=True, exist_ok=True)
    # one place written by the OLD interpreter (legacy names)...
    _place_long("Oldtown, UK", "UK", [("gamma_index_bike", 0.6), ("alpha_index_bike", 0.4)]).to_csv(
        results.settings.results_places / "Oldtown, UK.csv", index=False
    )
    # ...one written by current code (already renamed)
    _place_long(
        "Newtown, DE", "DE", [("connectivity_ratio_bike", 0.7), ("meshedness_bike", 0.5)]
    ).to_csv(results.settings.results_places / "Newtown, DE.csv", index=False)

    wide = results.build_combined()

    assert "connectivity_ratio_bike" in wide.columns
    assert "meshedness_bike" in wide.columns
    assert "gamma_index_bike" not in wide.columns
    assert "alpha_index_bike" not in wide.columns
    # both places land in the same canonical columns, no NaN gaps from the rename
    assert wide.loc["Oldtown, UK", "connectivity_ratio_bike"] == 0.6
    assert wide.loc["Newtown, DE", "connectivity_ratio_bike"] == 0.7
    assert wide["meshedness_bike"].notna().all()
