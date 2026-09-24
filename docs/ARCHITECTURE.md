# Architecture

## Purpose

`sofa_resp_sim` is organized around one rule: respiratory scoring and simulation
remain Python source-of-truth modules, while CLI and browser surfaces call those
modules through thin contracts.

## Module map

| Path | Responsibility | Notes |
|---|---|---|
| `src/sofa_resp_sim/core/resp_utils.py` | Pure helpers | Oracle-style rounding and SpO2-to-PaO2 conversion |
| `src/sofa_resp_sim/core/resp_scoring.py` | Respiratory SOFA scoring | Public scoring entrypoint and diagnostics |
| `src/sofa_resp_sim/core/resp_simulation.py` | Simulation engine | Replicates and parameter sweeps |
| `src/sofa_resp_sim/core/experiment_config.py` | v2 scientific configuration | Strict units, profiles and normalized condition identity |
| `src/sofa_resp_sim/core/paired_simulation.py` | v2 latent patient generation | Fixed minute grid and stable patient/process streams |
| `src/sofa_resp_sim/core/observation.py` | v2 observation/documentation | Independent schedules and observable event records |
| `src/sofa_resp_sim/core/experiment_scoring.py` | Bounded v2 scoring | Observable evidence, source selection and exclusion traces |
| `src/sofa_resp_sim/reporting/experiment_service.py` | Paired orchestration | Per-patient generation/cache and selected trace reconstruction |
| `src/sofa_resp_sim/reporting/experiment_results.py` | Paired estimands | Explicit denominators, transitions and pointwise MC uncertainty |
| `src/sofa_resp_sim/reporting/experiment_catalogue.py` | Finite experiment definitions | Prespecified comparisons; expands edited bases without resets |
| `src/sofa_resp_sim/reporting/rule_explorer.py` | Deterministic rule grid | Event versus explicit encounter scoring |
| `src/sofa_resp_sim/reporting/experiment_bundle.py` | Portable synthetic bundles | Typed CSV, hashes, versions, ZIP import/export |
| `src/sofa_resp_sim/reporting/experiment_request.py` | v2 request normalization | One resolved base/comparator/condition contract |
| `src/sofa_resp_sim/resp_*.py` | Compatibility wrappers | Preserve existing imports |
| `src/sofa_resp_sim/reporting/view_model.py` | Request schemas and validation | Browser-safe, no UI dependencies |
| `src/sofa_resp_sim/reporting/app_services.py` | Scenario/sweep orchestration | Calls the core simulation layer |
| `src/sofa_resp_sim/reporting/reference.py` | Reference distribution normalization | Supports CSV probability/count schemas |
| `src/sofa_resp_sim/reporting/presets.py` | Presets and serialization | Shared by tests and browser contract |
| `src/sofa_resp_sim/browser_contract.py` | Pyodide API | JSON-safe payload boundary |
| `src/sofa_resp_sim/data/` | Packaged reference fallback | Used outside repo/staged web layouts |
| `src/sofa_resp_sim/workflows/experiment_cli.py` | Paired experiment CLI | Run, explain, verify, reproduce and append |
| `src/sofa_resp_sim/workflows/cli.py` | CLI entrypoint | `resp-sofa-sim` |
| `scripts/stage_web_python.py` | Web staging | Allowlists browser-safe Python and data |
| `web/` | Static app | HTML/CSS/JS plus Pyodide worker |

## Dependency direction

Allowed direction:

```text
web JavaScript -> pyodide_worker.js -> browser_contract -> reporting -> core
CLI -> core
reporting -> core
simulation -> scoring/utils
scoring -> utils
```

Disallowed direction:

```text
core -> reporting
core -> browser_contract
Python core -> JavaScript
JavaScript -> scoring decisions
```

## Public entrypoints

### Python API

- `sofa_resp_sim.score_respiratory`
- `sofa_resp_sim.SimulationConfig`
- `sofa_resp_sim.run_parameter_sweep`
- compatibility imports from `sofa_resp_sim.resp_scoring`,
  `sofa_resp_sim.resp_simulation`, and `sofa_resp_sim.resp_utils`

### Browser contract

- `get_app_config_payload()`
- `run_scenario_payload(payload)`
- `run_sweep_payload(payload)`
- `run_experiment_payload(payload)`
- `explain_experiment_payload(payload)`
- `get_experiment_catalogue_payload(payload)`
- `run_rule_explorer_payload(payload)`
- `export_experiment_bundle_payload(payload)`
- `import_experiment_bundle_payload(payload)`

All browser contract outputs must be JSON serializable and should return
structured `{"ok": false, "error": ...}` failures instead of uncaught tracebacks
at the worker boundary.

### CLI

- `resp-sofa-sim`
- `resp-sofa-experiment`
- `python -m sofa_resp_sim.workflows.cli`

### Static app

- `web/index.html`
- `web/pyodide_worker.js`
- `web/assets/js/investigation.js` and `web/assets/css/investigation.css` (default paired page)
- `web/assets/js/app.js` and `web/assets/css/styles.css` (legacy scenario/sweep page)

Generated staged assets under `web/assets/py/` and `web/assets/data/` are
ignored and reproducible.

Installed package use falls back to the packaged reference CSV under
`sofa_resp_sim.data` when repo and Pyodide filesystem paths are unavailable.

## Architecture invariants

The paired experimental workbench is implemented on the current default branch
alongside the retained legacy entry points. The default investigation interface
uses one editable request and a separate immutable completed result; the
historical scenario/sweep UI remains at `web/legacy.html`. The
[paired implementation status](implementation/sofa_experiment_v2_status.md)
records acceptance at its stated historical commit, not release, current
deployment, or clinical/source-fidelity validation.

1. Scoring rules live in `src/sofa_resp_sim/core/`.
2. JavaScript never computes SOFA scores, simulation summaries, uncertainty
   intervals, or reference deltas.
3. Browser-facing Python uses a narrow payload contract and returns plain JSON
   types plus CSV strings.
4. Web staging is allowlist-based and excludes tests, docs, workflow-only code,
   caches, and raw artifacts.
5. Checked-in artifacts remain small, aggregate/synthetic, and documented.

## Historical sensitivity extension

The v3 historical profile, normalized context boundary, conditional C views and
qualification limits are documented in [TROPS_SCORING_CONTRACT.md](TROPS_SCORING_CONTRACT.md).
The original v2 contract and reference evidence remain preserved. New frozen
requests live in `experiments/trops_v1/`; new evidence uses
`artifacts/trops_sensitivity_v1/`. Historical mapping is not SQL execution
validation or current-production equivalence.
