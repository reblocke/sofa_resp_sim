# Respiratory SOFA Applet Milestone 2 Uncertainty Validation

Representative run parameters: n_reps=300, seed=2026, CI=95%, bootstrap_samples=1000.

- L1 distance: 0.096667
- Jensen-Shannon distance: 0.047952

| score | p_scenario | ci_lower | ci_upper | p_reference | delta_vs_reference | l1_distance | jensen_shannon_distance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.096667 | 0.047952 |
| 1 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.096667 | 0.047952 |
| 2 | 0.873333 | 0.833333 | 0.910000 | 0.825000 | 0.048333 | 0.096667 | 0.047952 |
| 3 | 0.116667 | 0.080000 | 0.153333 | 0.160000 | -0.043333 | 0.096667 | 0.047952 |
| 4 | 0.010000 | 0.000000 | 0.023333 | 0.015000 | -0.005000 | 0.096667 | 0.047952 |

Columns: `score`, `p_scenario`, `ci_lower`, `ci_upper`, `p_reference`, `delta_vs_reference`, `l1_distance`, `jensen_shannon_distance`.