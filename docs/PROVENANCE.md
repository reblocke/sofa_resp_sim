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
