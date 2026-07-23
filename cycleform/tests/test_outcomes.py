"""Outcomes harmonisation tests (Phase 2). Read the real files in external/."""

from __future__ import annotations

import pandas as pd

from cycleform.outcomes import (
    COLUMNS,
    build_outcomes,
    load_max_value,
    load_modalshare,
    load_oecd_fua,
    place_key,
    prefer_outcome,
)


def test_place_key_normalisation():
    assert place_key("Newcastle upon Tyne, United Kingdom") == "newcastle upon tyne"
    assert place_key("München") == "munchen"  # de-accented
    assert place_key("  Berlin ") == "berlin"


def test_max_value_loads_with_encoding():
    df = load_max_value()
    assert list(df.columns) == COLUMNS
    assert len(df) > 200
    # cp1252 decoding: Munchen present and de-accented in the key
    assert (df["place_key"] == "munchen").any()
    assert df["value"].notna().all()


def test_oecd_latest_year_per_fua():
    df = load_oecd_fua(latest_only=True)
    assert list(df.columns) == COLUMNS
    # one row per FUA when latest_only
    assert df["place_id"].is_unique or df["notes"].is_unique
    assert (df["measure_type"] == "commute_mode_share").all()
    assert df["value"].between(0, 100).all()


def test_modalshare_loads():
    df = load_modalshare(latest_only=True)
    assert list(df.columns) == COLUMNS
    assert len(df) > 500
    assert (df["source"] == "modalshare").all()
    assert (df["measure_type"] == "commute_mode_share").all()
    assert df["value"].dropna().between(0, 100).all()
    # UK cities carry the "UK" code (same scheme as the OECD extract, not "GB")
    assert (df.loc[df["place_key"] == "cambridge", "country"] == "UK").any()


def test_build_outcomes_keeps_sources_separate():
    long = build_outcomes(save=False)
    assert set(long["source"]) == {"modalshare", "oecd_fua", "legacy_max_value"}
    # Newcastle upon Tyne appears from the legacy + OECD sources, kept separate
    nut = long[long["place_key"] == "newcastle upon tyne"]
    assert {"legacy_max_value", "oecd_fua"} <= set(nut["source"])


def test_prefer_outcome_is_modalshare_first():
    df = pd.DataFrame(
        {
            "place_key": ["x", "x", "x", "y"],
            "source": ["legacy_max_value", "modalshare", "oecd_fua", "oecd_fua"],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )
    out = prefer_outcome(df)
    assert len(out) == 2  # one row per place_key
    xrow = out[out["place_key"] == "x"].iloc[0]
    assert xrow["source"] == "modalshare" and xrow["value"] == 2.0  # ModalShare wins


def test_values_are_percentages():
    long = build_outcomes(save=False)
    assert long["value"].dropna().between(0, 100).all()
