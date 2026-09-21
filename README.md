# sofa_resp_sim

Respiratory SOFA scoring, simulation, and static browser validation app.

Use the published app: [Respiratory SOFA Simulation](https://reblocke.github.io/sofa_resp_sim/).

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

The CLI is the batch/export surface for local or scripted runs. It accepts
comma-separated values for `--obs-freq`, `--noise-sd`, and
`--room-air-threshold`, so a single command can run a small parameter sweep.
Single values produce a one-cell sweep.

```bash
uv run resp-sofa-sim --help
uv run resp-sofa-sim --replicates 200 --obs-freq 15 --noise-sd 1.0 --room-air-threshold 94 --seed 0
uv run resp-sofa-sim --replicates 100 --obs-freq 15,30,60 --noise-sd 0.5,1.0 --room-air-threshold 92,94 --seed 0 --output /tmp/sofa_resp_sweep.csv
```

The first example is a one-cell sweep / single-configuration run. The second
writes a multi-cell sweep summary to CSV.

Invalid CLI inputs fail fast with validation errors printed to stderr instead of
uncaught Python tracebacks.

## Web app

The GitHub Pages app is the main interactive surface. JavaScript collects
inputs, renders returned tables/charts, and downloads CSV/JSON exports. Scoring
and simulation logic run inside Pyodide from staged Python source.

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

## Repository Notes

### Description

Simulation to explore SOFA respiratory score generation from EHR data at elevation

### Project Status

No manuscript version is expected. Code and simulation text are repository-authored unless otherwise noted.

### Data and Reuse

Simulation data only

### Contact

Maintainer: Brian W. Locke (`@reblocke`). Use GitHub issues or pull requests for repository-specific questions when the repository is public.

## Paired workbench implementation

The v2 paired Python/worker API is under active implementation alongside the
existing scenario/sweep workflows. See [implementation status](docs/implementation/sofa_experiment_v2_status.md)
for completed checks and remaining acceptance and reference-run work.

## Paired experiment CLI and bundles

The default browser page provides Experiment, Explain an encounter, and Methods
and export views. It displays a saved synthetic example before Python loads.
The historical scenario/sweep interface remains available at `legacy.html`.
A small saved bundle includes normalized requests, patient scores, summaries,
paired contrasts, transitions, reclassification, selected traces and content hashes.
These are uncalibrated synthetic results.

```bash
uv run resp-sofa-experiment list
uv run resp-sofa-experiment run --entry E1_density --stratum room_air --replicates 200 --output artifacts/local/example-bundle
uv run resp-sofa-experiment verify-bundle artifacts/local/example-bundle
uv run resp-sofa-experiment reproduce artifacts/local/example-bundle --output artifacts/local/reproduced.zip
uv run resp-sofa-experiment append artifacts/local/example-bundle --replicates 1000 --output artifacts/local/extended-bundle
```

`run --request request.json` accepts a fully normalized request; optional
`--replicates` overrides N explicitly. `explain BUNDLE --patient ID --condition ID`
regenerates one trace and verifies its saved score. Output paths must be new.
Exact reproduction/append require the recorded runtime and package source.
`reproduce --allow-runtime-difference` explicitly permits a cross-runtime check
with exact discrete values and the declared float tolerance, recorded in the
new manifest. Unknown scientific versions still fail.

Use `make experiments-smoke` for native mechanism/bundle checks and
`make experiments-install-check` for an isolated locked wheel reproduction.
The full reference collection is in `artifacts/experiments_v2/`, with reviewed
figures, source hashes and interpretation. The completed delivery audit is recorded in `docs/implementation/sofa_experiment_v2_status.md`.

`make experiments-reference` runs the complete frozen catalogue at 2,000 paired
patients per stochastic stratum (one for the deterministic episode). It retains
verified bundles and logs under `artifacts/local/references_v2/` and resumes
matching completed bundles. This can take substantially longer than a preview.
See `docs/VALIDATION.md` for resumption and reference-evidence rules.

The completed historical phase is documented in the
[TROPS eligibility sensitivity target and acceptance ledger](docs/implementation/trops_fidelity_goal/GOAL.md).
See the [completion report](docs/implementation/trops_fidelity_goal/COMPLETION_REPORT.md)
and [reference findings](artifacts/trops_sensitivity_v1/FINDINGS.md). External
SQL execution is separate future work.

The v3 historical TROPS sensitivity profile is described in
[the source-mapped contract](docs/TROPS_SCORING_CONTRACT.md). It is historical and
not execution-validated; C=0/1/≥2 are conditional scenarios, not population weights.
