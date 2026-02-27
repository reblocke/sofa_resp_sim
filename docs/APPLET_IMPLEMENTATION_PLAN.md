# Respiratory SOFA Applet — Implementation Plan

## 1) Scope and success criteria
Implement a browser-based applet that wraps the existing simulation core so users can:
1. change key simulation parameters,
2. run single scenarios and targeted parameter sweeps,
3. compare resulting SOFA distributions against a reference,
4. inspect uncertainty and export outputs.

**Success criteria (v1):**
- Streamlit app available under `python/src/tcco2_accuracy/web/applet_streamlit.py`.
- Deterministic equivalence with current simulation functions for identical config/seed.
- Reference overlay + delta view for SOFA 0–4 probabilities.
- Basic sweep visualization and CSV export.
- Automated tests for config mapping and deterministic behavior.

## 2) Architecture decisions to carry forward
- **Simulation core remains unchanged** in `resp_simulation.py`; app layer only maps UI inputs to `SimulationConfig` and post-processes outputs.
- **Two-layer app structure (even in Streamlit):**
  - `web/view_model.py` (validation, coercion, defaults, preset handling),
  - `web/app_services.py` (execution, caching, summary/comparison metrics).
- **Reference input abstraction:**
  - Built-in baseline loader now,
  - parser interface for future uploaded CSV.

## 3) Work plan by milestone

### Milestone 1 — Scaffold + single-run baseline
**Deliverables**
- Create `python/src/tcco2_accuracy/web/` package.
- Add typed schemas/dataclasses for UI payload and normalized run request.
- Build Streamlit page sections: controls panel + distribution output.
- Wire run action to `run_replicates` and summarize `p_sofa_0..4`.

**Tasks**
- Add files:
  - `web/applet_streamlit.py`
  - `web/view_model.py`
  - `web/app_services.py`
  - `web/presets.py`
- Implement strict numeric range checks and default coercion.
- Add deterministic cache key from `(config, n_reps, seed)`.

**Validation gates**
- Unit tests for request parsing/defaults.
- Golden test: app service summary equals direct simulation call.

### Milestone 2 — Reference comparison + uncertainty views
**Deliverables**
- Built-in reference distribution loading from artifacts.
- Overlay bar chart and delta chart (scenario minus reference).
- Uncertainty tab with replicate-level summary stats and CIs.

**Tasks**
- Add `web/reference.py` for normalization/validation.
- Add metrics helpers: L1 distance and Jensen–Shannon distance.
- Add table output for `p_sofa_k` + CI.

**Validation gates**
- Tests for reference normalization (probability and count forms).
- Tests for divergence metric invariants.

### Milestone 3 — Sweep mode + exports
**Deliverables**
- Parameter sweep controls (`obs_freq_minutes`, `noise_sd`, `room_air_threshold`).
- Heatmap/table summary for selected sweep objective (`p_sofa_3plus`, etc.).
- Download buttons for replicate-level and summary CSV.

**Tasks**
- Extend service layer with sweep request builder.
- Add guardrails for sweep size and runtime warning thresholds.
- Implement export formatting with stable column order.

**Validation gates**
- Tests for sweep grid generation and shape invariants.
- Snapshot-style test for exported summary schema.

### Milestone 4 — Hardening + handoff decision
**Deliverables**
- Presets with version tag + reset behavior.
- Performance pass (target: 1k replicates in <2s on dev environment).
- Release notes + decision memo: keep Streamlit vs split API/frontend.

**Tasks**
- Add lightweight profiling harness script.
- Add docs page for running applet locally.
- Capture known limitations and future FastAPI transition steps.

**Validation gates**
- Smoke test for end-to-end run from UI control change to rendered charts.
- Regression tests for preset serialization roundtrip.

## 4) Proposed file-level implementation map
- `python/src/tcco2_accuracy/resp_simulation.py` (reuse only; no model-logic changes expected).
- `python/src/tcco2_accuracy/web/view_model.py` (input schema + validation).
- `python/src/tcco2_accuracy/web/app_services.py` (run/sweep orchestration and comparison metrics).
- `python/src/tcco2_accuracy/web/reference.py` (reference loaders/parsers).
- `python/src/tcco2_accuracy/web/applet_streamlit.py` (UI composition).
- `python/tests/test_web_view_model.py`.
- `python/tests/test_web_services.py`.
- `python/tests/test_web_reference.py`.

## 5) Execution order (practical sequence)
1. Implement Milestone 1 completely with tests.
2. Add built-in reference and comparison metrics (Milestone 2).
3. Add sweep + export mechanics (Milestone 3).
4. Run performance/hardening and write handoff decision memo (Milestone 4).

This ordering minimizes UI churn by stabilizing request/response contracts early.

## 6) Risks and mitigations
- **Risk:** UI controls drift from true `SimulationConfig` semantics.
  - **Mitigation:** single source of truth mapping tests + golden equivalence tests.
- **Risk:** Sweep runs become too slow for interactive use.
  - **Mitigation:** cap grid size in UI, progressive warnings, cached run reuse.
- **Risk:** Reference file schema mismatch.
  - **Mitigation:** strict parser with explicit error messages and schema tests.

## 7) Definition of done for this planning milestone
- Implementation plan document committed.
- `pytest` executed and result recorded.
- Continuity ledger updated with current plan status and open questions.
