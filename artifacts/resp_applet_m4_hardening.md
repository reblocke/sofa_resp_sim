# Respiratory SOFA Applet Milestone 4 Hardening

## Release notes
- Added versioned applet presets in `python/src/sofa_resp_sim/web/presets.py`:
  - scenario presets: `Default`, `High noise`, `Sparse observations`, `Conservative oxygen policy`
  - sweep presets: `Quick`, `Broad`, `Custom`
  - preset schema version: `m4-v1`
- Added preset serialization/parse helpers for deterministic roundtrip coverage.
- Added explicit sidebar reset behavior: `Reset controls to selected preset`.
- Added local applet runbook:
  - `docs/APPLET_RUNBOOK.md`
- Added handoff decision memo:
  - `docs/APPLET_HANDOFF_DECISION.md`
- Added performance harness:
  - `python/scripts/profile_applet_performance.py`
  - benchmark output in `artifacts/resp_applet_m4_performance.csv`

## Performance pass
Command run:

```bash
conda run -n proj-env env PYTHONPATH=python/src \
  python python/scripts/profile_applet_performance.py \
  --n-reps 1000 --repeats 1 --seed 0 --target-seconds 2.0 \
  --output-csv artifacts/resp_applet_m4_performance.csv
```

Observed benchmark summary:

| n_reps | repeats | seed | mean_seconds | median_seconds | target_seconds | meets_target |
| --- | --- | --- | --- | --- | --- | --- |
| 1000 | 1 | 0 | 26.5609 | 26.5609 | 2.0 | False |

Interpretation:
- The Milestone 4 performance target (`<2s` for `n_reps=1000`) is **not met** in this environment.
- This supports the handoff decision to keep Streamlit for internal use and move production toward an async backend architecture.

## Validation
- `conda run -n proj-env python -m pytest` -> `80 passed`
- `conda run -n proj-env python -m ruff check python/src/sofa_resp_sim/web python/scripts/profile_applet_performance.py python/tests/test_web_*` -> all checks passed

## Remaining limitations
- Single-scenario and sweep execution remain synchronous in Streamlit.
- Built-in reference remains the only runtime reference source (upload UI deferred).
