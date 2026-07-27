# cycleform — results summary

_Generated 2026-07-26 · metric_version 0.5.0 · snapshot 2025-01-01_

**Study question.** Is the *form/structure* of a city's cycle network (and the road network it sits in) associated with its cycling rate across many cities, and can cycling rate be predicted from network form? Metrics are computed identically on real OSM cities and on Chapter-5 grown networks. This is a descriptive + predictive screen, not causal inference.

## 1. Dataset

- **1163 input places** with network metrics computed.
- **1132** of them have an observed cycling rate (the modelled sample).
- UK places: **127**.
- Top countries by place count: {'US': 338, 'DE': 161, 'UK': 127, 'IT': 92, 'FR': 89, 'NL': 34, 'ES': 26, 'CA': 25}.

Cycling-rate outcome by source (one preferred source per place, ModalShare first, then OECD FUA, then legacy):

| source | places used | years |
| --- | --- | --- |
| ModalShare (Prieto-Curiel et al.; commute cycling share) | 935 | 1991–2024 |
| OECD FUA (bicycle commute mode share) | 193 | 2005–2024 |
| Eurostat + 2011 UK census (legacy max_value.csv, mixed) | 4 | unspecified |

_All three sources measure commute-to-work cycling share. ModalShare is a harmonised multi-source dataset and takes priority; OECD FUA and the legacy max_value.csv (mixed Eurostat + 2011 UK census, year unspecified) fill the places ModalShare doesn't cover._

## 2. Cycling rate (outcome, % mode share)

- n=1132, min=0.0, median=2.0, mean=5.4, max=49.5, sd=7.6.
- Right-skewed; correlations below use Spearman (rank-based, robust).

## 3. Metric correlations with cycling rate

Ranked by |Spearman rho|, top 20 of 67 analysed metrics. `significant` = two-sided p < 0.05. Correlation is a signpost, not a model.

| metric | spearman | spearman_p | pearson | n | significant |
| --- | --- | --- | --- | --- | --- |
| bikeable_length_share | 0.644 | <0.001 | 0.559 | 1132 | yes |
| intersection_ratio_bike_road | 0.633 | <0.001 | 0.461 | 1132 | yes |
| circuity_avg_bike | -0.572 | <0.001 | -0.201 | 1090 | yes |
| entropy_gap_kl | -0.547 | <0.001 | -0.212 | 1090 | yes |
| bike_lcc_share_of_road | 0.539 | <0.001 | 0.483 | 1132 | yes |
| intersection_density_km2_bike | 0.518 | <0.001 | 0.408 | 1132 | yes |
| cycle_network_density_km2 | 0.495 | <0.001 | 0.435 | 1132 | yes |
| n_components_bike | 0.489 | <0.001 | 0.248 | 1132 | yes |
| edge_length_avg_m_bike | -0.483 | <0.001 | -0.237 | 1090 | yes |
| n_nodes_bike | 0.479 | <0.001 | 0.269 | 1132 | yes |
| n_edges_bike | 0.464 | <0.001 | 0.250 | 1132 | yes |
| intersection_count_bike | 0.453 | <0.001 | 0.228 | 1132 | yes |
| mean_route_lts | -0.439 | <0.001 | -0.358 | 1132 | yes |
| orientation_order_bike | -0.435 | <0.001 | -0.253 | 1090 | yes |
| orientation_entropy_bike | 0.435 | <0.001 | 0.203 | 1090 | yes |
| intersection_density_per_km_bike | 0.431 | <0.001 | 0.288 | 1090 | yes |
| three_way_proportion_bike | 0.425 | <0.001 | 0.304 | 1090 | yes |
| component_size_gini_bike | 0.410 | <0.001 | 0.348 | 1071 | yes |
| orientation_entropy_road | 0.401 | <0.001 | 0.295 | 1132 | yes |
| orientation_order_road | -0.401 | <0.001 | -0.308 | 1132 | yes |

- Strongest **positive**: bikeable_length_share, intersection_ratio_bike_road, bike_lcc_share_of_road.
- Strongest **negative**: circuity_avg_bike, entropy_gap_kl, edge_length_avg_m_bike.

## 4. Predictive model (cross-validated)

Out-of-sample R² for three feature sets: network **form** only, **country** (national context) only, and **form+country**. Compares how much network form predicts beyond national context.

| feature_set | model | cv_r2 | cv_r2_sd | cv_rmse | n |
| --- | --- | --- | --- | --- | --- |
| form | elasticnet | 0.449 | 0.045 | 5.645 | 1132 |
| form | random_forest | 0.604 | 0.035 | 4.778 | 1132 |
| country | elasticnet | 0.614 | 0.029 | 4.730 | 1132 |
| country | random_forest | 0.616 | 0.029 | 4.713 | 1132 |
| form+country | elasticnet | 0.605 | 0.041 | 4.774 | 1132 |
| form+country | random_forest | 0.665 | 0.021 | 4.404 | 1132 |

Top 12 network-form predictors (random-forest permutation importance, form-only model):

| metric | importance | importance_sd |
| --- | --- | --- |
| bikeable_length_share | 0.613 | 0.028 |
| modal_directness_gap | 0.113 | 0.012 |
| meshedness_bike | 0.092 | 0.008 |
| circuity_avg_bike | 0.090 | 0.007 |
| intersection_ratio_bike_road | 0.074 | 0.005 |
| bike_offroad_share | 0.047 | 0.005 |
| street_density_km2 | 0.021 | 0.001 |
| circuity_avg_road | 0.019 | 0.002 |
| lts1_coverage | 0.017 | 0.002 |
| connectivity_ratio_bike | 0.016 | 0.002 |
| low_stress_coverage | 0.015 | 0.001 |
| orientation_order_road | 0.015 | 0.002 |

## 5. UK vs rest of sample (key metrics)

| metric | uk_mean | rest_mean | uk_minus_rest | n_uk | n_rest |
| --- | --- | --- | --- | --- | --- |
| bike_lcc_share_of_road | 0.102 | 0.162 | -0.061 | 127 | 1036 |
| bikeable_length_share | 0.346 | 0.367 | -0.021 | 127 | 1036 |
| circuity_avg_bike | 1.051 | 1.084 | -0.033 | 127 | 1036 |
| components_per_km_bike | 0.614 | 0.639 | -0.025 | 127 | 1036 |
| intersection_density_per_km_road | 5.727 | 3.705 | 2.022 | 127 | 1036 |
| low_stress_coverage | 0.759 | 0.763 | -0.004 | 127 | 1036 |
| meshedness_bike | 0.471 | 0.466 | 0.005 | 127 | 1036 |

## 6. Bike vs road network form

`bike_gt_road_share` = fraction of cities where the cycle network exceeds the road network on that metric.

| metric | road_mean | bike_mean | bike_minus_road_mean | bike_gt_road_share | n |
| --- | --- | --- | --- | --- | --- |
| n_nodes | 5499.411 | 2711.684 | -2787.727 | 0.229 | 1163 |
| n_edges | 7301.937 | 5047.230 | -2254.707 | 0.318 | 1163 |
| length_km | 1143.628 | 332.192 | -811.436 | 0.053 | 1163 |
| k_avg | 2.643 | 3.643 | 1.000 | 0.971 | 1121 |
| intersection_density_per_km | 3.966 | 4.872 | 0.906 | 0.652 | 1121 |
| dead_end_proportion | 0.249 | 0.020 | -0.229 | 0.006 | 1121 |
| four_way_proportion | 0.138 | 0.654 | 0.516 | 0.988 | 1121 |
| circuity_avg | 1.085 | 1.080 | -0.004 | 0.269 | 1121 |
| orientation_entropy | 3.412 | 3.333 | -0.079 | 0.326 | 1121 |
| lcc_length_share | 0.999 | 0.366 | -0.633 | 0.007 | 1121 |
| components_per_km | 0.004 | 0.636 | 0.632 | 1 | 1121 |
| self_loop_proportion | 0.002 | 0.001 | -0.001 | 0.147 | 1121 |
| betweenness_mean | 0.014 | 0.013 | -0.001 | 0.182 | 1116 |
| closeness_mean | 0.000 | 0.000 | 0.000 | 0.269 | 1121 |
| clustering_mean | 0.026 | 0.011 | -0.016 | 0.102 | 1116 |

## 7. Network-form typology

Standardise → PCA → k-means. **k=3** (silhouette 0.262); cluster sizes {0: 198, 1: 826, 2: 97}. Profiles are mean standardised (z) values per cluster (features: bikeable_length_share, low_stress_coverage, modal_directness_gap, entropy_gap_kl, bike_lcc_share_of_road, lcc_length_share_bike, circuity_avg_bike, orientation_entropy_bike, intersection_density_per_km_road, orientation_entropy_road, circuity_avg_road):

| type | bikeable_length_share | low_stress_coverage | modal_directness_gap | entropy_gap_kl | bike_lcc_share_of_road | lcc_length_share_bike | circuity_avg_bike | orientation_entropy_bike | intersection_density_per_km_road | orientation_entropy_road | circuity_avg_road |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1.540 | 0.350 | -0.910 | -0.450 | 1.680 | 1.160 | -0.340 | 0.380 | -0.080 | 0.320 | 0.050 |
| 1 | -0.260 | -0.050 | 0.290 | -0.190 | -0.340 | -0.420 | 0 | 0.210 | 0.060 | 0.040 | -0.020 |
| 2 | -0.970 | -0.300 | -0.580 | 2.510 | -0.500 | 1.230 | 0.680 | -2.540 | -0.310 | -0.990 | 0.080 |

## 8. Grown-network what-if (Tyne & Wear)

Merging each borough's Chapter-5 grown cycle network, then re-measuring.

Predicted cycling rate now vs with the grown network (model fit on the full dataset, borough included):

| place_id | observed | baseline_pred | scenario_pred | shift |
| --- | --- | --- | --- | --- |
| Gateshead, United Kingdom | 1.509 | 1.922 | 17.522 | 15.600 |
| Newcastle upon Tyne, United Kingdom | 2.300 | 2.547 | 14.193 | 11.647 |
| North Tyneside, United Kingdom | 2.629 | 4.461 | 17.697 | 13.236 |
| South Tyneside, United Kingdom | 2.347 | 3.186 | 15.051 | 11.864 |
| Sunderland, United Kingdom | 1.413 | 1.775 | 15.735 | 13.961 |

Out-of-fold predicted rate (each borough held out of training -- the honest estimate):

| place_id | observed | baseline_oof | scenario_oof | shift |
| --- | --- | --- | --- | --- |
| Gateshead, United Kingdom | 1.509 | 2.827 | 18.106 | 15.280 |
| Newcastle upon Tyne, United Kingdom | 2.300 | 2.989 | 13.972 | 10.984 |
| North Tyneside, United Kingdom | 2.629 | 6.342 | 18.303 | 11.961 |
| South Tyneside, United Kingdom | 2.347 | 4.893 | 15.741 | 10.848 |
| Sunderland, United Kingdom | 1.413 | 2.117 | 17.155 | 15.038 |

## 9. Key caveats

- Correlations/predictions are descriptive + predictive, **not causal** (no confounder control yet; that is future work).
- Spearman is primary (cycling rate is skewed); Pearson shown alongside.
- A few metrics (entropy_gap_kl, bike centralities, components_per_km_bike) have extreme values driven by cities with a near-empty cycle network; these are kept (rank-based stats are robust), so plots show real outliers.
- Bike layer is raw OSM; road layer is neatnet-simplified — so raw *count* metrics are comparable within a layer across cities, not bike-vs-road.
- Densities are normalised by network length, not built-up area.
- `n` varies by metric: ~45 places predate newer metrics (fixed by re-running) and some metrics are genuinely undefined (e.g. gini on a single-component network).
