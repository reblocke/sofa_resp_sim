# TcCO2 Accuracy (Python): Respiratory SOFA SQL-Parity + Simulation

This repository currently contains a Python implementation of respiratory SOFA
scoring logic that matches the project SQL rules, plus a simulation framework to
stress-test scoring behavior under different observation and support patterns.

## Current functionality

- Score respiratory SOFA from event-level observations (`SpO2`, optional measured
  `PaO2`, FiO2 fields, support modality, room-air indicator, flow rate).
- Preserve SQL-parity intermediate fields for debugging and validation
  (FiO2 lookbacks/look-forward, PaO2 source priority, PF ratio, rubric score,
  measures-stage gating fields).
- Apply acute/baseline respiratory selection and suppression rules, returning:
  `sofa_pulm`, `sofa_pulm_bl`, `sofa_pulm_delta`, and qualifying PF counts.
- Simulate synthetic encounters and run Monte Carlo sweeps to estimate score
  distributions as assumptions change (frequency, noise, support thresholds).
- Validate behavior with unit tests and golden fixtures that encode SQL-parity
  expectations.

## Key modules

- `python/src/tcco2_accuracy/resp_scoring.py`
  - Core scoring function: `score_respiratory(...)`
  - Returns `RespiratoryScoreResult`, including `event_level` diagnostics.
- `python/src/tcco2_accuracy/resp_simulation.py`
  - Encounter simulator plus `run_replicates(...)` and `run_parameter_sweep(...)`.
- `python/src/tcco2_accuracy/resp_sofa_runner.py`
  - CLI runner for simulation sweeps.
- `python/src/tcco2_accuracy/resp_utils.py`
  - Oracle-style rounding and SpO2 to PaO2 conversion helper.

## Quickstart

```bash
# 1) Create environment (mamba or conda)
mamba env create -f environment.yml
mamba activate proj-env

# 2) Optional dev hooks
pre-commit install

# 3) Run tests and lint
python -m pytest
ruff check .
```

## Run the simulation CLI

From repo root:

```bash
PYTHONPATH=python/src python -m tcco2_accuracy.resp_sofa_runner \
  --replicates 200 \
  --obs-freq 15 \
  --noise-sd 1.0 \
  --room-air-threshold 94 \
  --seed 0
```

Expected output:

- A one-row or multi-row summary table (depending on parameter list sizes) with:
  `obs_freq_minutes`, `noise_sd`, `room_air_threshold`, `n_reps`,
  `mean_count_pf_ratio_acute`, `p_single_pf_suppressed`, and `p_sofa_0..p_sofa_4`.

To write CSV instead of printing:

```bash
PYTHONPATH=python/src python -m tcco2_accuracy.resp_sofa_runner --output artifacts/resp_sofa_sim_summary.csv
```

## Respiratory SOFA SQL-parity notes

- `sofa_ts` is a 24-hour bin anchored to `admit_dts` day boundaries.
- `quartile` splits each `sofa_ts` into 6-hour bins labeled `1..4`.
- FiO2 association is selected in this order:
  minute lookback (`-14 to -1 min`), minute look-forward (`0 to +5 min`),
  then 24-hour lookback, with room air defaulting to 21%.
- Measures-stage gating caps non-IMV/NIPPV respiratory scores at 2.
- Acute single-PF suppression can set acute respiratory score to 0 when only one
  qualifying PF record exists and no IMV/NIPPV support is present.

## Testing

- Run `python -m pytest` from repo root.
- Golden fixtures: `python/tests/test_resp_scoring_golden_fixtures.py`.
- Core tests: `python/tests/test_resp_scoring.py`.
- Smoke test: `tests/test_smoke.py`.

## Repository layout

```text
python/src/tcco2_accuracy/   # Python package (scoring + simulation)
python/tests/                # SQL-parity and unit tests
tests/                       # Project-level smoke test(s)
artifacts/                   # Small generated summaries/tables
docs/                        # Runbooks and notes
data/                        # Placeholder data directory
environment.yml              # Conda/mamba environment
pyproject.toml               # Tooling config + script entrypoint metadata
```

## Citation and license

- Citation metadata: `CITATION.cff`
- License: `LICENSE`
