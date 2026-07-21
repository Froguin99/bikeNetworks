# Metric reference

Every metric cycleform computes, what it means, and how it is calculated. This is
the companion to `ASSUMPTIONS.md` (which records the modelling *choices* and
caveats). Definitions here match the code in `src/cycleform/metrics/` and
`src/cycleform/geometry.py`.

## How to read this

- **Layer**: most structural metrics are computed on **both** networks and the
  output column is suffixed `_road` or `_bike` (e.g. `circuity_avg_road`,
  `circuity_avg_bike`). *Relational* and *LTS* metrics combine layers and have no
  suffix.
- **Road network** = OSM `network_type="drive"`, simplified with neatnet.
  **Cycle network** = protected/segregated + shared-with-pedestrians cycle
  infrastructure, filtered from OSM `network_type="all"` (not neatnet-simplified).
  **Street network** = the *cyclable* network: roads a cyclist may use (excludes
  motorways/steps/pure-pedestrian) **plus** the cycle infrastructure, from the
  same `all` fetch. The LTS and routing metrics (§8, §9) run on this so cycle
  infrastructure is included.
- A network is a set of **nodes** (junctions, degree = number of edges meeting)
  and **edges** (street/path segments, each with a length in metres). `n` = node
  count, `m` = edge count.
- **Cross-layer caveat**: because the road network is neatnet-simplified but the
  cycle network is raw, *count-based* metrics (`k_avg`, `meshedness`,
  `connectivity_ratio`, `intersection_ratio_bike_road`, degree proportions) are directly
  comparable **across cities within one layer**, but a within-city road-vs-cycle
  difference on them is confounded. Length-based and ratio metrics are not
  affected.

---

## 1. Outcome (what we predict)

| column | meaning |
|---|---|
| `value` | **Cycling rate** — % of commuters cycling to work (mode share). From OECD Functional Urban Areas (latest year per city) or the legacy `max_value.csv`. `source` and `measure_type` distinguish constructs; `year` records the survey year. |

---

## 2. Size

| metric | what it measures | how it is calculated |
|---|---|---|
| `n_nodes` | number of junctions/endpoints | count of nodes |
| `n_edges` | number of segments | count of edges |
| `length_km` | total network length | Σ edge length ÷ 1000 |
| `edge_length_avg_m` | typical segment length | mean edge length (m). Short segments → finer-grained network |

---

## 3. Connectivity & junction structure

How well-connected the network is and what kind of junctions it has.

| metric | what it measures | how it is calculated |
|---|---|---|
| `k_avg` | average junction connectivity (mean node degree) | 2·m ÷ n |
| `intersection_count` | number of true intersections | count of nodes with degree ≥ 3 (dead-ends and pass-through points excluded) |
| `intersection_density_per_km` | intersections per km of network | `intersection_count` ÷ `length_km` |
| `dead_end_proportion` | share of nodes that are dead-ends | (nodes with degree 1) ÷ n. High = many cul-de-sacs / stubs |
| `three_way_proportion` | share of T-junctions | (nodes with degree 3) ÷ n |
| `four_way_proportion` | share of crossroads | (nodes with degree ≥ 4) ÷ n. High = grid-like |
| `self_loop_proportion` | share of loop edges | (edges whose two ends are the same node) ÷ m |
| `connectivity_ratio` | realised edges vs the planar maximum (classic **gamma index**). 0 = minimally connected, 1 = fully meshed | m ÷ (3·(n − 2)) |
| `meshedness` | how many independent *loops* the network has vs the maximum (classic **alpha index**). **0 = a tree** (exactly one route between any two points, forced detours), **→1 = many alternative routes** | (m − n + components) ÷ (2·n − 5) |

*Why meshedness / connectivity matter for cycling*: a high-`meshedness` cycle
network lets a rider choose alternative, quieter or more direct paths; a tree-like
(`meshedness` ≈ 0) network funnels everyone onto the same few links.

---

## 4. Fragmentation (is the network joined up?)

| metric | what it measures | how it is calculated |
|---|---|---|
| `n_components` | number of disconnected pieces | count of connected components (isolated nodes included) |
| `components_per_km` | fragmentation per unit size | `n_components` ÷ `length_km` |
| `lcc_length_share` | how much of the network is in one piece | (length of the largest connected component) ÷ (total length). 1.0 = fully joined up |
| `lcc_length_km` | absolute size of the biggest connected piece | largest-component length ÷ 1000 |
| `component_size_gini` | how unequal the component sizes are | Gini coefficient of component lengths. 0 = all pieces equal, →1 = one piece dominates. NaN when there is a single component |

*For cycle networks these are central*: a fragmented cycle network (low
`lcc_length_share`, high `components_per_km`) means a rider constantly drops back
into traffic between disconnected stretches. Because every network metric is
computed per layer, **`components_per_km_bike`** is precisely "how many
disconnected pieces the cycle network has per km of cycle network" — the
size-normalised fragmentation of the current cycle network — and
`components_per_km_road` the same for the road network.

---

## 5. Shape & orientation

| metric | what it measures | how it is calculated |
|---|---|---|
| `circuity_avg` | **directness** — how much longer network paths are than straight lines | (Σ edge length) ÷ (Σ straight-line distance between each edge's endpoints). ≥ 1; 1.2 ≈ paths are 20 % longer than as-the-crow-flies. Lower = more direct |
| `orientation_entropy` | how many directions streets run in | Shannon entropy of the length-weighted distribution of edge bearings (36 bins over 0–360°, direction-symmetric). Low = few dominant directions, high = streets run every way |
| `orientation_order` | **griddedness** (Boeing 2019 φ) | 1 − ((H − ln 4) ÷ (ln 36 − ln 4))², where H = `orientation_entropy`. **1 = perfect grid**, 0 = disordered |

> `linearity_mean` / `linearity_median` are also computed but **excluded from the
> analysis** as redundant with `circuity_avg` (they measure the same directness
> concept per-edge); circuity is the single directness metric used.

---

## 6. Centrality (sampled — see ASSUMPTIONS §sampling)

How "central" nodes are on average. Computed on a seeded sample of source nodes
(`config.centrality_sample`, default 500) so they stay affordable at scale.

| metric | what it measures | how it is calculated |
|---|---|---|
| `betweenness_mean`, `betweenness_median` | how much through-traffic concentrates on key links | mean/median node **betweenness centrality** (networkx, length-weighted, k-sampled sources): the fraction of shortest paths passing through each node |
| `closeness_mean`, `closeness_median` | how easily the whole network is reached from a typical node | mean/median **closeness** = (reachable nodes) ÷ (total shortest-path distance to them), Wasserman–Faust scaled, over sampled sources |
| `clustering_mean` | how locally interconnected junctions are | mean node **clustering coefficient** (fraction of a node's neighbours that are themselves connected); computed exactly |

---

## 7. Density per unit area

Classic area-based densities (per km²). **Caveat**: area is the *geocoded boundary
area*, not GHSL built-up land, so it overstates the denominator — treat as
provisional and compare with the network-length-normalised versions.

| metric | what it measures | how it is calculated |
|---|---|---|
| `street_density_km2` | road length per km² | road `length_km` ÷ boundary area (km²) |
| `cycle_network_density_km2` | cycle length per km² | cycle `length_km` ÷ boundary area |
| `intersection_density_km2_road` | road intersections per km² | road `intersection_count` ÷ boundary area |
| `intersection_density_km2_bike` | cycle intersections per km² | cycle `intersection_count` ÷ boundary area |

---

## 8. Level of Traffic Stress (LTS) — the cyclable street network

LTS is assigned to each edge from its `highway` tag (ported from the Chapter-5
growth model): motorway/trunk/primary/secondary = 4, tertiary/unclassified = 3,
residential/living_street = 2, cycleway/track/path/bridleway = 1, unknown
(incl. service) = 1.

**Coverage is length-weighted over the cyclable STREET network** (roads a cyclist
may use + cycle infrastructure — §Street network), *not* the drive network. This
matters: the drive network contains no cycleways, so measuring LTS there ignored
the actual cycle infrastructure entirely (and gave near-zero correlations). On the
street network, dedicated cycleways (LTS 1) count.

| metric | what it measures | how it is calculated |
|---|---|---|
| `low_stress_coverage` | share of the cyclable network that is comfortable (LTS ≤ 2) | (street length at LTS ≤ 2) ÷ (street length) |
| `lts2_coverage` | share at LTS 2 | (street length at LTS == 2) ÷ (street length) ≈ **residential streets** |
| `lts1_coverage` | share at LTS 1 | (street length at LTS == 1) ÷ (street length). Includes **dedicated cycleways/paths** *and* service roads (both LTS 1). For a clean "dedicated cycle infrastructure" measure use the cycle-network metrics (§9), which isolate segregated provision |

> The LTS lookup is highway-tag-only (ignores `cycleway:*`, maxspeed, separation)
> and lumps service roads with cycleways at LTS 1 — a known limitation
> (ASSUMPTIONS §LTS). `low_stress_coverage` is the robust summary.

---

## 9. Relational metrics — cycle network vs road network (the novelty)

These compare the two layers directly; no `_road`/`_bike` suffix.

| metric | what it measures | how it is calculated |
|---|---|---|
| `bikeable_length_share` | **provision** — cycle infrastructure relative to the road network it sits in | cycle `length_km` ÷ road `length_km`. > 1 possible where cycle paths run off the road network (parks, canals) |
| `bike_offroad_share` | **separation quality** — how much cycle infrastructure is on its own alignment vs alongside traffic | (cycle length on dedicated ways: highway = cycleway/path/footway/pedestrian/bridleway/track) ÷ (total cycle length) |
| `bike_lcc_share_of_road` | **size-normalised connectedness** of the cycle network | (largest cycle component length) ÷ (road `length_km` × 1000). A single joined-up cycle network scores high |
| `intersection_ratio_bike_road` | how finely the cycle network is woven into the street grid | cycle `intersection_count` ÷ road `intersection_count` |
| `entropy_gap_kl` | **does the cycle network run the same ways as the roads?** | Kullback–Leibler divergence of the cycle network's orientation distribution from the road network's. 0 = same orientations; larger = the cycle network is oriented differently (e.g. "only runs N–S") |
| `modal_directness_gap` | **how much further a comfortable cycling route is than the most direct one** | median over sampled OD pairs of (actual length of the **LTS-weighted** low-stress-seeking route on the street network) ÷ (shortest-distance route length). The cyclist routes to minimise `length × LTS` (matching the growth chapter's `sp_lts_distance`), but the route's *real* length is measured. ≥ 1; 1.9 = nearly double the distance to stay comfortable |
| `low_stress_route_fraction` | **connectivity of the low-stress network** | fraction of sampled connected OD pairs that also have a route staying entirely on LTS ≤ 2 streets |
| `mean_route_lts` | **typical stress a cyclist experiences on a sensible route** | for each sampled OD pair, route the low-stress-seeking path on the street network and take its **length-weighted mean LTS** (a long LTS-4 stretch weighs more than a short one); return the **median** over pairs. Lower = a rider can get around mostly on comfortable streets |

---

## Provenance & bookkeeping columns (not metrics)

`place_id`, `country`, `is_uk`, `place_key`, `source`, `measure_type`, `year`,
`snapshot_date`, `metric_version` — identifiers and provenance, excluded from all
metric analysis.
