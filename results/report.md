# cycleform — results summary

_Generated 2026-07-23 · metric_version 0.5.0 · snapshot 2025-01-01_

**Study question.** Is the *form/structure* of a city's cycle network (and the road network it sits in) associated with its cycling rate across many cities, and can cycling rate be predicted from network form? Metrics are computed identically on real OSM cities and on Chapter-5 grown networks. This is a descriptive + predictive screen, not causal inference.

## 1. Dataset

- **432 input places** with network metrics computed.
- **425** of them have an observed cycling rate (the modelled sample).
- UK places: **77**.
- Top countries by place count: {'IT': 79, 'UK': 77, 'DE': 72, 'US': 65, 'FR': 65, 'PT': 12, 'BE': 10, 'CH': 9}.

Cycling-rate outcome by source (one preferred source per place, OECD FUA first where a place has several):

| source | places used | years |
| --- | --- | --- |
| OECD FUA (bicycle commute mode share) | 244 | 2005–2024 |
| Eurostat + 2011 UK census (legacy max_value.csv, mixed) | 181 | unspecified |

_Eurostat and the 2011 UK census are combined in the legacy `max_value.csv` (year unspecified) and are not separable within it; supplying them as separate files would let them be reported (and modelled) apart._

## 2. Cycling rate (outcome, % mode share)

- n=425, min=0.0, median=2.9, mean=5.4, max=36.6, sd=6.2.
- Right-skewed; correlations below use Spearman (rank-based, robust).

## 3. Metric correlations with cycling rate

Ranked by |Spearman rho|, top 20 of 67 analysed metrics. `significant` = two-sided p < 0.05. Correlation is a signpost, not a model.

| metric | spearman | spearman_p | pearson | n | significant |
| --- | --- | --- | --- | --- | --- |
| intersection_ratio_bike_road | 0.726 | <0.001 | 0.639 | 425 | yes |
| bikeable_length_share | 0.705 | <0.001 | 0.659 | 425 | yes |
| circuity_avg_bike | -0.613 | <0.001 | -0.232 | 414 | yes |
| bike_lcc_share_of_road | 0.593 | <0.001 | 0.595 | 425 | yes |
| mean_route_lts | -0.589 | <0.001 | -0.474 | 400 | yes |
| intersection_density_km2_bike | 0.579 | <0.001 | 0.393 | 400 | yes |
| entropy_gap_kl | -0.573 | <0.001 | -0.257 | 414 | yes |
| cycle_network_density_km2 | 0.554 | <0.001 | 0.416 | 400 | yes |
| n_nodes_bike | 0.551 | <0.001 | 0.411 | 425 | yes |
| edge_length_avg_m_bike | -0.548 | <0.001 | -0.293 | 414 | yes |
| n_edges_bike | 0.538 | <0.001 | 0.414 | 425 | yes |
| intersection_count_bike | 0.532 | <0.001 | 0.407 | 425 | yes |
| low_stress_route_fraction | 0.530 | <0.001 | 0.570 | 425 | yes |
| n_components_bike | 0.522 | <0.001 | 0.365 | 425 | yes |
| intersection_density_per_km_bike | 0.518 | <0.001 | 0.373 | 414 | yes |
| component_size_gini_bike | 0.471 | <0.001 | 0.451 | 408 | yes |
| lcc_length_km_bike | 0.467 | <0.001 | 0.443 | 400 | yes |
| lts1_coverage | 0.450 | <0.001 | 0.399 | 400 | yes |
| orientation_entropy_bike | 0.418 | <0.001 | 0.248 | 414 | yes |
| orientation_order_bike | -0.418 | <0.001 | -0.300 | 414 | yes |

- Strongest **positive**: intersection_ratio_bike_road, bikeable_length_share, bike_lcc_share_of_road.
- Strongest **negative**: circuity_avg_bike, mean_route_lts, entropy_gap_kl.

## 4. Predictive model (cross-validated)

Out-of-sample R² for three feature sets: network **form** only, **country** (national context) only, and **form+country**. Compares how much network form predicts beyond national context.

| feature_set | model | cv_r2 | cv_r2_sd | cv_rmse | n |
| --- | --- | --- | --- | --- | --- |
| form | elasticnet | 0.537 | 0.072 | 3.119 | 425 |
| form | random_forest | 0.604 | 0.091 | 2.871 | 425 |
| country | elasticnet | 0.450 | 0.081 | 3.396 | 425 |
| country | random_forest | 0.439 | 0.079 | 3.432 | 425 |
| form+country | elasticnet | 0.595 | 0.065 | 2.911 | 425 |
| form+country | random_forest | 0.623 | 0.086 | 2.806 | 425 |

Top 12 network-form predictors (random-forest permutation importance, form-only model):

| metric | importance | importance_sd |
| --- | --- | --- |
| intersection_ratio_bike_road | 0.515 | 0.033 |
| bike_lcc_share_of_road | 0.094 | 0.008 |
| modal_directness_gap | 0.054 | 0.006 |
| bikeable_length_share | 0.048 | 0.002 |
| low_stress_coverage | 0.030 | 0.003 |
| lts1_coverage | 0.030 | 0.003 |
| circuity_avg_bike | 0.028 | 0.003 |
| components_per_km_bike | 0.022 | 0.003 |
| bike_offroad_share | 0.022 | 0.002 |
| edge_length_avg_m_road | 0.016 | 0.002 |
| entropy_gap_kl | 0.014 | 0.002 |
| low_stress_route_fraction | 0.013 | 0.001 |

## 5. UK vs rest of sample (key metrics)

| metric | uk_mean | rest_mean | uk_minus_rest | n_uk | n_rest |
| --- | --- | --- | --- | --- | --- |
| bike_lcc_share_of_road | 0.110 | 0.169 | -0.059 | 77 | 355 |
| bikeable_length_share | 0.379 | 0.420 | -0.041 | 77 | 355 |
| circuity_avg_bike | 1.052 | 1.090 | -0.038 | 77 | 355 |
| components_per_km_bike | 0.632 | 0.674 | -0.042 | 77 | 355 |
| intersection_density_per_km_road | 5.649 | 3.712 | 1.937 | 77 | 355 |
| low_stress_coverage | 0.758 | 0.724 | 0.034 | 77 | 355 |
| meshedness_bike | 0.473 | 0.454 | 0.019 | 77 | 355 |

## 6. Bike vs road network form

`bike_gt_road_share` = fraction of cities where the cycle network exceeds the road network on that metric.

| metric | road_mean | bike_mean | bike_minus_road_mean | bike_gt_road_share | n |
| --- | --- | --- | --- | --- | --- |
| n_nodes | 5800.792 | 3260.894 | -2539.898 | 0.259 | 432 |
| n_edges | 7422.657 | 6014.553 | -1408.104 | 0.349 | 432 |
| length_km | 1289.979 | 397.263 | -892.717 | 0.067 | 432 |
| k_avg | 2.570 | 3.612 | 1.042 | 0.986 | 421 |
| intersection_density_per_km | 4.094 | 5.118 | 1.023 | 0.675 | 421 |
| dead_end_proportion | 0.270 | 0.025 | -0.245 | 0.007 | 421 |
| four_way_proportion | 0.108 | 0.637 | 0.529 | 0.998 | 421 |
| circuity_avg | 1.091 | 1.083 | -0.008 | 0.190 | 421 |
| orientation_entropy | 3.479 | 3.402 | -0.077 | 0.271 | 421 |
| lcc_length_share | 0.999 | 0.317 | -0.682 | 0.009 | 421 |
| components_per_km | 0.005 | 0.667 | 0.662 | 1 | 421 |
| self_loop_proportion | 0.002 | 0.001 | -0.001 | 0.126 | 421 |
| betweenness_mean | 0.013 | 0.010 | -0.003 | 0.100 | 420 |
| closeness_mean | 0.000 | 0.000 | 0 | 0.195 | 421 |
| clustering_mean | 0.025 | 0.010 | -0.015 | 0.121 | 420 |

## 7. Network-form typology

Standardise → PCA → k-means. **k=2** (silhouette 0.368); cluster sizes {0: 83, 1: 338}. Profiles are mean standardised (z) values per cluster (features: bikeable_length_share, low_stress_coverage, modal_directness_gap, entropy_gap_kl, bike_lcc_share_of_road, lcc_length_share_bike, circuity_avg_bike, orientation_entropy_bike, intersection_density_per_km_road, orientation_entropy_road, circuity_avg_road):

| type | bikeable_length_share | low_stress_coverage | modal_directness_gap | entropy_gap_kl | bike_lcc_share_of_road | lcc_length_share_bike | circuity_avg_bike | orientation_entropy_bike | intersection_density_per_km_road | orientation_entropy_road | circuity_avg_road |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | -0.870 | -1.350 | -0.780 | 1.020 | -0.480 | 0.160 | 0.750 | -1.030 | -1.020 | -0.440 | 1 |
| 1 | 0.210 | 0.330 | 0.190 | -0.250 | 0.120 | -0.040 | -0.180 | 0.250 | 0.250 | 0.110 | -0.240 |

## 8. Grown-network what-if (Tyne & Wear)

Merging each borough's Chapter-5 grown cycle network, then re-measuring.

Predicted cycling rate now vs with the grown network (model fit on the full dataset, borough included):

| place_id | observed | baseline_pred | scenario_pred | shift |
| --- | --- | --- | --- | --- |
| Gateshead, United Kingdom | 1.200 | 2.638 | 5.874 | 3.236 |
| Newcastle upon Tyne, United Kingdom | 2.300 | 2.882 | 5.473 | 2.591 |
| North Tyneside, United Kingdom | 1.900 | 3.246 | 5.747 | 2.501 |
| South Tyneside, United Kingdom | 1.800 | 3.177 | 5.316 | 2.139 |
| Sunderland, United Kingdom | 1.700 | 1.907 | 5.261 | 3.353 |

Out-of-fold predicted rate (each borough held out of training -- the honest estimate):

| place_id | observed | baseline_oof | scenario_oof | shift |
| --- | --- | --- | --- | --- |
| Gateshead, United Kingdom | 1.200 | 2.638 | 5.874 | 3.236 |
| Newcastle upon Tyne, United Kingdom | 2.300 | 3.373 | 5.460 | 2.087 |
| North Tyneside, United Kingdom | 1.900 | 3.246 | 5.747 | 2.501 |
| South Tyneside, United Kingdom | 1.800 | 3.177 | 5.316 | 2.139 |
| Sunderland, United Kingdom | 1.700 | 2.158 | 5.294 | 3.136 |

## 9. Key caveats

- Correlations/predictions are descriptive + predictive, **not causal** (no confounder control yet; that is future work).
- Spearman is primary (cycling rate is skewed); Pearson shown alongside.
- A few metrics (entropy_gap_kl, bike centralities, components_per_km_bike) have extreme values driven by cities with a near-empty cycle network; these are kept (rank-based stats are robust), so plots show real outliers.
- Bike layer is raw OSM; road layer is neatnet-simplified — so raw *count* metrics are comparable within a layer across cities, not bike-vs-road.
- Densities are normalised by network length, not built-up area.
- `n` varies by metric: ~45 places predate newer metrics (fixed by re-running) and some metrics are genuinely undefined (e.g. gini on a single-component network).
