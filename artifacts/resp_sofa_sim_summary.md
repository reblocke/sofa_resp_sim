# Respiratory SOFA Simulation Summary

Parameters: 200 replicates, obs_freq=15m, noise_sd=1.0, room_air_threshold=94

| obs_freq_minutes | noise_sd | room_air_threshold | n_reps | mean_count_pf_ratio_acute | p_single_pf_suppressed | p_sofa_0 | p_sofa_1 | p_sofa_2 | p_sofa_3 | p_sofa_4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 15.0000 | 1.0000 | 94.0000 | 200.0000 | 74.7200 | 0.0000 | 0.0000 | 0.0000 | 0.8250 | 0.1600 | 0.0150 |

## SQL-parity fixtures

Golden respiratory SOFA fixtures are in ``python/tests/test_resp_scoring_golden_fixtures.py``
and summarized in ``artifacts/resp_scoring_fixtures.md``/``.csv``. They cover
SpO2→PaO2 conversion, FiO2 lookbacks/selection, PF ratios (including quartile
suppression), support gating, baseline selection, altitude thresholds, and
24h/6h binning for ``sofa_ts``/``quartile`` as implemented in
``python/src/tcco2_accuracy/resp_scoring.py``.
