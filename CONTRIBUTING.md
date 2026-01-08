# Contributing

## Dev setup

1. Create environment (mamba preferred):

   ```bash
   mamba env create -f environment.yml
   mamba activate proj-env
   ```

2. Install pre-commit hooks (recommended):

   ```bash
   pre-commit install
   ```

## Branching & PRs

- Use feature branches: `feat/short-topic`, `fix/bug-123`.
- Keep PRs small and focused; link issues when relevant.
- Require review; checks must pass before merge.

## Tests & checks

```bash
ruff check .
ruff format .
pytest -q
```

Add tests in `tests/` for new or changed behavior.

## Style

- Ruff enforces linting and formatting.
- Prefer explicit types in public functions.
- Keep notebooks light; move logic to `src/` and import.

## Data

- Never commit PHI/PII or raw restricted data.
- Use `data/` for placeholders and derived small examples only.
- Store pointers and provenance (sources, dates, filters) in repo docs.
