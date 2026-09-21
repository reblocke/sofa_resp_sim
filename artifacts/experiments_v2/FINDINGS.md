# Paired synthetic experiment findings

These are descriptive results conditional on the prespecified, uncalibrated model.
Support strata are separate experiments with no population weights. They do not
establish clinical accuracy, causal treatment effects, or external validation.
Intervals quantify pointwise Monte Carlo uncertainty, not patient-level uncertainty.
Each row below reports the first prespecified distinct comparison in that stratum.
Contrasts follow preset order, not observed effect magnitude; intervals are pointwise.
Full absolute and paired tables retain every metric and comparison, including nulls.

All signs are variant minus comparator. An observed zero does not prove equivalence.
Unavailable uncertainty at N < 2 is not a zero-width interval.

## E1_density: Observation density

Changed mechanism: SpO2 sampling interval. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | 5 minutes: +0.050 percentage points | [-0.218 percentage points, +0.319 percentage points] | 2000 | 0/3 |
| low_flow | 5 minutes: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 3/3 |
| hfnc | 5 minutes: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 3/3 |
| imv | 5 minutes: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 3/3 |

Uncalibrated illustrative simulation; strata have no population weights. Denser sampling need not increase every encounter score.

[Absolute figure](figures/E1_density_absolute.svg) · [Paired figure](figures/E1_density_paired.svg)

## E1_episode: Deterministic sampling opportunity

Changed mechanism: SpO2 sampling interval. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | 5 minutes: +0.000 percentage points | unavailable | 1 | 2/3 |
| low_flow | 5 minutes: +0.000 percentage points | unavailable | 1 | 3/3 |
| hfnc | 5 minutes: +0.000 percentage points | unavailable | 1 | 3/3 |
| imv | 5 minutes: +0.000 percentage points | unavailable | 1 | 3/3 |

Uncalibrated illustrative simulation; strata have no population weights.

[Absolute figure](figures/E1_episode_absolute.svg) · [Paired figure](figures/E1_episode_paired.svg)

## E2_noise: Measurement noise

Changed mechanism: Measurement noise SD. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | SD 0.5: +0.050 percentage points | [-0.442 percentage points, +0.539 percentage points] | 2000 | 0/3 |
| low_flow | SD 0.5: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 3/3 |
| hfnc | SD 0.5: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 3/3 |
| imv | SD 0.5: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 3/3 |

Uncalibrated illustrative simulation; strata have no population weights.

[Absolute figure](figures/E2_noise_absolute.svg) · [Paired figure](figures/E2_noise_paired.svg)

## E2_bias: Measurement bias

Changed mechanism: Additive measurement bias. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | Bias -2: +0.050 percentage points | [-0.218 percentage points, +0.319 percentage points] | 2000 | 0/2 |
| low_flow | Bias -2: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |
| hfnc | Bias -2: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |
| imv | Bias -2: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |

Uncalibrated illustrative simulation; strata have no population weights.

[Absolute figure](figures/E2_bias_absolute.svg) · [Paired figure](figures/E2_bias_paired.svg)

## E2_rounding: Measurement rounding

Changed mechanism: Documented saturation rounding. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | One decimal: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/2 |
| low_flow | One decimal: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |
| hfnc | One decimal: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |
| imv | One decimal: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |

Uncalibrated illustrative simulation; strata have no population weights.

[Absolute figure](figures/E2_rounding_absolute.svg) · [Paired figure](figures/E2_rounding_paired.svg)

## E2_assignment: Support assignment stress test

Changed mechanism: Support assignment policy. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | Assignment stress test: +0.050 percentage points | [-0.218 percentage points, +0.319 percentage points] | 2000 | 0/1 |
| low_flow | Assignment stress test: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| hfnc | Assignment stress test: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| imv | Assignment stress test: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |

Uncalibrated illustrative simulation; strata have no population weights. The stratum identifies the fixed comparator only. Stress assignment can cross support categories and is not treatment physiology.

[Absolute figure](figures/E2_assignment_absolute.svg) · [Paired figure](figures/E2_assignment_paired.svg)

## E3_missing: Missing FiO2 evidence

Changed mechanism: Whole denominator evidence bundle missingness. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `no_qualifying_data`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | Missing 0.25: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/3 |
| low_flow | Missing 0.25: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/3 |
| hfnc | Missing 0.25: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/3 |
| imv | Missing 0.25: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/3 |

Uncalibrated illustrative simulation; strata have no population weights.

[Absolute figure](figures/E3_missing_absolute.svg) · [Paired figure](figures/E3_missing_paired.svg)

## E3_timing: Documentation timestamp boundaries

Changed mechanism: Documented FiO2 timestamp error. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `no_qualifying_data`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | Offset -14.001 minutes: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 5/5 |
| low_flow | Offset -14.001 minutes: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 5/5 |
| hfnc | Offset -14.001 minutes: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 5/5 |
| imv | Offset -14.001 minutes: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 5/5 |

Uncalibrated illustrative simulation; strata have no population weights. Timestamp error differs from record availability delay.

[Absolute figure](figures/E3_timing_absolute.svg) · [Paired figure](figures/E3_timing_paired.svg)

## E3_sources: FiO2 source disagreement

Changed mechanism: Measured/set source disagreement. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | Measured source +0.1: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| low_flow | Measured source +0.1: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| hfnc | Measured source +0.1: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| imv | Measured source +0.1: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |

Uncalibrated illustrative simulation; strata have no population weights. Room-air and low-flow proxies do not acquire known delivered FiO2 from this setting.

[Absolute figure](figures/E3_sources_absolute.svg) · [Paired figure](figures/E3_sources_paired.svg)

## E3_stale: Stale FiO2 documentation

Changed mechanism: Age of documented denominator value. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | 30-minute-old value: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| low_flow | 30-minute-old value: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| hfnc | 30-minute-old value: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| imv | 30-minute-old value: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |

Uncalibrated illustrative simulation; strata have no population weights. Prescribed support/FiO2 step demonstrates stale values; room air is an inert control.

[Absolute figure](figures/E3_stale_absolute.svg) · [Paired figure](figures/E3_stale_paired.svg)

## E3_labels: FiO2 source-label control

Changed mechanism: Identical values labeled measured versus set. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | Measured source: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| low_flow | Measured source: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| hfnc | Measured source: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |
| imv | Measured source: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |

Uncalibrated illustrative simulation; strata have no population weights. Identical values without conflict change provenance only; room-air/flow sources are unaffected.

[Absolute figure](figures/E3_labels_absolute.svg) · [Paired figure](figures/E3_labels_paired.svg)

## E3_zero: Zero-perturbation control

Changed mechanism: Explicit zero documentation perturbations. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | No distinct normalized variant | not applicable: no distinct contrast | 2000 | 0/0 |
| low_flow | No distinct normalized variant | not applicable: no distinct contrast | 2000 | 0/0 |
| hfnc | No distinct normalized variant | not applicable: no distinct contrast | 2000 | 0/0 |
| imv | No distinct normalized variant | not applicable: no distinct contrast | 2000 | 0/0 |

Uncalibrated illustrative simulation; strata have no population weights. Identical normalized configurations share scientific rows by construction.

[Absolute figure](figures/E3_zero_absolute.svg) · [Paired figure](figures/E3_zero_paired.svg)

## E4_estimated: Threshold factors with estimated PaO2

Changed mechanism: Scoring threshold factor. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | Factor 0.85: -47.200 percentage points | [-49.730 percentage points, -44.461 percentage points] | 2000 | 0/2 |
| low_flow | Factor 0.85: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |
| hfnc | Factor 0.85: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |
| imv | Factor 0.85: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |

Uncalibrated illustrative simulation; strata have no population weights. Threshold scaling changes neither PaO2 nor P/F and implies no altitude in metres.

[Absolute figure](figures/E4_estimated_absolute.svg) · [Paired figure](figures/E4_estimated_paired.svg)

## E4_measured: Threshold factors with measured PaO2

Changed mechanism: Scoring threshold factor. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | Factor 0.85: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |
| low_flow | Factor 0.85: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/2 |
| hfnc | Factor 0.85: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |
| imv | Factor 0.85: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 2/2 |

Uncalibrated illustrative simulation; strata have no population weights. Fixed illustrative PaO2=84 mmHg; threshold scaling is not physiological altitude response.

[Absolute figure](figures/E4_measured_absolute.svg) · [Paired figure](figures/E4_measured_paired.svg)

## E5_opportunity: Independent stationary baseline opportunity

Changed mechanism: Baseline exposure and observation interval. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `delta_legacy_ge1`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | 1h every 15 minutes: +71.750 percentage points | [+68.829 percentage points, +74.395 percentage points] | 2000 | 0/5 |
| low_flow | 1h every 15 minutes: +0.050 percentage points | [-0.218 percentage points, +0.319 percentage points] | 2000 | 3/5 |
| hfnc | 1h every 15 minutes: +0.050 percentage points | [-0.218 percentage points, +0.319 percentage points] | 2000 | 3/5 |
| imv | 1h every 15 minutes: +0.050 percentage points | [-0.218 percentage points, +0.319 percentage points] | 2000 | 3/5 |

Uncalibrated illustrative simulation; strata have no population weights. Independent stationary blocks can have different extrema without deterioration. Delta is not sepsis incidence.

[Absolute figure](figures/E5_opportunity_absolute.svg) · [Paired figure](figures/E5_opportunity_paired.svg)

## E5_replay: Six-hour exact replay control

Changed mechanism: No change: identical six-hour exposure and rules. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `delta_legacy_ge1`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | No distinct normalized variant | not applicable: no distinct contrast | 2000 | 0/0 |
| low_flow | No distinct normalized variant | not applicable: no distinct contrast | 2000 | 0/0 |
| hfnc | No distinct normalized variant | not applicable: no distinct contrast | 2000 | 0/0 |
| imv | No distinct normalized variant | not applicable: no distinct contrast | 2000 | 0/0 |

Uncalibrated illustrative simulation; strata have no population weights. Same full segment at the same UTC time of day within one date, contemporaneous FiO2 and at least two records; only this construction promises zero delta.

[Absolute figure](figures/E5_replay_absolute.svg) · [Paired figure](figures/E5_replay_paired.svg)

## E6_rules: Rule contribution

Changed mechanism: One scoring rule at a time. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | No singleton suppression: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 5/7 |
| low_flow | No singleton suppression: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 5/7 |
| hfnc | No singleton suppression: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 5/7 |
| imv | No singleton suppression: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 5/7 |

Uncalibrated illustrative simulation; strata have no population weights. Rules interact; contrasts are not additive attribution. Mechanism fixtures separately cover inactive rules in dense records.

[Absolute figure](figures/E6_rules_absolute.svg) · [Paired figure](figures/E6_rules_paired.svg)

## E6_singleton: Singleton suppression mechanism

Changed mechanism: Single-record suppression. Within a comparison: patient IDs, generator and all settings not explicitly overridden.

Primary outcome: `score_ge2`.

| Stratum | First prespecified contrast | Pointwise 95% MC interval | Paired N | Observed zero comparisons |
|---|---|---|---:|---:|
| room_air | Suppression disabled: +7.750 percentage points | [+6.245 percentage points, +9.195 percentage points] | 2000 | 0/1 |
| low_flow | Suppression disabled: +90.700 percentage points | [+88.924 percentage points, +92.104 percentage points] | 2000 | 0/1 |
| hfnc | Suppression disabled: +90.700 percentage points | [+88.924 percentage points, +92.104 percentage points] | 2000 | 0/1 |
| imv | Suppression disabled: +0.000 percentage points | [-0.219 percentage points, +0.219 percentage points] | 2000 | 1/1 |

Uncalibrated illustrative simulation; strata have no population weights.

[Absolute figure](figures/E6_singleton_absolute.svg) · [Paired figure](figures/E6_singleton_paired.svg)

## Provenance

Exact source tables, requests and bundles are identified in `table_provenance.json`.
Figure-specific selections and image hashes are in `figure_data_manifest.json`.
Paired-table SHA256: `03b10d11db0cae9da335ec910db5a106d8ec01ac31c7f2815771aac8971b84dd`.

This is an automatically generated descriptive readout. See `INTERPRETATION.md`
for the reviewed interpretation of this reference collection and its limits.
