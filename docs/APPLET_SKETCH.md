# Respiratory SOFA Simulation Applet — Conversion Sketch

## 1) Product intent
Build a browser-based applet that lets a user:
1. modify simulation parameters,
2. run one scenario or a parameter sweep,
3. compare resulting SOFA score distributions against a reference distribution,
4. inspect uncertainty across replicates.

This should wrap the current simulation core (`SimulationConfig`, `run_replicates`, `run_parameter_sweep`) without rewriting the model math.

## 2) Recommended first implementation path

### Phase A (fastest): Streamlit single-process app
- **Why**: minimal boilerplate, Python-only, good for quick internal validation.
- **How**:
  - put UI in `python/src/tcco2_accuracy/web/applet_streamlit.py`,
  - call simulation functions directly in-process,
  - use Plotly for interactive charts.

### Phase B (production): FastAPI backend + React/Vue frontend
- **Why**: better scalability, async jobs, cleaner API boundaries.
- **How**:
  - backend endpoints for simulation runs + presets + exports,
  - frontend controls and charting (e.g., ECharts/Plotly),
  - optional task queue for large sweeps.

## 3) Applet control surface (parameter inputs)

### Scenario controls (single-run config)
Expose the current `SimulationConfig` fields as grouped controls:

1. **Timeline**
   - `admit_dts`
   - `acute_start_hours`, `acute_end_hours`
   - `include_baseline`, `baseline_days_before`, `baseline_duration_hours`

2. **SpO2 trajectory process**
   - `spo2_mean`, `spo2_sd`, `ar1`
   - `desat_prob`, `desat_depth`, `desat_duration_minutes`

3. **Measurement model**
   - `measurement_sd`
   - `spo2_rounding` (`int`, `one_decimal`, raw)

4. **Support assignment policy**
   - `room_air_threshold`
   - optionally advanced thresholds: `low_flow_threshold`, `hfnc_threshold`, `nippv_threshold`
   - `support_based_on_observed`

5. **FiO2 / support settings**
   - per-support mean/sd for HFNC/NIPPV/IMV (`fio2_settings`)
   - `fio2_meas_prob`
   - `oxygen_flow_range`

6. **Scoring assumptions**
   - `altitude_factor`

7. **Simulation controls**
   - `n_reps`
   - `seed`
   - run mode: single condition vs sweep

### Sweep controls
For sweep mode, allow comma/range inputs for:
- `obs_freq_minutes`
- `noise_sd` (maps to `measurement_sd`)
- `room_air_threshold`

## 4) Reference distribution design
Support two options:

1. **Built-in reference**
   - load a default reference distribution from `artifacts/resp_sofa_sim_summary.csv` (or a curated baseline JSON).

2. **User-provided reference**
   - upload CSV with required columns:
     - either probability form: `p_sofa_0 ... p_sofa_4`,
     - or count form: `sofa_pulm`, `count` (to be normalized in app).

Comparison outputs:
- overlaid bar chart (`p_sofa_k` scenario vs reference),
- delta chart (`scenario - reference` by score),
- optional divergence metrics (L1 distance, Jensen–Shannon distance).

## 5) UX layout sketch

### Left panel: controls
- Presets: “Default”, “High noise”, “Sparse observations”, “Conservative oxygen policy”.
- Basic/Advanced toggle.
- Reproducibility block: seed + copy/share config JSON.

### Main panel: results tabs
1. **Distribution**
   - scenario SOFA distribution (0..4)
   - overlay reference
2. **Uncertainty**
   - replicate violin/box plots of `count_pf_ratio_acute`
   - CI table for `p_sofa_k`
3. **Sweep grid**
   - heatmaps (e.g., `p_sofa_3plus` across noise × obs frequency)
4. **Raw data**
   - downloadable replicate-level CSV
   - downloadable summary CSV

## 6) Minimal backend contract (if split architecture)

### `POST /simulate/run`
Input:
- serialized `SimulationConfig`
- `n_reps`, `seed`
- optional `reference_id` or inline reference payload

Output:
- summary metrics (`p_sofa_0..4`, `mean_count_pf_ratio_acute`, `p_single_pf_suppressed`)
- replicate-level rows (optional toggle)
- comparison metrics vs reference

### `POST /simulate/sweep`
Input:
- base config
- arrays for `obs_freq_minutes`, `noise_sd`, `room_air_threshold`
- `n_reps`, `seed`

Output:
- sweep summary table
- optional replicate table tagged with sweep parameters

### `GET /presets`
- returns named parameter presets (with version tag).

## 7) Technical implementation notes
- Keep model functions pure; app layer should only:
  - parse/coerce UI input,
  - call simulation functions,
  - aggregate comparison metrics.
- Cache deterministic runs by hash of `(config, n_reps, seed)`.
- Add strict input validation for all numeric ranges.
- Use background execution for large sweeps (>~10k total replicates).

## 8) Validation and quality gates
Before applet release:
1. Unit tests for UI-to-config mapping (especially threshold derivation and defaults).
2. Golden test: applet API run equals CLI/API baseline for same seed/config.
3. Smoke test for built-in reference comparison pipeline.
4. Performance budget checks (e.g., single run <2s for 1k reps on dev machine).

## 9) Concrete next coding steps
1. Add `web/` package scaffold and app config schemas.
2. Implement streamlit prototype with:
   - controls for core parameters,
   - run button + cached simulation,
   - distribution overlay vs built-in reference.
3. Add export/download buttons and preset handling.
4. Add tests for config parsing + deterministic outputs.
5. Decide whether to harden Streamlit or transition to FastAPI+frontend.
