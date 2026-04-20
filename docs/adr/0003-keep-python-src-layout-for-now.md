# Keep the current `python/src` layout for the first hardening pass

- Status: accepted
- Date: 2026-04-20

## Context and Problem Statement

The repository already uses a nested `python/src/sofa_resp_sim` layout. Flattening to `src/sofa_resp_sim` may be cleaner, but it would create additional churn during the first hardening pass.

## Decision Drivers

- minimize unnecessary movement,
- improve packaging and docs first,
- keep diffs focused.

## Considered Options

- flatten immediately to `src/`
- keep `python/src/` for now and revisit later

## Decision Outcome

Chosen option: keep `python/src/` for now.

## Consequences

### Positive
- smaller migration surface
- packaging and CI can be stabilized first

### Negative
- layout remains slightly less conventional than root-level `src/`
- future flattening may still be worth considering
