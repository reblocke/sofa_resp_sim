---
name: implementation-strategy
description: Plan changes to respiratory scoring, simulation assumptions, public contracts, or package boundaries.
---

# Implementation Strategy

Use a plan when scientific or interface choices need resolving. Inspect the affected source, invariants, tests, and evidence; identify the contract to preserve and the verification needed. Continue with authorized implementation once those choices are clear.

- Scoring truth lives in `src/sofa_resp_sim/core/resp_scoring.py`, `src/sofa_resp_sim/core/resp_utils.py`, and `src/sofa_resp_sim/core/resp_simulation.py`.
- Browser-facing code calls the Python contract instead of duplicating model logic.
- Package identity remains `sofa_resp_sim`.
- Changes to scoring assumptions or public schemas require an explicit decision; update affected docs and artifacts when that decision changes behavior.
