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
