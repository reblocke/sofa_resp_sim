# Validation

## Purpose

This file maps system invariants to concrete tests and checked-in evidence.

## Core invariants

| Invariant | Primary evidence |
|---|---|
| SpO2→PaO2 conversion behavior is stable | `python/tests/test_resp_scoring.py`, `python/tests/test_resp_scoring_golden_fixtures.py` |
| FiO2 prioritization and lookback logic are stable | `python/tests/test_resp_scoring.py`, golden fixtures |
| PF ratio scoring and support gating are stable | golden fixtures |
| Acute single-PF suppression is stable | golden fixtures |
| Simulation outputs are deterministic under fixed seeds | `python/tests/test_web_services.py` |
| Reference normalization is stable | `python/tests/test_web_reference.py` |
| Sweep shapes and metrics are stable | `python/tests/test_web_sweep.py` |
| Preset serialization is stable | `python/tests/test_web_presets.py` |
| Uncertainty table schema is stable | `python/tests/test_web_uncertainty.py` |
| Root docs and metadata do not drift to stale identities | `tests/test_repository_contract.py` |
| CLI help contract remains valid | `python/tests/test_cli_contract.py` |
| Streamlit render contract remains valid | `python/tests/test_streamlit_app_smoke.py` |

## Canonical commands

```bash
uv sync --dev
uv run pytest -q
uv run ruff check .
uv run python -m build
uv run resp-sofa-sim --help
uv run pytest -q python/tests/test_streamlit_app_smoke.py
```

The Makefile wraps the common local checks:

```bash
make check
make app
make build
```

## Artifact evidence

Checked-in validation artifacts live under:
- `artifacts/`

See:
- `artifacts/README.md`

## Release-oriented checks

Before a release or public visibility change:
- run the canonical commands above,
- confirm `git status --short --branch` has no tracked changes,
- inspect `docs/PUBLIC_RELEASE_AUDIT.md` for PHI/confidentiality and history-cleanup notes,
- regenerate or document any changed artifacts in `artifacts/README.md`.

## When to update this file

Update this file when:
- a new invariant is added,
- a validation artifact becomes canonical,
- the test layout changes,
- public output schemas change,
- the applet gains a new stable contract that merits direct testing.
