"""Compute metrics for every place we have a cycling rate for (~900).

Resumable: places already computed under the current metric_version are skipped,
so re-running continues where a previous run stopped. Safe to Ctrl-C and restart.
Mega-cities above settings.max_road_edges are skipped and logged.

Run from the package root with the neatnetenv interpreter:
    python run_all.py            # all outcome places
    python run_all.py --uk       # only UK places (faster subset)
    python run_all.py --shard 0/2   # split across two machines (see --shard)
Progress is logged to results/run_all.log and printed.

Splitting across machines: run `--shard 0/2` on one and `--shard 1/2` on another
(a different IP = a separate Overpass rate-limit budget). The shards are disjoint,
so with a shared results/ folder (e.g. OneDrive) the two halves land in
results/places/ without collision. In shard mode the combined + analysis tables
are NOT rebuilt (so the machines don't fight over those files); rebuild them once
every shard has synced -- `report.refresh()`, or notebook 03 with refresh_first.
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


def _parse_shard(text: str) -> tuple[int, int]:
    """Parse an "i/n" shard spec into (i, n) with 0 <= i < n."""
    try:
        i_str, n_str = text.split("/")
        i, n = int(i_str), int(n_str)
    except ValueError as exc:
        raise SystemExit(f"--shard must look like i/n (e.g. 0/2), got {text!r}") from exc
    if n < 1 or not (0 <= i < n):
        raise SystemExit(f"--shard i/n needs n>=1 and 0<=i<n, got {text!r}")
    return i, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uk", action="store_true", help="only UK places")
    ap.add_argument("--force", action="store_true", help="recompute even if cached")
    ap.add_argument(
        "--shard",
        metavar="i/n",
        help="run only every n-th place starting at i (0-based) -- e.g. 0/2 on one "
        "machine and 1/2 on another to split the work. Disjoint shards; the "
        "combined/analysis tables are NOT rebuilt in shard mode (rebuild once all "
        "shards have synced).",
    )
    args = ap.parse_args()
    shard = _parse_shard(args.shard) if args.shard else None

    settings.results.mkdir(parents=True, exist_ok=True)
    # a shard writes its own log so parallel machines don't clobber run_all.log
    log_name = f"run_all_shard{shard[0]}of{shard[1]}.log" if shard else "run_all.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.FileHandler(settings.results / log_name), logging.StreamHandler()],
    )
    for noisy in ("osmnx", "urllib3", "fiona", "pyogrio", "matplotlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    specs = all_outcome_specs()
    if args.uk:
        specs = [s for s in specs if s.country == "UK"]
    if shard:
        i, n = shard
        specs = specs[i::n]  # stride partition: disjoint across machines, same order
        logging.info("shard %d/%d -> %d places", i, n, len(specs))
    logging.info("running %d places (metric_version %s)", len(specs), settings.metric_version)

    # In shard mode skip the shared combined/analysis writes so parallel machines
    # don't fight over those files (they're regenerable once every shard has synced).
    status = run_places(specs, combine=shard is None, force=args.force)
    counts = status["status"].value_counts().to_dict()
    logging.info("DONE: %s", counts)
    failed = status[status["status"] == "failed"]
    if len(failed):
        logging.info("failed places: %s", failed["place_id"].tolist())

    if shard is None:
        _, report = build_analysis_table(save=True)
        logging.info(
            "analysis table: %d matched -> %d rows",
            report["matched_places"],
            report["analysis_rows"],
        )
    else:
        logging.info(
            "shard done; per-place CSVs written. Once every shard has synced, "
            "rebuild the tables: report.refresh() (or notebook 03 with refresh_first=True)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
