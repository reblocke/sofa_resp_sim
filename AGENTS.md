# AGENTS.md

## Project overview

`sofa_resp_sim` is a research-software repository for respiratory SOFA scoring,
simulation, and static browser exploration through GitHub Pages/Pyodide.

The source of truth for scoring and simulation lives in:
- `src/sofa_resp_sim/core/resp_scoring.py`
- `src/sofa_resp_sim/core/resp_utils.py`
- `src/sofa_resp_sim/core/resp_simulation.py`

The browser-facing API is:
- `src/sofa_resp_sim/browser_contract.py`

The static app lives in:
- `web/`

## Instruction priorities

1. Keep scoring and simulation math centralized in Python.
2. Do not reimplement model logic in JavaScript.
3. Keep package metadata, docs, commands, and staged assets aligned with the real layout.
4. Never commit PHI, patient-level raw extracts, restricted data, secrets, or publisher PDFs.

## Use these skills

- Use `$implementation-strategy` when changing scoring logic, simulation assumptions,
  public schemas, package layout, browser payloads, or CLI contracts.
- Use `$scientific-numerics-verification` when changing core scoring/simulation,
  scoring fixtures, reference distributions, or simulation assumptions.
- Use `$pages-pyodide-verification` when changing `web/`,
  `scripts/stage_web_python.py`, `src/sofa_resp_sim/browser_contract.py`,
  app presets/defaults, or browser-facing exports.
- Use `$packaging-integrity-check` when changing `pyproject.toml`, dependency
  declarations, console scripts, setup commands, CI, or build configuration.
- Use `$docs-sync` after substantive behavior, command, package layout, artifact,
  or public-output changes.
- Use `$artifact-digest-refresh` when changing checked-in validation artifacts
  or documented artifact-generation evidence.
- Use `$repo-governance-sync` when changing `.github/*`, contribution/security/
  support files, conduct files, or citation metadata.
- Use `$pr-draft-summary` when work is ready for review.

## Canonical commands

```bash
uv sync --dev
make stage-web
make test
make e2e
make verify
uv run resp-sofa-sim --help
```

## Repository map

- `src/sofa_resp_sim/core/` - pure scoring/simulation/utilities.
- `src/sofa_resp_sim/reporting/` - browser-safe request, preset, reference,
  uncertainty, and export helpers.
- `src/sofa_resp_sim/browser_contract.py` - Pyodide-facing public API.
- `src/sofa_resp_sim/workflows/` - CLI workflows.
- `web/` - static Pages app and Pyodide worker.
- `scripts/` - staging and local maintenance helpers.
- `tests/` - core, contract, workflow, and e2e tests.
- `docs/` - architecture, validation, scope, provenance, and ADRs.
- `artifacts/` - small checked-in validation summaries and evidence.

## Engineering rules

- Keep the numerical core pure and importable.
- Keep JavaScript as presentation, worker orchestration, and export UX only.
- Stage browser Python through `scripts/stage_web_python.py`; do not hand-edit
  generated `web/assets/py/` or `web/assets/data/` outputs.
- Prefer explicit types, stable payload schemas, and JSON-serializable browser
  contract outputs.
- Update docs when package names, paths, commands, payloads, or outputs change.

## Definition of done

A change is not done until:
- relevant tests pass,
- lint/format checks pass for touched code,
- canonical docs are updated if behavior or workflow changed,
- validation artifacts are updated if their underlying logic changed,
- no stale package names, inactive app references, or placeholder metadata remain
  in active public-facing files.
