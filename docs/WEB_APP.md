# Web app

## Runtime model

The web app is a static GitHub Pages application. It does not use a backend.

Runtime flow:

1. `web/index.html` loads `web/assets/js/investigation.js`.
2. `investigation.js` displays the saved example, then starts `web/pyodide_worker.js`.
3. The worker loads Pyodide, `numpy`, `pandas`, `scipy`, and `tzdata`.
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
- stages `artifacts/resp_sofa_sim_summary.csv` and `artifacts/saved_experiment_v2.json`,
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

The historical UI at `legacy.html` provides scenario and sweep input help. The help
copy is static presentation text in `web/assets/js/app.js`; scoring, simulation,
reference comparison, and uncertainty calculations still come from the Python
browser contract.

## Browser contract

Public functions:

```python
get_app_config_payload() -> dict
run_scenario_payload(payload: dict) -> dict
run_sweep_payload(payload: dict) -> dict
run_experiment_payload(payload: dict, *, on_progress=None) -> dict
get_experiment_workload_payload(payload: dict) -> dict
explain_experiment_payload(payload: dict) -> dict
get_experiment_catalogue_payload(payload: dict) -> dict
run_rule_explorer_payload(payload: dict) -> dict
export_experiment_bundle_payload(payload: dict) -> dict
import_experiment_bundle_payload(payload: dict) -> dict
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

## Paired experiment API (implementation in progress)

The worker accepts `experiment` and `explain` messages for the v2 Python API.
Requests cross the worker boundary as strict JSON so null values and integral
numbers normalize consistently in native Python and Pyodide. Nonfinite numbers
fail before execution. The default investigation interface displays a saved
200-patient synthetic example before Python initializes. It is labeled as saved,
not a new run or a full reference demonstration.

Paired results include patient scores, condition summaries, paired contrasts,
transition cells with contributor IDs, reclassification and metric units.
Explanations regenerate only the selected patient. See the implementation status
for verified scope; these APIs do not imply the complete workbench is delivered.

The `catalogue` worker message lists the finite demonstrations and returns a
normalized selected request. Supplying `base` expands comparator/condition
overrides against that exact edited base; it does not silently reapply preset
generation settings. The `rule_explorer` message evaluates deterministic SpO2 or
measured-PaO2 values against explicit fixed support configurations, with one or
two records 15 minutes apart. Both are available through the experiment selector.

The `export_bundle` worker message takes the immutable completed result and an
optional patient ID, returning a base64 ZIP. `import_bundle` takes that archive,
checks hashes/versions and reconciles tables to patient rows before returning
results. Archive imports are bounded to 64 MiB compressed and expanded content.
No ZIP paths are extracted into the host filesystem. These worker APIs have
actual Pyodide coverage and visible export/import controls. Edited inputs mark
the prior result stale; its bundle retains the original immutable request.

## Preview limits and cancellation

Python checks workload before allocation: at most 200 patients, 1,600 scoring
evaluations, 720,000 generated minutes, 400,000 documented events, and 10,000
generated minutes per patient across cached generators. All 72 catalogue
previews fit this envelope. Larger runs use an exported request with the CLI.
These counts describe work, not a prediction of peak RAM.

Progress reports attempted patients, completed patients and scoring evaluations.
Cancellation terminates and recreates the worker while preserving edited inputs.
Worker messages are serialized; responses from an earlier worker generation
cannot replace the current result.

`uv run python scripts/measure_preview_runtime.py` measures the production worker
in the local browser. Its receipt reports initialization and 200-patient E1/E5
elapsed times. Browser heap snapshots do not measure worker/Wasm peak memory.

## Encounter evidence display

The oxygenation plot uses crosses for excluded observed points and rings for
all determining events, including ties, using Python-returned reason codes and
IDs. Missing values remain unavailable in the table rather than being plotted
as zero. The score table exposes detail and final support caps, suppression and
source age. A separate source-record table shows FiO2 documentation measurement
and availability times and source IDs. Low-flow traces add a separate flow panel
in L/min; FiO2 remains on its fraction panel and is labeled as a proxy where
inferred. Every trace panel shares the same time domain.

Bundle file size is checked before the browser reads it into memory. The UI also
asks the Python workload estimator to check a one-patient reconstruction before
explaining or re-exporting a result; imported results do not bypass the trace
budget. Larger traces use the CLI. A worker crash leaves the prior result and
edited request intact, disables execution until restart, and cannot publish a
failed run as a completed example.

The [control scope inventory](EXPERIMENT_CONTROLS.md) describes each editable
mechanism, conditional inactivity and the difference between a changed
intermediate value and an unchanged discrete score.

Methods and export offers direct CSV downloads for absolute estimates, paired
contrasts, transitions and synthetic patient scores. They serialize the immutable
result rows; a stale result adds `stale-original-` to the filename. The complete
ZIP remains the reproducible package with requests, metric metadata and hashes.

The baseline-opportunity matrix uses a declared color range. Signed probability
changes share a -100 to +100 percentage-point range centered on white zero;
unavailable cells are gray and labeled U. Count outcomes use a labeled symmetric
range for paired differences. Numeric labels remain visible independently of color.
