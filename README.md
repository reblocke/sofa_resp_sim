# Project Title

One-paragraph summary of what this repository does and who it’s for.

## Quickstart

```bash
# 1) Create environment (conda/mamba)
mamba env create -f environment.yml   # or: conda env create -f environment.yml
mamba activate proj-env               # or: conda activate proj-env

# 2) Pre-commit hooks (optional but recommended)
pre-commit install

# 3) Run checks/tests
ruff check .
pytest -q
```

## Respiratory SOFA (SQL-parity)

- ``sofa_ts`` is a 24h bin anchored to ``admit_dts`` midnight; acute lead-in
  records (default −6h) are assigned to the admit-day bin.
- ``quartile`` splits each ``sofa_ts`` into 6h sub-bins labeled 1–4.
- FiO2 selection uses a 14-minute lookback (excluding current), a 0–5 minute
  look-forward (including current), then a 24h lookback; room air defaults to 21%.
- Measures-stage gating caps non-IMV/NIPPV records at 2 and applies the acute
  single-PF suppression rule when only one qualifying PF ratio exists without
  IMV/NIPPV support.

## Testing

- Run ``python -m pytest`` (or ``pytest -q``) from the repo root.
- Golden SQL-parity fixtures live in
  ``python/tests/test_resp_scoring_golden_fixtures.py`` and validate SpO2→PaO2
  conversion, FiO2 prioritization/lookbacks, PF ratios (including quartile-based
  suppression), support gating, baseline selection, and altitude thresholds.
- Inspect row-level outputs via ``RespiratoryScoreResult.event_level`` for
  intermediate columns (``pao2_calc``, ``fio2_lookback``, ``pf_ratio_temp``, etc.).

## Repo structure

```
├── src/                # Source code (importable package under src/ layout)
├── notebooks/          # Jupyter notebooks (keep light; move code to src/)
├── data/               # Data placeholders; do NOT commit restricted data
├── tests/              # Unit tests
├── environment.yml     # Reproducible env (conda/mamba)
├── pyproject.toml      # Tooling config (ruff, pytest) and project metadata
├── CONTRIBUTING.md     # How to contribute, run checks, style
├── CITATION.cff        # How to cite this work
└── README.md
```

## Reproducibility notes

- Pin dependencies in `environment.yml` (mamba preferred for speed/solver reliability).
- Keep credentials in `.env` (never commit). See `.env.example`.
- Record data provenance and transformations in `DATA_NOTES.md` (add if needed).
- Keep analysis code importable and testable: notebooks should call `src/` code.

## How to cite

See `CITATION.cff` or the GitHub “Cite this repository” box.

## License

Add a license (e.g., MIT) and any data-use restrictions.
