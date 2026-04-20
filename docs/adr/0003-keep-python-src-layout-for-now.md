# Keep the current `python/src` layout for the first hardening pass

- Status: superseded by `0005-streamlit-to-pages.md`
- Date: 2026-04-20

## Context and Problem Statement

The repository used a nested `python/src/sofa_resp_sim` layout during the first
hardening pass. Flattening to root `src/sofa_resp_sim` was deferred to avoid
mixing packaging movement with governance cleanup.

## Decision Drivers

- minimize unnecessary movement,
- improve packaging and docs first,
- keep diffs focused.

## Considered Options

- flatten immediately to `src/`
- keep `python/src/` for now and revisit later

## Decision Outcome

Chosen option at the time: keep `python/src/` temporarily.

This decision was later superseded by the Pages/Pyodide migration, which moved
the package to root `src/`.

## Consequences

### Positive
- smaller migration surface
- packaging and CI can be stabilized first

### Negative
- layout remains slightly less conventional than root-level `src/`
- future flattening may still be worth considering
