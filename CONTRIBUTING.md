# Contributing

## Canonical development setup

This repository uses `uv` as the canonical development path.

```bash
uv sync --dev
make check
```

## Common commands

```bash
make sync
make lint
make test
make check
make app
```

## Branching and pull requests

- Use focused branches.
- Keep pull requests small enough to review coherently.
- Link issues when applicable.
- Summarize validation performed in the PR body.
- Update canonical docs when behavior, commands, or outputs change.

## Required checks before review

```bash
make check
```

If app-facing code changed, also run the relevant app verification tests.

## Code standards

- Keep respiratory scoring and simulation logic in the package core.
- Do not duplicate scoring logic in the Streamlit layer.
- Prefer explicit names and small functions with one level of abstraction.
- Keep user-facing commands and paths truthful.
- Add or update tests for changed behavior.

## Data and artifact policy

- Never commit PHI, patient-level raw extracts, or restricted datasets.
- Keep checked-in artifacts small, reproducible, and documented in `artifacts/README.md`.
- Document external references and checked-in non-code assets in `docs/PROVENANCE.md`.

## Architecture decisions

Record architectural or workflow-significant choices under:
- `docs/adr/`
