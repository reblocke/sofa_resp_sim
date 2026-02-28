# Package Namespace Migration

## Summary
Namespace migration completed for this repository:
- Old: `tcco2_accuracy`
- New: `sofa_resp_sim`

## Scope
| Area | Status |
| --- | --- |
| Package directory rename (`python/src/tcco2_accuracy` -> `python/src/sofa_resp_sim`) | done |
| Python imports (source/tests) | done |
| CLI entrypoints in `pyproject.toml` | done |
| Docs/artifact path references | done |

## Validation
| Check | Result |
| --- | --- |
| `conda run -n proj-env python -m pytest` | pass (`40 passed`) |
| `conda run -n proj-env env PYTHONPATH=python/src python -m sofa_resp_sim.resp_sofa_runner --help` | pass |
| `conda run -n proj-env python -m ruff check .` | fail (pre-existing lint issues outside migration scope) |
