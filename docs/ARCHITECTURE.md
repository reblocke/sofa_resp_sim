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
| `src/sofa_resp_sim/resp_*.py` | Compatibility wrappers | Preserve existing imports |
| `src/sofa_resp_sim/reporting/view_model.py` | Request schemas and validation | Browser-safe, no UI dependencies |
| `src/sofa_resp_sim/reporting/app_services.py` | Scenario/sweep orchestration | Calls the core simulation layer |
| `src/sofa_resp_sim/reporting/reference.py` | Reference distribution normalization | Supports CSV probability/count schemas |
| `src/sofa_resp_sim/reporting/presets.py` | Presets and serialization | Shared by tests and browser contract |
| `src/sofa_resp_sim/browser_contract.py` | Pyodide API | JSON-safe payload boundary |
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

All browser contract outputs must be JSON serializable and should return
structured `{"ok": false, "error": ...}` failures instead of uncaught tracebacks
at the worker boundary.

### CLI

- `resp-sofa-sim`
- `python -m sofa_resp_sim.workflows.cli`

### Static app

- `web/index.html`
- `web/pyodide_worker.js`
- `web/assets/js/app.js`
- `web/assets/css/styles.css`

Generated staged assets under `web/assets/py/` and `web/assets/data/` are
ignored and reproducible.

## Architecture invariants

1. Scoring rules live in `src/sofa_resp_sim/core/`.
2. JavaScript never computes SOFA scores, simulation summaries, uncertainty
   intervals, or reference deltas.
3. Browser-facing Python uses a narrow payload contract and returns plain JSON
   types plus CSV strings.
4. Web staging is allowlist-based and excludes tests, docs, workflow-only code,
   caches, and raw artifacts.
5. Checked-in artifacts remain small, aggregate/synthetic, and documented.
