"""Outcomes harmonisation tests (Phase 2). Read the real files in external/."""

from __future__ import annotations

from cycleform.outcomes import COLUMNS, build_outcomes, load_max_value, load_oecd_fua, place_key


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


def test_build_outcomes_keeps_sources_separate():
    long = build_outcomes(save=False)
    assert set(long["source"]) == {"legacy_max_value", "oecd_fua"}
    # Newcastle upon Tyne should appear from both sources, not merged
    nut = long[long["place_key"] == "newcastle upon tyne"]
    assert set(nut["source"]) == {"legacy_max_value", "oecd_fua"}


def test_values_are_percentages():
    long = build_outcomes(save=False)
    assert long["value"].dropna().between(0, 100).all()
