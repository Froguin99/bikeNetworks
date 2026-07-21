# cycleform — results summary

_Generated 2026-07-21 · metric_version 0.5.0 · snapshot 2025-01-01_

**Study question.** Is the *form/structure* of a city's cycle network (and the road network it sits in) associated with its cycling rate across many cities, and can cycling rate be predicted from network form? Metrics are computed identically on real OSM cities and on Chapter-5 grown networks. This is a descriptive + predictive screen, not causal inference.

## 1. Dataset

- **232 places** with metrics; **225** have a cycling rate.
- UK places: **76**.
- Outcome sources (deduped per place): {'oecd_fua': 116, 'legacy_max_value': 109}.
- Top countries by place count: {'UK': 76, 'DE': 41, 'IT': 31, 'FR': 30, 'US': 19, 'PT': 6, 'BE': 6, 'CH': 4}.

## 2. Cycling rate (outcome, % mode share)

- n=225, min=0.0, median=3.6, mean=6.2, max=36.6, sd=6.6.
- Right-skewed; correlations below use Spearman (rank-based, robust).

## 3. Metric correlations with cycling rate

Ranked by |Spearman rho|, top 20 of 71 analysed metrics. `significant` = two-sided p < 0.05. Correlation is a signpost, not a model.

| metric | spearman | spearman_p | pearson | n | significant |
| --- | --- | --- | --- | --- | --- |
| intersection_ratio_bike_road | 0.695 | <0.001 | 0.567 | 213 | yes |
| bikeable_length_share | 0.645 | <0.001 | 0.614 | 225 | yes |
| circuity_avg_bike | -0.612 | <0.001 | -0.334 | 221 | yes |
| mean_route_lts | -0.587 | <0.001 | -0.471 | 187 | yes |
| lts1_coverage | 0.582 | <0.001 | 0.484 | 187 | yes |
| bike_lcc_share_of_road | 0.582 | <0.001 | 0.547 | 225 | yes |
| n_nodes_bike | 0.575 | <0.001 | 0.439 | 225 | yes |
| n_edges_bike | 0.557 | <0.001 | 0.412 | 225 | yes |
| intersection_count_bike | 0.549 | <0.001 | 0.392 | 225 | yes |
| low_stress_route_fraction | 0.531 | <0.001 | 0.489 | 225 | yes |
| edge_length_avg_m_bike | -0.530 | <0.001 | -0.308 | 221 | yes |
| n_components_bike | 0.525 | <0.001 | 0.420 | 225 | yes |
| lcc_length_km_bike | 0.519 | <0.001 | 0.422 | 187 | yes |
| intersection_density_km2_bike | 0.502 | <0.001 | 0.372 | 187 | yes |
| entropy_gap_kl | -0.499 | <0.001 | -0.215 | 221 | yes |
| component_size_gini_bike | 0.485 | <0.001 | 0.434 | 220 | yes |
| intersection_density_per_km_bike | 0.478 | <0.001 | 0.329 | 221 | yes |
| cycle_network_density_km2 | 0.470 | <0.001 | 0.376 | 187 | yes |
| gamma_index_road | 0.429 | 0.289 | 0.583 | 8 | no |
| alpha_index_road | 0.429 | 0.289 | 0.581 | 8 | no |

- Strongest **positive**: intersection_ratio_bike_road, bikeable_length_share, lts1_coverage.
- Strongest **negative**: circuity_avg_bike, mean_route_lts, edge_length_avg_m_bike.

## 4. Predictive model (cross-validated)

Out-of-sample R² for three feature sets: network **form** only, **country** (national context) only, and **form+country**. Compares how much network form predicts beyond national context.

| feature_set | model | cv_r2 | cv_r2_sd | cv_rmse | n |
| --- | --- | --- | --- | --- | --- |
| form | elasticnet | 0.370 | 0.089 | 3.567 | 225 |
| form | random_forest | 0.430 | 0.154 | 3.335 | 225 |
| country | elasticnet | 0.327 | 0.187 | 3.615 | 225 |
| country | random_forest | 0.308 | 0.198 | 3.659 | 225 |
| form+country | elasticnet | 0.385 | 0.098 | 3.514 | 225 |
| form+country | random_forest | 0.449 | 0.147 | 3.287 | 225 |

Top 12 network-form predictors (random-forest permutation importance, form-only model):

| metric | importance | importance_sd |
| --- | --- | --- |
| bike_lcc_share_of_road | 0.181 | 0.027 |
| bikeable_length_share | 0.146 | 0.018 |
| intersection_ratio_bike_road | 0.096 | 0.012 |
| circuity_avg_bike | 0.036 | 0.003 |
| low_stress_route_fraction | 0.028 | 0.006 |
| n_nodes_bike | 0.025 | 0.004 |
| betweenness_median_bike | 0.018 | 0.002 |
| edge_length_avg_m_bike | 0.017 | 0.002 |
| three_way_proportion_bike | 0.017 | 0.003 |
| lcc_length_km_bike | 0.017 | 0.004 |
| length_km_bike | 0.014 | 0.002 |
| dead_end_proportion_bike | 0.014 | 0.001 |

## 5. UK vs rest of sample (key metrics)

| metric | uk_mean | rest_mean | uk_minus_rest | n_uk | n_rest |
| --- | --- | --- | --- | --- | --- |
| bike_lcc_share_of_road | 0.110 | 0.196 | -0.086 | 76 | 156 |
| bikeable_length_share | 0.379 | 0.479 | -0.100 | 76 | 156 |
| circuity_avg_bike | 1.052 | 1.072 | -0.021 | 76 | 156 |
| components_per_km_bike | 0.631 | 0.732 | -0.101 | 76 | 156 |
| intersection_density_per_km_road | 5.648 | 3.737 | 1.911 | 76 | 156 |
| low_stress_coverage | 0.754 | 0.686 | 0.068 | 76 | 156 |
| meshedness_bike | 0.474 | 0.441 | 0.033 | 76 | 156 |

## 6. Bike vs road network form

`bike_gt_road_share` = fraction of cities where the cycle network exceeds the road network on that metric.

| metric | road_mean | bike_mean | bike_minus_road_mean | bike_gt_road_share | n |
| --- | --- | --- | --- | --- | --- |
| n_nodes | 5753.289 | 3136.711 | -2616.578 | 0.280 | 232 |
| n_edges | 7129.397 | 5768.784 | -1360.612 | 0.353 | 232 |
| length_km | 1190.022 | 389.723 | -800.299 | 0.069 | 232 |
| k_avg | 2.518 | 3.607 | 1.089 | 0.991 | 228 |
| intersection_density_per_km | 4.405 | 5.243 | 0.838 | 0.632 | 228 |
| dead_end_proportion | 0.288 | 0.026 | -0.261 | 0.009 | 228 |
| four_way_proportion | 0.091 | 0.637 | 0.546 | 1 | 228 |
| circuity_avg | 1.088 | 1.065 | -0.023 | 0.118 | 228 |
| orientation_entropy | 3.511 | 3.454 | -0.058 | 0.250 | 228 |
| lcc_length_share | 0.999 | 0.300 | -0.700 | 0.004 | 228 |
| components_per_km | 0.004 | 0.698 | 0.694 | 1 | 228 |
| self_loop_proportion | 0.002 | 0.001 | -0.001 | 0.092 | 228 |
| betweenness_mean | 0.012 | 0.007 | -0.005 | 0.070 | 228 |
| closeness_mean | 0.000 | 0.000 | 0 | 0.149 | 228 |
| clustering_mean | 0.023 | 0.009 | -0.013 | 0.140 | 228 |

## 7. Network-form typology

Standardise → PCA → k-means. **k=2** (silhouette 0.416); cluster sizes {0: 44, 1: 184}. Profiles are mean standardised (z) values per cluster (features: bikeable_length_share, low_stress_coverage, modal_directness_gap, entropy_gap_kl, bike_lcc_share_of_road, lcc_length_share_bike, circuity_avg_bike, orientation_entropy_bike, intersection_density_per_km_road, orientation_entropy_road, circuity_avg_road):

| type | bikeable_length_share | low_stress_coverage | modal_directness_gap | entropy_gap_kl | bike_lcc_share_of_road | lcc_length_share_bike | circuity_avg_bike | orientation_entropy_bike | intersection_density_per_km_road | orientation_entropy_road | circuity_avg_road |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | -0.950 | -1.400 | -0.850 | 0.950 | -0.570 | -0.180 | 1.420 | -0.910 | -1.170 | -0.730 | 0.930 |
| 1 | 0.230 | 0.340 | 0.200 | -0.230 | 0.140 | 0.040 | -0.340 | 0.220 | 0.280 | 0.180 | -0.220 |

## 9. Key caveats

- Correlations/predictions are descriptive + predictive, **not causal** (no confounder control yet; that is future work).
- Spearman is primary (cycling rate is skewed); Pearson shown alongside.
- A few metrics (entropy_gap_kl, bike centralities, components_per_km_bike) have extreme values driven by cities with a near-empty cycle network; these are kept (rank-based stats are robust), so plots show real outliers.
- Bike layer is raw OSM; road layer is neatnet-simplified — so raw *count* metrics are comparable within a layer across cities, not bike-vs-road.
- Densities are normalised by network length, not built-up area.
- `n` varies by metric: ~45 places predate newer metrics (fixed by re-running) and some metrics are genuinely undefined (e.g. gini on a single-component network).
