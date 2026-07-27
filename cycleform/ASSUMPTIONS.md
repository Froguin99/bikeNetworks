# Assumptions & caveats

A running log of every modelling choice, approximation and known limitation, so
the thesis can state them explicitly. Newest decisions at the bottom of each
section. When you change something here, change it in code too (and vice versa).

## Networks & geometry

- **Road network** = OSM `network_type="drive"`, simplified with **neatnet**,
  then re-noded into canonical node/edge frames. neatnet collapses dual
  carriageways / roundabouts / sliproads so intersection counts are comparable
  across countries (the old repo's raw-count defect).
- **Bike network** = filtered from OSM `network_type="all"` by the tuned
  infrastructure classifier (ported from old notebook 00). It is **not**
  neatnet-simplified — neatnet's block logic is built for road networks and
  distorts sparse, fragmented cycle paths. Consequence: `_bike` structural
  counts are on a *raw* representation and `_road` counts on a *simplified* one,
  so raw-count comparisons between the two layers are not like-for-like. Use the
  ratio / topology metrics (shares, proportions, entropy) for bike-vs-road
  comparison, and street length as the size control. (Decision: user, road-only
  neatnet.)
- **Boundary / built-up area is NOT used as a denominator.** Densities are
  normalised by network length (per km of edge). `PlaceContext.built_up_area_km2`
  is still populated (geocoded boundary area) but no metric divides by it.
  (Decision: user — "I don't care about built-up area; normalise by street
  length".)
- **Projected CRS** = per-place UTM chosen by osmnx. Lengths in metres.
- **Boundary clipping inflates dead-ends.** `graph_from_polygon` cuts edges at
  the boundary (default `truncate_by_edge=False`), leaving degree-1 stubs. On
  Chester `dead_end_proportion_road` ≈ 0.38. This is partly real (service-road
  stubs) and partly an edge effect; revisit with `truncate_by_edge=True` if it
  distorts cross-city comparison.

## LTS (level of traffic stress)

- LTS is a **highway-tag lookup** (`lts.py`), ported from the Chapter-5 growth
  repo. It ignores `cycleway:*`, maxspeed and physical separation — the
  cross-national tagging heterogeneity risk (CLAUDE.md §8).
- **Deviation from the growth chapter:** cycleway/track/path/bridleway were
  changed from LTS **0** (growth repo) to LTS **1** here (user edit). This does
  not affect the LTS≤2 "low-stress" classification, but means `lts.py` is no
  longer byte-identical to `bikenwgrowth/code/tag_lts.py`. Unknown highway types
  default to LTS 1. OSM list-valued `highway` takes the max (most stressful) LTS.

## Sampling (expensive metrics)

- **Betweenness** (node): networkx k-source estimator, `k =
  config.centrality_sample` (default 500), seeded (`config.centrality_seed`).
  Graphs at or below k are exact.
- **Closeness**: exact single-source shortest paths averaged over the same
  sample of source nodes (unbiased estimator of the mean); rustworkx Dijkstra.
- **Modal directness**: OD pairs formed from `config.modal_od_sample` (default
  200) sampled nodes, all-pairs among them (~k² comparisons from 2k shortest-
  path trees). Seeded.
- Clustering, circuity, orientation entropy, linearity, degree structure and
  connectivity are **exact** (cheap).

## Modal directness gap — OPEN definitional question

- CLAUDE.md §5c specifies: median of (shortest path on the **LTS≤2-only**
  network) / (shortest path on the drive network) — a **hard filter**.
- The Chapter-5 growth model instead routes on an **LTS-weighted** network
  (`sp_lts_distance`, length divided by LTS in `deweight_edges`) — a **soft**
  penalty where every OD stays connected.
- On Chester the hard-filter version is **degenerate**: only ~2 % of drive-
  connected OD pairs have any LTS≤2 route (`low_stress_route_fraction ≈ 0.02`),
  and for those few the ratio is exactly 1.0 (the pockets are locally low-
  stress, so no detour). So `modal_directness_gap` currently carries little
  information on its own; read it together with `low_stress_route_fraction`.
- **Needs a decision (CLAUDE.md §10 — metric defs must match Chapter 5):** keep
  the hard filter as specified, or switch to the LTS-weighted routing the growth
  chapter uses. Flagged to the user 2026-07-17; unresolved.

## Bike-infrastructure classifier (country-agnostic) — fixed after pilot

- **osmnx 2.x dropped every cycling tag by default.** Its default
  `useful_tags_way` has no `cycleway`, `cycleway:left/right/both`, `bicycle`,
  `bicycle_road`. So the classifier only ever saw `highway=cycleway` and silently
  under-counted on-road provision. The pilot exposed this: Freiburg and Münster
  (two of Germany's top cycling cities) came out at `bikeable_length_share`
  ≈ 0.07-0.09, vs ~0.7-1.0 for NL/US/Cambridge. `osm.configure_osmnx()` now
  re-adds the cycling tags before any fetch. (Existing osmnx caches still work —
  the raw Overpass JSON already held the tags; only parsing changed.)
- **Definition (user decision, 2026-07-17): protected/segregated OR mixed-use-
  with-pedestrians only.** An edge counts as cycle infrastructure iff any of:
  - `highway` in {cycleway, bridleway} (dedicated segregated ways);
  - `cycleway[:left|:right|:both]` = `track` or `opposite_track` (kerb-separated
    on-road tracks);
  - `highway` in {footway, path, pedestrian} AND `bicycle` in {yes, designated}
    (shared foot+cycle paths).
- **Deliberately EXCLUDED** by this definition (lower-stress but not physically
  separated from motor traffic): painted on-road lanes (`cycleway=lane`), cycle
  streets (`bicycle_road`/`cyclestreet`), and modal-filtered roads
  (`motor_vehicle=no` on residential). Consequence: cities whose provision is
  mostly painted lanes or cyclestreets will score lower on bike metrics — this
  is intended (it measures *segregated* provision).
- `cycleway=separate` is NOT counted on the road edge: the cycleway is mapped as
  its own `highway=cycleway` way and already captured; counting both would
  double-count length.

## Geocoding

- `resolve_boundary` fails if Nominatim's result is not a polygon. Hit on the
  50-city run for **Leicester** and **Gothenburg** (2/49 failed), earlier on
  Odense (fixed via "Odense Kommune"). Robustness (auto-fallback to
  municipality / which_result search, or endonym e.g. "Göteborg") still TODO.
  Failures are logged and returned in the batch status, never silently dropped.
- **Region mis-geocodes masquerade as huge networks.** Some names resolve to a
  far larger polygon than the city: **Calais, France** geocoded to ~631k raw drive
  edges (a whole department/arrondissement, not the town). These trip the
  `max_road_edges` guard, so they are skipped -- but the fix is a geocoding
  correction (a tighter query / place id), not a bigger cap. Distinguish these
  from genuinely large cities when reviewing skips.

## Network size cap (`max_road_edges`, raised 2026-07-21)

- Raised from **60000 to 200000** raw drive edges after the full run skipped many
  real cities. The cap guards neatnet + sampled routing against
  compute/memory blow-ups on region-scale geocodes; it is **not** a quality filter.
- Observed raw sizes (so the cap is set with evidence): Berlin ~74k, Leeds ~71k,
  Derby ~77k, Cosenza ~93k, Bergamo ~111k, Brescia ~155k -- all now **included**.
  Still capped: Oita ~233k, Okayama ~411k, Greater LA ~638k (OECD **FUA** metro
  regions, which include rural hinterland and are not city-scale-comparable), and
  the Calais mis-geocode (~631k).
- **Cost caveat:** the largest included cities (100k-155k raw) are slow through
  neatnet and memory-heavy; the sequential batch pauses on them for minutes. Not
  part of `metric_version`, so changing it neither invalidates the cache nor
  forces a recompute. Tunable per run via `CYCLEFORM_MAX_ROAD_EDGES` (e.g. lower it
  on a memory-limited machine, or raise it to attempt a FUA). A wall-clock budget
  on the neatnet step would be a more robust guard than a fixed edge count -- a
  possible future change.

## Figures

- Categorical colour is the **Okabe-Ito** CVD-safe palette in fixed order. With
  >6 countries the palette is NOT cycled (a dataviz non-negotiable); the 6 most
  frequent countries keep distinct hues and the rest fold into a neutral grey
  "Other". So single-city countries (CH, US, IE, ...) share grey.
- The metric-vs-cycling scatter shows one point per place (preferring OECD),
  labels only the extremes, and reports Spearman rho. It is a descriptive
  signpost, NOT a model (no confounder control) -- Q2 (Phase 5) does that.
- **Trend guide on the scatters (2026-07-24).** The overlaid curve is a *guide to
  the eye only*; the reported inference is the Spearman rho (monotone, form-free),
  so the curve carries no statistical weight. To let the shape vary between panels
  WITHOUT per-plot cherry-picking, a FIXED candidate set of two monotone forms is
  fitted to every panel -- **linear** (`a+b*x`) and **exponential** (`a*exp(b*x)`,
  multiplicative) -- and the winner is chosen by one objective criterion (**AICc**).
  (A log form was trialled and dropped, 2026-07-24, on visual grounds.) The procedure
  is identical for every figure even though the selected form differs, which is what
  makes it principled model selection rather than fishing. Two rigour points: (1) both
  are fitted on the RAW cycling-rate scale (the exponential by non-linear least
  squares, not by regressing `log y`), so their AICc is directly comparable -- fitting
  one form on a transformed axis and another on the raw axis is the classic invalid
  comparison; (2) the two forms share a parameter count, so AICc, AIC and R^2 rank
  them identically here, but AICc is used so the method stays valid if a higher-order
  form is added. The curve is drawn ON TOP of the points (dashed, semi-transparent, so
  it reads as a guide and is visible over dense scatter), is **clipped at 0 and the
  y-axis floored at 0** (cycling mode share cannot be negative -- previously a steep
  linear fit descended below zero and dragged the autoscaled axis negative), and its
  form + R^2 is reported in the legend / panel title (never floating on the axes, where
  dense points or a shifting legend would overwrite it). `figures._fit_trend`.
- **Metric-family grids (2026-07-24).** Alongside the one-scatter-per-metric figures,
  `figures.fig_metric_group_grids` draws a compact small-multiple grid per metric
  family (Size, Connectivity edge/node, Fragmentation, Shape & orientation, Centrality,
  LTS coverage, Relational comparisons -- the thesis subsections), so a paragraph can
  discuss one family at a time. Same guide curve as the individual scatters; both bike
  and road layers get a panel where they exist. Taxonomy in `figures.METRIC_GROUPS`.

## Correlation analysis decisions (2026-07-20)

- **Spearman is the primary correlation** (Pearson reported alongside). Cycling
  rate is strongly right-skewed and several metric relationships are monotonic-
  but-curved (e.g. directness: Spearman ~0.6 vs Pearson ~0.36), so a rank-based,
  outlier-robust, distribution-free measure is the appropriate descriptive screen.
  The rigorous proportion model is Phase 5.
- **No multiple-testing correction.** These correlations are a descriptive screen,
  not confirmatory tests, so a plain two-sided p<0.05 flag is reported and
  Benjamini-Hochberg FDR was dropped (unnecessary complexity here).
- **Redundant metrics excluded from analysis** (still computed, just not analysed;
  `describe._REDUNDANT`): `linearity_mean` and `linearity_median` (both layers) --
  circuity captures the same directness concept and is the standard transport
  metric, so it is the single directness measure kept. `year` and other outcome/
  bookkeeping columns are excluded from the metric list (no longer leak in).
- Figures are **PNG only** (PDF dropped). `report.make_figures` draws an
  individual metric-vs-cycling scatter for EVERY analysed metric, plus an all-
  metric correlation bar and an all-metric metric-metric heatmap.

## Outliers, skew & missing values (2026-07-21)

- **No cities are excluded and no values are deleted** (user decision). A few
  places sit far out on some metrics -- most visibly `entropy_gap_kl` (bulk < 0.5,
  a handful near 2), `closeness_mean_bike`, `betweenness_median_bike`,
  `components_per_km_bike`. These are **tiny-network artifacts, not real variation**:
  the extreme places have a near-empty cycle network (1.6-8 km, 6-83 edges, vs a
  215 km median), and centrality/orientation on a handful of edges is unstable.
  Confirmed: each such metric correlates with bike-network size at Spearman ≈ −0.8
  (the extremes *are* the smallest networks).
- **Why we keep them:** deleting points by value biases results (cherry-picking),
  and the headline analysis is already robust -- correlations use **Spearman**
  (rank-based, outlier-insensitive) and the model is a random forest, neither of
  which assumes normality. So the skew does not distort the reported statistics.
- **Plots show the full range, outliers included** (user decision, 2026-07-21). An
  axis-clipping / off-scale-marker display was tried and removed -- the carets
  looked worse than the skew they fixed. So a few points sit far out on the
  affected metrics; that is accepted rather than hidden or trimmed. (A per-metric
  log axis is the only cleaner alternative and can be added later if wanted; it was
  judged not worth the interpretive cost for now.)
- **Distribution shape:** cycling rate and several metrics are right-skewed / not
  normal. That is expected and fine for the current (rank-based + tree) methods; a
  future parametric/Bayesian model would use an appropriate link/transform rather
  than forcing normality on the raw data.

## Varying n across plots (2026-07-21)

- The place count differs between metrics for two distinct reasons:
  1. **metric_version skew (fixable by re-running):** ~45 of 215 places were
     computed under an older version (26 at 0.2.0) and lack every metric added
     since -- LTS coverage, `mean_route_lts`, the density metrics, `lcc_length_km`
     -- which therefore sit at n ≈ 170. Re-running those places at the current
     version (`run_all.py`, once Overpass cooperates) fills them in.
  2. **Genuinely undefined (re-running will not help, and NaN is correct):**
     `component_size_gini` is undefined for a single-component network (most road
     networks are one piece → n ≈ 109), and bike metrics are undefined on the
     degenerate tiny networks above.
- The combined table stitches every per-place file regardless of version, so stale
  places appear with NaNs rather than being dropped -- missingness stays visible.

## Added metrics (metric_version 0.3.0)

- `lts1_coverage`, `lts2_coverage` (road): LTS==1 and ==2 length share (splits the
  LTS<=2 low_stress_coverage). `lcc_length_km`: absolute largest-component length.
- Area-based densities (metrics/density.py, per km2 of **boundary area** --
  provisional, GHSL built-up pending): `street_density_km2`,
  `cycle_network_density_km2`, `intersection_density_km2_road/_bike`. Provided
  ALONGSIDE the network-length-normalised versions (user asked for both).
- Correlation reporting (`describe.correlate_with_outcome`) now returns Spearman
  AND Pearson with p-values and a Benjamini-Hochberg FDR-significance flag
  (many metrics tested at once). Bookkeeping columns (year/value/numerator/...)
  are excluded from the metric list so `year` no longer leaks in as a "metric".

## Added metrics (metric_version 0.2.0)

- `connectivity_ratio` (classic gamma index), `meshedness` (classic alpha index),
  per layer: planar connectivity / loop redundancy (0 = tree, ->1 = fully meshed).
  Renamed from `gamma_index`/`alpha_index` (2026-07-21) for readability; values
  unchanged. `orientation_order` (per layer): Boeing phi griddedness (1 = grid,
  0 = disordered). `bike_offroad_share`: cycle length on separate alignments.
  `intersection_ratio_bike_road`: cycle vs road junction count. All O(n).
- **Cross-layer caveat:** topology-*count* metrics (meshedness, connectivity_ratio, k_avg,
  intersection_ratio, four_way_proportion) are affected by the road-neatnet vs
  bike-raw processing asymmetry -- the raw bike graph keeps more nodes/edges per
  junction, inflating its counts relative to the simplified road graph. These are
  valid *within a layer across cities* and as predictors, but a within-city
  bike-vs-road *difference* on them is confounded. Length-based relational metrics
  (bikeable_length_share, bike_offroad_share, entropy_gap_kl) are not affected.

## Grown-network what-if (cycleform.scenarios, 2026-07-20)

- **What it is.** For the five Tyne & Wear boroughs (Newcastle, Gateshead,
  Sunderland, North Tyneside, South Tyneside) the Chapter-5 growth model produced
  a proposed protected cycle network. This merges that network into the real OSM
  network and re-measures every metric, to ask: if it were built, how does network
  form shift and would the fitted regression predict a higher cycling rate?
- **Which grown network.** The `demand`-weighted `current_ltn_scenario` pickle per
  borough (`bikenwgrowth_external/results/<place>/current_ltn_scenario/`), taking
  `GTs[-1]` — the **fully-grown** network (final prune quantile). So it is an
  upper-bound "entire proposed network built" scenario, not a partial rollout.
  (Configurable via `settings.scenario_*` and `load_grown_edges(quantile_index=)`.)
- **Merge = upgrade in place (user decision, 2026-07-20).** A grown corridor is
  protected cycle infrastructure added *to an existing street* (a kerb-separated
  track along the road), so:
  - **road** layer: **unchanged** (identical object; road metrics cannot move);
  - **bike** layer: **grows** — grown corridors are added as new protected infra,
    so its length, circuity, connectivity (LCC) and density change;
  - **street** layer: **same topology and total length**, but every street edge
    lying on a grown corridor has its `lts` set to 1 in place. Structural metrics
    (grid-ness, circuity, node counts) stay put; stress-coverage and routing
    metrics (`low_stress_coverage`, `lts1_coverage`, `low_stress_route_fraction`,
    `mean_route_lts`) improve. No parallel length is added to the street network.
- **Corridor matching is by OSM identity, not geometry** (following the old repo's
  `04-analyse-grown-networks.ipynb`, which merged on `['u','v','key']`). The growth
  model built the grown network on the same OSM graph, so each grown segment shares
  its endpoint OSM node ids (and way `osmid`) with the base network. We match on the
  **undirected OSM node pair** — exact and *per-segment*.
  - Node-pair, **not** way `osmid`: one OSM way spans many segments (mean 7.7, up to
    184 for Newcastle) and the grown network often uses only part of a way, so a
    way-`osmid` match would over-upgrade whole roads. Node-pair matching upgrades
    exactly the segments the grown network used.
  - cycleform re-nodes to canonical node ids from geometry, so the original OSM ids
    are carried **alongside** as edge columns (`osm_u`, `osm_v`, `osmid`) — metric
    values are therefore identical to the main pipeline.
  - **Spatial fallback** for the minority of grown segments whose node ids don't
    match any base edge (OSM re-split/edits between the ~2023 growth snapshot and
    the current fetch, or genuinely new links): those are buffered by
    `scenario_match_tol_m` (15 m) and a street edge is upgraded if ≥
    `scenario_cover_frac` (0.5) of its length is covered.
  - Grown geometry (for the fallback + the bike layer) is reconstructed as straight
    segments between the grown graph's OSM nodes (median ~14 m for Newcastle;
    adjacent-node scale, so straight ≈ real). Bike-layer merge is the inclusive
    node-pair union of notebook 04: grown corridors already present as cycle infra
    (same node pair) are dropped so length isn't double-counted; each new corridor
    is added once (not doubled for "each side of the road" — network metrics care
    about the corridor's connectivity, not two parallel lines). MultiDiGraph
    reciprocal directions are de-duplicated.
- **Comparison is like-for-like.** Baseline and scenario are measured from the
  *same* freshly-built context in one run, so a metric shift is attributable only
  to the merge, never to a re-fetch or a different boundary.
- **Prediction.** The regression is fit on the **full cross-city dataset** (form
  features, random forest — `models.fit_predictor`) and applied to each borough's
  baseline and scenario metrics. Kept **out of** the training/analysis set: scenario
  runs are saved under `results/scenarios/`, never `results/places/`, so they never
  contaminate the cross-city correlations or the model fit.
- **Read as illustrative, not causal.** The prediction says "a city with this
  network *form* tends to have this cycling rate", not "building this raises cycling
  by X" — the confounder-controlled causal model is Phase 5.

## Caching (metric_version)

- Per-place files record `metric_version`; `batch.run_place` skips a place already
  computed under the current version (status "cached") unless `force=True`. A run
  is therefore resumable, and figures/tables are rebuilt from saved files without
  recompute (`report.py`). Bump `settings.metric_version` to invalidate.

## Full run (~900 places, 2026-07-18 to 20)

- Of 938 places, **146 computed OK, 791 failed, 1 cached**; the combined table has
  171 places and **166 matched a cycling rate** (75 UK, then FR/US/IT/DE/...).
- **Failures were overwhelmingly Overpass API timeouts**, not data problems --
  even ordinary UK cities (Derby, Leeds, Glasgow) failed once the server
  throttled us over 2 days of sustained requests. They are transient and
  **retryable**: re-running `run_all.py` retries the failures (successes cached).
- Mitigation added (osm.py + networks.py): `requests_timeout=300`,
  `overpass_rate_limit=True`, and retry-with-backoff (3 attempts) on transient
  fetch errors. Re-run to recover the failed places; consider spacing runs out so
  Overpass isn't freshly throttled.
- The timeouts happened to filter out most non-European places (only 1 JP, 1 ME
  survived), which is fine -- those had the least reliable cycle tagging (§8).
- **Findings on n=166 (bigger, less cherry-picked than the 50-city set):** the
  UK-vs-rest gap SHRANK (bikeable_share UK 0.38 vs rest 0.43, not vs 0.76) because
  the 50-city "rest" was cherry-picked cycling cities -- the larger sample is more
  honest. Top Spearman correlates hold: cycle circuity -0.60, cycle linearity
  0.60, bikeable_share 0.56, intersection_ratio_bike_road 0.55, bike_lcc 0.52.

## Scale-test observations (50 cities, 2026-07-17)

- **Parma** is a typology + linearity outlier (lowest cycle-network linearity).
  Check whether real or an ingest artefact before trusting its metrics.
- Top Spearman correlates of cycling rate (n=46, descriptive): cycle-network
  linearity (0.75), bikeable_length_share (0.67), cycle circuity (-0.58),
  bike_lcc_share_of_road (0.57). Direction matches the thesis hypothesis.

## Things to validate (suspicious, not yet explained)

- `four_way_proportion_bike` ≈ 0.65 on Chester seems high for cycle paths;
  check whether it is real grade-separated crossings or a tagging artefact of
  the "all"-network filter.

## Outcomes (cycling rate) — Phase 2

- Harmonised long table from multiple sources with `source` and `measure_type`
  as fixed effects; constructs are never silently stacked (CLAUDE.md §4). One
  outcome is chosen per place by `outcomes.SOURCE_PRIORITY` via `prefer_outcome`.
- **Primary source (added 2026-07-23): ModalShare.** `modalshare.csv`, the
  commute-to-work cycling share compiled by Prieto-Curiel & Ospina (see
  attribution below), latest observation per city (`LastObservation == YES`),
  stored 0–1 → scaled to %. Preferred over the others because it is broad
  (~1,050 cities with a cycling value), harmonised across Eurostat / US-CA-AU
  census / EPOMM / EF China, and agrees with the old values (Pearson ≈ 0.90)
  while giving stronger, higher-n correlations. Expanded the run list to ~1,450
  places.
- **Gap-fill sources** (used only where ModalShare has no value): OECD FUA
  commute mode share (**most recent year per FUA**), then `max_value.csv` (old
  project; Eurostat + 2011 UK census; mixed construct, year unknown).
- All three measure the **same construct** — cycle commute-to-work mode share —
  so mixing them is defensible; `source` is still carried for a fixed effect /
  sensitivity check.

### Data attribution

- **ModalShare** — Prieto-Curiel, R. & Ospina, J. P., *"Large cities are less
  efficient for sustainable transport: The ABC of mobility"* (dataset).
  Complexity Science Hub / EAFIT. Source repo:
  <https://github.com/rafaelprietocuriel/ModalShare> (`ModalShare.csv`, accessed
  2026-07-23; copied to `external/cycling_rates/modalshare.csv`, README preserved
  as `modalshare_SOURCE.md`, `CITATION.cff` in the repo). The dataset itself is
  compiled from many underlying sources, referenced per row in its `DataSource` /
  `DataLink` columns (carried into the `notes` field).
- **OECD FUA** — OECD Functional Urban Area commute mode share (Eurostat browser
  `urb_ltran` lineage), `oecd_fua_commute_bicycle.csv`.
- **Legacy** — `max_value.csv` from the predecessor project (Eurostat + 2011 UK
  census, mixed).


## "n" differances

- The number "n" of items in each plot sometimes is different. This could be because some places may have (for example) a signle component network
