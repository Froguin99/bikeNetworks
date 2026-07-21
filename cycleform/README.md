# cycleform

Form and structure of urban cycle networks, measured **against the road networks
they inhabit**, related to cycling rates across many cities. This is the 2026
rewrite of `bikeNetworksEDA` (thesis Objective 1 + Objective 7).

The full rationale, research questions and constraints live in the top-level
`CLAUDE.md`. This README is just how to *run* it.

## The one rule that shapes everything

Metric code must give the **same answer** on a real OSM city and on a network
grown by the Chapter-5 model. That is why there is a package at all: every place
— real or grown — is turned into the same `PlaceContext` object *before* any
metric sees it, so a metric can never ask "is this simulated?". The test
`tests/test_invariant.py` fails if that ever stops being true.

## How this is meant to be used

You keep working in **notebooks** (`notebooks/`). The notebooks stay thin: they
import `cycleform`, call functions, and plot. All the real logic — network
building, metrics, stats — lives in `src/cycleform/` where it can be unit-tested
and reused. So a notebook cell looks like:

```python
from cycleform.ingest import context_from_osm
from cycleform.metrics import REGISTRY, results_to_frame

ctx = context_from_osm("Newcastle upon Tyne, United Kingdom")
results = REGISTRY.run(ctx)          # every metric, one code path
results_to_frame(results)            # tidy long table, keeps missingness visible
```

If you find yourself writing more than a few lines of *logic* in a notebook,
that logic probably belongs in a module in `src/cycleform/` with a test. That
is the whole discipline — nothing heavier (no snakemake yet).

## Environment

Uses the conda env **`neatnetenv`** (a clone of `growbikenet` + `neatnet` and
the modern geo stack: osmnx 2.1, geopandas 1.1, momepy 1.0). The Chapter-5
growth env `growbikenet` is left untouched.

```powershell
# one-time: install the package into the env in editable mode
& "$env:LOCALAPPDATA\miniforge3\envs\neatnetenv\python.exe" -m pip install -e . --no-deps --no-build-isolation
```

Then select the `neatnetenv` kernel in the notebook.

## Running the tests

```powershell
$py = "$env:LOCALAPPDATA\miniforge3\envs\neatnetenv\python.exe"
& $py -m pytest            # offline: synthetic graphs + the §2 invariant
$env:CYCLEFORM_RUN_OSM_TESTS = "1"; & $py -m pytest   # also hit OSM (slow)
& $py -m ruff check; & $py -m ruff format
```

## Where results and inputs live

```
2026_edition/
  cycleform/                 the package (this folder)
  external/                  INPUT drop-zone (you add data here)
    cycling_rates/           max_value.csv, oecd_fua_commute_bicycle.csv, ...
  results/                   OUTPUT (written by the pipeline)
    places/<place>.csv       one file per place, all metrics (long form)
    combined_metrics.csv     one row per place, one column per metric (wide)
    outcomes_long.csv        harmonised cycling-rate table
```

Save a place's metrics with `results.save_place(ctx, results)`; stitch the wide
table with `results.build_combined()`. Build the outcome table with
`outcomes.build_outcomes()`.

## Layout

```
src/cycleform/
  config.py        paths, CRS, SNAPSHOT_DATE, sampling sizes  (pydantic-settings)
  places.py        boundary resolution (OSM now; GISCO/ONS later)
  networks.py      road / bike network construction from OSM  (+ bike filter)
  simplify.py      neatnet wrapper + re-noding to canonical frames
  lts.py           LTS classification, ported from the growth repo — do not rewrite
  geometry.py      bearings, orientation histograms, circuity, KL, Gini
  ingest.py        OSM -> PlaceContext           (real-city path)
  synthetic.py     grid networks + a fake grown PlaceContext  (grown-network path)
  results.py       per-place + combined metric tables
  outcomes.py      cycling-rate harmonisation    (Phase 2)
  metrics/
    base.py        Network, PlaceContext, NetworkMetric, PlaceMetric
    registry.py    REGISTRY + run() — never raises, never silently drops a metric
    structural.py  per-network form metrics (run on road AND bike -> _road/_bike)
    centrality.py  sampled betweenness / closeness / clustering
    relational.py  cycle-vs-road metrics (§5c) — the novelty
tests/             golden-value, property, invariant, outcomes, and (gated) OSM tests
notebooks/         exploration only; strip outputs with nbstripout
```

## Status

- **Phase 1 (scaffolding) — gate passed**: the same metric registry runs on
  real Chester and on a synthetic grown network.
- **Metric suite**: ~30 metrics -> 54 output columns. Structural metrics
  (`NetworkMetric`) run on both the road and bike layers, suffixed `_road` /
  `_bike`; relational metrics (`PlaceMetric`) compare the two. Expensive
  centralities are sampled (seeded). Densities are normalised by network
  length, not area.
- **Phase 2 (outcomes) — table built**: `outcomes_long.csv`, 1,135 rows, 938
  places, from `max_value.csv` (legacy) + OECD FUA (latest year per FUA), with
  `source` / `measure_type` kept as fixed effects.

Next: Phase 3 (join metrics to outcomes -> analysis table, run at scale), then
typology / modelling / scenarios. See `CLAUDE.md §9` and `ASSUMPTIONS.md`.

### Open decisions (see ASSUMPTIONS.md)

- **Modal directness gap**: CLAUDE.md specifies a hard LTS≤2 filter, but the
  growth chapter routes on an LTS-*weighted* network. The hard filter is
  degenerate on fragmented low-stress networks (Chester: ~2 % of OD pairs have
  a low-stress route). Needs a definition decision.
- **LTS** ignores `cycleway:*` / maxspeed / separation (tagging risk, §8) and
  now differs from the growth repo (cycleway 0 -> 1). Kept simple on purpose.
