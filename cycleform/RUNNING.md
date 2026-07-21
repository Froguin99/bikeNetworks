# How to run cycleform

Short guide to running the pipeline. Fuller context is in `README.md`, the metric
definitions in `METRICS.md`, and the modelling/analysis caveats in `ASSUMPTIONS.md`.

## 0. One-time setup

Use the **`neatnetenv`** conda environment (already created). Its Python is:

```
C:\Users\b8008458\AppData\Local\miniforge3\envs\neatnetenv\python.exe
```

If the package isn't installed into it yet:

```powershell
$py = "$env:LOCALAPPDATA\miniforge3\envs\neatnetenv\python.exe"
& $py -m pip install -e . --no-deps --no-build-isolation   # from the cycleform/ folder
```

In notebooks, pick the **neatnetenv** kernel.

## 1. Compute metrics for places

Metrics are computed per place and cached to `results/places/<place>.csv`. A run
**skips places already computed** at the current `metric_version`, so it is
resumable and cheap to re-run.

```powershell
$py = "$env:LOCALAPPDATA\miniforge3\envs\neatnetenv\python.exe"
& $py run_all.py            # every place we have a cycling rate for (~900), UK first
& $py run_all.py --uk       # only UK places (a fast subset)
& $py run_all.py --force    # recompute everything, ignoring the cache
```

- It runs for a long time (hours to ~2 days for all places); just re-run it to
  resume if it stops. Progress is in `results/run_all.log`.
- Failures (geocoding, Overpass timeouts, over-size cities) are logged and the run
  continues. Re-running retries them.
- To compute a custom list instead, in Python:

```python
from cycleform.batch import run_places, PlaceSpec
run_places([PlaceSpec("Bristol, United Kingdom", "Bristol, United Kingdom", "UK")])
```

## 2. Build the analysis tables

`run_all.py` does this at the end, but you can rebuild any time from the per-place
files (e.g. mid-run to include newly-finished places):

```python
from cycleform import report
wide, table = report.refresh()   # rebuilds combined_metrics.csv + analysis_table.csv
```

Outputs in `results/`: `combined_metrics.csv` (one row per place),
`analysis_table.csv` (metrics joined to cycling rate), `outcomes_long.csv`.

## 3. Make figures and tables (any time after step 1)

Fully decoupled from computation — reads the saved CSVs, so you can restyle freely
while a batch keeps running. Also in `notebooks/03-figures.ipynb`.

```python
from cycleform import report
report.make_figures()          # all figures -> results/figures/ (PNG)
report.make_figures(refresh_first=True)   # rebuild tables from per-place files first
report.summary_tables()        # dict of Q1 tables + metric-vs-cycling correlations
```

Each metric-vs-cycling scatter, the typology, and the prediction plot are written
in two variants: `<name>.png` (points only) and `<name>_labeled.png` (a fixed set
of exemplar cities labelled).

## 4. Predictive model

```python
from cycleform import report
res = report.make_model_report()   # -> model_performance.csv, model_feature_importance.csv, figures
res["performance"]   # cross-validated R2 for form / country / form+country
res["importance"]    # top network-form predictors
```

## 5. Grown-network what-if (Tyne & Wear)

Separate analysis: merge each Tyne & Wear borough's Chapter-5 grown cycle network
into its real network and see how the metrics and the predicted cycling rate
shift. Build the main dataset (steps 1-2) **first** — the predictor is fit on all
cities. Full guide in `SCENARIOS.md`.

```powershell
$py = "$env:LOCALAPPDATA\miniforge3\envs\neatnetenv\python.exe"
& $py run_scenarios.py               # five boroughs, then figures
& $py run_scenarios.py --report-only # just remake figures from saved runs
```

Outputs: `results/scenario_comparison.csv`, `results/scenario_predictions.csv`, and
`scenario_shift_<place>.png` / `scenario_prediction_shift.png` /
`scenario_typology_shift.png` in `results/figures/`.

## Where things live

```
results/
  places/<place>.csv        per-place metrics (the cache; source of truth)
  combined_metrics.csv      wide table, one row per place
  analysis_table.csv        metrics x cycling rate
  outcomes_long.csv         harmonised cycling rates
  figures/*.png             all figures
  model_*.csv               model results
  scenario_*.csv            grown-network what-if results (see SCENARIOS.md)
  scenarios/                per-borough baseline/scenario runs (kept out of analysis)
  run_all.log               run progress
external/cycling_rates/     INPUT: drop cycling-rate data here
```
