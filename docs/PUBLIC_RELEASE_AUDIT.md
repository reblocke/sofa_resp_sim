# Public release audit

## Current status

Last local audit: 2026-04-20.

No PHI, patient identifiers, patient-level extracts, credentials, tokens, SSNs,
MRNs, DOBs, emails, phone numbers, or obvious confidential research data were
found in the tracked `main` tree during the local scan.

The current tracked tree is intended to contain:
- source code,
- tests,
- documentation,
- small synthetic or aggregate validation artifacts.

## Known public-release blocker

Two literature PDFs are not tracked at `HEAD`, but were previously committed in
the GitHub PR #3 branch/merge history:
- `docs/approaches_to_converting_spo2_fio2_ratio_to.18.pdf`
- `docs/ccm_54_4_2025_12_09_chaudhuri_ccmed-d-25-00833_sdc1 (1).pdf`

They did not appear to contain PHI in the local text/metadata inspection, but
they are publisher-controlled documents and should not be redistributed through
repository history without confirming rights.

Before making an existing hosted repository public, either:
- purge those PDF blobs from git history and GitHub PR refs, or
- publish a fresh public repository from a clean `HEAD` export instead of the
  existing history.

## Suggested audit commands

Run from repo root:

```bash
git status --short --branch --ignored=matching
git ls-files
git log --all --name-only --pretty=format: | sort -u
git rev-list --objects --all | rg -i '(patient|phi|mrn|dob|ssn|secret|token|key|\\.pdf$|\\.csv$|\\.xlsx$|\\.parquet$|\\.dta$)'
git grep -n -I -E '(MRN|patient[ _-]?(id|name|dob|birth|record)|DOB|SSN|token|secret|password|api[_-]?key|private key)' -- ':!uv.lock'
```

If available, also run a dedicated secret scanner such as `gitleaks` or
`trufflehog` against all history.

## Policy

- Do not commit PHI, patient-level raw extracts, restricted data, credentials,
  or publisher PDFs.
- Keep `docs/*.pdf` ignored unless a specific documented licensing/provenance
  decision says otherwise.
- Keep checked-in validation artifacts small, synthetic or aggregate, and
  documented in `artifacts/README.md`.
