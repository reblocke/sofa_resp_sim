# Respiratory SOFA Applet Milestone 3 Sweep Validation

Representative sweep configuration:
- obs_freq_minutes=[15, 30, 60]
- noise_sd=[0.5, 1.0, 1.5]
- room_air_threshold=[92.0, 94.0, 96.0]
- heatmap_metric=p_sofa_3plus
- n_reps=120
- seed=2026
- combinations=27
- total_runs=3240

Top summary rows (CSV excerpt):
```csv
obs_freq_minutes,noise_sd,room_air_threshold,n_reps,mean_count_pf_ratio_acute,p_single_pf_suppressed,p_sofa_0,p_sofa_1,p_sofa_2,p_sofa_3,p_sofa_4,p_sofa_3plus,p_sofa_3plus_check
15,0.5,92.0,120,74.575,0.0,0.0,0.09166666666666666,0.8833333333333333,0.025,0.0,0.025,0.0
15,0.5,94.0,120,75.65,0.0,0.0,0.0,0.8833333333333333,0.1,0.016666666666666666,0.11666666666666667,0.0
15,0.5,96.0,120,76.79166666666667,0.0,0.0,0.0,0.5916666666666667,0.39166666666666666,0.016666666666666666,0.4083333333333333,0.0
15,1.0,92.0,120,75.16666666666667,0.0,0.0,0.03333333333333333,0.925,0.041666666666666664,0.0,0.041666666666666664,0.0
15,1.0,94.0,120,73.78333333333333,0.0,0.0,0.0,0.85,0.125,0.025,0.15,0.0
15,1.0,96.0,120,75.525,0.0,0.0,0.0,0.6083333333333333,0.375,0.016666666666666666,0.39166666666666666,0.0
15,1.5,92.0,120,72.5,0.0,0.0,0.03333333333333333,0.95,0.016666666666666666,0.0,0.016666666666666666,0.0
15,1.5,94.0,120,72.375,0.0,0.0,0.0,0.8416666666666667,0.15,0.008333333333333333,0.15833333333333333,0.0
```

Derived metric check:
- max_abs(p_sofa_3plus - (p_sofa_3 + p_sofa_4)) = 0.000000000000

Guardrail behavior note:
- hard stop threshold: 50000 runs
- oversized sweep result: Sweep workload exceeds guardrail (52500 runs > 50000). Combinations=75, n_reps=700.

Export schema snapshot:
- summary columns: ['obs_freq_minutes', 'noise_sd', 'room_air_threshold', 'n_reps', 'mean_count_pf_ratio_acute', 'p_single_pf_suppressed', 'p_sofa_0', 'p_sofa_1', 'p_sofa_2', 'p_sofa_3', 'p_sofa_4', 'p_sofa_3plus', 'p_sofa_3plus_check']
- replicate columns: ['obs_freq_minutes', 'noise_sd', 'room_air_threshold', 'replicate', 'seed', 'sofa_pulm', 'sofa_pulm_bl', 'sofa_pulm_delta', 'count_pf_ratio_acute', 'n_qualifying_pf_records_acute', 'n_qualifying_pf_records_baseline', 'single_pf_suppressed']
