"""Analysis-table assembly (Phase 3). Needs a combined_metrics.csv to exist."""

from __future__ import annotations

import pytest

from cycleform.assemble import build_analysis_table, load_metrics_wide
from cycleform.config import settings

pytestmark = pytest.mark.skipif(
    not (settings.results / "combined_metrics.csv").exists(),
    reason="no combined_metrics.csv yet (run a batch first)",
)


def test_metrics_have_place_key():
    wide = load_metrics_wide()
    assert "place_key" in wide.columns
    assert wide["place_key"].notna().all()


def test_analysis_table_and_report():
    table, report = build_analysis_table(save=False)
    assert report["matched_places"] <= report["metric_places"]
    assert report["matched_places"] <= report["outcome_places"]
    # source is preserved for fixed-effect modelling
    if len(table):
        assert "source" in table.columns
        assert "value" in table.columns
        assert "bikeable_length_share" in table.columns
    # unmatched places are surfaced, not dropped
    assert isinstance(report["metric_places_without_outcome"], list)
