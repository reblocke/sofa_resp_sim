# AGENTS.md

## Project overview

`sofa_resp_sim` is a research-software repository for:
- respiratory SOFA scoring,
- simulation of respiratory observation/support patterns,
- a Streamlit validation and parameter-exploration applet.

The numerical source of truth lives in:
- `python/src/sofa_resp_sim/resp_scoring.py`
- `python/src/sofa_resp_sim/resp_utils.py`
- `python/src/sofa_resp_sim/resp_simulation.py`

The user-facing applet lives in:
- `python/src/sofa_resp_sim/web/`

## Instruction priorities

1. Keep scoring and simulation math truthful and centralized.
2. Keep repo metadata, docs, and commands aligned with the real package name and paths.
3. Keep checked-in artifacts small, reproducible, and documented.
4. Never commit PHI, patient-level raw extracts, or other restricted data.

## Use these skills

- Use `$implementation-strategy` when changing:
  - scoring logic,
  - simulation assumptions,
  - public schemas,
  - package layout,
  - CLI contracts.
- Use `$scientific-numerics-verification` when changing:
  - `resp_scoring.py`,
  - `resp_utils.py`,
  - `resp_simulation.py`,
  - scoring fixtures or reference distributions.
- Use `$streamlit-app-verification` when changing:
  - `python/src/sofa_resp_sim/web/*`,
  - applet defaults/presets,
  - app runbooks,
  - app-facing exports.
- Use `$packaging-integrity-check` when changing:
  - `pyproject.toml`,
  - environment/setup commands,
  - console scripts,
  - CI/tooling commands.
- Use `$docs-sync` after substantive behavior changes.
- Use `$artifact-digest-refresh` when changing validation artifacts or their generation path.
- Use `$repo-governance-sync` when changing:
  - `.github/*`,
  - `CONTRIBUTING.md`,
  - `SECURITY.md`,
  - `SUPPORT.md`,
  - `CODE_OF_CONDUCT.md`,
  - `CITATION.cff`.
- Use `$pr-draft-summary` when work is ready for review.

## Canonical commands

```bash
uv sync --dev
uv run pytest -q
uv run ruff check .
uv run resp-sofa-sim --help
uv run streamlit run python/src/sofa_resp_sim/web/applet_streamlit.py
```

## Repository map

- `python/src/sofa_resp_sim/`
  - package code
- `python/src/sofa_resp_sim/web/`
  - Streamlit UI, request validation, app services
- `python/tests/`
  - package and app tests
- `tests/`
  - repository contract tests
- `docs/`
  - canonical architecture, validation, scope, provenance, ADRs
- `artifacts/`
  - small checked-in validation summaries and evidence

## Engineering rules

- Keep the numerical core pure and importable.
- Do not re-implement scoring logic in the UI layer.
- Prefer explicit types and descriptive names.
- Make all public-facing commands and examples copy-pasteable.
- Update docs when package names, paths, commands, or outputs change.
- Keep root instructions short; push repeated procedures into skills.

## Definition of done

A change is not done until:
- relevant tests pass,
- lint passes for touched code,
- canonical docs are updated if behavior changed,
- validation artifacts are updated if their underlying logic changed,
- no stale package names or placeholder metadata remain in touched files.
