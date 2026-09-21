# Clinical scope

## Intended use

This repository is research software for:
- respiratory SOFA scoring logic,
- simulation of respiratory observation/support scenarios,
- validation and exploration of assumptions through a static browser app.

The browser app runs locally in the user's browser through Pyodide. It is a
research and validation surface over the same Python scoring/simulation code.

## Not intended as

This repository is not presented as:
- a regulated medical device,
- stand-alone clinical decision support,
- a replacement for clinician judgment,
- a substitute for local policy, patient context, or full chart review.

## Scope boundaries

- The repository encodes specific respiratory SOFA logic and simulation
  assumptions implemented in the current codebase.
- Outputs should be interpreted in the context of those assumptions.
- Browser outputs are deterministic for fixed seeds but remain simulation
  summaries, not patient-specific recommendations.
- User-facing text must not overstate certainty beyond what the scoring and
  simulation logic actually supports.

## Data policy

- Do not commit PHI, patient-level raw extracts, restricted data, secrets, or
  publisher PDFs.
- Keep only small, de-identified, reproducible fixtures and summaries in version
  control.
- Generated web staging outputs are ignored and reproducible.

## Documentation expectations

Changes that affect interpretation, thresholds, assumptions, browser payloads,
or public language must update:
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/VALIDATION.md`
- `docs/PROVENANCE.md`
- this file

## Paired v2 model

The paired model is an uncalibrated illustrative simulation. Fixed support is
held independent of observation noise; the separately labeled assignment stress
test is not treatment physiology. Pointwise Monte Carlo intervals quantify finite
synthetic-patient sampling conditional on the model, not clinical or parameter
uncertainty. Delta outcomes are score changes, not sepsis incidence.

## Historical sensitivity extension

The v3 historical profile, normalized context boundary, conditional C views and
qualification limits are documented in [TROPS_SCORING_CONTRACT.md](TROPS_SCORING_CONTRACT.md).
The original v2 contract and reference evidence remain preserved. New frozen
requests live in `experiments/trops_v1/`; new evidence uses
`artifacts/trops_sensitivity_v1/`. Historical mapping is not SQL execution
validation or current-production equivalence.
