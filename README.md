# sofa_resp_sim

Respiratory SOFA scoring, simulation, and static browser validation app.

This repository contains:
- a Python respiratory SOFA scoring engine with diagnostic outputs,
- deterministic simulation helpers for respiratory observation/support scenarios,
- a static GitHub Pages app that runs the Python package in Pyodide,
- small checked-in validation artifacts and contract tests.

This is research software. It is not a medical device, standalone clinical
decision support, or a replacement for clinician judgment.

## Quickstart

```bash
uv sync --dev
make test
make stage-web
make serve
```

Then open the local server URL printed by `python3 -m http.server`.

## Common commands

```bash
make sync       # uv sync --locked --dev
make test       # Python tests, excluding browser e2e
make e2e        # Playwright browser smoke test for the static app
make verify     # stage web assets, format check, lint, tests, e2e
make build      # build the Python package
make sim-help   # show CLI help
```

## Package layout

- `src/sofa_resp_sim/core/`
  - pure scoring, simulation, and utility modules.
- `src/sofa_resp_sim/resp_scoring.py`, `resp_simulation.py`, `resp_utils.py`
  - compatibility wrappers for existing imports.
- `src/sofa_resp_sim/reporting/`
  - browser-safe request normalization, presets, reference comparison,
    uncertainty summaries, and export formatting.
- `src/sofa_resp_sim/browser_contract.py`
  - the narrow Pyodide-facing API used by the static app.
- `src/sofa_resp_sim/workflows/cli.py`
  - `resp-sofa-sim` console entrypoint.
- `web/`
  - static HTML/CSS/JavaScript and the Pyodide worker.
- `scripts/stage_web_python.py`
  - reproducibly stages allowlisted Python/data assets into `web/assets/`.
- `tests/`
  - core, contract, workflow, and browser e2e tests.

## Python API

Existing imports remain valid:

```python
from sofa_resp_sim import score_respiratory
from sofa_resp_sim.resp_simulation import SimulationConfig, run_parameter_sweep
```

The browser app calls only:

```python
from sofa_resp_sim.browser_contract import (
    get_app_config_payload,
    run_scenario_payload,
    run_sweep_payload,
)
```

## CLI

```bash
uv run resp-sofa-sim --help
uv run resp-sofa-sim --replicates 200 --obs-freq 15 --noise-sd 1.0 --room-air-threshold 94 --seed 0
```

## Web app

The GitHub Pages app is static. JavaScript collects inputs, renders returned
tables/charts, and downloads CSV/JSON exports. Scoring and simulation logic run
inside Pyodide from staged Python source.

```bash
make stage-web
make serve
make e2e
```

Generated staged assets under `web/assets/py/` and `web/assets/data/` are
ignored because they are reproducible from source and artifacts.

## Validation

Primary validation commands:

```bash
make test
make e2e
make verify
uv run python -m build
uv run resp-sofa-sim --help
```

See `docs/VALIDATION.md` and `artifacts/README.md`.

## Public release posture

The tracked tree is intended to contain only source code, docs, tests, and small
synthetic or aggregate artifacts. Local literature PDFs are ignored by
`docs/*.pdf`.

Before making an existing hosted repository public, review
`docs/PUBLIC_RELEASE_AUDIT.md`: the current tree has no known PHI, but earlier
GitHub history/PR refs may still contain publisher PDF blobs.

## More documentation

- `docs/ARCHITECTURE.md`
- `docs/WEB_APP.md`
- `docs/DEPLOY_PAGES.md`
- `docs/VALIDATION.md`
- `docs/CLINICAL_SCOPE.md`
- `docs/PROVENANCE.md`
- `docs/DECISIONS.md`
- `docs/PUBLIC_RELEASE_AUDIT.md`

## Citation and license

- Citation metadata: `CITATION.cff`
- License: `LICENSE`
