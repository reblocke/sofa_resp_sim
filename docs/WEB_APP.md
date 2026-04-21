# Web app

## Runtime model

The web app is a static GitHub Pages application. It does not use a backend.

Runtime flow:

1. `web/index.html` loads `web/assets/js/app.js`.
2. `app.js` starts `web/pyodide_worker.js`.
3. The worker loads Pyodide, `numpy`, and `pandas`.
4. The worker fetches `web/assets/py/manifest.json`.
5. Staged Python files are mounted under `/home/pyodide/src`.
6. Staged data files are mounted under `/home/pyodide/assets/data`.
7. JavaScript calls `sofa_resp_sim.browser_contract`.

JavaScript must not implement scoring, simulation, uncertainty, or reference
comparison logic.

## Staging

```bash
make stage-web
```

This runs `scripts/stage_web_python.py`, which:
- stages an explicit allowlist of browser-safe Python files,
- stages `artifacts/resp_sofa_sim_summary.csv`,
- writes `web/assets/py/manifest.json`,
- writes `web/.nojekyll`,
- excludes tests, docs, workflows, caches, and raw artifacts.

Generated directories are ignored:
- `web/assets/py/`
- `web/assets/data/`

## Local run

```bash
make serve
```

Then open the local HTTP server URL. Opening `web/index.html` directly from the
filesystem is not a supported runtime because Pyodide and worker fetches require
HTTP semantics.

The browser UI provides inline help for each scenario and sweep input. The help
copy is static presentation text in `web/assets/js/app.js`; scoring, simulation,
reference comparison, and uncertainty calculations still come from the Python
browser contract.

## Browser contract

Public functions:

```python
get_app_config_payload() -> dict
run_scenario_payload(payload: dict) -> dict
run_sweep_payload(payload: dict) -> dict
```

Contract rules:
- return JSON-serializable values only,
- include `ok: true` for successful payloads,
- include `ok: false` and a structured `error` object for validation failures,
- include CSV strings for browser downloads,
- preserve deterministic behavior for fixed seeds.

## Verification

```bash
make stage-web
make e2e
```

The e2e test starts a local static server, waits for Pyodide initialization,
runs a small scenario, runs a small sweep, checks rendered charts/tables, and
verifies CSV downloads are wired.
