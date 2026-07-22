# cycleform — results summary

_Generated 2026-07-22 · metric_version 0.5.0 · snapshot 2025-01-01_

**Study question.** Is the *form/structure* of a city's cycle network (and the road network it sits in) associated with its cycling rate across many cities, and can cycling rate be predicted from network form? Metrics are computed identically on real OSM cities and on Chapter-5 grown networks. This is a descriptive + predictive screen, not causal inference.

## 1. Dataset

- **373 input places** with network metrics computed.
- **366** of them have an observed cycling rate (the modelled sample).
- UK places: **76**.
- Top countries by place count: {'UK': 76, 'DE': 71, 'FR': 64, 'IT': 60, 'US': 38, 'PT': 11, 'BE': 10, 'CH': 9}.

Cycling-rate outcome by source (one preferred source per place, OECD FUA first where a place has several):

| source | places used | years |
| --- | --- | --- |
| OECD FUA (bicycle commute mode share) | 188 | 2005–2024 |
| Eurostat + 2011 UK census (legacy max_value.csv, mixed) | 178 | unspecified |

_Eurostat and the 2011 UK census are combined in the legacy `max_value.csv` (year unspecified) and are not separable within it; supplying them as separate files would let them be reported (and modelled) apart._

## 2. Cycling rate (outcome, % mode share)

- n=366, min=0.0, median=3.3, mean=6.0, max=36.6, sd=6.5.
- Right-skewed; correlations below use Spearman (rank-based, robust).

## 3. Metric correlations with cycling rate

Ranked by |Spearman rho|, top 20 of 67 analysed metrics. `significant` = two-sided p < 0.05. Correlation is a signpost, not a model.

| metric | spearman | spearman_p | pearson | n | significant |
| --- | --- | --- | --- | --- | --- |
| intersection_ratio_bike_road | 0.720 | <0.001 | 0.619 | 363 | yes |
| bikeable_length_share | 0.681 | <0.001 | 0.635 | 366 | yes |
| n_nodes_bike | 0.617 | <0.001 | 0.463 | 366 | yes |
| mean_route_lts | -0.610 | <0.001 | -0.473 | 337 | yes |
| n_edges_bike | 0.604 | <0.001 | 0.460 | 366 | yes |
| intersection_count_bike | 0.599 | <0.001 | 0.450 | 366 | yes |
| bike_lcc_share_of_road | 0.582 | <0.001 | 0.582 | 366 | yes |
| n_components_bike | 0.573 | <0.001 | 0.426 | 366 | yes |
| low_stress_route_fraction | 0.567 | <0.001 | 0.582 | 366 | yes |
| circuity_avg_bike | -0.561 | <0.001 | -0.200 | 361 | yes |
| entropy_gap_kl | -0.554 | <0.001 | -0.237 | 361 | yes |
| lcc_length_km_bike | 0.546 | <0.001 | 0.478 | 337 | yes |
| lts1_coverage | 0.539 | <0.001 | 0.434 | 337 | yes |
| intersection_density_km2_bike | 0.514 | <0.001 | 0.335 | 337 | yes |
| edge_length_avg_m_bike | -0.509 | <0.001 | -0.272 | 361 | yes |
| component_size_gini_bike | 0.498 | <0.001 | 0.462 | 356 | yes |
| cycle_network_density_km2 | 0.489 | <0.001 | 0.358 | 337 | yes |
| intersection_density_per_km_bike | 0.478 | <0.001 | 0.332 | 361 | yes |
| length_km_bike | 0.460 | <0.001 | 0.452 | 366 | yes |
| orientation_order_bike | -0.416 | <0.001 | -0.287 | 358 | yes |

- Strongest **positive**: intersection_ratio_bike_road, bikeable_length_share, n_nodes_bike.
- Strongest **negative**: mean_route_lts, circuity_avg_bike, entropy_gap_kl.

## 4. Predictive model (cross-validated)

Out-of-sample R² for three feature sets: network **form** only, **country** (national context) only, and **form+country**. Compares how much network form predicts beyond national context.

| feature_set | model | cv_r2 | cv_r2_sd | cv_rmse | n |
| --- | --- | --- | --- | --- | --- |
| form | elasticnet | 0.548 | 0.090 | 3.240 | 366 |
| form | random_forest | 0.608 | 0.132 | 3.008 | 366 |
| country | elasticnet | 0.417 | 0.131 | 3.670 | 366 |
| country | random_forest | 0.412 | 0.134 | 3.681 | 366 |
| form+country | elasticnet | 0.551 | 0.089 | 3.222 | 366 |
| form+country | random_forest | 0.615 | 0.131 | 2.977 | 366 |

Top 12 network-form predictors (random-forest permutation importance, form-only model):

| metric | importance | importance_sd |
| --- | --- | --- |
| intersection_ratio_bike_road | 0.397 | 0.022 |
| bike_lcc_share_of_road | 0.119 | 0.009 |
| modal_directness_gap | 0.046 | 0.005 |
| low_stress_coverage | 0.036 | 0.005 |
| n_components_bike | 0.029 | 0.003 |
| bikeable_length_share | 0.029 | 0.002 |
| circuity_avg_bike | 0.026 | 0.002 |
| components_per_km_bike | 0.023 | 0.002 |
| bike_offroad_share | 0.019 | 0.003 |
| betweenness_median_bike | 0.016 | 0.001 |
| edge_length_avg_m_road | 0.015 | 0.002 |
| lts1_coverage | 0.014 | 0.001 |

## 5. UK vs rest of sample (key metrics)

| metric | uk_mean | rest_mean | uk_minus_rest | n_uk | n_rest |
| --- | --- | --- | --- | --- | --- |
| bike_lcc_share_of_road | 0.110 | 0.185 | -0.075 | 76 | 297 |
| bikeable_length_share | 0.379 | 0.454 | -0.075 | 76 | 297 |
| circuity_avg_bike | 1.052 | 1.085 | -0.034 | 76 | 297 |
| components_per_km_bike | 0.631 | 0.705 | -0.074 | 76 | 297 |
| intersection_density_per_km_road | 5.648 | 3.726 | 1.922 | 76 | 297 |
| low_stress_coverage | 0.754 | 0.714 | 0.041 | 76 | 297 |
| meshedness_bike | 0.474 | 0.449 | 0.025 | 76 | 297 |

## 6. Bike vs road network form

`bike_gt_road_share` = fraction of cities where the cycle network exceeds the road network on that metric.

| metric | road_mean | bike_mean | bike_minus_road_mean | bike_gt_road_share | n |
| --- | --- | --- | --- | --- | --- |
| n_nodes | 5368.461 | 3197.917 | -2170.544 | 0.289 | 373 |
| n_edges | 6757.603 | 5904.389 | -853.215 | 0.375 | 373 |
| length_km | 1209.320 | 388.804 | -820.516 | 0.078 | 373 |
| k_avg | 2.558 | 3.595 | 1.038 | 0.989 | 368 |
| intersection_density_per_km | 4.150 | 5.204 | 1.054 | 0.685 | 368 |
| dead_end_proportion | 0.273 | 0.026 | -0.247 | 0.008 | 368 |
| four_way_proportion | 0.102 | 0.632 | 0.530 | 0.997 | 368 |
| circuity_avg | 1.092 | 1.078 | -0.014 | 0.144 | 368 |
| orientation_entropy | 3.501 | 3.420 | -0.081 | 0.239 | 368 |
| lcc_length_share | 0.999 | 0.318 | -0.682 | 0.008 | 368 |
| components_per_km | 0.004 | 0.690 | 0.685 | 1 | 368 |
| self_loop_proportion | 0.002 | 0.001 | -0.001 | 0.101 | 368 |
| betweenness_mean | 0.013 | 0.009 | -0.004 | 0.087 | 367 |
| closeness_mean | 0.000 | 0.000 | 0 | 0.193 | 368 |
| clustering_mean | 0.025 | 0.009 | -0.016 | 0.109 | 367 |

## 7. Network-form typology

Standardise → PCA → k-means. **k=2** (silhouette 0.386); cluster sizes {0: 294, 1: 74}. Profiles are mean standardised (z) values per cluster (features: bikeable_length_share, low_stress_coverage, modal_directness_gap, entropy_gap_kl, bike_lcc_share_of_road, lcc_length_share_bike, circuity_avg_bike, orientation_entropy_bike, intersection_density_per_km_road, orientation_entropy_road, circuity_avg_road):

| type | bikeable_length_share | low_stress_coverage | modal_directness_gap | entropy_gap_kl | bike_lcc_share_of_road | lcc_length_share_bike | circuity_avg_bike | orientation_entropy_bike | intersection_density_per_km_road | orientation_entropy_road | circuity_avg_road |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.220 | 0.370 | 0.190 | -0.230 | 0.130 | 0 | -0.200 | 0.220 | 0.290 | 0.140 | -0.250 |
| 1 | -0.890 | -1.460 | -0.760 | 0.900 | -0.520 | 0 | 0.780 | -0.880 | -1.140 | -0.550 | 1 |

## 8. Grown-network what-if (Tyne & Wear)

Merging each borough's Chapter-5 grown cycle network, then re-measuring.

Predicted cycling rate now vs with the grown network (model fit on the full dataset, borough included):

| place_id | observed | baseline_pred | scenario_pred | shift |
| --- | --- | --- | --- | --- |
| Gateshead, United Kingdom | 1.200 | 2.346 | 6.296 | 3.950 |
| Newcastle upon Tyne, United Kingdom | 2.300 | 2.682 | 5.752 | 3.070 |
| North Tyneside, United Kingdom | 1.900 | 3.301 | 6.269 | 2.968 |
| South Tyneside, United Kingdom | 1.800 | 3.331 | 5.822 | 2.491 |
| Sunderland, United Kingdom | 1.700 | 1.866 | 5.667 | 3.801 |

Out-of-fold predicted rate (each borough held out of training -- the honest estimate):

| place_id | observed | baseline_oof | scenario_oof | shift |
| --- | --- | --- | --- | --- |
| Gateshead, United Kingdom | 1.200 | 2.346 | 6.296 | 3.950 |
| Newcastle upon Tyne, United Kingdom | 2.300 | 3.648 | 5.865 | 2.217 |
| North Tyneside, United Kingdom | 1.900 | 3.300 | 6.269 | 2.968 |
| South Tyneside, United Kingdom | 1.800 | 3.331 | 5.822 | 2.491 |
| Sunderland, United Kingdom | 1.700 | 2.173 | 5.624 | 3.451 |

## 9. Key caveats

- Correlations/predictions are descriptive + predictive, **not causal** (no confounder control yet; that is future work).
- Spearman is primary (cycling rate is skewed); Pearson shown alongside.
- A few metrics (entropy_gap_kl, bike centralities, components_per_km_bike) have extreme values driven by cities with a near-empty cycle network; these are kept (rank-based stats are robust), so plots show real outliers.
- Bike layer is raw OSM; road layer is neatnet-simplified — so raw *count* metrics are comparable within a layer across cities, not bike-vs-road.
- Densities are normalised by network length, not built-up area.
- `n` varies by metric: ~45 places predate newer metrics (fixed by re-running) and some metrics are genuinely undefined (e.g. gini on a single-component network).
