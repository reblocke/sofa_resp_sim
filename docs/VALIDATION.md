# Validation

## Purpose

This file maps system invariants to tests, generated browser assets, and
checked-in evidence.

## Core invariants

| Invariant | Primary evidence |
|---|---|
| SpO2-to-PaO2 conversion behavior is stable | `tests/core/test_resp_scoring.py`, `tests/core/test_resp_scoring_golden_fixtures.py` |
| FiO2 prioritization and lookback logic are stable | `tests/core/test_resp_scoring.py`, golden fixtures |
| PF ratio scoring and support gating are stable | golden fixtures |
| Acute single-PF suppression is stable | golden fixtures |
| Simulation outputs are deterministic under fixed seeds | `tests/contracts/test_reporting_services.py` |
| Reference normalization is stable | `tests/contracts/test_reporting_reference.py` |
| Sweep shapes and metrics are stable | `tests/contracts/test_reporting_sweep.py` |
| Preset serialization is stable | `tests/contracts/test_reporting_presets.py` |
| Uncertainty table schema is stable | `tests/contracts/test_reporting_uncertainty.py` |
| Browser payloads are JSON serializable and structured | `tests/contracts/test_browser_contract.py` |
| Web staging is allowlist-based and reproducible | `tests/contracts/test_stage_web_python.py` |
| CLI help contract remains valid | `tests/workflows/test_cli_contract.py` |
| Root docs and metadata do not drift to stale identities | `tests/contracts/test_repository_contract.py` |
| Static app initializes and runs scenario/sweep workflows | `tests/e2e/test_web_app.py` |

## Canonical commands

```bash
uv sync --dev
make stage-web
make test
make e2e
make verify
uv run python -m build
uv run resp-sofa-sim --help
```

`make test` excludes browser e2e tests. `make e2e` stages web assets first and
then runs the Playwright static-app smoke test.

## Artifact evidence

Checked-in validation artifacts live under:
- `artifacts/`

See:
- `artifacts/README.md`

Generated browser staging outputs live under:
- `web/assets/py/`
- `web/assets/data/`

Those generated outputs are ignored because `scripts/stage_web_python.py`
recreates them from tracked Python source and checked-in aggregate artifacts.

## Release-oriented checks

Before a release or public visibility change:
- run `make verify`,
- run `uv run python -m build`,
- run `uv run resp-sofa-sim --help`,
- confirm `git status --short --branch --ignored=matching` has no unexpected
  tracked or untracked changes,
- inspect `docs/PUBLIC_RELEASE_AUDIT.md` for PHI/confidentiality and history
  cleanup notes,
- regenerate or document any changed artifacts in `artifacts/README.md`.

## When to update this file

Update this file when:
- a new invariant is added,
- a validation artifact becomes canonical,
- test layout changes,
- public output schemas change,
- the browser contract or static app gains a new stable behavior.
