# Clinical scope

## Intended use

This repository is research software for:
- respiratory SOFA scoring logic,
- simulation of respiratory observation/support scenarios,
- validation and exploration of assumptions through a Streamlit applet.

## Not intended as

This repository is **not** presented as:
- a regulated medical device,
- stand-alone clinical decision support,
- a replacement for clinician judgment,
- a substitute for local policy, patient context, or full chart review.

## Scope boundaries

- The repository encodes specific respiratory SOFA logic and simulation assumptions implemented in the current codebase.
- Outputs should be interpreted in the context of those assumptions.
- User-facing text must not overstate certainty beyond what the scoring and simulation logic actually supports.

## Data policy

- Do not commit PHI, patient-level raw extracts, or restricted data.
- Keep only small, de-identified, reproducible fixtures and summaries in version control.

## Documentation expectations

Changes that affect interpretation, thresholds, assumptions, or public language must update:
- `README.md`
- `docs/VALIDATION.md`
- `docs/PROVENANCE.md`
- this file
