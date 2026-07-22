"""Grown-network what-if for the Tyne & Wear boroughs (cycleform.scenarios).

Merges each borough's Chapter-5 grown cycle network (bikenwgrowth,
current_ltn_scenario) into its real OSM network and re-measures every metric,
then draws the metric-shift, predicted-rate-shift and form-space-movement
figures. Resumable: a borough already run at the current metric_version is
skipped unless --force.

Run from the package root with the neatnetenv interpreter:
    python run_scenarios.py             # run the five boroughs, then make figures
    python run_scenarios.py --force     # recompute even if cached
    python run_scenarios.py --report-only   # just (re)make figures from saved runs

Needs the main cross-city dataset already built (results/combined_metrics.csv +
analysis_table.csv) so the predictor and form-space context exist. Progress is
logged to results/scenarios/run_scenarios.log.
"""

from __future__ import annotations

import argparse
import logging
import sys
import warnings

warnings.filterwarnings("ignore")

from cycleform import report, scenarios  # noqa: E402
from cycleform.config import settings  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="recompute even if cached")
    ap.add_argument("--report-only", action="store_true", help="skip runs, just make figures")
    args = ap.parse_args()

    settings.results_scenarios.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(settings.results_scenarios / "run_scenarios.log"),
            logging.StreamHandler(),
        ],
    )
    for noisy in ("osmnx", "urllib3", "fiona", "pyogrio", "matplotlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if not args.report_only:
        logging.info(
            "running %d boroughs (metric_version %s)",
            len(scenarios.TYNE_AND_WEAR),
            settings.metric_version,
        )
        status = scenarios.run_scenarios(force=args.force)
        logging.info("runs: %s", status["status"].value_counts().to_dict())

    res = report.make_scenario_report()
    logging.info("wrote %d figures; predicted cycling-rate shift:", len(res["figures"]))
    logging.info("  full-fit (borough in training):")
    for _, r in res["predictions"].iterrows():
        logging.info(
            "    %-24s now %.1f%% -> grown %.1f%%  (%+.1f)",
            str(r["place_id"]).split(",")[0],
            r["baseline_pred"],
            r["scenario_pred"],
            r["shift"],
        )
    logging.info("  out-of-fold (borough held out):")
    for _, r in res["predictions_oof"].iterrows():
        logging.info(
            "    %-24s now %.1f%% -> grown %.1f%%  (%+.1f)",
            str(r["place_id"]).split(",")[0],
            r["baseline_oof"],
            r["scenario_oof"],
            r["shift"],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
