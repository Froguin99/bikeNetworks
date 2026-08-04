# cycleform — results summary

_Generated 2026-08-04 · metric_version 0.5.0 · snapshot 2025-01-01_

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

Cycling rate by country (every country; one row per place, preferred source; sorted by mean). Small-n means are noisy -- read with the `n` column:

| country | n | mean | median |
| --- | --- | --- | --- |
| AL | 1 | 29 | 29 |
| NL | 33 | 28.200 | 27.700 |
| GR | 2 | 22.500 | 22.500 |
| DK | 7 | 19.200 | 17.800 |
| SE | 12 | 17 | 17.500 |
| FI | 10 | 15 | 14 |
| AT | 9 | 14.700 | 15 |
| IL | 1 | 13 | 13 |
| DE | 150 | 12.900 | 11.200 |
| BE | 15 | 11.500 | 11 |
| CH | 11 | 10.600 | 9.100 |
| BG | 18 | 9.700 | 9.500 |
| MZ | 1 | 9 | 9 |
| BD | 1 | 8 | 8 |
| SI | 5 | 7 | 8 |
| CL | 18 | 7 | 6.700 |
| CZ | 16 | 6.200 | 2.400 |
| NO | 18 | 5.700 | 5 |
| LV | 3 | 5.700 | 5 |
| IN | 5 | 5.600 | 3 |
| SK | 8 | 5.600 | 4.900 |
| AR | 2 | 4.900 | 4.900 |
| PL | 6 | 4.500 | 4.400 |
| HU | 5 | 4.400 | 3 |
| IT | 90 | 4.400 | 2.900 |
| IE | 5 | 4.100 | 3 |
| FR | 85 | 4 | 3.400 |
| TW | 1 | 4 | 4 |
| BR | 3 | 4 | 4 |
| NZ | 5 | 4 | 2.200 |
| EE | 2 | 3.800 | 3.800 |
| UK | 122 | 3.100 | 2.300 |
| CO | 3 | 3.100 | 1 |
| RO | 1 | 2 | 2 |
| PH | 1 | 2 | 2 |
| KO | 20 | 1.900 | 1.300 |
| UY | 1 | 1.700 | 1.700 |
| ES | 26 | 1.700 | 0.700 |
| CA | 25 | 1.500 | 1 |
| LT | 3 | 1.300 | 1 |
| AU | 9 | 1 | 1 |
| BY | 1 | 1 | 1 |
| SG | 1 | 1 | 1 |
| UA | 1 | 1 | 1 |
| HR | 1 | 1 | 1 |
| GH | 1 | 1 | 1 |
| MY | 1 | 1 | 1 |
| CY | 1 | 1 | 1 |
| PT | 24 | 0.900 | 0.700 |
| US | 337 | 0.600 | 0.300 |
| HK | 1 | 0.500 | 0.500 |

## 3. Metric correlations with cycling rate

Ranked by |Spearman rho|, all of 67 analysed metrics. `significant` = two-sided p < 0.05. Correlation is a signpost, not a model.

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
| low_stress_route_fraction | 0.403 | <0.001 | 0.483 | 1132 | yes |
| modal_directness_gap | -0.384 | <0.001 | -0.370 | 1132 | yes |
| lcc_length_km_bike | 0.375 | <0.001 | 0.285 | 1132 | yes |
| length_km_bike | 0.371 | <0.001 | 0.208 | 1132 | yes |
| four_way_proportion_road | -0.368 | <0.001 | -0.243 | 1132 | yes |
| lts2_coverage | -0.351 | <0.001 | -0.245 | 1132 | yes |
| meshedness_bike | -0.341 | <0.001 | -0.200 | 1089 | yes |
| bike_offroad_share | -0.333 | <0.001 | -0.121 | 1093 | yes |
| three_way_proportion_road | 0.318 | <0.001 | 0.263 | 1132 | yes |
| dead_end_proportion_bike | 0.309 | <0.001 | 0.121 | 1093 | yes |
| connectivity_ratio_road | -0.294 | <0.001 | -0.151 | 1132 | yes |
| meshedness_road | -0.292 | <0.001 | -0.149 | 1132 | yes |
| connectivity_ratio_bike | -0.289 | <0.001 | -0.169 | 1089 | yes |
| k_avg_road | -0.281 | <0.001 | -0.142 | 1132 | yes |
| four_way_proportion_bike | -0.266 | <0.001 | -0.186 | 1093 | yes |
| components_per_km_bike | 0.261 | <0.001 | 0.024 | 1093 | yes |
| lts1_coverage | 0.246 | <0.001 | 0.216 | 1132 | yes |
| k_avg_bike | -0.223 | <0.001 | -0.117 | 1093 | yes |
| dead_end_proportion_road | 0.213 | <0.001 | 0.075 | 1132 | yes |
| closeness_mean_bike | -0.203 | <0.001 | -0.052 | 1093 | yes |
| betweenness_median_bike | -0.198 | <0.001 | -0.094 | 1089 | yes |
| intersection_density_per_km_road | 0.195 | <0.001 | 0.049 | 1132 | yes |
| clustering_mean_bike | -0.192 | <0.001 | -0.125 | 1089 | yes |
| edge_length_avg_m_road | -0.181 | <0.001 | -0.062 | 1132 | yes |
| circuity_avg_road | 0.164 | <0.001 | 0.042 | 1132 | yes |
| self_loop_proportion_bike | -0.148 | <0.001 | -0.122 | 1093 | yes |
| lcc_length_km_road | -0.142 | <0.001 | -0.137 | 1132 | yes |
| length_km_road | -0.142 | <0.001 | -0.137 | 1132 | yes |
| closeness_median_bike | -0.120 | <0.001 | -0.041 | 1093 | yes |
| street_density_km2 | -0.114 | <0.001 | -0.097 | 1132 | yes |
| closeness_median_road | 0.113 | <0.001 | -0.049 | 1132 | yes |
| closeness_mean_road | 0.112 | <0.001 | -0.051 | 1132 | yes |
| n_edges_road | -0.102 | <0.001 | -0.126 | 1132 | yes |
| intersection_count_road | -0.100 | <0.001 | -0.123 | 1132 | yes |
| component_size_gini_road | -0.096 | 0.025 | -0.034 | 548 | yes |
| components_per_km_road | 0.093 | 0.002 | -0.058 | 1132 | yes |
| low_stress_coverage | -0.090 | 0.003 | 0.004 | 1132 | yes |
| self_loop_proportion_road | 0.085 | 0.004 | 0.051 | 1132 | yes |
| n_nodes_road | -0.077 | 0.010 | -0.121 | 1132 | yes |
| lcc_length_share_bike | 0.071 | 0.018 | 0.222 | 1093 | yes |
| betweenness_mean_bike | -0.059 | 0.053 | -0.089 | 1089 | no |
| betweenness_median_road | -0.050 | 0.093 | -0.104 | 1132 | no |
| betweenness_mean_road | 0.043 | 0.145 | -0.074 | 1132 | no |
| n_components_road | -0.030 | 0.309 | -0.046 | 1132 | no |
| lcc_length_share_road | -0.027 | 0.366 | -0.074 | 1132 | no |
| intersection_density_km2_road | -0.022 | 0.452 | -0.041 | 1132 | no |
| clustering_mean_road | -0.021 | 0.481 | 0.010 | 1132 | no |

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

Network-form predictors (67 shown; random-forest permutation importance, form-only model):

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
| four_way_proportion_bike | 0.014 | 0.001 |
| orientation_entropy_road | 0.014 | 0.001 |
| three_way_proportion_bike | 0.011 | 0.001 |
| four_way_proportion_road | 0.010 | 0.001 |
| bike_lcc_share_of_road | 0.010 | 0.000 |
| low_stress_route_fraction | 0.009 | 0.000 |
| edge_length_avg_m_road | 0.009 | 0.001 |
| components_per_km_bike | 0.009 | 0.001 |
| dead_end_proportion_bike | 0.008 | 0.001 |
| clustering_mean_road | 0.007 | 0.001 |
| k_avg_bike | 0.007 | 0.001 |
| entropy_gap_kl | 0.007 | 0.000 |
| three_way_proportion_road | 0.007 | 0.001 |
| lcc_length_share_bike | 0.007 | 0.001 |
| intersection_density_per_km_bike | 0.007 | 0.001 |
| clustering_mean_bike | 0.007 | 0.001 |
| intersection_density_km2_road | 0.007 | 0.000 |
| component_size_gini_bike | 0.006 | 0.000 |
| betweenness_mean_bike | 0.006 | 0.001 |
| intersection_density_per_km_road | 0.006 | 0.000 |
| closeness_mean_road | 0.006 | 0.000 |
| lts2_coverage | 0.005 | 0.000 |
| edge_length_avg_m_bike | 0.005 | 0.000 |
| mean_route_lts | 0.005 | 0.000 |
| n_components_bike | 0.005 | 0.000 |
| self_loop_proportion_road | 0.005 | 0.000 |
| components_per_km_road | 0.005 | 0.000 |
| lcc_length_km_bike | 0.005 | 0.000 |
| cycle_network_density_km2 | 0.004 | 0.000 |
| betweenness_median_bike | 0.004 | 0.000 |
| closeness_median_road | 0.004 | 0.000 |
| lcc_length_share_road | 0.004 | 0.000 |
| closeness_median_bike | 0.004 | 0.000 |
| intersection_density_km2_bike | 0.004 | 0.000 |
| dead_end_proportion_road | 0.004 | 0.001 |
| self_loop_proportion_bike | 0.004 | 0.000 |
| closeness_mean_bike | 0.004 | 0.001 |
| orientation_entropy_bike | 0.003 | 0.000 |
| component_size_gini_road | 0.003 | 0.000 |
| betweenness_median_road | 0.003 | 0.000 |
| betweenness_mean_road | 0.002 | 0.000 |
| orientation_order_bike | 0.002 | 0.000 |
| intersection_count_bike | 0.002 | 0.000 |
| meshedness_road | 0.002 | 0.000 |
| k_avg_road | 0.002 | 0.000 |
| connectivity_ratio_road | 0.002 | 0.000 |
| n_edges_bike | 0.002 | 0.000 |
| length_km_bike | 0.002 | 0.000 |
| n_nodes_bike | 0.001 | 0.000 |
| length_km_road | 0.001 | 0.000 |
| lcc_length_km_road | 0.001 | 0.000 |
| n_edges_road | 0.001 | 0.000 |
| intersection_count_road | 0.001 | 0.000 |
| n_nodes_road | 0.001 | 0.000 |
| n_components_road | 0.001 | 0.000 |

**Implementation gap by country** — mean (observed − predicted) cycling rate in percentage points, form-only out-of-fold model. Positive = the country cycles MORE than its network form predicts (culture/policy amplify form); negative = less. Small-n is noisy -- read with `n`.

| country | n | mean_gap |
| --- | --- | --- |
| AL | 1 | 26.360 |
| GR | 2 | 17.040 |
| MZ | 1 | 8.160 |
| AT | 9 | 6.490 |
| DK | 7 | 6.070 |
| NL | 33 | 5.720 |
| BG | 18 | 5.300 |
| SE | 12 | 3.350 |
| IL | 1 | 3.030 |
| BD | 1 | 2.920 |
| CH | 11 | 2.620 |
| LV | 3 | 2.220 |
| CL | 18 | 1.370 |
| BR | 3 | 0.920 |
| CZ | 16 | 0.910 |
| IN | 5 | 0.890 |
| AR | 2 | 0.840 |
| FI | 10 | 0.350 |
| SK | 8 | 0.330 |
| DE | 150 | 0.320 |
| IE | 5 | 0.050 |
| IT | 90 | -0.160 |
| RO | 1 | -0.540 |
| MY | 1 | -0.600 |
| UK | 122 | -0.670 |
| CA | 25 | -0.800 |
| SI | 5 | -0.810 |
| US | 337 | -0.900 |
| HU | 5 | -0.950 |
| KO | 20 | -0.960 |
| PT | 24 | -1.160 |
| BE | 15 | -1.300 |
| PH | 1 | -1.890 |
| NZ | 5 | -2.050 |
| FR | 85 | -2.090 |
| GH | 1 | -2.540 |
| NO | 18 | -2.770 |
| ES | 26 | -3.120 |
| CO | 3 | -3.230 |
| UY | 1 | -3.270 |
| CY | 1 | -3.320 |
| TW | 1 | -3.610 |
| PL | 6 | -4.350 |
| AU | 9 | -4.490 |
| HK | 1 | -4.610 |
| HR | 1 | -4.740 |
| SG | 1 | -5.160 |
| UA | 1 | -5.510 |
| LT | 3 | -6.660 |
| EE | 2 | -7.570 |
| BY | 1 | -7.760 |

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

### Growth curve: predicted cycling rate vs distance invested

Sweeping the grown network's build-out stages (GTs prune quantiles). **Distance invested** = new protected cycleway that must actually be built (grown corridors already present as cycle infrastructure are excluded). The **elbow** is the best trade-off -- the km built where the predicted-rate gain starts to plateau (`elbow_gain_captured_frac` = share of the total predicted gain reached by then). Figures: `growth_curve_predicted_rate.png` (level) and `growth_marginal.png` (gain per km).

| place_id | total_invested_km | total_gain_pp | elbow_km | elbow_km_frac | elbow_gain_captured_frac |
| --- | --- | --- | --- | --- | --- |
| Gateshead, United Kingdom | 192.700 | 16.140 | 95.800 | 0.500 | 0.820 |
| Newcastle upon Tyne, United Kingdom | 197.300 | 13.410 | 112.300 | 0.570 | 0.410 |
| North Tyneside, United Kingdom | 156.200 | 14.450 | 34.600 | 0.220 | 0.690 |
| South Tyneside, United Kingdom | 119.100 | 13.270 | 89.400 | 0.750 | 0.930 |
| Sunderland, United Kingdom | 271.800 | 14.660 | 209.700 | 0.770 | 0.440 |
| AVERAGE | 187.420 | 14.390 | 108.360 | 0.560 | 0.660 |

_Caveats: predicted rates are the cross-national form model extrapolated to networks far denser than typical UK -- read as directional (relative build value), not literal forecasts. The growth model's prune order is not benefit-ordered, so per-borough marginal returns are bumpy (growth_marginal.png)._

## 9. Key caveats

- Correlations/predictions are descriptive + predictive, **not causal** (no confounder control yet; that is future work).
- Spearman is primary (cycling rate is skewed); Pearson shown alongside.
- A few metrics (entropy_gap_kl, bike centralities, components_per_km_bike) have extreme values driven by cities with a near-empty cycle network; these are kept (rank-based stats are robust), so plots show real outliers.
- Bike layer is raw OSM; road layer is neatnet-simplified — so raw *count* metrics are comparable within a layer across cities, not bike-vs-road.
- Densities are normalised by network length, not built-up area.
- `n` varies by metric: ~45 places predate newer metrics (fixed by re-running) and some metrics are genuinely undefined (e.g. gini on a single-component network).
