---
name: scientific-numerics-verification
description: Use when changing respiratory SOFA scoring, SpO2-to-PaO2 conversion, FiO2 handling, support gating, simulation assumptions, validation fixtures, or reference distributions. Do not use for governance-file-only changes.
---

Verification checklist:

1. Run targeted scoring and simulation tests first.
2. Re-run the full pytest suite after targeted checks pass.
3. Confirm invariants explicitly:
   - conversion edge behavior,
   - FiO2 prioritization/lookback logic,
   - PF ratio behavior,
   - rubric scoring,
   - support gating,
   - acute single-PF suppression,
   - baseline selection,
   - deterministic behavior under fixed seed.
4. If outputs changed intentionally:
   - update `docs/VALIDATION.md`,
   - update checked-in small artifacts under `artifacts/`,
   - explain the change in the PR summary.

For this repo, start with:
```bash
uv run pytest -q tests/core/test_resp_scoring.py tests/core/test_resp_scoring_golden_fixtures.py
make test
```
