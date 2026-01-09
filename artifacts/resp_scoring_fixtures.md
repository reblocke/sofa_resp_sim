# Respiratory SOFA SQL-Parity Fixtures

- `admit_dts`: 2026-01-01 00:00:00 (timezone-naive)
- Default `altitude_factor`: 1.0 unless specified
- Coverage: SpO2 conversion, FiO2 prioritization/lookbacks, PF ratio + quartile suppression,
  resp-detail vs measures gating, acute single-PF suppression, baseline day selection

## Summary

| Fixture | Scenario | Expected | Key Assertion |
| --- | --- | --- | --- |
| 0 | SpO2→PaO2 conversion | PaO2 reference values | `spo2_to_pao2` rounding to 1 decimal |
| 1 | SpO2>96 room air | `SOFA_PULM=0` | `pf_ratio_temp` NULL |
| 2 | 24h FiO2 lookback only | `SOFA_PULM=0` | minute window NULL blocks acute |
| 3 | HFNC two PF ratios | `SOFA_PULM=2` | resp-detail 3 → measures cap 2 |
| 4 | IMV single PF ratio | `SOFA_PULM=4` | no single-PF suppression |
| 5 | NIPPV single PF ratio | `SOFA_PULM=3` | no single-PF suppression |
| 6 | Single PF, no support | `SOFA_PULM=0` | acute single-PF suppression |
| 7 | Baseline recent day | `SOFA_PULM_BL=1` | most recent day selected |
| 8 | Quartile suppression | `SOFA_PULM=0` | room-air fallback blocked |
| 9 | Altitude factor | `SOFA_PULM=4/3` | thresholds scale by altitude |

See `artifacts/resp_scoring_fixtures.csv` for full expectations.
