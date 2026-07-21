"""Compute metrics for every place we have a cycling rate for (~900).

Resumable: places already computed under the current metric_version are skipped,
so re-running continues where a previous run stopped. Safe to Ctrl-C and restart.
Mega-cities above settings.max_road_edges are skipped and logged.

Run from the package root with the neatnetenv interpreter:
    python run_all.py            # all outcome places
    python run_all.py --uk       # only UK places (faster subset)
Progress is logged to results/run_all.log and printed.
"""

from __future__ import annotations

import argparse
import logging
import sys
import warnings

warnings.filterwarnings("ignore")

from cycleform.assemble import build_analysis_table  # noqa: E402
from cycleform.batch import all_outcome_specs, run_places  # noqa: E402
from cycleform.config import settings  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uk", action="store_true", help="only UK places")
    ap.add_argument("--force", action="store_true", help="recompute even if cached")
    args = ap.parse_args()

    settings.results.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.FileHandler(settings.results / "run_all.log"), logging.StreamHandler()],
    )
    for noisy in ("osmnx", "urllib3", "fiona", "pyogrio", "matplotlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    specs = all_outcome_specs()
    if args.uk:
        specs = [s for s in specs if s.country == "UK"]
    logging.info("running %d places (metric_version %s)", len(specs), settings.metric_version)

    status = run_places(specs, force=args.force)
    counts = status["status"].value_counts().to_dict()
    logging.info("DONE: %s", counts)
    failed = status[status["status"] == "failed"]
    if len(failed):
        logging.info("failed places: %s", failed["place_id"].tolist())

    _, report = build_analysis_table(save=True)
    logging.info(
        "analysis table: %d matched -> %d rows",
        report["matched_places"],
        report["analysis_rows"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
