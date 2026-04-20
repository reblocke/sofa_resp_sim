# Provenance

## Purpose

This file explains where checked-in non-code materials come from and how they should be interpreted.

## Categories of material in this repository

### 1. Source code
- Python package code under `python/src/sofa_resp_sim/`
- tests under `python/tests/` and `tests/`

### 2. Canonical documentation
- `README.md`
- files in `docs/`
- ADRs in `docs/adr/`

### 3. Literature or reference files
No literature PDFs are currently tracked in git.

Local workspaces may contain untracked PDFs under `docs/`. Do not add them to
version control unless their provenance, purpose, and redistribution posture are
documented here first.

Rules:
- keep only files that are genuinely needed for project context or provenance,
- document why each checked-in reference exists,
- do not assume a checked-in PDF implies redistribution rights beyond what applies.

### 4. Generated validation artifacts
Files under `artifacts/` are small checked-in evidence files.
Each should be documented in `artifacts/README.md`.

## Data restrictions

- No PHI
- No patient-level raw extracts
- No restricted upstream datasets unless explicitly allowed and documented

## REUSE staging plan

Stage 1:
- keep this provenance file truthful and complete
- classify checked-in non-code assets

Stage 2:
- add machine-readable REUSE coverage and SPDX headers where appropriate
