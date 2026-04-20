# Decisions

This file summarizes active implementation decisions. Longer-lived decisions are
recorded as ADRs under `docs/adr/`.

## Active decisions

- Python remains the only source of truth for scoring, simulation, uncertainty,
  and reference comparison.
- The package layout is root `src/`, with tests under root `tests/`.
- Top-level `sofa_resp_sim.resp_scoring`, `resp_simulation`, and `resp_utils`
  wrappers preserve existing imports.
- The static browser app uses Pyodide in a web worker and calls only
  `sofa_resp_sim.browser_contract`.
- Generated browser staging outputs are ignored and recreated with
  `make stage-web`.
- Streamlit is no longer an active runtime or dependency.
- `uv` is the canonical environment and lockfile workflow.

## Deferred decisions

- Public repository publication from a clean history remains separate from this
  migration; see `docs/PUBLIC_RELEASE_AUDIT.md`.
- Release/Zenodo automation remains deferred.
- Any model changes, new simulation assumptions, or clinical interpretation
  changes require separate validation and documentation.
