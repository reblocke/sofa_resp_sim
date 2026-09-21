# Historical sensitivity findings

Historical TROPS specification mapped to Python; synthetic verification complete; execution against the study SQL not performed.

All 48 prespecified requests use 2,000 paired synthetic patients, seed 173203, stationary saturation (mean 96%, SD 0.5 percentage points, correlation time 30 minutes), no episodes or support drift. C strata have no population weights. Intervals quantify Monte Carlo uncertainty, not clinical uncertainty. Original v2 nulls and demonstrations remain in the separate v2 namespace.

| Mechanism / profile / support | Common comparator → variant | Paired difference | Common N |
|---|---:|---:|---:|
| density / historical / room_air | 0 → 0 | 0 | 2000 |
| density / experimental / room_air | 0 → 0 | 0 | 2000 |
| density / historical / low_flow | 0 → 0 | 0 | 2000 |
| density / experimental / low_flow | 0 → 0 | 0 | 2000 |
| density / historical / hfnc | 0 → 0 | 0 | 2000 |
| density / experimental / hfnc | 0 → 0 | 0 | 2000 |
| density / historical / imv | 0 → 0 | 0 | 2000 |
| density / experimental / imv | 0 → 0 | 0 | 2000 |
| missing / historical / room_air | 0.539 → 0.269 | -0.27 | 2000 |
| missing / experimental / room_air | 0.539 → 0.269 | -0.27 | 2000 |
| missing / historical / low_flow | 0.539 → 0.269 | -0.27 | 2000 |
| missing / experimental / low_flow | 0.539 → 0.269 | -0.27 | 2000 |
| missing / historical / hfnc | 0.539 → 0.269 | -0.27 | 2000 |
| missing / experimental / hfnc | 0.539 → 0.269 | -0.27 | 2000 |
| missing / historical / imv | 0.539 → 0.269 | -0.27 | 2000 |
| missing / experimental / imv | 0.539 → 0.269 | -0.27 | 2000 |
| timing / historical / room_air | 0.539 → 0.534 | -0.00537 | 2000 |
| timing / experimental / room_air | 0.539 → 0.533 | -0.00542 | 2000 |
| timing / historical / low_flow | 0.539 → 0.534 | -0.00537 | 2000 |
| timing / experimental / low_flow | 0.539 → 0.533 | -0.00542 | 2000 |
| timing / historical / hfnc | 0.539 → 0.534 | -0.00537 | 2000 |
| timing / experimental / hfnc | 0.539 → 0.533 | -0.00542 | 2000 |
| timing / historical / imv | 0.539 → 0.534 | -0.00537 | 2000 |
| timing / experimental / imv | 0.539 → 0.533 | -0.00542 | 2000 |
| baseline_density / historical / room_air | 0 → 0 | 0 | 1964 |
| baseline_density / experimental / room_air | 0 → 0 | 0 | 1970 |
| baseline_density / historical / low_flow | 0 → 0 | 0 | 1964 |
| baseline_density / experimental / low_flow | 0 → 0 | 0 | 1970 |
| baseline_density / historical / hfnc | 0 → 0 | 0 | 1964 |
| baseline_density / experimental / hfnc | 0 → 0 | 0 | 1970 |
| baseline_density / historical / imv | 0 → 0 | 0 | 1964 |
| baseline_density / experimental / imv | 0 → 0 | 0 | 1970 |
| history / historical / room_air | 0 → 0 | 0 | 2000 |
| history / experimental / room_air | 0 → 0 | 0 | 2000 |
| history / historical / low_flow | 0 → 0 | 0 | 2000 |
| history / experimental / low_flow | 0 → 0 | 0 | 2000 |
| history / historical / hfnc | 0 → 0 | 0 | 2000 |
| history / experimental / hfnc | 0 → 0 | 0 | 2000 |
| history / historical / imv | 0 → 0 | 0 | 2000 |
| history / experimental / imv | 0 → 0 | 0 | 2000 |
| alignment / historical / room_air | 0 → 0 | 0 | 2000 |
| alignment / experimental / room_air | 0 → 0 | 0 | 1999 |
| alignment / historical / low_flow | 0 → 0 | 0 | 2000 |
| alignment / experimental / low_flow | 0 → 0 | 0 | 1999 |
| alignment / historical / hfnc | 0 → 0 | 0 | 2000 |
| alignment / experimental / hfnc | 0 → 0 | 0 | 1999 |
| alignment / historical / imv | 0 → 0 | 0 | 2000 |
| alignment / experimental / imv | 0 → 0 | 0 | 1999 |

Values for binary outcomes are percentages/percentage-point differences; retention uses fractions. Exact intervals, numerators, condition-specific marginals, all three C views and secondary outcomes are in the CSV tables. Empty common denominators are unavailable; N=1 has no interval.

Stable saturation near the conversion ceiling can exclude otherwise recorded observations. Retention therefore need not be 100% even with no missing documentation. A null eligibility contrast does not show that documentation is irrelevant: examine retention and evidence transitions. C≥2 is eligible in every condition by construction. E5 baseline opportunity counts are the actual selected-day counts in the patient explanations, rather than total-history counts. Acute scores are a negative control for baseline-only perturbations. Low-flow delivered FiO2 error is unavailable because the flow proxy does not identify true delivered FiO2.
