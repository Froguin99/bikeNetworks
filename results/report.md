# cycleform — results summary

_Generated 2026-07-27 · metric_version 0.5.0 · snapshot 2025-01-01_

**Study question.** Is the *form/structure* of a city's cycle network (and the road network it sits in) associated with its cycling rate across many cities, and can cycling rate be predicted from network form? Metrics are computed identically on real OSM cities and on Chapter-5 grown networks. This is a descriptive + predictive screen, not causal inference.

## 1. Dataset

- **1137 input places** with network metrics computed.
- **1132** of them have an observed cycling rate (the modelled sample).
- UK places: **123**.
- Top countries by place count: {'US': 338, 'DE': 150, 'UK': 123, 'IT': 91, 'FR': 85, 'NL': 34, 'ES': 26, 'CA': 25}.

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
| bikeable_length_share | 0.650 | <0.001 | 0.567 | 1132 | yes |
| intersection_ratio_bike_road | 0.640 | <0.001 | 0.466 | 1132 | yes |
| circuity_avg_bike | -0.570 | <0.001 | -0.206 | 1093 | yes |
| entropy_gap_kl | -0.551 | <0.001 | -0.214 | 1093 | yes |
| bike_lcc_share_of_road | 0.545 | <0.001 | 0.491 | 1132 | yes |
| intersection_density_km2_bike | 0.525 | <0.001 | 0.419 | 1132 | yes |
| cycle_network_density_km2 | 0.502 | <0.001 | 0.446 | 1132 | yes |
| n_components_bike | 0.496 | <0.001 | 0.253 | 1132 | yes |
| n_nodes_bike | 0.487 | <0.001 | 0.276 | 1132 | yes |
| edge_length_avg_m_bike | -0.485 | <0.001 | -0.237 | 1093 | yes |
| n_edges_bike | 0.471 | <0.001 | 0.256 | 1132 | yes |
| intersection_count_bike | 0.461 | <0.001 | 0.233 | 1132 | yes |
| mean_route_lts | -0.447 | <0.001 | -0.372 | 1132 | yes |
| orientation_order_bike | -0.440 | <0.001 | -0.256 | 1093 | yes |
| orientation_entropy_bike | 0.440 | <0.001 | 0.206 | 1093 | yes |
| intersection_density_per_km_bike | 0.433 | <0.001 | 0.290 | 1093 | yes |
| three_way_proportion_bike | 0.426 | <0.001 | 0.305 | 1093 | yes |
| component_size_gini_bike | 0.414 | <0.001 | 0.351 | 1075 | yes |
| orientation_entropy_road | 0.406 | <0.001 | 0.304 | 1132 | yes |
| orientation_order_road | -0.406 | <0.001 | -0.315 | 1132 | yes |

- Strongest **positive**: bikeable_length_share, intersection_ratio_bike_road, bike_lcc_share_of_road.
- Strongest **negative**: circuity_avg_bike, entropy_gap_kl, edge_length_avg_m_bike.

## 4. Predictive model (cross-validated)

Out-of-sample R² for three feature sets: network **form** only, **country** (national context) only, and **form+country**. Compares how much network form predicts beyond national context.

| feature_set | model | cv_r2 | cv_r2_sd | cv_rmse | n |
| --- | --- | --- | --- | --- | --- |
| form | elasticnet | 0.483 | 0.034 | 5.468 | 1132 |
| form | random_forest | 0.606 | 0.036 | 4.768 | 1132 |
| country | elasticnet | 0.614 | 0.029 | 4.730 | 1132 |
| country | random_forest | 0.616 | 0.029 | 4.713 | 1132 |
| form+country | elasticnet | 0.641 | 0.012 | 4.561 | 1132 |
| form+country | random_forest | 0.670 | 0.015 | 4.368 | 1132 |

Top 12 network-form predictors (random-forest permutation importance, form-only model):

| metric | importance | importance_sd |
| --- | --- | --- |
| bikeable_length_share | 0.596 | 0.027 |
| meshedness_bike | 0.100 | 0.009 |
| circuity_avg_bike | 0.098 | 0.007 |
| modal_directness_gap | 0.087 | 0.008 |
| intersection_ratio_bike_road | 0.082 | 0.006 |
| bike_offroad_share | 0.046 | 0.005 |
| street_density_km2 | 0.022 | 0.001 |
| orientation_order_road | 0.017 | 0.002 |
| lts1_coverage | 0.017 | 0.002 |
| low_stress_coverage | 0.016 | 0.001 |
| circuity_avg_road | 0.015 | 0.002 |
| connectivity_ratio_bike | 0.014 | 0.002 |

## 5. UK vs rest of sample

**Cycling rate.** UK n=122, median 2.3% / mean 3.1%; rest median 1.9% / mean 5.7%. UK is middling and compressed (max 32% vs 49%): it lacks both the near-zero and the very-high tails.

**Network form (key metrics).** Similar bikeable *share*, but the UK cycle network is more fragmented and less connected:

| metric | uk_mean | rest_mean | uk_minus_rest | n_uk | n_rest |
| --- | --- | --- | --- | --- | --- |
| bike_lcc_share_of_road | 0.102 | 0.159 | -0.056 | 123 | 1014 |
| bikeable_length_share | 0.349 | 0.362 | -0.013 | 123 | 1014 |
| circuity_avg_bike | 1.052 | 1.083 | -0.032 | 123 | 1014 |
| components_per_km_bike | 0.617 | 0.638 | -0.022 | 123 | 1014 |
| intersection_density_per_km_road | 5.739 | 3.712 | 2.027 | 123 | 1014 |
| low_stress_coverage | 0.761 | 0.764 | -0.003 | 123 | 1014 |
| meshedness_bike | 0.471 | 0.466 | 0.005 | 123 | 1014 |

**Different trends?** Spearman(metric, cycling) computed *within* the UK vs *within* the rest -- the UK relationships are markedly weaker (partly restriction of range, as the UK spans a narrower band of both form and rate):

| metric | rho_uk | rho_rest | diff | n_uk |
| --- | --- | --- | --- | --- |
| bikeable_length_share | 0.220 | 0.654 | -0.433 | 122 |
| intersection_ratio_bike_road | 0.407 | 0.644 | -0.237 | 122 |
| bike_lcc_share_of_road | 0.277 | 0.558 | -0.280 | 122 |
| cycle_network_density_km2 | 0.239 | 0.508 | -0.269 | 122 |
| circuity_avg_bike | -0.391 | -0.572 | 0.181 | 122 |
| modal_directness_gap | -0.258 | -0.401 | 0.143 | 122 |

**Implementation gap.** Fitting cycling ~ bikeable_share on the rest (slope 13.0) and applying it to UK provision predicts 5.6% for the UK, but the UK observes 3.1% -- it cycles **-2.4 pp** relative to what its provision predicts. See `implementation_gap_by_country.png` for the full-form, per-country version.

## 6. Bike vs road network form

`bike_gt_road_share` = fraction of cities where the cycle network exceeds the road network on that metric.

| metric | road_mean | bike_mean | bike_minus_road_mean | bike_gt_road_share | n |
| --- | --- | --- | --- | --- | --- |
| n_nodes | 5564.025 | 2694.846 | -2869.178 | 0.223 | 1137 |
| n_edges | 7393.288 | 5009.944 | -2383.345 | 0.312 | 1137 |
| length_km | 1156.814 | 331.069 | -825.745 | 0.049 | 1137 |
| k_avg | 2.645 | 3.643 | 0.997 | 0.971 | 1098 |
| intersection_density_per_km | 3.969 | 4.863 | 0.894 | 0.649 | 1098 |
| dead_end_proportion | 0.248 | 0.020 | -0.228 | 0.006 | 1098 |
| four_way_proportion | 0.139 | 0.655 | 0.516 | 0.988 | 1098 |
| circuity_avg | 1.084 | 1.080 | -0.004 | 0.273 | 1098 |
| orientation_entropy | 3.410 | 3.332 | -0.078 | 0.328 | 1098 |
| lcc_length_share | 0.999 | 0.365 | -0.635 | 0.007 | 1098 |
| components_per_km | 0.004 | 0.636 | 0.631 | 1 | 1098 |
| self_loop_proportion | 0.002 | 0.001 | -0.001 | 0.147 | 1098 |
| betweenness_mean | 0.014 | 0.013 | -0.001 | 0.186 | 1094 |
| closeness_mean | 0.000 | 0.000 | 0.000 | 0.272 | 1098 |
| clustering_mean | 0.026 | 0.011 | -0.016 | 0.103 | 1094 |

## 7. Network-form typology

Standardise → PCA → k-means. **k=3** (silhouette 0.26); cluster sizes {0: 92, 1: 817, 2: 189}. Profiles are mean standardised (z) values per cluster (features: bikeable_length_share, low_stress_coverage, modal_directness_gap, entropy_gap_kl, bike_lcc_share_of_road, lcc_length_share_bike, circuity_avg_bike, orientation_entropy_bike, intersection_density_per_km_road, orientation_entropy_road, circuity_avg_road):

| type | bikeable_length_share | low_stress_coverage | modal_directness_gap | entropy_gap_kl | bike_lcc_share_of_road | lcc_length_share_bike | circuity_avg_bike | orientation_entropy_bike | intersection_density_per_km_road | orientation_entropy_road | circuity_avg_road |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | -0.960 | -0.380 | -0.640 | 2.570 | -0.500 | 1.230 | 0.430 | -2.620 | -0.330 | -0.880 | 0.100 |
| 1 | -0.250 | -0.040 | 0.280 | -0.180 | -0.340 | -0.410 | 0.030 | 0.210 | 0.050 | 0.020 | -0.020 |
| 2 | 1.560 | 0.370 | -0.910 | -0.460 | 1.710 | 1.170 | -0.350 | 0.390 | -0.050 | 0.320 | 0.040 |

## 8. Grown-network what-if (Tyne & Wear)

Merging each borough's Chapter-5 grown cycle network, then re-measuring.

Predicted cycling rate now vs with the grown network (model fit on the full dataset, borough included):

| place_id | observed | baseline_pred | scenario_pred | shift |
| --- | --- | --- | --- | --- |
| Gateshead, United Kingdom | 1.509 | 1.868 | 18.094 | 16.226 |
| Newcastle upon Tyne, United Kingdom | 2.300 | 2.496 | 16.098 | 13.602 |
| North Tyneside, United Kingdom | 2.629 | 4.350 | 18.544 | 14.194 |
| South Tyneside, United Kingdom | 2.347 | 3.024 | 16.643 | 13.619 |
| Sunderland, United Kingdom | 1.413 | 1.638 | 16.492 | 14.854 |

Out-of-fold predicted rate (each borough held out of training -- the honest estimate):

| place_id | observed | baseline_oof | scenario_oof | shift |
| --- | --- | --- | --- | --- |
| Gateshead, United Kingdom | 1.509 | 2.740 | 18.038 | 15.298 |
| Newcastle upon Tyne, United Kingdom | 2.300 | 3.132 | 15.931 | 12.799 |
| North Tyneside, United Kingdom | 2.629 | 5.553 | 18.268 | 12.714 |
| South Tyneside, United Kingdom | 2.347 | 4.679 | 16.585 | 11.906 |
| Sunderland, United Kingdom | 1.413 | 2.186 | 16.916 | 14.730 |

## 9. Key caveats

- Correlations/predictions are descriptive + predictive, **not causal** (no confounder control yet; that is future work).
- Spearman is primary (cycling rate is skewed); Pearson shown alongside.
- A few metrics (entropy_gap_kl, bike centralities, components_per_km_bike) have extreme values driven by cities with a near-empty cycle network; these are kept (rank-based stats are robust), so plots show real outliers.
- Bike layer is raw OSM; road layer is neatnet-simplified — so raw *count* metrics are comparable within a layer across cities, not bike-vs-road.
- Densities are normalised by network length, not built-up area.
- `n` varies by metric: ~45 places predate newer metrics (fixed by re-running) and some metrics are genuinely undefined (e.g. gini on a single-component network).
