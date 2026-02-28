# Respiratory SOFA Applet Handoff Decision (Milestone 4)

## Decision
Use a two-track approach:
1. Keep the current Streamlit applet as the internal validation and parameter-exploration surface.
2. Plan a production transition to `FastAPI + frontend` with background execution for heavy runs.

## Rationale
- Milestones 1–4 established deterministic mappings, uncertainty views, sweeps, and exports.
- Preset contracts and regression tests are now in place for reproducibility.
- Performance profiling of single-scenario `n_reps=1000` is above the target budget in this environment, making synchronous request/response UX fragile for broader use.
- Splitting backend/frontend does not change simulation math, but enables:
  - asynchronous job execution,
  - queueing/retries/cancellation,
  - multi-user reliability,
  - clearer API contracts for external integrations.

## Recommendation for next milestone
1. Freeze Streamlit as a validated reference UX for scientific review.
2. Build `POST /simulate/run` and `POST /simulate/sweep` endpoints around existing service functions.
3. Add async job orchestration for sweep jobs near or above the current guardrail.
4. Keep export schemas and preset versioning unchanged to preserve continuity.

## Non-goals in this handoff
- No changes to `resp_simulation.py` math.
- No changes to study-level uncertainty assumptions.
- No changes to existing Milestone 1–3 output schemas.
