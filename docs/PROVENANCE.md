# Provenance

## Purpose

This file explains where checked-in non-code materials come from and how they
should be interpreted.

## Categories of material in this repository

### 1. Source code

- Python package code under `src/sofa_resp_sim/`
- tests under `tests/`
- web app code under `web/`
- staging and maintenance helpers under `scripts/`

Generated staged browser assets under `web/assets/py/` and `web/assets/data/`
are not source assets; regenerate them with `make stage-web`.

The packaged fallback CSV under `src/sofa_resp_sim/data/` intentionally mirrors
`artifacts/resp_sofa_sim_summary.csv` so the browser contract also works from an
installed wheel.

### 2. Canonical documentation

- `README.md`
- files in `docs/`
- ADRs in `docs/adr/`

### 3. Literature or reference files

No literature PDFs are currently tracked in git.

Local workspaces may contain untracked PDFs under `docs/`. Do not add them to
version control unless their provenance, purpose, and redistribution posture are
documented here first.

Public-release note: the current tracked tree does not include PDFs, but a
hosted repository may still expose historical blobs through old commits or PR
refs. Check `docs/PUBLIC_RELEASE_AUDIT.md` before changing repository visibility
or publishing a public mirror.

### 4. Generated validation artifacts

Files under `artifacts/` are small checked-in evidence files. Each should be
documented in `artifacts/README.md`.

The static app currently stages `artifacts/resp_sofa_sim_summary.csv` as its
reference distribution through `scripts/stage_web_python.py`.

## Data restrictions

- No PHI
- No patient-level raw extracts
- No restricted upstream datasets unless explicitly allowed and documented
- No credentials, API tokens, or private keys
- No publisher PDFs unless redistribution rights are explicitly documented

## REUSE staging plan

Stage 1:
- keep this provenance file truthful and complete,
- classify checked-in non-code assets,
- keep generated browser assets reproducible and ignored.

Stage 2:
- add machine-readable REUSE coverage and SPDX headers where appropriate.

## Paired v2 implementation provenance

The accepted implementation pack is preserved verbatim under
`docs/implementation/paired_experiment_goal/source/`; its planning ledger records
the archive hash and base commit. Legacy seeded outputs and historical artifact
hashes are frozen in `tests/experiments/fixtures/legacy_py_v1.json`. Existing
200-replicate distribution artifacts are saved synthetic benchmarks, not clinical
reference data. No independent clinical calibration or SQL equivalence has been
established by the paired implementation.

## Aggregate-reference template

`docs/templates/aggregate_reference.csv` and its matching JSON metadata are
invented aggregate examples for future local reference comparisons. Validate
with `sofa_resp_sim.reporting.aggregate_reference.validate_aggregate_reference`.
Each stratum requires seven explicit cells: observed scores 0-4, suppressed zero,
and no-qualifying-data zero. Include zero-count cells; counts must sum to one
positive patient denominator per stratum. Strata are validated independently;
validation does not establish that strata are disjoint.

Metadata requires source, extraction date, cohort and denominator definitions,
units (`patient_counts`), scoring profile and access class. The validator resolves
the scoring profile and rejects unknown fields/versions. Access classes are
`synthetic`, `public_aggregate`, and `restricted_aggregate`; the last is marked
ineligible for public export. Validation is schema/arithmetic checking, not
individual-level validation or clinical calibration. Templates are documentation
and are not automatically staged or uploaded.
