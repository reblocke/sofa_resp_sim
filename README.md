# sofa_resp_sim

How do observation, documentation, support, and scoring choices change respiratory SOFA results for the **same synthetic patients**? This repository is a paired respiratory SOFA experiment workbench with a Python batch CLI and a static Pyodide browser app. The default browser page is the paired investigation interface; the earlier scenario/sweep workflow remains available for compatibility.

The simulations are **uncalibrated illustrations**, not clinical predictions or a population sample. Their intervals describe pointwise Monte Carlo sampling uncertainty conditional on fixed model assumptions, not parameter or clinical uncertainty. The four support strata have no population weights, and observed zero differences do not prove equivalence. This software is not a medical device, standalone clinical decision support, or a replacement for clinician judgment.

## Paired workbench implementation

| Route | Current use | Evidence boundary |
|---|---|---|
| [Hosted app](https://reblocke.github.io/sofa_resp_sim/) | Interactive exploration through the configured GitHub Pages URL. | A link or Pages configuration does not verify the currently deployed build. |
| Local browser development | Stage source assets, serve over HTTP, and inspect the default Experiment, Explain an encounter, and Methods and export views. | Staging and a local page load are not clinical validation. |
| `resp-sofa-experiment` | Run a prespecified or normalized paired request, save and verify a synthetic bundle, explain a patient, reproduce or append. | Bundle verification checks its recorded structure, hashes, versions, and table reconciliation; source/runtime requirements still govern replay. |
| Legacy scenario/sweep | `resp-sofa-sim`, compatibility imports, and [`web/legacy.html`](web/legacy.html). | Retained for older workflows; not the primary paired interface. |

The paired implementation and its acceptance checks are recorded at specific historical commits in the [v2 status and receipt](docs/implementation/sofa_experiment_v2_status.md). The current default branch includes that work and later historical-sensitivity/DST changes; the old receipt is not a fresh check of this head. Merge, release, current hosted deployment, independent source fidelity, and clinical validation require separate evidence. The [historical TROPS completion report](docs/implementation/trops_fidelity_goal/COMPLETION_REPORT.md) covers source-mapped **synthetic** verification; execution against the study SQL remains unperformed.

## Quickstart

From the repository root, use Python **3.11 or newer** and `uv` with the committed lockfile. The example is a small synthetic E1 observation-density experiment in the room-air stratum; it does not run the full reference catalogue.

```bash
uv sync --locked --dev
uv run resp-sofa-experiment list
uv run resp-sofa-experiment run --entry E1_density --stratum room_air --replicates 200 --output artifacts/local/readme-e1-room-air
uv run resp-sofa-experiment verify-bundle artifacts/local/readme-e1-room-air
```

Choose a **new** output path for each run: the CLI refuses to replace an existing bundle. `run` reports `completed_patients` and its output path. The new directory contains `request.json`, `manifest.json`, `scores.csv`, `condition_summary.csv`, `paired_contrasts.csv`, `transitions.csv`, `reclassification.csv`, selected trace tables, metric metadata, and `SHA256SUMS`. A successful verification prints JSON with `"status": "verified"` and the scientific-data hash. These commands are defined in `src/sofa_resp_sim/workflows/experiment_cli.py`; the execution status for this README change is reported in its PR.

On the **same recorded Python/dependency and package source**, an optional exact replay writes to another new path:

```bash
uv run resp-sofa-experiment reproduce artifacts/local/readme-e1-room-air --output artifacts/local/readme-e1-room-air-reproduced
uv run resp-sofa-experiment verify-bundle artifacts/local/readme-e1-room-air-reproduced
```

If versions or source differ, the CLI rejects exact replay. Its explicit `--allow-runtime-difference` route uses exact discrete comparisons and the declared float tolerance rather than claiming byte-identical output. See [validation and bundle rules](docs/VALIDATION.md) before interpreting a replay as source fidelity.

## Paired experiment CLI and bundles

`resp-sofa-experiment run --request request.json --output NEW_PATH` accepts a normalized request; `explain BUNDLE --patient ID --condition ID` regenerates one saved patient's trace. `append` increases the total paired N without regenerating earlier patients. Directory and ZIP bundles record requests, per-patient scores, summaries, contrasts, transitions, trace selections, versions, and hashes. The [experiment controls](docs/EXPERIMENT_CONTROLS.md), [architecture](docs/ARCHITECTURE.md), and [artifact inventory](artifacts/README.md) hold the detailed contracts.

The complete 18-entry, four-stratum reference collection and its prespecified checks are described in [validation](docs/VALIDATION.md) and the [synthetic interpretation](artifacts/experiments_v2/INTERPRETATION.md). `make experiments-reference` is a much larger frozen run, not an onboarding command. Historical TROPS conditional C=0/1/≥2 views are **scenarios**, not population weights; see the [source-mapped contract](docs/TROPS_SCORING_CONTRACT.md). Reproducing archived bundles requires their recorded source and runtime, and the external study SQL has not been executed here.

## Web app

The default [`web/index.html`](web/index.html) uses a saved, labeled synthetic example while Pyodide starts, then runs Python scoring/simulation in a worker. For a local HTTP-served development view:

```bash
make stage-web
make serve
```

Open the URL printed by `python3 -m http.server`; opening `index.html` directly as a file is unsupported. `make serve` stages ignored `web/assets/py/` and `web/assets/data/` assets first. The worker uses the current paired experiment, workload, catalogue, explanation, rule-explorer, and bundle import/export payload functions; scenario/sweep calls remain for the legacy page. See [web app behavior and limits](docs/WEB_APP.md). A local browser run and a hosted Pages deployment are separate checks.

## Python API

Core scoring and simulation live in `src/sofa_resp_sim/core/`; `src/sofa_resp_sim/browser_contract.py` is the JSON-safe browser boundary. Existing compatibility imports such as `from sofa_resp_sim import score_respiratory` remain available. The worker calls the current paired functions as well as `get_app_config_payload`, `run_scenario_payload`, and `run_sweep_payload`; the full current API list is in [docs/WEB_APP.md](docs/WEB_APP.md). JavaScript does not compute SOFA scores or uncertainty intervals.

## CLI

The older `resp-sofa-sim` CLI remains a legacy scenario/sweep entry point. `uv run resp-sofa-sim --help` shows its options; comma-separated observation frequency, noise SD, and room-air threshold values create a sweep. Its Python compatibility wrappers remain under `src/sofa_resp_sim/resp_scoring.py`, `resp_simulation.py`, and `resp_utils.py`. Use `resp-sofa-experiment` above for the paired workbench.

## Common commands

- `make sync`: locked development environment.
- `make test`: native tests without browser e2e.
- `make e2e`: stage assets and run Playwright browser tests; browser installation may be required.
- `make verify`: stage, format check, lint, native tests, and e2e; inspect side effects before running.
- `make experiments-smoke`: frozen-catalogue check and bounded native experiment tests.
- `make experiments-install-check`: build and verify a clean-wheel replay.

These are defined in the [Makefile](Makefile). The quickstart above is the smaller runnable path; do not use `make verify`, reference generation, release, or deployment as an incidental README smoke test.

## Validation

[docs/VALIDATION.md](docs/VALIDATION.md) maps tests, bundle checks, installed reproduction, and reference evidence. A verified synthetic bundle establishes internal consistency under its recorded source/runtime; it is not population calibration, clinical validation, or equivalence to an independently run SQL scorer. The [clinical scope](docs/CLINICAL_SCOPE.md) and [reference interpretation](artifacts/experiments_v2/INTERPRETATION.md) explain missing evidence, conditional uncertainty, null results, and limits of inference. Current checks performed for this documentation change belong in its PR, separate from older acceptance receipts.

## Public release posture

The tracked tree is intended to contain source, documentation, tests, and small synthetic or aggregate artifacts. Local literature PDFs are ignored. The current [public release audit](docs/PUBLIC_RELEASE_AUDIT.md) reports no known PHI in the tracked tree, but old GitHub history or PR refs may still expose publisher PDF blobs. Review that audit before a public visibility or release decision. A documentation change does not clear that audit or authorize data sharing.

## More documentation

- [Architecture and source routes](docs/ARCHITECTURE.md) · [web app](docs/WEB_APP.md) · [provenance](docs/PROVENANCE.md) · [decisions](docs/DECISIONS.md)
- [Experiment controls](docs/EXPERIMENT_CONTROLS.md) · [validation](docs/VALIDATION.md) · [historical TROPS contract](docs/TROPS_SCORING_CONTRACT.md)
- [Artifact inventory](artifacts/README.md) · [paired implementation status](docs/implementation/sofa_experiment_v2_status.md)

## Package layout

`src/sofa_resp_sim/core/` owns scoring and simulation; `reporting/` owns paired requests, results, uncertainty and bundles; `workflows/` owns both CLIs; `web/` contains the static app and Pyodide worker; `scripts/` stages assets and maintains evidence; `tests/` covers core, contracts, workflows and browser behavior. See [architecture](docs/ARCHITECTURE.md) for the detailed map.

## Citation and license

See [CITATION.cff](CITATION.cff) for repository citation metadata and [LICENSE](LICENSE) for the software license. Code and simulation text are repository-authored unless otherwise noted. The simulation and checked-in examples do not grant rights to any external clinical data or third-party PDFs.

## Repository Notes

This is a research-software workspace; no manuscript version is expected here. Maintainer: Brian W. Locke (`@reblocke`). Use [GitHub Issues](https://github.com/reblocke/sofa_resp_sim/issues) or pull requests for repository-specific questions.
