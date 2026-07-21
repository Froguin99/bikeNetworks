# Grown-network what-if (Tyne & Wear)

Merge each Tyne & Wear borough's **Chapter-5 grown cycle network** into its real
OSM network, re-measure every metric, and ask: *if this network were built, how
does its form shift, and would the fitted regression predict a higher cycling
rate?* Method and caveats are in `ASSUMPTIONS.md` ("Grown-network what-if").

This is the mirror image of the §2 invariant — the same metric code runs on the
merged network, so the shift is meaningful.

## What gets merged

For each borough the growth model (`bikenwgrowth`, `current_ltn_scenario`,
demand-weighted) produced a proposed protected cycle network. We take the
**fully-grown** graph (`GTs[-1]`) and merge it so that:

| layer | effect |
|---|---|
| **road** | unchanged — the drive network is untouched |
| **bike** | grows — grown corridors added as new protected infrastructure (length, circuity, connectivity, density move) |
| **street** | same topology & total length, but grown corridors become **LTS 1** in place (stress-coverage and routing metrics improve; structural metrics stay put) |

Baseline and scenario are measured from the **same** freshly-built context, so a
metric shift is caused only by the merge.

**Matching is by OSM identity, not a spatial join** — the grown network was built
on the same OSM graph, so each grown segment shares its endpoint OSM node ids with
the base network (as in the old repo's `04-analyse-grown-networks.ipynb`, which
merged on `['u','v','key']`). We match on the undirected OSM node *pair* — exact
and per-segment, so a partly-used road isn't wholly upgraded (which a way-`osmid`
match would do). A spatial fallback catches segments whose ids drifted between the
2023 growth snapshot and the current fetch. See `ASSUMPTIONS.md` for detail.

## Prerequisites

1. The **neatnetenv** interpreter (see `RUNNING.md`).
2. The **main cross-city dataset already built** — `results/combined_metrics.csv`
   and `results/analysis_table.csv` must exist, because the predictor and the
   form-space context are fit on all cities. Build the dataset first
   (`python run_all.py`); *then* run scenarios.
3. The grown pickles present at `settings.grown_results_dir`
   (`.../bikenwgrowth_external/results/<place>/current_ltn_scenario/...`). Read-only.

## Run it

From the package root:

```powershell
$py = "$env:LOCALAPPDATA\miniforge3\envs\neatnetenv\python.exe"
& $py run_scenarios.py                # run the five boroughs, then make figures
& $py run_scenarios.py --force        # recompute even if cached
& $py run_scenarios.py --report-only  # just (re)make figures from saved runs
```

Each borough fetches its OSM network once (reusing the osmnx cache if it was
fetched for the main run) and writes two rows — baseline and scenario. Resumable:
a borough already run at the current `metric_version` is skipped unless `--force`.

Progress → `results/scenarios/run_scenarios.log`.

## Or from Python

```python
from cycleform import scenarios, report

scenarios.run_scenarios()               # default = the five Tyne & Wear boroughs
res = report.make_scenario_report()     # figures + tables from the saved runs
res["comparison"]    # per-(place, metric): baseline, scenario, delta
res["predictions"]   # per-place predicted rate now vs with grown network (+ shift)
```

To inspect a single borough's merge without saving:

```python
from cycleform import scenarios

spec = scenarios.TYNE_AND_WEAR[0]                               # Newcastle
ctx = scenarios.scenario_base_context(spec)                    # base, keeps OSM ids
grown = scenarios.load_grown_edges("newcastle", ctx.road.crs)  # 204 km of cycleway
sctx = scenarios.scenario_context(ctx, grown)                  # merged context
```

Use `scenario_base_context` (not `ingest.context_from_osm`) as the base: it keeps
the OSM node ids the identity match needs. `scenario_context` still works on a plain
`context_from_osm` context, but with no ids it can only match spatially.

## Outputs

In `results/`:

- `scenario_comparison.csv` — one row per (place, metric): `baseline`, `scenario`,
  `delta`.
- `scenario_predictions.csv` — per place: `baseline_pred`, `scenario_pred`,
  `shift`, and `observed` (current rate where known).

In `results/figures/`:

- `scenario_shift_<place>.png` — dumbbell of how that borough's metrics shift,
  z-scored against all cities (SD units): grey = current, blue = with grown network.
- `scenario_prediction_shift.png` — predicted cycling rate now vs with the grown
  network, all boroughs; the tick marks the observed current rate.
- `scenario_typology_shift.png` — each borough's movement in form-space (PCA), an
  arrow from current to grown position over the all-cities backdrop.

In `results/scenarios/`: the raw per-borough `<place>__baseline.csv` /
`<place>__scenario.csv` (the cache; kept out of the cross-city analysis set).

## Changing what is analysed

- **Different boroughs / places** — build a `scenarios.ScenarioSpec(growth_placeid,
  query, place_id, country)` list and pass it to `run_scenarios(specs=...)`. Needs a
  matching grown pickle under `grown_results_dir`.
- **Different grown variant** — set `settings.scenario_prune_measure`
  (`demand` | `betweenness` | ...) or pass `prune_measure=` through
  `load_grown_edges`.
- **Partial build instead of the full network** — `load_grown_edges(...,
  quantile_index=k)` picks an earlier prune quantile (`-1` = fully grown).
- **Match tolerance** — `settings.scenario_match_tol_m` and
  `settings.scenario_cover_frac`.
