# sofa_resp_sim

Respiratory SOFA scoring, simulation, and Streamlit-based validation applet.

This repository contains:
- a respiratory SOFA scoring engine with event-level diagnostic outputs,
- a simulation framework for respiratory observation/support scenarios,
- a Streamlit applet for deterministic exploration, reference comparison, uncertainty views, parameter sweeps, presets, and CSV exports.

## Repository status

This is research software.
It is intended for:
- method development,
- internal validation,
- reproducible simulation and documentation of respiratory SOFA behavior.

It is **not** presented as a medical device or as stand-alone clinical decision support.

See:
- `docs/CLINICAL_SCOPE.md`
- `docs/VALIDATION.md`
- `docs/PROVENANCE.md`
- `docs/PUBLIC_RELEASE_AUDIT.md`

## Package layout

- `python/src/sofa_resp_sim/resp_scoring.py`
  - respiratory SOFA scoring and SQL-parity diagnostics
- `python/src/sofa_resp_sim/resp_utils.py`
  - helper functions such as Oracle-style rounding and SpO2→PaO2 conversion
- `python/src/sofa_resp_sim/resp_simulation.py`
  - simulation and replicate/sweep helpers
- `python/src/sofa_resp_sim/resp_sofa_runner.py`
  - CLI entrypoint for simulation sweeps
- `python/src/sofa_resp_sim/web/`
  - Streamlit applet, request normalization, service orchestration, presets, and reference handling
- `python/scripts/profile_applet_performance.py`
  - local single-scenario app-service benchmark helper
- `python/tests/`
  - package and app tests
- `tests/`
  - repository contract tests
- `artifacts/`
  - small checked-in validation summaries
- `docs/`
  - canonical architecture, validation, scope, provenance, and ADRs

## Quickstart

### Canonical setup path

This repository uses `uv` as the canonical environment manager.

```bash
uv sync --dev
uv run pytest -q
uv run ruff check .
```

### Run the CLI

```bash
uv run resp-sofa-sim --help
uv run resp-sofa-sim --replicates 200 --obs-freq 15 --noise-sd 1.0 --room-air-threshold 94 --seed 0
```

### Run the Streamlit applet

```bash
uv run streamlit run python/src/sofa_resp_sim/web/applet_streamlit.py
```

The applet supports single-scenario runs, parameter sweeps, built-in presets,
reference-distribution comparison, uncertainty summaries, guardrails for large
sweeps, and CSV export. See `docs/APPLET_RUNBOOK.md`.

## Development commands

```bash
make sync
make lint
make test
make check
make app
make build
```

## Validation

Current automated validation includes:
- `python/tests/test_resp_scoring.py`
- `python/tests/test_resp_scoring_golden_fixtures.py`
- `python/tests/test_web_*.py`
- `python/tests/test_streamlit_app_smoke.py`
- `python/tests/test_cli_contract.py`
- `tests/test_repository_contract.py`

See:
- `docs/VALIDATION.md`
- `artifacts/README.md`

For release checks, run:

```bash
make check
uv run python -m build
uv run resp-sofa-sim --help
uv run pytest -q python/tests/test_streamlit_app_smoke.py
```

## Public release posture

The current tracked tree is intended to contain only source code, docs, tests,
and small synthetic or aggregate artifacts. Local literature PDFs are ignored by
`docs/*.pdf`.

Before making an existing hosted repository public, review
`docs/PUBLIC_RELEASE_AUDIT.md`: the current tree has no known PHI, but earlier
GitHub history/PR refs may still contain PDF blobs that should be purged or
avoided by publishing from a clean history.

## Contribution guidance

See:
- `CONTRIBUTING.md`
- `SECURITY.md`
- `SUPPORT.md`
- `CODE_OF_CONDUCT.md`

## Citation and license

- Citation metadata: `CITATION.cff`
- License: `LICENSE`
