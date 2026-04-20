# Contributing

## Canonical development setup

This repository uses `uv` as the canonical development path.

```bash
uv sync --dev
make test
```

## Common commands

```bash
make sync
make lint
make test
make stage-web
make e2e
make verify
make serve
```

## Branching and pull requests

- Use focused branches.
- Keep pull requests small enough to review coherently.
- Link issues when applicable.
- Summarize validation performed in the PR body.
- Update canonical docs when behavior, commands, or outputs change.

## Required checks before review

```bash
make test
```

If browser-facing code changed, also run:

```bash
make e2e
```

## Code standards

- Keep respiratory scoring and simulation logic in the package core.
- Do not duplicate scoring or simulation logic in JavaScript.
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
