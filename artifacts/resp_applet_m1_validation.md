# Respiratory SOFA Applet Milestone 1 Validation

| Check | Scope | Result | Details |
| --- | --- | --- | --- |
| `pytest` | repo | pass | 40 passed in 16.49s |
| `ruff` | web + new tests | pass | All checks passed |
| `ruff` | repo | fail | Pre-existing lint issues in non-web files (`resp_scoring.py`, `resp_simulation.py`, `resp_utils.py`, legacy tests) |
| Streamlit module smoke | bare mode | pass | `python -m tcco2_accuracy.web.applet_streamlit` executed; expected ScriptRunContext warnings outside `streamlit run` |

## Notes
- Milestone 1 scope implemented under `python/src/tcco2_accuracy/web/`.
- Built-in reference is loaded from `artifacts/resp_sofa_sim_summary.csv`.
