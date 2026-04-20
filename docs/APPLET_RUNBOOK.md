# Respiratory SOFA Applet Runbook

## 1) Local launch
From repo root:

```bash
uv sync --dev
uv run streamlit run python/src/sofa_resp_sim/web/applet_streamlit.py
```

Or use the Makefile wrapper:

```bash
make app
```

Do not use `uv run resp-sofa-applet` as the normal launch path. That console
script executes the app module in bare mode and Streamlit will warn that it
should be run through `streamlit run`.

## 2) Sidebar control workflow
1. Choose `Run mode` (`Single scenario` or `Parameter sweep`).
2. Select presets:
   - `Scenario preset`
   - `Sweep preset`
3. Click `Reset controls to selected preset` when you want to reapply preset defaults.
4. Click `Run simulation`.

Preset schema version is shown in the sidebar. This version is used by preset serialization helpers for deterministic roundtrips.

## 3) Validation commands
Run these from repo root before release:

```bash
make check
uv run pytest -q python/tests/test_streamlit_app_smoke.py
uv run pytest -q python/tests/test_web_*
```

## 4) Performance profiling
Profile single-scenario runtime:

```bash
uv run python python/scripts/profile_applet_performance.py \\
  --n-reps 1000 --repeats 5 --seed 0 --target-seconds 2.0 \\
  --output-csv artifacts/resp_applet_m4_performance.csv
```

## 5) Smoke tests

Native Streamlit smoke coverage runs inside pytest without a browser:

```bash
uv run pytest -q python/tests/test_streamlit_app_smoke.py
```

For a manual headless server check:

```bash
uv run streamlit run python/src/sofa_resp_sim/web/applet_streamlit.py \\
  --server.headless true \\
  --server.address 127.0.0.1 \\
  --server.port 8511
```

Open [http://127.0.0.1:8511](http://127.0.0.1:8511) to verify:
- charts render after control changes,
- sweep heatmaps render for valid presets,
- CSV download buttons return non-empty files.

## 6) Known limitations
- Large synchronous sweeps can still feel slow near the guardrail (`50,000` total runs).
- Built-in reference is currently fixed to artifact input (upload workflow is deferred).
- Streamlit state is session-local and not shared across clients.
