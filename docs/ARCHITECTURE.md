# Architecture

## Purpose

`sofa_resp_sim` is organized around one rule:

**the respiratory scoring and simulation core is the source of truth; the applet is a presentation and orchestration layer.**

## Module map

| Module | Responsibility | Notes |
|---|---|---|
| `resp_utils.py` | small pure helpers | rounding and SpO2→PaO2 conversion |
| `resp_scoring.py` | respiratory SOFA scoring and diagnostics | public scoring entrypoint |
| `resp_simulation.py` | simulation engine and replicate/sweep helpers | depends on core utilities/scoring |
| `resp_sofa_runner.py` | CLI entrypoint | thin wrapper around simulation functions |
| `web/view_model.py` | input schemas, normalization, defaults | no scoring logic duplication |
| `web/app_services.py` | app orchestration, summary tables, uncertainty, exports | calls the simulation/core layer |
| `web/reference.py` | reference input normalization | app-facing support module |
| `web/presets.py` | app presets and serialization | app-facing support module |
| `web/applet_streamlit.py` | Streamlit UI composition | must stay thin |

## Dependency direction

Allowed direction:

```text
web/* -> simulation/core
CLI -> simulation/core
simulation -> scoring/utils
scoring -> utils
```

Disallowed direction:

```text
core/scoring -> web/*
utils -> web/*
simulation -> Streamlit UI
```

## Public entrypoints

### Python API
- `score_respiratory(...)`
- simulation helpers exposed from the package

### CLI
- `resp-sofa-sim`

### Streamlit applet
- `python/src/sofa_resp_sim/web/applet_streamlit.py`

## Architecture invariants

1. Scoring rules live in the package core.
2. Streamlit code does not redefine scoring logic.
3. Public docs and commands must use the current package name and paths.
4. Checked-in artifacts must remain small and reproducible.
5. Clinical wording must remain aligned with actual outputs and scope.

## Future extension point

The current Streamlit applet is the validated reference UI.
A future API/frontend split is possible, but should preserve:
- core math modules,
- request/response contracts,
- validation expectations,
- artifact and doc updates.
